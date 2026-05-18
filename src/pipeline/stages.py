"""
Estágios individuais do pipeline de processamento.
Cada estágio é uma etapa isolada e testável.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import structlog

from src.detector.comparator import ChangeType, Comparator, DetectedChange
from src.detector.filter import FalsePositiveFilter
from src.detector.hasher import ContentHasher
from src.scraper.extractor import Extractor
from src.scraper.models import ActivityData, CourseData, SectionData
from src.storage.repository import (
    ActivityRepository,
    ChangeRepository,
    CourseRepository,
    FileRepository,
    NotificationLogRepository,
    SectionRepository,
    SnapshotRepository,
)

logger = logging.getLogger("moodle_monitor.pipeline.stages")


@dataclass
class StageContext:
    """Contexto compartilhado entre estágios do pipeline."""
    courses: list[CourseData] = field(default_factory=list)
    sections_by_course: dict[str, list[SectionData]] = field(default_factory=dict)
    activities_by_course: dict[str, list[ActivityData]] = field(default_factory=dict)
    snapshots_created: dict[str, str] = field(default_factory=dict)
    changes_detected: list[DetectedChange] = field(default_factory=list)


class CourseScanStage:
    """Estágio 1: Escaneia todos os cursos do usuário."""

    def __init__(
        self,
        extractor: Extractor,
        course_repo: CourseRepository,
        course_ids: list[int] | None = None,
    ):
        self._extractor = extractor
        self._course_repo = course_repo
        self._course_ids = course_ids or []

    async def execute(self, ctx: StageContext) -> StageContext:
        logger.info("Estágio 1: Escaneando cursos")
        courses = await asyncio.to_thread(self._extractor.extract_courses)

        if self._course_ids:
            courses = [c for c in courses if c.course_id in self._course_ids]
            logger.info(
                "Filtrando para %d cursos configurados (de %d encontrados)",
                len(courses), len(self._course_ids),
            )

        for course in courses:
            db_id = await asyncio.to_thread(self._course_repo.upsert, course)
            logger.debug("Curso processado", extra={
                "course_id": course.course_id,
                "name": course.fullname,
                "db_id": db_id,
            })

        ctx.courses = courses
        logger.info("Cursos encontrados: %d", len(courses))
        return ctx


class SectionScanStage:
    """Estágio 2: Escaneia seções e atividades de cada curso."""

    def __init__(
        self,
        extractor: Extractor,
        course_repo: CourseRepository,
        section_repo: SectionRepository,
        activity_repo: ActivityRepository,
        max_concurrent: int = 5,
        include_types: set[str] | None = None,
    ):
        self._extractor = extractor
        self._course_repo = course_repo
        self._section_repo = section_repo
        self._activity_repo = activity_repo
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._include_types = include_types

    async def execute(self, ctx: StageContext) -> StageContext:
        logger.info("Estágio 2: Escaneando seções e atividades")

        async def process_course(course: CourseData):
            async with self._semaphore:
                return await self._process_single_course(course, ctx)

        tasks = [process_course(c) for c in ctx.courses]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Erro ao processar curso %s: %s",
                    ctx.courses[i].course_id, result,
                )
                await asyncio.to_thread(
                    self._course_repo.increment_failures,
                    str(ctx.courses[i].course_id),
                )
            elif result:
                cid, sections, activities = result
                ctx.sections_by_course[cid] = sections
                ctx.activities_by_course[cid] = activities
                await asyncio.to_thread(self._course_repo.reset_failures, cid)

        return ctx

    async def _process_single_course(
        self, course: CourseData, ctx: StageContext,
    ) -> Optional[tuple[str, list[SectionData], list[ActivityData]]]:
        course_db_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"course:{course.course_id}"))

        sections = await asyncio.to_thread(
            self._extractor.extract_course_contents, course,
        )

        all_activities = []
        for section in sections:
            section_db_id = None
            if section.section_id:
                section_db_id = str(uuid.uuid5(
                    uuid.NAMESPACE_DNS,
                    f"section:{course_db_id}:{section.section_id}",
                ))
                await asyncio.to_thread(
                    self._section_repo.upsert, course_db_id, section,
                )

            for activity in section.activities:
                if self._include_types is not None and activity.type.value not in self._include_types:
                    continue
                activity_db_id = await asyncio.to_thread(
                    self._activity_repo.upsert, course_db_id, section_db_id, activity,
                )
                all_activities.append(activity)

        return course_db_id, sections, all_activities


class ActivityDetailStage:
    """Estágio 3: Enriquece atividades com detalhes (descrição, arquivos, datas)."""

    def __init__(self, extractor: Extractor, max_concurrent: int = 10):
        self._extractor = extractor
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute(self, ctx: StageContext) -> StageContext:
        logger.info("Estágio 3: Extraindo detalhes das atividades")

        all_activities = []
        for activities in ctx.activities_by_course.values():
            all_activities.extend(activities)

        async def enrich(activity: ActivityData) -> ActivityData:
            async with self._semaphore:
                detailed = await asyncio.to_thread(
                    self._extractor.extract_activity_detail, activity,
                )
                return detailed or activity

        tasks = [enrich(a) for a in all_activities]
        enriched = await asyncio.gather(*tasks)

        enriched_idx = 0
        for course_id in ctx.activities_by_course:
            for i in range(len(ctx.activities_by_course[course_id])):
                if enriched_idx < len(enriched):
                    ctx.activities_by_course[course_id][i] = enriched[enriched_idx]
                    enriched_idx += 1

        return ctx


class SnapshotStage:
    """Estágio 4: Gera snapshots e hashes das atividades."""

    def __init__(
        self,
        activity_repo: ActivityRepository,
        snapshot_repo: SnapshotRepository,
        file_repo: FileRepository,
    ):
        self._activity_repo = activity_repo
        self._snapshot_repo = snapshot_repo
        self._file_repo = file_repo

    async def execute(self, ctx: StageContext) -> StageContext:
        logger.info("Estágio 4: Gerando snapshots")

        for course_id, activities in ctx.activities_by_course.items():
            for activity in activities:
                db_activity = await asyncio.to_thread(
                    self._activity_repo.get_by_cmid, course_id, activity.cmid,
                )
                if not db_activity:
                    continue

                activity_id = db_activity["id"]
                last_snapshot = await asyncio.to_thread(
                    self._snapshot_repo.get_latest_by_activity, activity_id,
                )

                version = (last_snapshot["version"] + 1) if last_snapshot else 1
                full_hash = ContentHasher.compute_full_hash(activity)
                files_hash = ContentHasher.compute_files_hash(activity.files)

                snapshot_id = await asyncio.to_thread(
                    self._snapshot_repo.create,
                    activity_id, activity, full_hash, files_hash, version,
                )

                ctx.snapshots_created[activity_id] = snapshot_id

                for file in activity.files:
                    await asyncio.to_thread(
                        self._file_repo.upsert, activity_id, snapshot_id, file,
                    )

        return ctx


class CompareStage:
    """Estágio 5: Compara snapshots e detecta mudanças."""

    def __init__(
        self,
        activity_repo: ActivityRepository,
        change_repo: ChangeRepository,
        snapshot_repo: SnapshotRepository,
        filter_instance: FalsePositiveFilter,
        notif_log_repo: NotificationLogRepository,
        min_diff_chars: int = 3,
    ):
        self._activity_repo = activity_repo
        self._change_repo = change_repo
        self._snapshot_repo = snapshot_repo
        self._filter = filter_instance
        self._notif_log_repo = notif_log_repo
        self._min_diff_chars = min_diff_chars

    async def execute(self, ctx: StageContext) -> StageContext:
        logger.info("Estágio 5: Comparando snapshots")

        last_notified = await asyncio.to_thread(
            self._notif_log_repo.get_last_notified_per_type,
        )

        all_changes: list[DetectedChange] = []

        for course_id, activities in ctx.activities_by_course.items():
            for activity in activities:
                db_activity = await asyncio.to_thread(
                    self._activity_repo.get_by_cmid, course_id, activity.cmid,
                )
                if not db_activity:
                    continue

                activity_id = db_activity["id"]
                new_snapshot_id = ctx.snapshots_created.get(activity_id)

                last_snapshot = await asyncio.to_thread(
                    self._snapshot_repo.get_latest_by_activity, activity_id,
                )
                if not last_snapshot:
                    all_changes.append(DetectedChange(
                        activity_id=activity_id,
                        change_type=ChangeType.NEW_ACTIVITY,
                        new_value=activity.name,
                        snapshot_to_id=new_snapshot_id,
                    ))
                    continue

                snap = dict(last_snapshot) if hasattr(last_snapshot, "keys") else last_snapshot

                # Version == 1 = first snapshot ever → NEW_ACTIVITY
                if snap.get("version", 0) == 1:
                    change = DetectedChange(
                        activity_id=activity_id,
                        change_type=ChangeType.NEW_ACTIVITY,
                        new_value=activity.name,
                        snapshot_to_id=new_snapshot_id,
                    )
                    await asyncio.to_thread(self._change_repo.create, change)
                    all_changes.append(change)
                    continue

                if snap["full_hash"] == ContentHasher.compute_full_hash(activity):
                    continue

                old_activity = self._snapshot_to_activity(last_snapshot)
                if old_activity is None:
                    continue

                changes = Comparator.compare(
                    activity_id=activity_id,
                    old_activity=old_activity,
                    new_activity=activity,
                    old_snapshot_id=snap["id"],
                    new_snapshot_id=new_snapshot_id,
                    min_diff_chars=self._min_diff_chars,
                )

                filtered = self._filter.filter_changes(changes, last_notified)

                for change in filtered:
                    await asyncio.to_thread(self._change_repo.create, change)
                    self._filter.register_notification(change)

                all_changes.extend(filtered)

                if changes:
                    logger.info(
                        "Mudanças detectadas em %s: %d",
                        activity.name, len(changes),
                        extra={
                            "activity_id": activity_id,
                            "activity_name": activity.name,
                            "changes": len(changes),
                            "filtered": len(filtered),
                        },
                    )

        ctx.changes_detected = all_changes
        logger.info("Total de mudanças detectadas: %d", len(all_changes))
        return ctx

    def _snapshot_to_activity(self, snapshot: dict) -> Optional[ActivityData]:
        try:
            snap = dict(snapshot) if hasattr(snapshot, "keys") else snapshot
            files_list = []
            return ActivityData(
                cmid=0,
                instance_id=0,
                name=snap["name"],
                type="unknown",
                url="",
                description=snap.get("description"),
                due_date=snap.get("due_date"),
                open_date=snap.get("open_date"),
                cutoff_date=snap.get("cutoff_date"),
                max_grade=snap.get("max_grade"),
                files=files_list,
                source="snapshot",
            )
        except Exception as e:
            logger.error("Erro ao converter snapshot para activity: %s", e)
            return None


class NotificationStage:
    """Estágio 6: Envia notificações para todos os canais configurados."""

    def __init__(
        self,
        notifiers: list,
        change_repo: ChangeRepository,
        notif_log_repo: NotificationLogRepository,
        activity_repo: ActivityRepository,
        course_repo: CourseRepository,
        notif_config: dict,
    ):
        self._notifiers = notifiers
        self._change_repo = change_repo
        self._notif_log_repo = notif_log_repo
        self._activity_repo = activity_repo
        self._course_repo = course_repo
        self._config = notif_config

    async def execute(self, ctx: StageContext) -> StageContext:
        if not self._notifiers:
            logger.info("Nenhum notificador configurado")
            return ctx

        logger.info(
            "Estágio 6: Enviando notificações (%d mudanças, %d canais)",
            len(ctx.changes_detected), len(self._notifiers),
        )

        for change in ctx.changes_detected:
            if not self._should_notify(change):
                continue

            activity_name = "Desconhecida"
            course_name = "Desconhecida"
            activity_url = ""

            if change.activity_id:
                db_activity = await asyncio.to_thread(
                    self._activity_repo.get_by_id, change.activity_id,
                )
                if db_activity:
                    db_activity = dict(db_activity) if hasattr(db_activity, "keys") else db_activity
                    activity_name = db_activity["name"]
                    activity_url = db_activity.get("url", "")
                    course_id = db_activity.get("course_id")
                    if course_id:
                        course = await asyncio.to_thread(
                            self._course_repo.get_by_id, course_id,
                        )
                        if course:
                            course = dict(course) if hasattr(course, "keys") else course
                            course_name = course.get("fullname") or course.get("shortname") or "Desconhecida"
            else:
                snapshot = await asyncio.to_thread(
                    self._activity_repo.get_snapshot_by_id,
                    change.snapshot_to_id,
                ) if change.snapshot_to_id else None
                if snapshot:
                    snap = dict(snapshot) if hasattr(snapshot, "keys") else snapshot
                    activity_name = snap.get("name", "Desconhecida")
                    activity_url = snap.get("url", "")

            for notifier in self._notifiers:
                try:
                    success = await notifier.send(
                        change, activity_name, course_name, activity_url,
                    )
                    await asyncio.to_thread(
                        self._notif_log_repo.log,
                        change.id, notifier.name, success,
                        None if success else "Failed to send",
                    )
                except Exception as e:
                    logger.error(
                        "Erro no notificador %s: %s",
                        notifier.name, e,
                    )
                    await asyncio.to_thread(
                        self._notif_log_repo.log,
                        change.id, notifier.name, False, str(e),
                    )

            await asyncio.to_thread(self._change_repo.mark_notified, change.id)

        return ctx

    def _should_notify(self, change: DetectedChange) -> bool:
        type_config_map = {
            ChangeType.NEW_ACTIVITY: "on_new_activity",
            ChangeType.DEADLINE_CHANGE: "on_deadline_change",
            ChangeType.DESCRIPTION_CHANGE: "on_description_change",
            ChangeType.FILE_ADDED: "on_file_added",
            ChangeType.FILE_REMOVED: "on_file_removed",
            ChangeType.NAME_CHANGE: "on_name_change",
            ChangeType.GRADE_CHANGE: "on_grade_change",
        }
        config_key = type_config_map.get(change.change_type)
        if config_key:
            return bool(self._config.get(config_key, True))
        return True
