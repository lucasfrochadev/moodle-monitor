from fastapi import APIRouter, Query
from datetime import datetime, timezone, timedelta

from api.database import db
from api.schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardStats)
def dashboard(
    due_date_after: str = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    now_dt = datetime.utcnow().replace(tzinfo=None)
    today_str = now_dt.strftime("%Y-%m-%d")

    after = due_date_after or today_str
    week_end = (now_dt + timedelta(days=7)).strftime("%Y-%m-%d")

    total_tasks = db.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE archived = 0 AND due_date >= ?",
        (after,),
    ).fetchone()["c"]

    pending = db.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE status = 'pending' AND archived = 0 AND due_date >= ?",
        (after,),
    ).fetchone()["c"]

    in_progress = db.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE status = 'in_progress' AND archived = 0 AND due_date >= ?",
        (after,),
    ).fetchone()["c"]

    completed = db.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE status = 'completed' AND archived = 0 AND due_date >= ?",
        (after,),
    ).fetchone()["c"]

    archived = db.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE archived = 1"
    ).fetchone()["c"]

    overdue = db.execute("""
        SELECT COUNT(*) AS c FROM tasks
        WHERE due_date IS NOT NULL
          AND due_date >= ?
          AND due_date < ?
          AND status NOT IN ('completed', 'archived')
          AND archived = 0
    """, (after, now_dt.isoformat())).fetchone()["c"]

    due_this_week = db.execute("""
        SELECT COUNT(*) AS c FROM tasks
        WHERE due_date IS NOT NULL
          AND due_date >= ?
          AND due_date <= ?
          AND archived = 0
    """, (now_dt.isoformat(), week_end)).fetchone()["c"]

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
