"""
OpenCode API 代理客户端示例

演示如何通过 app_opencode_api_proxy.py 提供的服务调用 minimax2.5-free 模型
"""

import requests
import json
from typing import Optional, List, Dict, Any


class OpenCodeAPIClient:
    """OpenCode API 代理客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        初始化客户端
        
        Args:
            base_url: 代理服务的基础URL
        """
        self.base_url = base_url.rstrip("/")
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态信息
        """
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        列出所有可用模型
        
        Returns:
            模型列表
        """
        response = requests.get(f"{self.base_url}/v1/models")
        response.raise_for_status()
        return response.json()["data"]
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "minimax-m2.5-free",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        发送聊天完成请求（非流式）
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "你好"}]
            model: 模型名称，默认为 minimax-m2.5-free
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            stream: 是否使用流式输出
        
        Returns:
            响应数据
        """
        url = f"{self.base_url}/v1/chat/completions"
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
        
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "minimax-m2.5-free",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        发送聊天完成请求（流式）
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成token数
        
        Yields:
            流式响应片段
        """
        url = f"{self.base_url}/v1/chat/completions/stream"
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }
        
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue
    
    def create_session(self) -> Dict[str, Any]:
        """
        创建新会话（使用 OpenCode 原生 API）
        
        Returns:
            会话信息
        """
        response = requests.post(f"{self.base_url}/v1/sessions")
        response.raise_for_status()
        return response.json()
    
    def send_session_message(
        self,
        session_id: str,
        parts: List[Dict[str, Any]],
        model_config: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        向指定会话发送消息（使用 OpenCode 原生 API）
        
        Args:
            session_id: 会话ID
            parts: 消息部分列表，例如 [{"text": "你好"}]
            model_config: 模型配置，例如 {"provider": "minimax", "model": "minimax-m2.5-free"}
        
        Returns:
            响应数据
        """
        url = f"{self.base_url}/v1/sessions/{session_id}/message"
        
        payload = {
            "parts": parts
        }
        
        if model_config:
            payload["model_config"] = model_config
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()


# ========== 使用示例 ==========

def example_simple_chat():
    """简单聊天示例"""
    print("=" * 60)
    print("示例1: 简单聊天")
    print("=" * 60)
    
    client = OpenCodeAPIClient()
    
    # 检查服务健康状态
    print("\n1. 健康检查:")
    health = client.health_check()
    print(f"   状态: {health['status']}")
    print(f"   OpenCode连接: {health['opencode_connected']}")
    
    # 列出可用模型
    print("\n2. 可用模型:")
    models = client.list_models()
    for model in models:
        print(f"   - {model['id']}")
    
    # 发送简单消息
    print("\n3. 发送消息:")
    response = client.chat_completion(
        messages=[{"role": "user", "content": "你好，请用一句话介绍你自己"}],
        model="minimax-m2.5-free"
    )
    
    print(f"   消息: {response['choices'][0]['message']['content']}")
    print(f"   使用模型: {response['model']}")
    print(f"   Token使用: {response['usage']}")


def example_multi_turn_chat():
    """多轮对话示例"""
    print("\n" + "=" * 60)
    print("示例2: 多轮对话")
    print("=" * 60)
    
    client = OpenCodeAPIClient()
    
    # 多轮对话
    conversation = [
        {"role": "user", "content": "我想学Python，给我一些建议"},
        {"role": "assistant", "content": "学习Python是个很好的选择！以下是一些建议："},
        {"role": "user", "content": "具体应该从哪里开始？"}
    ]
    
    print("\n对话历史:")
    for msg in conversation:
        print(f"  {msg['role']}: {msg['content']}")
    
    print("\nAI回复:")
    response = client.chat_completion(
        messages=conversation,
        model="minimax-m2.5-free"
    )
    
    print(f"  {response['choices'][0]['message']['content']}")


def example_streaming_chat():
    """流式聊天示例"""
    print("\n" + "=" * 60)
    print("示例3: 流式聊天")
    print("=" * 60)
    
    client = OpenCodeAPIClient()
    
    prompt = "请写一首关于春天的诗"
    print(f"\n问题: {prompt}")
    print("\n回答（流式）:")
    print("  ", end="")
    
    for chunk in client.chat_completion_stream(
        messages=[{"role": "user", "content": prompt}],
        model="minimax-m2.5-free"
    ):
        if "choices" in chunk and len(chunk["choices"]) > 0:
            delta = chunk["choices"][0].get("delta", {})
            if "content" in delta:
                print(delta["content"], end="", flush=True)
    
    print()  # 换行


def example_with_parameters():
    """带参数的聊天示例"""
    print("\n" + "=" * 60)
    print("示例4: 带参数的聊天")
    print("=" * 60)
    
    client = OpenCodeAPIClient()
    
    # 使用不同的温度参数
    temperatures = [0.1, 0.7, 1.0]
    
    for temp in temperatures:
        print(f"\n温度={temp}:")
        response = client.chat_completion(
            messages=[{"role": "user", "content": "给我讲一个笑话"}],
            model="minimax-m2.5-free",
            temperature=temp
        )
        print(f"  {response['choices'][0]['message']['content']}")


def example_native_api():
    """使用 OpenCode 原生 API"""
    print("\n" + "=" * 60)
    print("示例5: 使用 OpenCode 原生 API")
    print("=" * 60)
    
    client = OpenCodeAPIClient()
    
    # 创建会话
    print("\n1. 创建会话:")
    session = client.create_session()
    session_id = session.get("sessionID") or session.get("session_id") or session.get("id")
    print(f"   会话ID: {session_id}")
    
    # 发送消息
    print("\n2. 发送消息:")
    response = client.send_session_message(
        session_id=session_id,
        parts=[{"text": "你好，使用原生API打招呼"}],
        model_config={
            "provider": "minimax",
            "model": "minimax-m2.5-free"
        }
    )
    
    print(f"   响应: {json.dumps(response, indent=2, ensure_ascii=False)}")


def example_error_handling():
    """错误处理示例"""
    print("\n" + "=" * 60)
    print("示例6: 错误处理")
    print("=" * 60)
    
    client = OpenCodeAPIClient()
    
    # 测试无效的模型
    print("\n1. 使用不存在的模型:")
    try:
        response = client.chat_completion(
            messages=[{"role": "user", "content": "你好"}],
            model="invalid-model"
        )
    except requests.exceptions.HTTPError as e:
        print(f"   错误: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 测试服务不可用
    print("\n2. 连接到不可用的服务:")
    invalid_client = OpenCodeAPIClient("http://localhost:9999")
    try:
        response = invalid_client.chat_completion(
            messages=[{"role": "user", "content": "你好"}]
        )
    except requests.exceptions.ConnectionError as e:
        print(f"   错误: 无法连接到服务器")
    except Exception as e:
        print(f"   错误: {e}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("OpenCode API 代理客户端示例")
    print("=" * 60)
    
    try:
        # 运行所有示例
        example_simple_chat()
        example_multi_turn_chat()
        example_streaming_chat()
        example_with_parameters()
        example_native_api()
        example_error_handling()
        
        print("\n" + "=" * 60)
        print("所有示例运行完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
