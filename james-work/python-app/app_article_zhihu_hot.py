#!/usr/bin/env python3
"""
Zhihu Hot Articles Fetcher
获取知乎热榜数据，保存到 MySQL 数据库
使用 Playwright 抓取页面
"""

import sys
import json
import time
import urllib.request
import urllib.error
import urllib.parse
import gzip
import re
import pandas as pd
from datetime import datetime

sys.path.insert(0, '/Users/Shared/_AllDocMap/02_Project/gitee/python-app')
from python_app.config import Config
from python_app.lib.data_write_util import DataWriteUtil

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

ARTICLE_COUNT = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
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


def fetch_zhihu_hot_playwright():
    if not PLAYWRIGHT_AVAILABLE:
        return []
    
    all_articles = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            
            try:
                page.goto("https://www.zhihu.com/billboard", wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(5000)
                
                html = page.content()
                print(f"HTML长度: {len(html)}")
                
            except Exception as e:
                print(f"加载页面失败: {e}")
                browser.close()
                return []
            
            try:
                page_classes = page.evaluate("""() => {
                    const allElements = document.querySelectorAll('*');
                    const classes = new Set();
                    allElements.forEach(el => {
                        if (el.className && typeof el.className === 'string') {
                            el.className.split(' ').forEach(c => { if(c) classes.add(c); });
                        }
                    });
                    return Array.from(classes).slice(0, 50);
                }""")
                
                print(f"页面CSS类: {page_classes[:20]}")
                
                all_text = page.evaluate("""() => document.body.innerText.substring(0, 2000)""")
                print(f"页面文本: {all_text[:500]}")
                
                hot_data = page.evaluate("""() => {
                    const data = [];
                    const items = document.querySelectorAll('.HotItem, [class*="HotItem"]');
                    items.forEach((item, idx) => {
                        const titleEl = item.querySelector('[class*="title"]');
                        const title = titleEl ? titleEl.innerText : '';
                        if (title) {
                            data.push({title: title, index: idx + 1});
                        }
                    });
                    return data;
                }""")
                
                print(f"JavaScript提取: {len(hot_data)} 条")
                
                for item in hot_data[:ARTICLE_COUNT]:
                    article = {
                        'article_id': str(item.get('index', 0)),
                        'title': item.get('title', '')[:500],
                        'source': '知乎',
                        'url': f"https://www.zhihu.com/search/?q={urllib.parse.quote(item.get('title', ''))}",
                        'abstract': '',
                        'content': '',
                        'images': '[]',
                        'category': '热榜',
                        'publish_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    all_articles.append(article)
                    
            except Exception as e:
                print(f"解析内容失败: {e}")
            
            browser.close()
            
    except Exception as e:
        print(f"Playwright错误: {e}")
    
    return all_articles


def fetch_zhihu_fallback():
    url = "https://www.zhihu.com/billboard"
    
    all_articles = []
    
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = decode_response(response)
        
        pattern = r'<div[^>]*class="HotItem-title"[^>]*>([^<]+)</div>'
        matches = re.findall(pattern, html)
        
        if not matches:
            return []
            
        for idx, title in enumerate(matches[:ARTICLE_COUNT]):
            title = title.strip()
            article = {
                'article_id': str(idx + 1),
                'title': title[:500],
                'source': '知乎',
                'url': f"https://www.zhihu.com/search/?q={urllib.parse.quote(title)}",
                'abstract': '',
                'content': '',
                'images': '[]',
                'category': '热榜',
                'publish_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            all_articles.append(article)
            
    except Exception as e:
        print(f"获取知乎热榜失败: {e}")
        
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
            print(f"已保存 {saved_count} 篇知乎热榜到数据库")
            
    except Exception as e:
        print(f"保存失败: {e}")
        return 0
    
    return saved_count


def run():
    config_path = "/Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/python-app/config/app_article_toutiao_hot_article_service.yaml"
    config = Config(config_path)
    db_connection_string = config.get_db_connection_string()
    
    print("=" * 60)
    print("开始获取知乎热榜...")
    print(f"Playwright: {'可用' if PLAYWRIGHT_AVAILABLE else '不可用'}")
    print("注意: 知乎需要登录Cookie才能访问热榜页面")
    print("=" * 60)
    
    if PLAYWRIGHT_AVAILABLE:
        print("尝试使用Playwright...")
        articles = fetch_zhihu_hot_playwright()
        if articles:
            print(f"Playwright获取到 {len(articles)} 条")
    else:
        articles = []
    
    if not articles:
        print("使用fallback方式...")
        articles = fetch_zhihu_fallback()
    
    if articles:
        save_to_mysql(articles, db_connection_string)
        print(f"完成! 共获取 {len(articles)} 条热榜")
    else:
        print("无法获取知乎热榜数据 (需要登录Cookie或使用代理)")
        print("建议: 可通过浏览器登录后导出Cookie来访问")


if __name__ == "__main__":
    run()
