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


@router.get("/default", response_model=BoardFull)
def get_default_board():
    boards = board_service.list_all()
    if boards:
        quadro = next((b for b in boards if b["name"] == "Quadro"), boards[0])
        board = board_service.get_full_board(quadro["id"])
    else:
        board = board_service.create("Quadro", "Quadro principal", "#4A90D9")
        board = board_service.get_full_board(board["id"])
        col_names = ["A Fazer", "Em Andamento", "Concluído"]
        from api.database import db
        for i, name in enumerate(col_names):
            db.execute(
                "INSERT INTO columns (id, board_id, name, position, created_at) VALUES (?, ?, ?, ?, ?)",
                (f"col_{i}_{board['id']}", board["id"], name, i, board["created_at"]),
            )
        board = board_service.get_full_board(board["id"])
    if not board:
        raise HTTPException(404, "Board not found")
    return board


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
