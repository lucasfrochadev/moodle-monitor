"""
Filtro de falsos positivos.
Evita notificações para mudanças triviais ou redundantes.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from src.detector.comparator import ChangeType, DetectedChange

logger = logging.getLogger("moodle_monitor.detector.filter")


class FalsePositiveFilter:
    """Filtra mudanças para evitar notificações irrelevantes ou duplicadas."""

    def __init__(
        self,
        cooldown_minutes: int = 30,
        min_diff_chars: int = 3,
    ):
        self._cooldown = timedelta(minutes=cooldown_minutes)
        self._min_diff_chars = min_diff_chars
        self._recent_notifications: dict[str, datetime] = {}

    def filter_changes(
        self,
        changes: list[DetectedChange],
        last_notified_at: Optional[dict[str, datetime]] = None,
    ) -> list[DetectedChange]:
        if not changes:
            return []

        filtered: list[DetectedChange] = []

        for change in changes:
            if self._is_trivial_change(change):
                logger.debug(
                    "Filtrado: mudança trivial",
                    extra={"type": change.change_type, "activity": change.activity_id},
                )
                continue

            if self._is_on_cooldown(change, last_notified_at):
                logger.debug(
                    "Filtrado: em cooldown",
                    extra={"type": change.change_type, "activity": change.activity_id},
                )
                continue

            filtered.append(change)

        return filtered

    def _is_trivial_change(self, change: DetectedChange) -> bool:
        if change.change_type == ChangeType.DESCRIPTION_CHANGE:
            if change.diff and len(change.diff) < self._min_diff_chars:
                return True

        if change.change_type in (ChangeType.FILE_ADDED, ChangeType.FILE_REMOVED):
            if not change.new_value and not change.old_value:
                return True

        return False

    def _is_on_cooldown(
        self,
        change: DetectedChange,
        last_notified: Optional[dict[str, datetime]] = None,
    ) -> bool:
        if not last_notified:
            return False

        key = f"{change.activity_id}:{change.change_type}"
        last_time = last_notified.get(key)

        if last_time and (datetime.now() - last_time) < self._cooldown:
            return True

        return False

    def register_notification(self, change: DetectedChange) -> None:
        key = f"{change.activity_id}:{change.change_type}"
        self._recent_notifications[key] = datetime.now()
