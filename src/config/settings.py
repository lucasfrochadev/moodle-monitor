"""
Gerenciamento de configuração centralizado.
Pipeline: file_env → YAML → env vars → defaults
Suporta dois domínios: portal customizado + Moodle.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass
class PortalConfig:
    url: str = ""
    username: str = ""
    password: str = ""
    campus_id: str = ""
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_backoff_base: float = 2.0
    verify_ssl: bool = True


@dataclass
class MoodleConfig:
    url: str = ""
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_backoff_base: float = 2.0
    verify_ssl: bool = True


@dataclass
class MonitoringConfig:
    check_interval_minutes: int = 15
    urgent_check_interval_minutes: int = 5
    expired_check_interval_minutes: int = 60
    jitter_percent: int = 20
    max_concurrent_courses: int = 5
    max_concurrent_activities_per_course: int = 10
    urgent_deadline_hours: int = 24
    snapshot_retention_days: int = 90
    change_retention_days: int = 180
    notification_cooldown_minutes: int = 30
    min_diff_chars: int = 3
    course_ids: list[int] = field(default_factory=list)


@dataclass
class StorageConfig:
    database_path: str = "./data/monitor.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    backup_dir: str = "./data/backups"


@dataclass
class NotificationsConfig:
    enabled: bool = True
    on_new_activity: bool = True
    on_deadline_change: bool = True
    on_description_change: bool = True
    on_file_added: bool = True
    on_file_removed: bool = False
    on_name_change: bool = True
    on_grade_change: bool = True
    telegram: dict = field(default_factory=lambda: {"enabled": False})
    discord: dict = field(default_factory=lambda: {"enabled": False})
    email: dict = field(default_factory=lambda: {"enabled": False})


@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "json"
    output: str = "console"
    file_path: str = "./logs/monitor.log"
    max_file_size_mb: int = 50
    backup_count: int = 7


@dataclass
class Config:
    portal: PortalConfig = field(default_factory=PortalConfig)
    moodle: MoodleConfig = field(default_factory=MoodleConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _resolve_env(value: Any) -> Any:
    if isinstance(value, str):
        pattern = re.compile(r"\$\{([^}]+)\}")
        return pattern.sub(lambda m: os.environ.get(m.group(1), ""), value)
    return value


def _resolve_env_dict(data: dict) -> dict:
    result = {}
    for k, v in data.items():
        if isinstance(v, dict):
            result[k] = _resolve_env_dict(v)
        elif isinstance(v, list):
            result[k] = [_resolve_env(item) for item in v]
        else:
            result[k] = _resolve_env(v)
    return result


def _dict_to_dataclass(data: dict, cls: type) -> Any:
    field_types = cls.__dataclass_fields__
    kwargs = {}
    for field_name, field_def in field_types.items():
        if field_name in data:
            val = data[field_name]
            if hasattr(field_def.type, "__dataclass_fields__"):
                if isinstance(val, dict):
                    kwargs[field_name] = _dict_to_dataclass(val, field_def.type)
                else:
                    kwargs[field_name] = val
            else:
                kwargs[field_name] = val
    return cls(**kwargs)


def load_config(path: str = "config.yaml") -> Config:
    load_dotenv()

    cfg = Config()

    if not Path(path).exists():
        return cfg

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    raw_resolved = _resolve_env_dict(raw)

    if "portal" in raw_resolved:
        cfg.portal = _dict_to_dataclass(raw_resolved["portal"], PortalConfig)
    if "moodle" in raw_resolved:
        cfg.moodle = _dict_to_dataclass(raw_resolved["moodle"], MoodleConfig)
    if "monitoring" in raw_resolved:
        cfg.monitoring = _dict_to_dataclass(raw_resolved["monitoring"], MonitoringConfig)
    if "storage" in raw_resolved:
        cfg.storage = _dict_to_dataclass(raw_resolved["storage"], StorageConfig)
    if "notifications" in raw_resolved:
        cfg.notifications = _dict_to_dataclass(raw_resolved["notifications"], NotificationsConfig)
    if "logging" in raw_resolved:
        cfg.logging = _dict_to_dataclass(raw_resolved["logging"], LoggingConfig)

    return cfg


def validate_config(config: Config) -> list[str]:
    errors = []

    if not config.portal.url:
        errors.append("portal.url é obrigatório (ex: https://unisalesiano.com.br/salaEstudo/alunos/)")
    if not config.portal.username:
        errors.append("portal.username é obrigatório (seu RA)")
    if not config.portal.password:
        errors.append("portal.password é obrigatório")
    if not config.moodle.url:
        errors.append("moodle.url é obrigatório (ex: https://missaosalesiana.mrooms.net/)")
    if config.monitoring.check_interval_minutes < 1:
        errors.append("monitoring.check_interval_minutes deve ser >= 1")

    if config.notifications.telegram.get("enabled"):
        if not config.notifications.telegram.get("bot_token"):
            errors.append("Telegram enabled but bot_token is missing")

    if config.notifications.discord.get("enabled"):
        if not config.notifications.discord.get("webhook_url"):
            errors.append("Discord enabled but webhook_url is missing")

    if config.notifications.email.get("enabled"):
        email = config.notifications.email
        if not email.get("smtp_server"):
            errors.append("Email enabled but smtp_server is missing")

    return errors
