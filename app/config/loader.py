
import os

DEFAULTS = {
    "crowdstrike": {
        "base_url": "https://api.us-2.crowdstrike.com"
    }
}

def get_connector_config(name: str) -> dict:
    cfg = DEFAULTS.get(name, {}).copy()
    env_key = f"{name.upper()}_BASE_URL"
    if env_key in os.environ:
        print("from .env")
        cfg["base_url"] = os.environ[env_key]
    return cfg