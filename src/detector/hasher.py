"""
Sistema de hashing de conteúdo para detecção determinística de mudanças.
SHA-256 do conteúdo normalizado, não de metadados voláteis.
"""

import hashlib
import logging
import re
from datetime import datetime
from typing import Optional

from src.scraper.models import ActivityData, MoodleFile

logger = logging.getLogger("moodle_monitor.detector.hasher")


class ContentHasher:
    """Gera hashes SHA-256 de conteúdo de atividade para comparação."""

    @staticmethod
    def compute_full_hash(activity: ActivityData) -> str:
        hasher = hashlib.sha256()

        hasher.update(ContentHasher._normalize_text(activity.name).encode("utf-8"))
        hasher.update(b"|")

        if activity.description:
            normalized_desc = ContentHasher._normalize_html(activity.description)
            hasher.update(normalized_desc.encode("utf-8"))
        hasher.update(b"|")

        hasher.update(ContentHasher._date_str(activity.due_date).encode("utf-8"))
        hasher.update(b"|")
        hasher.update(ContentHasher._date_str(activity.open_date).encode("utf-8"))
        hasher.update(b"|")
        hasher.update(ContentHasher._date_str(activity.cutoff_date).encode("utf-8"))
        hasher.update(b"|")

        grade = str(activity.max_grade or "") if activity.max_grade is not None else ""
        hasher.update(grade.encode("utf-8"))
        hasher.update(b"|")

        files_hash = ContentHasher.compute_files_hash(activity.files)
        hasher.update(files_hash.encode("utf-8"))

        return hasher.hexdigest()

    @staticmethod
    def compute_description_hash(description: Optional[str]) -> Optional[str]:
        if not description:
            return None
        normalized = ContentHasher._normalize_html(description)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_files_hash(files: list[MoodleFile]) -> str:
        if not files:
            return hashlib.sha256(b"empty").hexdigest()

        file_hashes = []
        for f in sorted(files, key=lambda x: x.filename or ""):
            fh = hashlib.sha256()
            fh.update((f.filename or "").encode("utf-8"))
            fh.update(b"|")
            fh.update(str(f.file_size or "").encode("utf-8"))
            fh.update(b"|")
            fh.update((f.file_url or "").encode("utf-8"))
            file_hashes.append(fh.hexdigest())

        final = hashlib.sha256()
        for fh in sorted(file_hashes):
            final.update(fh.encode("utf-8"))
            final.update(b"|")

        return final.hexdigest()

    @staticmethod
    def compute_file_hash(filename: str, file_size: Optional[int] = None) -> str:
        h = hashlib.sha256()
        h.update((filename or "").encode("utf-8"))
        h.update(b"|")
        h.update(str(file_size or "").encode("utf-8"))
        return h.hexdigest()

    @staticmethod
    def _normalize_text(text: str) -> str:
        if not text:
            return ""
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        text = text.lower()
        return text

    @staticmethod
    def _normalize_html(html: str) -> str:
        if not html:
            return ""
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"data-[a-zA-Z_-]+=\"[^\"]*\"", "", text)
        text = re.sub(r"\s+", " ", text)
        text = text.strip()
        text = text.lower()
        return text

    @staticmethod
    def _date_str(dt: Optional[datetime]) -> str:
        if dt is None:
            return ""
        return dt.strftime("%Y-%m-%d %H:%M")
