import requests
from typing import Optional

BASE_URL = "http://localhost:18011"


def search(query: str, top_n: int = 3, db: Optional[str] = None, collection: Optional[str] = None):
    params = {"q": query, "top_n": top_n}
    if db:
        params["db"] = db
    if collection:
        params["collection"] = collection
    response = requests.get(f"{BASE_URL}/search", params=params)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    query = "观测质量管理体系的内审要求是什么"
    results = search(query, top_n=5)
    print(f"查询: {results['query']}")
    print(f"返回结果数: {len(results['results'])}")
    print("-" * 128)
    for i, r in enumerate(results['results'], 1):
        print(f"\n结果 {i}:")
        print(f"  距离: {r['distance']}")
        print(f"  路径: {r['file_path']}")
        print(f"  内容: {r['content'][:200]}...")
