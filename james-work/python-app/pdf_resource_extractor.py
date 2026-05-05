#!/usr/bin/env python3
import re
import os
import sys
from urllib.parse import urlparse

try:
    import pdfplumber
except ImportError:
    print("please install pdfplumber: pip install pdfplumber")
    sys.exit(1)


def extract_resources_from_pdf(pdf_path: str):
    resources = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            try:
                annots = page.annotating.get('annots', []) if hasattr(page, 'annotating') else getattr(page, 'annots', [])
            except:
                annots = []
            
            for annot in annots:
                uri = annot.get('uri', '')
                if not uri or not uri.startswith('http'):
                    continue
                
                resource_type = identify_resource_type(uri)
                
                resources.append({
                    'title': '',
                    'url': uri,
                    'type': resource_type,
                    'page': page_num
                })
    
    return resources


def identify_resource_type(url: str) -> str:
    url_lower = url.lower()
    
    if '/video/' in url_lower or 'video_id=' in url_lower:
        return 'video'
    
    if 'douyin.com' in url_lower or 'ixigua.com' in url_lower or 'bilibili.com' in url_lower:
        return 'video'
    
    if '/is/' in url_lower:
        return 'video'
    
    return 'article'


def extract_title_from_context(lines: list, url_line_idx: int, url: str) -> str:
    title = ""
    
    for offset in range(1, 4):
        if url_line_idx - offset >= 0:
            candidate = lines[url_line_idx - offset].strip()
            if candidate and not candidate.startswith('http') and len(candidate) > 5:
                title = candidate
                break
    
    if not title and url_line_idx + 1 < len(lines):
        candidate = lines[url_line_idx + 1].strip()
        if candidate and not candidate.startswith('http') and len(candidate) > 5:
            title = candidate
    
    title = re.sub(r'^\d+[\.\)]\s*', '', title)
    title = title[:100] if title else "unnamed"
    
    return title


def main():
    pdf_path = "/Volumes/james1t/proj_feishu/收藏资源URL.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF not found: {pdf_path}")
        sys.exit(1)
    
    resources = extract_resources_from_pdf(pdf_path)
    
    videos = [r for r in resources if r['type'] == 'video']
    articles = [r for r in resources if r['type'] == 'article']
    
    print(f"Total: {len(resources)} | Videos: {len(videos)} | Articles: {len(articles)}")
    
    return resources


if __name__ == "__main__":
    main()
