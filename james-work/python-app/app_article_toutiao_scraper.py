#!/usr/bin/env python3
"""
Toutiao Hot Articles Fetcher
每10分钟获取一次 https://www.toutiao.com/ 的10条热点文章，保存到 markdown 文件
使用 Playwright 提取文章正文内容
支持保存到 MySQL 数据库
"""

import argparse
import gzip
import json
import re
import time
import os
import sys
import zlib
import pandas as pd
from datetime import datetime
from pathlib import Path
from dateutil import parser as date_parser

sys.path.insert(0, '/Users/Shared/_AllDocMap/02_Project/gitee/python-app')

from python_app.config import Config
from python_app.processor import Processor
from python_app.lib.data_write_util import DataWriteUtil

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

import urllib.request
import urllib.error

OUTPUT_FILE = Path("./toutiao_articles.md")
FETCH_INTERVAL = 3600
ARTICLE_COUNT = 20

CATEGORY_MAP = {
    "财经": "news_finance",
    "科技": "news_tech", 
    "国际": "news_world",
    "上海": "news_society",
    "深圳": "news_society",
    "杭州": "news_society"
}

CATEGORIES = ["财经", "科技", "国际"]

CONFIG_PATH = "/Users/Shared/_AllDocMap/02_Project/gitee/python-app/app_local/article/config/app_article_config.yaml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "close",
    "Referer": "https://www.toutiao.com/",
}


def decode_response(response):
    """
    Decode HTTP response, handling gzip compression and different encodings
    """
    content = response.read()
    
    content_encoding = response.headers.get('Content-Encoding', '').lower()
    
    if content_encoding == 'gzip':
        try:
            content = gzip.decompress(content)
        except Exception:
            pass
    elif content_encoding == 'deflate':
        try:
            content = gzip.decompress(content)
        except:
            try:
                content = zlib.decompress(content)
            except Exception:
                pass
    
    content_type = response.headers.get('Content-Type', '')
    charset = 'utf-8'
    
    if 'charset=' in content_type:
        match = re.search(r'charset=([^\s;]+)', content_type)
        if match:
            charset = match.group(1).lower()
    
    encodings_to_try = [charset]
    if 'gb' not in charset:
        encodings_to_try.extend(['gbk', 'gb2312', 'gb18030'])
    
    for encoding in encodings_to_try:
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    
    return content.decode('utf-8', errors='replace')


def fetch_article_content_playwright(url):
    """
    使用 Playwright 获取文章正文内容
    参数: url - 文章URL
    返回: 正文文本
    """
    if not PLAYWRIGHT_AVAILABLE:
        return ""
    
    mobile_url = url.replace('www.toutiao.com', 'm.toutiao.com').replace('/group/', '/article/')
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                viewport={'width': 390, 'height': 844}
            )
            page = context.new_page()
            
            try:
                page.goto(mobile_url, wait_until="networkidle", timeout=20000)
                page.wait_for_timeout(2000)
            except Exception:
                browser.close()
                return ""
            
            if "error" in page.url.lower() or page.title() == "":
                browser.close()
                return ""
            
            try:
                body = page.query_selector("body")
                if body:
                    text = body.inner_text()
                    lines = text.split('\n')
                    meaningful = []
                    noise_patterns = ['打开APP', 'APP内打开', '去听全文', '查看图片详情', '立即下载', '扫码下载']
                    for line in lines:
                        line = line.strip()
                        if len(line) > 20 and not any(p in line for p in noise_patterns):
                            meaningful.append(line)
                    
                    if meaningful:
                        text = '\n'.join(meaningful[:40])
                        browser.close()
                        return text[:5000]
            except:
                pass
            
            browser.close()
            return ""
            
    except Exception as e:
        print(f"Playwright error: {e}")
        return ""


def fetch_article_content_fallback(url):
    """
    备用方法：使用 urllib 获取文章正文
    """
    try:
        mobile_url = url.replace('www.toutiao.com', 'm.toutiao.com')
        req = urllib.request.Request(mobile_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = decode_response(response)
        
        patterns = [
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*article[^"]*"[^>]*>(.*?)</div>',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                text = re.sub(r'<[^>]+>', '', match.group(1))
                text = re.sub(r'\s+', ' ', text).strip()
                if len(text) > 50:
                    return text[:3000]
        
        return ""
        
    except Exception:
        return ""


def extract_publish_time(item):
    """
    Extract publish time from API item
    Returns: datetime string in MySQL format (YYYY-MM-DD HH:MM:SS) or None
    """
    publish_time = None
    
    if item.get('publish_time'):
        pt = item.get('publish_time')
    elif item.get('create_time'):
        pt = item.get('create_time')
    elif item.get('datetime'):
        pt = item.get('datetime')
    elif item.get('publish_time_str'):
        pt = item.get('publish_time_str')
    else:
        return None
    
    if pt is None:
        return None
    
    if isinstance(pt, (int, float)):
        try:
            dt = datetime.fromtimestamp(pt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            return None
    elif isinstance(pt, str):
        try:
            dt = date_parser.parse(pt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return None
    
    return None


def fetch_hot_articles(category=None, fetch_content=False):
    """
    获取今日头条热点文章
    参数: 
        category - 文章分类 (财经/科技/国际/上海/深圳/杭州), 默认获取热点
        fetch_content - 是否获取全文内容，默认False（快速模式）
    返回: 文章列表
    """
    if category and category in CATEGORY_MAP:
        category_id = CATEGORY_MAP[category]
    else:
        category_id = "news_hot"
    
    url = f"https://www.toutiao.com/api/pc/feed/?category={category_id}&utm_source=toutiao&widen=1&max_behot_time=0&max_behot_time_tmp=0&tadrequire=true&as=A1152B8F0F9F0F5&cp=5F9E0F9E0F9E5"
    
    timeout = 15
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            decoded = decode_response(response)
            data = json.loads(decoded)
            
        if not data or not isinstance(data, dict):
            return []
            
        articles = []
        data_items = data.get('data')
        if not data_items or not isinstance(data_items, list):
            return []
            
        for item in data_items[:ARTICLE_COUNT * 2]:
            if not isinstance(item, dict):
                continue
            if item.get('is_ad') or item.get('ad_id'):
                continue
            if item.get('item_type') == 'ad':
                continue
                
            article_url = f"https://www.toutiao.com{item.get('source_url', '')}"
            if not article_url or article_url == 'https://www.toutiao.com':
                continue
                
            content = ""
            if fetch_content and PLAYWRIGHT_AVAILABLE:
                content = fetch_article_content_playwright(article_url)
            
            if fetch_content and not content:
                content = fetch_article_content_fallback(article_url)
            
            article = {
                'title': item.get('title', '无标题'),
                'source': item.get('source', '未知来源'),
                'url': article_url,
                'abstract': item.get('abstract', '')[:300] if item.get('abstract') else '',
                'content': content,
                'images': [img.get('url', '') for img in item.get('image_list', [])[:3]],
                'category': category or '热点',
                'publish_time': extract_publish_time(item)
            }
            articles.append(article)
            
            if len(articles) >= ARTICLE_COUNT:
                break
                
        return articles
        
    except urllib.error.URLError as e:
        print(f"网络请求失败 ({category}): {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON解析失败 ({category}): {e}")
        return []
    except Exception as e:
        print(f"获取文章失败 ({category}): {e}")
        return []


def save_to_markdown(articles):
    """
    将文章保存到 markdown 文件
    """
    if not articles:
        print("没有文章可保存")
        return
        
    existing_content = ""
    if OUTPUT_FILE.exists():
        existing_content = OUTPUT_FILE.read_text(encoding='utf-8')
    
    articles_by_category = {}
    for article in articles:
        cat = article.get('category', '热点')
        if cat not in articles_by_category:
            articles_by_category[cat] = []
        articles_by_category[cat].append(article)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_content = ""
    
    for category in CATEGORIES:
        cat_articles = articles_by_category.get(category, [])
        if not cat_articles:
            continue
        new_content += f"# {category} ({len(cat_articles)}篇)\n\n"
        
        for i, article in enumerate(cat_articles, 1):
            new_content += f"## {i}. {article['title']}\n\n"
            new_content += f"- 来源: {article['source']}\n"
            new_content += f"- 链接: {article['url']}\n"
            
            if article.get('abstract'):
                new_content += f"- 摘要: {article['abstract']}\n"
            
            if article.get('content'):
                content_preview = article['content'][:4096] if len(article['content']) > 4096 else article['content']
                new_content += f"- 正文: {content_preview}\n"
            
            if article.get('images'):
                img_links = ' | '.join([f"![img](https:{img})" for img in article['images'] if img])
                if img_links:
                    new_content += f"- 图片: {img_links}\n"
            
            new_content += "\n---\n\n"
    
    if existing_content:
        if "更新时间:" in existing_content:
            parts = existing_content.split("更新时间:", 1)
            if len(parts) > 1:
                rest = parts[1]
                if "## " in rest:
                    existing_content = rest.split("## ", 1)[1]
                else:
                    existing_content = rest
    
    final_content = f"# 今日头条热点文章\n\n更新时间: {timestamp}\n\n总计: {len(articles)}篇\n\n{new_content}\n{existing_content}"
    
    OUTPUT_FILE.write_text(final_content, encoding='utf-8')
    print(f"已保存 {len(articles)} 篇文章到 {OUTPUT_FILE}")


def save_to_mysql(articles, db_connection_string):
    """
    将文章保存到 MySQL 数据库
    """
    if not articles:
        print("没有文章可保存到数据库")
        return 0
    
    saved_count = 0
    try:
        records = []
        for article in articles:
            article_id = ""
            if '/group/' in article.get('url', ''):
                article_id = article['url'].split('/group/')[1].split('/')[0].split('?')[0]
            
            record = {
                'article_id': article_id,
                'title': article.get('title', ''),
                'source': article.get('source', ''),
                'url': article.get('url', ''),
                'abstract': article.get('abstract', ''),
                'content': article.get('content', ''),
                'images': json.dumps(article.get('images', []), ensure_ascii=False),
                'category': article.get('category', '热点'),
                'publish_time': article.get('publish_time'),
                'created_by': 'system',
                'updated_by': 'system'
            }
            records.append(record)
        
        if records:
            df = pd.DataFrame(records)
            DataWriteUtil.write_to_db_with_create_info(df, "t_app_toutiao_article_acc", db_connection_string)
            saved_count = len(records)
            print(f"已保存 {saved_count} 篇文章到数据库")
        
    except Exception as e:
        print(f"保存到数据库失败: {e}")
        return 0
    
    return saved_count


def process(config: Config, dt: str, categories: list = None, fetch_content: bool = False):
    """
    业务处理函数
    参数:
        config - 配置对象
        dt - 日期参数
        categories - 分类列表
        fetch_content - 是否获取全文内容，默认False（快速模式）
    """
    if categories is None:
        categories = CATEGORIES
    
    db_connection_string = config.get_db_connection_string()
    
    content_mode = "完整模式 (含正文)" if fetch_content else "快速模式 (仅标题/摘要)"
    print(f"\n{'='*60}")
    print(f"开始获取今日头条热点文章...")
    print(f"  模式: {content_mode}")
    print(f"  分类: {', '.join(categories)}")
    print(f"  每类: {ARTICLE_COUNT} 篇")
    print(f"  Playwright: {'可用' if PLAYWRIGHT_AVAILABLE else '不可用'}")
    print(f"{'='*60}")
    
    all_articles = []
    total_categories = len(categories)
    last_category_id = None
    for idx, category in enumerate(categories, 1):
        category_id = CATEGORY_MAP.get(category, 'news_hot')
        
        if category_id == last_category_id:
            print(f"[{idx}/{total_categories}] 获取 {category} ... (跳过重复)")
            last_category_id = category_id
            continue
        
        last_category_id = category_id
        print(f"[{idx}/{total_categories}] 获取 {category} ...", end=" ", flush=True)
        
        try:
            articles = fetch_hot_articles(category, fetch_content)
        except Exception as e:
            print(f"错误: {e}")
            articles = []
            
        if articles:
            print(f"✓ {len(articles)} 篇")
            all_articles.extend(articles)
        else:
            print("✗ 无文章")
        
        if idx < total_categories:
            time.sleep(2)
    
    print(f"\n{'='*60}")
    if all_articles:
        save_to_markdown(all_articles)
        save_to_mysql(all_articles, db_connection_string)
        content_count = sum(1 for a in all_articles if a.get('content'))
        print(f"完成! 共获取 {len(all_articles)} 篇文章 ({content_count} 篇含正文)")
    else:
        print("获取失败或无文章")


def main():
    parser = argparse.ArgumentParser(description="获取今日头条热点文章")
    parser.add_argument("-d", "--dt", type=str, default="", help="日期参数")
    parser.add_argument("-c", "--config_path", type=str, default=CONFIG_PATH, help="配置文件路径")
    parser.add_argument("-i", "--interval", type=int, default=FETCH_INTERVAL, help="获取间隔(秒)")
    parser.add_argument("-cat", "--category", type=str, default="", 
                        help=f"指定分类 (可选: {', '.join(CATEGORIES)}, 默认全部)")
    parser.add_argument("-n", "--no-content", action="store_true", 
                        help="跳过获取全文内容（快速模式）")
    args = parser.parse_args()
    
    fetch_content = not args.no_content
    
    dt = args.dt
    config = Config(args.config_path)
    
    target_categories = CATEGORIES
    if args.category:
        if args.category in CATEGORY_MAP:
            target_categories = [args.category]
        else:
            print(f"未知分类: {args.category}")
            print(f"可用分类: {', '.join(CATEGORY_MAP.keys())}")
            return
    
    content_mode = "快速模式 (仅标题/摘要)" if not fetch_content else "完整模式 (含正文)"
    
    if args.interval > 0:
        print(f"\n{'='*60}")
        print(f"今日头条热点文章获取程序")
        print(f"  保存文件: {OUTPUT_FILE.absolute()}")
        print(f"  获取间隔: {args.interval} 秒")
        print(f"  模式: {content_mode}")
        print(f"{'='*60}\n")
        
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cycle_start = time.time()
            print(f"\n[{timestamp}] ===== 开始获取 =====")
            process(config, dt, target_categories, fetch_content)
            elapsed = time.time() - cycle_start
            print(f"[{timestamp}] 本轮耗时: {elapsed:.1f}秒")
            print(f"等待 {args.interval} 秒...\n")
            time.sleep(args.interval)
    else:
        print(f"模式: {content_mode}")
        processor = Processor(process=lambda: process(config, dt, target_categories, fetch_content))
        processor.do_process()


if __name__ == '__main__':
    main()
