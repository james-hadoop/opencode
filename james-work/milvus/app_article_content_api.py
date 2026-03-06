import json
import re
from fastapi import FastAPI, Query
from typing import Optional

app = FastAPI()


def read_content_list_from_content_list_file(content_list_file_path: str) -> list[str]:
    with open(content_list_file_path, 'r', encoding='utf-8') as f:
        content_list = json.load(f)
    
    texts = []
    for item in content_list:
        if item.get("type") == "text" and len(item.get("text", "")) > 5:
            text = item["text"]
            text = re.sub(r'\n+', 'CH_NL', text)
            texts.append(text)
    return texts


def read_content_from_content_list_file(content_list_file_path: str) -> str:
    with open(content_list_file_path, 'r', encoding='utf-8') as f:
        content_list = json.load(f)
    
    texts = [item["text"].replace("\n", "CH_NL") for item in content_list if item.get("type") == "text"]
    return " ".join(texts)


def chunk_content_by_size(content: str, chunk_size: int = 8192) -> list[str]:
    return [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]


@app.get("/content")
def get_content(
    file_path: str = Query(..., description="Path to the JSON content list file"),
    as_list: bool = Query(False, description="Return as list instead of merged string"),
    chunk_size: int = Query(8192, description="Chunk size for splitting content"),
    chunked: bool = Query(False, description="Return content in chunks")
):
    if as_list:
        content_list = read_content_list_from_content_list_file(file_path)
        if chunked:
            merged = " ".join(content_list)
            return {"chunks": chunk_content_by_size(merged, chunk_size)}
        return {"contents": content_list}
    else:
        content = read_content_from_content_list_file(file_path)
        if chunked:
            return {"chunks": chunk_content_by_size(content, chunk_size)}
        return {"content": content}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18011)
