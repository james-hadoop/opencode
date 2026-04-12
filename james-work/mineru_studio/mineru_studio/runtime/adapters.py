from typing import Any
import uuid


class NodeRuntimeAdapter:
    async def execute(self, node_id: str, config: dict, input_data: dict) -> dict:
        raise NotImplementedError


class CodeNodeAdapter(NodeRuntimeAdapter):
    async def execute(self, node_id: str, config: dict, input_data: dict) -> dict:
        code = config.get("code", "")
        result = {"output": f"Code executed: {code[:50]}...", "nodeId": node_id}
        return result


class ShellNodeAdapter(NodeRuntimeAdapter):
    async def execute(self, node_id: str, config: dict, input_data: dict) -> dict:
        command = config.get("command", "")
        result = {"output": f"Shell command executed: {command[:50]}...", "nodeId": node_id}
        return result


class RemoteHttpNodeAdapter(NodeRuntimeAdapter):
    async def execute(self, node_id: str, config: dict, input_data: dict) -> dict:
        base_url = config.get("baseUrl", "")
        timeout_ms = config.get("timeoutMs", 30000)
        retry_limit = config.get("retryLimit", 0)

        result = {
            "output": {
                "status": "accepted",
                "externalTaskId": f"task_{uuid.uuid4().hex[:12]}",
            },
            "nodeId": node_id,
        }
        return result


class RuntimeRegistry:
    def __init__(self):
        self.adapters: dict[str, NodeRuntimeAdapter] = {}

    def register(self, adapter: NodeRuntimeAdapter, node_type: str = None):
        adapter_type = node_type or adapter.__class__.__name__.replace("NodeAdapter", "").lower()
        self.adapters[adapter_type] = adapter

    def get(self, node_type: str) -> NodeRuntimeAdapter | None:
        return self.adapters.get(node_type)

    def execute(self, node_type: str, node_id: str, config: dict, input_data: dict) -> dict:
        adapter = self.get(node_type)
        if not adapter:
            return {"error": f"No adapter for node type: {node_type}"}
        return adapter.execute(node_id, config, input_data)