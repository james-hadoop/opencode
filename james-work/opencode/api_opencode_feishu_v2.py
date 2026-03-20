"""
飞书 Channel FastAPI 本地服务 v2

基于官方 lark_oapi SDK 实现：
- WebSocket 长连接接收消息
- 使用官方 SDK 发送消息
- 消息处理和权限检查
- 工具 API (发送消息、获取消息、获取用户/群组信息)
- OpenCode 主动推送支持
"""

import asyncio
import json
import logging
import os
import queue
import threading
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any, Optional

import lark_oapi as lark
from lark_oapi import EventDispatcherHandler, ws, im, LogLevel
from fastapi import APIRouter, BackgroundTasks, Body, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatType(str, Enum):
    P2P = "p2p"
    GROUP = "group"
    PRIVATE = "private"


class FeishuConfig(BaseModel):
    app_id: str = "cli_a92e7a228b38dcd4"
    app_secret: str = "hpIQx2hMoNO2XT5NmvNU7bPIyaDtGVZl"
    auto_approve_users: bool = True


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
    content: str
    content_type: str = "text"


class SendMessageRequest(BaseModel):
    to: str
    text: str
    msg_type: str = "text"
    reply_to_message_id: Optional[str] = None
    reply_in_thread: bool = False


class PushMessageRequest(BaseModel):
    """主动推送消息请求"""
    to: str
    text: str
    msg_type: str = "text"


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


class ConversationContext:
    """对话上下文管理"""
    
    def __init__(self, max_history: int = 10):
        self._conversations: dict[str, list[dict]] = defaultdict(list)
        self._max_history = max_history
        self._user_sessions: dict[str, str] = {}
    
    def add_message(self, user_id: str, role: str, content: str):
        """添加对话消息"""
        self._conversations[user_id].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
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
    
    def get_messages_for_api(self, user_id: str) -> list[dict]:
        """获取适合 API 调用的消息格式"""
        history = self.get_history(user_id)
        return [{"role": msg["role"], "content": msg["content"]} for msg in history]


class FeishuChannelService:
    """飞书 Channel 服务 (基于 lark_oapi SDK)"""
    
    def __init__(self, config: FeishuConfig):
        self.config = config
        self.client = lark.Client.builder().app_id(config.app_id).app_secret(config.app_secret).build()
        self.message_store = MessageStore()
        self.conversation_context = ConversationContext()
        self._bot_open_id: Optional[str] = None
        self._message_callbacks: list[callable] = []
        self._running = False
        self._ws_client: Optional[lark.ws.Client] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._opencode_api_url: str = "http://localhost:18000"
        self._auto_approve_users: bool = config.auto_approve_users
        
        if self._auto_approve_users:
            logger.info("Auto-approve users mode enabled")
    
    def set_opencode_api_url(self, url: str):
        """设置 OpenCode API 地址"""
        self._opencode_api_url = url
    
    async def push_message(self, to: str, text: str) -> dict:
        """主动推送消息到飞书"""
        try:
            result = await self.send_message(to=to, text=text)
            logger.info(f"Push message sent to {to}: {text[:50]}...")
            return {"code": 0, "message_id": result.get("message_id")}
        except Exception as e:
            logger.error(f"Push message failed: {e}")
            return {"code": -1, "error": str(e)}
    
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
        except httpx.ConnectError as e:
            logger.error(f"OpenCode API connection failed: {e}")
            raise Exception(f"OpenCode服务未运行，请确保 OpenCode 服务已启动并监听在 {self._opencode_api_url}")
        except Exception as e:
            logger.error(f"OpenCode API error: {e}")
            return None
    
    async def _process_user_message(self, context: FeishuMessageContext, sender_id: str):
        """处理用户消息，转发到 OpenCode 服务"""
        content = context.content
        
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
                await self.send_message(
                    to=f"user:{sender_id}", 
                    text=f"抱歉，OpenCode 服务暂时没有返回响应。请检查 OpenCode 服务是否正常运行。"
                )
                logger.warning(f"No response from OpenCode API")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to call OpenCode API: {e}")
            
            # 发送友好的错误消息给用户
            if "OpenCode服务未运行" in error_msg:
                await self.send_message(
                    to=f"user:{sender_id}",
                    text=f"⚠️ {error_msg}\n\n请启动 OpenCode 服务后重试。\n当前配置的 OpenCode API 地址: {self._opencode_api_url}"
                )
            else:
                await self.send_message(
                    to=f"user:{sender_id}",
                    text=f"抱歉，处理消息时发生错误: {error_msg[:100]}"
                )
    
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
/status - 显示状态信息

直接发送消息开始对话"""
            await self.send_message(to=f"user:{sender_id}", text=help_text)
        
        elif command == "/clear":
            self.conversation_context.clear_history(sender_id)
            await self.send_message(to=f"user:{sender_id}", text="✅ 对话历史已清除")
        
        elif command == "/status":
            status = f"""📊 状态信息：
- 服务运行中: {self._running}
- OpenCode API: {self._opencode_api_url}
- 对话历史: {len(self.conversation_context.get_history(sender_id))} 条"""
            await self.send_message(to=f"user:{sender_id}", text=status)
        
        else:
            await self.send_message(to=f"user:{sender_id}", text=f"未知命令: {command}\n输入 /help 查看可用命令")
    
    async def _dispatch_message(self, context: FeishuMessageContext):
        """分发消息到注册的回调"""
        # 分发消息到回调
        for callback in self._message_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(context)
                else:
                    callback(context)
            except Exception as e:
                logger.error(f"Message callback error: {e}")
    
    def register_callback(self, callback: callable):
        """注册消息处理回调"""
        self._message_callbacks.append(callback)
    
    async def start_websocket(self):
        """启动 WebSocket 长连接"""
        if self._running:
            return
        
        self._running = True
        
        def handle_message_read(data):
            """处理消息已读事件 (同步函数)"""
            try:
                event = data.event
                if event and event.message:
                    message_id = event.message.message_id
                    logger.info(f"Message read: {message_id}")
            except Exception as e:
                logger.debug(f"Ignored message read event: {e}")
        
        def run_ws():
            try:
                # 创建事件处理器
                event_handler = (
                    EventDispatcherHandler.builder(self.config.app_id, self.config.app_secret)
                    .register_p2_im_message_receive_v1(self._handle_ws_message)
                    .build()
                )
            except Exception as e:
                logger.warning(f"Failed to create event handler with p1 register: {e}")
                # 备用：只注册 p2 事件
                event_handler = (
                    EventDispatcherHandler.builder(self.config.app_id, self.config.app_secret)
                    .register_p2_im_message_receive_v1(self._handle_ws_message)
                    .build()
                )
            
            # 创建 WebSocket 客户端
            self._ws_client = ws.Client(
                app_id=self.config.app_id,
                app_secret=self.config.app_secret,
                event_handler=event_handler,
                log_level=LogLevel.INFO,
            )
            
            logger.info("WebSocket client starting...")
            self._ws_client.start()
        
        # 在独立线程中运行 WebSocket
        self._ws_thread = threading.Thread(target=run_ws, daemon=True)
        self._ws_thread.start()
        
        # 等待 WebSocket 连接建立
        await asyncio.sleep(2)
        logger.info("WebSocket connection started")
    
    async def stop_websocket(self):
        """停止 WebSocket 连接"""
        self._running = False
        if self._ws_client:
            try:
                # WebSocket 客户端没有 stop 方法，通过设置标志让线程自然退出
                # 实际应用中可能需要更优雅的退出机制
                pass
            except Exception as e:
                logger.error(f"Stop websocket error: {e}")
        if self._ws_thread:
            self._ws_thread.join(timeout=5)
        logger.info("WebSocket connection stopped")
    
    def _handle_ws_message(self, data):
        """处理 WebSocket 接收到的消息 (同步函数，供 lark_oapi SDK 调用)"""
        try:
            event = data.event
            if not event or not event.message:
                return
            
            msg_type = event.message.message_type
            message_id = event.message.message_id
            chat_id = event.message.chat_id
            chat_type = event.message.chat_type
            
            # 获取发送者 ID
            sender_id = ""
            if event.sender and event.sender.sender_id:
                sender_id = event.sender.sender_id.open_id or event.sender.sender_id.user_id or ""
            
            # 解析消息内容
            content = ""
            if msg_type == "text":
                try:
                    content_dict = json.loads(event.message.content or "{}")
                    content = content_dict.get("text", "")
                except:
                    content = event.message.content or ""
            else:
                content = f"[{msg_type} message]"
            
            logger.info(f"Received message: type={msg_type}, from={sender_id}, chat={chat_id}")
            
            # 构建消息上下文
            context = FeishuMessageContext(
                chat_id=chat_id or "",
                message_id=message_id or "",
                sender_id=sender_id,
                sender_open_id=sender_id,
                chat_type=ChatType(chat_type) if chat_type in ["p2p", "group", "private"] else ChatType.P2P,
                content=content,
                content_type=msg_type,
                mentioned_bot=False,
            )
            
            # 消息去重
            if message_id and self.message_store.is_duplicate(message_id):
                logger.info(f"Duplicate message ignored: {message_id}")
                return
            
            # 处理异步操作 - 使用线程中的新事件循环
            def run_async():
                asyncio.run(self._handle_message_async(context, message_id, chat_id, chat_type, content))
            
            thread = threading.Thread(target=run_async, daemon=True)
            thread.start()
            
        except Exception as e:
            import traceback
            logger.error(f"Error handling ws message: {e}")
            logger.error(traceback.format_exc())
    
    async def _handle_message_async(self, context, message_id, chat_id, chat_type, content):
        """异步处理消息的辅助方法"""
        
        # 原样返回消息 (Echo) - 类似 echo_bot
        echo_content = json.dumps({"text": f"收到消息: {content}"})
        
        try:
            if chat_type == "p2p":
                # 私聊：发送新消息
                request = (
                    im.v1.CreateMessageRequest.builder()
                    .receive_id_type("chat_id")
                    .request_body(
                        im.v1.CreateMessageRequestBody.builder()
                        .receive_id(chat_id)
                        .msg_type("text")
                        .content(echo_content)
                        .build()
                    )
                    .build()
                )
                response = self.client.im.v1.message.create(request)
                if not response.success():
                    logger.warning(f"Echo failed: {response.code} {response.msg}")
            else:
                # 群组：回复消息
                request = (
                    im.v1.ReplyMessageRequest.builder()
                    .message_id(message_id)
                    .request_body(
                        im.v1.ReplyMessageRequestBody.builder()
                        .msg_type("text")
                        .content(echo_content)
                        .build()
                    )
                    .build()
                )
                response = self.client.im.v1.message.reply(request)
                if not response.success():
                    logger.warning(f"Echo failed: {response.code} {response.msg}")
        except Exception as e:
            logger.error(f"Echo error: {e}")
        
        # 分发消息
        await self._dispatch_message(context)
        
        # 检查命令
        sender_id = context.sender_open_id or context.sender_id
        if context.content.startswith("/"):
            await self._handle_command(context, sender_id)
            return
        
        # 处理用户消息（转发到 OpenCode 服务）
        await self._process_user_message(context, sender_id)
    
    async def send_message(self, to: str, text: str, reply_to_message_id: Optional[str] = None, reply_in_thread: bool = False) -> dict:
        """发送消息 (使用 lark_oapi SDK)"""
        receive_id, receive_id_type = self._parse_target(to)
        
        content = json.dumps({"text": text})
        
        try:
            if reply_to_message_id:
                # 回复消息
                request = (
                    im.v1.ReplyMessageRequest.builder()
                    .message_id(reply_to_message_id)
                    .request_body(
                        im.v1.ReplyMessageRequestBody.builder()
                        .msg_type("text")
                        .content(content)
                        .build()
                    )
                    .build()
                )
                response = self.client.im.v1.message.reply(request)
                
                if not response.success():
                    raise Exception(f"Reply failed: {response.code} {response.msg}")
                
                return {"message_id": response.data.message_id, "chat_id": receive_id}
            else:
                # 发送新消息
                request = (
                    im.v1.CreateMessageRequest.builder()
                    .receive_id_type(receive_id_type)
                    .request_body(
                        im.v1.CreateMessageRequestBody.builder()
                        .receive_id(receive_id)
                        .msg_type("text")
                        .content(content)
                        .build()
                    )
                    .build()
                )
                response = self.client.im.v1.message.create(request)
                
                if not response.success():
                    raise Exception(f"Send failed: {response.code} {response.msg}")
                
                return {"message_id": response.data.message_id, "chat_id": receive_id}
                
        except Exception as e:
            logger.error(f"Send message error: {e}")
            raise
    
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
    
    async def get_bot_info(self) -> dict:
        """获取机器人信息"""
        try:
            # 使用 im/v1/bot/info 接口获取机器人信息
            # lark_oapi SDK 的方式
            response = self.client.im.v1.bot.info.get({})
            if response.success():
                return {"bot": {"open_id": response.data.get("open_id")} if response.data else {}}
        except Exception as e:
            logger.info(f"get_bot_info not available: {e}")
        
        # 如果获取失败，返回空信息，不影响主要功能
        return {}


class AppState:
    """应用状态"""
    
    def __init__(self):
        self.service: Optional[FeishuChannelService] = None
        self.config: Optional[FeishuConfig] = None


state = AppState()
router = APIRouter()


@router.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "feishu_channel_v2"}


@router.get("/config")
async def get_config():
    """获取当前配置"""
    if not state.config:
        raise HTTPException(status_code=404, detail="Config not set")
    return {
        "code": 0,
        "data": {
            "app_id": state.config.app_id[:8] + "****" if state.config.app_id else None,
            "auto_approve_users": state.config.auto_approve_users,
        }
    }


@router.post("/config")
async def set_config(config: FeishuConfig):
    """设置配置"""
    if state.service:
        await state.service.stop_websocket()
    
    state.config = config
    state.service = FeishuChannelService(config)
    
    # 获取机器人信息
    try:
        bot_info = await state.service.get_bot_info()
        if bot_info:
            state.service._bot_open_id = bot_info.get("bot", {}).get("open_id")
            logger.info(f"Bot open_id: {state.service._bot_open_id}")
    except Exception as e:
        logger.warning(f"Failed to get bot info: {e}")
    
    # 启动 WebSocket 连接
    await state.service.start_websocket()
    
    logger.info(f"Feishu channel service v2 initialized with config: app_id={config.app_id[:8]}****")
    return {"code": 0, "msg": "Config updated, WebSocket started"}


@router.post("/opencode_url")
async def set_opencode_url(req: dict):
    """设置 OpenCode API URL"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    url = req.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing url")
    
    state.service.set_opencode_api_url(url)
    logger.info(f"OpenCode API URL set to: {url}")
    return {"code": 0, "msg": f"OpenCode API URL updated to: {url}"}


@router.get("/opencode_url")
async def get_opencode_url():
    """获取 OpenCode API URL"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return {"code": 0, "data": {"url": state.service._opencode_api_url}}


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


@router.post("/push_message")
async def push_message(req: PushMessageRequest):
    """推送消息 (供外部服务调用)"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    result = await state.service.push_message(to=req.to, text=req.text)
    return result


@router.get("/get_bot_info")
async def get_bot_info():
    """获取机器人信息"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    bot_info = await state.service.get_bot_info()
    return {"code": 0, "data": bot_info}


@router.post("/register_callback")
async def register_callback(req: dict):
    """注册消息处理回调"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    callback_url = req.get("callback_url")
    if not callback_url:
        raise HTTPException(status_code=400, detail="Missing callback_url")
    
    async def http_callback(context: FeishuMessageContext):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(callback_url, json=context.model_dump())
        except Exception as e:
            logger.error(f"Callback error: {e}")
    
    state.service.register_callback(http_callback)
    return {"code": 0, "msg": "Callback registered", "callback_url": callback_url}


@router.get("/conversation_history/{user_id}")
async def get_conversation_history(user_id: str, limit: int = Query(10, ge=1, le=100)):
    """获取对话历史"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    messages = state.service.conversation_context.get_history(user_id)
    return {
        "code": 0,
        "data": {
            "messages": messages[-limit:],
            "total": len(messages)
        }
    }


@router.delete("/conversation_history/{user_id}")
async def clear_conversation_history(user_id: str):
    """清除对话历史"""
    if not state.service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    state.service.conversation_context.clear_history(user_id)
    return {"code": 0, "msg": "Conversation history cleared"}


# 默认配置
DEFAULT_APP_ID = "cli_a92e7a228b38dcd4"
DEFAULT_APP_SECRET = "hpIQx2hMoNO2XT5NmvNU7bPIyaDtGVZl"


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Feishu Channel API v2 starting...")
        
        # 自动初始化服务配置
        if not state.service:
            config = FeishuConfig(
                app_id=DEFAULT_APP_ID,
                app_secret=DEFAULT_APP_SECRET,
                auto_approve_users=True,
            )
            
            state.config = config
            state.service = FeishuChannelService(config)
            
            # 获取机器人信息
            try:
                bot_info = await state.service.get_bot_info()
                if bot_info:
                    bot_data = bot_info.get("bot", {})
                    state.service._bot_open_id = bot_data.get("open_id")
                    logger.info(f"Bot open_id: {state.service._bot_open_id}")
            except Exception as e:
                logger.warning(f"Failed to get bot info: {e}")
            
            # 启动 WebSocket 连接
            await state.service.start_websocket()
            
            logger.info(f"Feishu channel service v2 initialized, app_id: {DEFAULT_APP_ID[:8]}****")
        
        yield
        
        if state.service:
            await state.service.stop_websocket()
        logger.info("Feishu Channel API v2 shutting down...")
    
    app = FastAPI(
        title="Feishu Channel API v2",
        description="飞书 Channel 本地服务 - 基于 lark_oapi SDK",
        version="2.0.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
