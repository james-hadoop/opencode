import sys
import json
import os
import requests
from lark_oapi import EventDispatcherHandler, ws, im, LogLevel

APP_ID = os.environ.get("FEISHU_APP_ID", "cli_a92e7a228b38dcd4")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "hpIQx2hMoNO2XT5NmvNU7bPIyaDtGVZl")
CALLBACK_URL = os.environ.get("FEISHU_CALLBACK_URL", "http://127.0.0.1:8000/_internal/message")

def handle_message(data):
    try:
        print(f"RAW_DATA: {data}", flush=True)
        
        event = data.event
        if not event:
            print("No event in data", flush=True)
            return
        
        print(f"Event type: {type(event)}", flush=True)
        print(f"Event: {event}", flush=True)
        
        if not hasattr(event, 'message') or not event.message:
            print("No message in event", flush=True)
            return
        
        msg_type = event.message.message_type
        message_id = event.message.message_id
        chat_id = event.message.chat_id
        chat_type = event.message.chat_type
        
        print(f"Message: type={msg_type}, id={message_id}, chat={chat_id}", flush=True)
        
        sender_id = ""
        if event.sender and event.sender.sender_id:
            sender_id = event.sender.sender_id.open_id or event.sender.sender_id.user_id or ""
        
        print(f"Sender: {sender_id}", flush=True)
        
        # 构建消息内容
        if msg_type == "text":
            content = event.message.content or "{}"
            try:
                content_dict = json.loads(content)
                text = content_dict.get("text", "")
            except:
                text = content
        else:
            text = f"[{msg_type} message]"
        
        print(f"Content: {text}", flush=True)
        
        # 发送消息到主服务
        msg_data = {
            "chat_id": chat_id or "",
            "message_id": message_id or "",
            "sender_id": sender_id,
            "sender_open_id": sender_id,
            "chat_type": chat_type or "p2p",
            "content": text,
            "content_type": msg_type,
            "mentioned_bot": False
        }
        
        print(f"Sending to callback: {msg_data}", flush=True)
        
        try:
            r = requests.post(CALLBACK_URL, json=msg_data, timeout=5)
            print(f"Callback response: {r.status_code} {r.text}", flush=True)
        except Exception as e:
            print(f"Callback error: {e}", flush=True)
        
        print(f"MSG:{message_id}", flush=True)
        
    except Exception as e:
        import traceback
        print(f"ERROR:{e}", flush=True)
        print(traceback.format_exc(), flush=True)

event_handler = EventDispatcherHandler.builder(
    APP_ID,
    APP_SECRET
).register_p2_im_message_receive_v1(handle_message).build()

client = ws.Client(
    app_id=APP_ID,
    app_secret=APP_SECRET,
    event_handler=event_handler,
    log_level=LogLevel.INFO
)

print("STARTING_WS", flush=True)
sys.stdout.flush()
client.start()
