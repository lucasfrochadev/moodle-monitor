from api.database import db
from api.schemas import new_id, now


class BoardService:

    def list_all(self) -> list[dict]:
        rows = db.execute(
            "SELECT * FROM boards ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_by_id(self, board_id: str) -> dict | None:
        row = db.execute(
            "SELECT * FROM boards WHERE id = ?", (board_id,)
        ).fetchone()
        return dict(row) if row else None

    def create(self, name: str, description: str = "", color: str = "#4A90D9") -> dict:
        board_id = new_id()
        ts = now()
        with db.transaction() as cur:
            cur.execute(
                "INSERT INTO boards (id, name, description, color, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (board_id, name, description, color, ts, ts),
            )
        return self.get_by_id(board_id)

    def update(self, board_id: str, data: dict) -> dict | None:
        fields = []
        params = []
        for key in ("name", "description", "color"):
            if key in data and data[key] is not None:
                fields.append(f"{key} = ?")
                params.append(data[key])
        if not fields:
            return self.get_by_id(board_id)
        fields.append("updated_at = ?")
        params.append(now())
        params.append(board_id)
        with db.transaction() as cur:
            cur.execute(
                f"UPDATE boards SET {', '.join(fields)} WHERE id = ?",
                params,
            )
        return self.get_by_id(board_id)

    def delete(self, board_id: str) -> bool:
        with db.transaction() as cur:
            cur.execute("DELETE FROM tasks WHERE board_id = ?", (board_id,))
            cur.execute("DELETE FROM columns WHERE board_id = ?", (board_id,))
            cur.execute("DELETE FROM boards WHERE id = ?", (board_id,))
            return cur.rowcount > 0

    def get_full_board(self, board_id: str) -> dict | None:
        board = self.get_by_id(board_id)
        if not board:
            return None
        columns = db.execute(
            "SELECT * FROM columns WHERE board_id = ? ORDER BY position",
            (board_id,),
        ).fetchall()
        board["columns"] = []
        for col in columns:
            col = dict(col)
            tasks = db.execute(
                "SELECT * FROM tasks WHERE column_id = ? AND archived = 0 ORDER BY position",
                (col["id"],),
            ).fetchall()
            col["tasks"] = [dict(t) for t in tasks]
            board["columns"].append(col)
        return board


board_service = BoardService()
