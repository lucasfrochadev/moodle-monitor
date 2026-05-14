from fastapi import APIRouter

from api.services.sync_service import sync_service
from api.schemas import SyncResult
from api.config import config

router = APIRouter(prefix="/api/sync", tags=["Sync"])


@router.post("", response_model=SyncResult)
def trigger_sync():
    sync_service.set_monitor_path(config.monitor_db_path)
    return sync_service.sync()


@router.get("/status")
def sync_status():
    import os
    from pathlib import Path
    monitor_path = Path(config.monitor_db_path)
    study_path = Path(config.study_db_path)
    return {
        "monitor_db_exists": monitor_path.exists(),
        "study_db_exists": study_path.exists(),
        "monitor_db_size": monitor_path.stat().st_size if monitor_path.exists() else 0,
        "study_db_size": study_path.stat().st_size if study_path.exists() else 0,
    }
