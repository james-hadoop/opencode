from .types import NodeRunStatus, WorkflowRunStatus, is_terminal_status, is_active_status
from typing import Any


class StateMachine:
    @staticmethod
    def get_node_next_status(current_status: NodeRunStatus, event_type: str) -> NodeRunStatus | None:
        transitions = {
            ("pending", "node.queued"): NodeRunStatus.QUEUED,
            ("queued", "node.started"): NodeRunStatus.RUNNING,
            ("running", "node.succeeded"): NodeRunStatus.SUCCEEDED,
            ("running", "node.failed"): NodeRunStatus.FAILED,
            ("running", "node.canceled"): NodeRunStatus.CANCELED,
            ("running", "node.timed_out"): NodeRunStatus.TIMED_OUT,
            ("running", "node.waiting"): NodeRunStatus.WAITING_CALLBACK,
            ("waiting_callback", "node.succeeded"): NodeRunStatus.SUCCEEDED,
            ("waiting_callback", "node.failed"): NodeRunStatus.FAILED,
            ("waiting_callback", "node.canceled"): NodeRunStatus.CANCELED,
            ("failed", "node.retry_scheduled"): NodeRunStatus.QUEUED,
        }
        return transitions.get((current_status.value, event_type))

    @staticmethod
    def get_workflow_next_status(current_status: WorkflowRunStatus, event_type: str) -> WorkflowRunStatus | None:
        transitions = {
            ("pending", "workflow.queued"): WorkflowRunStatus.QUEUED,
            ("pending", "workflow.started"): WorkflowRunStatus.RUNNING,
            ("queued", "workflow.started"): WorkflowRunStatus.RUNNING,
            ("running", "workflow.completed"): WorkflowRunStatus.SUCCEEDED,
            ("running", "workflow.failed"): WorkflowRunStatus.FAILED,
            ("running", "workflow.canceled"): WorkflowRunStatus.CANCELED,
            ("running", "workflow.timed_out"): WorkflowRunStatus.TIMED_OUT,
        }
        return transitions.get((current_status.value, event_type))

    @staticmethod
    def is_node_complete(status: NodeRunStatus) -> bool:
        return status in (
            NodeRunStatus.SUCCEEDED,
            NodeRunStatus.FAILED,
            NodeRunStatus.CANCELED,
            NodeRunStatus.TIMED_OUT,
        )

    @staticmethod
    def is_workflow_complete(status: WorkflowRunStatus) -> bool:
        return status in (
            WorkflowRunStatus.SUCCEEDED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELED,
            WorkflowRunStatus.TIMED_OUT,
        )