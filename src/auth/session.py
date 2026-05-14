"""
Gerenciamento de sessão HTTP com suporte a:
- Cookie jar persistente em memória
- Detecção automática de expiração de sessão
- Retry com backoff exponencial
- Headers consistentes
- URLs absolutas ou relativas
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import httpx


SESSION_REDIRECT_INDICATORS = [
    "/login/index.php",
    "login?",
    "Acesso restrito",
    "please login",
    "Sessão expirou",
    "Sua sessão expirou",
]


@dataclass
class SessionState:
    valid: bool = False
    created_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    sesskey: Optional[str] = None
    user_id: Optional[int] = None
    user_fullname: Optional[str] = None
    token: Optional[str] = None


class SessionManager:
    """Gerencia sessão HTTP com cookie jar, retry e detecção de expiração."""

    def __init__(
        self,
        base_url: str,
        user_agent: str,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_base: float = 2.0,
        verify_ssl: bool = True,
    ):
        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent

        limits = httpx.Limits(
            max_keepalive_connections=10,
            max_connections=20,
        )

        timeout_config = httpx.Timeout(
            timeout,
            connect=timeout,
            read=timeout,
            write=timeout,
            pool=timeout,
        )

        transport = httpx.HTTPTransport(
            verify=verify_ssl,
            retries=max_retries,
        )

        self._client = httpx.Client(
            cookies=httpx.Cookies(),
            headers=self._build_headers(),
            follow_redirects=True,
            timeout=timeout_config,
            limits=limits,
            transport=transport,
        )

        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._state = SessionState()

    def _build_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self._user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    @property
    def client(self) -> httpx.Client:
        return self._client

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def base_url(self) -> str:
        return self._base_url

    def get_cookie(self, name: str) -> Optional[str]:
        for cookie in self._client.cookies.jar:
            if cookie.name == name:
                return cookie.value
        return None

    def update_sesskey(self, html: str) -> Optional[str]:
        import re
        match = re.search(
            r'sesskey["\']?\s*[:=]\s*["\']([a-f0-9]+)["\']',
            html, re.IGNORECASE,
        )
        if match:
            self._state.sesskey = match.group(1)
            return match.group(1)

        match = re.search(
            r'name="sesskey"\s+value="([a-f0-9]+)"',
            html,
        )
        if match:
            self._state.sesskey = match.group(1)
            return match.group(1)

        return None

    def is_session_expired(self, response: httpx.Response) -> bool:
        if response.url.path.startswith("/login/"):
            return True
        body_lower = response.text.lower()
        for indicator in SESSION_REDIRECT_INDICATORS:
            if indicator.lower() in body_lower:
                return True
        return False

    def mark_session_valid(self, valid: bool = True) -> None:
        self._state.valid = valid
        if valid and not self._state.created_at:
            self._state.created_at = datetime.now()
        self._state.last_used_at = datetime.now()

    def reset_session(self) -> None:
        self._client.cookies.clear()
        self._state = SessionState()

    def close(self) -> None:
        self._client.close()

    def resolve_url(self, url_or_path: str) -> str:
        """Resolve URL absoluta ou relativa contra a base."""
        if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
            return url_or_path
        base = self._base_url.rstrip("/") + "/"
        clean_path = url_or_path.lstrip("/")
        return urljoin(base, clean_path)

    def request(
        self,
        method: str,
        url_or_path: str,
        *,
        retry_on_session_expiry: bool = True,
        **kwargs,
    ) -> httpx.Response:
        url = self.resolve_url(url_or_path)

        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.request(method, url, **kwargs)

                if retry_on_session_expiry and self.is_session_expired(response):
                    raise SessionExpiredError(
                        f"Session expired during request to {url}"
                    )

                return response

            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as e:
                if attempt < self._max_retries:
                    import time
                    wait = self._backoff_base ** attempt
                    time.sleep(wait)
                    continue
                raise MoodleConnectionError(
                    f"Request failed after {self._max_retries} retries: {e}"
                ) from e

        raise MoodleConnectionError(f"Request failed: {method} {url}")


class SessionExpiredError(Exception):
    """Sessão expirou e precisa ser renovada."""


class MoodleConnectionError(Exception):
    """Erro de conexão com o servidor."""
