"""Comprehensive test suite for QuantAI Workflow Coordinator."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from tools.coordinator.coordinator import WorkflowCoordinator, DuplicateMessageError
from tools.coordinator.models import MilestoneStatus, ReviewDecision, TaskStatus


class TestWorkflowCoordinator(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.state_file = Path(self.test_dir) / "test_state.json"
        self.coordinator = WorkflowCoordinator(state_path=self.state_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_initial_state(self):
        state = self.coordinator.state
        self.assertEqual(state.active_milestone_id, "M03")
        self.assertEqual(state.active_task_id, "QAI-M03-BRIDGE-001")
        self.assertEqual(len(state.milestones), 10)
        self.assertEqual(state.milestones[0].status, MilestoneStatus.COMPLETED)
        self.assertEqual(state.milestones[1].status, MilestoneStatus.COMPLETED)
        self.assertEqual(state.milestones[2].status, MilestoneStatus.IN_PROGRESS)

    def test_pass_next_milestone_advancement(self):
        response = """
        Review complete!
        Decision: PASS_NEXT_MILESTONE
        Great work on Milestone 3.

        NEXT_TASK_BEGIN
        TASK ID: QAI-UI-REDESIGN-001
        MILESTONE ID: M04
        Implement the responsive QuantAI UI redesign.
        NEXT_TASK_END
        """
        decision, next_prompt = self.coordinator.process_review_response(response)
        self.assertEqual(decision, ReviewDecision.PASS_NEXT_MILESTONE)
        self.assertIn("Implement the responsive QuantAI UI redesign", next_prompt)
        
        # Verify M03 completed and M04 active
        self.assertEqual(self.coordinator.state.milestones[2].status, MilestoneStatus.COMPLETED)
        self.assertEqual(self.coordinator.state.milestones[3].status, MilestoneStatus.IN_PROGRESS)
        self.assertEqual(self.coordinator.state.active_milestone_id, "M04")
        self.assertEqual(self.coordinator.state.active_task_id, "QAI-UI-REDESIGN-001")
        self.assertFalse(self.coordinator.state.is_paused)

    def test_retry_logic_and_limit_exhaustion(self):
        retry_response_1 = "Decision: RETRY_CURRENT_MILESTONE\nPlease fix unit test assertion."
        self.coordinator.process_review_response(retry_response_1)
        
        task = next(t for t in self.coordinator.state.tasks_history if t.task_id == "QAI-M03-BRIDGE-001")
        self.assertEqual(task.retries, 1)
        self.assertEqual(task.status, TaskStatus.RETRY_PENDING)
        self.assertFalse(self.coordinator.state.is_paused)

        retry_response_2 = "Decision: RETRY_CURRENT_MILESTONE\nPlease fix typing issue."
        self.coordinator.process_review_response(retry_response_2)
        self.assertEqual(task.retries, 2)
        self.assertFalse(self.coordinator.state.is_paused)

        retry_response_3 = "Decision: RETRY_CURRENT_MILESTONE\nStill failing."
        self.coordinator.process_review_response(retry_response_3)
        self.assertEqual(task.retries, 3)
        self.assertEqual(task.status, TaskStatus.BLOCKED)
        self.assertTrue(self.coordinator.state.is_paused)
        self.assertIn("Exceeded max retry attempts", self.coordinator.state.pause_reason)

    def test_stop_on_human_approval_required(self):
        response = "Decision: HUMAN_APPROVAL_REQUIRED\nScope change requires human review."
        decision, _ = self.coordinator.process_review_response(response)
        self.assertEqual(decision, ReviewDecision.HUMAN_APPROVAL_REQUIRED)
        self.assertTrue(self.coordinator.state.is_paused)
        self.assertIn("HUMAN_APPROVAL_REQUIRED", self.coordinator.state.pause_reason)

    def test_duplicate_message_rejection(self):
        response = "Decision: PASS_NEXT_MILESTONE\nGood."
        self.coordinator.process_review_response(response)
        
        # Second time should raise DuplicateMessageError
        with self.assertRaises(DuplicateMessageError):
            self.coordinator.process_review_response(response)

    def test_persistence_and_recovery(self):
        response = """
        Decision: PASS_NEXT_MILESTONE
        NEXT_TASK_BEGIN
        TASK ID: QAI-UI-REDESIGN-001
        NEXT_TASK_END
        """
        self.coordinator.process_review_response(response)

        # Reload a new coordinator instance pointing to the same file
        recovered = WorkflowCoordinator(state_path=self.state_file)
        self.assertEqual(recovered.state.active_milestone_id, "M04")
        self.assertEqual(recovered.state.active_task_id, "QAI-UI-REDESIGN-001")
        self.assertEqual(recovered.state.milestones[2].status, MilestoneStatus.COMPLETED)

    def test_human_approval_gates(self):
        self.assertTrue(self.coordinator.check_human_approval_gate("deploy to production"))
        self.assertTrue(self.coordinator.check_human_approval_gate("git force-push origin main"))
        self.assertTrue(self.coordinator.check_human_approval_gate("merge to main"))
        self.assertFalse(self.coordinator.check_human_approval_gate("run local unit tests"))
        self.assertFalse(self.coordinator.check_human_approval_gate("update frontend styles"))

    def test_blocked_decision_processing(self):
        response = "Decision: BLOCKED\nAccess to external API is permanently restricted."
        decision, _ = self.coordinator.process_review_response(response)
        self.assertEqual(decision, ReviewDecision.BLOCKED)
        self.assertTrue(self.coordinator.state.is_paused)
        self.assertIn("BLOCKED", self.coordinator.state.pause_reason)
        current_m = next(m for m in self.coordinator.state.milestones if m.id == "M03")
        self.assertEqual(current_m.status, MilestoneStatus.BLOCKED)

    def test_project_complete_decision_processing(self):
        response = "Decision: PROJECT_COMPLETE\nAll acceptance criteria met for final release."
        decision, _ = self.coordinator.process_review_response(response)
        self.assertEqual(decision, ReviewDecision.PROJECT_COMPLETE)
        self.assertTrue(self.coordinator.state.is_paused)
        self.assertIn("Project complete", self.coordinator.state.pause_reason)

    def test_invalid_decision_rejection(self):
        invalid_response = "Looks okay, maybe proceed if you want."
        with self.assertRaises(ValueError):
            self.coordinator.process_review_response(invalid_response)
        self.assertTrue(self.coordinator.state.is_paused)
        self.assertIn("No valid review decision", self.coordinator.state.pause_reason)

    def test_atomic_state_save(self):
        # Verify that state file exists and tmp file is removed after save
        self.coordinator.save_state()
        self.assertTrue(self.state_file.exists())
        tmp_file = self.state_file.with_suffix(".tmp")
        self.assertFalse(tmp_file.exists())
        # Verify content parses as valid JSON
        data = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.assertEqual(data["active_milestone_id"], "M03")


if __name__ == "__main__":
    unittest.main()
