"""
Estratégias de extração de dados do Moodle.
Pipeline: API primeiro, AJAX em segundo, HTML como fallback.
Coordena as múltiplas fontes de dados e normaliza a saída.
"""

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

from src.auth.session import SessionManager
from src.scraper.api_client import MoodleAPIClient
from src.scraper.html_parser import MoodleHTMLParser
from src.scraper.models import ActivityData, CourseData, SectionData

logger = logging.getLogger("moodle_monitor.scraper.extractor")


class ExtractionError(Exception):
    """Erro durante extração de dados do Moodle."""


class Extractor:
    """Estratégia híbrida de extração: API primeiro, HTML como fallback."""

    def __init__(self, session: SessionManager):
        self._session = session
        self._api = MoodleAPIClient(session)
        self._html = MoodleHTMLParser()
        self._api_available = self._api.available

    @property
    def api_available(self) -> bool:
        return self._api_available

    def extract_courses(self) -> list[CourseData]:
        if self._api_available:
            courses = self._api.get_users_courses()
            if courses:
                logger.info(
                    "Cursos obtidos via API",
                    extra={"count": len(courses), "source": "api"},
                )
                return courses

        logger.info("Fallback: extraindo cursos via HTML")
        return self._extract_courses_html()

    def extract_course_contents(self, course: CourseData) -> list[SectionData]:
        if self._api_available:
            sections = self._api.get_course_contents(course.course_id)
            if sections:
                activity_count = sum(len(s.activities) for s in sections)
                logger.info(
                    "Conteúdo do curso via API",
                    extra={
                        "course_id": course.course_id,
                        "sections": len(sections),
                        "activities": activity_count,
                    },
                )
                return sections

        logger.info(
            "Fallback: extraindo conteúdo via HTML",
            extra={"course_id": course.course_id},
        )
        return self._extract_contents_html(course)

    def extract_activity_detail(self, activity: ActivityData) -> Optional[ActivityData]:
        if activity.source == "api" and activity.description:
            return activity

        return self._extract_activity_detail_html(activity)

    def _extract_courses_html(self) -> list[CourseData]:
        try:
            response = self._session.request("GET", "/my/")
        except Exception as e:
            logger.error(
                "Erro ao buscar dashboard via HTML",
                extra={"error": str(e)},
            )
            return []

        course_ids = set()
        for match in re.finditer(r'/course/view\.php\?id=(\d+)', response.text):
            course_ids.add(int(match.group(1)))

        if not course_ids:
            try:
                course_list_resp = self._session.request("GET", "/course/index.php")
                for match in re.finditer(r'/course/view\.php\?id=(\d+)', course_list_resp.text):
                    course_ids.add(int(match.group(1)))
            except Exception:
                pass

        if not course_ids:
            try:
                soup = BeautifulSoup(response.text, "lxml")
                course_select = soup.find("select", id="calendar-course-filter-1")
                if course_select:
                    for opt in course_select.find_all("option"):
                        val = opt.get("value", "")
                        if val and val.isdigit() and int(val) > 1:
                            course_ids.add(int(val))
            except Exception:
                pass

        courses = []
        for cid in course_ids:
            try:
                course_resp = self._session.request("GET", f"/course/view.php?id={cid}")
                parsed = self._html.parse_course_page(course_resp.text, cid)
                if parsed:
                    courses.append(parsed)
                else:
                    courses.append(CourseData(
                        course_id=cid,
                        fullname=f"Curso {cid}",
                        shortname=f"curso{cid}",
                    ))
            except Exception as e:
                logger.warning(
                    "Erro ao buscar curso individual HTML",
                    extra={"course_id": cid, "error": str(e)},
                )

        return courses

    def _extract_contents_html(self, course: CourseData) -> list[SectionData]:
        try:
            response = self._session.request(
                "GET",
                f"/course/view.php?id={course.course_id}",
            )
            parsed_course = self._html.parse_course_page(response.text, course.course_id)
            if parsed_course:
                return parsed_course.sections
            return []
        except Exception as e:
            logger.error(
                "Erro ao extrair conteúdo HTML do curso",
                extra={"course_id": course.course_id, "error": str(e)},
            )
            return []

    def _extract_activity_detail_html(self, activity: ActivityData) -> Optional[ActivityData]:
        try:
            response = self._session.request("GET", activity.url)
            parsed = self._html.parse_activity_page(response.text, activity.cmid)

            if parsed:
                parsed.cmid = activity.cmid
                parsed.type = activity.type
                if not parsed.url:
                    parsed.url = activity.url
                return parsed

            return activity
        except Exception as e:
            logger.debug(
                "Erro ao extrair detalhe da atividade via HTML",
                extra={"cmid": activity.cmid, "error": str(e)},
            )
            return activity
