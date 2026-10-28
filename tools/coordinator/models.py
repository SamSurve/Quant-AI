"""Data models for QuantAI 10-Milestone Workflow Coordinator."""

from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class MilestoneStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class ReviewDecision(str, Enum):
    PASS_NEXT_MILESTONE = "PASS_NEXT_MILESTONE"
    RETRY_CURRENT_MILESTONE = "RETRY_CURRENT_MILESTONE"
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
    BLOCKED = "BLOCKED"
    PROJECT_COMPLETE = "PROJECT_COMPLETE"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    VERIFIED = "VERIFIED"
    REPORTED = "REPORTED"
    ACCEPTED = "ACCEPTED"
    RETRY_PENDING = "RETRY_PENDING"
    BLOCKED = "BLOCKED"


class MilestoneInfo(BaseModel):
    id: str  # e.g. "M01", "M02", ..., "M10"
    title: str
    status: MilestoneStatus = MilestoneStatus.PENDING
    accepted_task_id: Optional[str] = None
    notes: Optional[str] = None


class TaskRecord(BaseModel):
    milestone_id: str
    task_id: str
    iteration: int = 1
    status: TaskStatus = TaskStatus.PENDING
    prompt: Optional[str] = None
    report: Optional[str] = None
    review_decision: Optional[ReviewDecision] = None
    review_response: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    created_at: str = ""
    updated_at: str = ""


class CoordinatorState(BaseModel):
    protocol_version: str = "1.0"
    project_name: str = "QuantAI Finance Agent"
    conversation_url: str = "https://chatgpt.com/c/6ae258f2-6168-83ee-8176-d53b6af3f39f"
    conversation_title: str = "GitHub Project Confirmation"
    expected_branch: str = "python-first-refactor"
    active_milestone_id: str = "M03"
    active_task_id: Optional[str] = "QAI-M03-BRIDGE-001"
    is_paused: bool = False
    pause_reason: Optional[str] = None
    milestones: List[MilestoneInfo] = Field(default_factory=list)
    tasks_history: List[TaskRecord] = Field(default_factory=list)
    processed_message_hashes: List[str] = Field(default_factory=list)
