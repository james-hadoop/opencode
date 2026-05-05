from .types import NodeRunStatus, WorkflowRunStatus, is_terminal_status, is_active_status
from .state_machine import StateMachine
from ..workflow.types import WorkflowDefinition, build_workflow_graph, get_ready_nodes
from ..db.repository import WorkflowRepository
from typing import Any, Callable
import uuid
from datetime import datetime


class WorkflowEngine:
    def __init__(self, repository: WorkflowRepository):
        self.repository = repository
        self.state_machine = StateMachine()
        self.subscribers: dict[str, list[Callable]] = {}

    async def create_run(self, workflow: WorkflowDefinition, triggered_by: str) -> str:
        run_id = f"run_{uuid.uuid4().hex[:16]}"
        graph = build_workflow_graph(workflow)

        state = {
            "run_id": run_id,
            "workflow_id": workflow.id,
            "status": "pending",
            "nodeRuns": {},
            "metadata": {
                "triggered_by": triggered_by,
                "created_at": int(datetime.now().timestamp() * 1000),
            },
        }

        for node_id in graph.nodes:
            state["nodeRuns"][node_id] = {
                "nodeId": node_id,
                "status": "pending",
                "attempts": 0,
            }

        await self.repository.save_run(run_id, workflow.id, state, triggered_by)
        await self._emit_event(run_id, {"type": "workflow.queued"})

        ready = get_ready_nodes(graph, set())
        for node_id in ready:
            await self._transition_node(run_id, node_id, "node.queued")

        return run_id

    async def get_snapshot(self, run_id: str) -> dict | None:
        return await self.repository.get_run(run_id)

    async def has_run(self, run_id: str) -> bool:
        return await self.repository.get_run(run_id) is not None

    async def poll_run(self, run_id: str) -> dict:
        state = await self.repository.get_run(run_id)
        if not state:
            return {"status": "not_found"}

        graph = build_workflow_graph(WorkflowDefinition(
            id=state["workflow_id"],
            name="",
            nodes=[],
            edges=[],
        ))

        waiting_nodes = [
            node_id for node_id, node_run in state["nodeRuns"].items()
            if node_run.get("status") == "waiting_callback"
        ]

        for node_id in waiting_nodes:
            await self._advance_node(run_id, node_id)

        return await self.repository.get_run(run_id)

    async def cancel_run(self, run_id: str) -> dict:
        state = await self.repository.get_run(run_id)
        if not state:
            return {"status": "not_found"}

        for node_id, node_run in state["nodeRuns"].items():
            if is_active_status(node_run.get("status", "")):
                node_run["status"] = "canceled"

        state["status"] = "canceled"
        await self.repository.update_run_state(run_id, state)
        await self._emit_event(run_id, {"type": "workflow.canceled"})

        return state

    async def timeout_run(self, run_id: str) -> dict:
        state = await self.repository.get_run(run_id)
        if not state:
            return {"status": "not_found"}

        now = int(datetime.now().timestamp() * 1000)

        for node_id, node_run in state["nodeRuns"].items():
            if node_run.get("status") == "running":
                active_since = node_run.get("activeSinceMs", 0)
                if now - active_since > 300000:
                    node_run["status"] = "timed_out"

        await self.repository.update_run_state(run_id, state)
        return state

    async def subscribe(self, run_id: str, callback: Callable):
        if run_id not in self.subscribers:
            self.subscribers[run_id] = []
        self.subscribers[run_id].append(callback)

    def unsubscribe(self, run_id: str, callback: Callable):
        if run_id in self.subscribers:
            self.subscribers[run_id].remove(callback)

    async def _transition_node(self, run_id: str, node_id: str, event_type: str):
        state = await self.repository.get_run(run_id)
        if not state:
            return

        node_run = state["nodeRuns"].get(node_id)
        if not node_run:
            return

        current_status = NodeRunStatus(node_run.get("status", "pending"))
        next_status = self.state_machine.get_node_next_status(current_status, event_type)

        if next_status:
            node_run["status"] = next_status.value
            if event_type == "node.started":
                node_run["activeSinceMs"] = int(datetime.now().timestamp() * 1000)

            await self.repository.update_run_state(run_id, state)
            await self._emit_event(run_id, {"type": event_type, "nodeId": node_id})

    async def _advance_node(self, run_id: str, node_id: str):
        state = await self.repository.get_run(run_id)
        if not state:
            return

        node_run = state["nodeRuns"].get(node_id)
        if not node_run or node_run.get("status") != "waiting_callback":
            return

        node_run["status"] = "succeeded"
        await self.repository.update_run_state(run_id, state)
        await self._emit_event(run_id, {"type": "node.succeeded", "nodeId": node_id})

    async def _emit_event(self, run_id: str, event: dict):
        state = await self.repository.get_run(run_id)
        if not state:
            return

        sequence = len(await self.repository.get_events(run_id))
        recorded_at = int(datetime.now().timestamp() * 1000)

        await self.repository.save_event(run_id, sequence, recorded_at, event)

        if run_id in self.subscribers:
            for callback in self.subscribers[run_id]:
                await callback(event)