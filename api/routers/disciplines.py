from pathlib import Path

import sqlite3
import yaml

from fastapi import APIRouter

router = APIRouter(prefix="/api/disciplines", tags=["Disciplinas"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"
MONITOR_DB_PATH = BASE_DIR / "data" / "monitor.db"


def _load_course_ids() -> list[int]:
    if not CONFIG_PATH.exists():
        return []
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("monitoring", {}).get("course_ids", [])


def _fetch_names(course_ids: list[int]) -> dict[int, str]:
    if not MONITOR_DB_PATH.exists() or not course_ids:
        return {}
    try:
        conn = sqlite3.connect(str(MONITOR_DB_PATH))
        conn.row_factory = sqlite3.Row
        placeholders = ",".join("?" * len(course_ids))
        rows = conn.execute(
            f"SELECT moodle_course_id, fullname FROM courses WHERE moodle_course_id IN ({placeholders})",
            course_ids,
        ).fetchall()
        conn.close()
        return {r["moodle_course_id"]: r["fullname"] for r in rows}
    except Exception:
        return {}


@router.get("")
def list_disciplines():
    course_ids = _load_course_ids()
    names = _fetch_names(course_ids)

    results = []
    for cid in course_ids:
        name = names.get(cid, f"Curso {cid}")
        results.append({
            "id": str(cid),
            "name": name,
            "code": f"COD{cid}",
            "course_id": cid,
        })
    return results
