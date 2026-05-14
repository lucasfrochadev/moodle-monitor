from fastapi import APIRouter, HTTPException, Query

from api.database import db
from api.schemas import (
    TaskCreate, TaskUpdate, TaskMove, TaskOut, ReorderPayload,
)
from api.services.task_service import task_service

router = APIRouter(prefix="/api/boards/{board_id}/tasks", tags=["Tasks"])


@router.get("")
def list_tasks(
    board_id: str,
    column_id: str = None,
    status: str = None,
    discipline: str = None,
    archived: bool = None,
):
    filters = {}
    if column_id:
        filters["column_id"] = column_id
    if status:
        filters["status"] = status
    if discipline:
        filters["discipline"] = discipline
    if archived is not None:
        filters["archived"] = archived
    return task_service.list_by_board(board_id, filters or None)


@router.post("", response_model=TaskOut, status_code=201)
def create_task(board_id: str, body: TaskCreate):
    board = db.execute("SELECT id FROM boards WHERE id = ?", (board_id,)).fetchone()
    if not board:
        raise HTTPException(404, "Board not found")
    return task_service.create(board_id, body.model_dump())


@router.get("/{task_id}", response_model=TaskOut)
def get_task(board_id: str, task_id: str):
    task = task_service.get_by_id(task_id)
    if not task or task["board_id"] != board_id:
        raise HTTPException(404, "Task not found")
    return task


@router.put("/{task_id}", response_model=TaskOut)
def update_task(board_id: str, task_id: str, body: TaskUpdate):
    old = task_service.get_by_id(task_id)
    if not old or old["board_id"] != board_id:
        raise HTTPException(404, "Task not found")
    result = task_service.update(task_id, body.model_dump(exclude_none=True))
    return result


@router.put("/{task_id}/move", response_model=TaskOut)
def move_task(board_id: str, task_id: str, body: TaskMove):
    task = task_service.get_by_id(task_id)
    if not task or task["board_id"] != board_id:
        raise HTTPException(404, "Task not found")
    result = task_service.move(task_id, body.column_id, body.position)
    if not result:
        raise HTTPException(400, "Invalid move destination")
    return result


@router.put("/reorder")
def reorder_tasks(board_id: str, body: ReorderPayload):
    task_service.reorder(body.items)
    return {"ok": True}


@router.delete("/{task_id}", status_code=204)
def delete_task(board_id: str, task_id: str):
    task = task_service.get_by_id(task_id)
    if not task or task["board_id"] != board_id:
        raise HTTPException(404, "Task not found")
    task_service.delete(task_id)
