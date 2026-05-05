from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from .models import WorkflowRun, WorkflowEvent, WorkflowDefinitionModel, Artifact
import json
from typing import Any
from datetime import datetime


class WorkflowRepository:
    def __init__(self, session_maker):
        self._session_maker = session_maker

    async def save_run(self, run_id: str, workflow_id: str, state: dict, triggered_by: str):
        now = int(datetime.now().timestamp() * 1000)
        run = WorkflowRun(
            run_id=run_id,
            workflow_id=workflow_id,
            status=state.get("status", "pending"),
            triggered_by=triggered_by,
            created_at=now,
            updated_at=now,
            state_json=json.dumps(state),
        )
        async with self._session_maker() as session:
            session.add(run)
            await session.commit()

    async def get_run(self, run_id: str) -> dict | None:
        async with self._session_maker() as session:
            result = await session.execute(
                select(WorkflowRun).where(WorkflowRun.run_id == run_id)
            )
            run = result.scalar_one_or_none()
            if run:
                return json.loads(run.state_json)
            return None

    async def update_run_state(self, run_id: str, state: dict):
        now = int(datetime.now().timestamp() * 1000)
        async with self._session_maker() as session:
            await session.execute(
                update(WorkflowRun)
                .where(WorkflowRun.run_id == run_id)
                .values(status=state.get("status", "pending"), state_json=json.dumps(state), updated_at=now)
            )
            await session.commit()

    async def delete_run(self, run_id: str):
        async with self._session_maker() as session:
            await session.execute(
                delete(WorkflowRun).where(WorkflowRun.run_id == run_id)
            )
            await session.commit()

    async def list_runs(self, limit: int = 100) -> list[dict]:
        async with self._session_maker() as session:
            result = await session.execute(
                select(WorkflowRun).order_by(WorkflowRun.created_at.desc()).limit(limit)
            )
            return [json.loads(run.state_json) for run in result.scalars()]

    async def save_event(self, run_id: str, sequence: int, recorded_at_ms: int, event: dict):
        event_record = WorkflowEvent(
            run_id=run_id,
            sequence=sequence,
            recorded_at_ms=recorded_at_ms,
            event_type=event.get("type", "unknown"),
            event_json=json.dumps(event),
        )
        async with self._session_maker() as session:
            session.add(event_record)
            await session.commit()

    async def get_events(self, run_id: str) -> list[dict]:
        async with self._session_maker() as session:
            result = await session.execute(
                select(WorkflowEvent)
                .where(WorkflowEvent.run_id == run_id)
                .order_by(WorkflowEvent.sequence)
            )
            return [json.loads(e.event_json) for e in result.scalars()]

    async def save_workflow(self, workflow: dict):
        now = datetime.now().isoformat()
        model = WorkflowDefinitionModel(
            id=workflow.get("id"),
            name=workflow.get("name", ""),
            description=workflow.get("description", ""),
            icon_json=json.dumps(workflow.get("icon", {})),
            nodes_json=json.dumps(workflow.get("nodes", [])),
            edges_json=json.dumps(workflow.get("edges", [])),
            settings_json=json.dumps(workflow.get("settings", {})),
            ownership_json=json.dumps(workflow.get("ownership", {})),
            status=workflow.get("status", "active"),
            created_at=workflow.get("created_at", now),
            updated_at=now,
        )
        async with self._session_maker() as session:
            session.add(model)
            await session.commit()

    async def get_workflow(self, workflow_id: str) -> dict | None:
        async with self._session_maker() as session:
            result = await session.execute(
                select(WorkflowDefinitionModel).where(WorkflowDefinitionModel.id == workflow_id)
            )
            wf = result.scalar_one_or_none()
            if wf:
                return {
                    "id": wf.id,
                    "name": wf.name,
                    "description": wf.description,
                    "icon": json.loads(wf.icon_json),
                    "nodes": json.loads(wf.nodes_json),
                    "edges": json.loads(wf.edges_json),
                    "settings": json.loads(wf.settings_json),
                    "ownership": json.loads(wf.ownership_json),
                    "status": wf.status,
                    "created_at": wf.created_at,
                    "updated_at": wf.updated_at,
                }
            return None

    async def list_workflows(self) -> list[dict]:
        async with self._session_maker() as session:
            result = await session.execute(
                select(WorkflowDefinitionModel).order_by(WorkflowDefinitionModel.updated_at.desc())
            )
            return [
                {
                    "id": wf.id,
                    "name": wf.name,
                    "description": wf.description,
                    "icon": json.loads(wf.icon_json),
                    "nodes": json.loads(wf.nodes_json),
                    "edges": json.loads(wf.edges_json),
                    "settings": json.loads(wf.settings_json),
                    "ownership": json.loads(wf.ownership_json),
                    "status": wf.status,
                    "created_at": wf.created_at,
                    "updated_at": wf.updated_at,
                }
                for wf in result.scalars()
            ]

    async def delete_workflow(self, workflow_id: str):
        async with self._session_maker() as session:
            await session.execute(
                delete(WorkflowDefinitionModel).where(WorkflowDefinitionModel.id == workflow_id)
            )
            await session.commit()


class ArtifactRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_artifact(self, artifact_id: str, run_id: str, node_id: str, path: str, size_bytes: int, content_type: str):
        now = int(datetime.now().timestamp() * 1000)
        artifact = Artifact(
            artifact_id=artifact_id,
            run_id=run_id,
            node_id=node_id,
            path=path,
            size_bytes=size_bytes,
            content_type=content_type,
            created_at=now,
        )
        self.session.add(artifact)
        await self.session.commit()

    async def get_artifact(self, artifact_id: str) -> dict | None:
        result = await self.session.execute(
            select(Artifact).where(Artifact.artifact_id == artifact_id)
        )
        a = result.scalar_one_or_none()
        if a:
            return {
                "artifact_id": a.artifact_id,
                "run_id": a.run_id,
                "node_id": a.node_id,
                "path": a.path,
                "size_bytes": a.size_bytes,
                "content_type": a.content_type,
                "created_at": a.created_at,
            }
        return None

    async def list_artifacts(self, run_id: str, node_id: str | None = None) -> list[dict]:
        query = select(Artifact).where(Artifact.run_id == run_id)
        if node_id:
            query = query.where(Artifact.node_id == node_id)
        result = await self.session.execute(query)
        return [
            {
                "artifact_id": a.artifact_id,
                "node_id": a.node_id,
                "path": a.path,
                "size_bytes": a.size_bytes,
                "content_type": a.content_type,
                "created_at": a.created_at,
            }
            for a in result.scalars()
        ]