from enum import Enum
from typing import Any


class NodeRunStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_CALLBACK = "waiting_callback"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    TIMED_OUT = "timed_out"


class WorkflowRunStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    TIMED_OUT = "timed_out"


class NodeFailureCategory(str, Enum):
    UNKNOWN = "unknown"
    USER_ERROR = "user_error"
    NETWORK_ERROR = "network_error"
    PROTOCOL_ERROR = "protocol_error"
    TIMEOUT = "timeout"
    RUNTIME_ERROR = "runtime_error"


def is_terminal_status(status: str) -> bool:
    return status in ("succeeded", "failed", "canceled", "timed_out")


def is_active_status(status: str) -> bool:
    return status in ("pending", "queued", "running", "waiting_callback")