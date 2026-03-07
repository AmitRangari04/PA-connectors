from datetime import datetime

STATE = {}
JOBS = []

def get_state(t,c):
    return STATE.get((t,c),{})

def save_state(t,c,s):
    STATE[(t,c)] = s

def record_job(job: dict):
    job["timestamp"] = datetime.utcnow().isoformat()
    JOBS.append(job)

def get_jobs(limit=50):
    return JOBS[-limit:]
