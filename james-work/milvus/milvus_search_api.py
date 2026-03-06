import json
import os
import subprocess
import warnings
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query
from pymilvus import MilvusClient

os.environ['GLOG_minloglevel'] = '3'
os.environ['GLOG_v'] = '0'
os.environ['GLOG_logtostderr'] = '0'
warnings.filterwarnings('ignore')

milvus_uri = "http://localhost:19530"
collection_name = "qixiang_md_demo_detail"


def get_embedding(text):
    result = subprocess.run(
        ['/Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/milvus/get_embedding.sh', text],
        capture_output=True,
        text=True,
        timeout=60
    )
    return json.loads(result.stdout.strip())


def search_with_file_path(
    query_text: str,
    top_n: int = 3,
    db_name: Optional[str] = None,
    collection_name_param: Optional[str] = None
) -> list[dict]:
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Milvus Search API", lifespan=lifespan)


@app.get("/search")
def search(
    q: str = Query(..., description="Search query text"),
    top_n: int = Query(30, description="Number of results to return"),
    db: Optional[str] = Query(None, description="Database name"),
    collection: Optional[str] = Query(None, description="Collection name")
):
    results = search_with_file_path(q, top_n=top_n, db_name=db, collection_name_param=collection)
    return {"query": q, "top_n": top_n, "db": db, "collection": collection, "results": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18011)
