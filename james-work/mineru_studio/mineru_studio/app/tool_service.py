from pydantic import BaseModel
from typing import Any


class HelpFaq(BaseModel):
    id: str
    category: str
    question: str
    answer: str
    keywords: list[str] = []
    enabled: bool = True
    display_order: int = 100


class HelpDoc(BaseModel):
    id: str
    title: str
    description: str
    icon_key: str
    href: str
    enabled: bool = True
    display_order: int = 100


class PlatformTool(BaseModel):
    tool_id: str
    name: str
    description: str
    category: str = "collection"
    runtime_kind: str = "remote"
    source_type: str = "admin"
    source_id: str | None = None
    owner_user_id: str | None = None
    owner_name: str | None = None
    team_id: str | None = None
    version: str = "1.0.0"
    badge: str = "MCP Ready"
    provider: str = "后台注册"
    status: str = "draft"
    manifest_url: str | None = None


class ToolRepoSource(BaseModel):
    source_id: str
    name: str
    repo_url: str
    branch: str = "main"
    scan_path: str
    auth_type: str = "none"
    auth_token: str | None = None
    sync_mode: str = "manual"
    sync_cron: str | None = None
    enabled: bool = True
    tool_count: int = 0


class AiOrchestratorConfig(BaseModel):
    id: str = "default"
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    enabled: bool = True


class PublishedSkill(BaseModel):
    skill_id: str
    workflow_id: str
    name: str
    description: str
    api_key: str
    status: str = "active"
    created_at: str = ""


class ToolDescriptor(BaseModel):
    tool_id: str
    name: str
    description: str
    category: str
    input_schema: dict[str, Any] = {}
    output_schema: dict[str, Any] = {}


class ToolCategory(BaseModel):
    id: str
    name: str
    icon: str = "folder"
    display_order: int = 0


class ToolCatalog(BaseModel):
    tools: list[ToolDescriptor]
    categories: list[ToolCategory]


class PlatformRegistry(BaseModel):
    repo_sources: list[ToolRepoSource]
    platform_tools: list[PlatformTool]


import uuid
from datetime import datetime


class MockToolService:
    def __init__(self):
        self._faqs: dict[str, HelpFaq] = {}
        self._docs: dict[str, HelpDoc] = {}
        self._tools: dict[str, ToolDescriptor] = {
            "lead_mining": ToolDescriptor(
                tool_id="lead_mining",
                name="线索挖掘工具",
                description="数据线索发现、调研、种子数据挖掘",
                category="data",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                output_schema={"type": "object"},
            ),
            "signal_agent": ToolDescriptor(
                tool_id="signal_agent",
                name="数据感知Agent",
                description="动态监控、官网/新闻/竞品信息感知",
                category="monitor",
                input_schema={"type": "object", "properties": {"keywords": {"type": "array", "items": {"type": "string"}}}},
                output_schema={"type": "object"},
            ),
            "mineru25_h": ToolDescriptor(
                tool_id="mineru25_h",
                name="MinerU2.5_H",
                description="PDF全文解析",
                category="parser",
                input_schema={
                    "type": "object",
                    "properties": {
                        "output_path": {"type": "string"},
                        "input_sql": {"type": "string"},
                    },
                },
                output_schema={"type": "object"},
            ),
            "feishu_push": ToolDescriptor(
                tool_id="feishu_push",
                name="飞书群消息推送",
                description="飞书消息通知",
                category="notification",
                input_schema={
                    "type": "object",
                    "properties": {
                        "webhook_url": {"type": "string"},
                        "msg_type": {"type": "string"},
                        "text_content": {"type": "string"},
                    },
                },
                output_schema={"type": "object"},
            ),
        }
        self._categories: list[ToolCategory] = [
            ToolCategory(id="data", name="数据", icon="database", display_order=1),
            ToolCategory(id="monitor", name="监控", icon="activity", display_order=2),
            ToolCategory(id="parser", name="解析", icon="file-text", display_order=3),
            ToolCategory(id="notification", name="通知", icon="bell", display_order=4),
        ]
        self._ai_config = AiOrchestratorConfig()
        self._repo_sources: dict[str, ToolRepoSource] = {}
        self._platform_tools: dict[str, PlatformTool] = {}
        self._skills: dict[str, PublishedSkill] = {}

    def get_catalog(self) -> ToolCatalog:
        return ToolCatalog(tools=list(self._tools.values()), categories=self._categories)

    def list_tool_descriptors(self) -> list[ToolDescriptor]:
        return list(self._tools.values())

    def get_tool(self, tool_id: str) -> ToolDescriptor | None:
        return self._tools.get(tool_id)

    def list_help_faqs(self, admin: bool = False) -> list[HelpFaq]:
        return [f for f in self._faqs.values() if admin or f.enabled]

    def create_help_faq(self, data: dict) -> HelpFaq:
        faq = HelpFaq(
            id=f"faq_{uuid.uuid4().hex[:8]}",
            category=data.get("category", ""),
            question=data.get("question", ""),
            answer=data.get("answer", ""),
            keywords=data.get("keywords", []),
            enabled=data.get("enabled", True),
            display_order=data.get("display_order", 100),
        )
        self._faqs[faq.id] = faq
        return faq

    def update_help_faq(self, faq_id: str, data: dict) -> HelpFaq | None:
        if faq_id not in self._faqs:
            return None
        faq = self._faqs[faq_id]
        for key, value in data.items():
            if hasattr(faq, key):
                setattr(faq, key, value)
        return faq

    def delete_help_faq(self, faq_id: str) -> bool:
        if faq_id in self._faqs:
            del self._faqs[faq_id]
            return True
        return False

    def list_help_doc_links(self, admin: bool = False) -> list[HelpDoc]:
        return [d for d in self._docs.values() if admin or d.enabled]

    def create_help_doc_link(self, data: dict) -> HelpDoc:
        doc = HelpDoc(
            id=f"doc_{uuid.uuid4().hex[:8]}",
            title=data.get("title", ""),
            description=data.get("description", ""),
            icon_key=data.get("icon_key", ""),
            href=data.get("href", ""),
            enabled=data.get("enabled", True),
            display_order=data.get("display_order", 100),
        )
        self._docs[doc.id] = doc
        return doc

    def update_help_doc_link(self, doc_id: str, data: dict) -> HelpDoc | None:
        if doc_id not in self._docs:
            return None
        doc = self._docs[doc_id]
        for key, value in data.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
        return doc

    def delete_help_doc_link(self, doc_id: str) -> bool:
        if doc_id in self._docs:
            del self._docs[doc_id]
            return True
        return False

    def get_ai_orchestrator_config(self) -> AiOrchestratorConfig:
        return self._ai_config

    def update_ai_orchestrator_config(self, config: dict) -> AiOrchestratorConfig:
        for key, value in config.items():
            if hasattr(self._ai_config, key):
                setattr(self._ai_config, key, value)
        return self._ai_config

    def list_published_skills(self, include_disabled: bool = False, query: str = "") -> list[PublishedSkill]:
        skills = list(self._skills.values())
        if not include_disabled:
            skills = [s for s in skills if s.status == "active"]
        if query:
            skills = [s for s in skills if query.lower() in s.name.lower() or query.lower() in s.description.lower()]
        return skills

    def get_skill(self, skill_id: str) -> PublishedSkill | None:
        return self._skills.get(skill_id)

    def upsert_skill(self, skill: PublishedSkill) -> PublishedSkill:
        self._skills[skill.skill_id] = skill
        return skill

    def rotate_skill_key(self, skill_id: str) -> str | None:
        if skill_id not in self._skills:
            return None
        new_key = f"sk_{uuid.uuid4().hex[:24]}"
        self._skills[skill_id].api_key = new_key
        return new_key

    def get_platform_tool_registry_snapshot(self) -> PlatformRegistry:
        return PlatformRegistry(
            repo_sources=list(self._repo_sources.values()),
            platform_tools=list(self._platform_tools.values()),
        )

    def upsert_tool_repo_source(self, source_id: str | None, data: dict) -> ToolRepoSource:
        if source_id is None:
            source_id = f"src_{uuid.uuid4().hex[:8]}"
        source = ToolRepoSource(
            source_id=source_id,
            name=data.get("name", ""),
            repo_url=data.get("repo_url", ""),
            branch=data.get("branch", "main"),
            scan_path=data.get("scan_path", ""),
            auth_type=data.get("auth_type", "none"),
            auth_token=data.get("auth_token"),
            sync_mode=data.get("sync_mode", "manual"),
            sync_cron=data.get("sync_cron"),
            enabled=data.get("enabled", True),
            tool_count=0,
        )
        self._repo_sources[source_id] = source
        return source

    def sync_tool_repo_source(self, source_id: str) -> ToolRepoSource | None:
        if source_id not in self._repo_sources:
            return None
        self._repo_sources[source_id].tool_count = 5
        return self._repo_sources[source_id]

    def upsert_platform_tool(self, data: dict) -> PlatformTool:
        tool_id = data.get("tool_id", f"tool_{uuid.uuid4().hex[:8]}")
        tool = PlatformTool(
            tool_id=tool_id,
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=data.get("category", "collection"),
            runtime_kind=data.get("runtime_kind", "remote"),
            source_type=data.get("source_type", "admin"),
            source_id=data.get("source_id"),
            owner_user_id=data.get("owner_user_id"),
            owner_name=data.get("owner_name"),
            team_id=data.get("team_id"),
            version=data.get("version", "1.0.0"),
            badge=data.get("badge", "MCP Ready"),
            provider=data.get("provider", "后台注册"),
            status=data.get("status", "draft"),
            manifest_url=data.get("manifest_url"),
        )
        self._platform_tools[tool_id] = tool
        return tool

    def get_user(self, user_id: str) -> dict:
        return {
            "id": user_id,
            "name": "User",
            "email": f"user_{user_id}@example.com",
            "team_id": "default_team",
        }

    def list_users(self) -> list[dict]:
        return [
            {"id": "default_user", "name": "Default User", "email": "user@example.com", "team_id": "default_team"},
        ]

    def get_request_context(self, user_id: str, team_id: str) -> dict:
        return {
            "current_user_id": user_id,
            "current_team_id": team_id,
        }