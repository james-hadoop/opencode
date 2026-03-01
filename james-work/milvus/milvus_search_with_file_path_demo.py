from pymilvus import MilvusClient, DataType
from pymilvus.milvus_client.index import IndexParams
import subprocess
import json
import os
import warnings
from python_app.lib.file_util import FileUtil
from python_app.lib.data_query_util import DataQueryUtil

os.environ['GLOG_minloglevel'] = '3'
os.environ['GLOG_v'] = '0'
os.environ['GLOG_logtostderr'] = '0'
warnings.filterwarnings('ignore')

milvus_uri = "http://localhost:19530"
collection_name = "qixiang_md_demo_1"

def get_embedding(text):
    result = subprocess.run(
        ['/Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/get_embedding.sh', text],
        capture_output=True,
        text=True,
        timeout=60
    )
    return json.loads(result.stdout.strip())

def create_collection_with_file_path(collection_name:str):
    client = MilvusClient(uri=milvus_uri)
    
    if client.has_collection(collection_name):
        client.drop_collection(collection_name)
    
    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=64)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=384)
    schema.add_field("content", DataType.VARCHAR, max_length=65530)
    schema.add_field("file_path", DataType.VARCHAR, max_length=512)
    
    client.create_collection(collection_name=collection_name, schema=schema)
    
    index_params = IndexParams()
    index_params.add_index(
        field_name="vector",
        index_type="AUTOINDEX",
        metric_type="COSINE"
    )
    client.create_index(collection_name=collection_name, index_params=index_params)
    
    client.load_collection(collection_name=collection_name)
    client.close()

def insert_data_with_file_path(file_md_list: list, file_path_list: list):
    client = MilvusClient(uri=milvus_uri)

    sample_data = []
    for file_md, file_path in zip(file_md_list, file_path_list):
        content = file_md.encode('utf-8')[:65530].decode('utf-8', errors='ignore')
        sample_data.append((content, file_path))

    for i, (content, file_path) in enumerate(sample_data, 1):
        print(f"正在插入第 {i} 条数据，字节长度: {len(content.encode('utf-8'))}")
        if len(file_path) > 512:
            file_path = file_path[:512]
        # 只使用前2000个字符生成向量，避免超时
        vector = get_embedding(content[:2000])
        client.insert(
            collection_name=collection_name,
            data=[{
                "id": str(i),
                "vector": vector,
                "content": content,
                "file_path": file_path
            }]
        )
    
    client.close()

def search_with_file_path(query_text):
    client = MilvusClient(uri=milvus_uri)
    
    if not client.has_collection(collection_name):
        print(f"集合 {collection_name} 不存在")
        return
    
    query_vector = get_embedding(query_text)
    
    results = client.search(
        collection_name=collection_name,
        data=[query_vector],
        limit=3,
        output_fields=["content", "file_path"]
    )
    
    print(f"\n查询: {query_text}")
    print("-" * 128)
    for result in results[0]:
        print(f"相关度: {result['distance']:.4f}")
        print(f"路径: {result['entity']['file_path']}")
        print(f"内容: {result['entity']['content']}")
        print("-" * 128)
    
    client.close()

if __name__ == "__main__":
#     print("1. 创建包含 file_path 字段的 collection...")
#     create_collection_with_file_path(collection_name)
#     print(f"✓ Collection: {collection_name} 创建完成")

#     print("\n2. 从数据库获取数据...")
#     sql = """
# SELECT  id
#        ,file_name
#        ,file_path
#        ,file_md
#        ,`type`
#        ,created_at
#        ,created_by
#        ,updated_at
#        ,updated_by
# FROM app.t_app_extract_md_from_article
# WHERE file_md is not null
# AND LENGTH(file_md) > 10
# ORDER BY id DESC
# LIMIT 3
# ;
# """
#
    # db_connection_string = "mysql+pymysql://dev:dEv#1234@localhost:3306/app"
    # df = DataQueryUtil.read_from_db(sql, db_connection_string)

    # file_md_list = df['file_md'].astype(str).tolist()
    # file_path_list = df['file_path'].astype(str).tolist()
    # print(f"✓ 获取到 {len(file_md_list)} 条内容")

    # print("\n3. 插入数据到 Milvus...")
    # insert_data_with_file_path(file_md_list = file_md_list, file_path_list = file_path_list)
    # print("✓ 数据插入完成")

    print("\n4. 向量检索示例...")
    search_with_file_path("气现象视频智能观测仪")
    print("✓ 检索完成")
