from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, AsyncGenerator, Literal
import requests
import json
import uuid
import time
import asyncio
from contextlib import asynccontextmanager
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenCode 配置
OPENCODE_BASE_URL = "http://localhost:4096"
DEFAULT_PROJECT_ID = "default"  # 默认项目ID
DEFAULT_TIMEOUT = 300

# 支持的模型列表
SUPPORTED_MODELS = {
    "minimax-m2.5-free": {
        "providerID": "opencode",
        "modelID": "minimax-m2.5-free",
        "description": "MiniMax M2.5 Free Model"
    },
    "glm-4.7-free": {
        "providerID": "opencode",
        "modelID": "glm-4.7-free",
        "description": "GLM 4.7 Free Model"
    },
    "minimax-m2.1-free": {
        "providerID": "opencode",
        "modelID": "minimax-m2.1-free",
        "description": "MiniMax M2.1 Free Model"
    },
    "gpt-4o-mini": {
        "providerID": "opencode",
        "modelID": "gpt-4o-mini",
        "description": "GPT-4o Mini Model"
    }
}


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = Field(default="minimax-m2.5-free", description="模型ID")
    messages: List[Message] = Field(..., min_length=1, description="消息列表")
    stream: Optional[bool] = Field(default=False, description="是否流式输出")
    temperature: Optional[float] = Field(default=1.0, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(default=None, description="最大token数")
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1, description="top-p采样")
    n: Optional[int] = Field(default=1, ge=1, le=5, description="生成数量")


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


class SessionInfo(BaseModel):
    id: str
    created: Optional[int] = None


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str


class ModelsResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


class OpenCodeClient:
    """OpenCode API 客户端"""
    
    def __init__(self, base_url: str = OPENCODE_BASE_URL, project_id: str = DEFAULT_PROJECT_ID):
        self.base_url = base_url
        self.project_id = project_id
    
    def create_session(self, directory: Optional[str] = None, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        创建新会话
        
        Args:
            directory: 工作目录路径
            parent_id: 父会话ID（用于分支）
        """
        try:
            url = f"{self.base_url}/project/{self.project_id}/session"
            payload: Dict[str, Any] = {}
            if directory:
                payload["directory"] = directory
            if parent_id:
                payload["parentID"] = parent_id
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict) or "id" not in result:
                raise ValueError(f"Invalid session response: {result}")
            return result
        except (requests.RequestException, ValueError) as e:
            # 尝试旧版API (向后兼容)
            try:
                response = requests.post(f"{self.base_url}/session", timeout=30)
                response.raise_for_status()
                result = response.json()
                if not isinstance(result, dict) or "id" not in result:
                    raise ValueError(f"Invalid session response: {result}")
                logger.info("使用旧版API创建会话成功")
                return result
            except Exception as fallback_error:
                logger.error(f"创建会话失败: {e}, 回退失败: {fallback_error}")
                raise
    
    def send_message(
        self, 
        session_id: str, 
        parts: List[Dict[str, Any]],
        model_config: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """发送消息到会话"""
        # 尝试新版API
        url = f"{self.base_url}/project/{self.project_id}/session/{session_id}/message"
        
        payload: Dict[str, Any] = {
            "parts": parts
        }
        
        if model_config:
            payload["model"] = model_config
        
        try:
            response = requests.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError(f"Invalid message response: {result}")
            return result
        except (requests.RequestException, ValueError) as e:
            # 尝试旧版API (向后兼容)
            try:
                old_url = f"{self.base_url}/session/{session_id}/message"
                response = requests.post(old_url, json=payload, timeout=DEFAULT_TIMEOUT)
                response.raise_for_status()
                result = response.json()
                if not isinstance(result, dict):
                    raise ValueError(f"Invalid message response: {result}")
                logger.info("使用旧版API发送消息成功")
                return result
            except Exception as fallback_error:
                logger.error(f"发送消息失败: {e}, 回退失败: {fallback_error}")
                raise
    
    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取消息历史"""
        # 尝试新版API
        url = f"{self.base_url}/project/{self.project_id}/session/{session_id}/message"
        params = {}
        if limit:
            params["limit"] = limit
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, list):
                raise ValueError(f"Invalid messages response: {result}")
            return result
        except (requests.RequestException, ValueError) as e:
            # 尝试旧版API (向后兼容)
            try:
                old_url = f"{self.base_url}/session/{session_id}/message"
                response = requests.get(old_url, params=params, timeout=30)
                response.raise_for_status()
                result = response.json()
                if not isinstance(result, list):
                    raise ValueError(f"Invalid messages response: {result}")
                logger.info("使用旧版API获取消息成功")
                return result
            except Exception as fallback_error:
                logger.error(f"获取消息历史失败: {e}, 回退失败: {fallback_error}")
                raise
    
    def abort_session(self, session_id: str) -> None:
        """中止会话"""
        # 尝试新版API
        url = f"{self.base_url}/project/{self.project_id}/session/{session_id}/abort"
        try:
            requests.post(url, timeout=10)
        except requests.RequestException as e:
            # 尝试旧版API (向后兼容)
            try:
                old_url = f"{self.base_url}/session/{session_id}/abort"
                requests.post(old_url, timeout=10)
                logger.info("使用旧版API中止会话成功")
            except Exception as fallback_error:
                logger.error(f"中止会话失败: {e}, 回退失败: {fallback_error}")


def parse_model_id(model_name: str) -> Dict[str, str]:
    """解析模型名称，返回 providerID 和 modelID"""
    # 移除可能的前缀
    clean_name = model_name.replace("minimax/", "").replace("glm/", "").replace("gpt/", "")
    
    # 查找匹配的模型配置
    if clean_name in SUPPORTED_MODELS:
        return SUPPORTED_MODELS[clean_name]
    
    # 默认返回配置
    return {
        "providerID": "opencode",
        "modelID": clean_name
    }


def build_prompt_parts(messages: List[Message]) -> List[Dict[str, str]]:
    """将消息列表转换为 opencode 的 parts 格式"""
    parts = []
    for msg in messages:
        parts.append({
            "type": "text",
            "text": f"{msg.role}: {msg.content}"
        })
    return parts


def extract_text_from_response(response: Dict[str, Any]) -> str:
    """从 opencode 响应中提取文本内容"""
    text_parts = []
    for part in response.get("parts", []):
        if part.get("type") == "text":
            text_parts.append(part.get("text", ""))
    return "".join(text_parts)


def extract_usage_info(response: Dict[str, Any]) -> Dict[str, int]:
    """从 opencode 响应中提取 token 使用信息"""
    info = response.get("info", {})
    tokens = info.get("tokens", {})
    
    return {
        "prompt_tokens": tokens.get("input", 0),
        "completion_tokens": tokens.get("output", 0),
        "total_tokens": tokens.get("input", 0) + tokens.get("output", 0)
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 OpenCode API Proxy 启动")
    yield
    logger.info("👋 OpenCode API Proxy 关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="OpenCode OpenAI Compatible API",
    description="OpenCode API 的 OpenAI 兼容代理服务",
    version="1.0.0",
    lifespan=lifespan
)

# 全局 OpenCode 客户端
opencode_client = OpenCodeClient()


@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 测试连接到 opencode (尝试多个端点)
        endpoints = [
            f"{OPENCODE_BASE_URL}/health",
            f"{OPENCODE_BASE_URL}/project",
            f"{OPENCODE_BASE_URL}/session"
        ]
        
        connected = False
        endpoint_used = None
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint, timeout=5)
                if response.status_code in [200, 404]:  # 404 也说明服务在运行
                    connected = True
                    endpoint_used = endpoint
                    break
            except:
                continue
        
        return {
            "status": "healthy" if connected else "degraded",
            "opencode_connected": connected,
            "endpoint_tested": endpoint_used,
            "base_url": OPENCODE_BASE_URL
        }
    except Exception as e:
        return {
            "status": "degraded",
            "opencode_connected": False,
            "error": str(e),
            "base_url": OPENCODE_BASE_URL
        }


@app.get("/v1/models", response_model=ModelsResponse)
async def list_models():
    """列出所有可用模型"""
    model_list = []
    for model_id, config in SUPPORTED_MODELS.items():
        model_list.append(ModelInfo(
            id=model_id,
            created=int(time.time()),
            owned_by="opencode"
        ))
    
    return ModelsResponse(data=model_list)


@app.get("/v1/models/{model_id}")
async def get_model(model_id: str):
    """获取指定模型信息"""
    if model_id in SUPPORTED_MODELS:
        config = SUPPORTED_MODELS[model_id]
        return ModelInfo(
            id=model_id,
            created=int(time.time()),
            owned_by=config["providerID"]
        )
    raise HTTPException(status_code=404, detail=f"Model {model_id} not found")


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(request: ChatCompletionRequest):
    """创建聊天完成（非流式）"""
    session_id = None
    try:
        # 解析模型配置
        model_config = parse_model_id(request.model)
        logger.info(f"使用模型: {model_config}")
        
        # 创建会话
        session = opencode_client.create_session()
        session_id = session["id"]
        
        # 构建消息
        parts = build_prompt_parts(request.messages)
        
        # 发送消息
        response = opencode_client.send_message(
            session_id=session_id,
            parts=parts,
            model_config=model_config
        )
        
        # 提取响应内容
        content = extract_text_from_response(response)
        usage = extract_usage_info(response)
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }],
            usage=usage
        )
    
    except requests.RequestException as e:
        logger.error(f"请求失败: {e}")
        if session_id:
            try:
                opencode_client.abort_session(session_id)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"OpenCode API 错误: {str(e)}")
    except Exception as e:
        logger.error(f"服务器错误: {e}")
        if session_id:
            try:
                opencode_client.abort_session(session_id)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/chat/completions/stream")
async def create_chat_completion_stream(request: ChatCompletionRequest):
    """创建聊天完成（流式）"""
    session_id = None
    try:
        # 解析模型配置
        model_config = parse_model_id(request.model)
        
        # 创建会话
        session = opencode_client.create_session()
        session_id = session["id"]
        
        # 构建消息
        parts = build_prompt_parts(request.messages)
        
        async def generate() -> AsyncGenerator[str, None]:
            nonlocal session_id
            if not session_id:
                yield f"data: {json.dumps({'error': {'message': 'Session creation failed', 'type': 'api_error'}}, ensure_ascii=False)}\n\n"
                return
            try:
                # 发送消息
                response = opencode_client.send_message(
                    session_id=session_id,
                    parts=parts,
                    model_config=model_config
                )
                
                # 提取文本内容
                content = extract_text_from_response(response)
                usage = extract_usage_info(response)
                
                # 模拟流式输出（逐字符）
                for char in content:
                    chunk = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": request.model,
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "content": char
                            },
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.01)  # 模拟流式延迟
                
                # 发送完成标记
                final_chunk = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }],
                    "usage": usage
                }
                yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"流式生成失败: {e}")
                error_chunk = {
                    "error": {
                        "message": str(e),
                        "type": "api_error"
                    }
                }
                yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
            finally:
                if session_id:
                    try:
                        opencode_client.abort_session(session_id)
                    except Exception:
                        pass
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    except Exception as e:
        if session_id:
            try:
                opencode_client.abort_session(session_id)
            except Exception:
                pass
        logger.error(f"流式请求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/sessions", response_model=SessionInfo)
async def create_opencode_session():
    """创建 OpenCode 会话"""
    try:
        session = opencode_client.create_session()
        return SessionInfo(id=session["id"], created=session.get("created"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, limit: Optional[int] = None):
    """获取会话消息历史"""
    try:
        messages = opencode_client.get_messages(session_id, limit)
        return {"data": messages}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/sessions/{session_id}/abort")
async def abort_opencode_session(session_id: str):
    """中止 OpenCode 会话"""
    try:
        opencode_client.abort_session(session_id)
        return {"status": "aborted", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MessageRequest(BaseModel):
    """消息请求模型"""
    parts: List[Dict[str, Any]]
    model_configuration: Optional[Dict[str, str]] = Field(None, alias="model_config")


@app.post("/v1/sessions/{session_id}/message")
async def send_session_message(
    session_id: str,
    request: MessageRequest
):
    """向指定会话发送消息（原始 API）"""
    try:
        response = opencode_client.send_message(session_id, request.parts, request.model_configuration)
        return response
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== OpenCode 原生 API 完整支持 ==========

@app.get("/project")
async def list_projects():
    """列出所有项目"""
    try:
        response = requests.get(f"{OPENCODE_BASE_URL}/project", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/project/init")
async def init_project():
    """初始化新项目"""
    try:
        response = requests.post(f"{OPENCODE_BASE_URL}/project/init", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/project/{project_id}/session")
async def list_project_sessions(project_id: str):
    """列出指定项目的所有会话"""
    try:
        response = requests.get(f"{OPENCODE_BASE_URL}/project/{project_id}/session", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/project/{project_id}/session/{session_id}")
async def get_project_session(project_id: str, session_id: str):
    """获取指定会话的详细信息"""
    try:
        response = requests.get(f"{OPENCODE_BASE_URL}/project/{project_id}/session/{session_id}", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CreateSessionRequest(BaseModel):
    """创建会话请求模型"""
    directory: str
    parent_id: Optional[str] = None


@app.post("/project/{project_id}/session")
async def create_project_session(
    project_id: str,
    request: CreateSessionRequest
):
    """创建新会话"""
    try:
        payload = {"directory": request.directory}
        if request.parent_id:
            payload["parentID"] = request.parent_id

        response = requests.post(
            f"{OPENCODE_BASE_URL}/project/{project_id}/session",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/project/{project_id}/session/{session_id}")
async def delete_project_session(project_id: str, session_id: str):
    """删除指定会话"""
    try:
        response = requests.delete(
            f"{OPENCODE_BASE_URL}/project/{project_id}/session/{session_id}",
            timeout=30
        )
        response.raise_for_status()
        return {"status": "deleted", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/project/{project_id}/session/{session_id}/init")
async def init_project_session(project_id: str, session_id: str):
    """初始化会话"""
    try:
        response = requests.post(
            f"{OPENCODE_BASE_URL}/project/{project_id}/session/{session_id}/init",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/project/{project_id}/session/{session_id}/abort")
async def abort_project_session(project_id: str, session_id: str):
    """中止会话"""
    try:
        response = requests.post(
            f"{OPENCODE_BASE_URL}/project/{project_id}/session/{session_id}/abort",
            timeout=30
        )
        response.raise_for_status()
        return {"status": "aborted", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/project/{project_id}/session/{session_id}/share")
async def share_project_session(project_id: str, session_id: str):
    """分享会话"""
    try:
        response = requests.post(
            f"{OPENCODE_BASE_URL}/project/{project_id}/session/{session_id}/share",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/project/{project_id}/session/{session_id}/share")
async def unshare_project_session(project_id: str, session_id: str):
    """取消分享会话"""
    try:
        response = requests.delete(
            f"{OPENCODE_BASE_URL}/project/{project_id}/session/{session_id}/share",
            timeout=30
        )
        response.raise_for_status()
        return {"status": "unshared", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/project/{project_id}/session/{session_id}/compact")
async def compact_project_session(project_id: str, session_id: str):
    """压缩会话历史"""
    try:
        response = requests.post(
            f"{OPENCODE_BASE_URL}/project/{project_id}/session/{session_id}/compact",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/project/{project_id}/session/{session_id}/message")
async def get_project_messages(
    project_id: str,
    session_id: str,
    limit: Optional[int] = None
):
    """获取会话消息历史"""
    try:
        params = {}
        if limit:
            params["limit"] = limit
        
        response = requests.get(
            f"{OPENCODE_BASE_URL}/project/{project_id}/session/{session_id}/message",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/project/{project_id}/session/{session_id}/message/{message_id}")
async def get_project_message(project_id: str, session_id: str, message_id: str):
    """获取指定消息"""
    try:
        response = requests.get(
            f"{OPENCODE_BASE_URL}/project/{project_id}/session/{session_id}/message/{message_id}",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/project/{project_id}/session/{session_id}/message")
async def send_project_message(
    project_id: str,
    session_id: str,
    request: MessageRequest
):
    """向项目会话发送消息"""
    try:
        payload: Dict[str, Any] = {"parts": request.parts}
        if request.model_configuration:
            payload["model"] = request.model_configuration

        response = requests.post(
            f"{OPENCODE_BASE_URL}/project/{project_id}/session/{session_id}/message",
            json=payload,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/project/{project_id}/session/{session_id}/revert")
async def revert_project_session(project_id: str, session_id: str):
    """回退会话状态"""
    try:
        response = requests.post(
            f"{OPENCODE_BASE_URL}/project/{project_id}/session/{session_id}/revert",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/project/{project_id}/session/{session_id}/unrevert")
async def unrevert_project_session(project_id: str, session_id: str):
    """撤销回退"""
    try:
        response = requests.post(
            f"{OPENCODE_BASE_URL}/project/{project_id}/session/{session_id}/unrevert",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/provider")
async def get_provider(directory: Optional[str] = None):
    """获取提供者信息"""
    try:
        params = {}
        if directory:
            params["directory"] = directory
        
        response = requests.get(
            f"{OPENCODE_BASE_URL}/provider",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config")
async def get_config(directory: Optional[str] = None):
    """获取配置"""
    try:
        params = {}
        if directory:
            params["directory"] = directory
        
        response = requests.get(
            f"{OPENCODE_BASE_URL}/config",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/project/{project_id}/agent")
async def get_project_agent(project_id: str, directory: Optional[str] = None):
    """获取项目代理"""
    try:
        params = {}
        if directory:
            params["directory"] = directory
        
        response = requests.get(
            f"{OPENCODE_BASE_URL}/project/{project_id}/agent",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/project/{project_id}/find/file")
async def find_project_files(project_id: str, directory: Optional[str] = None):
    """查找项目文件"""
    try:
        params = {}
        if directory:
            params["directory"] = directory
        
        response = requests.get(
            f"{OPENCODE_BASE_URL}/project/{project_id}/find/file",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/project/{project_id}/session/{session_id}/find/file")
async def find_session_files(project_id: str, session_id: str):
    """在会话中查找文件"""
    try:
        response = requests.get(
            f"{OPENCODE_BASE_URL}/project/{project_id}/session/{session_id}/find/file",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/project/{project_id}/session/{session_id}/file")
async def get_session_file(project_id: str, session_id: str):
    """获取会话文件"""
    try:
        response = requests.get(
            f"{OPENCODE_BASE_URL}/project/{project_id}/session/{session_id}/file",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/project/{project_id}/session/{session_id}/file/status")
async def get_session_file_status(project_id: str, session_id: str):
    """获取会话文件状态"""
    try:
        response = requests.get(
            f"{OPENCODE_BASE_URL}/project/{project_id}/session/{session_id}/file/status",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18000, log_level="info")
