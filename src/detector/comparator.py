"""
Comparador de snapshots de atividades.
Detecta o que mudou entre dois estados de uma atividade.
"""

import difflib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Optional
from uuid import uuid4

from src.detector.hasher import ContentHasher
from src.scraper.models import ActivityData, MoodleFile

logger = logging.getLogger("moodle_monitor.detector.comparator")


class ChangeType(StrEnum):
    NEW_ACTIVITY = "new_activity"
    DESCRIPTION_CHANGE = "description_change"
    DEADLINE_CHANGE = "deadline_change"
    OPEN_DATE_CHANGE = "open_date_change"
    CUTOFF_DATE_CHANGE = "cutoff_date_change"
    FILE_ADDED = "file_added"
    FILE_REMOVED = "file_removed"
    GRADE_CHANGE = "grade_change"
    NAME_CHANGE = "name_change"
    SECTION_CHANGE = "section_change"


class Severity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


_SEVERITY_MAP = {
    ChangeType.NEW_ACTIVITY: Severity.CRITICAL,
    ChangeType.DEADLINE_CHANGE: Severity.CRITICAL,
    ChangeType.DESCRIPTION_CHANGE: Severity.WARNING,
    ChangeType.FILE_ADDED: Severity.WARNING,
    ChangeType.FILE_REMOVED: Severity.INFO,
    ChangeType.GRADE_CHANGE: Severity.INFO,
    ChangeType.NAME_CHANGE: Severity.WARNING,
    ChangeType.OPEN_DATE_CHANGE: Severity.INFO,
    ChangeType.CUTOFF_DATE_CHANGE: Severity.INFO,
    ChangeType.SECTION_CHANGE: Severity.INFO,
}


def _get_severity(change_type: ChangeType) -> Severity:
    return _SEVERITY_MAP.get(change_type, Severity.INFO)


@dataclass
class DetectedChange:
    id: str = ""
    activity_id: str = ""
    change_type: ChangeType = ChangeType.NEW_ACTIVITY
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    diff: Optional[str] = None
    snapshot_from_id: Optional[str] = None
    snapshot_to_id: Optional[str] = None
    severity: Severity = Severity.INFO
    detected_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())
        if self.detected_at is None:
            self.detected_at = datetime.now()
        if self.change_type and self.severity == Severity.INFO:
            self.severity = _get_severity(self.change_type)


class Comparator:
    """Compara snapshots de atividades e detecta mudanças específicas."""

    @staticmethod
    def compare(
        activity_id: str,
        old_activity: Optional[ActivityData],
        new_activity: ActivityData,
        old_snapshot_id: Optional[str] = None,
        new_snapshot_id: Optional[str] = None,
        min_diff_chars: int = 3,
    ) -> list[DetectedChange]:
        if old_activity is None:
            return [DetectedChange(
                activity_id=activity_id,
                change_type=ChangeType.NEW_ACTIVITY,
                new_value=new_activity.name,
                severity=Severity.CRITICAL,
                snapshot_to_id=new_snapshot_id,
            )]

        changes: list[DetectedChange] = []

        name_change = Comparator._compare_field(
            activity_id, old_activity.name, new_activity.name,
            ChangeType.NAME_CHANGE, old_snapshot_id, new_snapshot_id,
        )
        if name_change:
            changes.append(name_change)

        desc_change = Comparator._compare_description(
            activity_id, old_activity.description, new_activity.description,
            old_snapshot_id, new_snapshot_id, min_diff_chars,
        )
        if desc_change:
            changes.append(desc_change)

        date_change = Comparator._compare_date(
            activity_id, "Prazo de entrega",
            old_activity.due_date, new_activity.due_date,
            ChangeType.DEADLINE_CHANGE, old_snapshot_id, new_snapshot_id,
        )
        if date_change:
            changes.append(date_change)

        open_change = Comparator._compare_date(
            activity_id, "Data de abertura",
            old_activity.open_date, new_activity.open_date,
            ChangeType.OPEN_DATE_CHANGE, old_snapshot_id, new_snapshot_id,
        )
        if open_change:
            changes.append(open_change)

        cutoff_change = Comparator._compare_date(
            activity_id, "Data de corte",
            old_activity.cutoff_date, new_activity.cutoff_date,
            ChangeType.CUTOFF_DATE_CHANGE, old_snapshot_id, new_snapshot_id,
        )
        if cutoff_change:
            changes.append(cutoff_change)

        grade_change = Comparator._compare_field(
            activity_id,
            str(old_activity.max_grade) if old_activity.max_grade is not None else "",
            str(new_activity.max_grade) if new_activity.max_grade is not None else "",
            ChangeType.GRADE_CHANGE, old_snapshot_id, new_snapshot_id,
        )
        if grade_change:
            changes.append(grade_change)

        file_changes = Comparator._compare_files(
            activity_id, old_activity.files, new_activity.files,
            old_snapshot_id, new_snapshot_id,
        )
        changes.extend(file_changes)

        return changes

    @staticmethod
    def _compare_field(
        activity_id: str,
        old_val: str,
        new_val: str,
        change_type: ChangeType,
        old_snapshot_id: Optional[str],
        new_snapshot_id: Optional[str],
    ) -> Optional[DetectedChange]:
        if old_val != new_val:
            return DetectedChange(
                activity_id=activity_id,
                change_type=change_type,
                old_value=old_val,
                new_value=new_val,
                severity=_get_severity(change_type),
                snapshot_from_id=old_snapshot_id,
                snapshot_to_id=new_snapshot_id,
            )
        return None

    @staticmethod
    def _compare_description(
        activity_id: str,
        old_desc: Optional[str],
        new_desc: Optional[str],
        old_snapshot_id: Optional[str],
        new_snapshot_id: Optional[str],
        min_diff_chars: int = 3,
    ) -> Optional[DetectedChange]:
        old_hash = ContentHasher.compute_description_hash(old_desc)
        new_hash = ContentHasher.compute_description_hash(new_desc)

        if old_hash == new_hash:
            return None

        if old_desc and new_desc:
            diff = "\n".join(difflib.unified_diff(
                old_desc.splitlines(),
                new_desc.splitlines(),
                fromfile="antigo",
                tofile="novo",
                lineterm="",
            ))

            if len(diff) < min_diff_chars:
                return None

            return DetectedChange(
                activity_id=activity_id,
                change_type=ChangeType.DESCRIPTION_CHANGE,
                old_value=old_desc[:500] if old_desc else "",
                new_value=new_desc[:500] if new_desc else "",
                diff=diff,
                severity=Severity.WARNING,
                snapshot_from_id=old_snapshot_id,
                snapshot_to_id=new_snapshot_id,
            )

        if old_desc is None and new_desc is not None:
            return DetectedChange(
                activity_id=activity_id,
                change_type=ChangeType.DESCRIPTION_CHANGE,
                new_value=new_desc[:500],
                severity=Severity.WARNING,
                snapshot_from_id=old_snapshot_id,
                snapshot_to_id=new_snapshot_id,
            )

        return None

    @staticmethod
    def _compare_date(
        activity_id: str,
        label: str,
        old_date: Optional[datetime],
        new_date: Optional[datetime],
        change_type: ChangeType,
        old_snapshot_id: Optional[str],
        new_snapshot_id: Optional[str],
    ) -> Optional[DetectedChange]:
        old_str = old_date.strftime("%Y-%m-%d %H:%M") if old_date else ""
        new_str = new_date.strftime("%Y-%m-%d %H:%M") if new_date else ""

        if old_str == new_str:
            return None

        return DetectedChange(
            activity_id=activity_id,
            change_type=change_type,
            old_value=old_str,
            new_value=new_str,
            severity=_get_severity(change_type),
            snapshot_from_id=old_snapshot_id,
            snapshot_to_id=new_snapshot_id,
        )

    @staticmethod
    def _compare_files(
        activity_id: str,
        old_files: list[MoodleFile],
        new_files: list[MoodleFile],
        old_snapshot_id: Optional[str],
        new_snapshot_id: Optional[str],
    ) -> list[DetectedChange]:
        changes: list[DetectedChange] = []

        old_file_map = {}
        for f in old_files:
            key = ContentHasher.compute_file_hash(f.filename or "", f.file_size)
            old_file_map[key] = f

        new_file_map = {}
        for f in new_files:
            key = ContentHasher.compute_file_hash(f.filename or "", f.file_size)
            new_file_map[key] = f

        for key, new_file in new_file_map.items():
            if key not in old_file_map:
                changes.append(DetectedChange(
                    activity_id=activity_id,
                    change_type=ChangeType.FILE_ADDED,
                    new_value=f"{new_file.filename} ({new_file.file_size or '?'} bytes)",
                    severity=Severity.WARNING,
                    snapshot_from_id=old_snapshot_id,
                    snapshot_to_id=new_snapshot_id,
                ))

        for key, old_file in old_file_map.items():
            if key not in new_file_map:
                changes.append(DetectedChange(
                    activity_id=activity_id,
                    change_type=ChangeType.FILE_REMOVED,
                    old_value=f"{old_file.filename}",
                    severity=Severity.INFO,
                    snapshot_from_id=old_snapshot_id,
                    snapshot_to_id=new_snapshot_id,
                ))

        return changes
