#!/usr/bin/env python3
"""
今日头条文章下载器
使用 Playwright 或 urllib 下载图文文章内容并保存为文件
支持图片下载到本地
"""
import sys
import os
import re
import json
import urllib.request
import urllib.error
import urllib.parse
import hashlib
import time
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "close",
    "Referer": "https://www.toutiao.com/",
}


def decode_response(response):
    """解码HTTP响应，处理gzip压缩"""
    import gzip
    content = response.read()
    
    content_encoding = response.headers.get('Content-Encoding', '').lower()
    if content_encoding == 'gzip':
        try:
            content = gzip.decompress(content)
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


BLOCKED_DOMAINS = [
    'csdnimg.cn/public/common/toolbar',
    'csdnimg.cn/release/blogv2/dist/mobile/img',
]

BLOCKED_PATTERNS = [
    'toolbar-icon',
    'wap-tobar',
    'wap-articleRead',
    'hotHeart',
    'iconLeftArrow',
    'renewal',
    'toolbar-icon',
]


def is_allowed_image(url):
    url_lower = url.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern in url_lower:
            return False
    return True


def download_image(url, save_path, headers=None):
    if not is_allowed_image(url):
        return None
    
    try:
        if headers is None:
            headers = HEADERS.copy()
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    image_data = response.read()
                
                if len(image_data) < 100:
                    raise Exception("下载的图片数据太小")
                
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(image_data)
                
                return os.path.basename(save_path)
            except urllib.error.HTTPError as e:
                if e.code == 403 and attempt < max_retries - 1:
                    print(f"  403错误，重试 {attempt + 1}/{max_retries}...")
                    time.sleep(1)
                    continue
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  下载失败，重试 {attempt + 1}/{max_retries}: {e}")
                    time.sleep(1)
                    continue
                raise
        
        return None
    except Exception as e:
        print(f"下载图片失败 {url}: {e}")
        return None


def get_image_filename(url):
    """根据URL生成图片文件名"""
    parsed_url = urllib.parse.urlparse(url)
    ext = os.path.splitext(parsed_url.path)[1]
    if not ext or len(ext) > 5:
        ext = '.jpg'
    
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:16]
    return f"{url_hash}{ext}"


def fetch_article_content_playwright(url):
    """
    使用 Playwright 获取文章正文内容和图片，格式化为 MinerU 风格 Markdown
    参数: url - 文章URL
    返回: (标题, Markdown内容, 图片URL列表)
    """
    if not PLAYWRIGHT_AVAILABLE:
        return None, None, []
    
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
                return None, None, []
            
            if "error" in page.url.lower() or page.title() == "":
                browser.close()
                return None, None, []
            
            title = page.title()
            
            try:
                body = page.query_selector("body")
                if body:
                    html_content = body.inner_html()
                    markdown_lines = []
                    image_urls = []
                    
                    noise_patterns = ['打开APP', 'APP内打开', '去听全文', '查看图片详情', '立即下载', '扫码下载', 
                                     '关注', '点赞', '评论', '分享', '广告', '推荐', '阅读全文', '点击查看']
                    
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    img_tags = soup.find_all('img')
                    for img in img_tags:
                        src = img.get('src', '')
                        data_src = img.get('data-src', '')
                        data_original = img.get('data-original', '')
                        
                        img_url = data_src or data_original or src
                        
                        if img_url and (img_url.startswith('http://') or img_url.startswith('https://')):
                            if img_url not in image_urls:
                                image_urls.append(img_url)
                    
                    for tag in soup.find_all(['h1', 'h2', 'h3', 'p']):
                        text = tag.get_text(strip=True)
                        
                        if not text or len(text) < 10:
                            continue
                        
                        if any(p in text for p in noise_patterns):
                            continue
                        
                        if tag.name == 'h1':
                            markdown_lines.append(f"# {text}")
                        elif tag.name == 'h2':
                            markdown_lines.append(f"## {text}")
                        elif tag.name == 'h3':
                            markdown_lines.append(f"### {text}")
                        elif tag.name == 'p':
                            markdown_lines.append(text)
                    
                    if markdown_lines:
                        markdown_content = '\n\n'.join(markdown_lines)
                        browser.close()
                        return title, markdown_content, image_urls
            except:
                pass
            
            browser.close()
            return None, None, []
            
    except Exception as e:
        print(f"Playwright error: {e}")
        return None, None, []


def fetch_article_content_fallback(url):
    """
    备用方法：使用 urllib 获取文章正文，格式化为 Markdown
    返回: (标题, Markdown内容, 图片URL列表)
    """
    try:
        mobile_url = url.replace('www.toutiao.com', 'm.toutiao.com')
        req = urllib.request.Request(mobile_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = decode_response(response)
        
        title = ""
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
        
        image_urls = []
        img_patterns = [
            r'<img[^>]+src=["\']([^"\']+)["\']',
            r'<img[^>]+data-src=["\']([^"\']+)["\']',
            r'<img[^>]+data-original=["\']([^"\']+)["\']',
        ]
        
        for pattern in img_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for img_url in matches:
                if img_url and (img_url.startswith('http://') or img_url.startswith('https://')):
                    if img_url not in image_urls:
                        image_urls.append(img_url)
        
        patterns = [
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*article[^"]*"[^>]*>(.*?)</div>',
        ]
        
        markdown_lines = []
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                content_html = match.group(1)
                
                h1_matches = re.findall(r'<h1[^>]*>(.*?)</h1>', content_html, re.IGNORECASE)
                for h1 in h1_matches:
                    text = re.sub(r'<[^>]+>', '', h1).strip()
                    if text:
                        markdown_lines.append(f"# {text}")
                
                h2_matches = re.findall(r'<h2[^>]*>(.*?)</h2>', content_html, re.IGNORECASE)
                for h2 in h2_matches:
                    text = re.sub(r'<[^>]+>', '', h2).strip()
                    if text:
                        markdown_lines.append(f"## {text}")
                
                p_matches = re.findall(r'<p[^>]*>(.*?)</p>', content_html, re.IGNORECASE)
                for p in p_matches:
                    text = re.sub(r'<[^>]+>', '', p).strip()
                    text = re.sub(r'\s+', ' ', text)
                    if len(text) > 20:
                        markdown_lines.append(text)
                
                if markdown_lines:
                    return title, '\n\n'.join(markdown_lines), image_urls
        
        return title, "", image_urls
        
    except Exception as e:
        print(f"Fallback error: {e}")
        return None, None, []


def download_article_from_toutiao(url, output_path):
    """
    下载文章内容到本地，保存为 MinerU 格式的 Markdown
    同时下载文章中的图片到本地 images/ 目录

    Args:
        url: 文章URL
        output_path: 输出目录

    Returns:
        (成功状态, 保存的文件路径)
    """
    print(f"从以下地址下载文章: {url}")
    print(f"输出目录: {output_path}")
    
    os.makedirs(output_path, exist_ok=True)
    
    title = None
    content = None
    image_urls = []
    
    print(f"\n[方法1] 尝试使用 Playwright...")
    if PLAYWRIGHT_AVAILABLE:
        title, content, image_urls = fetch_article_content_playwright(url)
        if content:
            print("✓ Playwright 获取成功")
        else:
            print("✗ Playwright 获取失败")
    else:
        print("✗ Playwright 不可用")
    
    if not content:
        print(f"\n[方法2] 尝试使用 urllib...")
        title, content, image_urls = fetch_article_content_fallback(url)
        if content:
            print("✓ urllib 获取成功")
        else:
            print("✗ urllib 获取失败")
    
    if not content:
        print("\n下载失败: 无法获取文章内容")
        return False, None
    
    if not title:
        title = "未命名文章"
    
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
    safe_title = safe_title[:100]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_title}_{timestamp}.md"
    file_path = os.path.join(output_path, filename)
    
    images_dir = os.path.join(output_path, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    downloaded_images = {}
    if image_urls:
        print(f"\n[3] 下载图片 (共 {len(image_urls)} 张)...")
        for idx, img_url in enumerate(image_urls[:20], 1):
            img_filename = get_image_filename(img_url)
            img_save_path = os.path.join(images_dir, img_filename)
            
            downloaded_filename = download_image(img_url, img_save_path)
            if downloaded_filename:
                downloaded_images[img_url] = f"images/{downloaded_filename}"
                print(f"  [{idx}/{min(len(image_urls), 20)}] ✓ {downloaded_filename}")
            else:
                print(f"  [{idx}/{min(len(image_urls), 20)}] ✗ {img_url}")
    
    markdown_content = f"# {title}\n\n{content}"
    
    if downloaded_images:
        markdown_content = f"# {title}\n\n"
        for img_url, local_path in downloaded_images.items():
            markdown_content += f"![]({local_path})\n\n"
        markdown_content += content
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"\n下载成功!")
    print(f"标题: {title}")
    print(f"内容长度: {len(content)} 字符")
    print(f"图片数量: {len(downloaded_images)} 张")
    print(f"保存路径: {file_path}")
    
    return True, file_path


def main():
    output_path = "/Volumes/james1t/proj_opencode/article/"

    article_url = """
https://www.toutiao.com/article/7618782647652794921/?app=news_article&category_new=__all__&module_name=Android_tt_others&share_did=MS4wLjACAAAAi_3K-Bdl8FxAtlKsQg3ZUlNX5x0E-d6L-7jrTpSdNG8&share_uid=MS4wLjABAAAAKW63wJ9i-ORmR-N82xWxGChfXj21ZgMfuUztQ7WSN9MaNMYGLBiSm-2vWLjgi_b0&timestamp=1773917733&tt_from=feishu&upstream_biz=Android_others&utm_campaign=client_share&utm_medium=toutiao_android&utm_source=feishu&share_token=d98d58ec-7236-4dca-9171-2a07864daa78&source=m_redirect
    """.strip()

    print("=" * 60)
    print("今日头条文章下载器")
    print("=" * 60)
    print(f"Playwright 可用性: {'是' if PLAYWRIGHT_AVAILABLE else '否'}\n")

    success, file_path = download_article_from_toutiao(article_url, output_path)

    if success:
        print(f"\n{'='*60}")
        print("完成!")
    else:
        print(f"\n下载失败，请检查:")
        print("1. 文章URL是否正确")
        print("2. 文章是否已删除或设为私密")
        print("3. 网络连接是否正常")
        print("4. 是否需要安装 Playwright: pip install playwright && playwright install chromium")
        sys.exit(1)

if __name__ == "__main__":
    main()
