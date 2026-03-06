import json

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


def read_content_from_content_list_file(content_list_file_path: str) -> str:
    """Read content from a JSON file containing a list of contents.
    
    Args:
        content_list_file_path: The file path to the JSON file.
        
    Returns:
        A string with all "text" values where "type" is "text", joined by spaces.
        Newlines are replaced by "CH_NL".
    """
    with open(content_list_file_path, 'r', encoding='utf-8') as f:
        content_list = json.load(f)
    
    texts = [item["text"].replace("\n", "CH_NL") for item in content_list if item.get("type") == "text"]
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

def main():
    content_list_file_path = "/Volumes/james1t/proj_openclaw/气象数据/_Markdown化文件/output_path/中国气象局气象观测质量管理体系质量手册-20210707/auto/中国气象局气象观测质量管理体系质量手册-20210707_content_list.json"
    content = read_content_from_content_list_file(content_list_file_path)
    content_list = chunk_content_by_size(content)
    
    for cont in content_list:
        print(cont)
    print(len(content_list))
    
    print("-" * 128)
    content_list = read_content_list_from_content_list_file(content_list_file_path)
    merged_content = " ".join(content_list)
    print(merged_content)
    print(len(content_list))

if __name__ == '__main__':
    main()