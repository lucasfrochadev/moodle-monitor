"""
Motor principal de monitoramento.
Orquestra todo o ciclo de vida: autenticação → pipeline → notificação → scheduler.
Suporta sessões em dois domínios: portal institucional + Moodle.
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import Optional

import structlog

from src.auth.moodle_auth import AuthManager, AuthenticationError
from src.auth.session import SessionManager, SessionExpiredError
from src.config.settings import Config
from src.detector.filter import FalsePositiveFilter
from src.notifier.base import Notifier
from src.notifier.discord import DiscordNotifier
from src.notifier.email import EmailNotifier
from src.notifier.telegram import TelegramNotifier
from src.pipeline.pipeline import Pipeline, PipelineError
from src.pipeline.stages import (
    ActivityDetailStage,
    CompareStage,
    CourseScanStage,
    NotificationStage,
    SectionScanStage,
    SnapshotStage,
    StageContext,
)
from src.scheduler.scheduler import AdaptiveScheduler
from src.scraper.extractor import Extractor
from src.storage.database import Database
from src.storage.repository import (
    ActivityRepository,
    ChangeRepository,
    CourseRepository,
    FileRepository,
    MonitorStateRepository,
    NotificationLogRepository,
    SectionRepository,
    SnapshotRepository,
)

logger = logging.getLogger("moodle_monitor.engine")


class MonitorEngine:
    """Engine principal que coordena todo o sistema de monitoramento."""

    def __init__(self, config: Config):
        self._config = config
        self._portal_session: Optional[SessionManager] = None
        self._moodle_session: Optional[SessionManager] = None
        self._auth: Optional[AuthManager] = None
        self._extractor: Optional[Extractor] = None
        self._db: Optional[Database] = None
        self._pipeline: Optional[Pipeline] = None
        self._scheduler: Optional[AdaptiveScheduler] = None
        self._notifiers: list[Notifier] = []
        self._state_repo: Optional[MonitorStateRepository] = None
        self._running = False
        self._started_at: Optional[datetime] = None

    async def initialize(self) -> None:
        self._started_at = datetime.now()
        self._setup_logging()

        logger.info(
            "Inicializando Moodle Monitor",
            extra={
                "portal": self._config.portal.url,
                "moodle": self._config.moodle.url,
                "check_interval": self._config.monitoring.check_interval_minutes,
            },
        )

        self._init_storage()
        self._init_sessions()
        self._authenticate()
        self._init_extractor()
        self._init_notifiers()
        self._init_pipeline()
        self._init_scheduler()

        await self._log_health()

    def _setup_logging(self) -> None:
        log_level = getattr(logging, self._config.logging.level.upper(), logging.INFO)

        processors = [
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ]

        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        logging.basicConfig(
            level=log_level,
            format="%(message)s",
            stream=sys.stdout,
            force=True,
        )

    def _init_storage(self) -> None:
        self._db = Database(self._config.storage.database_path)
        self._db.initialize()

        integrity_ok = self._db.check_integrity()
        if not integrity_ok:
            logger.critical("Integridade do banco de dados comprometida")
            raise RuntimeError("Database integrity check failed")

        self._state_repo = MonitorStateRepository(self._db)
        logger.info("Storage inicializado", extra={"path": self._config.storage.database_path})

    def _init_sessions(self) -> None:
        """Inicializa duas sessões: uma para o portal, outra para o Moodle."""
        common_kwargs = dict(
            user_agent=self._config.portal.user_agent,
            timeout=self._config.portal.timeout_seconds,
            max_retries=self._config.portal.max_retries,
            backoff_base=self._config.portal.retry_backoff_base,
            verify_ssl=self._config.portal.verify_ssl,
        )

        self._portal_session = SessionManager(
            base_url=self._config.portal.url,
            **common_kwargs,
        )

        self._moodle_session = SessionManager(
            base_url=self._config.moodle.url,
            **common_kwargs,
        )

        logger.debug(
            "Sessões inicializadas: portal=%s, moodle=%s",
            self._config.portal.url,
            self._config.moodle.url,
        )

    def _authenticate(self) -> None:
        """Autentica nos dois domínios: portal → Moodle."""
        self._auth = AuthManager(
            portal_session=self._portal_session,
            moodle_session=self._moodle_session,
            username=self._config.portal.username,
            password=self._config.portal.password,
            campus_id=self._config.portal.campus_id,
        )

        try:
            self._auth.authenticate()
            self._state_repo.set("session_valid", "true")

            username = (
                self._moodle_session.state.user_fullname
                or self._portal_session.state.user_fullname
                or self._config.portal.username
            )
            logger.info("Autenticado como %s", username)

        except AuthenticationError as e:
            self._state_repo.set("session_valid", "false")
            self._state_repo.set("last_auth_error", str(e))
            logger.critical("Falha na autenticação: %s", e)
            raise

    def _init_extractor(self) -> None:
        """Extractor usa a sessão do Moodle para acessar dados."""
        self._extractor = Extractor(self._moodle_session)

        api_token = self._moodle_session.state.token if self._moodle_session else None
        if api_token:
            logger.info("Modo API + HTML (token Moodle disponível)")
        else:
            logger.warning("Modo somente HTML (API Moodle indisponível)")

    def _init_notifiers(self) -> None:
        notif_config = self._config.notifications

        if notif_config.telegram.get("enabled"):
            token = notif_config.telegram.get("bot_token", "")
            chat_id = notif_config.telegram.get("chat_id", "")
            if token and chat_id:
                self._notifiers.append(TelegramNotifier(token, chat_id))
                logger.info("Notificador Telegram configurado")

        if notif_config.discord.get("enabled"):
            webhook = notif_config.discord.get("webhook_url", "")
            if webhook:
                self._notifiers.append(DiscordNotifier(webhook))
                logger.info("Notificador Discord configurado")

        if notif_config.email.get("enabled"):
            email_cfg = notif_config.email
            if email_cfg.get("smtp_server"):
                self._notifiers.append(EmailNotifier(
                    smtp_server=email_cfg["smtp_server"],
                    smtp_port=email_cfg.get("smtp_port", 587),
                    smtp_username=email_cfg.get("smtp_username", ""),
                    smtp_password=email_cfg.get("smtp_password", ""),
                    from_address=email_cfg.get("from_address", ""),
                    to_address=email_cfg.get("to_address", ""),
                    use_tls=email_cfg.get("use_tls", True),
                ))
                logger.info("Notificador Email configurado")

        if not self._notifiers:
            logger.warning("Nenhum notificador configurado")

    def _init_pipeline(self) -> None:
        course_repo = CourseRepository(self._db)
        section_repo = SectionRepository(self._db)
        activity_repo = ActivityRepository(self._db)
        snapshot_repo = SnapshotRepository(self._db)
        file_repo = FileRepository(self._db)
        change_repo = ChangeRepository(self._db)
        notif_log_repo = NotificationLogRepository(self._db)

        fp_filter = FalsePositiveFilter(
            cooldown_minutes=self._config.monitoring.notification_cooldown_minutes,
            min_diff_chars=self._config.monitoring.min_diff_chars,
        )

        notif_config_dict = {
            "on_new_activity": self._config.notifications.on_new_activity,
            "on_deadline_change": self._config.notifications.on_deadline_change,
            "on_description_change": self._config.notifications.on_description_change,
            "on_file_added": self._config.notifications.on_file_added,
            "on_file_removed": self._config.notifications.on_file_removed,
            "on_name_change": self._config.notifications.on_name_change,
            "on_grade_change": self._config.notifications.on_grade_change,
        }

        self._pipeline = Pipeline()

        self._pipeline.add_stage(CourseScanStage(
            self._extractor, course_repo,
            course_ids=self._config.monitoring.course_ids or None,
        ))
        self._pipeline.add_stage(SectionScanStage(
            self._extractor, course_repo, section_repo, activity_repo,
            max_concurrent=self._config.monitoring.max_concurrent_courses,
            include_types={'assign', 'quiz', 'forum', 'unknown', 'hsuforum'},
        ))
        self._pipeline.add_stage(ActivityDetailStage(
            self._extractor,
            max_concurrent=self._config.monitoring.max_concurrent_activities_per_course,
        ))
        self._pipeline.add_stage(SnapshotStage(activity_repo, snapshot_repo, file_repo))
        self._pipeline.add_stage(CompareStage(
            activity_repo, change_repo, snapshot_repo, fp_filter, notif_log_repo,
            min_diff_chars=self._config.monitoring.min_diff_chars,
        ))
        self._pipeline.add_stage(NotificationStage(
            self._notifiers, change_repo, notif_log_repo,
            activity_repo, course_repo, notif_config_dict,
        ))

        logger.info("Pipeline configurado com %d estágios", len(self._pipeline._stages))

    def _init_scheduler(self) -> None:
        async def pipeline_callback():
            if not self._running:
                return

            if not self._is_moodle_session_valid():
                logger.warning("Sessão Moodle inválida, tentando renovar...")
                if not self._auth or not self._auth.renew_session():
                    logger.error("Falha ao renovar sessão, pulando ciclo")
                    return
                self._state_repo.set("session_valid", "true")

            try:
                ctx = await self._pipeline.execute()
                self._state_repo.set("last_successful_check", datetime.now().isoformat())
                self._state_repo.set("consecutive_errors", "0")
            except PipelineError as e:
                logger.error("Pipeline error: %s", e)
                err_count = int(self._state_repo.get("consecutive_errors") or "0") + 1
                self._state_repo.set("consecutive_errors", str(err_count))
            except SessionExpiredError:
                logger.info("Sessão Moodle expirou durante pipeline")
                self._state_repo.set("session_valid", "false")

        self._scheduler = AdaptiveScheduler(
            callback=pipeline_callback,
            default_interval_minutes=self._config.monitoring.check_interval_minutes,
            urgent_interval_minutes=self._config.monitoring.urgent_check_interval_minutes,
            expired_interval_minutes=self._config.monitoring.expired_check_interval_minutes,
            jitter_percent=self._config.monitoring.jitter_percent,
        )

    def _is_moodle_session_valid(self) -> bool:
        return bool(self._moodle_session and self._moodle_session.state.valid)

    async def run_single_cycle(self) -> StageContext:
        logger.info("Executando ciclo único de monitoramento")
        self._running = True

        if not self._is_moodle_session_valid():
            if self._auth:
                self._auth.renew_session()

        ctx = await self._pipeline.execute()
        self._running = False
        return ctx

    async def run_forever(self) -> None:
        self._running = True
        self._state_repo.set("monitor_status", "running")
        self._state_repo.set("started_at", self._started_at.isoformat())

        logger.info(
            "Monitor iniciado. Verificando a cada %d minutos (urgente: %d min, expirado: %d min)",
            self._config.monitoring.check_interval_minutes,
            self._config.monitoring.urgent_check_interval_minutes,
            self._config.monitoring.expired_check_interval_minutes,
        )

        try:
            await self._scheduler.run_forever()
        except asyncio.CancelledError:
            logger.info("Monitor cancelado")
        finally:
            self._running = False
            self._state_repo.set("monitor_status", "stopped")

    async def shutdown(self) -> None:
        logger.info("Desligando monitor...")
        self._running = False

        if self._scheduler:
            self._scheduler.stop()

        if self._state_repo and self._started_at:
            uptime = datetime.now() - self._started_at
            try:
                self._state_repo.set("last_shutdown", datetime.now().isoformat())
                self._state_repo.set("total_uptime_seconds", str(int(uptime.total_seconds())))
            except Exception:
                pass

        if self._portal_session:
            self._portal_session.close()
        if self._moodle_session:
            self._moodle_session.close()

        if self._db:
            size = self._db.get_size()
            self._db.close()
            logger.info("Banco de dados fechado (tamanho: %.2f MB)", size / (1024 * 1024))

        logger.info("Monitor desligado")

    async def _log_health(self) -> None:
        uptime = datetime.now() - self._started_at
        moodle_ok = self._is_moodle_session_valid()
        api_ok = bool(self._moodle_session and self._moodle_session.state.token)

        logger.info(
            "Health check: online há %s | Canais: %d | Moodle: %s | API: %s",
            uptime, len(self._notifiers),
            "conectado" if moodle_ok else "desconectado",
            "disponível" if api_ok else "indisponível",
        )
