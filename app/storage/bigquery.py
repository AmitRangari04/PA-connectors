
import os, json

def insert_rows(rows: list):
    os.makedirs("data", exist_ok=True)
    with open("data/bigquery_fallback.jsonl", "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
