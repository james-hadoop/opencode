import json
import os
import subprocess
import warnings
from typing import Optional, Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

warnings.filterwarnings('ignore')

milvus_uri = "http://localhost:19530"
collection_name = "XiXiang_DiMian_2"


def get_embedding(text: str) -> list[float]:
    result = subprocess.run(
        ['/Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/milvus/get_embedding.sh', text],
        capture_output=True,
        text=True,
        timeout=600
    )
    return json.loads(result.stdout.strip())


def search_with_file_path(
    query_text: str,
    top_n: int = 30,
    db_name: Optional[str] = None,
    collection_name_param: Optional[str] = None
) -> list[dict]:
    from pymilvus import MilvusClient
    
    client = MilvusClient(uri=milvus_uri)

    coll_name = collection_name_param or collection_name

    if not client.has_collection(coll_name):
        print(f"集合 {coll_name} 不存在")
        return []

    query_vector = get_embedding(query_text)

    search_params = {
        "collection_name": coll_name,
        "data": [query_vector],
        "limit": top_n,
        "output_fields": ["content", "file_path"]
    }
    if db_name:
        search_params["db_name"] = db_name

    results = client.search(**search_params)

    output = []
    for result in results[0]:
        output.append({
            "distance": result['distance'],
            "content": result['entity']['content'],
            "file_path": result['entity']['file_path']
        })

    client.close()
    return output


app = Server("milvus-search")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="milvus_search",
            description="Search documents in Milvus vector database by text query. Returns matching documents with content, file paths, and similarity distances.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "The search query text"
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Number of results to return (default: 30)",
                        "default": 30
                    },
                    "db_name": {
                        "type": "string",
                        "description": "Database name (optional)"
                    },
                    "collection": {
                        "type": "string",
                        "description": "Collection name (default: XiXiang_DiMian_2)"
                    }
                },
                "required": ["query_text"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "milvus_search":
        query_text: str = arguments.get("query_text", "")
        top_n: int = arguments.get("top_n", 30)
        db_name: Optional[str] = arguments.get("db_name")
        collection: Optional[str] = arguments.get("collection")
        
        results = search_with_file_path(
            query_text=query_text,
            top_n=top_n,
            db_name=db_name,
            collection_name_param=collection
        )
        
        return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]
    
    raise ValueError(f"Unknown tool: {name}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
