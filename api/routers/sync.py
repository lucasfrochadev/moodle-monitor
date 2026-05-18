import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from api.services.sync_service import sync_service
from api.schemas import SyncResult
from api.config import config

logger = logging.getLogger("api.sync")
router = APIRouter(prefix="/api/sync", tags=["Sync"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _load_course_ids() -> list[int] | None:
    config_path = BASE_DIR / "config.yaml"
    if not config_path.exists():
        return None
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    ids = cfg.get("monitoring", {}).get("course_ids", [])
    return ids if ids else None


def _run_scraper() -> str:
    log_path = BASE_DIR / f"scraper_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "main.py"), "--once"],
        capture_output=True, text=True, timeout=600, cwd=str(BASE_DIR),
    )
    output = result.stdout or ""
    if result.stderr:
        output += "\nERROS:\n" + result.stderr
    log_path.write_text(output, encoding="utf-8")
    logger.info("Scraper output salvo em %s (returncode=%d)", log_path.name, result.returncode)
    if result.returncode != 0:
        raise RuntimeError(
            f"Scraper falhou (código {result.returncode}):\n{output}"
        )
    return output


@router.post("")
def trigger_sync():
    scraper_output = ""
    try:
        scraper_output = _run_scraper()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraper: {e}")

    sync_service.set_monitor_path(config.monitor_db_path)
    course_ids = _load_course_ids()
    try:
        result = sync_service.sync(course_ids)
    except Exception as e:
        import traceback
        logger.error("Sync error: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Sync: {e}")
    result["message"] = f"Scraper executado. " + result["message"]
    return result


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
