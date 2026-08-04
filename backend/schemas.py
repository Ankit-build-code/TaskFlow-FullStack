"""
Pydantic request/response schemas for TaskFlow.
Includes Field constraints and custom validators.
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, EmailStr


# ─────────────────────────── User ────────────────────────────

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank or whitespace-only")
        return v.strip()


class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    model_config = {"from_attributes": True}


# ─────────────────────────── Project ─────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    owner_id: int

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("project name must not be blank or whitespace-only")
        return v.strip()


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int

    model_config = {"from_attributes": True}


# ─────────────────────────── Task ────────────────────────────

VALID_PRIORITIES = {"low", "medium", "high"}
VALID_STATUSES = {"todo", "in_progress", "done"}


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    priority: str = Field(default="medium")
    due_date: Optional[str] = None
    status: str = Field(default="todo")
    project_id: int

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        """Reject blank/whitespace-only titles."""
        if not v.strip():
            raise ValueError("title must not be blank or whitespace-only")
        return v.strip()

    @field_validator("priority")
    @classmethod
    def priority_must_be_valid(cls, v: str) -> str:
        """Restrict priority to the closed set low/medium/high."""
        if v not in VALID_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(VALID_PRIORITIES)}")
        return v

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("title must not be blank or whitespace-only")
        return v.strip() if v else v

    @field_validator("priority")
    @classmethod
    def priority_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(VALID_PRIORITIES)}")
        return v

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return v


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    priority: str
    due_date: Optional[str]
    status: str
    project_id: int

    model_config = {"from_attributes": True}


# ─────────────────────── Statistics ──────────────────────────

class ProjectStats(BaseModel):
    project_id: int
    project_name: str
    total_tasks: int
    todo_count: int
    in_progress_count: int
    done_count: int


# ─────────────────────── Quick-Add ───────────────────────────

class QuickAddRequest(BaseModel):
    description: str = Field(..., min_length=1)
    project_id: int

    @field_validator("description")
    @classmethod
    def description_not_blank(cls, v: str) -> str:
        # Allow whitespace-only (the parser handles it → "Untitled task")
        return v
