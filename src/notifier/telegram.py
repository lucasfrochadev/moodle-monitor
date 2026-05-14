"""
Notificador via Telegram Bot API.
Requer: TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID configurados.
"""

import logging
from typing import Optional

import httpx

from src.notifier.base import Notifier

logger = logging.getLogger("moodle_monitor.notifier.telegram")


class TelegramNotifier(Notifier):
    def __init__(self, bot_token: str, chat_id: str):
        self._token = bot_token
        self._chat_id = chat_id
        self._api_base = f"https://api.telegram.org/bot{bot_token}"

    @property
    def name(self) -> str:
        return "telegram"

    async def send(
        self,
        change,
        activity_name: str,
        course_name: str,
        activity_url: str,
    ) -> bool:
        message = self._format_message(change, activity_name, course_name, activity_url)
        message = message.replace("*", "**").replace("_", "__")
        message = message[:4096]

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{self._api_base}/sendMessage",
                    json={
                        "chat_id": self._chat_id,
                        "text": message,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True,
                    },
                )
                if response.status_code == 200:
                    logger.info("Notificação Telegram enviada")
                    return True
                else:
                    logger.error(
                        "Erro Telegram API: %s %s",
                        response.status_code,
                        response.text,
                    )
                    return False

        except httpx.TimeoutException:
            logger.error("Timeout ao enviar notificação Telegram")
            return False
        except Exception as e:
            logger.error("Erro ao enviar notificação Telegram: %s", e)
            return False

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self._api_base}/getMe")
                return response.status_code == 200
        except Exception:
            return False
