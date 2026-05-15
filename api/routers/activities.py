from fastapi import APIRouter, Query

from api.database import db
from api.services.task_service import task_service
from api.schemas import ActivityImportOut

router = APIRouter(prefix="/api/activities", tags=["Atividades Vigentes"])


from datetime import datetime


@router.get("/vigent")
def list_vigent(
    disciplina: str = None,
    status: str = None,
    due_date_before: str = None,
    due_date_after: str = None,
):
    results = task_service.list_vigent()
    if disciplina:
        results = [r for r in results
                   if r.get("discipline", "").lower() == disciplina.lower()]
    if status:
        results = [r for r in results if r.get("status") == status]
    if due_date_before:
        limit = _parse_date(due_date_before)
        if limit:
            results = [r for r in results
                       if r.get("due_date")
                       and _parse_date(str(r["due_date"]))
                       and _parse_date(str(r["due_date"])) <= limit]
    if due_date_after:
        limit = _parse_date(due_date_after)
        if limit:
            results = [r for r in results
                       if not r.get("due_date")
                       or (_parse_date(str(r["due_date"]))
                           and _parse_date(str(r["due_date"])) >= limit)]
    return results


def _parse_date(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


@router.get("/imported")
def list_imported(limit: int = Query(100, ge=1, le=500)):
    rows = db.execute("""
        SELECT ai.*, t.title, t.discipline, t.status, t.due_date
        FROM activity_imports ai
        JOIN tasks t ON t.id = ai.task_id
        ORDER BY ai.last_synced_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(r) for r in rows]
