#!/usr/bin/env python3
"""
Bilibili Hot Articles Fetcher
获取B站热门视频数据，保存到 MySQL 数据库
使用官方API: x/web-interface/ranking/v2
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


def fetch_bilibili_hot():
    all_articles = []
    
    urls = [
        ("https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all", "全站"),
        ("https://api.bilibili.com/x/web-interface/ranking/v2?rid=1&type=hot", "动画"),
        ("https://api.bilibili.com/x/web-interface/ranking/v2?rid=3&type=hot", "音乐"),
    ]
    
    for url, category in urls[:1]:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as response:
                html = decode_response(response)
            
            data = json.loads(html)
            if data.get('code') != 0:
                print(f"B站API错误: {data.get('message')}")
                continue
            
            list_data = data.get('data', {}).get('list', [])
            for idx, item in enumerate(list_data[:ARTICLE_COUNT]):
                pics = item.get('pictures', [])
                img = pics[0].get('img_url', '') if pics else item.get('pic', '')
                
                article = {
                    'article_id': str(item.get('aid', idx + 1)),
                    'title': item.get('title', '')[:500],
                    'source': 'B站',
                    'url': f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                    'abstract': item.get('desc', '')[:500],
                    'content': '',
                    'images': json.dumps([img]),
                    'category': category,
                    'publish_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                all_articles.append(article)
                
        except Exception as e:
            print(f"获取B站热门失败: {e}")
    
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
                'category': article.get('category', '热榜'),
                'publish_time': article.get('publish_time'),
                'created_by': 'system',
                'updated_by': 'system'
            }
            records.append(record)
        
        if records:
            df = pd.DataFrame(records)
            DataWriteUtil.write_to_db_with_create_info(df, "t_app_article_zhihu_hot", db_connection_string)
            saved_count = len(records)
            print(f"已保存 {saved_count} 篇B站热门到数据库")
            
    except Exception as e:
        print(f"保存失败: {e}")
        return 0
    
    return saved_count


def run():
    config_path = "/Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/python-app/config/app_article_toutiao_hot_article_service.yaml"
    config = Config(config_path)
    db_connection_string = config.get_db_connection_string()
    
    print("=" * 60)
    print("开始获取B站热门视频...")
    print("=" * 60)
    
    articles = fetch_bilibili_hot()
    
    if articles:
        save_to_mysql(articles, db_connection_string)
        print(f"完成! 共获取 {len(articles)} 条热门视频")
    else:
        print("无法获取B站热门数据")


if __name__ == "__main__":
    run()
