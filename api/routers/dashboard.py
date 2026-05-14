from fastapi import APIRouter
from datetime import datetime, timezone

from api.database import db
from api.schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardStats)
def dashboard():
    now_dt = datetime.utcnow().replace(tzinfo=None)

    total_tasks = db.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE archived = 0"
    ).fetchone()["c"]

    pending = db.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE status = 'pending' AND archived = 0"
    ).fetchone()["c"]

    in_progress = db.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE status = 'in_progress' AND archived = 0"
    ).fetchone()["c"]

    completed = db.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE status = 'completed' AND archived = 0"
    ).fetchone()["c"]

    archived = db.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE archived = 1"
    ).fetchone()["c"]

    overdue = db.execute("""
        SELECT COUNT(*) AS c FROM tasks
        WHERE due_date IS NOT NULL
          AND due_date < ?
          AND status NOT IN ('completed', 'archived')
          AND archived = 0
    """, (now_dt.isoformat(),)).fetchone()["c"]

    due_this_week = db.execute("""
        SELECT COUNT(*) AS c FROM tasks
        WHERE due_date IS NOT NULL
          AND due_date >= ?
          AND due_date <= ?
          AND archived = 0
    """, (
        now_dt.isoformat(),
        datetime(now_dt.year, now_dt.month, now_dt.day + 7
                 if now_dt.day + 7 <= 28 else 28).isoformat(),
    )).fetchone()["c"]

    total_boards = db.execute(
        "SELECT COUNT(*) AS c FROM boards"
    ).fetchone()["c"]

    total_imports = db.execute(
        "SELECT COUNT(*) AS c FROM activity_imports"
    ).fetchone()["c"]

    return DashboardStats(
        total_tasks=total_tasks,
        pending=pending,
        in_progress=in_progress,
        completed=completed,
        overdue=overdue,
        archived=archived,
        due_this_week=due_this_week,
        total_boards=total_boards,
        total_activities_imported=total_imports,
    )
