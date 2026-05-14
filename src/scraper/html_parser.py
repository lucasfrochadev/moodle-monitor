"""
Parser de HTML do Moodle usando BeautifulSoup + lxml.
Extrai dados estruturados de páginas HTML quando a API não está disponível.
"""

import logging
import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup, Tag

from src.scraper.models import (
    ActivityData,
    ActivityType,
    CourseData,
    MoodleFile,
    SectionData,
)

logger = logging.getLogger("moodle_monitor.scraper.html")


class MoodleHTMLParser:
    """Parser de HTML para páginas do Moodle usando seletores CSS estáveis."""

    # Seletores estáveis identificados no Moodle 3.x-4.x
    COURSE_SECTION_SELECTOR = "li.section"
    ACTIVITY_SELECTOR = "li.activity"
    ACTIVITY_INSTANCE_SELECTOR = "div.activityinstance"
    INSTANCE_NAME_SELECTOR = "span.instancename"
    SECTION_NAME_SELECTOR = "h3.sectionname"
    BREADCRUMB_SELECTOR = "nav.breadcrumb ol.breadcrumb li"
    CONTENT_SELECTOR = "div.no-overflow"

    def parse_course_page(self, html: str, course_id: int) -> Optional[CourseData]:
        soup = BeautifulSoup(html, "lxml")

        fullname = self._extract_course_name(soup)
        if not fullname:
            logger.warning("Não foi possível extrair nome do curso da página")
            return None

        shortname = self._extract_shortname(soup) or fullname
        sections = self._parse_sections(soup, course_id)

        return CourseData(
            course_id=course_id,
            fullname=fullname,
            shortname=shortname,
            sections=sections,
        )

    def parse_activity_page(self, html: str, cmid: int) -> Optional[ActivityData]:
        soup = BeautifulSoup(html, "lxml")

        name = self._extract_activity_name(soup)
        if not name:
            return None

        description_html = self._extract_description_html(soup)
        description_text = self._clean_html(description_html) if description_html else None

        activity_type = self._detect_activity_type(soup)
        instance_id = self._extract_instance_id(soup)
        url = f"/mod/{activity_type}/view.php?id={cmid}"

        return ActivityData(
            cmid=cmid,
            instance_id=instance_id or 0,
            type=activity_type,
            name=name,
            url=url,
            description=description_text,
            description_html=description_html,
            due_date=self._extract_due_date(soup),
            open_date=self._extract_open_date(soup),
            files=self._extract_files(soup),
            source="html",
        )

    def parse_assign_page(self, html: str, cmid: int) -> Optional[ActivityData]:
        return self.parse_activity_page(html, cmid)

    def parse_resource_page(self, html: str, cmid: int) -> Optional[ActivityData]:
        soup = BeautifulSoup(html, "lxml")

        name = self._extract_activity_name(soup)
        if not name:
            return None

        files = self._extract_files(soup)
        description_html = self._extract_description_html(soup)
        description_text = self._clean_html(description_html) if description_html else None

        return ActivityData(
            cmid=cmid,
            instance_id=0,
            type=ActivityType.RESOURCE,
            name=name,
            url=f"/mod/resource/view.php?id={cmid}",
            description=description_text,
            files=files,
            source="html",
        )

    def _parse_sections(self, soup: BeautifulSoup, course_id: int) -> list[SectionData]:
        sections = []
        section_elements = soup.select(self.COURSE_SECTION_SELECTOR)

        for idx, sec_el in enumerate(section_elements):
            section_name_el = sec_el.select_one(self.SECTION_NAME_SELECTOR)
            section_name = section_name_el.get_text(strip=True) if section_name_el else f"Tópico {idx + 1}"

            section_id_match = re.search(r"section-(\d+)", sec_el.get("id", ""))
            section_id = int(section_id_match.group(1)) if section_id_match else idx

            activities = self._parse_activities_in_section(sec_el)

            sections.append(SectionData(
                section_id=section_id,
                name=section_name,
                position=idx,
                activities=activities,
            ))

        return sections

    def _parse_activities_in_section(self, section_element: Tag) -> list[ActivityData]:
        activities = []
        activity_elements = section_element.select(self.ACTIVITY_SELECTOR)

        for act_el in activity_elements:
            activity = self._parse_single_activity(act_el)
            if activity:
                activities.append(activity)

        return activities

    def _parse_single_activity(self, element: Tag) -> Optional[ActivityData]:
        instance_el = element.select_one(self.ACTIVITY_INSTANCE_SELECTOR)
        if not instance_el:
            return None

        link_el = instance_el.find("a") if isinstance(instance_el, Tag) else None
        if not link_el:
            return None

        name_el = link_el.select_one(self.INSTANCE_NAME_SELECTOR)
        if not name_el:
            return None

        name = name_el.get_text(strip=True).replace("￼", "").strip()

        href = link_el.get("href", "")
        if isinstance(href, list):
            href = href[0] if href else ""

        cmid = self._extract_cmid_from_url(str(href))

        mod_classes = element.get("class", [])
        activity_type = self._detect_type_from_classes(mod_classes)

        return ActivityData(
            cmid=cmid or 0,
            instance_id=0,
            type=activity_type,
            name=name,
            url=str(href),
            source="html",
        )

    def _extract_course_name(self, soup: BeautifulSoup) -> Optional[str]:
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        breadcrumb = soup.select_one(self.BREADCRUMB_SELECTOR)
        if breadcrumb:
            items = soup.select(self.BREADCRUMB_SELECTOR)
            if items:
                return items[-1].get_text(strip=True)

        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
            parts = re.split(r"[/|]", title)
            return parts[0].strip() if parts else title

        return None

    def _extract_shortname(self, soup: BeautifulSoup) -> Optional[str]:
        match = re.search(
            r'courseShortname["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            soup.text,
        )
        if match:
            return match.group(1)
        return None

    def _extract_activity_name(self, soup: BeautifulSoup) -> Optional[str]:
        h2 = soup.find("h2")
        if h2:
            text = h2.get_text(strip=True)
            if text:
                return text

        title = soup.find("title")
        if title:
            full = title.get_text(strip=True)
            parts = re.split(r"[/|]", full)
            if len(parts) >= 2:
                return parts[-2].strip()
            return parts[0].strip()

        return None

    def _extract_description_html(self, soup: BeautifulSoup) -> Optional[str]:
        content_div = soup.select_one(self.CONTENT_SELECTOR)
        if content_div:
            return str(content_div)

        desc_div = soup.select_one("div.description")
        if desc_div:
            return str(desc_div)

        intro_div = soup.select_one("div.activityintro")
        if intro_div:
            return str(intro_div)

        return None

    def _extract_due_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        texts = ["Data de entrega", "Due date", "Vencimento", "Prazo final"]
        return self._find_date_after_text(soup, texts)

    def _extract_open_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        texts = ["Disponível a partir de", "Abrir", "Open", "Data de abertura"]
        return self._find_date_after_text(soup, texts)

    def _extract_instance_id(self, soup: BeautifulSoup) -> Optional[int]:
        for script in soup.find_all("script"):
            if script.string:
                match = re.search(r'instance["\']?\s*[:=]\s*(\d+)', script.string)
                if match:
                    return int(match.group(1))

        for input_tag in soup.find_all("input", {"type": "hidden"}):
            name = input_tag.get("name", "")
            if "instance" in name.lower():
                val = input_tag.get("value", "")
                try:
                    return int(val)
                except (ValueError, TypeError):
                    pass

        return None

    def _extract_files(self, soup: BeautifulSoup) -> list[MoodleFile]:
        files = []
        for link in soup.find_all("a", href=re.compile(r"pluginfile.php", re.I)):
            href = link.get("href", "")
            filename = link.get_text(strip=True) or href.split("/")[-1]

            files.append(MoodleFile(
                filename=filename,
                file_url=str(href),
            ))

        for link in soup.find_all("a", href=re.compile(r"mod/resource/view", re.I)):
            href = link.get("href", "")
            filename = link.get_text(strip=True) or href.split("?")[0].split("/")[-1]

            files.append(MoodleFile(
                filename=filename,
                file_url=str(href),
            ))

        return files

    def _extract_cmid_from_url(self, url: str) -> Optional[int]:
        match = re.search(r"[?&]id=(\d+)", url)
        if match:
            return int(match.group(1))
        return None

    def _detect_activity_type(self, soup: BeautifulSoup) -> ActivityType:
        body_classes = soup.find("body").get("class", []) if soup.find("body") else []
        for cls in body_classes:
            for at in ActivityType:
                if at.value in str(cls):
                    return at

        url_path = ""
        for link in soup.find_all("link"):
            pass

        for script in soup.find_all("script"):
            if script.string:
                match = re.search(r'currentmodule["\']?\s*[:=]\s*["\']?(\w+)', script.string)
                if match:
                    mod = match.group(1).lower()
                    if mod in ActivityType:
                        return ActivityType(mod)

        return ActivityType.UNKNOWN

    def _detect_type_from_classes(self, classes) -> ActivityType:
        class_str = " ".join(str(c) for c in classes) if classes else ""
        for at in ActivityType:
            if at.value in class_str:
                return at
        return ActivityType.UNKNOWN

    def _find_date_after_text(
        self, soup: BeautifulSoup, label_texts: list[str]
    ) -> Optional[datetime]:
        for text in label_texts:
            pattern = re.compile(re.escape(text), re.IGNORECASE)
            for element in soup.find_all(string=pattern):
                parent = element.parent
                if parent:
                    next_text = parent.find_next(string=True)
                    if next_text:
                        dates = self._extract_dates(str(next_text))
                        if dates:
                            return dates[0]

                    sibling = parent.find_next_sibling()
                    if sibling:
                        dates = self._extract_dates(sibling.get_text())
                        if dates:
                            return dates[0]

        for text in label_texts:
            pattern = re.compile(
                rf"{re.escape(text)}[:\s]*(\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}}[:\s]*\d{{1,2}}:\d{{2}})",
                re.IGNORECASE,
            )
            match = pattern.search(soup.text)
            if match:
                dates = self._extract_dates(match.group(0))
                if dates:
                    return dates[0]

        return None

    def _extract_dates(self, text: str) -> list[datetime]:
        formats = [
            r"(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})",
            r"(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})",
            r"(\d{1,2})/(\d{1,2})/(\d{2})\s+(\d{1,2}):(\d{2})",
            r"(\d{1,2}) de (\w+) de (\d{4}),\s+(\d{1,2}):(\d{2})",
        ]

        results = []
        for fmt in formats:
            for match in re.finditer(fmt, text):
                try:
                    if fmt == formats[3]:
                        month_map = {
                            "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
                            "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
                            "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
                        }
                        month = month_map.get(match.group(2).lower(), 1)
                        dt = datetime(
                            int(match.group(3)),
                            month,
                            int(match.group(1)),
                            int(match.group(4)),
                            int(match.group(5)),
                        )
                    else:
                        dt = datetime(
                            int(match.group(3)),
                            int(match.group(2)),
                            int(match.group(1)),
                            int(match.group(4)),
                            int(match.group(5)),
                        )
                    results.append(dt)
                except (ValueError, IndexError):
                    continue

        return results

    def _clean_html(self, html: str) -> str:
        if not html:
            return ""
        soup = BeautifulSoup(html, "lxml")

        for tag in soup.find_all(["script", "style", "meta", "link"]):
            tag.decompose()

        for tag in soup.find_all(attrs={"onclick": True}):
            del tag["onclick"]
        for tag in soup.find_all(attrs={"onload": True}):
            del tag["onload"]
        for tag in soup.find_all(attrs={"onchange": True}):
            del tag["onchange"]

        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
