#!/usr/bin/env python3
"""
Toutiao Hot Articles Fetcher
每10分钟获取一次 https://www.toutiao.com/ 的10条热点文章，保存到 markdown 文件
使用 Playwright 提取文章正文内容
支持保存到 MySQL 数据库
"""

import json
import re
import time
import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

# 添加 python_app 到路径
sys.path.insert(0, '/Users/Shared/_AllDocMap/02_Project/gitee/python-app')

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

import urllib.request
import urllib.error

try:
    from python_app.config import Config
    from python_app.lib.data_write_util import DataWriteUtil
    PYTHON_APP_AVAILABLE = True
except ImportError:
    PYTHON_APP_AVAILABLE = False

# 配置
OUTPUT_FILE = Path("./toutiao_articles.md")
FETCH_INTERVAL = 600  # 10分钟 = 600秒
ARTICLE_COUNT = 10

# 配置文件路径
CONFIG_PATH = "/Users/Shared/_AllDocMap/02_Project/gitee/python-app/app_local/article/config/app_article_config.yaml"

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.toutiao.com/",
    "Cookie": "tt_webid=; csrftoken=; sid_tt=; sessionid=;"
}


def fetch_article_content_playwright(url):
    """
    使用 Playwright 获取文章正文内容
    参数: url - 文章URL
    返回: 正文文本
    """
    if not PLAYWRIGHT_AVAILABLE:
        return ""
    
    # 转换为移动端URL
    mobile_url = url.replace('www.toutiao.com', 'm.toutiao.com').replace('/group/', '/article/')
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                viewport={'width': 390, 'height': 844}
            )
            page = context.new_page()
            
            # 访问移动端文章页面
            try:
                page.goto(mobile_url, wait_until="networkidle", timeout=20000)
                page.wait_for_timeout(2000)
            except Exception as e:
                browser.close()
                return ""
            
            # 检查是否是错误页面
            if "error" in page.url.lower() or page.title() == "":
                browser.close()
                return ""
            
            # 获取主要内容
            try:
                body = page.query_selector("body")
                if body:
                    text = body.inner_text()
                    # 清理文本
                    lines = text.split('\n')
                    # 过滤短行和噪声
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
        # 尝试移动端
        mobile_url = url.replace('www.toutiao.com', 'm.toutiao.com')
        req = urllib.request.Request(mobile_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
        
        # 查找可能包含正文的标签
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


def fetch_hot_articles():
    """
    获取今日头条热点文章
    返回: 文章列表
    """
    url = "https://www.toutiao.com/api/pc/feed/?category=news_hot&utm_source=toutiao&widen=1&max_behot_time=0&max_behot_time_tmp=0&tadrequire=true&as=A1152B8F0F9F0F5&cp=5F9E0F9E0F9E5&_signature="
    
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        articles = []
        if data.get('data'):
            for item in data['data'][:ARTICLE_COUNT * 2]:
                # 过滤广告和无关内容
                if item.get('is_ad') or item.get('ad_id'):
                    continue
                if item.get('item_type') == 'ad':
                    continue
                    
                article_url = f"https://www.toutiao.com{item.get('source_url', '')}"
                
                # 使用 Playwright 获取正文
                content = ""
                if PLAYWRIGHT_AVAILABLE:
                    content = fetch_article_content_playwright(article_url)
                
                # 如果 Playwright 失败，使用备用方法
                if not content:
                    content = fetch_article_content_fallback(article_url)
                
                article = {
                    'title': item.get('title', '无标题'),
                    'source': item.get('source', '未知来源'),
                    'url': article_url,
                    'abstract': item.get('abstract', '')[:300] if item.get('abstract') else '',
                    'content': content,
                    'images': [img.get('url', '') for img in item.get('image_list', [])[:3]]
                }
                articles.append(article)
                
                if len(articles) >= ARTICLE_COUNT:
                    break
                    
        return articles
        
    except urllib.error.URLError as e:
        print(f"网络请求失败: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        return []
    except Exception as e:
        print(f"获取文章失败: {e}")
        return []


def save_to_markdown(articles):
    """
    将文章保存到 markdown 文件
    """
    if not articles:
        print("没有文章可保存")
        return
        
    # 读取现有内容
    existing_content = ""
    if OUTPUT_FILE.exists():
        existing_content = OUTPUT_FILE.read_text(encoding='utf-8')
    
    # 生成新内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_content = ""
    
    for i, article in enumerate(articles, 1):
        new_content += f"## {i}. {article['title']}\n\n"
        new_content += f"- 来源: {article['source']}\n"
        new_content += f"- 链接: {article['url']}\n"
        
        # 添加摘要
        if article.get('abstract'):
            new_content += f"- 摘要: {article['abstract']}\n"
        
        # 添加正文内容
        if article.get('content'):
            content_preview = article['content'][:4096] if len(article['content']) > 4096 else article['content']
            new_content += f"- 正文: {content_preview}\n"
        
        # 添加图片
        if article.get('images'):
            img_links = ' | '.join([f"![img](https:{img})" for img in article['images'] if img])
            if img_links:
                new_content += f"- 图片: {img_links}\n"
        
        new_content += "\n---\n\n"
    
    # 追加到文件
    if existing_content:
        if "更新时间:" in existing_content:
            parts = existing_content.split("更新时间:", 1)
            if len(parts) > 1:
                rest = parts[1]
                if "## " in rest:
                    existing_content = rest.split("## ", 1)[1]
                else:
                    existing_content = rest
    
    final_content = f"# 今日头条热点文章\n\n更新时间: {timestamp}\n\n{new_content}\n{existing_content}"
    
    OUTPUT_FILE.write_text(final_content, encoding='utf-8')
    print(f"已保存 {len(articles)} 篇文章到 {OUTPUT_FILE}")


def save_to_mysql(articles):
    """
    将文章保存到 MySQL 数据库（使用 python_app DataWriteUtil）
    """
    if not articles:
        print("没有文章可保存到数据库")
        return 0
    
    if not PYTHON_APP_AVAILABLE:
        print("python_app 库未安装，无法保存到数据库")
        return 0
    
    saved_count = 0
    try:
        # 加载配置文件
        config = Config(CONFIG_PATH)
        db_connection_string = config.get_db_connection_string()
        
        # 准备数据
        records = []
        for article in articles:
            # 提取文章ID
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
                'created_by': 'system',
                'updated_by': 'system'
            }
            records.append(record)
        
        if records:
            # 使用 DataWriteUtil 写入数据库
            df = pd.DataFrame(records)
            DataWriteUtil.write_to_db_with_create_info(df, "t_app_toutiao_article_acc", db_connection_string)
            saved_count = len(records)
            print(f"已保存 {saved_count} 篇文章到数据库")
        
    except Exception as e:
        print(f"保存到数据库失败: {e}")
        return 0
    
    return saved_count


def main():
    """
    主循环：每10分钟获取一次文章
    """
    print(f"今日头条热点文章获取程序已启动")
    print(f"保存文件: {OUTPUT_FILE.absolute()}")
    print(f"获取间隔: {FETCH_INTERVAL} 秒")
    print(f"Playwright可用: {PLAYWRIGHT_AVAILABLE}")
    print(f"python_app可用: {PYTHON_APP_AVAILABLE}")
    print("-" * 50)
    
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] 正在获取热点文章...")
        
        articles = fetch_hot_articles()
        
        if articles:
            # 保存到markdown文件
            save_to_markdown(articles)
            # 保存到数据库
            save_to_mysql(articles)
            # 统计有正文的文章数量
            content_count = sum(1 for a in articles if a.get('content'))
            print(f"[{timestamp}] 获取成功，共 {len(articles)} 篇文章，其中 {content_count} 篇包含正文")
        else:
            print(f"[{timestamp}] 获取失败或无文章")
        
        print(f"等待 {FETCH_INTERVAL} 秒后继续...")
        time.sleep(FETCH_INTERVAL)


if __name__ == "__main__":
    main()
