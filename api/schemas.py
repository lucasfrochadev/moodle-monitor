from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now() -> str:
    return datetime.utcnow().isoformat()


# ─── Board ────────────────────────────────────────────────────────────────────

class BoardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = ""
    color: str = "#4A90D9"


class BoardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = None
    color: Optional[str] = None


class BoardOut(BaseModel):
    id: str
    name: str
    description: str
    color: str
    created_at: str
    updated_at: str


class BoardFull(BoardOut):
    columns: list["ColumnWithTasks"] = []


# ─── Column ───────────────────────────────────────────────────────────────────

class ColumnCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    color: str = "#E0E0E0"
    position: Optional[int] = None


class ColumnUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=80)
    color: Optional[str] = None
    position: Optional[int] = None


class ColumnOut(BaseModel):
    id: str
    board_id: str
    name: str
    position: int
    color: str
    created_at: str


class ColumnWithTasks(ColumnOut):
    tasks: list[TaskOut] = []


# ─── Task ─────────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    column_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    discipline: str = ""
    due_date: Optional[str] = None
    publication_date: Optional[str] = None
    status: str = "pending"
    priority: int = 0
    activity_url: str = ""


class TaskUpdate(BaseModel):
    column_id: Optional[str] = None
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    discipline: Optional[str] = None
    due_date: Optional[str] = None
    publication_date: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    position: Optional[int] = None
    archived: Optional[bool] = None
    activity_url: Optional[str] = None


class TaskMove(BaseModel):
    column_id: str
    position: Optional[int] = None


class TaskOut(BaseModel):
    id: str
    column_id: Optional[str]
    board_id: str
    title: str
    description: str
    discipline: str
    due_date: Optional[str]
    publication_date: Optional[str]
    status: str
    priority: int
    position: int
    activity_url: str
    archived: bool
    created_at: str
    updated_at: str
    source_course_name: str = ""
    source_activity_id: str = ""


# ─── Activity (imported) ──────────────────────────────────────────────────────

class ActivityImportOut(BaseModel):
    id: str
    task_id: str
    source_activity_id: str
    source_course_id: int
    source_course_name: str
    source_hash: str
    last_synced_at: str
    task: Optional[TaskOut] = None


# ─── Sync ─────────────────────────────────────────────────────────────────────

class SyncResult(BaseModel):
    imported: int = 0
    updated: int = 0
    errors: int = 0
    message: str = ""


# ─── Dashboard / Stats ────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_tasks: int = 0
    pending: int = 0
    in_progress: int = 0
    completed: int = 0
    overdue: int = 0
    archived: int = 0
    due_this_week: int = 0
    total_boards: int = 0
    total_activities_imported: int = 0


class VigentActivityOut(BaseModel):
    id: str
    title: str
    description: str
    discipline: str
    due_date: Optional[str]
    publication_date: Optional[str]
    status: str
    priority: int
    activity_url: str
    source_course_name: str
    days_until_due: Optional[int]
    is_overdue: bool = False


# ─── Reorder ──────────────────────────────────────────────────────────────────

class ReorderPayload(BaseModel):
    items: list[dict]  # [{"id": "...", "position": N}, ...]
