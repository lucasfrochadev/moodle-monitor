"""
Conexão e operações de baixo nível com SQLite.
Gerencia pool de conexões, WAL mode, transações e integridade.
"""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from src.storage.migrations import run_migrations

logger = logging.getLogger("moodle_monitor.storage.database")


class DatabaseError(Exception):
    """Erro geral de banco de dados."""


class Database:
    """Gerenciador de conexão SQLite com suporte a WAL e transações."""

    def __init__(self, db_path: str):
        self._db_path = Path(db_path)
        self._ensure_dir()
        self._conn: Optional[sqlite3.Connection] = None

    def _ensure_dir(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> None:
        self._conn = sqlite3.connect(
            str(self._db_path),
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA cache_size=-8000")
        self._conn.execute("PRAGMA temp_store=MEMORY")
        logger.info("Banco de dados conectado", extra={"path": str(self._db_path)})

    def initialize(self) -> None:
        if not self._conn:
            self.connect()
        run_migrations(self._conn)

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise DatabaseError("Banco de dados não conectado")
        return self._conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        if self._conn is None:
            raise DatabaseError("Banco de dados não conectado")
        cursor = self._conn.cursor()
        try:
            yield cursor
            self._conn.commit()
        except Exception:
            try:
                self._conn.rollback()
            except Exception:
                pass
            raise
        finally:
            cursor.close()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Banco de dados desconectado")

    def get_size(self) -> int:
        return self._db_path.stat().st_size if self._db_path.exists() else 0

    def vacuum(self) -> None:
        if self._conn:
            self._conn.execute("VACUUM")
            logger.info("VACUUM concluído")

    def backup(self, backup_path: str) -> None:
        import shutil
        if self._db_path.exists():
            Path(backup_path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(self._db_path), backup_path)
            logger.info("Backup realizado", extra={"path": backup_path})

    def check_integrity(self) -> bool:
        try:
            result = self.conn.execute("PRAGMA integrity_check").fetchone()
            ok = result[0] == "ok"
            if not ok:
                logger.error("Integridade do banco comprometida", extra={"result": result[0]})
            return ok
        except Exception as e:
            logger.error("Erro ao verificar integridade", extra={"error": str(e)})
            return False


from typing import Optional
