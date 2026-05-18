from api.database import db
from api.schemas import new_id, now
from api.services.board_service import board_service


class TaskService:

    def _row(self, task_id: str, cur=None) -> dict | None:
        exec_fn = cur.execute if cur else db.execute
        row = exec_fn("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

    def _enrich(self, task: dict) -> dict:
        imp = db.execute(
            "SELECT source_course_name, source_activity_id FROM activity_imports WHERE task_id = ?",
            (task["id"],),
        ).fetchone()
        if imp:
            task["source_course_name"] = imp["source_course_name"] or ""
            task["source_activity_id"] = imp["source_activity_id"] or ""
        else:
            task["source_course_name"] = ""
            task["source_activity_id"] = ""
        return task

    def list_by_board(self, board_id: str, filters: dict = None) -> list[dict]:
        query = "SELECT * FROM tasks WHERE board_id = ?"
        params = [board_id]
        if filters:
            if filters.get("column_id"):
                query += " AND column_id = ?"
                params.append(filters["column_id"])
            if filters.get("status"):
                query += " AND status = ?"
                params.append(filters["status"])
            if filters.get("discipline"):
                query += " AND discipline = ?"
                params.append(filters["discipline"])
            if filters.get("archived") is not None:
                query += " AND archived = ?"
                params.append(1 if filters["archived"] else 0)
            else:
                query += " AND archived = 0"
        else:
            query += " AND archived = 0"
        query += " ORDER BY position, created_at"
        rows = db.execute(query, params).fetchall()
        return [self._enrich(dict(r)) for r in rows]

    def get_by_id(self, task_id: str) -> dict | None:
        task = self._row(task_id)
        if task:
            task = self._enrich(task)
        return task

    def create(self, board_id: str, data: dict) -> dict:
        task_id = new_id()
        ts = now()
        column_id = data.get("column_id")
        if column_id:
            col = db.execute(
                "SELECT id FROM columns WHERE id = ? AND board_id = ?",
                (column_id, board_id),
            ).fetchone()
            if not col:
                column_id = None
        if not column_id:
            first_col = db.execute(
                "SELECT id FROM columns WHERE board_id = ? ORDER BY position LIMIT 1",
                (board_id,),
            ).fetchone()
            column_id = first_col["id"] if first_col else None

        max_pos = db.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS np FROM tasks WHERE column_id = ?",
            (column_id,),
        ).fetchone()["np"]

        due = data.get("due_date")
        pub = data.get("publication_date")

        with db.transaction() as cur:
            cur.execute("""
                INSERT INTO tasks
                    (id, column_id, board_id, title, description, discipline,
                     due_date, publication_date, status, priority, position,
                     activity_url, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id, column_id, board_id,
                data["title"], data.get("description", ""),
                data.get("discipline", ""),
                due, pub,
                data.get("status", "pending"),
                data.get("priority", 0),
                max_pos,
                data.get("activity_url", ""),
                ts, ts,
            ))
        return self._enrich(self._row(task_id))

    def update(self, task_id: str, data: dict) -> dict | None:
        old = self._row(task_id)
        if not old:
            return None
        fields = []
        params = []
        for key in ("title", "description", "discipline", "status",
                     "priority", "position", "activity_url"):
            if key in data and data[key] is not None:
                fields.append(f"{key} = ?")
                params.append(data[key])
        if "due_date" in data:
            fields.append("due_date = ?")
            params.append(data["due_date"])
        if "publication_date" in data:
            fields.append("publication_date = ?")
            params.append(data["publication_date"])
        if "archived" in data and data["archived"] is not None:
            fields.append("archived = ?")
            params.append(1 if data["archived"] else 0)
        if "column_id" in data and data["column_id"] is not None:
            fields.append("column_id = ?")
            params.append(data["column_id"])

        if not fields:
            return self._enrich(old)

        fields.append("updated_at = ?")
        params.append(now())
        params.append(task_id)

        with db.transaction() as cur:
            cur.execute(
                f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?",
                params,
            )
            self._log_history(cur, task_id, old, data)
        return self._enrich(self._row(task_id))

    def move(self, task_id: str, column_id: str, position: int = None) -> dict | None:
        task = self._row(task_id)
        if not task:
            return None
        col = db.execute(
            "SELECT id FROM columns WHERE id = ?", (column_id,)
        ).fetchone()
        if not col:
            return None

        if position is None:
            position = db.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 AS np FROM tasks WHERE column_id = ?",
                (column_id,),
            ).fetchone()["np"]

        with db.transaction() as cur:
            old_task = dict(task)
            cur.execute(
                "UPDATE tasks SET column_id = ?, position = ?, updated_at = ? WHERE id = ?",
                (column_id, position, now(), task_id),
            )
            self._log_history(cur, task_id, old_task, {
                "column_id": column_id,
                "position": position,
            })
        return self._enrich(self._row(task_id))

    def reorder(self, items: list[dict]) -> bool:
        with db.transaction() as cur:
            for item in items:
                cur.execute(
                    "UPDATE tasks SET position = ?, updated_at = ? WHERE id = ?",
                    (item["position"], now(), item["id"]),
                )
        return True

    def delete(self, task_id: str) -> bool:
        with db.transaction() as cur:
            cur.execute("DELETE FROM activity_imports WHERE task_id = ?", (task_id,))
            cur.execute("DELETE FROM task_history WHERE task_id = ?", (task_id,))
            cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cur.rowcount > 0

    def _log_history(self, cur, task_id: str, old: dict, new_data: dict):
        ts = now()
        for key, new_val in new_data.items():
            if new_val is None:
                continue
            old_val = old.get(key)
            if old_val is not None:
                old_str = str(old_val)
            else:
                old_str = ""
            new_str = str(new_val)
            if old_str != new_str:
                cur.execute(
                    "INSERT INTO task_history (id, task_id, field_name, old_value, new_value, changed_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (new_id(), task_id, key, old_str[:500], new_str[:500],
                     "user", ts),
                )

    # ── Vigent activities ─────────────────────────────────────────────────

    def list_vigent(self, due_date_after: str | None = None) -> list[dict]:
        from datetime import datetime, timezone
        board = db.execute(
            "SELECT id FROM boards WHERE name = ?", ("Atividades Vigentes",)
        ).fetchone()
        if not board:
            return []

        query = """
            SELECT t.*, ai.source_course_name, ai.source_activity_id
            FROM tasks t
            LEFT JOIN activity_imports ai ON ai.task_id = t.id
            WHERE t.board_id = ?
              AND t.archived = 0
              AND t.due_date IS NOT NULL
        """
        params = [board["id"]]
        if due_date_after:
            query += " AND t.due_date >= ?"
            params.append(due_date_after)
        query += " ORDER BY t.due_date ASC, t.created_at DESC"
        rows = db.execute(query, params).fetchall()

        now_dt = datetime.utcnow().replace(tzinfo=None)
        results = []
        for r in rows:
            t = dict(r)
            days = None
            overdue = False
            if t.get("due_date"):
                try:
                    dd = datetime.fromisoformat(
                        str(t["due_date"]).replace("Z", "+00:00")
                    )
                    if dd.tzinfo:
                        dd = dd.replace(tzinfo=None)
                    delta = (dd - now_dt).days
                    days = delta if delta >= 0 else delta
                    overdue = delta < 0
                except (ValueError, TypeError):
                    pass
            t["days_until_due"] = days
            t["is_overdue"] = overdue
            results.append(t)
        return results


task_service = TaskService()
