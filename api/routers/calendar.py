from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from api.database import db
from api.schemas import new_id, now, CalendarEventCreate, CalendarEventUpdate, CalendarEventOut

router = APIRouter(prefix="/api/calendar", tags=["Calendar"])


@router.get("/events", response_model=list[CalendarEventOut])
def list_events(
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    sql = "SELECT * FROM calendar_events"
    params = []
    conditions = []
    if date:
        conditions.append("event_date = ?")
        params.append(date)
    if month:
        conditions.append("event_date LIKE ?")
        params.append(f"{month}%")
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY event_date, event_time"
    with db.transaction() as cur:
        rows = cur.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


@router.get("/events/today", response_model=list[CalendarEventOut])
def list_today():
    return list_events(date=now()[:10])


@router.post("/events", response_model=CalendarEventOut, status_code=201)
def create_event(body: CalendarEventCreate):
    eid = new_id()
    ts = now()
    color = body.color or "#8B5CF6"
    with db.transaction() as cur:
        cur.execute(
            """INSERT INTO calendar_events (id, title, event_date, event_time, event_type, description, color, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (eid, body.title, body.event_date, body.event_time,
             body.event_type, body.description, color, ts, ts),
        )
    return {
        "id": eid, "title": body.title, "event_date": body.event_date,
        "event_time": body.event_time, "event_type": body.event_type,
        "description": body.description, "color": color,
        "created_at": ts, "updated_at": ts,
    }


@router.put("/events/{event_id}", response_model=CalendarEventOut)
def update_event(event_id: str, body: CalendarEventUpdate):
    with db.transaction() as cur:
        row = cur.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Evento não encontrado")
        updates = {}
        for field in ("title", "event_date", "event_time", "event_type", "description", "color"):
            val = getattr(body, field, None)
            if val is not None:
                updates[field] = val
        if not updates:
            return dict(row)
        updates["updated_at"] = now()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        vals = list(updates.values()) + [event_id]
        cur.execute(f"UPDATE calendar_events SET {set_clause} WHERE id = ?", vals)
        row = cur.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,)).fetchone()
    return dict(row)


@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: str):
    with db.transaction() as cur:
        row = cur.execute("SELECT id FROM calendar_events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Evento não encontrado")
        cur.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))


@router.get("/board-tasks")
def list_board_tasks():
    with db.transaction() as cur:
        rows = cur.execute("""
            SELECT t.id, t.title, t.discipline, t.due_date, t.priority, t.status,
                   t.column_id, t.board_id
            FROM tasks t
            WHERE t.due_date IS NOT NULL AND t.archived = 0
            ORDER BY t.due_date
        """).fetchall()
    return [dict(r) for r in rows]
