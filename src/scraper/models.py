"""
Modelos de dados do Moodle.
Representam a estrutura do portal acadêmico independente do storage interno.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Optional


class ActivityType(StrEnum):
    ASSIGN = "assign"
    QUIZ = "quiz"
    FORUM = "forum"
    RESOURCE = "resource"
    PAGE = "page"
    URL = "url"
    FOLDER = "folder"
    LESSON = "lesson"
    CHOICE = "choice"
    FEEDBACK = "feedback"
    GLOSSARY = "glossary"
    WIKI = "wiki"
    WORKSHOP = "workshop"
    UNKNOWN = "unknown"


@dataclass
class MoodleFile:
    filename: str
    file_url: str
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    mimetype: Optional[str] = None


@dataclass
class ActivityData:
    """Dados normalizados de uma atividade extraída do Moodle."""
    cmid: int
    instance_id: int
    type: ActivityType
    name: str
    url: str

    description: Optional[str] = None
    description_html: Optional[str] = None

    due_date: Optional[datetime] = None
    open_date: Optional[datetime] = None
    cutoff_date: Optional[datetime] = None

    max_grade: Optional[float] = None
    grade_pass: Optional[float] = None

    files: list[MoodleFile] = field(default_factory=list)

    section_id: Optional[int] = None
    section_name: Optional[str] = None
    section_position: Optional[int] = None

    completion_enabled: bool = False
    completion_expected: Optional[datetime] = None

    source: str = "api"


@dataclass
class CourseData:
    """Dados normalizados de um curso/disciplina."""
    course_id: int
    fullname: str
    shortname: str
    summary: Optional[str] = None
    category: Optional[str] = None
    url: Optional[str] = None
    sections: list = field(default_factory=list)


@dataclass
class SectionData:
    """Dados normalizados de uma seção/tópico de curso."""
    section_id: int
    name: str
    position: int
    summary: Optional[str] = None
    activities: list[ActivityData] = field(default_factory=list)
