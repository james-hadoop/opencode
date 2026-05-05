#!/usr/bin/env python3
"""
Weibo Hot Articles Fetcher
获取微博热搜榜数据，保存到 MySQL 数据库
"""

import sys
import json
import time
import urllib.request
import urllib.error
import gzip
import pandas as pd
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/Users/Shared/_AllDocMap/02_Project/gitee/python-app')
from python_app.config import Config
from python_app.lib.data_write_util import DataWriteUtil

ARTICLE_COUNT = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Referer": "https://weibo.com/",
}


def decode_response(response):
    content = response.read()
    content_encoding = response.headers.get('Content-Encoding', '').lower()
    if content_encoding == 'gzip':
        try:
            content = gzip.decompress(content)
        except Exception:
            pass
    return content.decode('utf-8', errors='replace')


def fetch_weibo_hot():
    url = "https://v2.xxapi.cn/api/weibohot"
    
    all_articles = []
    
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as response:
            decoded = decode_response(response)
            data = json.loads(decoded)
        
        data_items = data.get('data', [])
        if not data_items:
            print("无微博热搜数据")
            return []
            
        for idx, item in enumerate(data_items[:ARTICLE_COUNT]):
            article = {
                'title': item.get('title', '无标题')[:500],
                'source': '微博',
                'url': item.get('url', '').replace('https://s.weibo.com/weibo?q=', 'https://weibo.com/search/?'),
                'abstract': f"热度: {item.get('hot', '')}",
                'content': '',
                'images': '[]',
                'category': '热搜',
                'publish_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'article_id': str(idx + 1),
            }
            all_articles.append(article)
            
    except Exception as e:
        print(f"获取微博热搜失败: {e}")
        
    return all_articles


def save_to_mysql(articles, db_connection_string):
    if not articles:
        print("没有文章可保存")
        return 0
    
    saved_count = 0
    try:
        records = []
        for article in articles:
            record = {
                'article_id': article.get('article_id', ''),
                'title': article.get('title', ''),
                'source': article.get('source', ''),
                'url': article.get('url', ''),
                'abstract': article.get('abstract', ''),
                'content': article.get('content', ''),
                'images': article.get('images', '[]'),
                'category': article.get('category', '热搜'),
                'publish_time': article.get('publish_time'),
                'created_by': 'system',
                'updated_by': 'system'
            }
            records.append(record)
        
        if records:
            df = pd.DataFrame(records)
            DataWriteUtil.write_to_db_with_create_info(df, "t_app_article_weibo_hot", db_connection_string)
            saved_count = len(records)
            print(f"已保存 {saved_count} 篇微博热搜到数据库")
            
    except Exception as e:
        print(f"保存失败: {e}")
        return 0
    
    return saved_count


def run():
    import sys
    config_path = "/Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/python-app/config/app_article_toutiao_hot_article_service.yaml"
    config = Config(config_path)
    db_connection_string = config.get_db_connection_string()
    
    print("=" * 60)
    print("开始获取微博热搜...")
    print("=" * 60)
    
    articles = fetch_weibo_hot()
    
    if articles:
        save_to_mysql(articles, db_connection_string)
        print(f"完成! 共获取 {len(articles)} 条热搜")
    else:
        print("无热搜数据")


if __name__ == "__main__":
    run()
