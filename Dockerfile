#Use lightweight Python image
FROM python:3.11-slim

# Prevent Python from buffering logs
ENV PYTHONUNBUFFERED=True

# Set working directory inside container
WORKDIR /app

# Copy dependency file first (better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY app/ app/
COPY data/ data/
COPY .env .env
COPY .idea/ .idea/ 

# Default command to run script
CMD ["python", "main.py"]
