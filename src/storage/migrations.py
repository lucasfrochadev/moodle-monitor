"""
Migrações de schema do banco SQLite.
Cada migração é uma função que recebe a conexão e aplica as mudanças.
O schema version é armazenado na tabela `_schema_version`.
"""

import logging
from typing import Optional

logger = logging.getLogger("moodle_monitor.storage.migrations")

_MIGRATIONS: list[tuple[int, str, str]] = []


def migration(version: int, description: str):
    def decorator(func):
        _MIGRATIONS.append((version, description, func.__name__))
        return func
    return decorator


def run_migrations(conn) -> None:
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    current = cursor.execute(
        "SELECT MAX(version) FROM _schema_version"
    ).fetchone()[0] or 0

    applied = 0
    for version, description, func_name in sorted(_MIGRATIONS, key=lambda x: x[0]):
        if version > current:
            logger.info(
                "Aplicando migração %d: %s",
                version, description,
                extra={"version": version, "description": description},
            )
            try:
                func = globals()[func_name]
                func(conn)
                cursor.execute(
                    "INSERT INTO _schema_version (version) VALUES (?)",
                    (version,),
                )
                conn.commit()
                applied += 1
            except Exception as e:
                conn.rollback()
                logger.critical(
                    "Falha na migração %d: %s",
                    version, e,
                    extra={"version": version, "error": str(e)},
                )
                raise

    if applied > 0:
        logger.info("%d migração(ões) aplicada(s)", applied)
    else:
        logger.debug("Schema já está atualizado (versão %d)", current)


@migration(1, "Tabelas iniciais: cursos, seções, atividades, snapshots")
def migration_001(conn) -> None:
    conn.executescript("""
        CREATE TABLE courses (
            id TEXT PRIMARY KEY,
            moodle_course_id INTEGER NOT NULL UNIQUE,
            fullname TEXT NOT NULL,
            shortname TEXT NOT NULL,
            summary TEXT,
            category TEXT,
            is_active INTEGER DEFAULT 1,
            last_check_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE course_sections (
            id TEXT PRIMARY KEY,
            course_id TEXT NOT NULL REFERENCES courses(id),
            moodle_section_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            position INTEGER NOT NULL,
            UNIQUE(course_id, moodle_section_id)
        );

        CREATE TABLE activities (
            id TEXT PRIMARY KEY,
            course_id TEXT NOT NULL REFERENCES courses(id),
            section_id TEXT REFERENCES course_sections(id),
            moodle_cmid INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            moodle_instance_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            url TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(course_id, moodle_cmid)
        );

        CREATE TABLE activity_snapshots (
            id TEXT PRIMARY KEY,
            activity_id TEXT NOT NULL REFERENCES activities(id),
            version INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            description_hash TEXT,
            due_date TIMESTAMP,
            open_date TIMESTAMP,
            cutoff_date TIMESTAMP,
            max_grade REAL,
            files_hash TEXT,
            full_hash TEXT NOT NULL,
            taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(activity_id, version)
        );

        CREATE TABLE activity_files (
            id TEXT PRIMARY KEY,
            activity_id TEXT NOT NULL REFERENCES activities(id),
            snapshot_id TEXT REFERENCES activity_snapshots(id),
            filename TEXT NOT NULL,
            file_url TEXT NOT NULL,
            file_size INTEGER,
            file_hash TEXT,
            mimetype TEXT,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE detected_changes (
            id TEXT PRIMARY KEY,
            activity_id TEXT NOT NULL REFERENCES activities(id),
            change_type TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            diff TEXT,
            snapshot_from_id TEXT REFERENCES activity_snapshots(id),
            snapshot_to_id TEXT REFERENCES activity_snapshots(id),
            severity TEXT DEFAULT 'info',
            notified INTEGER DEFAULT 0,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE notification_log (
            id TEXT PRIMARY KEY,
            change_id TEXT NOT NULL REFERENCES detected_changes(id),
            channel TEXT NOT NULL,
            delivered INTEGER DEFAULT 0,
            error TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE monitor_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)


@migration(2, "Índices para performance")
def migration_002(conn) -> None:
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_activities_course
            ON activities(course_id, is_active);
        CREATE INDEX IF NOT EXISTS idx_activities_cmid
            ON activities(course_id, moodle_cmid);
        CREATE INDEX IF NOT EXISTS idx_snapshots_activity_version
            ON activity_snapshots(activity_id, version DESC);
        CREATE INDEX IF NOT EXISTS idx_snapshots_taken_at
            ON activity_snapshots(taken_at);
        CREATE INDEX IF NOT EXISTS idx_changes_notified
            ON detected_changes(notified, detected_at);
        CREATE INDEX IF NOT EXISTS idx_changes_detected_at
            ON detected_changes(detected_at);
        CREATE INDEX IF NOT EXISTS idx_changes_activity
            ON detected_changes(activity_id, detected_at DESC);
        CREATE INDEX IF NOT EXISTS idx_notification_log_change
            ON notification_log(change_id);
        CREATE INDEX IF NOT EXISTS idx_files_activity
            ON activity_files(activity_id);
        CREATE INDEX IF NOT EXISTS idx_courses_active
            ON courses(is_active);
    """)


@migration(3, "Campo de erro para atividades degradadas")
def migration_003(conn) -> None:
    conn.executescript("""
        ALTER TABLE activities ADD COLUMN last_error TEXT;
        ALTER TABLE activities ADD COLUMN consecutive_failures INTEGER DEFAULT 0;
        ALTER TABLE courses ADD COLUMN consecutive_failures INTEGER DEFAULT 0;
    """)


def get_current_version(conn) -> int:
    cursor = conn.execute("SELECT MAX(version) FROM _schema_version")
    return cursor.fetchone()[0] or 0
