from app.config.loader import get_connector_config
import os, time, requests
from dotenv import load_dotenv
#from app.core.secrets import get_secret

class CrowdStrikeAuth:
    def __init__(self, base_url: str):
        load_dotenv()
        self.base_url = os.getenv("CROWDSTRIKE_BASE_URL")
        self.token_url = f"{self.base_url}/oauth2/token"
        self.mock = os.getenv("MOCK_MODE","false").lower() == "true"
        # self.client_id = get_secret("CS_CLIENT_ID")
        self.client_id = os.getenv("CS_CLIENT_ID")
        # self.client_secret = get_secret("CS_CLIENT_SECRET")
        self.client_secret = os.getenv("CS_CLIENT_SECRET")
        self.token = None
        self.expiry = 0

    def _refresh(self):
        if self.mock:
            self.token = "mock-token"
            self.expiry = time.time() + 3600
            return

        r = requests.post(
            self.token_url,
            data={"client_id": self.client_id, "client_secret": self.client_secret},
            timeout=30
        )
        r.raise_for_status()
        d = r.json()
        self.token = d["access_token"]
        self.expiry = time.time() + int(d.get("expires_in",1800))

    def get_headers(self):
        if not self.token or time.time() > self.expiry:
            self._refresh()
        return {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}


def _auth():
    cfg = get_connector_config("crowdstrike")
    return cfg, CrowdStrikeAuth(cfg["base_url"])