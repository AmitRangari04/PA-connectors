import json
import pathlib
# from app.storage.raw import upload_to_gcs
from app.connectors.crowdstrike.fetcher import Fetcher
from app.storage.bigquery import insert_rows
from app.state.store import save_state, record_job
from app.eventbus.pubsub import publish
import requests

async def run_pipeline(tenant, name, fetcher):
    raws = await fetcher.fetch(tenant, {}, name)
    # enriched = []
    upload_to_gcs(tenant, name, raws)
    """

    # for item in raws:
    #     enriched.append(enricher.enrich(item, name))

    # if enriched:
    #     insert_rows(enriched)

    save_state(tenant, name, {"count": len(raws)})
    publish({"tenant": tenant, "collector": name, "records": len(raws)})

    record_job({
        "tenant": tenant,
        "collector": name,
        "records": len(raws)
    })"""
