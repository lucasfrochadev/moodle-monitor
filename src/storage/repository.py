"""
Repositórios (padrão Repository) para acesso a dados.
Cada entidade tem seu próprio repositório com métodos CRUD + queries específicas.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from src.detector.comparator import ChangeType, DetectedChange, Severity
from src.scraper.models import ActivityData, CourseData, MoodleFile, SectionData
from src.storage.database import Database

logger = logging.getLogger("moodle_monitor.storage.repository")


class CourseRepository:
    def __init__(self, db: Database):
        self._db = db

    def upsert(self, course: CourseData) -> str:
        cid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"course:{course.course_id}"))
        with self._db.transaction() as cur:
            cur.execute("""
                INSERT INTO courses (id, moodle_course_id, fullname, shortname, summary, category, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(moodle_course_id) DO UPDATE SET
                    fullname = excluded.fullname,
                    shortname = excluded.shortname,
                    summary = excluded.summary,
                    category = excluded.category,
                    updated_at = CURRENT_TIMESTAMP
            """, (cid, course.course_id, course.fullname, course.shortname,
                  course.summary, course.category))
        return cid

    def get_by_id(self, course_id: str) -> Optional[dict]:
        with self._db.transaction() as cur:
            cur.execute(
                "SELECT * FROM courses WHERE id = ?",
                (course_id,),
            )
            return cur.fetchone()

    def get_by_moodle_id(self, moodle_course_id: int) -> Optional[dict]:
        with self._db.transaction() as cur:
            cur.execute(
                "SELECT * FROM courses WHERE moodle_course_id = ?",
                (moodle_course_id,),
            )
            return cur.fetchone()

    def get_all_active(self) -> list[dict]:
        with self._db.transaction() as cur:
            cur.execute(
                "SELECT * FROM courses WHERE is_active = 1 ORDER BY fullname"
            )
            return cur.fetchall()

    def mark_inactive(self, course_id: str) -> None:
        with self._db.transaction() as cur:
            cur.execute(
                "UPDATE courses SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (course_id,),
            )

    def update_check_time(self, course_id: str) -> None:
        with self._db.transaction() as cur:
            cur.execute(
                "UPDATE courses SET last_check_at = CURRENT_TIMESTAMP WHERE id = ?",
                (course_id,),
            )

    def increment_failures(self, course_id: str) -> int:
        with self._db.transaction() as cur:
            cur.execute("""
                UPDATE courses SET consecutive_failures = consecutive_failures + 1
                WHERE id = ?
            """, (course_id,))
            cur.execute("SELECT consecutive_failures FROM courses WHERE id = ?", (course_id,))
            row = cur.fetchone()
            return row["consecutive_failures"] if row else 0

    def reset_failures(self, course_id: str) -> None:
        with self._db.transaction() as cur:
            cur.execute(
                "UPDATE courses SET consecutive_failures = 0 WHERE id = ?",
                (course_id,),
            )


class SectionRepository:
    def __init__(self, db: Database):
        self._db = db

    def upsert(self, course_id: str, section: SectionData) -> str:
        sid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"section:{course_id}:{section.section_id}"))
        with self._db.transaction() as cur:
            cur.execute("""
                INSERT INTO course_sections (id, course_id, moodle_section_id, name, position)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(course_id, moodle_section_id) DO UPDATE SET
                    name = excluded.name,
                    position = excluded.position
            """, (sid, course_id, section.section_id, section.name, section.position))
        return sid


class ActivityRepository:
    def __init__(self, db: Database):
        self._db = db

    def upsert(self, course_id: str, section_id: Optional[str], activity: ActivityData) -> str:
        aid = str(uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"activity:{course_id}:{activity.cmid}",
        ))
        with self._db.transaction() as cur:
            cur.execute("""
                INSERT INTO activities (id, course_id, section_id, moodle_cmid, activity_type,
                    moodle_instance_id, name, description, url, last_checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(course_id, moodle_cmid) DO UPDATE SET
                    section_id = excluded.section_id,
                    activity_type = excluded.activity_type,
                    moodle_instance_id = excluded.moodle_instance_id,
                    name = excluded.name,
                    description = excluded.description,
                    url = excluded.url,
                    is_active = 1,
                    last_checked_at = CURRENT_TIMESTAMP
            """, (aid, course_id, section_id, activity.cmid, activity.type.value,
                  activity.instance_id, activity.name, activity.description, activity.url))
        return aid

    def get_by_cmid(self, course_id: str, cmid: int) -> Optional[dict]:
        with self._db.transaction() as cur:
            cur.execute(
                "SELECT * FROM activities WHERE course_id = ? AND moodle_cmid = ?",
                (course_id, cmid),
            )
            return cur.fetchone()

    def get_by_course(self, course_id: str) -> list[dict]:
        with self._db.transaction() as cur:
            cur.execute(
                "SELECT * FROM activities WHERE course_id = ? AND is_active = 1",
                (course_id,),
            )
            return cur.fetchall()

    def mark_inactive(self, activity_ids: list[str]) -> None:
        if not activity_ids:
            return
        with self._db.transaction() as cur:
            placeholders = ",".join("?" for _ in activity_ids)
            cur.execute(
                f"UPDATE activities SET is_active = 0 WHERE id IN ({placeholders})",
                activity_ids,
            )

    def get_by_id(self, activity_id: str) -> Optional[dict]:
        with self._db.transaction() as cur:
            cur.execute(
                "SELECT * FROM activities WHERE id = ?",
                (activity_id,),
            )
            return cur.fetchone()

    def get_last_snapshot(self, activity_id: str) -> Optional[dict]:
        with self._db.transaction() as cur:
            cur.execute("""
                SELECT * FROM activity_snapshots
                WHERE activity_id = ?
                ORDER BY version DESC LIMIT 1
            """, (activity_id,))
            return cur.fetchone()

    def get_snapshot_by_id(self, snapshot_id: str) -> Optional[dict]:
        with self._db.transaction() as cur:
            cur.execute(
                "SELECT * FROM activity_snapshots WHERE id = ?",
                (snapshot_id,),
            )
            return cur.fetchone()


class SnapshotRepository:
    def __init__(self, db: Database):
        self._db = db

    def create(
        self,
        activity_id: str,
        activity: ActivityData,
        full_hash: str,
        files_hash: str,
        version: int,
    ) -> str:
        sid = str(uuid.uuid4())
        desc_hash = self._compute_desc_hash(activity.description)

        prev = self.get_latest_by_activity(activity_id)
        due_date = activity.due_date or (prev["due_date"] if prev else None)
        open_date = activity.open_date or (prev["open_date"] if prev else None)
        cutoff_date = activity.cutoff_date or (prev["cutoff_date"] if prev else None)

        with self._db.transaction() as cur:
            cur.execute("""
                INSERT INTO activity_snapshots
                    (id, activity_id, version, name, description, description_hash,
                     due_date, open_date, cutoff_date, max_grade, files_hash, full_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sid, activity_id, version, activity.name, activity.description,
                desc_hash,
                due_date, open_date, cutoff_date,
                activity.max_grade, files_hash, full_hash,
            ))
        return sid

    def get_latest_by_activity(self, activity_id: str) -> Optional[dict]:
        with self._db.transaction() as cur:
            cur.execute("""
                SELECT * FROM activity_snapshots
                WHERE activity_id = ?
                ORDER BY version DESC LIMIT 1
            """, (activity_id,))
            return cur.fetchone()

    def _compute_desc_hash(self, desc: Optional[str]) -> Optional[str]:
        if not desc:
            return None
        import hashlib
        import re
        text = re.sub(r"<[^>]+>", " ", desc)
        text = re.sub(r"\s+", " ", text).strip().lower()
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def delete_old(self, retention_days: int) -> int:
        cutoff = datetime.now() - timedelta(days=retention_days)
        with self._db.transaction() as cur:
            cur.execute(
                "DELETE FROM activity_snapshots WHERE taken_at < ?",
                (cutoff,),
            )
            return cur.rowcount


class FileRepository:
    def __init__(self, db: Database):
        self._db = db

    def upsert(self, activity_id: str, snapshot_id: Optional[str], file: MoodleFile) -> str:
        fid = str(uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"file:{activity_id}:{file.filename}:{file.file_size}",
        ))
        with self._db.transaction() as cur:
            cur.execute("""
                INSERT INTO activity_files (id, activity_id, snapshot_id, filename, file_url,
                    file_size, file_hash, mimetype)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
            """, (fid, activity_id, snapshot_id, file.filename, file.file_url,
                  file.file_size, file.file_hash, file.mimetype))
        return fid

    def get_by_activity(self, activity_id: str) -> list[dict]:
        with self._db.transaction() as cur:
            cur.execute(
                "SELECT * FROM activity_files WHERE activity_id = ?",
                (activity_id,),
            )
            return cur.fetchall()


class ChangeRepository:
    def __init__(self, db: Database):
        self._db = db

    def create(self, change: DetectedChange) -> str:
        with self._db.transaction() as cur:
            cur.execute("""
                INSERT INTO detected_changes
                    (id, activity_id, change_type, old_value, new_value, diff,
                     snapshot_from_id, snapshot_to_id, severity, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                change.id, change.activity_id, change.change_type.value,
                change.old_value, change.new_value, change.diff,
                change.snapshot_from_id, change.snapshot_to_id,
                change.severity.value, change.detected_at,
            ))
        return change.id

    def mark_notified(self, change_id: str) -> None:
        with self._db.transaction() as cur:
            cur.execute(
                "UPDATE detected_changes SET notified = 1 WHERE id = ?",
                (change_id,),
            )

    def get_unnotified(self, limit: int = 100) -> list[dict]:
        with self._db.transaction() as cur:
            cur.execute("""
                SELECT * FROM detected_changes
                WHERE notified = 0
                ORDER BY detected_at ASC
                LIMIT ?
            """, (limit,))
            return cur.fetchall()

    def get_by_activity(self, activity_id: str, limit: int = 50) -> list[dict]:
        with self._db.transaction() as cur:
            cur.execute("""
                SELECT * FROM detected_changes
                WHERE activity_id = ?
                ORDER BY detected_at DESC
                LIMIT ?
            """, (activity_id, limit))
            return cur.fetchall()

    def delete_old(self, retention_days: int) -> int:
        cutoff = datetime.now() - timedelta(days=retention_days)
        with self._db.transaction() as cur:
            cur.execute(
                "DELETE FROM detected_changes WHERE detected_at < ?",
                (cutoff,),
            )
            return cur.rowcount


class NotificationLogRepository:
    def __init__(self, db: Database):
        self._db = db

    def log(self, change_id: str, channel: str, delivered: bool, error: Optional[str] = None) -> str:
        nid = str(uuid.uuid4())
        with self._db.transaction() as cur:
            cur.execute("""
                INSERT INTO notification_log (id, change_id, channel, delivered, error)
                VALUES (?, ?, ?, ?, ?)
            """, (nid, change_id, channel, 1 if delivered else 0, error))
        return nid

    def get_last_notified_per_type(self) -> dict[str, datetime]:
        result = {}
        with self._db.transaction() as cur:
            cur.execute("""
                SELECT dc.activity_id, dc.change_type, MAX(nl.sent_at) as last_sent
                FROM notification_log nl
                JOIN detected_changes dc ON nl.change_id = dc.id
                WHERE nl.delivered = 1
                GROUP BY dc.activity_id, dc.change_type
            """)
            for row in cur.fetchall():
                key = f"{row['activity_id']}:{row['change_type']}"
                result[key] = datetime.fromisoformat(row["last_sent"])
        return result


class MonitorStateRepository:
    def __init__(self, db: Database):
        self._db = db

    def set(self, key: str, value: str) -> None:
        with self._db.transaction() as cur:
            cur.execute("""
                INSERT INTO monitor_state (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """, (key, value))

    def get(self, key: str) -> Optional[str]:
        with self._db.transaction() as cur:
            cur.execute("SELECT value FROM monitor_state WHERE key = ?", (key,))
            row = cur.fetchone()
            return row["value"] if row else None
