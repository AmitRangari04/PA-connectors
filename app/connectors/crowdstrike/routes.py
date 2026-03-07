from fastapi import APIRouter
from app.config.loader import get_connector_config
from app.connectors.crowdstrike.auth import CrowdStrikeAuth
from app.connectors.crowdstrike.fetcher import Fetcher
from app.connectors.crowdstrike.enricher import Enricher
from app.pipelines.runner import run_pipeline

router = APIRouter(prefix="/crowdstrike")

def _auth():
    cfg = get_connector_config("crowdstrike")
    return CrowdStrikeAuth(cfg["base_url"])

#==================================================================================
# Fetcher Routes
#==================================================================================

@router.get("/devices/raw",tags=["Fetcher"])
async def fetch_devices():
    return await Fetcher(query="/devices/queries/devices/v1").fetch()

@router.get("/apps/raw",tags=["Fetcher"])
async def apps_raw():
    return await Fetcher(query="/devices/queries/installed-applications/v1").fetch()

@router.get("/apps/hosts",tags=["Fetcher"])
async def apps_hosts():
    return await Fetcher(query="/devices/queries/devices-hidden/v1").fetch()

#==================================================================================
# Enrichment Routes
#==================================================================================

@router.post("/run/{tenant}/crowdstrike/devices",tags=["Enricher"])
async def run_devices(tenant: str):
    await run_pipeline(tenant, "cs_devices", Fetcher(auth=_auth()), Enricher())
    return {"status": "ok", "collector": "devices"}


@router.post("/run/{tenant}/crowdstrike/users",tags=["Enricher"])
def run_users(tenant: str):
    run_pipeline(tenant, "cs_users", Fetcher(auth=_auth()), Enricher())
    return {"status": "ok", "collector": "users"}


@router.post("/run/{tenant}/crowdstrike/apps",tags=["Enricher"])
def run_apps(tenant: str):
    run_pipeline(tenant, "cs_apps", Fetcher(auth=_auth()), Enricher())
    return {"status": "ok", "collector": "apps"}


@router.post("/run/{tenant}/crowdstrike/processes",tags=["Enricher"])
def run_processes(tenant: str):
    run_pipeline(tenant, "cs_processes", Fetcher(auth=_auth()), Enricher())
    return {"status": "ok", "collector": "processes"}


@router.post("/run/{tenant}/crowdstrike/vulnerabilities",tags=["Enricher"])
def run_vulns(tenant: str):
    run_pipeline(tenant, "cs_vulns", Fetcher(auth=_auth()), Enricher())
    return {"status": "ok", "collector": "vulnerabilities"}
