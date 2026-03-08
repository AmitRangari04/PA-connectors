import json
import os, requests
import pathlib
import time
from urllib.parse import quote

from app.connectors.crowdstrike.auth import _auth
from dotenv import load_dotenv
# import httpx
from pathlib import Path
from datetime import datetime
from google.cloud import storage

class Fetcher:
    def __init__(self, query="", auth=""):
        load_dotenv()
        self.query = query
        self.mock = os.getenv("MOCK_MODE", "false").lower() == "true"
        if auth:
            self.auth = auth
            print("self.auth:", self.auth[0],type(self.auth))
            self.base_url = auth[0]["base_url"]

    def fetch(self, tenant="", state={}, name=""):
        # if self.mock:
        #     return _mock("users-api") #edit this
        print("tenant found: ",tenant)
        if tenant:  # fetching for enrichment
            
            endpoints = {'cs_apps': ({"tenant": tenant, "device_id": "abc123", "name": "Chrome", "version": "120"},
                                     "/devices/queries/installed-applications/v1",
                                     "/devices/entities/installed-applications/v1"),
                         'cs_devices': ({"tenant": tenant, "device_id": "abc123", "hostname": "laptop-1"},
                                        "/devices/queries/devices/v1",
                                        "/devices/entities/devices/v2"),
                         'cs_processes': ({"tenant": tenant, "process_name": "chrome.exe", "device_id": "abc123"},
                                          "/devices/queries/processes/v1",
                                          "/devices/entities/processes/v1"),
                         'cs_users': ({"tenant": tenant, "user_id": "u1", "username": "admin"},
                                      "/users/queries/users/v1",
                                      "/users/entities/users/v1"),
                         'cs_vulns': ({"tenant": tenant, "cve_id": "CVE-2024-0001", "severity": "high"},
                                      "/spotlight/queries/vulnerabilities/v1",
                                      "/spotlight/entities/vulnerabilities/v2")}

            # if self.mock:
            #     return [endpoints.get(name)[0]]
            queries_endpoint = endpoints.get(name)[1]
            entities_endpoint = endpoints.get(name)[2]
            self.query = queries_endpoint

        cfg, auth = _auth()
        start_time = time.time()
        print("query  -----   ", self.query)
        r = requests.get(f"{cfg['base_url']}{self.query}", headers=auth.get_headers(), timeout=30)
        # async with httpx.AsyncClient() as client:
        #     r = await client.get(f"{cfg['base_url']}{self.query}", headers=auth.get_headers(), timeout=30)
        #     r.raise_for_status()
        if tenant:
            ids = r.json()["resources"]
            results = []
            for i in range(0, len(ids), 100):
                er = requests.get(
                        f"{cfg['base_url']}{entities_endpoint}",
                        headers=self.auth.get_headers(),
                        params={"ids": ids[i:i + 100]}
                )
                for a in er.json().get("resources", []):
                    a["tenant"] = tenant
                    results.append(a)
                # for a in dr.json().get("resources", []):
                #     a["tenant"] = tenant
                #     results.append(a)
                    print("time taken ", time.time() - start_time)
            return results
        print("time taken ", time.time() - start_time)
        return r.json()

    def upload_to_gcs(self, tenant: str, connector: str):
        fp = 'data/raw/acme44/cs_devices/2026-02-24T07-33-48.397853.json'
        path = f"{tenant}/{connector}/{datetime.utcnow().isoformat().replace(':', '-').replace('.','-')}.json"
        # path.write_text(json.dumps(payload, indent=2))
        project_id = os.getenv('GCP_PROJECT_ID')
        client = storage.Client(project=project_id)
        bucket_name = os.getenv('BUCKET_NAME')
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(path)
        blob.upload_from_filename(filename=fp, content_type="application/json")

        # blob.upload_from_string(data=payload)

"""
class Fetcher:
    def __init__(self, query):
        self.query = query
        self.mock = os.getenv("MOCK_MODE", "false").lower() == "true"

    def fetch(self):
        if self.mock:
            return _mock("users-api")

        cfg, auth = _auth()
        r = requests.get(
            f"{cfg['base_url']}/{self.query}",
            headers=auth.get_headers(), timeout=30
        )
        return r.json()
        """
