import sqlite3
import contextlib
from pathlib import Path
from typing import Optional

from api.config import config


class StudyDatabase:
    def __init__(self, db_path: str = ""):
        self._path = db_path or config.study_db_path
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self):
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def close(self):
        if self._conn:
            self._conn.close()

    @contextlib.contextmanager
    def transaction(self):
        if not self._conn:
            raise RuntimeError("Database not connected")
        yield self._conn
        self._conn.commit()

    def execute(self, sql: str, params=()):
        if not self._conn:
            raise RuntimeError("Database not connected")
        return self._conn.execute(sql, params)

    def _migrate(self):
        schema = """
        CREATE TABLE IF NOT EXISTS boards (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            color TEXT DEFAULT '#4A90D9',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS columns (
            id TEXT PRIMARY KEY,
            board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            color TEXT DEFAULT '#E0E0E0',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            column_id TEXT REFERENCES columns(id) ON DELETE SET NULL,
            board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            discipline TEXT DEFAULT '',
            due_date TIMESTAMP,
            publication_date TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'pending',
            priority INTEGER NOT NULL DEFAULT 0,
            position INTEGER NOT NULL DEFAULT 0,
            activity_url TEXT DEFAULT '',
            archived INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS activity_imports (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            source_activity_id TEXT NOT NULL,
            source_course_id INTEGER NOT NULL,
            source_course_name TEXT DEFAULT '',
            source_hash TEXT DEFAULT '',
            last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_activity_id)
        );

        CREATE TABLE IF NOT EXISTS task_history (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            field_name TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_by TEXT DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT DEFAULT '',
            read INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_columns_board ON columns(board_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_board ON tasks(board_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_column ON tasks(column_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
        CREATE INDEX IF NOT EXISTS idx_imports_source ON activity_imports(source_activity_id);
        CREATE INDEX IF NOT EXISTS idx_history_task ON task_history(task_id);
        CREATE INDEX IF NOT EXISTS idx_notifications_read
            ON notifications(read);

        CREATE TABLE IF NOT EXISTS calendar_events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            event_date TEXT NOT NULL,
            event_time TEXT DEFAULT '',
            event_type TEXT NOT NULL DEFAULT 'other',
            description TEXT DEFAULT '',
            color TEXT DEFAULT '#8B5CF6',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        with self.transaction() as cur:
            cur.executescript(schema)


db = StudyDatabase()
