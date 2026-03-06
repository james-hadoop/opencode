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
collection_name = "qixiang_md_demo"

def get_embedding(text):
    result = subprocess.run(
        ['/Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/milvus/get_embedding.sh', text],
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

def read_content_list_from_content_list_file(content_list_file_path: str) -> list[str]:
    """Read content from a JSON file containing a list of contents.
    
    Args:
        content_list_file_path: The file path to the JSON file.
        
    Returns:
        A list of text strings where "type" is "text" and text length > 5,
        with newlines replaced by "CH_NL" and multiple consecutive newlines collapsed.
    """
    import re
    with open(content_list_file_path, 'r', encoding='utf-8') as f:
        content_list = json.load(f)
    
    texts = []
    for item in content_list:
        if item.get("type") == "text" and len(item.get("text", "")) > 5:
            text = item["text"]
            text = re.sub(r'\n+', 'CH_NL', text)
            texts.append(text)
    return texts

def read_content_from_content_list_file(content_list_file_list: str) -> str:
    """Read content from a JSON file containing a list of contents.
    
    Args:
        content_list_file_list: The file path to the JSON file.
        
    Returns:
        A string with all "text" values where "type" is "text", joined by spaces.
    """
    with open(content_list_file_list, 'r', encoding='utf-8') as f:
        content_list = json.load(f)
    
    texts = [item["text"] for item in content_list if item.get("type") == "text"]
    return " ".join(texts)

def chunk_content_by_size(content: str, chunk_size: int = 8192) -> list[str]:
    """Split content into chunks of specified size.
    
    Args:
        content: The content string to split.
        chunk_size: The maximum size of each chunk in characters.
        
    Returns:
        A list of content chunks.
    """
    return [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]

def insert_data_with_file_path(file_md_list: list, file_path_list: list, content_list_file_list: list):
    client = MilvusClient(uri=milvus_uri)

    sample_data = []
    # for file_md, file_path in zip(file_md_list, file_path_list):
    for content_list_file, file_path in zip(content_list_file_list, file_path_list):
        # 将 content_list 先合并，再按照 chunk_size 分块
        content = read_content_from_content_list_file(content_list_file).encode('utf-8').decode('utf-8', errors='ignore')
        content_list = chunk_content_by_size(content)

        # # 使用 MinerU 的提取结果进行分块
        # content_list = read_content_list_from_content_list_file(content_list_file)
        
        for cont in content_list:
            sample_data.append((cont.encode('utf-8').decode('utf-8', errors='ignore'), file_path))

    for i, (content, file_path) in enumerate(sample_data, 1):
        print(f"正在插入第 {i} 条数据，字节长度: {len(content.encode('utf-8'))}, 文件路径: {file_path}")

        # 只使用前 N 个字符生成向量，避免超时
        vector = get_embedding(content[:65530])
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
        print("\n\n")
        print("-" * 128)
        # print(f"内容: {result['entity']['content']}")
        print("-" * 128)
        print("\n\n")
    
    client.close()

if __name__ == "__main__":
    print("1. 创建包含 file_path 字段的 collection...")
    create_collection_with_file_path(collection_name)
    print(f"✓ Collection: {collection_name} 创建完成")

    print("\n2. 从数据库获取数据...")
    sql = """
SELECT  id
       ,file_name
       ,file_path
       ,file_md
       ,`type`
       ,created_at
       ,created_by
       ,updated_at
       ,updated_by
FROM app.t_app_extract_md_from_article
WHERE id BETWEEN 1772 AND 1900
-- WHERE id BETWEEN 1790 AND 1800
-- AND id = 1793
-- AND file_name LIKE '%中国气象局气象观测质量管理体系质量手册%'
AND file_md is not null
AND LENGTH(file_md) > 10
ORDER BY id DESC
;
"""

    db_connection_string = "mysql+pymysql://dev:dEv#1234@localhost:3306/app"
    df = DataQueryUtil.read_from_db(sql, db_connection_string)
    df['content_list_file_list'] = df['file_path'] + '/auto/' + df['file_name'] + '_content_list.json'
    df['origin_file_list'] = df['file_path'] + '/auto/' + df['file_name'] + '_origin.pdf'

    file_md_list = df['file_md'].astype(str).tolist()
    file_path_list = df['file_path'].astype(str).tolist()
    content_list_file_list = df['content_list_file_list'].astype(str).tolist()
    origin_file_list = df['origin_file_list'].astype(str).tolist()
    print(f"✓ 获取到 {len(content_list_file_list)} 条内容")
    print("-" * 128)
    for f in content_list_file_list:
        print(f)
    print("-" * 128)    

    print("\n3. 插入数据到 Milvus...")
    insert_data_with_file_path(file_md_list = file_md_list, file_path_list = origin_file_list, content_list_file_list = content_list_file_list)
    print("✓ 数据插入完成")

    search_word = "观测质量管理体系"
    print("\n4. 向量检索示例...")
    search_with_file_path(search_word)
    print("✓ 检索完成")
