#!/usr/bin/env python3
"""
今日头条文章发布器 v2.0
将本地 markdown 文件中的文字和图片发布到今日头条
支持 Playwright 浏览器自动化发布

使用方法:
    python app_toutiao_ariticle_publisher.py -f <markdown文件路径>
    python app_toutiao_ariticle_publisher.py --debug  # 开启调试模式
    python app_toutiao_ariticle_publisher.py --multi -f <多文章文件> -n 5  # 多文章模式
"""

from __future__ import annotations
import argparse
import gzip
import json
import os
import re
import sys
import time
import hashlib
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

DEBUG_MODE = False
PUBLISH_TIMEOUT = 30000

def log(msg: str) -> None:
    """调试日志"""
    if DEBUG_MODE:
        print(f"[DEBUG] {datetime.now().strftime('%H:%M:%S')} {msg}")

def print_step(step: str, msg: str) -> None:
    """打印步骤信息"""
    print(f"[{step}] {msg}")

try:
    from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None

APP_DIR = Path("/Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/python-app")
DATA_DIR = APP_DIR / "data"
COOKIE_FILE = DATA_DIR / "toutiao_cookies.json"
STATUS_FILE = DATA_DIR / "publish_status.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "close",
}

PUBLISH_URL = "https://mp.toutiao.com/profile_v4/graphic/publish"


class PublishStatus:
    """发布状态管理"""
    
    def __init__(self):
        self.status = self._load()
    
    def _load(self) -> Dict:
        if STATUS_FILE.exists():
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"published": [], "failed": [], "last_update": None}
    
    def _save(self) -> None:
        self.status["last_update"] = datetime.now().isoformat()
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.status, f, ensure_ascii=False, indent=2, default=str)
    
    def mark_published(self, file_path: str, title: str, url: str = None) -> None:
        self.status["published"].append({
            "file": file_path,
            "title": title,
            "url": url,
            "time": datetime.now().isoformat()
        })
        self._save()
    
    def mark_failed(self, file_path: str, title: str, error: str) -> None:
        self.status["failed"].append({
            "file": file_path,
            "title": title,
            "error": error,
            "time": datetime.now().isoformat()
        })
        self._save()
    
    def is_published(self, file_path: str) -> bool:
        return any(p["file"] == file_path for p in self.status["published"])
    
    def clear(self) -> None:
        self.status = {"published": [], "failed": [], "last_update": None}
        self._save()


def decode_response(response):
    """解码 HTTP 响应"""
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


def download_image(url: str, save_dir: str, headers: dict = None) -> Tuple[Optional[str], Optional[str]]:
    """下载图片到本地"""
    if headers is None:
        headers = HEADERS.copy()
    
    try:
        os.makedirs(save_dir, exist_ok=True)
        
        parsed_url = urllib.parse.urlparse(url)
        ext = os.path.splitext(parsed_url.path)[1]
        if not ext or len(ext) > 5:
            ext = '.jpg'
        
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:16]
        filename = f"{url_hash}{ext}"
        save_path = os.path.join(save_dir, filename)
        
        if os.path.exists(save_path) and os.path.getsize(save_path) > 100:
            return filename, save_path
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    image_data = response.read()
                
                if len(image_data) < 100:
                    raise Exception("下载的图片数据太小")
                
                with open(save_path, 'wb') as f:
                    f.write(image_data)
                
                return filename, save_path
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                raise
        
        return None, None
    except Exception as e:
        print(f"下载图片失败 {url}: {e}")
        return None, None


def parse_single_markdown(file_path: str) -> Tuple[str, str, List[str]]:
    """
    解析单个 markdown 文件，提取标题、正文和图片路径
    """
    file_path = Path(file_path)
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    title = None
    body_lines = []
    image_paths = []
    base_dir = file_path.parent
    
    lines = content.split('\n')
    in_frontmatter = False
    
    for line in lines:
        stripped = line.strip()
        
        if stripped == '---':
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                in_frontmatter = False
                continue
        
        if in_frontmatter:
            continue
        
        if line.startswith('# '):
            if title is None:
                title = line[2:].strip()
            else:
                body_lines.append(line)
        elif line.startswith('## '):
            body_lines.append(f"**{line[3:].strip()}**")
        elif line.startswith('> '):
            body_lines.append(f"*{line[2:].strip()}*")
        elif re.match(r'!\[[^\]]*\]\(([^)]+)\)', line):
            img_match = re.search(r'!\[[^\]]*\]\(([^)]+)\)', line)
            if img_match:
                img_path = img_match.group(1)
                
                if img_path.startswith('http://') or img_path.startswith('https://'):
                    image_paths.append(img_path)
                elif img_path.startswith('/'):
                    image_paths.append(img_path)
                else:
                    full_path = str(base_dir / img_path)
                    if os.path.exists(full_path):
                        image_paths.append(full_path)
        elif stripped == '---':
            continue
        elif stripped:
            body_lines.append(line)
    
    if title is None:
        title = file_path.stem
    
    full_content = '\n'.join(body_lines)
    
    return title, full_content, image_paths


def parse_toutiao_articles_markdown(file_path: str) -> List[Tuple[str, str, List[str]]]:
    """解析 toutiao_articles.md 格式的文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    articles = []
    current_title = None
    current_content = []
    current_images = []
    collecting_content = False
    
    lines = content.split('\n')
    
    for line in lines:
        line = line.rstrip()
        
        if line.startswith('## '):
            if current_title and current_content:
                articles.append((
                    current_title,
                    '\n'.join(current_content),
                    current_images.copy()
                ))
            
            current_title = line[3:].strip()
            current_content = []
            current_images = []
            collecting_content = False
            
        elif line.startswith('- 正文:'):
            collecting_content = True
            text = line[5:].strip()
            if text:
                current_content.append(text)
        elif line.startswith('- 图片:'):
            img_part = line[5:].strip()
            img_matches = re.findall(r'https?://[^\s|)]+', img_part)
            current_images.extend(img_matches)
        elif line.startswith('##'):
            continue
        elif line.startswith('#'):
            continue
        elif line.strip() == '---':
            collecting_content = False
        elif collecting_content and line.strip():
            current_content.append(line.strip())
        elif line.strip() and not line.startswith('-'):
            if current_title and not collecting_content:
                current_content.append(line.strip())
    
    if current_title and current_content:
        articles.append((
            current_title,
            '\n'.join(current_content),
            current_images.copy()
        ))
    
    return articles


class ToutiaoPublisher:
    """今日头条发布器"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.cookies = self._load_cookies()
        self.playwright = None
        self.status = PublishStatus()
    
    def _load_cookies(self) -> list:
        if COOKIE_FILE.exists():
            try:
                with open(COOKIE_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def _save_cookies(self, cookies: list) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(COOKIE_FILE, 'w') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        self.cookies = cookies
    
    def setup(self) -> 'ToutiaoPublisher':
        if not PLAYWRIGHT_AVAILABLE:
            raise Exception("Playwright 不可用，请安装: pip install playwright && playwright install chromium")
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 720}
        )
        
        if self.cookies:
            for cookie in self.cookies:
                try:
                    self.context.add_cookies([cookie])
                except Exception:
                    pass
        
        self.page = self.context.new_page()
        self.page.set_default_timeout(30000)
        return self
    
    def login(self) -> 'ToutiaoPublisher':
        if not self.page:
            self.setup()
        
        print("打开登录页面...")
        self.page.goto("https://mp.toutiao.com/auth/page/login", timeout=60000)
        
        print("\n" + "="*60)
        print("请使用今日头条 App 扫码登录")
        print("登录成功后按 Enter 继续...")
        print("="*60 + "\n")
        
        input()
        
        cookies = self.context.cookies()
        self._save_cookies(cookies)
        print("登录状态已保存")
        
        return self
    
    def check_login_status(self) -> bool:
        if not self.page:
            self.setup()
        
        try:
            self.page.goto("https://mp.toutiao.com/", timeout=30000, wait_until="domcontentloaded")
            self.page.wait_for_timeout(2000)
            
            if "登录" in self.page.url or "login" in self.page.url.lower():
                return False
            
            return True
        except Exception:
            return False
    
    def _close_popups(self) -> None:
        """关闭弹窗"""
        log("关闭弹窗")
        
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(300)
        
        try:
            close_selectors = [
                '.byte-drawer-mask',
                '[class*="mask"]',
                '[class*="modal"] [class*="close"]',
                '[aria-label="关闭"]',
                'button[class*="close"]'
            ]
            
            for selector in close_selectors:
                try:
                    overlays = self.page.locator(selector)
                    for i in range(overlays.count()):
                        try:
                            overlays.nth(i).click(timeout=500)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        
        self.page.wait_for_timeout(300)
    
    def _find_and_fill_title(self, title: str) -> bool:
        """填写标题"""
        log(f"填写标题: {title[:20]}...")
        
        title_selectors = [
            'textarea[placeholder*="标题"]',
            'input[placeholder*="标题"]',
            'input:not([type="radio"]):not([type="checkbox"]):not([type="file"])'
        ]
        
        for selector in title_selectors:
            try:
                inputs = self.page.locator(selector)
                count = inputs.count()
                log(f"标题选择器 '{selector}' 找到 {count} 个")
                
                for i in range(min(count, 10)):
                    inp = inputs.nth(i)
                    try:
                        if inp.is_visible(timeout=500):
                            bbox = inp.bounding_box()
                            if bbox and bbox['width'] > 100 and bbox['height'] > 20:
                                inp.click(timeout=1000)
                                inp.fill(title)
                                log("标题填写成功")
                                return True
                    except Exception:
                        continue
            except Exception:
                continue
        
        log("标题填写失败，使用 Tab")
        self.page.keyboard.press("Tab")
        self.page.keyboard.type(title, delay=30)
        return True
    
    def _fill_editor(self, content: str) -> bool:
        """填写编辑器内容"""
        log(f"填写内容，长度: {len(content)} 字符")
        
        editor_selectors = [
            '.ProseMirror',
            '[contenteditable="true"]',
            'div[contenteditable="true"]'
        ]
        
        for selector in editor_selectors:
            try:
                candidates = self.page.locator(selector)
                count = candidates.count()
                log(f"编辑器选择器 '{selector}' 找到 {count} 个")
                
                if count > 0:
                    for i in range(min(count, 3)):
                        editor = candidates.nth(i)
                        try:
                            if editor.is_visible(timeout=500):
                                bbox = editor.bounding_box()
                                if bbox and bbox['width'] > 200 and bbox['height'] > 100:
                                    editor.click(timeout=1000)
                                    log("编辑器已点击")
                                    break
                        except Exception:
                            continue
            except Exception:
                continue
        
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        total = len(paragraphs)
        
        for idx, para in enumerate(paragraphs):
            log(f"输入段落 {idx+1}/{total}")
            self.page.keyboard.type(para, delay=10)
            self.page.keyboard.press("Enter")
            self.page.wait_for_timeout(30)
        
        log("内容填写完成")
        return True
    
    def _insert_images_to_editor(self, images: List[str]) -> int:
        """向编辑器插入图片"""
        valid_images = [img for img in images if os.path.exists(img)]
        if not valid_images:
            log("没有有效图片")
            return 0
        
        log(f"插入图片，有效数量: {len(valid_images)}")
        
        inserted = 0
        for i, img_path in enumerate(valid_images[:9]):
            log(f"尝试插入图片 {i+1}/{min(len(valid_images), 9)}")
            
            try:
                img_buttons = self.page.locator('button:has-text("图片"), [aria-label*="图片"], [aria-label*="image"]')
                if img_buttons.count() > 0:
                    for j in range(min(img_buttons.count(), 3)):
                        btn = img_buttons.nth(j)
                        if btn.is_visible(timeout=500):
                            try:
                                with self.page.expect_file_chooser(timeout=2000) as fc_info:
                                    btn.click()
                                fc_info.value.set_files([img_path])
                                inserted += 1
                                log(f"图片 {i+1} 插入成功")
                                self.page.wait_for_timeout(2000)
                                break
                            except Exception as e:
                                log(f"图片 {i+1} 插入失败: {e}")
                                continue
            except Exception as e:
                log(f"插入图片 {i+1} 出错: {e}")
        
        log(f"图片插入完成: {inserted} 张")
        return inserted
    
    def _select_cover_image(self) -> int:
        """选择封面图，返回选择的数量"""
        log("选择封面图")
        
        self.page.wait_for_timeout(1000)
        
        cover_count = 0
        try:
            cover_selectors = [
                'div:has-text("封面")',
                '[class*="cover"]',
                '[class*="article-cover"]'
            ]
            
            for selector in cover_selectors:
                try:
                    elements = self.page.locator(selector)
                    count = elements.count()
                    log(f"封面选择器 '{selector}' 找到 {count} 个")
                    
                    if count > 0:
                        for i in range(min(count, 10)):
                            el = elements.nth(i)
                            try:
                                if el.is_visible(timeout=500):
                                    bbox = el.bounding_box()
                                    if bbox and bbox['width'] > 30:
                                        el.click(timeout=1000)
                                        log(f"点击封面区域 {i}")
                                        cover_count += 1
                                        break
                            except Exception:
                                continue
                except Exception:
                    continue
        except Exception as e:
            log(f"选择封面出错: {e}")
        
        if cover_count > 0:
            self.page.wait_for_timeout(1000)
            
            try:
                tab_selectors = [
                    'button:has-text("我的素材")',
                    'span:has-text("我的素材")'
                ]
                
                for selector in tab_selectors:
                    try:
                        tabs = self.page.locator(selector)
                        if tabs.count() > 0 and tabs.first.is_visible(timeout=500):
                            tabs.first.click(timeout=1000)
                            log("点击'我的素材'标签")
                            self.page.wait_for_timeout(1000)
                            break
                    except Exception:
                        continue
            except Exception:
                pass
            
            selected = 0
            try:
                img_containers = self.page.locator('[class*="material"], [class*="image-item"], [class*="img"]')
                count = img_containers.count()
                log(f"找到 {count} 个图片容器")
                
                for i in range(min(count, 12)):
                    try:
                        el = img_containers.nth(i)
                        if el.is_visible(timeout=500):
                            el.click(timeout=1000)
                            selected += 1
                            log(f"选择图片 {selected}")
                            self.page.wait_for_timeout(300)
                            if selected >= 3:
                                break
                    except Exception:
                        continue
            except Exception as e:
                log(f"选择图片出错: {e}")
            
            if selected > 0:
                self.page.wait_for_timeout(500)
                
                try:
                    confirm_selectors = [
                        'button:has-text("完成")',
                        'button:has-text("确定")',
                        'span:has-text("完成")',
                        'div:has-text("完成")'
                    ]
                    
                    for selector in confirm_selectors:
                        try:
                            btns = self.page.locator(selector)
                            if btns.count() > 0:
                                for i in range(btns.count()):
                                    btn = btns.nth(i)
                                    if btn.is_visible(timeout=500):
                                        btn.click(timeout=1000)
                                        log("点击完成按钮")
                                        self.page.wait_for_timeout(2000)
                                        return selected
                        except Exception:
                            continue
                except Exception as e:
                    log(f"确认选择出错: {e}")
        
        return cover_count
    
    def _save_draft(self) -> bool:
        """保存草稿"""
        log("保存草稿")
        
        try:
            draft_selectors = [
                'button:has-text("保存草稿")',
                'button:has-text("存为草稿")',
                'button:has-text("草稿")'
            ]
            
            for selector in draft_selectors:
                try:
                    btns = self.page.locator(selector)
                    if btns.count() > 0:
                        for i in range(btns.count()):
                            btn = btns.nth(i)
                            if btn.is_visible(timeout=500):
                                bbox = btn.bounding_box()
                                if bbox and bbox['width'] > 30:
                                    btn.click(timeout=2000)
                                    log("草稿保存成功")
                                    self.page.wait_for_timeout(2000)
                                    return True
                except Exception:
                    continue
        except Exception as e:
            log(f"保存草稿出错: {e}")
        
        return False
    
    def _click_publish(self) -> bool:
        log("点击发布按钮")
        
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.page.wait_for_timeout(500)
        
        publish_selectors = [
            'button:has-text("预览并发布")',
            'button:has-text("发布")',
        ]
        
        for selector in publish_selectors:
            try:
                btns = self.page.locator(selector)
                count = btns.count()
                log(f"选择器 '{selector}' 找到 {count} 个")
                
                if count > 0:
                    for i in range(count):
                        try:
                            btn = btns.nth(i)
                            bbox = btn.bounding_box()
                            text = (btn.text_content(timeout=500) or "").strip()
                            
                            if bbox and bbox['width'] > 50:
                                log(f"尝试点击: text='{text}', bbox={bbox}")
                                
                                center_x = bbox['x'] + bbox['width'] / 2
                                center_y = bbox['y'] + bbox['height'] / 2
                                
                                try:
                                    self.page.mouse.click(center_x, center_y)
                                    log(f"✓ 发布按钮已点击 (mouse): {text}")
                                    return True
                                except Exception as e:
                                    log(f"mouse.click 失败: {e}")
                                
                                try:
                                    btn.click(timeout=1000)
                                    log(f"✓ 发布按钮已点击: {text}")
                                    return True
                                except Exception as e:
                                    log(f"click 失败: {e}")
                                
                                try:
                                    btn.click(timeout=1000, force=True)
                                    log(f"✓ 发布按钮已点击 (force): {text}")
                                    return True
                                except Exception as e:
                                    log(f"force click 失败: {e}")
                                
                        except Exception as e:
                            log(f"按钮 {i} 处理失败: {e}")
                            continue
            except Exception as e:
                log(f"选择器 '{selector}' 出错: {e}")
        
        log("未找到发布按钮")
        return False
    
    def _wait_for_publish_complete(self) -> bool:
        log(f"等待发布完成，超时 {PUBLISH_TIMEOUT/1000} 秒...")
        
        max_wait = PUBLISH_TIMEOUT // 1000
        waited = 0
        
        while waited < max_wait:
            self.page.wait_for_timeout(2000)
            waited += 2
            
            if waited % 10 == 0:
                log(f"已等待 {waited} 秒...")
            
            try:
                all_buttons = self.page.locator('button')
                count = all_buttons.count()
                log(f"当前页面有 {count} 个按钮")
                
                confirm_keywords = ["确认发布", "确定", "确认", "发布", "提交", "完成", "关闭"]
                
                for i in range(count):
                    try:
                        btn = all_buttons.nth(i)
                        text = (btn.text_content(timeout=200) or "").strip()
                        
                        if any(kw in text for kw in confirm_keywords):
                            if btn.is_visible(timeout=200):
                                bbox = btn.bounding_box()
                                if bbox and bbox['width'] > 30:
                                    log(f"找到确认按钮: '{text}', 点击...")
                                    try:
                                        self.page.mouse.click(bbox['x'] + bbox['width']/2, bbox['y'] + bbox['height']/2)
                                        self.page.wait_for_timeout(3000)
                                        log("确认完成")
                                        return True
                                    except Exception as e:
                                        log(f"点击失败: {e}")
                    except Exception:
                        continue
            except Exception as e:
                log(f"检测按钮出错: {e}")
            
            try:
                page_text = self.page.content()
                success_keywords = ["发布成功", "发布完成", "已发布", "审核中", "文章管理", "提交成功"]
                
                for keyword in success_keywords:
                    if keyword in page_text:
                        log(f"检测到成功关键字: {keyword}")
                        self.page.wait_for_timeout(2000)
                        return True
            except Exception:
                pass
            
            try:
                current_url = self.page.url
                log(f"当前URL: {current_url}")
                
                if "success" in current_url.lower() or "published" in current_url.lower():
                    log("URL 表明发布成功")
                    return True
                
                if "article" in current_url or "content" in current_url:
                    if "publish" not in current_url:
                        log("离开发布页面，可能成功")
                        return True
            except Exception:
                pass
        
        log("等待发布完成超时，检查页面状态...")
        
        try:
            page_text = self.page.content()
            if any(kw in page_text for kw in ["审核中", "已发布", "发布成功"]):
                log("超时但检测到成功关键字")
                return True
        except Exception:
            pass
        
        log("返回失败")
        return False
    
    def publish_article(self, title: str, content: str, images: List[str] = None) -> Tuple[bool, str, str]:
        """发布文章"""
        if not self.page:
            raise Exception("请先调用 setup() 或 login()")
        
        if not title:
            return False, "标题不能为空", None
        
        title = title[:30]
        if len(title) < 2:
            title = title + " " * (2 - len(title))
        
        try:
            print(f"\n发布文章: {title[:20]}...")
            log("="*50)
            log("开始发布流程")
            
            log("步骤1: 打开发布页面")
            self.page.goto(PUBLISH_URL, timeout=60000, wait_until="networkidle")
            self.page.wait_for_timeout(2000)
            
            log("步骤2: 关闭弹窗")
            self._close_popups()
            
            log("步骤3: 填写标题")
            if self._find_and_fill_title(title):
                print("  ✓ 标题已填写")
            else:
                print("  ⚠ 标题填写可能失败")
            
            self.page.wait_for_timeout(500)
            
            log("步骤4: 填写内容")
            self._fill_editor(content)
            print("  ✓ 内容已填写")
            
            self.page.wait_for_timeout(1000)
            self._close_popups()
            
            log("步骤5: 插入图片")
            inserted = 0
            if images and len(images) > 0:
                inserted = self._insert_images_to_editor(images)
            print(f"  ✓ 已嵌入 {inserted} 张图片")
            
            log("步骤6: 选择封面图")
            cover_count = self._select_cover_image()
            print(f"  ✓ 封面图已选择 ({cover_count}张)")
            
            self.page.wait_for_timeout(500)
            
            log("步骤7: 保存草稿")
            if self._save_draft():
                print("  ✓ 草稿已保存")
            
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(500)
            
            log("步骤8: 点击发布")
            if self._click_publish():
                print("  ✓ 点击发布按钮成功")
            else:
                return False, "未找到发布按钮", None
            
            log("步骤9: 等待发布完成")
            if self._wait_for_publish_complete():
                print("  ✓ 文章发布成功")
                log("发布流程完成")
                return True, "发布成功", None
            else:
                return False, "发布等待超时", None
            
        except Exception as e:
            import traceback
            log(f"发布异常: {e}")
            log(traceback.format_exc())
            return False, f"发布失败: {str(e)}", None
    
    def close(self) -> None:
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


def publish_single_file(markdown_path: str, images_dir: str = None, skip_published: bool = True) -> int:
    """发布单个 markdown 文件"""
    
    print("="*60)
    print("今日头条文章发布器 v2.0 - 单文件模式")
    print("="*60)
    print(f"源文件: {markdown_path}")
    print(f"Playwright: {'可用' if PLAYWRIGHT_AVAILABLE else '不可用'}")
    
    if not PLAYWRIGHT_AVAILABLE:
        print("\n错误: 需要安装 Playwright")
        print("安装命令: pip install playwright && playwright install chromium")
        return 1
    
    md_path = Path(markdown_path)
    if not md_path.exists():
        print(f"\n错误: 文件不存在 - {markdown_path}")
        return 1
    
    status = PublishStatus()
    
    if skip_published and status.is_published(markdown_path):
        print("\n该文件已发布过，跳过...")
        return 0
    
    title, content, image_paths = parse_single_markdown(markdown_path)
    
    print(f"\n解析结果:")
    print(f"  标题: {title[:50]}...")
    print(f"  正文长度: {len(content)} 字符")
    print(f"  图片数量: {len(image_paths)}")
    
    local_images = [p for p in image_paths if os.path.exists(p)]
    remote_images = [p for p in image_paths if p.startswith('http')]
    
    print(f"  本地图片: {len(local_images)}")
    print(f"  远程图片: {len(remote_images)}")
    
    if images_dir is None:
        images_dir = str(md_path.parent / "temp_images")
    
    os.makedirs(images_dir, exist_ok=True)
    
    for img_url in remote_images[:9]:
        filename, save_path = download_image(img_url, images_dir)
        if save_path:
            local_images.append(save_path)
            print(f"  下载图片: {filename}")
    
    publisher = ToutiaoPublisher(headless=False)
    
    try:
        publisher.setup()
        
        if not publisher.check_login_status():
            print("\n需要登录...")
            publisher.login()
        
        if not publisher.check_login_status():
            print("\n登录失败，程序退出")
            return 1
        
        success, msg, url = publisher.publish_article(title, content, local_images)
        
        if success:
            print(f"\n{'='*60}")
            print(f"✓ 发布成功!")
            print("="*60)
            status.mark_published(markdown_path, title, url)
            return 0
        else:
            print(f"\n{'='*60}")
            print(f"✗ 发布失败: {msg}")
            print("="*60)
            status.mark_failed(markdown_path, title, msg)
            return 1
        
    finally:
        publisher.close()


def publish_multiple_files(file_list: List[str], images_dir: str = None) -> int:
    """发布多个文件"""
    
    print("="*60)
    print("今日头条文章发布器 v2.0 - 多文件模式")
    print("="*60)
    print(f"文件数量: {len(file_list)}")
    print(f"Playwright: {'可用' if PLAYWRIGHT_AVAILABLE else '不可用'}")
    
    if not PLAYWRIGHT_AVAILABLE:
        print("\n错误: 需要安装 Playwright")
        return 1
    
    publisher = ToutiaoPublisher(headless=False)
    status = PublishStatus()
    
    try:
        publisher.setup()
        
        if not publisher.check_login_status():
            print("\n需要登录...")
            publisher.login()
        
        if not publisher.check_login_status():
            print("\n登录失败，程序退出")
            return 1
        
        success_count = 0
        fail_count = 0
        
        for idx, file_path in enumerate(file_list, 1):
            print(f"\n[{idx}/{len(file_list)}] 处理: {Path(file_path).name[:30]}...")
            
            if status.is_published(file_path):
                print("  ⏭ 已发布过，跳过")
                continue
            
            title, content, image_paths = parse_single_markdown(file_path)
            local_images = [p for p in image_paths if os.path.exists(p)]
            
            success, msg, url = publisher.publish_article(title, content, local_images)
            
            if success:
                print(f"  ✓ {msg}")
                success_count += 1
                status.mark_published(file_path, title, url)
            else:
                print(f"  ✗ {msg}")
                fail_count += 1
                status.mark_failed(file_path, title, msg)
            
            if idx < len(file_list):
                print("  等待 5 秒...")
                time.sleep(5)
        
        print("\n" + "="*60)
        print(f"发布完成: 成功 {success_count}, 失败 {fail_count}")
        print("="*60)
        
        return 0 if fail_count == 0 else 1
        
    finally:
        publisher.close()


def main():
    default_file = "/Volumes/james1t/proj_opencode/article/工信部深夜发了一条消息，很多数据团队还没意识到机会 - 今日头条_20260320_052444.md"
    
    parser = argparse.ArgumentParser(
        description="今日头条文章发布器 v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python app_toutiao_ariticle_publisher.py -f article.md
  python app_toutiao_ariticle_publisher.py --debug
  python app_toutiao_ariticle_publisher.py -l file1.md file2.md file3.md
  python app_toutiao_ariticle_publisher.py --clear-status
        """
    )
    
    parser.add_argument("-f", "--file", type=str, default=default_file,
                        help="Markdown 文件路径")
    parser.add_argument("-l", "--list", nargs='+', type=str,
                        help="多个 Markdown 文件路径")
    parser.add_argument("-i", "--images-dir", type=str, default=None,
                        help="图片下载目录")
    parser.add_argument("--headless", action="store_true",
                        help="无头模式运行")
    parser.add_argument("--relogin", action="store_true",
                        help="强制重新登录")
    parser.add_argument("--debug", action="store_true",
                        help="开启调试模式")
    parser.add_argument("--no-skip", action="store_true",
                        help="不跳过已发布的文件")
    parser.add_argument("--clear-status", action="store_true",
                        help="清除发布状态记录")
    parser.add_argument("--show-status", action="store_true",
                        help="显示发布状态")
    
    args = parser.parse_args()
    
    global DEBUG_MODE
    DEBUG_MODE = args.debug
    
    status = PublishStatus()
    
    if args.show_status:
        print("\n发布状态:")
        print(f"  已发布: {len(status.status['published'])} 篇")
        print(f"  失败: {len(status.status['failed'])} 篇")
        if status.status['last_update']:
            print(f"  最后更新: {status.status['last_update']}")
        return 0
    
    if args.clear_status:
        status.clear()
        print("已清除发布状态记录")
        return 0
    
    if args.relogin:
        if COOKIE_FILE.exists():
            COOKIE_FILE.unlink()
            print("已清除登录状态")
    
    if args.list:
        return publish_multiple_files(args.list, args.images_dir)
    else:
        return publish_single_file(args.file, args.images_dir, skip_published=not args.no_skip)


if __name__ == "__main__":
    sys.exit(main())
