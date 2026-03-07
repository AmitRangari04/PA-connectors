
import json
from pathlib import Path
from datetime import datetime
from google.cloud import storage

"""
def write_raw(tenant: str, connector: str, payload: dict):
    base = Path(f"data/raw/{tenant}/{connector}")
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{datetime.utcnow().isoformat().replace(':', '-')}.json"
    path.write_text(json.dumps(payload, indent=2))
"""

"""
def upload_to_gcs(tenant: str, connector: str, payload: dict):
    base = Path(f"data/raw/{tenant}/{connector}")
    # base.mkdir(parents=True, exist_ok=True)
    path = base / f"{datetime.utcnow().isoformat().replace(':', '-')}.json"
    # path.write_text(json.dumps(payload, indent=2)) 


    client = storage.Client()
    bucket = client.bucket('pa-bucket') 
    blob = bucket.blob(path)
    blob.upload_from_string(data=payload)
"""