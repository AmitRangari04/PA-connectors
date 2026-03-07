"""
Async Batch Processor
=====================
Handles concurrent processing of large data sets with configurable batch sizes.
Supports retry logic, timeout handling, and progress tracking.
"""

import asyncio
import logging
from typing import List, Any, Callable, TypeVar, Generic, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


class TaskStatus(Enum):
    """Status of a processing task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult(Generic[R]):
    """Result of a single task execution."""
    status: TaskStatus
    result: Optional[R] = None
    error: Optional[str] = None
    duration_ms: float = 0
    retries: int = 0


@dataclass
class BatchResult(Generic[R]):
    """Result of batch processing."""
    total: int
    successful: int
    failed: int
    results: List[TaskResult[R]]
    duration_ms: float
    started_at: datetime
    completed_at: datetime


class AsyncBatchProcessor(Generic[T, R]):
    """
    Processes items in batches with configurable concurrency.
    Supports retry logic and timeout handling.
    """
    
    def __init__(
        self,
        max_concurrent: int = 10,
        batch_size: int = 100,
        timeout: float = 30.0,
        retry_attempts: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize the batch processor.
        
        Args:
            max_concurrent: Maximum concurrent tasks
            batch_size: Items per batch
            timeout: Timeout per task in seconds
            retry_attempts: Number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.max_concurrent = max_concurrent
        self.batch_size = batch_size
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._cancelled = False
    
    async def _execute_with_retry(
        self,
        func: Callable[[T], R],
        item: T
    ) -> TaskResult[R]:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            item: Input item
            
        Returns:
            TaskResult with execution result
        """
        start_time = asyncio.get_event_loop().time()
        retries = 0
        last_error = None
        
        while retries <= self.retry_attempts:
            if self._cancelled:
                return TaskResult(
                    status=TaskStatus.CANCELLED,
                    duration_ms=(asyncio.get_event_loop().time() - start_time) * 1000
                )
            
            try:
                # Execute with timeout
                if asyncio.iscoroutinefunction(func):
                    result = await asyncio.wait_for(func(item), timeout=self.timeout)
                else:
                    result = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, func, item),
                        timeout=self.timeout
                    )
                
                return TaskResult(
                    status=TaskStatus.COMPLETED,
                    result=result,
                    duration_ms=(asyncio.get_event_loop().time() - start_time) * 1000,
                    retries=retries
                )
                
            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.timeout}s"
                logger.warning(f"Task timeout (attempt {retries + 1}/{self.retry_attempts + 1})")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Task error (attempt {retries + 1}/{self.retry_attempts + 1}): {e}")
            
            retries += 1
            if retries <= self.retry_attempts:
                await asyncio.sleep(self.retry_delay * retries)  # Exponential backoff
        
        return TaskResult(
            status=TaskStatus.FAILED,
            error=last_error,
            duration_ms=(asyncio.get_event_loop().time() - start_time) * 1000,
            retries=retries - 1
        )
    
    async def _process_item(
        self,
        func: Callable[[T], R],
        item: T
    ) -> TaskResult[R]:
        """Process a single item with semaphore control."""
        async with self._semaphore:
            return await self._execute_with_retry(func, item)
    
    async def process_batch(
        self,
        items: List[T],
        processor: Callable[[T], R],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> BatchResult[R]:
        """
        Process a batch of items concurrently.
        
        Args:
            items: List of items to process
            processor: Function to process each item
            progress_callback: Optional callback for progress updates
            
        Returns:
            BatchResult with all results
        """
        started_at = datetime.utcnow()
        start_time = asyncio.get_event_loop().time()
        self._cancelled = False
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Create tasks for all items
        tasks = [
            self._process_item(processor, item)
            for item in items
        ]
        
        # Process with progress tracking
        results: List[TaskResult[R]] = []
        completed = 0
        
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            completed += 1
            
            if progress_callback:
                progress_callback(completed, len(items))
        
        completed_at = datetime.utcnow()
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        
        successful = sum(1 for r in results if r.status == TaskStatus.COMPLETED)
        failed = sum(1 for r in results if r.status == TaskStatus.FAILED)
        
        return BatchResult(
            total=len(items),
            successful=successful,
            failed=failed,
            results=results,
            duration_ms=duration_ms,
            started_at=started_at,
            completed_at=completed_at
        )
    
    async def process_in_batches(
        self,
        items: List[T],
        processor: Callable[[T], R],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[BatchResult[R]]:
        """
        Process items in multiple batches.
        
        Args:
            items: All items to process
            processor: Function to process each item
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of BatchResults for each batch
        """
        batch_results = []
        total_processed = 0
        
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            
            def batch_progress(completed: int, total: int):
                if progress_callback:
                    progress_callback(total_processed + completed, len(items))
            
            result = await self.process_batch(batch, processor, batch_progress)
            batch_results.append(result)
            total_processed += len(batch)
            
            logger.info(
                f"Batch {len(batch_results)} completed: "
                f"{result.successful}/{result.total} successful"
            )
        
        return batch_results
    
    def cancel(self) -> None:
        """Cancel ongoing processing."""
        self._cancelled = True
        logger.info("Batch processing cancelled")


class ConnectionPool:
    """
    Simple connection pool for managing API client connections.
    Supports connection reuse and health checking.
    """
    
    def __init__(
        self,
        factory: Callable[[], Any],
        pool_size: int = 10,
        max_overflow: int = 20,
        timeout: int = 30,
        recycle: int = 3600
    ):
        """
        Initialize connection pool.
        
        Args:
            factory: Function to create new connections
            pool_size: Base pool size
            max_overflow: Maximum overflow connections
            timeout: Connection timeout in seconds
            recycle: Connection recycle time in seconds
        """
        self.factory = factory
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.timeout = timeout
        self.recycle = recycle
        
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self._overflow = 0
        self._lock = asyncio.Lock()
        self._created_at: Dict[int, float] = {}
    
    async def acquire(self) -> Any:
        """Acquire a connection from the pool."""
        try:
            # Try to get from pool without waiting
            conn = self._pool.get_nowait()
            
            # Check if connection needs recycling
            conn_id = id(conn)
            if conn_id in self._created_at:
                import time
                if time.time() - self._created_at[conn_id] > self.recycle:
                    logger.debug("Recycling old connection")
                    del self._created_at[conn_id]
                    conn = self.factory()
                    self._created_at[id(conn)] = time.time()
            
            return conn
            
        except asyncio.QueueEmpty:
            async with self._lock:
                if self._overflow < self.max_overflow:
                    self._overflow += 1
                    conn = self.factory()
                    import time
                    self._created_at[id(conn)] = time.time()
                    return conn
            
            # Wait for a connection
            return await asyncio.wait_for(
                self._pool.get(),
                timeout=self.timeout
            )
    
    async def release(self, conn: Any) -> None:
        """Release a connection back to the pool."""
        try:
            self._pool.put_nowait(conn)
        except asyncio.QueueFull:
            async with self._lock:
                self._overflow -= 1
    
    async def close_all(self) -> None:
        """Close all connections in the pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                if hasattr(conn, 'close'):
                    conn.close()
            except asyncio.QueueEmpty:
                break
        
        self._created_at.clear()
        self._overflow = 0
    
    def stats(self) -> Dict:
        """Get pool statistics."""
        return {
            "pool_size": self.pool_size,
            "available": self._pool.qsize(),
            "overflow": self._overflow,
            "max_overflow": self.max_overflow,
            "total_created": len(self._created_at)
        }
