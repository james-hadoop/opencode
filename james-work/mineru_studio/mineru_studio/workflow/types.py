"""Workflow types and definitions."""
from typing import Any, Literal
from pydantic import BaseModel, Field


class WorkflowNodeInput(BaseModel):
    id: str
    type: str
    config: dict[str, Any] = Field(default_factory=dict)
    input: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    source: str
    target: str


class WorkflowSettings(BaseModel):
    execution_timeout_ms: int = 0
    retry_limit: int = 0
    retry_delay_ms: int = 0


class WorkflowOwnership(BaseModel):
    owner_user_id: str | None = None
    owner_team_id: str | None = None
    public: bool = False


class WorkflowDefinition(BaseModel):
    id: str
    name: str
    description: str = ""
    icon: dict[str, Any] = Field(default_factory=lambda: {"name": "workflow", "color": "blue"})
    nodes: list[WorkflowNodeInput]
    edges: list[WorkflowEdge]
    settings: WorkflowSettings = Field(default_factory=WorkflowSettings)
    ownership: WorkflowOwnership = Field(default_factory=WorkflowOwnership)
    status: Literal["template", "active", "archived"] = "active"
    created_at: str = ""
    updated_at: str = ""


class NodeId(str):
    """Type alias for node ID."""
    pass


class WorkflowGraph(BaseModel):
    """DAG structure for workflow."""
    nodes: dict[str, WorkflowNodeInput]
    adjacency: dict[str, list[str]]  # node_id -> list of dependent node IDs
    reverse_adjacency: dict[str, list[str]]  # node_id -> list of prerequisite node IDs


def build_workflow_graph(definition: WorkflowDefinition) -> WorkflowGraph:
    """Build DAG from workflow definition."""
    nodes = {node.id: node for node in definition.nodes}
    adjacency: dict[str, list[str]] = {node.id: [] for node in definition.nodes}
    reverse_adjacency: dict[str, list[str]] = {node.id: [] for node in definition.nodes}

    for edge in definition.edges:
        if edge.source in adjacency and edge.target in adjacency:
            adjacency[edge.source].append(edge.target)
            reverse_adjacency[edge.target].append(edge.source)

    return WorkflowGraph(
        nodes=nodes,
        adjacency=adjacency,
        reverse_adjacency=reverse_adjacency,
    )


def get_ready_nodes(
    graph: WorkflowGraph,
    completed_nodes: set[str],
) -> list[str]:
    """Get nodes that are ready to execute (all prerequisites completed)."""
    ready = []
    for node_id in graph.nodes:
        if node_id in completed_nodes:
            continue
        prerequisites = graph.reverse_adjacency.get(node_id, [])
        if all(prereq in completed_nodes for prereq in prerequisites):
            ready.append(node_id)
    return ready