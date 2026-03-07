import os, requests
from app.connectors.crowdstrike.auth import _auth

class Fetcher:
    def __init__(self, query="",auth="",name=""):
        self.query = query
        self.mock = os.getenv("MOCK_MODE", "false").lower() == "true"
        if auth:
            self.name = name
            self.auth = auth
            self.base_url = auth.base_url

    def fetch(self,tenant="",state={}):
        if self.mock:
            return _mock("users-api") #edit this

        if tenant:  #fetching for enrichment
            endpoints = {'apps': ({"tenant": tenant, "device_id": "abc123", "name": "Chrome", "version": "120"},
                                "/devices/queries/installed-applications/v1",
                                "/devices/entities/installed-applications/v1"),
                        'devices': ({"tenant": tenant, "device_id": "abc123", "hostname": "laptop-1"},
                                    "/devices/queries/devices/v1",
                                    "/devices/entities/devices/v2"),
                        'processes': ({"tenant": tenant, "process_name": "chrome.exe", "device_id": "abc123"},
                                    "/devices/queries/processes/v1",
                                    "/devices/entities/processes/v1"),
                        'users': ({"tenant": tenant, "user_id": "u1", "username": "admin"},
                                "/users/queries/users/v1",
                                "/users/entities/users/v1"),
                        'vulnerabilities': ({"tenant": tenant, "cve_id": "CVE-2024-0001", "severity": "high"},
                                            "/spotlight/queries/vulnerabilities/v1",
                                            "/spotlight/entities/vulnerabilities/v2")}

            if self.mock:
                return [endpoints.get(self.name)[0]]
            queries_endpoint = endpoints.get(self.name)[1]
            entities_endpoint = endpoints.get(self.name)[2]
            self.query = queries_endpoint

        cfg, auth = _auth()
        r = requests.get(
            f"{cfg['base_url']}{self.query}",
            headers=auth.get_headers(), timeout=30
        )
        if tenant:
            ids = r.json().get("resources", [])
            results = []

            for i in range(0, len(ids), 100):
                er = requests.get(
                    f"{cfg['base_url']}{entities_endpoint}",
                    headers=self.auth.get_headers(),
                    params={"ids": ",".join(ids[i:i + 100])}
                )
                er.raise_for_status()
                for a in er.json().get("resources", []):
                    a["tenant"] = tenant
                    results.append(a)
            return results
        return r.json()





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
        