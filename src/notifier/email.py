"""
Notificador via Email SMTP.
Requer configuração SMTP no .env.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from typing import Optional

from src.notifier.base import Notifier

logger = logging.getLogger("moodle_monitor.notifier.email")


class EmailNotifier(Notifier):
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        from_address: str,
        to_address: str,
        use_tls: bool = True,
    ):
        self._server = smtp_server
        self._port = smtp_port
        self._username = smtp_username
        self._password = smtp_password
        self._from = from_address
        self._to = to_address
        self._use_tls = use_tls

    @property
    def name(self) -> str:
        return "email"

    async def send(
        self,
        change,
        activity_name: str,
        course_name: str,
        activity_url: str,
    ) -> bool:
        message = self._format_message(change, activity_name, course_name, activity_url)
        subject = f"[Moodle Monitor] {self._get_change_label(change.change_type)} - {activity_name}"

        html = self._build_html(subject, message)

        msg = MIMEText(html, "html")
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = self._to

        try:
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._send_sync, msg)
            return result
        except Exception as e:
            logger.error("Erro ao enviar email: %s", e)
            return False

    def _send_sync(self, msg: MIMEText) -> bool:
        try:
            if self._use_tls:
                server = smtplib.SMTP(self._server, self._port)
                server.starttls()
            else:
                server = smtplib.SMTP(self._server, self._port)

            if self._username and self._password:
                server.login(self._username, self._password)

            server.send_message(msg)
            server.quit()
            logger.info("Email enviado para %s", self._to)
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("Falha de autenticação SMTP")
            return False
        except smtplib.SMTPException as e:
            logger.error("Erro SMTP: %s", e)
            return False

    def _build_html(self, subject: str, body: str) -> str:
        body_html = body.replace("\n", "<br>")
        body_html = body_html.replace("*", "<b>").replace("*", "</b>")
        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5;">
<div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; padding: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
<h2 style="color: #2c3e50; margin-top: 0;">{subject}</h2>
<div style="line-height: 1.6;">{body_html}</div>
<hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
<p style="color: #95a5a6; font-size: 12px;">Enviado por Moodle Monitor</p>
</div>
</body>
</html>"""

    async def health_check(self) -> bool:
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._check_sync)
            return result
        except Exception:
            return False

    def _check_sync(self) -> bool:
        try:
            if self._use_tls:
                server = smtplib.SMTP(self._server, self._port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(self._server, self._port, timeout=10)
            server.quit()
            return True
        except Exception:
            return False
