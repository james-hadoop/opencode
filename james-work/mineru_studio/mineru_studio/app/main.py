from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Any, Optional
import json
from datetime import datetime
import uuid

from mineru_studio.orchestrator.engine import WorkflowEngine
from mineru_studio.orchestrator.types import is_terminal_status
from mineru_studio.workflow.types import WorkflowDefinition, WorkflowNodeInput, WorkflowEdge
from mineru_studio.runtime.adapters import RuntimeRegistry, CodeNodeAdapter, ShellNodeAdapter, RemoteHttpNodeAdapter
from mineru_studio.app.tool_service import MockToolService, HelpFaq, HelpDoc, PlatformTool, ToolRepoSource, AiOrchestratorConfig
from mineru_studio.app.auth import auth_service, UserContext, TokenResponse, LoginRequest
from mineru_studio.app.artifact_storage import artifact_storage


security = HTTPBearer(auto_error=False)

app = FastAPI(title="MinerU Studio API")


@app.get("/")
async def root():
    return {"message": "MinerU Studio API", "version": "1.0.0", "docs": "/docs"}


tool_service = MockToolService()
async_session: Any = None
engine: WorkflowEngine | None = None
registry: RuntimeRegistry | None = None
ws_subscriptions: dict[str, list[WebSocket]] = {}
tool_sessions: dict[str, dict] = {}


async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserContext:
    user_id = request.headers.get("x-mineru-user-id")
    team_id = request.headers.get("x-mineru-team-id")
    if user_id:
        return UserContext(current_user_id=user_id, current_team_id=team_id or "default_team")
    
    if not credentials:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token_data = auth_service.verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return UserContext(current_user_id=token_data.user_id, current_team_id=token_data.team_id)


async def get_optional_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserContext:
    user_id = request.headers.get("x-mineru-user-id")
    team_id = request.headers.get("x-mineru-team-id")
    if user_id:
        return UserContext(current_user_id=user_id, current_team_id=team_id or "default_team")
    
    if not credentials:
        return UserContext(current_user_id="default_user", current_team_id="default_team")
    
    token_data = auth_service.verify_token(credentials.credentials)
    if not token_data:
        return UserContext(current_user_id="default_user", current_team_id="default_team")
    
    return UserContext(current_user_id=token_data.user_id, current_team_id=token_data.team_id)


class CreateRunRequest(BaseModel):
    workflow_id: str
    input: dict[str, Any] = {}


class WorkflowCreateRequest(BaseModel):
    name: str
    description: str = ""
    icon: dict[str, Any] = {"name": "workflow", "color": "blue"}
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []


class HelpFaqRequest(BaseModel):
    category: str
    question: str
    answer: str
    keywords: list[str] = []
    enabled: bool = True
    display_order: int = 100


class HelpDocRequest(BaseModel):
    title: str
    description: str
    icon_key: str
    href: str
    enabled: bool = True
    display_order: int = 100


class ToolRepoSourceRequest(BaseModel):
    name: str
    repo_url: str
    branch: str = "main"
    scan_path: str
    auth_type: str = "none"
    auth_token: Optional[str] = None
    sync_mode: str = "manual"
    sync_cron: Optional[str] = None
    enabled: bool = True


class PlatformToolRequest(BaseModel):
    tool_id: str
    name: str
    description: str
    category: str = "collection"
    runtime_kind: str = "remote"
    source_type: str = "admin"
    version: str = "1.0.0"
    badge: str = "MCP Ready"
    status: str = "draft"


class AiOrchestratorConfigRequest(BaseModel):
    base_url: str
    model: str
    api_key: str
    enabled: bool = True


@app.on_event("startup")
async def startup():
    global engine, registry, async_session
    from mineru_studio.db.models import create_db_engine
    from mineru_studio.db.repository import WorkflowRepository
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    
    engine_obj = await create_db_engine("/tmp/mineru-studio.sqlite")
    async_session = async_sessionmaker(engine_obj, class_=AsyncSession, expire_on_commit=False)
    
    repository = WorkflowRepository(async_session)
    engine = WorkflowEngine(repository)
    registry = RuntimeRegistry()
    registry.register(CodeNodeAdapter())
    registry.register(ShellNodeAdapter())
    registry.register(RemoteHttpNodeAdapter())


@app.post("/auth/login")
async def login(req: LoginRequest):
    user = auth_service.authenticate(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = auth_service.create_access_token(user)
    return TokenResponse(access_token=token, user=user)


@app.get("/auth/me")
async def get_me(user_ctx: UserContext = Depends(get_current_user)):
    user = auth_service.get_user(user_ctx.current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user": user.model_dump(),
        "context": user_ctx.model_dump(),
    }


@app.post("/runs")
async def create_run(req: CreateRunRequest, user_ctx: UserContext = Depends(get_current_user)):
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    
    workflow = WorkflowDefinition(
        id=req.workflow_id,
        name="Workflow",
        nodes=[],
        edges=[],
    )
    run_id = await engine.create_run(workflow, user_ctx.current_user_id)
    return {"run_id": run_id}


@app.get("/runs/{run_id}")
async def get_run(run_id: str, user_ctx: UserContext = Depends(get_current_user)):
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    
    snapshot = await engine.get_snapshot(run_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Workflow run {run_id} was not found")
    
    triggered_by = snapshot.get("metadata", {}).get("triggered_by", "")
    if triggered_by != user_ctx.current_user_id:
        raise HTTPException(status_code=404, detail=f"Workflow run {run_id} was not found")
    
    return snapshot


@app.post("/runs/{run_id}/poll")
async def poll_run(run_id: str, user_ctx: UserContext = Depends(get_current_user)):
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    
    result = await engine.poll_run(run_id)
    return result


@app.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, user_ctx: UserContext = Depends(get_current_user)):
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    
    result = await engine.cancel_run(run_id)
    return result


@app.post("/runs/{run_id}/timeout")
async def timeout_run(run_id: str, req: Optional[dict] = None, user_ctx: UserContext = Depends(get_current_user)):
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    
    result = await engine.timeout_run(run_id)
    return result


@app.delete("/runs/{run_id}/artifacts")
async def purge_artifacts(run_id: str, user_ctx: UserContext = Depends(get_current_user)):
    count = await artifact_storage.delete_artifacts_for_run(run_id)
    return {"run_id": run_id, "deleted_artifacts": count}


@app.get("/runs/{run_id}/nodes/{node_id}/artifacts")
async def list_node_artifacts(run_id: str, node_id: str, user_ctx: UserContext = Depends(get_current_user)):
    artifacts = await artifact_storage.list_artifacts(run_id, node_id)
    return {"run_id": run_id, "node_id": node_id, "artifacts": artifacts}


@app.get("/metrics")
async def get_metrics(user_ctx: UserContext = Depends(get_optional_user)):
    return {
        "total_runs": 0,
        "running_runs": 0,
        "completed_runs": 0,
        "failed_runs": 0,
    }


@app.get("/catalog")
async def get_catalog(user_ctx: UserContext = Depends(get_optional_user)):
    return tool_service.get_catalog().model_dump()


@app.get("/api/tools")
async def get_tools(user_ctx: UserContext = Depends(get_optional_user)):
    return {"tools": [t.model_dump() for t in tool_service.list_tool_descriptors()]}


@app.post("/api/tools/{tool_id}/call")
async def call_tool(tool_id: str, req: dict, user_ctx: UserContext = Depends(get_current_user)):
    tool = tool_service.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")
    return {"output": f"Tool {tool_id} executed"}


@app.post("/api/tools/{tool_id}/start")
async def start_tool(tool_id: str, req: dict, user_ctx: UserContext = Depends(get_current_user)):
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    return {"status": "accepted", "task_id": task_id}


@app.get("/api/tool-profiles/by-tool/{tool_id}")
async def get_tool_profile(tool_id: str):
    tool = tool_service.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool profile {tool_id} not found")
    return {"tool": tool.model_dump()}


@app.get("/api/me")
async def get_me(user_ctx: UserContext = Depends(get_current_user)):
    user = auth_service.get_user(user_ctx.current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user": user.model_dump(),
        "context": {
            "currentUserId": user_ctx.current_user_id,
            "currentTeamId": user_ctx.current_team_id,
            "authProvider": "local_password",
        },
    }


@app.get("/api/users")
async def get_users():
    return {"users": [u.model_dump() for u in auth_service.list_users()]}


@app.post("/api/telemetry")
async def ingest_telemetry(req: dict, user_ctx: UserContext = Depends(get_current_user)):
    return {"ok": True}


@app.get("/api/admin/observability")
async def get_observability(time_range: str = "24h", log_limit: int = 80, user_ctx: UserContext = Depends(get_current_user)):
    return {
        "overview": {"total_logs": 0, "total_audits": 0, "total_telemetry": 0},
        "logs": [],
        "audits": [],
        "telemetry": [],
    }


@app.get("/api/help/faqs")
async def get_faqs():
    return {"faqs": [f.model_dump() for f in tool_service.list_help_faqs(False)]}


@app.get("/api/help/docs")
async def get_docs():
    return {"docs": [d.model_dump() for d in tool_service.list_help_doc_links(False)]}


@app.get("/api/admin/help/faqs")
async def get_admin_faqs(user_ctx: UserContext = Depends(get_current_user)):
    return {"faqs": [f.model_dump() for f in tool_service.list_help_faqs(True)]}


@app.get("/api/admin/help/docs")
async def get_admin_docs(user_ctx: UserContext = Depends(get_current_user)):
    return {"docs": [d.model_dump() for d in tool_service.list_help_doc_links(True)]}


@app.post("/api/admin/help/faqs", status_code=201)
async def create_faq(req: HelpFaqRequest, user_ctx: UserContext = Depends(get_current_user)):
    faq = tool_service.create_help_faq(req.model_dump())
    return {"faq": faq.model_dump()}


@app.put("/api/admin/help/faqs/{faq_id}")
async def update_faq(faq_id: str, req: HelpFaqRequest, user_ctx: UserContext = Depends(get_current_user)):
    faq = tool_service.update_help_faq(faq_id, req.model_dump())
    if not faq:
        raise HTTPException(status_code=404, detail=f"FAQ {faq_id} not found")
    return {"faq": faq.model_dump()}


@app.delete("/api/admin/help/faqs/{faq_id}")
async def delete_faq(faq_id: str, user_ctx: UserContext = Depends(get_current_user)):
    if not tool_service.delete_help_faq(faq_id):
        raise HTTPException(status_code=404, detail=f"FAQ {faq_id} not found")
    return {"ok": True}


@app.post("/api/admin/help/docs", status_code=201)
async def create_doc(req: HelpDocRequest, user_ctx: UserContext = Depends(get_current_user)):
    doc = tool_service.create_help_doc_link(req.model_dump())
    return {"doc": doc.model_dump()}


@app.put("/api/admin/help/docs/{doc_id}")
async def update_doc(doc_id: str, req: HelpDocRequest, user_ctx: UserContext = Depends(get_current_user)):
    doc = tool_service.update_help_doc_link(doc_id, req.model_dump())
    if not doc:
        raise HTTPException(status_code=404, detail=f"Doc {doc_id} not found")
    return {"doc": doc.model_dump()}


@app.delete("/api/admin/help/docs/{doc_id}")
async def delete_doc(doc_id: str, user_ctx: UserContext = Depends(get_current_user)):
    if not tool_service.delete_help_doc_link(doc_id):
        raise HTTPException(status_code=404, detail=f"Doc {doc_id} not found")
    return {"ok": True}


@app.get("/api/admin/ai/orchestrator")
async def get_ai_config(user_ctx: UserContext = Depends(get_current_user)):
    return {"config": tool_service.get_ai_orchestrator_config().model_dump()}


@app.put("/api/admin/ai/orchestrator")
async def update_ai_config(req: AiOrchestratorConfigRequest, user_ctx: UserContext = Depends(get_current_user)):
    config = tool_service.update_ai_orchestrator_config(req.model_dump())
    return {"config": config.model_dump()}


@app.get("/api/admin/skills")
async def list_skills(query: str = "", include_disabled: bool = True, user_ctx: UserContext = Depends(get_current_user)):
    return {"skills": [s.model_dump() for s in tool_service.list_published_skills(include_disabled, query)]}


@app.get("/api/admin/skills/{skill_id}")
async def get_skill(skill_id: str, user_ctx: UserContext = Depends(get_current_user)):
    skill = tool_service.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found")
    return {"skill": skill.model_dump()}


@app.post("/api/admin/skills/{skill_id}/rotate-key")
async def rotate_skill_key(skill_id: str, user_ctx: UserContext = Depends(get_current_user)):
    new_key = tool_service.rotate_skill_key(skill_id)
    if not new_key:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found")
    return {"api_key": new_key}


@app.post("/api/admin/skills/{skill_id}/status")
async def update_skill_status(skill_id: str, req: dict, user_ctx: UserContext = Depends(get_current_user)):
    return {"status": "active"}


@app.get("/api/admin/tools")
async def get_platform_tools(user_ctx: UserContext = Depends(get_current_user)):
    return {"registry": tool_service.get_platform_tool_registry_snapshot().model_dump()}


@app.post("/api/admin/tools/repo-sources")
async def create_repo_source(req: ToolRepoSourceRequest, user_ctx: UserContext = Depends(get_current_user)):
    source = tool_service.upsert_tool_repo_source(None, req.model_dump())
    return {"source": source.model_dump(), "registry": tool_service.get_platform_tool_registry_snapshot().model_dump()}


@app.put("/api/admin/tools/repo-sources/{source_id}")
async def update_repo_source(source_id: str, req: ToolRepoSourceRequest, user_ctx: UserContext = Depends(get_current_user)):
    source = tool_service.upsert_tool_repo_source(source_id, req.model_dump())
    return {"source": source.model_dump(), "registry": tool_service.get_platform_tool_registry_snapshot().model_dump()}


@app.post("/api/admin/tools/repo-sources/{source_id}/sync")
async def sync_repo_source(source_id: str, user_ctx: UserContext = Depends(get_current_user)):
    source = tool_service.sync_tool_repo_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Repo source {source_id} not found")
    return {"source": source.model_dump(), "registry": tool_service.get_platform_tool_registry_snapshot().model_dump()}


@app.post("/api/admin/tools/platform-tools")
async def create_platform_tool(req: PlatformToolRequest, user_ctx: UserContext = Depends(get_current_user)):
    tool = tool_service.upsert_platform_tool(req.model_dump())
    return {"tool": tool.model_dump(), "registry": tool_service.get_platform_tool_registry_snapshot().model_dump()}


@app.put("/api/admin/tools/platform-tools/{tool_id}")
async def update_platform_tool(tool_id: str, req: PlatformToolRequest, user_ctx: UserContext = Depends(get_current_user)):
    tool = tool_service.upsert_platform_tool({**req.model_dump(), "tool_id": tool_id})
    return {"tool": tool.model_dump(), "registry": tool_service.get_platform_tool_registry_snapshot().model_dump()}


@app.get("/api/workflows")
async def list_workflows(user_ctx: UserContext = Depends(get_current_user)):
    return {"workflows": []}


@app.post("/api/workflows")
async def create_workflow(req: WorkflowCreateRequest, user_ctx: UserContext = Depends(get_current_user)):
    workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
    workflow = WorkflowDefinition(
        id=workflow_id,
        name=req.name,
        description=req.description,
        icon=req.icon,
        nodes=[WorkflowNodeInput(id=n.get("id", ""), type=n.get("type", ""), config=n.get("config", {}), input=n.get("input", {})) for n in req.nodes],
        edges=[WorkflowEdge(source=e.get("source", ""), target=e.get("target", "")) for e in req.edges],
    )
    return {"workflow": workflow.model_dump()}


@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str, user_ctx: UserContext = Depends(get_current_user)):
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    
    wf = await engine.repository.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    
    return {"workflow": wf}


@app.put("/api/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, req: WorkflowCreateRequest, user_ctx: UserContext = Depends(get_current_user)):
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    
    existing = await engine.repository.get_workflow(workflow_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    
    workflow = WorkflowDefinition(
        id=workflow_id,
        name=req.name,
        description=req.description,
        icon=req.icon,
        nodes=[WorkflowNodeInput(id=n.get("id", ""), type=n.get("type", ""), config=n.get("config", {}), input=n.get("input", {})) for n in req.nodes],
        edges=[WorkflowEdge(source=e.get("source", ""), target=e.get("target", "")) for e in req.edges],
    )
    await engine.repository.save_workflow(workflow.model_dump())
    return {"workflow": workflow.model_dump()}


@app.delete("/api/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str, user_ctx: UserContext = Depends(get_current_user)):
    return {"ok": True}


@app.get("/api/workflows/{workflow_id}/skill")
async def get_workflow_skill(workflow_id: str, user_ctx: UserContext = Depends(get_current_user)):
    return {"skill_id": f"skill_{workflow_id}", "workflow_id": workflow_id}


@app.post("/api/workflows/{workflow_id}/skill/publish")
async def publish_workflow_skill(workflow_id: str, user_ctx: UserContext = Depends(get_current_user)):
    skill_id = f"skill_{uuid.uuid4().hex[:8]}"
    from .app.tool_service import PublishedSkill
    skill = tool_service.upsert_skill(PublishedSkill(
        skill_id=skill_id,
        workflow_id=workflow_id,
        name=f"Skill for {workflow_id}",
        description="Published workflow skill",
        api_key=f"sk_{uuid.uuid4().hex[:24]}",
        status="active",
        created_at=datetime.now().isoformat(),
    ))
    return {"skill": skill.model_dump()}


@app.post("/api/workflows/{workflow_id}/skill/rotate-key")
async def rotate_workflow_key(workflow_id: str, user_ctx: UserContext = Depends(get_current_user)):
    new_key = f"sk_{uuid.uuid4().hex[:24]}"
    return {"api_key": new_key}


@app.post("/api/workflows/{workflow_id}/skill/status")
async def update_workflow_skill_status(workflow_id: str, req: dict, user_ctx: UserContext = Depends(get_current_user)):
    return {"status": req.get("status", "active")}


@app.post("/api/workflows/import")
async def import_workflow(req: dict, user_ctx: UserContext = Depends(get_current_user)):
    return {"workflow": req}


@app.post("/api/workflows/generate")
async def generate_workflow(req: dict, user_ctx: UserContext = Depends(get_current_user)):
    return {
        "name": "AI 生成 · 线索挖掘流程",
        "desc": "围绕线索发现与数据调研自动生成的 Agent 应用。",
        "icon": {"name": "target", "color": "amber"},
        "nodes": [{"id": "n1", "itemId": "lead_mining", "sourceType": "tool", "title": "线索挖掘工具"}],
        "edges": [],
    }


@app.get("/api/workflow-runs")
async def list_workflow_runs(mode: str = "all", user_ctx: UserContext = Depends(get_current_user)):
    return {"runs": []}


@app.get("/api/workflow-runs/{run_id}")
async def get_workflow_run(run_id: str, user_ctx: UserContext = Depends(get_current_user)):
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    
    snapshot = await engine.get_snapshot(run_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Workflow run {run_id} not found")
    
    if snapshot.get("metadata", {}).get("triggeredBy") != user_ctx.current_user_id:
        raise HTTPException(status_code=404, detail=f"Workflow run {run_id} not found")
    
    return {"run": snapshot}


@app.get("/api/tool-runs")
async def list_tool_runs(mode: str = "all", user_ctx: UserContext = Depends(get_current_user)):
    return {"runs": []}


@app.get("/api/tool-runs/{history_id}")
async def get_tool_run(history_id: str, user_ctx: UserContext = Depends(get_current_user)):
    return {"run": {"history_id": history_id, "status": "completed"}}


@app.post("/api/tasks/{task_id}")
async def poll_task(task_id: str):
    return {"status": "completed", "output": {}}


@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    return {"status": "canceled"}


@app.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str):
    result = await artifact_storage.get_artifact_by_id(artifact_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")
    content, filename = result
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"X-MinerU-Artifact-Path": filename},
    )


@app.post("/api/base-nodes/{node_id}/test")
async def test_base_node(node_id: str, req: dict, user_ctx: UserContext = Depends(get_current_user)):
    return {"status": "succeeded", "output": {}}


@app.post("/api/base-node-remote/start")
async def start_remote_node(req: dict, user_ctx: UserContext = Depends(get_current_user)):
    return {"status": "accepted", "task_id": f"task_{uuid.uuid4().hex[:12]}"}


@app.post("/api/base-node-remote/tasks/{task_id}")
async def poll_remote_task(task_id: str):
    return {"status": "completed"}


@app.post("/api/base-node-remote/tasks/{task_id}/cancel")
async def cancel_remote_task(task_id: str):
    return {"status": "canceled"}


@app.post("/api/workflow-tools/start")
async def start_workflow_tool(req: dict, user_ctx: UserContext = Depends(get_current_user)):
    return {"status": "accepted", "task_id": f"task_{uuid.uuid4().hex[:12]}"}


@app.post("/api/workflow-tools/tasks/{task_id}")
async def poll_workflow_tool_task(task_id: str):
    return {"status": "completed"}


@app.post("/api/workflow-tools/tasks/{task_id}/cancel")
async def cancel_workflow_tool_task(task_id: str):
    return {"status": "canceled"}


@app.get("/api/tool-sessions/{session_id}")
async def get_tool_session(session_id: str):
    if session_id not in tool_sessions:
        raise HTTPException(status_code=404, detail=f"Tool session {session_id} not found")
    
    return tool_sessions[session_id]


@app.get("/api/tool-sessions/{session_id}/events")
async def get_tool_session_events(session_id: str):
    return {"events": []}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_ctx: UserContext = Depends(get_current_user)):
    await websocket.accept()
    run_id = None
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "subscribe":
                run_id = message.get("run_id")
                if run_id:
                    if run_id not in ws_subscriptions:
                        ws_subscriptions[run_id] = []
                    ws_subscriptions[run_id].append(websocket)
                    
                    if engine:
                        snapshot = await engine.get_snapshot(run_id)
                        if snapshot:
                            await websocket.send_json({
                                "type": "run.snapshot",
                                "payload": snapshot,
                            })
    except WebSocketDisconnect:
        if run_id and run_id in ws_subscriptions:
            ws_subscriptions[run_id].remove(websocket)


async def broadcast_run_event(run_id: str, event: dict):
    if run_id in ws_subscriptions:
        for ws in ws_subscriptions[run_id]:
            try:
                await ws.send_json({
                    "type": "run.event",
                    "payload": event,
                })
            except:
                pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)