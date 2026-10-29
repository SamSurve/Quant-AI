"""CLI Runner for the QuantAI Workflow Coordinator."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from tools.coordinator.coordinator import WorkflowCoordinator, DuplicateMessageError
from tools.coordinator.models import MilestoneStatus


def print_status(coordinator: WorkflowCoordinator) -> None:
    state = coordinator.state
    print("\n" + "=" * 60)
    print(f" QUANTAI WORKFLOW COORDINATOR — STATUS")
    print("=" * 60)
    print(f"Project:            {state.project_name}")
    print(f"Conversation:       {state.conversation_title}")
    print(f"URL:                {state.conversation_url}")
    print(f"Branch:             {state.expected_branch}")
    print(f"Active Milestone:   {state.active_milestone_id}")
    print(f"Active Task:        {state.active_task_id or 'None'}")
    print(f"Paused:             {state.is_paused} ({state.pause_reason or 'Running'})")
    print("-" * 60)
    print("MILESTONE ROADMAP:")
    for m in state.milestones:
        status_symbol = {
            MilestoneStatus.COMPLETED: " [x] COMPLETED",
            MilestoneStatus.IN_PROGRESS: " [>] ACTIVE   ",
            MilestoneStatus.PENDING: " [ ] PENDING  ",
            MilestoneStatus.BLOCKED: " [!] BLOCKED  ",
            MilestoneStatus.FAILED: " [X] FAILED   ",
        }.get(m.status, str(m.status))
        print(f" {m.id}: {status_symbol} — {m.title}")
    print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="QuantAI Workflow Coordinator CLI")
    parser.add_argument("--status", action="store_true", help="Display current coordinator and milestone status")
    parser.add_argument("--init", action="store_true", help="Reinitialize default state")
    parser.add_argument("--check-gate", type=str, help="Check if an action requires human approval")
    args = parser.parse_args()

    coordinator = WorkflowCoordinator()

    if args.init:
        coordinator.load_state()
        print("Coordinator state initialized.")
        print_status(coordinator)
        return

    if args.check_gate:
        requires_approval = coordinator.check_human_approval_gate(args.check_gate)
        print(f"Action '{args.check_gate}' -> Requires Human Approval: {requires_approval}")
        return

    # Default action: status
    print_status(coordinator)


if __name__ == "__main__":
    main()
