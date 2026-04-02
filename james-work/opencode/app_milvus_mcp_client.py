import asyncio
import sys
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_params = StdioServerParameters(
        command="/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python",
        args=["/Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/opencode/app_milvus_mcp.py"],
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                print(f"Available tools: {[t.name for t in tools.tools]}", file=sys.stderr)

                print("Searching for: 气象质量管理", file=sys.stderr)
                result = await session.call_tool(
                    "milvus_search",
                    arguments={
                        "query_text": "气象质量管理",
                        "top_n": 10
                    }
                )

                if result.content:
                    text_content = result.content[0]
                    if hasattr(text_content, 'text'):
                        data = json.loads(text_content.text)
                        print(f"\n找到 {len(data)} 条结果:\n")
                        for i, item in enumerate(data, 1):
                            print(f"--- 结果 {i} ---")
                            print(f"距离: {item.get('distance', 'N/A')}")
                            print(f"文件: {item.get('file_path', 'N/A')}")
                            content = item.get('content', '')
                            print(f"内容: {content[:200]}..." if len(content) > 200 else f"内容: {content}")
                            print()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
