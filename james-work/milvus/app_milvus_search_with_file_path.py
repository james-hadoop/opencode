from pymilvus import MilvusClient, DataType
from pymilvus.milvus_client.index import IndexParams
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

def get_embedding(text):
    result = subprocess.run(
        ['/Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/get_embedding.sh', text],
        capture_output=True,
        text=True,
        timeout=60
    )
    return json.loads(result.stdout.strip())

has_collection = client.has_collection(collection_name=collection_name)

if has_collection:
    schema = client.describe_collection(collection_name)
    fields = [f['name'] for f in schema.get('fields', [])]
    
    if 'file_path' not in fields:
        print(f"正在重建集合 {collection_name}，添加 file_path 字段...")
        client.drop_collection(collection_name=collection_name)
        
        from pymilvus import DataType
        schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=64)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=384)
        schema.add_field("content", DataType.VARCHAR, max_length=65535)
        schema.add_field("file_path", DataType.VARCHAR, max_length=512)
        
        client.create_collection(collection_name=collection_name, schema=schema)
        
        print("正在插入带有 file_path 的示例数据...")
        sample_data = [
            ("附件：大气本底站观测场室技术规范", "/Users/Shared/_AllDocMap/02_Project/docs/大气本底站观测场室技术规范.pdf"),
            ("为了规范大气本底站观测场室布局，我司组织制定了《大气本底站观测场室技术规范》", "/Users/Shared/_AllDocMap/02_Project/docs/大气本底站技术规范通知.pdf"),
            ("气测函〔2013〕111 号", "/Users/Shared/_AllDocMap/02_Project/docs/气测函2013-111.pdf"),
        ]
        
        for i, (content, file_path) in enumerate(sample_data, 1):
            vector = get_embedding(content)
            client.insert(
                collection_name=collection_name,
                data=[{
                    "id": str(i),
                    "vector": vector,
                    "content": content,
                    "file_path": file_path
                }]
            )
        print("✓ 示例数据插入完成")
        
        print("正在创建索引...")
        index_params = IndexParams()
        index_params.add_index(
            field_name="vector",
            index_type="AUTOINDEX",
            metric_type="COSINE"
        )
        client.create_index(collection_name=collection_name, index_params=index_params)
        
        print("正在加载 collection 到内存...")
        client.load_collection(collection_name=collection_name)
        print("✓ Collection 加载完成")
    else:
        print(f"✓ 集合 {collection_name} 已包含 file_path 字段")
        
        print("正在加载 collection 到内存...")
        client.load_collection(collection_name=collection_name)
        print("✓ Collection 加载完成")
else:
    print(f"✗ 集合 {collection_name} 不存在，将创建新集合...")
    
    from pymilvus import DataType
    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=64)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=384)
    schema.add_field("content", DataType.VARCHAR, max_length=65535)
    schema.add_field("file_path", DataType.VARCHAR, max_length=512)
    
    client.create_collection(collection_name=collection_name, schema=schema)
    
    print("正在插入带有 file_path 的示例数据...")
    sample_data = [
        ("附件：大气本底站观测场室技术规范", "/Users/Shared/_AllDocMap/02_Project/docs/大气本底站观测场室技术规范.pdf"),
        ("为了规范大气本底站观测场室布局，我司组织制定了《大气本底站观测场室技术规范》", "/Users/Shared/_AllDocMap/02_Project/docs/大气本底站技术规范通知.pdf"),
        ("气测函〔2013〕111 号", "/Users/Shared/_AllDocMap/02_Project/docs/气测函2013-111.pdf"),
    ]
    
    for i, (content, file_path) in enumerate(sample_data, 1):
        vector = get_embedding(content)
        client.insert(
            collection_name=collection_name,
            data=[{
                "id": str(i),
                "vector": vector,
                "content": content,
                "file_path": file_path
            }]
        )
    print("✓ 示例数据插入完成")
    
    print("正在创建索引...")
    index_params = IndexParams()
    index_params.add_index(
        field_name="vector",
        index_type="AUTOINDEX",
        metric_type="COSINE"
    )
    client.create_index(collection_name=collection_name, index_params=index_params)
    
    print("正在加载 collection 到内存...")
    client.load_collection(collection_name=collection_name)
    print("✓ Collection 加载完成")

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
        output_fields=["content", "file_path"]
    )
    for idx, result in enumerate(results[0], 1):
        print(f"[{idx}] 相关度: {result['distance']:.4f}")
        content = result['entity'].get('content', '')
        file_path = result['entity'].get('file_path', '')
        print(f"    内容: {content[:60]}...")
        if file_path:
            print(f"    路径: {file_path}")

print("\n" + "="*50)
print("✓ 测试完成！")

try:
    client.close()
    print("✓ 已断开连接")
except:
    pass
