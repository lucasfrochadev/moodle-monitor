from fastapi import APIRouter, HTTPException

from api.database import db
from api.schemas import ColumnCreate, ColumnUpdate, ColumnOut, ReorderPayload, new_id, now

router = APIRouter(prefix="/api/boards/{board_id}/columns", tags=["Columns"])


@router.get("")
def list_columns(board_id: str):
    rows = db.execute(
        "SELECT * FROM columns WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("", response_model=ColumnOut, status_code=201)
def create_column(board_id: str, body: ColumnCreate):
    board = db.execute("SELECT id FROM boards WHERE id = ?", (board_id,)).fetchone()
    if not board:
        raise HTTPException(404, "Board not found")
    col_id = new_id()
    position = body.position
    if position is None:
        position = db.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS np FROM columns WHERE board_id = ?",
            (board_id,),
        ).fetchone()["np"]
    with db.transaction() as cur:
        cur.execute(
            "INSERT INTO columns (id, board_id, name, position, color) VALUES (?, ?, ?, ?, ?)",
            (col_id, board_id, body.name, position, body.color),
        )
    row = db.execute("SELECT * FROM columns WHERE id = ?", (col_id,)).fetchone()
    return dict(row)


@router.put("/{column_id}", response_model=ColumnOut)
def update_column(board_id: str, column_id: str, body: ColumnUpdate):
    col = db.execute(
        "SELECT * FROM columns WHERE id = ? AND board_id = ?",
        (column_id, board_id),
    ).fetchone()
    if not col:
        raise HTTPException(404, "Column not found")
    fields = []
    params = []
    for key in ("name", "color", "position"):
        if getattr(body, key, None) is not None:
            fields.append(f"{key} = ?")
            params.append(getattr(body, key))
    if fields:
        params.append(column_id)
        with db.transaction() as cur:
            cur.execute(
                f"UPDATE columns SET {', '.join(fields)} WHERE id = ?",
                params,
            )
    row = db.execute("SELECT * FROM columns WHERE id = ?", (column_id,)).fetchone()
    return dict(row)


@router.delete("/{column_id}", status_code=204)
def delete_column(board_id: str, column_id: str):
    col = db.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?",
        (column_id, board_id),
    ).fetchone()
    if not col:
        raise HTTPException(404, "Column not found")
    with db.transaction() as cur:
        cur.execute("UPDATE tasks SET column_id = NULL WHERE column_id = ?", (column_id,))
        cur.execute("DELETE FROM columns WHERE id = ?", (column_id,))


@router.put("/reorder")
def reorder_columns(board_id: str, body: ReorderPayload):
    with db.transaction() as cur:
        for item in body.items:
            cur.execute(
                "UPDATE columns SET position = ? WHERE id = ? AND board_id = ?",
                (item["position"], item["id"], board_id),
            )
    return {"ok": True}
