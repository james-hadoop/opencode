import requests

BASE_URL = "http://localhost:18011"


def get_content(file_path: str, as_list: bool = False, chunked: bool = False, chunk_size: int = 8192):
    params = {
        "file_path": file_path,
        "as_list": as_list,
        "chunked": chunked,
        "chunk_size": chunk_size
    }
    resp = requests.get(f"{BASE_URL}/content", params=params)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python client.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    print("=== Get merged content ===")
    result = get_content(file_path)
    print(result.get("content", "")[:500])
    
    print("\n=== Get content as list ===")
    result = get_content(file_path, as_list=True)
    print(f"Total items: {len(result.get('contents', []))}")
    
    print("\n=== Get chunked content ===")
    result = get_content(file_path, chunked=True)
    print(f"Total chunks: {len(result.get('chunks', []))}")
