import json
import os
import subprocess
import warnings

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


def search_with_file_path(query_text: str, top_n: int = 3) -> list[dict]:
    """Search for the most relevant documents in Milvus.
    
    Args:
        query_text: The search query text.
        top_n: The number of most relevant results to return.
        
    Returns:
        A list of dictionaries containing search results with 'distance', 'content', and 'file_path'.
    """
    client = MilvusClient(uri=milvus_uri)
    
    if not client.has_collection(collection_name):
        print(f"集合 {collection_name} 不存在")
        return []
    
    query_vector = get_embedding(query_text)
    
    results = client.search(
        collection_name=collection_name,
        data=[query_vector],
        limit=top_n,
        output_fields=["content", "file_path"]
    )
    
    output = []
    for result in results[0]:
        output.append({
            "distance": result['distance'],
            "content": result['entity']['content'],
            "file_path": result['entity']['file_path']
        })
    
    client.close()
    return output


def merge_results_by_file_path(results: list[dict]) -> list[tuple[str, int]]:
    """Merge search results by file_path and count frequency.
    
    Args:
        results: List of search result dictionaries containing 'file_path'.
        
    Returns:
        A list of tuples (file_path, frequency) sorted by frequency in descending order.
    """
    from collections import Counter
    
    file_paths = [result['file_path'] for result in results]
    counter = Counter(file_paths)
    return counter.most_common()


def main():
    search_word = "观测质量管理体系的内审要求是什么"
    top_n = 20
    
    results = search_with_file_path(search_word, top_n=top_n)
    
    print(f"\n查询: {search_word}")
    print(f"返回结果数: {len(results)}")
    print("-" * 128)
    
    merged = merge_results_by_file_path(results)
    print(f"\n按 file_path 合并后（按频次从高到低排序）:")
    print("-" * 128)
    for file_path, freq in merged:
        print(f"频次: {freq}\t路径: {file_path}")
    print("-" * 128)


if __name__ == "__main__":
    main()
