"""
Estratégias de autenticação em dois estágios:
1. Login no portal institucional (validarLogin.php)
2. Extrai credenciais Moodle via loginAva.php (SSO automático)
3. Login no Moodle com as credenciais extraídas

Pipeline completo:
  Portal (validarLogin.php) → loginAva.php → Moodle (missaosalesiana.mrooms.net)
"""

import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from src.auth.session import SessionManager, SessionExpiredError

logger = logging.getLogger("moodle_monitor.auth")


class AuthenticationError(Exception):
    """Falha na autenticação no portal ou Moodle."""


class AuthManager:
    """Autenticação em dois estágios: portal institucional → Moodle.

    Fluxo:
      1. POST para validarLogin.php com RA + senha + unidade
      2. POST para loginAva.php que retorna HTML com formulário contendo
         credenciais Moodle (username + password) geradas automaticamente
      3. Login no Moodle com as credenciais extraídas
      4. Obtém token da API Web Services do Moodle
    """

    def __init__(
        self,
        portal_session: SessionManager,
        moodle_session: SessionManager,
        username: str,
        password: str,
        campus_id: str = "",
    ):
        self._portal_session = portal_session
        self._moodle_session = moodle_session
        self._username = username
        self._password = password
        self._campus_id = campus_id
        self._moodle_username: Optional[str] = None
        self._moodle_password: Optional[str] = None

    def authenticate(self) -> tuple[SessionManager, SessionManager]:
        """Executa o pipeline completo de autenticação em dois estágios."""
        logger.info("Iniciando autenticação em dois estágios", extra={
            "portal": self._portal_session.base_url,
            "moodle": self._moodle_session.base_url,
            "username": self._username,
        })

        self._login_portal()
        self._get_moodle_credentials()
        self._login_moodle()

        logger.info("Autenticação completa: portal + Moodle")
        return self._portal_session, self._moodle_session

    # ───────────────────────────────
    # ESTÁGIO 1: Login no Portal
    # ───────────────────────────────

    def _login_portal(self) -> None:
        """Login no portal institucional via AJAX endpoint (../libs/soa/validarLogin.php).

        O formulário HTML aponta para validarLogin.php, mas o JavaScript
        sobrescreve para ../libs/soa/validarLogin.php. A resposta é JSON:
          [{tipo: "OK", url: "menu.php"}] em caso de sucesso
          [{tipo: "NEGADO", mensagem: "..."}] em caso de falha
        """
        logger.info("Estágio 1: Login no portal institucional")

        login_data = {
            "ra": self._username,
            "senha": self._password,
        }
        if self._campus_id:
            login_data["idCasa"] = self._campus_id

        try:
            response = self._portal_session.request(
                "POST",
                "../libs/soa/validarLogin.php",
                data=login_data,
                retry_on_session_expiry=False,
            )

            if response.status_code != 200:
                raise AuthenticationError(
                    f"Portal retornou HTTP {response.status_code}"
                )

            try:
                json_response = response.json()
            except Exception:
                raise AuthenticationError(
                    "Resposta do portal não é JSON válido"
                )

            if not isinstance(json_response, list) or len(json_response) == 0:
                raise AuthenticationError("Resposta JSON inesperada do portal")

            result = json_response[0]
            tipo = result.get("tipo", "")

            if tipo == "NEGADO":
                mensagem = result.get("mensagem", "Acesso negado")
                raise AuthenticationError(f"Login negado: {mensagem}")

            if tipo != "OK":
                raise AuthenticationError(f"Resposta inesperada do portal: tipo={tipo}")

            portal_url = result.get("url", "")
            if portal_url:
                logger.info("Login OK, redirecionando para: %s", portal_url)

            self._portal_session.mark_session_valid(True)
            logger.info("Login no portal bem-sucedido")

        except httpx.HTTPStatusError as e:
            raise AuthenticationError(f"Erro HTTP no login do portal: {e}") from e
        except httpx.RequestError as e:
            raise AuthenticationError(f"Erro de conexão com o portal: {e}") from e

    # ───────────────────────────────
    # ESTÁGIO 2: Extrair Credenciais do Moodle
    # ───────────────────────────────

    def _get_moodle_credentials(self) -> tuple[str, str]:
        """POST para loginAva.php que retorna HTML com formulário contendo
        as credenciais Moodle (username + password) geradas automaticamente
        pelo portal para SSO.

        O HTML retornado contém:
          <form id="frmBB" method="post" action="https://missaosalesiana.mrooms.net/login/index.php">
            <input type="hidden" name="username" value="..."/>
            <input type="hidden" name="password" value="..."/>
          </form>
          <script>document.getElementById('frmBB').submit();</script>
        """
        logger.info("Estágio 2: Extraindo credenciais do Moodle via loginAva.php")

        try:
            response = self._portal_session.request(
                "POST",
                "../libs/soa/loginAva.php",
                data={},
                retry_on_session_expiry=False,
            )
        except Exception as e:
            raise AuthenticationError(
                f"Erro ao acessar loginAva.php: {e}"
            ) from e

        soup = BeautifulSoup(response.text, "lxml")
        form = soup.find("form", id="frmBB")
        if not form:
            raise AuthenticationError(
                "Formulário frmBB não encontrado em loginAva.php. "
                "Verifique se o login do portal foi bem-sucedido."
            )

        username_input = form.find("input", {"name": "username"})
        password_input = form.find("input", {"name": "password"})
        if not username_input or not password_input:
            raise AuthenticationError(
                "Campos username/password não encontrados no formulário loginAva.php"
            )

        self._moodle_username = username_input.get("value", "")
        self._moodle_password = password_input.get("value", "")

        if not self._moodle_username or not self._moodle_password:
            raise AuthenticationError(
                "Credenciais Moodle vazias retornadas por loginAva.php"
            )

        logger.info(
            "Credenciais Moodle extraídas",
            extra={"username": self._moodle_username},
        )
        return self._moodle_username, self._moodle_password

    # ───────────────────────────────
    # ESTÁGIO 3: Login no Moodle
    # ───────────────────────────────

    def _login_moodle(self) -> None:
        """Estabelece sessão no Moodle.

        Tenta:
          1. Login direto no formulário Moodle com credenciais extraídas do loginAva.php
          2. Token API com as mesmas credenciais
        """
        logger.info("Estágio 3: Login no Moodle")

        if not self._moodle_username or not self._moodle_password:
            raise AuthenticationError(
                "Credenciais Moodle não disponíveis. Execute _get_moodle_credentials primeiro."
            )

        session_ok = self._try_direct_moodle_login()

        self._try_moodle_token_auth()

        if not session_ok and not self._moodle_session.state.valid:
            raise AuthenticationError(
                "Não foi possível autenticar no Moodle por nenhum método disponível"
            )

    def _try_direct_moodle_login(self) -> bool:
        """Login direto no formulário do Moodle com as credenciais extraídas."""
        try:
            login_page = self._moodle_session.request(
                "GET",
                "/login/index.php",
                retry_on_session_expiry=False,
            )

            logintoken = self._extract_login_token(login_page.text)
            login_data = {
                "username": self._moodle_username,
                "password": self._moodle_password,
            }
            if logintoken:
                login_data["logintoken"] = logintoken

            response = self._moodle_session.request(
                "POST",
                "/login/index.php",
                data=login_data,
                retry_on_session_expiry=False,
            )

            if self._moodle_session.get_cookie("MoodleSession"):
                self._moodle_session.update_sesskey(response.text)
                self._moodle_session.mark_session_valid(True)
                logger.info("Login direto no Moodle bem-sucedido")
                return True

            body_lower = response.text.lower()
            login_url = str(response.url)
            if "/login" in login_url or "invalid" in body_lower or "incorrect" in body_lower:
                logger.warning("Credenciais Moodle inválidas ou login recusado")

            return False

        except Exception as e:
            logger.debug("Login direto no Moodle falhou: %s", e)
            return False

    def _try_moodle_token_auth(self) -> bool:
        """Tenta autenticação via token da Web Services API do Moodle."""
        try:
            response = self._moodle_session.request(
                "POST",
                "/login/token.php",
                data={
                    "username": self._moodle_username,
                    "password": self._moodle_password,
                    "service": "moodle_mobile_app",
                },
                retry_on_session_expiry=False,
            )

            data = response.json()
            if "token" in data:
                self._moodle_session.state.token = data["token"]
                self._moodle_session.mark_session_valid(True)

                site_info = self._fetch_site_info()
                if site_info:
                    self._moodle_session.state.user_id = site_info.get("userid")
                    self._moodle_session.state.user_fullname = site_info.get("fullname")

                logger.info("Autenticação via token API Moodle bem-sucedida")
                return True

            logger.debug("Token API falhou: %s", data.get("error", "resposta inesperada"))
            return False

        except Exception as e:
            logger.debug("Token auth falhou: %s", e)
            return False

    def _fetch_site_info(self) -> Optional[dict]:
        token = self._moodle_session.state.token
        if not token:
            return None
        try:
            response = self._moodle_session.request(
                "GET",
                "/webservice/rest/server.php",
                params={
                    "wstoken": token,
                    "wsfunction": "core_webservice_get_site_info",
                    "moodlewsrestformat": "json",
                },
                retry_on_session_expiry=False,
            )
            return response.json()
        except Exception as e:
            logger.debug("Failed to fetch site info: %s", e)
            return None

    # ───────────────────────────────
    # Utilitários
    # ───────────────────────────────

    def _extract_login_token(self, html: str) -> Optional[str]:
        match = re.search(
            r'<input\s+type="hidden"[^>]*name="logintoken"[^>]*value="([^"]+)"',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1)
        match = re.search(
            r'logintoken["\']?\s*[:=]\s*["\']([a-f0-9]+)["\']',
            html,
            re.IGNORECASE,
        )
        return match.group(1) if match else None

    def renew_session(self) -> bool:
        """Renova sessão completa (portal + Moodle)."""
        logger.info("Renovando sessão completa (portal + Moodle)")
        self._portal_session.reset_session()
        self._moodle_session.reset_session()
        self._moodle_username = None
        self._moodle_password = None

        try:
            self.authenticate()
            return True
        except AuthenticationError as e:
            logger.critical("Falha ao renovar sessão: %s", e)
            return False
