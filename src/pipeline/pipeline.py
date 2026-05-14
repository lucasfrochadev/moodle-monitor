"""
Orquestrador do pipeline de processamento.
Coordena a execução sequencial dos estágios.
"""

import asyncio
import logging
import time
from typing import Optional

import structlog

from src.pipeline.stages import (
    ActivityDetailStage,
    CompareStage,
    CourseScanStage,
    NotificationStage,
    SectionScanStage,
    SnapshotStage,
    StageContext,
)

logger = logging.getLogger("moodle_monitor.pipeline")


class Pipeline:
    """Orquestrador que executa os estágios do pipeline em sequência."""

    def __init__(self):
        self._stages: list = []
        self._last_duration: Optional[float] = None

    def add_stage(self, stage) -> "Pipeline":
        self._stages.append(stage)
        return self

    async def execute(self, ctx: Optional[StageContext] = None) -> StageContext:
        if ctx is None:
            ctx = StageContext()

        start = time.monotonic()
        logger.info("Pipeline iniciado com %d estágios", len(self._stages))

        for i, stage in enumerate(self._stages):
            stage_start = time.monotonic()
            stage_name = type(stage).__name__

            try:
                ctx = await stage.execute(ctx)
                stage_duration = time.monotonic() - stage_start
                logger.info(
                    "Estágio %d/%d concluído em %.2fs",
                    i + 1, len(self._stages), stage_duration,
                    extra={"stage": stage_name, "duration_s": round(stage_duration, 2)},
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(
                    "Estágio %d/%d falhou: %s",
                    i + 1, len(self._stages), e,
                    exc_info=True,
                    extra={"stage": stage_name, "error": str(e)},
                )
                raise PipelineError(f"Pipeline falhou no estágio {stage_name}: {e}") from e

        total_duration = time.monotonic() - start
        self._last_duration = total_duration

        logger.info(
            "Pipeline concluído em %.2fs. Cursos: %d, Mudanças: %d",
            total_duration, len(ctx.courses), len(ctx.changes_detected),
            extra={
                "duration_s": round(total_duration, 2),
                "courses": len(ctx.courses),
                "changes": len(ctx.changes_detected),
                "activities": sum(len(v) for v in ctx.activities_by_course.values()),
            },
        )

        return ctx

    @property
    def last_duration(self) -> Optional[float]:
        return self._last_duration


class PipelineError(Exception):
    """Erro durante execução do pipeline."""
