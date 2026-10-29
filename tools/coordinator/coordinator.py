"""Core Workflow Coordinator for the QuantAI 10-Milestone Development Loop."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import re
from typing import Optional, Tuple

from .models import (
    CoordinatorState,
    MilestoneInfo,
    MilestoneStatus,
    ReviewDecision,
    TaskRecord,
    TaskStatus,
)

ROOT_DIR = Path(__file__).resolve().parents[2]
COORDINATOR_DIR = Path(__file__).resolve().parent
STATE_FILE = COORDINATOR_DIR / "state.json"
AUDIT_LOG_FILE = COORDINATOR_DIR / "audit.log"

logging.basicConfig(
    filename=str(AUDIT_LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("coordinator")


def get_default_milestones() -> list[MilestoneInfo]:
    return [
        MilestoneInfo(id="M01", title="Project baseline and preservation", status=MilestoneStatus.COMPLETED, accepted_task_id="QAI-BASELINE-000", notes="Preservation audit complete"),
        MilestoneInfo(id="M02", title="Core backend reliability", status=MilestoneStatus.COMPLETED, accepted_task_id="QAI-BASELINE-001", notes="Standalone scripts verified, pytest collected 0 diagnosed"),
        MilestoneInfo(id="M03", title="ChatGPT–Antigravity coordinator", status=MilestoneStatus.IN_PROGRESS, accepted_task_id=None, notes="Workflow coordinator verification & implementation"),
        MilestoneInfo(id="M04", title="Responsive QuantAI UI redesign", status=MilestoneStatus.PENDING),
        MilestoneInfo(id="M05", title="Integration, accessibility and performance", status=MilestoneStatus.PENDING),
        MilestoneInfo(id="M06", title="Git reconciliation and release preparation", status=MilestoneStatus.PENDING),
        MilestoneInfo(id="M07", title="Vercel routing, access and domain", status=MilestoneStatus.PENDING),
        MilestoneInfo(id="M08", title="Live provider and end-to-end verification", status=MilestoneStatus.PENDING),
        MilestoneInfo(id="M09", title="Automation reliability hardening", status=MilestoneStatus.PENDING),
        MilestoneInfo(id="M10", title="Final acceptance and documentation", status=MilestoneStatus.PENDING),
    ]


class DuplicateMessageError(Exception):
    """Raised when an identical message is re-processed."""
    pass


class ApprovalRequiredError(Exception):
    """Raised when an operation requires explicit human approval."""
    pass


class WorkflowCoordinator:
    """Manages milestone lifecycle, task tracking, and ChatGPT message validation."""

    def __init__(self, state_path: Path = STATE_FILE):
        self.state_path = state_path
        self.state = self.load_state()

    def load_state(self) -> CoordinatorState:
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                return CoordinatorState.model_validate(data)
            except Exception as e:
                logger.error(f"Failed to load state: {e}. Reinitializing with defaults.")
        
        # Initialize default state
        state = CoordinatorState(
            milestones=get_default_milestones(),
            active_milestone_id="M03",
            active_task_id="QAI-M03-BRIDGE-001",
        )
        self.save_state(state)
        return state

    def save_state(self, state: Optional[CoordinatorState] = None) -> None:
        if state is not None:
            self.state = state
        tmp_file = self.state_path.with_suffix(".tmp")
        tmp_file.write_text(self.state.model_dump_json(indent=2), encoding="utf-8")
        tmp_file.replace(self.state_path)
        logger.info(f"State saved. Active Milestone: {self.state.active_milestone_id}, Task: {self.state.active_task_id}")

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()

    def record_message(self, content: str) -> str:
        msg_hash = self.compute_hash(content)
        if msg_hash in self.state.processed_message_hashes:
            logger.warning(f"Duplicate message detected with hash {msg_hash[:8]}")
            raise DuplicateMessageError(f"Message hash {msg_hash[:8]} has already been processed.")
        self.state.processed_message_hashes.append(msg_hash)
        self.save_state()
        return msg_hash

    @staticmethod
    def extract_decision(response_text: str) -> Optional[ReviewDecision]:
        match = re.search(r"Decision:\s*(PASS_NEXT_MILESTONE|RETRY_CURRENT_MILESTONE|HUMAN_APPROVAL_REQUIRED|BLOCKED|PROJECT_COMPLETE)", response_text, re.IGNORECASE)
        if match:
            decision_str = match.group(1).upper()
            return ReviewDecision(decision_str)
        # Check for fallback decision patterns
        for decision in ReviewDecision:
            if decision.value in response_text:
                return decision
        return None

    @staticmethod
    def extract_next_task(response_text: str) -> Optional[str]:
        match = re.search(r"NEXT_TASK_BEGIN\s*(.*?)\s*NEXT_TASK_END", response_text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def check_human_approval_gate(self, action_name: str, details: str = "") -> bool:
        """Determines if an action requires explicit human approval before execution."""
        restricted_keywords = [
            "deploy",
            "production deployment",
            "force push",
            "force-push",
            "merge main",
            "merge to main",
            "reset --hard",
            "secret",
            "credential",
            "api_key",
            "paid service",
        ]
        action_lower = f"{action_name} {details}".lower()
        for kw in restricted_keywords:
            if kw in action_lower:
                logger.warning(f"Human approval required for action: {action_name} ({details})")
                self.state.is_paused = True
                self.state.pause_reason = f"Human approval required: {action_name}"
                self.save_state()
                return True
        return False

    def process_review_response(self, response_text: str) -> Tuple[ReviewDecision, Optional[str]]:
        """Processes ChatGPT's review response, updates milestone/task status, and determines next action."""
        # Check duplicate
        msg_hash = self.compute_hash(response_text)
        if msg_hash in self.state.processed_message_hashes:
            logger.warning(f"Duplicate review response received: {msg_hash[:8]}")
            raise DuplicateMessageError("Duplicate review response received.")
        self.state.processed_message_hashes.append(msg_hash)

        decision = self.extract_decision(response_text)
        if not decision:
            logger.error("No valid review decision found in ChatGPT response.")
            self.state.is_paused = True
            self.state.pause_reason = "No valid review decision found in response."
            self.save_state()
            raise ValueError("Response does not contain a valid ReviewDecision.")

        next_task_prompt = self.extract_next_task(response_text)
        now_str = datetime.now(timezone.utc).isoformat()

        logger.info(f"Processing Review Decision: {decision.value} for milestone {self.state.active_milestone_id}")

        current_milestone = next((m for m in self.state.milestones if m.id == self.state.active_milestone_id), None)
        active_task = next((t for t in self.state.tasks_history if t.task_id == self.state.active_task_id), None)

        if not active_task and self.state.active_task_id:
            active_task = TaskRecord(
                milestone_id=self.state.active_milestone_id,
                task_id=self.state.active_task_id,
                created_at=now_str,
            )
            self.state.tasks_history.append(active_task)

        if active_task:
            active_task.review_decision = decision
            active_task.review_response = response_text
            active_task.updated_at = now_str

        if decision == ReviewDecision.PASS_NEXT_MILESTONE:
            if current_milestone:
                current_milestone.status = MilestoneStatus.COMPLETED
                current_milestone.accepted_task_id = self.state.active_task_id

            # Advance to next milestone
            current_idx = next((i for i, m in enumerate(self.state.milestones) if m.id == self.state.active_milestone_id), -1)
            if current_idx >= 0 and current_idx + 1 < len(self.state.milestones):
                next_milestone = self.state.milestones[current_idx + 1]
                next_milestone.status = MilestoneStatus.IN_PROGRESS
                self.state.active_milestone_id = next_milestone.id
                
                # Extract task ID from next_task_prompt if available
                if next_task_prompt:
                    task_id_match = re.search(r"TASK ID:\s*([A-Za-z0-9_\-]+)", next_task_prompt)
                    self.state.active_task_id = task_id_match.group(1) if task_id_match else f"QAI-{next_milestone.id}-001"
                else:
                    self.state.active_task_id = f"QAI-{next_milestone.id}-001"
                
                logger.info(f"Advanced to Milestone {next_milestone.id}: {next_milestone.title} (Task: {self.state.active_task_id})")
            else:
                self.state.active_milestone_id = "ALL_COMPLETED"
                self.state.active_task_id = None
                self.state.is_paused = True
                self.state.pause_reason = "All 10 milestones completed."
                logger.info("All 10 milestones have been completed successfully.")

        elif decision == ReviewDecision.RETRY_CURRENT_MILESTONE:
            if active_task:
                active_task.retries += 1
                if active_task.retries >= active_task.max_retries:
                    active_task.status = TaskStatus.BLOCKED
                    if current_milestone:
                        current_milestone.status = MilestoneStatus.BLOCKED
                    self.state.is_paused = True
                    self.state.pause_reason = f"Exceeded max retry attempts ({active_task.max_retries}) for task {active_task.task_id}."
                    logger.error(self.state.pause_reason)
                else:
                    active_task.status = TaskStatus.RETRY_PENDING
                    logger.warning(f"Retry requested for {active_task.task_id}. Attempt {active_task.retries} of {active_task.max_retries}")

        elif decision in (ReviewDecision.HUMAN_APPROVAL_REQUIRED, ReviewDecision.BLOCKED):
            self.state.is_paused = True
            self.state.pause_reason = f"Review requested stop: {decision.value}"
            if current_milestone and decision == ReviewDecision.BLOCKED:
                current_milestone.status = MilestoneStatus.BLOCKED
            logger.warning(f"Workflow paused: {self.state.pause_reason}")

        elif decision == ReviewDecision.PROJECT_COMPLETE:
            self.state.is_paused = True
            self.state.pause_reason = "Project complete acknowledged by reviewer."
            logger.info("Project completed.")

        self.save_state()
        return decision, next_task_prompt
