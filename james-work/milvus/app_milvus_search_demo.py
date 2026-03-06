from pymilvus import MilvusClient
import subprocess
import json
import os
import warnings

os.environ['GLOG_minloglevel'] = '3'
os.environ['GLOG_v'] = '0'
os.environ['GLOG_logtostderr'] = '0'
warnings.filterwarnings('ignore')

milvus_uri = "http://localhost:19530"
collection_name = "documents"

print("正在连接 Milvus...")
client = MilvusClient(uri=milvus_uri)
print("✓ Milvus 连接成功")

if not client.has_collection(collection_name=collection_name):
    print(f"✗ 集合 {collection_name} 不存在")
    exit(1)

print(f"✓ 集合 {collection_name} 存在")

def get_embedding(text):
    result = subprocess.run(
        ['/Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/milvus/get_embedding.sh', text],
        capture_output=True,
        text=True,
        timeout=60
    )
    return json.loads(result.stdout.strip())

print("\n使用系统 Python 加载向量模型...")

test_queries = ["大气本底站观测场室布局", "温室气体观测"]

for query in test_queries:
    print(f"\n查询: {query}")
    print("-" * 40)
    query_vector = get_embedding(query)
    results = client.search(
        collection_name=collection_name,
        data=[query_vector],
        limit=2,
        output_fields=["content"]
    )
    for idx, result in enumerate(results[0], 1):
        print(f"[{idx}] 相关度: {result['distance']:.4f}")
        content = result['entity'].get('content', '')
        print(f"    内容: {content[:60]}...")

print("\n" + "="*50)
print("✓ 测试完成！")

try:
    client.close()
    print("✓ 已断开连接")
except:
    pass
