# from os import name
from app.pipelines.runner import run_pipeline
from app.connectors.crowdstrike.fetcher import Fetcher
from app.connectors.crowdstrike.auth import _auth


# from app.storage.raw import upload_to_gcs
if __name__ == "__main__":
    # run_pipeline("acme", "cs_devices", Fetcher(auth=_auth()))
    fetcher = Fetcher(auth=_auth())
    print("fetcher created: ", fetcher, type(fetcher))
    # raws = fetcher.fetch("acme", {}, "cs_devices")
    # print("raws: ", raws)
    print("fetcher ran successfully")
    fetcher.upload_to_gcs("acme", "cs_devices")
