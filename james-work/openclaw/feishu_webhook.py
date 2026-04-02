# 第一步：安装飞书官方 SDK
# pip install larksuite-api

import asyncio
from larksuiteoapi import Config
from larksuiteoapi.im.v1 import P2Receiver

# 替换为你的应用参数
APP_ID = "cli_a921c3836bb95bcb"
APP_SECRET = "S8Dz0bu4QU7Gq8EEHfUricCTwjxJpVp4"
VERIFICATION_TOKEN = "yW3HnMBsWaYrrjS7VV4W3fZR0vOQEBZK"

# 1. 配置 SDK（沙箱环境用 lark_sandbox，正式环境用 lark）
config = Config.new_internal_app_config(APP_ID, APP_SECRET)
# 开启调试模式，方便看连接日志
config.debug = True

# 2. 定义消息接收回调（收到用户消息时触发）
def on_message_receive(event):
    """处理收到的消息"""
    print("✅ 收到用户消息：", event)
    # 这里可以添加回复消息的逻辑（后续扩展）
    return True

# 3. 启动 WebSocket 长连接
async def start_websocket():
    # 创建 P2 接收器（处理消息事件）
    receiver = P2Receiver(config, VERIFICATION_TOKEN)
    # 注册 im.message.receive_v1 事件的回调
    receiver.register("im.message.receive_v1", on_message_receive)
    
    print("🔌 正在建立 WebSocket 长连接...")
    # 启动长连接（会一直运行，不要关闭）
    await receiver.start()

if __name__ == "__main__":
    try:
        # 运行异步任务
        asyncio.run(start_websocket())
    except KeyboardInterrupt:
        print("\n❌ 长连接已手动关闭")
    except Exception as e:
        print(f"❌ 连接失败：{str(e)}")
        print("排查：1. APP_ID/SECRET 是否正确 2. 网络是否通飞书服务器 3. 应用是否已启用机器人能力")