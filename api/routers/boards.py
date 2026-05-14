from fastapi import APIRouter, HTTPException

from api.schemas import BoardCreate, BoardUpdate, BoardOut, BoardFull
from api.services.board_service import board_service

router = APIRouter(prefix="/api/boards", tags=["Boards"])


@router.get("")
def list_boards():
    return board_service.list_all()


@router.post("", response_model=BoardOut, status_code=201)
def create_board(body: BoardCreate):
    return board_service.create(body.name, body.description, body.color)


@router.get("/{board_id}", response_model=BoardFull)
def get_board(board_id: str):
    board = board_service.get_full_board(board_id)
    if not board:
        raise HTTPException(404, "Board not found")
    return board


@router.put("/{board_id}", response_model=BoardOut)
def update_board(board_id: str, body: BoardUpdate):
    board = board_service.update(board_id, body.model_dump(exclude_none=True))
    if not board:
        raise HTTPException(404, "Board not found")
    return board


@router.delete("/{board_id}", status_code=204)
def delete_board(board_id: str):
    if not board_service.delete(board_id):
        raise HTTPException(404, "Board not found")
