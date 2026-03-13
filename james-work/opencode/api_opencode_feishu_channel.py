"""
飞书 Channel FastAPI 本地服务

基于 openclaw/extensions/feishu 实现的核心功能：
- 消息接收 (Webhook/WebSocket)
- 消息发送
- 消息处理和权限检查
- 工具 API (发送消息、获取消息、获取用户/群组信息)
- 流式响应支持
- 多轮对话上下文管理
- OpenCode 主动推送支持
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import queue
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Optional
from urllib.parse import parse_qs

from fastapi import APIRouter, BackgroundTasks, Body, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeishuDomain(str, Enum):
    FEISHU = "feishu"
    LARK = "lark"


class ConnectionMode(str, Enum):
    WEBSOCKET = "websocket"
    WEBHOOK = "webhook"


class ChatType(str, Enum):
    P2P = "p2p"
    GROUP = "group"
    PRIVATE = "private"


class FeishuConfig(BaseModel):
    app_id: str
    app_secret: str
    encrypt_key: Optional[str] = None
    verification_token: Optional[str] = None
    domain: FeishuDomain = FeishuDomain.FEISHU
    connection_mode: ConnectionMode = ConnectionMode.WEBHOOK
    webhook_port: int = 8000
    webhook_path: str = "/webhook"


class FeishuMessageEvent(BaseModel):
    message_id: str
    root_id: Optional[str] = None
    parent_id: Optional[str] = None
    thread_id: Optional[str] = None
    chat_id: str
    chat_type: ChatType
    message_type: str
    content: str
    create_time: Optional[str] = None
    sender_id: Optional[str] = None
    sender_id_type: Optional[str] = None


class FeishuMessageContext(BaseModel):
    chat_id: str
    message_id: str
    sender_id: str
    sender_open_id: Optional[str] = None
    sender_name: Optional[str] = None
    chat_type: ChatType
    mentioned_bot: bool = False
    root_id: Optional[str] = None
    parent_id: Optional[str] = None
    thread_id: Optional[str] = None
    content: str
    content_type: str


class SendMessageRequest(BaseModel):
    to: str
    text: str
    msg_type: str = "text"
    reply_to_message_id: Optional[str] = None
    reply_in_thread: bool = False


class SendCardRequest(BaseModel):
    to: str
    card: dict


class GetMessageRequest(BaseModel):
    message_id: str


class FeishuAPI:
    """飞书 API 封装"""
    
    BASE_URLS = {
        FeishuDomain.FEISHU: "https://open.feishu.cn",
        FeishuDomain.LARK: "https://open.larksuite.com",
    }
    
    def __init__(self, config: FeishuConfig):
        self.config = config
        self.base_url = self.BASE_URLS.get(config.domain, self.BASE_URLS[FeishuDomain.FEISHU])
        self._tenant_access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建共享的 AsyncClient"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        """关闭 AsyncClient"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def get_tenant_access_token(self) -> str:
        """获取 tenant_access_token"""
        if self._tenant_access_token and time.time() < self._token_expires_at - 300:
            return self._tenant_access_token
        
        url = f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal"
        client = await self._get_client()
        resp = await client.post(url, json={
            "app_id": self.config.app_id,
            "app_secret": self.config.app_secret,
        })
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"Failed to get tenant_access_token: {data}")
        self._tenant_access_token = data["tenant_access_token"]
        self._token_expires_at = time.time() + data.get("expire", 7200)
        return self._tenant_access_token
    
    async def request(self, method: str, path: str, **kwargs) -> dict:
        """发起 API 请求"""
        token = await self.get_tenant_access_token()
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        client = await self._get_client()
        resp = await client.request(method, url, headers=headers, **kwargs)
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"API error: {data}")
        return data.get("data", {})
    
    async def send_message(self, receive_id: str, receive_id_type: str, content: str, msg_type: str = "text") -> dict:
        """发送消息"""
        return await self.request("POST", "/open-apis/im/v1/messages", params={
            "receive_id_type": receive_id_type,
        }, json={
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": content,
        })
    
    async def reply_message(self, message_id: str, content: str, msg_type: str = "text", reply_in_thread: bool = False) -> dict:
        """回复消息"""
        data = {
            "msg_type": msg_type,
            "content": content,
        }
        if reply_in_thread:
            data["reply_in_thread"] = True
        return await self.request("POST", f"/open-apis/im/v1/messages/{message_id}/reply", json=data)
    
    async def get_message(self, message_id: str) -> dict:
        """获取消息"""
        return await self.request("GET", f"/open-apis/im/v1/messages/{message_id}")
    
    async def get_user_info(self, user_id: str, user_id_type: str = "open_id") -> dict:
        """获取用户信息"""
        return await self.request("GET", f"/open-apis/contact/v3/users/{user_id}", params={
            "user_id_type": user_id_type,
        })
    
    async def get_chat_info(self, chat_id: str) -> dict:
        """获取群组信息"""
        return await self.request("GET", f"/open-apis/im/v1/chats/{chat_id}")
    
    async def upload_image(self, image_type: str, image: bytes) -> dict:
        """上传图片"""
        token = await self.get_tenant_access_token()
        url = f"{self.base_url}/open-apis/im/v1/images"
        files = {"image": ("image.png", image, "image/png")}
        data = {"image_type": image_type}
        headers = {"Authorization": f"Bearer {token}"}
        client = await self._get_client()
        resp = await client.post(url, files=files, data=data, headers=headers)
        result = resp.json()
        if result.get("code") != 0:
            raise Exception(f"Upload image failed: {result}")
        return result.get("data", {})


class MessageStore:
    """消息存储和去重"""
    
    def __init__(self):
        self._messages: dict[str, float] = {}
    
    def is_duplicate(self, message_id: str) -> bool:
        """检查消息是否重复"""
        if message_id in self._messages:
            return True
        self._messages[message_id] = time.time()
        self._cleanup()
        return False
    
    def _cleanup(self):
        """清理过期消息记录"""
        now = time.time()
        expired = [k for k, v in self._messages.items() if now - v > 3600]
        for k in expired:
            del self._messages[k]


class PairingStore:
    """配对请求存储"""
    
    def __init__(self):
        self._requests: dict[str, dict] = {}  # code -> {id, name, created_at}
        self._approved: dict[str, str] = {}   # user_id -> ""
    
    def create_pairing_request(self, user_id: str, user_name: str = "") -> tuple[str, bool]:
        """创建配对请求，返回 (code, is_new)"""
        # 检查是否已有配对请求
        for code, req in self._requests.items():
            if req["id"] == user_id:
                return code, False
        
        # 生成配对码
        import random
        import string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        self._requests[code] = {
            "id": user_id,
            "name": user_name,
            "created_at": time.time()
        }
        return code, True
    
    def approve_pairing(self, code: str) -> Optional[str]:
        """批准配对请求，返回用户ID"""
        if code not in self._requests:
            return None
        
        user_id = self._requests[code]["id"]
        self._approved[user_id] = ""
        del self._requests[code]
        return user_id
    
    def is_approved(self, user_id: str) -> bool:
        """检查用户是否已批准"""
        return user_id in self._approved
    
    def list_pending_requests(self) -> list[dict]:
        """列出待批准的配对请求"""
        return [
            {"code": code, "id": req["id"], "name": req["name"], "created_at": req["created_at"]}
            for code, req in self._requests.items()
        ]


class ConversationContext:
    """对话上下文管理"""
    
    def __init__(self, max_history: int = 10):
        self._conversations: dict[str, list[dict]] = defaultdict(list)
        self._max_history = max_history
        self._user_sessions: dict[str, str] = {}  # user_id -> session_id
    
    def add_message(self, user_id: str, role: str, content: str):
        """添加对话消息"""
        self._conversations[user_id].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        # 限制历史长度
        if len(self._conversations[user_id]) > self._max_history * 2:
            self._conversations[user_id] = self._conversations[user_id][-self._max_history * 2:]
    
    def get_history(self, user_id: str) -> list[dict]:
        """获取对话历史"""
        return self._conversations.get(user_id, [])
    
    def clear_history(self, user_id: str):
        """清除对话历史"""
        if user_id in self._conversations:
            del self._conversations[user_id]
        if user_id in self._user_sessions:
            del self._user_sessions[user_id]
    
    def set_session(self, user_id: str, session_id: str):
        """设置用户的会话ID"""
        self._user_sessions[user_id] = session_id
    
    def get_session(self, user_id: str) -> Optional[str]:
        """获取用户的会话ID"""
        return self._user_sessions.get(user_id)
    
    def get_messages_for_api(self, user_id: str) -> list[dict]:
        """获取适合 API 调用的消息格式"""
        history = self.get_history(user_id)
        return [{"role": msg["role"], "content": msg["content"]} for msg in history]


class PushMessageRequest(BaseModel):
    """主动推送消息请求"""
    to: str
    text: str
    msg_type: str = "text"


class StreamChatRequest(BaseModel):
    """流式聊天请求"""
    message: str
    to: str
    session_id: Optional[str] = None
    model: str = "minimax-m2.5-free"


class FeishuChannelService:
    """飞书 Channel 服务"""
    
    def __init__(self, config: FeishuConfig):
        self.config = config
        self.api = FeishuAPI(config)
        self.message_store = MessageStore()
        self.pairing_store = PairingStore()
        self.conversation_context = ConversationContext()
        self._bot_open_id: Optional[str] = None
        self._message_callbacks: list[callable] = []
        self._ws_task: Optional[asyncio.Task] = None
        self._running = False
        self._msg_queue: queue.Queue = queue.Queue()
        self._received_messages: list[dict] = []
        self._opencode_api_url: str = "http://localhost:18000"
    
    def set_opencode_api_url(self, url: str):
        """设置 OpenCode API 地址"""
        self._opencode_api_url = url
    
    async def push_message(self, to: str, text: str) -> dict:
        """
        主动推送消息到飞书
        供 OpenCode 服务调用
        """
        try:
            result = await self.send_message(to=to, text=text)
            logger.info(f"Push message sent to {to}: {text[:50]}...")
            return {"code": 0, "message_id": result.get("message_id")}
        except Exception as e:
            logger.error(f"Push message failed: {e}")
            return {"code": -1, "error": str(e)}
    
    async def stream_chat(self, user_id: str, message: str, session_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        流式聊天响应
        供 OpenCode 服务调用，返回流式响应
        """
        receive_id, receive_id_type = self._parse_target(f"user:{user_id}")
        
        # 获取对话历史
        messages = self.conversation_context.get_messages_for_api(user_id)
        messages.append({"role": "user", "content": message})
        
        # 发送初始消息
        try:
            initial_content = ""
            async with httpx.AsyncClient(timeout=300.0) as client:
                payload = {
                    "model": "minimax-m2.5-free",
                    "messages": messages,
                    "stream": True
                }
                
                async with client.stream(
                    "POST",
                    f"{self._opencode_api_url}/v1/chat/completions",
                    json=payload
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    initial_content += content
                                    yield f"data: {json.dumps({'content': content})}\n\n"
                            except json.JSONDecodeError:
                                continue
            
            # 保存对话历史
            self.conversation_context.add_message(user_id, "user", message)
            self.conversation_context.add_message(user_id, "assistant", initial_content)
            
            # 发送完成消息
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    async def get_weather(self, message: str) -> Optional[str]:
        """获取天气信息"""
        import re
        
        # 提取城市名称
        city = "北京"  # 默认城市
        patterns = [
            r"天气.*?(\S+?(?:市|区|省|县))",
            r"(\S+?(?:市|区|省|县))天气",
            r"(.+?)天气",
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                city = match.group(1).strip()
                break
        
        # 调用天气API (使用免费的 wttr.in)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # 使用 wttr.in API
                url = f"https://wttr.in/{city}?format=j1"
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    current = data.get("current_condition", [{}])[0]
                    
                    temp = current.get("temp_C", "N/A")
                    condition = current.get("weatherDesc", [{}])[0].get("value", "N/A")
                    humidity = current.get("humidity", "N/A")
                    wind = current.get("windspeedKmph", "N/A")
                    
                    result = f"""🌤️ {city}天气预报

温度: {temp}°C
天气: {condition}
湿度: {humidity}%
风速: {wind} km/h

数据来源: wttr.in"""
                    return result
                else:
                    return f"抱歉，无法获取 {city} 的天气信息"
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return f"抱歉，天气服务暂时不可用"
    
    async def call_opencode_api(self, user_message: str, context_messages: Optional[list[dict]] = None) -> Optional[str]:
        """调用 OpenCode API 处理用户消息"""
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                messages = []
                if context_messages:
                    messages.extend(context_messages)
                messages.append({"role": "user", "content": user_message})
                
                payload = {
                    "model": "minimax-m2.5-free",
                    "messages": messages
                }
                
                resp = await client.post(
                    f"{self._opencode_api_url}/v1/chat/completions",
                    json=payload
                )
                
                if resp.status_code != 200:
                    logger.error(f"OpenCode API error: {resp.status_code} {resp.text}")
                    return None
                
                result = resp.json()
                
                choices = result.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    logger.info(f"OpenCode API response: {content[:100]}...")
                    return content
                
                return None
                
        except Exception as e:
            logger.error(f"OpenCode API error: {e}")
            return None
    
    async def call_opencode_api_stream(self, user_message: str, context_messages: Optional[list[dict]] = None):
        """调用 OpenCode API 流式响应"""
        
        try:
            messages = []
            if context_messages:
                messages.extend(context_messages)
            messages.append({"role": "user", "content": user_message})
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                payload = {
                    "model": "minimax-m2.5-free",
                    "messages": messages,
                    "stream": True
                }
                
                async with client.stream(
                    "POST",
                    f"{self._opencode_api_url}/v1/chat/completions",
                    json=payload
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
                            
        except Exception as e:
            logger.error(f"OpenCode API stream error: {e}")
            yield f"[错误: {str(e)}]"
    
    async def start_websocket(self):
        """启动 WebSocket 连接"""
        if self._ws_task:
            return
        
        self._running = True
        self._ws_task = asyncio.create_task(self._websocket_loop())
        logger.info("WebSocket connection started")
    
    async def stop_websocket(self):
        """停止 WebSocket 连接"""
        self._running = False
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
            self._ws_task = None
        if hasattr(self, '_ws_client') and self._ws_client:
            try:
                # SDK 没有 stop 方法，通过设置标志让线程自然退出
                self._running = False
            except:
                pass
            self._ws_client = None
        logger.info("WebSocket connection stopped")
    
    async def _websocket_loop(self):
        """WebSocket 连接循环"""
        logger.info("WebSocket loop started")
        while self._running:
            try:
                await self._connect_websocket()
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            
            # 处理 queue 中的消息
            logger.info(f"Checking queue, size: {self._msg_queue.qsize()}")
            while not self._msg_queue.empty():
                try:
                    item = self._msg_queue.get_nowait()
                    context = item[0]
                    logger.info(f"Got message from queue: {context}")
                    await self._dispatch_message(context)
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"Process queue message error: {e}")
            
            if self._running:
                await asyncio.sleep(1)
    
    async def _connect_websocket(self):
        """建立 WebSocket 连接（使用飞书SDK，在独立进程中运行）"""
        import subprocess
        import threading
        import sys
        import os
        
        # 如果已有进程，先杀掉
        if hasattr(self, '_ws_process') and self._ws_process and self._ws_process.poll() is None:
            logger.info("WebSocket process already running")
            return
        
        logger.info("Starting Feishu WebSocket in separate process...")
        
        # 使用外部脚本
        ws_script_path = os.path.join(os.path.dirname(__file__), "feishu_ws_client.py")
        
        # 在独立进程中运行，传递配置
        env = os.environ.copy()
        env["FEISHU_APP_ID"] = self.config.app_id
        env["FEISHU_APP_SECRET"] = self.config.app_secret
        env["FEISHU_CALLBACK_URL"] = f"http://127.0.0.1:{self.config.webhook_port}{self.config.webhook_path.replace('/webhook', '/_internal/message')}"
        
        self._ws_process = subprocess.Popen(
            [sys.executable, ws_script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env
        )
        
        logger.info(f"WebSocket process started: {self._ws_process.pid}")
        
        # 读取输出
        def read_output():
            try:
                for line in self._ws_process.stdout:
                    logger.info(f"[WS] {line.strip()}")
            except Exception as e:
                logger.error(f"WebSocket output error: {e}")
        
        threading.Thread(target=read_output, daemon=True).start()
        
        logger.info(f"App ID: {self.config.app_id}")
        logger.info("WebSocket client started, waiting for messages...")
    
    async def _handle_ws_message(self, msg):
        """处理 WebSocket 消息"""
        if isinstance(msg, bytes):
            msg = msg.decode("utf-8")
        
        try:
            data = json.loads(msg)
        except:
            return
        
        msg_type = data.get("type")
        if msg_type != "event_callback":
            return
        
        event = data.get("event", {})
        event_msg_type = event.get("msg_type")
        
        if event_msg_type == "text":
            context = await self._handle_text_message(event)
        elif event_msg_type == "post":
            context = await self._handle_post_message(event)
        elif event_msg_type == "image":
            context = await self._handle_image_message(event)
        elif event_msg_type == "file":
            context = await self._handle_file_message(event)
        else:
            logger.info(f"Ignored message type: {event_msg_type}")
            return
        
        if context and self.message_store.is_duplicate(context.message_id):
            logger.info(f"Duplicate message ignored: {context.message_id}")
            return
        
        if context:
            await self._dispatch_message(context)
    
    def register_callback(self, callback: callable):
        """注册消息处理回调"""
        self._message_callbacks.append(callback)
    
    async def _handle_command(self, context: FeishuMessageContext, sender_id: str):
        """处理命令"""
        content = context.content.strip()
        parts = content.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if command == "/help":
            help_text = """🤖 OpenCode 飞书机器人命令：

/help - 显示帮助信息
/clear - 清除对话历史
/weather <城市> - 查询天气
/pairing - 显示配对信息

直接发送消息开始对话"""
            await self.send_message(to=f"user:{sender_id}", text=help_text)
        
        elif command == "/clear":
            self.conversation_context.clear_history(sender_id)
            await self.send_message(to=f"user:{sender_id}", text="✅ 对话历史已清除")
        
        elif command == "/weather":
            weather_info = await self.get_weather(args or context.content)
            if weather_info:
                await self.send_message(to=f"user:{sender_id}", text=weather_info)
            else:
                await self.send_message(to=f"user:{sender_id}", text="抱歉，无法获取天气信息")
        
        elif command == "/pairing":
            if self.pairing_store.is_approved(sender_id):
                await self.send_message(to=f"user:{sender_id}", text="✅ 您已完成配对，可以正常使用")
            else:
                code, is_new = self.pairing_store.create_pairing_request(sender_id, "")
                pairing_msg = self._build_pairing_message(sender_id, code)
                await self.send_message(to=f"user:{sender_id}", text=pairing_msg)
        
        elif command == "/status":
            status = f"""📊 状态信息：
- 服务运行中: {self._running}
- 队列大小: {self._msg_queue.qsize()}
- OpenCode API: {self._opencode_api_url}
- 对话历史: {len(self.conversation_context.get_history(sender_id))} 条"""
            await self.send_message(to=f"user:{sender_id}", text=status)
        
        else:
            await self.send_message(to=f"user:{sender_id}", text=f"未知命令: {command}\n输入 /help 查看可用命令")
    
    async def _process_user_message(self, context: FeishuMessageContext, sender_id: str):
        """处理用户消息"""
        content = context.content
        
        # # 检查天气
        # if "天气" in content:
        #     logger.info(f"Weather query detected from {sender_id}")
        #     try:
        #         weather_info = await self.get_weather(content)
        #         if weather_info:
        #             await self.send_message(to=f"user:{sender_id}", text=weather_info)
        #             logger.info(f"Weather info sent to {sender_id}")
        #     except Exception as e:
        #         logger.error(f"Failed to get weather: {e}")
        #     return
        
        # 获取对话历史
        context_messages = self.conversation_context.get_messages_for_api(sender_id)
        
        # 调用 OpenCode API
        logger.info(f"Calling OpenCode API for user message from {sender_id}, content: {content[:50]}")
        try:
            response_text = await self.call_opencode_api(content, context_messages)
            logger.info(f"OpenCode API returned: {response_text[:100] if response_text else 'None'}")
            if response_text:
                await self.send_message(to=f"user:{sender_id}", text=response_text)
                # 保存对话历史
                self.conversation_context.add_message(sender_id, "user", content)
                self.conversation_context.add_message(sender_id, "assistant", response_text)
                logger.info(f"OpenCode response sent to {sender_id}")
            else:
                logger.warning(f"No response from OpenCode API")
        except Exception as e:
            logger.error(f"Failed to call OpenCode API: {e}")
        
        # 分发消息
        await self._dispatch_message(context)
    
    async def _dispatch_message(self, context: FeishuMessageContext):
        """分发消息到注册的回调"""
        # 调试：存储消息
        self._received_messages.append(context.model_dump() if hasattr(context, 'model_dump') else context)
        if len(self._received_messages) > 100:
            self._received_messages = self._received_messages[-100:]
        
        # 未配对用户直接返回，不处理消息
        if context.chat_type == ChatType.P2P:
            sender_id = getattr(context, 'sender_open_id', '') or getattr(context, 'sender_id', '')
            if sender_id and not self.pairing_store.is_approved(sender_id):
                return
        
        # 分发消息到回调
        for callback in self._message_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(context)
                else:
                    callback(context)
            except Exception as e:
                logger.error(f"Message callback error: {e}")
    
    def _build_pairing_message(self, user_id: str, code: str) -> str:
        """构建配对消息"""
        return f"""OpenClaw: access not configured.

Your Feishu user id: {user_id}

Pairing code: {code}

Ask the bot owner to approve with:
/opencode pairing approve feishu {code}"""
    
    async def get_bot_info(self) -> dict:
        """获取机器人信息"""
        try:
            token = await self.api.get_tenant_access_token()
            url = f"{self.api.base_url}/open-apis/bot/v3/info"
            headers = {"Authorization": f"Bearer {token}"}
            client = await self.api._get_client()
            resp = await client.get(url, headers=headers)
            data = resp.json()
            if data.get("code") != 0:
                raise Exception(f"API error: {data}")
            return data
        except Exception as e:
            logger.warning(f"Failed to get bot info: {e}")
            return {}
    
    async def handle_webhook_event(self, event: dict) -> Optional[dict]:
        """处理 Webhook 事件"""
        event_type = event.get("type")
        
        if event_type == "url_verification":
            return {
                "challenge": event.get("challenge"),
            }
        
        if event_type == "event_callback":
            event_data = event.get("event", {})
            msg_type = event_data.get("msg_type")
            
            if msg_type == "text":
                return await self._handle_text_message(event_data)
            elif msg_type == "post":
                return await self._handle_post_message(event_data)
            elif msg_type == "image":
                return await self._handle_image_message(event_data)
            elif msg_type == "file":
                return await self._handle_file_message(event_data)
            else:
                logger.warning(f"Unsupported message type: {msg_type}")
        
        return None
    
    async def _handle_text_message(self, event_data: dict) -> dict:
        """处理文本消息"""
        message_id = event_data.get("message_id")
        chat_id = event_data.get("chat_id")
        chat_type = event_data.get("chat_type")
        content = event_data.get("content", {})
        
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except:
                pass
        
        text = content.get("text", "") if isinstance(content, dict) else str(content)
        
        sender_id = event_data.get("sender_id", {})
        if isinstance(sender_id, dict):
            sender_id = sender_id.get("open_id") or sender_id.get("user_id") or ""
        
        mentioned_bot = False
        if self._bot_open_id and isinstance(content, dict):
            mentions = content.get("mentions", [])
            for mention in mentions:
                mention_id = mention.get("id", {})
                if isinstance(mention_id, dict):
                    if (mention_id.get("open_id") == self._bot_open_id or 
                        mention_id.get("user_id") == self._bot_open_id or
                        mention_id.get("union_id") == self._bot_open_id):
                        mentioned_bot = True
                        break
                elif mention_id == self._bot_open_id:
                    mentioned_bot = True
                    break
        
        if not mentioned_bot and self._bot_open_id and text:
            import re
            mention_pattern = r"<@[^>]+>"
            if re.search(mention_pattern, text):
                mentioned_bot = True
        
        return FeishuMessageContext(
            chat_id=chat_id,
            message_id=message_id,
            sender_id=sender_id,
            sender_open_id=sender_id,
            chat_type=ChatType(chat_type) if chat_type in ["p2p", "group", "private"] else ChatType.P2P,
            content=text,
            content_type="text",
            mentioned_bot=mentioned_bot,
        ).model_dump()
    
    async def _handle_post_message(self, event_data: dict) -> dict:
        """处理富文本消息"""
        message_id = event_data.get("message_id")
        chat_id = event_data.get("chat_id")
        chat_type = event_data.get("chat_type")
        
        sender_id = event_data.get("sender_id", {})
        if isinstance(sender_id, dict):
            sender_id = sender_id.get("open_id") or sender_id.get("user_id") or ""
        
        content = event_data.get("content", {})
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except:
                pass
        
        post_content = ""
        mentioned_bot = False
        
        if isinstance(content, dict):
            post = content.get("post", {})
            if isinstance(post, dict):
                post_content = self._extract_post_text(post)
            
            if not mentioned_bot and self._bot_open_id and post_content:
                import re
                mention_pattern = rf"<@[a-zA-Z0-9_]+>|<@all>|<@here>|<@everyone>"
                if re.search(mention_pattern, post_content):
                    mentioned_bot = True
            
            mentions = content.get("mentions", [])
            for mention in mentions:
                if self._bot_open_id and mention.get("id") == self._bot_open_id:
                    mentioned_bot = True
                    break
        
        if not post_content:
            post_content = "[Rich text message]"
        
        return FeishuMessageContext(
            chat_id=chat_id,
            message_id=message_id,
            sender_id=sender_id,
            sender_open_id=sender_id,
            chat_type=ChatType(chat_type) if chat_type in ["p2p", "group", "private"] else ChatType.P2P,
            content=post_content,
            content_type="post",
            mentioned_bot=mentioned_bot,
        ).model_dump()
    
    def _extract_post_text(self, post: dict) -> str:
        """从 post 消息中提取文本内容"""
        parts = []
        body = post.get("body", {})
        if isinstance(body, dict):
            elements = body.get("elements", [])
            parts.extend(self._extract_elements_text(elements))
        return "\n".join(parts)
    
    def _extract_elements_text(self, elements: list) -> list:
        """递归提取元素文本"""
        result = []
        for element in elements:
            if not isinstance(element, dict):
                continue
            
            tag = element.get("tag")
            
            if tag == "text":
                text = element.get("text", "")
                if text:
                    result.append(text)
            
            elif tag == "a":
                text = element.get("text", "")
                if text:
                    result.append(text)
            
            elif tag == "at":
                user_id = element.get("user_id", "")
                name = element.get("name", "")
                if name:
                    result.append(f"@{name}")
                elif user_id:
                    result.append(f"@{user_id}")
            
            elif tag == "img":
                alt = element.get("alt", "")
                if alt:
                    result.append(f"[Image: {alt}]")
            
            elif tag == "div" or tag == "paragraph":
                children = element.get("elements", []) or element.get("text", "")
                if isinstance(children, list):
                    result.extend(self._extract_elements_text(children))
                elif isinstance(children, str) and children:
                    result.append(children)
            
            elif tag == "text_tag":
                content = element.get("content", "")
                if content:
                    result.append(content)
            
            elif tag == "embed":
                url = element.get("url", "")
                title = element.get("title", "")
                if title:
                    result.append(title)
                elif url:
                    result.append(url)
            
            else:
                text = element.get("text", "")
                if text:
                    result.append(text)
                
                children = element.get("elements", [])
                if children:
                    result.extend(self._extract_elements_text(children))
        
        return result
    
    async def _handle_image_message(self, event_data: dict) -> dict:
        """处理图片消息"""
        message_id = event_data.get("message_id")
        chat_id = event_data.get("chat_id")
        chat_type = event_data.get("chat_type")
        
        sender_id = event_data.get("sender_id", {})
        if isinstance(sender_id, dict):
            sender_id = sender_id.get("open_id") or sender_id.get("user_id") or ""
        
        return FeishuMessageContext(
            chat_id=chat_id,
            message_id=message_id,
            sender_id=sender_id,
            sender_open_id=sender_id,
            chat_type=ChatType(chat_type) if chat_type in ["p2p", "group", "private"] else ChatType.P2P,
            content="[Image message]",
            content_type="image",
        ).model_dump()
    
    async def _handle_file_message(self, event_data: dict) -> dict:
        """处理文件消息"""
        message_id = event_data.get("message_id")
        chat_id = event_data.get("chat_id")
        chat_type = event_data.get("chat_type")
        
        sender_id = event_data.get("sender_id", {})
        if isinstance(sender_id, dict):
            sender_id = sender_id.get("open_id") or sender_id.get("user_id") or ""
        
        return FeishuMessageContext(
            chat_id=chat_id,
            message_id=message_id,
            sender_id=sender_id,
            sender_open_id=sender_id,
            chat_type=ChatType(chat_type) if chat_type in ["p2p", "group", "private"] else ChatType.P2P,
            content="[File message]",
            content_type="file",
        ).model_dump()
    
    async def send_message(self, to: str, text: str, reply_to_message_id: Optional[str] = None, reply_in_thread: bool = False) -> dict:
        """发送消息"""
        receive_id, receive_id_type = self._parse_target(to)
        
        if reply_to_message_id:
            content = json.dumps({"text": text})
            result = await self.api.reply_message(
                reply_to_message_id, 
                content, 
                msg_type="text",
                reply_in_thread=reply_in_thread
            )
        else:
            content = json.dumps({"text": text})
            result = await self.api.send_message(receive_id, receive_id_type, content, "text")
        
        return {
            "message_id": result.get("message_id"),
            "chat_id": receive_id,
        }
    
    async def send_card(self, to: str, card: dict, reply_to_message_id: Optional[str] = None) -> dict:
        """发送卡片消息"""
        receive_id, receive_id_type = self._parse_target(to)
        
        if reply_to_message_id:
            result = await self.api.reply_message(
                reply_to_message_id,
                json.dumps(card),
                msg_type="interactive",
            )
        else:
            result = await self.api.send_message(receive_id, receive_id_type, json.dumps(card), "interactive")
        
        return {
            "message_id": result.get("message_id"),
            "chat_id": receive_id,
        }
    
    async def get_message(self, message_id: str) -> Optional[dict]:
        """获取消息"""
        try:
            result = await self.api.get_message(message_id)
            return result.get("message", {})
        except Exception as e:
            logger.error(f"Failed to get message: {e}")
            return None
    
    async def get_user_info(self, user_id: str) -> Optional[dict]:
        """获取用户信息"""
        try:
            result = await self.api.get_user_info(user_id)
            return result.get("user", {})
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None
    
    async def get_chat_info(self, chat_id: str) -> Optional[dict]:
        """获取群组信息"""
        try:
            result = await self.api.get_chat_info(chat_id)
            return result
        except Exception as e:
            logger.error(f"Failed to get chat info: {e}")
            return None
    
    def _parse_target(self, target: str) -> tuple[str, str]:
        """解析发送目标"""
        if target.startswith("user:"):
            return target[5:], "open_id"
        elif target.startswith("chat:"):
            return target[5:], "chat_id"
        elif target.startswith("email:"):
            return target[6:], "email"
        else:
            return target, "open_id"


class AppState:
    """应用状态"""
    
    def __init__(self):
        self.service: Optional[FeishuChannelService] = None
        self.config: Optional[FeishuConfig] = None


state = AppState()
router = APIRouter()


def decrypt_event(encrypt_key: str, encrypt: str) -> dict:
    """解密事件"""
    import base64
    
    key = base64.b64decode(encrypt_key)
    encrypted = base64.b64decode(encrypt)
    
    iv = key[:16]
    encrypted = encrypted[16:]
    
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(encrypted) + decryptor.update(b"" + decryptor.finalize())
    
    padding = decrypted[-1]
    decrypted = decrypted[:-padding]
    
    text = decrypted.decode("utf-8")
    return json.loads(text)


def verify_signature(encrypt_key: str, timestamp: str, nonce: str, encrypt: str, signature: str) -> bool:
    """验证签名"""
    import base64
    
    key = base64.b64decode(encrypt_key)
    sign_string = timestamp + nonce + encrypt
    
    h = hmac.new(key, sign_string.encode("utf-8"), hashlib.sha256)
    expected_signature = base64.b64encode(h.digest()).decode("utf-8")
    
    return signature == expected_signature


@router.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    timestamp: Optional[str] = Query(None),
    nonce: Optional[str] = Query(None),
    signature: Optional[str] = Query(None),
):
    """Webhook 回调入口"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    body = await request.body()
    content = body.decode("utf-8")
    
    try:
        event = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    if state.config.encrypt_key and event.get("encrypt"):
        if not signature or not timestamp or not nonce:
            raise HTTPException(status_code=400, detail="Missing signature parameters")
        if not verify_signature(
            state.config.encrypt_key,
            timestamp,
            nonce,
            event.get("encrypt", ""),
            signature
        ):
            raise HTTPException(status_code=401, detail="Invalid signature")
        event = decrypt_event(state.config.encrypt_key, event.get("encrypt", ""))
    
    if state.config.verification_token and event.get("token") != state.config.verification_token:
        raise HTTPException(status_code=401, detail="Invalid verification token")
    
    result = await state.service.handle_webhook_event(event)
    
    if event.get("type") == "url_verification":
        return result
    
    if event.get("type") == "event_callback" and result:
        context = FeishuMessageContext(**result)
        
        if state.service.message_store.is_duplicate(context.message_id):
            logger.info(f"Duplicate message ignored: {context.message_id}")
            return {"code": 0, "msg": "duplicate ignored"}
        
        await state.service._dispatch_message(context)
    
    return {"code": 0, "msg": "success"}


@router.post("/send_message")
async def send_message(req: SendMessageRequest):
    """发送消息"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    try:
        result = await state.service.send_message(
            to=req.to,
            text=req.text,
            reply_to_message_id=req.reply_to_message_id,
            reply_in_thread=req.reply_in_thread,
        )
        return {"code": 0, "data": result}
    except Exception as e:
        logger.error(f"Send message failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send_card")
async def send_card(req: SendCardRequest):
    """发送卡片消息"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    try:
        result = await state.service.send_card(
            to=req.to,
            card=req.card,
        )
        return {"code": 0, "data": result}
    except Exception as e:
        logger.error(f"Send card failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_message/{message_id}")
async def get_message(message_id: str):
    """获取消息"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    result = await state.service.get_message(message_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"code": 0, "data": result}


@router.get("/get_user_info/{user_id}")
async def get_user_info(user_id: str):
    """获取用户信息"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    result = await state.service.get_user_info(user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"code": 0, "data": result}


@router.get("/get_chat_info/{chat_id}")
async def get_chat_info(chat_id: str):
    """获取群组信息"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    result = await state.service.get_chat_info(chat_id)
    return {"code": 0, "data": result}


@router.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "feishu_channel"}


@router.get("/config")
async def get_config():
    """获取当前配置"""
    if not state.config:
        raise HTTPException(status_code=404, detail="Config not set")
    return {
        "code": 0,
        "data": {
            "app_id": state.config.app_id[:8] + "****" if state.config.app_id else None,
            "domain": state.config.domain,
            "connection_mode": state.config.connection_mode,
        }
    }


@router.post("/config")
async def set_config(config: FeishuConfig):
    """设置配置"""
    if state.service:
        await state.service.stop_websocket()
    
    state.config = config
    state.service = FeishuChannelService(config)
    
    bot_info = await state.service.get_bot_info()
    if bot_info:
        bot_data = bot_info.get("bot", {})
        state.service._bot_open_id = bot_data.get("open_id")
        logger.info(f"Bot open_id: {state.service._bot_open_id}")
    
    if config.connection_mode == ConnectionMode.WEBSOCKET:
        await state.service.start_websocket()
        logger.info(f"WebSocket mode enabled")
    else:
        logger.info(f"Webhook mode enabled")
    
    logger.info(f"Feishu channel service initialized with config: domain={config.domain}, mode={config.connection_mode}")
    return {"code": 0, "msg": "Config updated"}


class RegisterCallbackRequest(BaseModel):
    callback_url: str


@router.post("/register_callback")
async def register_callback(req: RegisterCallbackRequest):
    """注册消息处理回调"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    async def http_callback(context: FeishuMessageContext):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(req.callback_url, json=context.model_dump())
        except Exception as e:
            logger.error(f"Callback error: {e}")
    
    state.service.register_callback(http_callback)
    return {"code": 0, "msg": "Callback registered", "callback_url": req.callback_url}


@router.get("/bot_info")
async def get_bot_info():
    """获取机器人信息"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    bot_info = await state.service.get_bot_info()
    return {"code": 0, "data": bot_info}


@router.get("/pairing/list")
async def list_pairing_requests():
    """列出待批准的配对请求"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    requests = state.service.pairing_store.list_pending_requests()
    return {"code": 0, "data": {"requests": requests}}


@router.post("/pairing/approve")
async def approve_pairing(code: str = Body(..., embed=True)):
    """批准配对请求"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    user_id = state.service.pairing_store.approve_pairing(code)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Pairing code not found")
    
    return {"code": 0, "msg": "Approved", "user_id": user_id}


@router.get("/pairing/status/{user_id}")
async def pairing_status(user_id: str):
    """检查用户配对状态"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    approved = state.service.pairing_store.is_approved(user_id)
    return {"code": 0, "data": {"user_id": user_id, "approved": approved}}


@router.post("/pairing/approve_user/{user_id}")
async def approve_user(user_id: str):
    """直接批准用户 ID"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    state.service.pairing_store._approved[user_id] = ""
    return {"code": 0, "msg": "User approved", "user_id": user_id}


@router.get("/debug/messages")
async def debug_messages():
    """调试端点：查看接收到的消息"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return {"code": 0, "data": {
        "messages": state.service._received_messages,
        "running": state.service._running,
        "ws_client": str(hasattr(state.service, '_ws_client')),
        "queue_size": state.service._msg_queue.qsize() if hasattr(state.service, '_msg_queue') else 0
    }}


@router.post("/push")
async def push_message(req: PushMessageRequest):
    """
    主动推送消息到飞书
    供 OpenCode 服务或其他外部服务调用
    """
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    result = await state.service.push_message(to=req.to, text=req.text)
    return result


@router.get("/conversation/history/{user_id}")
async def get_conversation_history(user_id: str):
    """获取用户对话历史"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    history = state.service.conversation_context.get_history(user_id)
    return {"code": 0, "data": {"user_id": user_id, "history": history}}


@router.delete("/conversation/history/{user_id}")
async def clear_conversation_history(user_id: str):
    """清除用户对话历史"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    state.service.conversation_context.clear_history(user_id)
    return {"code": 0, "msg": "History cleared", "user_id": user_id}


@router.post("/conversation/stream")
async def stream_chat(req: StreamChatRequest):
    """
    流式聊天端点
    返回 SSE 流式响应
    """
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    sender_id = req.to.replace("user:", "")
    messages = state.service.conversation_context.get_messages_for_api(sender_id)
    
    async def event_generator():
        try:
            async for chunk in state.service.call_opencode_api_stream(req.message, messages):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            # 保存对话历史
            state.service.conversation_context.add_message(sender_id, "user", req.message)
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


class SetOpenCodeUrlRequest(BaseModel):
    url: str

@router.post("/config/opencode_url")
async def set_opencode_url(req: SetOpenCodeUrlRequest):
    """设置 OpenCode API URL"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    state.service.set_opencode_api_url(req.url)
    return {"code": 0, "msg": "OpenCode URL updated", "url": req.url}


@router.get("/config/opencode_url")
async def get_opencode_url():
    """获取 OpenCode API URL"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return {"code": 0, "data": {"url": state.service._opencode_api_url}}


@router.get("/events")
async def events():
    """
    SSE 事件流
    实时推送接收到的消息
    """
    import asyncio
    
    async def event_generator():
        queue = asyncio.Queue()
        
        async def callback(context):
            await queue.put(context)
        
        if state.service:
            state.service.register_callback(callback)
        
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {json.dumps(msg)}\n\n"
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'heartbeat', 'time': time.time()})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/messages")
async def get_messages(last_message_id: Optional[str] = None, limit: int = Query(50, ge=1, le=100)):
    """
    获取消息列表
    支持轮询拉取
    """
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    messages = state.service._received_messages
    
    if last_message_id:
        idx = next((i for i, m in enumerate(messages) if m.get("message_id") == last_message_id), -1)
        if idx >= 0:
            messages = messages[idx+1:]
    
    return {"code": 0, "data": {
        "messages": messages[-limit:],
        "total": len(messages)
    }}


@router.post("/_internal/message")
async def internal_message(req: dict):
    """内部端点：接收飞书 WebSocket 消息"""
    if not state.service:
        logger.warning("Service not initialized")
        return {"code": 0}
    
    logger.info(f"Received internal message: {req}")
    
    try:
        message_id = req.get("message_id", "")
        
        # 消息去重检查
        if message_id and state.service.message_store.is_duplicate(message_id):
            logger.info(f"Duplicate message ignored: {message_id}")
            return {"code": 0, "msg": "duplicate ignored"}
        
        context = FeishuMessageContext(
            chat_id=req.get("chat_id", ""),
            message_id=message_id,
            sender_id=req.get("sender_id", ""),
            sender_open_id=req.get("sender_open_id", ""),
            chat_type=ChatType(req.get("chat_type", "p2p")),
            content=req.get("content", ""),
            content_type=req.get("content_type", "text"),
            mentioned_bot=req.get("mentioned_bot", False),
        )
        
        sender_id = context.sender_open_id or context.sender_id
        
        # 检查命令
        if context.content.startswith("/"):
            await state.service._handle_command(context, sender_id)
            return {"code": 0}
        
        # 检查配对
        if context.chat_type == ChatType.P2P and sender_id:
            if not state.service.pairing_store.is_approved(sender_id):
                code, is_new = state.service.pairing_store.create_pairing_request(sender_id, "")
                logger.info(f"Pairing request created for {sender_id}: code={code}")
                
                pairing_message = state.service._build_pairing_message(sender_id, code)
                try:
                    await state.service.send_message(to=f"user:{sender_id}", text=pairing_message)
                except Exception as e:
                    logger.error(f"Failed to send pairing message: {e}")
                return {"code": 0, "msg": "pairing_required"}
        
        # 处理消息
        await state.service._process_user_message(context, sender_id)
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
    
    return {"code": 0}


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Feishu Channel API starting...")
        yield
        if state.service:
            await state.service.api.close()
        logger.info("Feishu Channel API shutting down...")
    
    app = FastAPI(
        title="Feishu Channel API",
        description="飞书 Channel 本地服务 - 基于 openclaw feishu 插件实现",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
