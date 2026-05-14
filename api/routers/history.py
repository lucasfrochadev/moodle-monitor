from fastapi import APIRouter
from api.database import db

router = APIRouter(prefix="/api/history", tags=["Histórico"])


@router.get("/{task_id}")
def task_history(task_id: str, limit: int = 50):
    rows = db.execute("""
        SELECT * FROM task_history
        WHERE task_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (task_id, limit)).fetchall()
    return [dict(r) for r in rows]
