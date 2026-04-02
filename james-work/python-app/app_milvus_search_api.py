#!/usr/bin/env python3

import time
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel

app = FastAPI(title="Milvus Search API", version="1.0.0")

TOKEN_STORE: Dict[str, Dict[str, Any]] = {}

VALID_CREDENTIALS = {
    "dev": "dEv#1234"
}

TOKEN_EXPIRY_SECONDS = 24 * 60 * 60


def generate_token(ak: str) -> str:
    raw_token = f"{ak}:{uuid.uuid4()}:{time.time()}"
    return hashlib.sha256(raw_token.encode()).hexdigest()


def verify_token(token: str) -> bool:
    if token not in TOKEN_STORE:
        return False
    
    token_info = TOKEN_STORE[token]
    if time.time() > token_info["expires_at"]:
        del TOKEN_STORE[token]
        return False
    
    return True


def get_ak_from_token(token: str) -> Optional[str]:
    if token in TOKEN_STORE:
        return TOKEN_STORE[token].get("ak")
    return None


class TokenRequest(BaseModel):
    ak: str
    sk: str


class SearchRequest(BaseModel):
    database: str
    collection_name: str
    search_word: str
    top_k: int = 10


class CollectionInfoRequest(BaseModel):
    database: str
    collection_name: str


async def verify_token_dependency(x_token: Optional[str] = Header(None)) -> str:
    if not x_token:
        raise HTTPException(status_code=401, detail="Missing token")
    
    if not verify_token(x_token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return x_token


@app.post("/get_token")
async def get_token(request: TokenRequest):
    valid_sk = VALID_CREDENTIALS.get(request.ak)
    if not valid_sk or valid_sk != request.sk:
        raise HTTPException(status_code=401, detail="Invalid AK/SK")
    
    token = generate_token(request.ak)
    expires_at = time.time() + TOKEN_EXPIRY_SECONDS
    
    TOKEN_STORE[token] = {
        "ak": request.ak,
        "expires_at": expires_at,
        "created_at": time.time()
    }
    
    return {"token": token}


@app.post("/get_collection_info")
async def get_collection_info(
    request: CollectionInfoRequest,
    x_token: str = Depends(verify_token_dependency)
):
    try:
        from pymilvus import connections
        from pymilvus import Collection, utility
        
        connections.connect(
            alias="default",
            host="localhost",
            port="19530"
        )
        
        coll = Collection(request.collection_name)
        coll.load()
        
        return {
            "collection_name": request.collection_name,
            "num_entities": coll.num_entities
        }
        
    except ImportError:
        return {
            "collection_name": request.collection_name,
            "message": "pymilvus not installed, mock response"
        }
    except Exception as e:
        error_msg = str(e)
        if "connect" in error_msg.lower() or "network" in error_msg.lower():
            return {
                "collection_name": request.collection_name,
                "message": f"Milvus connection failed: {error_msg}"
            }
        raise HTTPException(status_code=500, detail=f"Get collection info failed: {error_msg}")


@app.post("/search")
async def search(
    request: SearchRequest,
    x_token: str = Depends(verify_token_dependency)
):
    ak = get_ak_from_token(x_token)
    
    try:
        from pymilvus import connections
        from pymilvus import Collection
        
        connections.connect(
            alias="default",
            host="localhost",
            port="19530"
        )
        
        coll = Collection(request.collection_name)
        coll.load()
        
        dim = 768
        query_embedding = [0.0] * dim
        
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10}
        }
        
        results = coll.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=request.top_k,
            output_fields=["text"]
        )
        
        search_results = []
        for hits in results:
            for hit in hits:
                search_results.append({
                    "id": hit.id,
                    "distance": hit.distance,
                    "text": hit.entity.get("text", "")
                })
        
        return {
            "results": search_results,
            "total": len(search_results)
        }
        
    except ImportError:
        return {
            "results": [],
            "total": 0,
            "message": "pymilvus not installed, mock response"
        }
    except Exception as e:
        error_msg = str(e)
        if "connect" in error_msg.lower() or "network" in error_msg.lower():
            return {
                "results": [],
                "total": 0,
                "message": f"Milvus connection failed: {error_msg}"
            }
        raise HTTPException(status_code=500, detail=f"Search failed: {error_msg}")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18012)
