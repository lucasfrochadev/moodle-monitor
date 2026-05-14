"""
Notificador via Discord Webhook.
Requer: DISCORD_WEBHOOK_URL configurado.
"""

import logging
from typing import Optional

import httpx

from src.notifier.base import Notifier

logger = logging.getLogger("moodle_monitor.notifier.discord")


class DiscordNotifier(Notifier):
    def __init__(self, webhook_url: str):
        self._webhook_url = webhook_url

    @property
    def name(self) -> str:
        return "discord"

    async def send(
        self,
        change,
        activity_name: str,
        course_name: str,
        activity_url: str,
    ) -> bool:
        message = self._format_message(change, activity_name, course_name, activity_url)

        embed_color = self._get_color(change.severity)
        embed = {
            "title": self._get_change_label(change.change_type),
            "description": message[:2048],
            "color": embed_color,
            "timestamp": change.detected_at.isoformat() if change.detected_at else None,
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    self._webhook_url,
                    json={
                        "embeds": [embed],
                        "username": "Moodle Monitor",
                    },
                )
                if response.status_code in (200, 204):
                    logger.info("Notificação Discord enviada")
                    return True
                else:
                    logger.error(
                        "Erro Discord webhook: %s %s",
                        response.status_code,
                        response.text,
                    )
                    return False

        except httpx.TimeoutException:
            logger.error("Timeout ao enviar notificação Discord")
            return False
        except Exception as e:
            logger.error("Erro ao enviar notificação Discord: %s", e)
            return False

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(self._webhook_url)
                return response.status_code < 400
        except Exception:
            return False

    def _get_color(self, severity) -> int:
        color_map = {
            "critical": 0xE74C3C,
            "warning": 0xF39C12,
            "info": 0x3498DB,
        }
        return color_map.get(str(severity.value) if hasattr(severity, 'value') else str(severity), 0x95A5A6)
