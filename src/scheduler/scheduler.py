"""
Scheduler assíncrono para execução periódica dos ciclos de monitoramento.
Suporta intervalos adaptativos baseados em urgência das atividades.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Callable, Optional

logger = logging.getLogger("moodle_monitor.scheduler")


class AdaptiveScheduler:
    """Scheduler com intervalos adaptativos por curso."""

    def __init__(
        self,
        callback: Callable[[], any],
        default_interval_minutes: int = 15,
        urgent_interval_minutes: int = 5,
        expired_interval_minutes: int = 60,
        jitter_percent: int = 20,
    ):
        self._callback = callback
        self._default_interval = timedelta(minutes=default_interval_minutes)
        self._urgent_interval = timedelta(minutes=urgent_interval_minutes)
        self._expired_interval = timedelta(minutes=expired_interval_minutes)
        self._jitter = jitter_percent / 100.0
        self._running = False
        self._cycle_count = 0
        self._last_duration: Optional[timedelta] = None
        self._consecutive_errors = 0

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    def _sleep_duration(self) -> timedelta:
        return self._default_interval

    def _apply_jitter(self, interval: timedelta) -> timedelta:
        jitter_range = interval.total_seconds() * self._jitter
        jitter = random.uniform(-jitter_range, jitter_range)
        return timedelta(seconds=max(1, interval.total_seconds() + jitter))

    async def run_forever(self) -> None:
        self._running = True
        logger.info(
            "Scheduler iniciado (intervalo: %s, urgente: %s)",
            self._default_interval, self._urgent_interval,
        )

        while self._running:
            cycle_start = datetime.now()
            self._cycle_count += 1

            try:
                if asyncio.iscoroutinefunction(self._callback):
                    await self._callback()
                else:
                    self._callback()

                self._consecutive_errors = 0

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._consecutive_errors += 1
                logger.error(
                    "Erro no ciclo %d: %s",
                    self._cycle_count, e,
                    exc_info=True,
                    extra={"cycle": self._cycle_count, "error": str(e)},
                )

            cycle_duration = datetime.now() - cycle_start
            self._last_duration = cycle_duration

            sleep_time = self._sleep_duration()
            sleep_time = self._apply_jitter(sleep_time)

            actual_sleep = max(
                timedelta(seconds=1),
                sleep_time - cycle_duration,
            )

            logger.info(
                "Ciclo %d concluído em %s. Próximo em %s",
                self._cycle_count,
                cycle_duration,
                actual_sleep,
            )

            await asyncio.sleep(actual_sleep.total_seconds())

    def stop(self) -> None:
        self._running = False
        logger.info("Scheduler parado")
