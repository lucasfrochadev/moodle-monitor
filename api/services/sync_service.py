import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from api.database import db
from api.schemas import new_id, now


class SyncService:

    def __init__(self, monitor_db_path: str = ""):
        self._monitor_path = monitor_db_path or ""
        self._board_cache: dict = {}

    def set_monitor_path(self, path: str):
        self._monitor_path = path

    def _connect_monitor(self) -> Optional[sqlite3.Connection]:
        if not self._monitor_path or not Path(self._monitor_path).exists():
            return None
        conn = sqlite3.connect(self._monitor_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_or_create_vigent_board(self) -> str:
        with db.transaction() as cur:
            row = cur.execute(
                "SELECT id FROM boards WHERE name = ?", ("Atividades Vigentes",)
            ).fetchone()
            if row:
                board_id = row["id"]
            else:
                board_id = new_id()
                cur.execute(
                    "INSERT INTO boards (id, name, description, color) VALUES (?, ?, ?, ?)",
                    (board_id, "Atividades Vigentes",
                     "Atividades importadas automaticamente do monitor acadêmico",
                     "#2ECC71"),
                )
            columns = cur.execute(
                "SELECT id, name FROM columns WHERE board_id = ? ORDER BY position",
                (board_id,),
            ).fetchall()
            expected = ["Novas", "Pendentes", "Fazendo", "Concluídas", "Arquivadas"]
            existing = {r["name"]: r["id"] for r in columns}
            names = []
            for pos, name in enumerate(expected):
                if name not in existing:
                    cid = new_id()
                    cur.execute(
                        "INSERT INTO columns (id, board_id, name, position, color) VALUES (?, ?, ?, ?, ?)",
                        (cid, board_id, name, pos, "#E0E0E0"),
                    )
                    names.append(name)
                else:
                    names.append(name)
            all_cols = cur.execute(
                "SELECT id, name FROM columns WHERE board_id = ? ORDER BY position",
                (board_id,),
            ).fetchall()
            self._board_cache[board_id] = {r["name"]: r["id"] for r in all_cols}
            return board_id

    def _status_to_column(self, status: str, vigent_cols: dict) -> str:
        mapping = {
            "nova": "Novas",
            "new": "Novas",
            "pending": "Pendentes",
            "pendente": "Pendentes",
            "in_progress": "Fazendo",
            "em andamento": "Fazendo",
            "completed": "Concluídas",
            "concluída": "Concluídas",
            "concluida": "Concluídas",
            "archived": "Arquivadas",
            "arquivada": "Arquivadas",
        }
        col_name = mapping.get(status.lower(), "Novas")
        return vigent_cols.get(col_name)

    def _calculate_status(self, due_date_str: Optional[str]) -> str:
        if not due_date_str:
            return "pending"
        try:
            due = datetime.fromisoformat(due_date_str)
            if due.tzinfo is None:
                from datetime import timezone
                due = due.replace(tzinfo=timezone.utc)
            now_dt = datetime.utcnow().replace(tzinfo=None)
            if due.tzinfo:
                due_naive = due.replace(tzinfo=None)
            else:
                due_naive = due
            if due_naive < now_dt:
                return "overdue"
        except (ValueError, TypeError):
            pass
        return "pending"

    def sync(self, course_ids: list[int] | None = None) -> dict:
        imported = 0
        updated = 0
        errors = 0

        monitor = self._connect_monitor()
        if not monitor:
            return {"imported": 0, "updated": 0, "errors": 0,
                    "message": "Monitor database not found"}

        vigent_board_id = self._get_or_create_vigent_board()
        vigent_cols = self._board_cache.get(vigent_board_id, {})

        try:
            query = """
                SELECT
                    a.id AS activity_id,
                    a.course_id,
                    a.name AS activity_name,
                    a.first_seen_at,
                    COALESCE(sn.description, '') AS description,
                    sn.due_date,
                    sn.full_hash,
                    c.fullname AS course_name
                FROM activities a
                LEFT JOIN (
                    SELECT activity_id, description, due_date, full_hash
                    FROM activity_snapshots
                    WHERE (activity_id, version) IN (
                        SELECT activity_id, MAX(version)
                        FROM activity_snapshots
                        GROUP BY activity_id
                    )
                ) sn ON sn.activity_id = a.id
                LEFT JOIN courses c ON c.id = a.course_id
            """
            params = []
            if course_ids:
                placeholders = ",".join("?" * len(course_ids))
                query += f" WHERE c.moodle_course_id IN ({placeholders})"
                params = course_ids
            query += " ORDER BY a.course_id, a.name"
            rows = monitor.execute(query, params).fetchall()

            with db.transaction() as cur:
                for row in rows:
                    try:
                        activity_id = str(row["activity_id"])
                        course_id = row["course_id"]
                        course_name = row["course_name"] or ""
                        title = row["activity_name"] or "(sem título)"
                        description = row["description"] or ""
                        first_seen = row["first_seen_at"] or ""
                        due_date_raw = row["due_date"]
                        due_date = None
                        if due_date_raw:
                            try:
                                dt = datetime.fromisoformat(
                                    str(due_date_raw).replace("Z", "+00:00")
                                )
                                due_date = dt.isoformat()
                            except (ValueError, TypeError):
                                due_date = str(due_date_raw)
                        full_hash = row["full_hash"] or ""

                        status = self._calculate_status(due_date)

                        existing = cur.execute(
                            "SELECT id, task_id, source_hash FROM activity_imports WHERE source_activity_id = ?",
                            (activity_id,),
                        ).fetchone()

                        if existing:
                            imp_id, task_id, old_hash = existing["id"], existing["task_id"], existing["source_hash"]
                            if full_hash and full_hash == old_hash:
                                continue
                            task_row = cur.execute(
                                "SELECT id FROM tasks WHERE id = ?", (task_id,)
                            ).fetchone()
                            if not task_row:
                                continue
                            column_id = self._status_to_column(status, vigent_cols)
                            cur.execute("""
                                UPDATE tasks
                                SET title = ?, description = ?, discipline = ?,
                                    due_date = ?, publication_date = ?,
                                    status = ?, updated_at = ?
                                WHERE id = ?
                            """, (title, description, course_name,
                                  due_date, first_seen,
                                  status, now(), task_id))
                            cur.execute("""
                                UPDATE activity_imports
                                SET source_hash = ?, source_course_name = ?,
                                    last_synced_at = ?
                                WHERE id = ?
                            """, (full_hash, course_name, now(), imp_id))
                            updated += 1
                        else:
                            task_id = new_id()
                            column_id = self._status_to_column(status, vigent_cols)
                            if not column_id:
                                column_id = next(
                                    (v for v in vigent_cols.values()),
                                    None
                                )
                            cur.execute("""
                                INSERT INTO tasks
                                    (id, column_id, board_id, title, description,
                                     discipline, due_date, publication_date,
                                     status, position)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (task_id, column_id, vigent_board_id,
                                  title, description, course_name,
                                  due_date, first_seen, status, 0))
                            imp_id = new_id()
                            cur.execute("""
                                INSERT INTO activity_imports
                                    (id, task_id, source_activity_id,
                                     source_course_id, source_course_name,
                                     source_hash, last_synced_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (imp_id, task_id, activity_id,
                                  course_id, course_name,
                                  full_hash, now()))
                            imported += 1
                    except Exception:
                        errors += 1
        finally:
            monitor.close()

        return {
            "imported": imported,
            "updated": updated,
            "errors": errors,
            "message": f"Sync complete: {imported} imported, {updated} updated, {errors} errors",
        }


sync_service = SyncService()
