"""
Cliente da Web Services REST API do Moodle.
Pipeline de endpoints por prioridade:
  1. core_enrol_get_users_courses → lista cursos
  2. core_course_get_contents → seções + módulos
  3. mod_assign_get_assignments → tarefas com datas
  4. mod_quiz_get_quizzes_by_courses → quizzes
  5. mod_resource_get_resources_by_courses → recursos
  6. core_calendar_get_action_events_by_timesort → eventos futuros
"""

import logging
from datetime import datetime
from typing import Any, Optional

from src.auth.session import SessionManager
from src.scraper.models import (
    ActivityData,
    ActivityType,
    CourseData,
    MoodleFile,
    SectionData,
)

logger = logging.getLogger("moodle_monitor.scraper.api")


class MoodleAPIClient:
    """Cliente para a API REST do Moodle via Web Services."""

    WS_ENDPOINT = "/webservice/rest/server.php"

    def __init__(self, session: SessionManager):
        self._session = session
        self._token = session.state.token

    @property
    def available(self) -> bool:
        return self._token is not None

    def _call(self, function: str, **params) -> Any:
        if not self._token:
            raise APINotAvailableError("Token de API não disponível")

        params.setdefault("moodlewsrestformat", "json")

        query_params: list[tuple[str, str]] = [
            ("wstoken", self._token),
            ("wsfunction", function),
        ]
        for key, value in params.items():
            if isinstance(value, list):
                for i, v in enumerate(value):
                    query_params.append((f"{key}[{i}]", str(v)))
            elif isinstance(value, bool):
                query_params.append((key, "1" if value else "0"))
            else:
                query_params.append((key, str(value)))

        response = self._session.request(
            "GET",
            self.WS_ENDPOINT,
            params=query_params,
        )

        try:
            data = response.json()
        except Exception as e:
            raise APIParseError(f"Falha ao parsear resposta JSON: {e}") from e

        if isinstance(data, dict) and "exception" in data:
            raise APIError(
                f"Moodle API error: {data.get('errorcode', 'unknown')}: "
                f"{data.get('message', 'no message')}"
            )

        return data

    def get_users_courses(self, user_id: Optional[int] = None) -> list[CourseData]:
        uid = user_id or self._session.state.user_id
        if not uid:
            raise APIError("user_id não disponível para buscar cursos")

        try:
            raw_courses = self._call("core_enrol_get_users_courses", userid=uid)
        except (APINotAvailableError, APIError) as e:
            logger.warning("API get_users_courses falhou: %s", e)
            return []

        courses = []
        for rc in raw_courses:
            courses.append(CourseData(
                course_id=rc["id"],
                fullname=rc.get("fullname", ""),
                shortname=rc.get("shortname", ""),
                summary=rc.get("summary"),
                category=str(rc.get("category", "")),
            ))
        return courses

    def get_course_contents(self, course_id: int) -> list[SectionData]:
        try:
            raw_sections = self._call("core_course_get_contents", courseid=course_id)
        except (APINotAvailableError, APIError) as e:
            logger.warning("API get_course_contents falhou para course %s: %s", course_id, e)
            return []

        sections = []
        for rs in raw_sections:
            activities = []
            for rm in rs.get("modules", []):
                activity = self._module_to_activity(rm, course_id, rs)
                if activity:
                    activities.append(activity)

            sections.append(SectionData(
                section_id=rs["id"],
                name=rs.get("name", ""),
                position=rs.get("section", 0),
                summary=rs.get("summary"),
                activities=activities,
            ))

        return sections

    def get_assignments(self, course_ids: list[int]) -> dict[int, list[ActivityData]]:
        try:
            raw = self._call(
                "mod_assign_get_assignments",
                courseids=course_ids,
                includecontents=True,
            )
        except (APINotAvailableError, APIError) as e:
            logger.warning("API get_assignments falhou: %s", e)
            return {}

        result: dict[int, list[ActivityData]] = {}
        for course_data in raw.get("courses", []):
            cid = course_data["id"]
            activities = []
            for ra in course_data.get("assignments", []):
                files = []
                for intro_attachment in ra.get("introattachments", []):
                    files.append(MoodleFile(
                        filename=intro_attachment.get("filename", ""),
                        file_url=intro_attachment.get("fileurl", ""),
                        file_size=intro_attachment.get("filesize"),
                        mimetype=intro_attachment.get("mimetype"),
                    ))

                activity = ActivityData(
                    cmid=ra.get("cmid", 0),
                    instance_id=ra["id"],
                    type=ActivityType.ASSIGN,
                    name=ra.get("name", ""),
                    url=ra.get("urls", {}).get("view", ""),
                    description=ra.get("intro", ""),
                    due_date=self._parse_timestamp(ra.get("duedate")),
                    open_date=self._parse_timestamp(ra.get("allowsubmissionsfromdate")),
                    cutoff_date=self._parse_timestamp(ra.get("cutoffdate")),
                    max_grade=float(ra["grade"]) if ra.get("grade") else None,
                    files=files,
                    source="api",
                )
                activities.append(activity)

            if activities:
                result[cid] = activities

        return result

    def get_quizzes(self, course_ids: list[int]) -> dict[int, list[ActivityData]]:
        try:
            raw = self._call("mod_quiz_get_quizzes_by_courses", courseids=course_ids)
        except (APINotAvailableError, APIError) as e:
            logger.warning("API get_quizzes falhou: %s", e)
            return {}

        result: dict[int, list[ActivityData]] = {}
        for quiz in raw.get("quizzes", []):
            cid = quiz.get("course", 0)
            if cid not in result:
                result[cid] = []

            activity = ActivityData(
                cmid=quiz.get("cmid", 0),
                instance_id=quiz["id"],
                type=ActivityType.QUIZ,
                name=quiz.get("name", ""),
                url=quiz.get("urls", {}).get("view", ""),
                description=quiz.get("intro", ""),
                open_date=self._parse_timestamp(quiz.get("timeopen")),
                due_date=self._parse_timestamp(quiz.get("timeclose")),
                max_grade=float(quiz["grade"]) if quiz.get("grade") else None,
                source="api",
            )
            result[cid].append(activity)

        return result

    def get_calendar_events(
        self,
        timesort_from: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[dict]:
        params: dict[str, Any] = {
            "timesortfrom": int(timesort_from.timestamp()) if timesort_from else 0,
            "limitnum": limit,
        }
        try:
            raw = self._call("core_calendar_get_action_events_by_timesort", **params)
            return raw.get("events", [])
        except (APINotAvailableError, APIError) as e:
            logger.warning("API get_calendar_events falhou: %s", e)
            return []

    def _module_to_activity(
        self,
        module: dict,
        course_id: int,
        section: dict,
    ) -> Optional[ActivityData]:
        modname = module.get("modname", "")
        activity_type = ActivityType(modname) if modname in ActivityType else ActivityType.UNKNOWN

        files = []
        for content in module.get("contents", []):
            files.append(MoodleFile(
                filename=content.get("filename", ""),
                file_url=content.get("fileurl", ""),
                file_size=content.get("filesize"),
                mimetype=content.get("mimetype"),
            ))

        url = module.get("url", "")
        if not url:
            url = f"/mod/{modname}/view.php?id={module.get('id', 0)}"

        description = None
        if "description" in module:
            description = module["description"]
        elif "intro" in module:
            description = module["intro"]

        return ActivityData(
            cmid=module.get("id", 0),
            instance_id=module.get("instance", 0),
            type=activity_type,
            name=module.get("name", ""),
            url=url,
            description=description,
            files=files,
            section_id=section.get("id"),
            section_name=section.get("name"),
            section_position=section.get("section", 0),
            source="api",
        )

    def _parse_timestamp(self, ts: Optional[int]) -> Optional[datetime]:
        if ts and ts > 0:
            return datetime.fromtimestamp(ts)
        return None


class APINotAvailableError(Exception):
    """API Web Service não está disponível."""


class APIParseError(Exception):
    """Erro ao processar resposta da API."""


class APIError(Exception):
    """Erro retornado pela API do Moodle."""
