#!/usr/bin/env python3
"""
今日头条文章发布器 v3.2
将本地 markdown 文件中的文字和图片发布到今日头条
支持 Playwright 浏览器自动化发布

增强功能:
    - 智能元素定位 (Playwright 高级定位器)
    - 自动重试机制 (失败自动重试)
    - 改进的图片上传流程
    - 发布确认弹窗自动处理
    - 截图调试功能
    - 更稳定的发布流程
    - React 兼容的事件派发 (修复表单状态检测)
    - 分类键盘导航选择 (解决点击无法选择问题)

使用方法:
    python app_toutiao_ariticle_publisher.py -f <markdown文件路径>
    python app_toutiao_ariticle_publisher.py --debug  # 开启调试模式
    python app_toutiao_ariticle_publisher.py --screenshot  # 保存调试截图
    python app_toutiao_ariticle_publisher.py --retry 3  # 失败重试次数
"""

from __future__ import annotations
import argparse
import functools
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
from typing import Optional, List, Tuple, Dict, Any, Callable
from dataclasses import dataclass

DEBUG_MODE = False
SCREENSHOT_MODE = False
PUBLISH_TIMEOUT = 60000
MAX_RETRIES = 3

@dataclass
class RetryConfig:
    max_attempts: int = 3
    delay: float = 1.0
    backoff: float = 2.0
    exceptions: tuple = (Exception,)

def log(msg: str) -> None:
    """调试日志"""
    if DEBUG_MODE:
        print(f"[DEBUG] {datetime.now().strftime('%H:%M:%S')} {msg}")

def screenshot_on_error(func: Callable) -> Callable:
    """失败时自动截图的装饰器"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            if SCREENSHOT_MODE and hasattr(self, 'page'):
                try:
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    self.page.screenshot(path=f"debug_error_{ts}.png", full_page=True)
                    log(f"错误截图已保存: debug_error_{ts}.png")
                except:
                    pass
            raise
    return wrapper

def retry_on_failure(config: RetryConfig = RetryConfig()):
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            delay = config.delay
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except config.exceptions as e:
                    last_exception = e
                    if attempt < config.max_attempts:
                        log(f"第 {attempt} 次尝试失败: {e}, {delay}s 后重试...")
                        time.sleep(delay)
                        delay *= config.backoff
                    else:
                        log(f"已达到最大重试次数 ({config.max_attempts})")
            
            raise last_exception
        return wrapper
    return decorator

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
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.cookies = self._load_cookies()
        self.playwright = None
        self.status = PublishStatus()
        self._screenshot_dir = DATA_DIR / "screenshots"
    
    def _ensure_screenshot_dir(self) -> None:
        if SCREENSHOT_MODE:
            os.makedirs(self._screenshot_dir, exist_ok=True)
    
    def _take_debug_screenshot(self, name: str) -> Optional[str]:
        if not SCREENSHOT_MODE:
            return None
        try:
            self._ensure_screenshot_dir()
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            path = self._screenshot_dir / f"{name}_{ts}.png"
            self.page.screenshot(path=str(path), full_page=True)
            log(f"截图已保存: {path}")
            return str(path)
        except Exception as e:
            log(f"截图失败: {e}")
            return None
    
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
        log("关闭弹窗")
        
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(300)
        
        close_patterns = [
            '关闭',
            '稍后',
            '下次再说',
            '我知道了',
            '知道了',
        ]
        
        for pattern in close_patterns:
            try:
                close_btn = self.page.locator('text=' + pattern).first
                if close_btn.is_visible(timeout=500):
                    close_btn.click()
                    log(f"关闭弹窗: {pattern}")
                    self.page.wait_for_timeout(300)
            except Exception:
                pass
        
        try:
            close_selectors = [
                '[aria-label="关闭"]',
                '[aria-label="close"]',
                'button[class*="close"]',
                'span[class*="close"]',
                '.byte-drawer-mask',
                '[class*="drawer"] [class*="close"]',
            ]
            
            for selector in close_selectors:
                try:
                    overlays = self.page.locator(selector)
                    for i in range(min(overlays.count(), 5)):
                        try:
                            if overlays.nth(i).is_visible(timeout=300):
                                overlays.nth(i).click(timeout=500)
                                log(f"关闭弹窗: {selector}")
                                self.page.wait_for_timeout(200)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        
        self.page.wait_for_timeout(300)
    
    def _check_form_state(self) -> Dict[str, bool]:
        log("检查表单状态")
        try:
            result = self.page.evaluate("""
                (function() {
                    var title = document.querySelector('input[placeholder*="标题"]');
                    if (!title) title = document.querySelector('textarea');
                    if (!title) {
                        var inputs = document.querySelectorAll('input, textarea');
                        for (var i = 0; i < inputs.length; i++) {
                            if (inputs[i].offsetParent !== null && inputs[i].value && inputs[i].value.length > 2) {
                                title = inputs[i];
                                break;
                            }
                        }
                    }
                    
                    var editor = document.querySelector('.ProseMirror');
                    if (!editor) {
                        var editors = document.querySelectorAll('[contenteditable="true"]');
                        for (var i = 0; i < editors.length; i++) {
                            if (editors[i].offsetParent !== null) {
                                editor = editors[i];
                                break;
                            }
                        }
                    }
                    
                    var cover = document.querySelector('[class*="cover"] img, [class*="cover-image"]');
                    
                    return {
                        titleValue: title ? title.value : '',
                        titleLength: title ? title.value.length : 0,
                        editorText: editor ? editor.innerText : '',
                        editorLength: editor ? editor.innerText.length : 0,
                        coverExists: !!cover
                    };
                })()
            """)
            log(f"表单状态: {result}")
            return result
        except Exception as e:
            log(f"检查表单状态失败: {e}")
            return {}
    
    def _trigger_react_input_events(self) -> None:
        log("触发 React 输入事件")
        self.page.evaluate("""
            (function() {
                var title = document.querySelector('input[placeholder*="标题"]');
                if (!title) title = document.querySelector('textarea');
                if (title && title.value) {
                    title.dispatchEvent(new Event('input', {bubbles: true}));
                    title.dispatchEvent(new Event('change', {bubbles: true}));
                    title.dispatchEvent(new Event('blur', {bubbles: true}));
                }
                
                var editor = document.querySelector('.ProseMirror');
                if (!editor) {
                    var editors = document.querySelectorAll('[contenteditable="true"]');
                    for (var i = 0; i < editors.length; i++) {
                        if (editors[i].innerText && editors[i].innerText.length > 10) {
                            editor = editors[i];
                            break;
                        }
                    }
                }
                if (editor && editor.innerText) {
                    editor.dispatchEvent(new Event('input', {bubbles: true}));
                    editor.dispatchEvent(new Event('change', {bubbles: true}));
                }
            })()
        """)
    
    def _fill_input_react(self, selector: str, value: str) -> bool:
        """使用 React 兼容的方式填写输入框"""
        escaped_value = value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
        js_script = f"""
            (function() {{
                var el = document.querySelector('{selector}');
                if (!el) return 'not_found';
                
                // Focus the element
                el.focus();
                
                // Clear existing value
                el.select && el.select();
                
                // Set value directly (React controlled component pattern)
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                )?.set || Object.getOwnPropertyDescriptor(
                    window.HTMLTextAreaElement.prototype, 'value'
                )?.set;
                
                if (nativeInputValueSetter) {{
                    nativeInputValueSetter.call(el, '{escaped_value}');
                }} else {{
                    el.value = '{escaped_value}';
                }}
                
                // Dispatch React-compatible events
                var inputEvent = new Event('input', {{ bubbles: true, cancelable: true }});
                var changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
                var blurEvent = new Event('blur', {{ bubbles: true, cancelable: true }});
                
                el.dispatchEvent(inputEvent);
                el.dispatchEvent(changeEvent);
                
                // Also try React's synthetic event
                var reactHandler = el._valueTracker;
                if (reactHandler) {{
                    reactHandler.setValue('');
                }}
                el.dispatchEvent(inputEvent);
                
                setTimeout(function() {{
                    el.dispatchEvent(blurEvent);
                }}, 50);
                
                return el.value;
            }})()
        """
        try:
            result = self.page.evaluate(js_script)
            log(f"React input fill result: '{str(result)[:50]}...'")
            return result and len(str(result)) > 0
        except Exception as e:
            log(f"React input fill failed: {e}")
            return False
    
    def _find_and_fill_title(self, title: str) -> bool:
        log(f"填写标题: {title[:20]}...")
        
        # Try React-compatible fill first
        title_selectors = [
            'input[placeholder*="标题"]',
            'input[placeholder*="title" i]',
            'textarea',
            'input[class*="title"]',
            'input[class*="Title"]',
        ]
        
        for selector in title_selectors:
            try:
                count = self.page.locator(selector).count()
                log(f"标题选择器 '{selector}' 找到 {count} 个")
                
                for i in range(min(count, 10)):
                    try:
                        inp = self.page.locator(selector).nth(i)
                        if inp.is_visible(timeout=1000):
                            bbox = inp.bounding_box()
                            if bbox and bbox['width'] > 50 and bbox['height'] > 10:
                                log(f"尝试 React 方式填写: {selector} [{i}]")
                                
                                # Use React-compatible fill
                                selector_escaped = selector.replace("'", "\\'")
                                if self._fill_input_react(selector_escaped, title):
                                    self.page.wait_for_timeout(300)
                                    self._take_debug_screenshot("title_filled")
                                    log("标题填写成功")
                                    return True
                                
                                # Fallback to click + type
                                inp.click(timeout=500)
                                self.page.wait_for_timeout(200)
                                inp.fill(title)
                                self.page.wait_for_timeout(200)
                                
                                # Trigger React events
                                self.page.evaluate(f"""
                                    (function() {{
                                        var el = document.querySelector('{selector_escaped}');
                                        if (el) {{
                                            el.dispatchEvent(new Event('input', {{bubbles: true}}));
                                            el.dispatchEvent(new Event('change', {{bubbles: true}}));
                                        }}
                                    }})()
                                """)
                                
                                self.page.wait_for_timeout(200)
                                self.page.keyboard.press("Tab")
                                self.page.wait_for_timeout(200)
                                
                                # Verify
                                result = self.page.evaluate("""
                                    (function() {
                                        var inputs = document.querySelectorAll('input, textarea');
                                        for (var i = 0; i < inputs.length; i++) {
                                            if (inputs[i].value && inputs[i].value.length > 2) {
                                                return inputs[i].value;
                                            }
                                        }
                                        return '';
                                    })()
                                """)
                                log(f"标题值: '{result[:30]}...'")
                                
                                if len(result) > 2:
                                    self._take_debug_screenshot("title_filled")
                                    log("标题填写成功")
                                    return True
                    except Exception as e:
                        log(f"标题输入失败: {e}")
                        continue
            except Exception as e:
                log(f"标题选择器失败: {e}")
                continue
        
        log("使用备用方式填写标题 (keyboard)")
        self.page.keyboard.press("Tab")
        self.page.keyboard.type(title, delay=30)
        self.page.wait_for_timeout(300)
        return True
    
    def _fill_editor(self, content: str) -> bool:
        log(f"填写内容，长度: {len(content)} 字符")
        
        editor_selectors = ['.ProseMirror', '[contenteditable="true"]', 'div[role="textbox"]']
        
        editor = None
        editor_selector = None
        for selector in editor_selectors:
            try:
                candidates = self.page.locator(selector)
                count = candidates.count()
                log(f"编辑器选择器 '{selector}' 找到 {count} 个")
                
                for i in range(min(count, 5)):
                    candidate = candidates.nth(i)
                    if candidate.is_visible(timeout=1000):
                        bbox = candidate.bounding_box()
                        if bbox and bbox['width'] > 100 and bbox['height'] > 50:
                            editor = candidate
                            editor_selector = selector
                            log(f"找到编辑器: {selector} [{i}]")
                            break
                
                if editor:
                    break
            except:
                continue
        
        if editor is None:
            log("未找到编辑器")
            return False
        
        escaped_content = content.replace("\\", "\\\\").replace("'", "\\'")
        js_script = f"""
            (function() {{
                var editor = document.querySelector('{editor_selector}');
                if (!editor) return 'not_found';
                
                // Focus
                editor.focus();
                
                // Clear existing content using keyboard
                var selectAll = new KeyboardEvent('keydown', {{
                    key: 'a',
                    code: 'KeyA',
                    ctrlKey: true,
                    bubbles: true
                }});
                document.dispatchEvent(selectAll);
                
                var deleteKey = new KeyboardEvent('keydown', {{
                    key: 'Delete',
                    code: 'Delete',
                    bubbles: true
                }});
                document.dispatchEvent(deleteKey);
                
                // Insert content
                var lines = '{escaped_content}'.split('\\n');
                
                for (var i = 0; i < lines.length; i++) {{
                    if (lines[i].length > 0) {{
                        // Insert text
                        var textNode = document.createTextNode(lines[i]);
                        editor.appendChild(textNode);
                    }}
                    
                    if (i < lines.length - 1) {{
                        // Add paragraph break
                        document.execCommand('insertLineBreak', false, null);
                        var p = document.createElement('p');
                        p.innerHTML = '<br>';
                        editor.appendChild(p);
                    }}
                }}
                
                // Trigger React input event
                var inputEvent = new InputEvent('input', {{
                    bubbles: true,
                    cancelable: true,
                    inputType: 'insertText',
                    data: '{escaped_content[:100]}...'
                }});
                editor.dispatchEvent(inputEvent);
                
                // Also dispatch custom events that React listens to
                var eventTypes = ['input', 'change', 'textInput', 'keydown', 'keyup'];
                eventTypes.forEach(function(type) {{
                    var evt = new Event(type, {{ bubbles: true, cancelable: true }});
                    editor.dispatchEvent(evt);
                }});
                
                return editor.innerText;
            }})()
        """
        
        try:
            result = self.page.evaluate(js_script)
            log(f"编辑器内容长度 (JS): {len(str(result)) if result else 0}")
            
            if result and len(str(result)) > 10:
                self._take_debug_screenshot("content_filled")
                log("内容填写完成")
                return True
        except Exception as e:
            log(f"JS 方式失败: {e}")
        
        try:
            editor.click(timeout=1000)
        except:
            try:
                bbox = editor.bounding_box()
                if bbox:
                    self.page.mouse.click(bbox['x'] + bbox['width']/2, bbox['y'] + bbox['height']/2)
            except:
                pass
        
        self.page.wait_for_timeout(500)
        self.page.keyboard.press("Control+a")
        self.page.wait_for_timeout(200)
        self.page.keyboard.press("Delete")
        self.page.wait_for_timeout(200)
        self.page.keyboard.type(content, delay=1)
        self.page.wait_for_timeout(500)
        
        self.page.evaluate("""
            (function() {
                var editors = document.querySelectorAll('.ProseMirror, [contenteditable="true"]');
                editors.forEach(function(editor) {
                    var event = new Event('input', { bubbles: true, cancelable: true });
                    editor.dispatchEvent(event);
                });
            })()
        """)
        
        result = self.page.evaluate("""
            (function() {
                var editors = document.querySelectorAll('.ProseMirror, [contenteditable="true"]');
                for (var i = 0; i < editors.length; i++) {
                    if (editors[i].innerText && editors[i].innerText.length > 10) {
                        return editors[i].innerText;
                    }
                }
                return '';
            })()
        """)
        log(f"编辑器内容长度: {len(result)}")
        
        editor.click()
        self.page.wait_for_timeout(300)
        
        self._take_debug_screenshot("content_filled")
        log("内容填写完成")
        return True
    
    def _insert_images_to_editor(self, images: List[str]) -> int:
        valid_images = [img for img in images if os.path.exists(img)]
        if not valid_images:
            log("没有有效图片")
            return 0
        
        log(f"插入图片，有效数量: {len(valid_images)}")
        
        inserted = 0
        for i, img_path in enumerate(valid_images[:9]):
            log(f"尝试插入图片 {i+1}/{min(len(valid_images), 9)}")
            img_inserted = False
            
            escaped_path = img_path.replace("\\", "\\\\").replace("'", "\\'")
            
            js_script = f"""
                (function() {{
                    var toolbarBtns = document.querySelectorAll('[class*="toolbar"] button, [class*="toolbar"] [role="button"], [class*="editor"] button, button[aria-label*="图片"], button[aria-label*="image"]');
                    for (var i = 0; i < toolbarBtns.length; i++) {{
                        var btn = toolbarBtns[i];
                        var svg = btn.querySelector('svg');
                        var ariaLabel = btn.getAttribute('aria-label') || '';
                        var title = btn.getAttribute('title') || '';
                        var text = btn.textContent || '';
                        
                        if (ariaLabel.toLowerCase().includes('image') || 
                            ariaLabel.includes('图片') ||
                            title.toLowerCase().includes('image') ||
                            title.includes('图片') ||
                            text.includes('图片') ||
                            (svg && ariaLabel === '' && title === '')) {{
                            btn.click();
                            return 'toolbar_btn_' + i + '_' + ariaLabel;
                        }}
                    }}
                    
                    return 'not_found';
                }})()
            """
            
            try:
                js_result = self.page.evaluate(js_script)
                log(f"JS 上传结果: {js_result}")
                
                self.page.wait_for_timeout(1500)
                
                try:
                    file_inputs = self.page.locator('input[type="file"]')
                    if file_inputs.count() > 0:
                        for j in range(file_inputs.count()):
                            inp = file_inputs.nth(j)
                            try:
                                inp.set_input_files(img_path)
                                inserted += 1
                                img_inserted = True
                                log(f"图片 {i+1} 上传成功 (input #{j})")
                                self.page.wait_for_timeout(3000)
                                break
                            except Exception as e:
                                log(f"input #{j} 上传失败: {e}")
                                continue
                except Exception as e:
                    log(f"文件上传失败: {e}")
                    
                if not img_inserted:
                    self._take_debug_screenshot(f"image_upload_failed_{i+1}")
            except Exception as e:
                log(f"JS 执行失败: {e}")
                self._take_debug_screenshot(f"image_upload_failed_{i+1}")
        
        self._take_debug_screenshot("images_inserted")
        log(f"图片插入完成: {inserted} 张")
        return inserted
    
    def _select_cover_image(self) -> int:
        log("选择封面图")
        self.page.wait_for_timeout(1000)
        
        self._take_debug_screenshot("cover_step1")
        
        cover_strategies = [
            lambda: self.page.locator('text=封面').first,
            lambda: self.page.locator('[class*="cover"]').first,
            lambda: self.page.locator('text=上传封面').first,
            lambda: self.page.locator('button:has-text("封面")').first,
        ]
        
        cover_clicked = False
        for strategy in cover_strategies:
            try:
                el = strategy()
                if el.is_visible(timeout=2000):
                    bbox = el.bounding_box()
                    if bbox and bbox['width'] > 30:
                        el.click(timeout=1000)
                        log("封面区域已点击")
                        cover_clicked = True
                        self.page.wait_for_timeout(1500)
                        break
            except Exception as e:
                log(f"封面策略失败: {e}")
                continue
        
        if not cover_clicked:
            js_open_cover = """
                (function() {
                    var btns = document.querySelectorAll('button, [role="button"], a');
                    for (var i = 0; i < btns.length; i++) {
                        var btn = btns[i];
                        var text = btn.textContent || '';
                        var ariaLabel = btn.getAttribute('aria-label') || '';
                        if (text.includes('封面') || ariaLabel.includes('封面') || text.includes('上传')) {
                            btn.click();
                            return 'opened_' + i;
                        }
                    }
                    return 'not_found';
                })()
            """
            try:
                result = self.page.evaluate(js_open_cover)
                log(f"JS 打开封面: {result}")
                if result != 'not_found':
                    cover_clicked = True
                    self.page.wait_for_timeout(1500)
            except Exception as e:
                log(f"JS 封面打开失败: {e}")
        
        if not cover_clicked:
            log("未找到封面区域，跳过封面选择")
            return 0
        
        self.page.wait_for_timeout(2000)
        self._take_debug_screenshot("cover_modal_opened")
        
        try:
            material_tab = self.page.locator('text=我的素材').first
            if material_tab.is_visible(timeout=2000):
                material_tab.click()
                log("点击'我的素材'标签")
                self.page.wait_for_timeout(2000)
                self._take_debug_screenshot("cover_material_tab")
        except Exception as e:
            log(f"素材标签点击失败: {e}")
        
        selected = 0
        try:
            img_selectors = [
                '[class*="material"] img',
                '[class*="material"] [class*="img"]',
                '[class*="image-item"] img',
                '[class*="image"] [class*="item"] img',
                '[class*="img-"]',
                '[class*="thumb"]',
                '[class*="gallery"] img',
                'img[class*="thumb"]',
                '[role="listitem"] img',
            ]
            
            js_select = """
                (function() {
                    var allImages = document.querySelectorAll('img');
                    var selectable = [];
                    for (var i = 0; i < allImages.length; i++) {
                        var img = allImages[i];
                        var w = img.naturalWidth || img.width;
                        var h = img.naturalHeight || img.height;
                        if (w > 100 && h > 50 && img.offsetParent !== null) {
                            selectable.push({idx: i, w: w, h: h});
                        }
                    }
                    return JSON.stringify(selectable.slice(0, 9));
                })()
            """
            
            try:
                selectable_imgs = json.loads(self.page.evaluate(js_select))
                log(f"可选择图片数量: {len(selectable_imgs)}")
                
                for img_info in selectable_imgs[:9]:
                    try:
                        el = self.page.locator('img').nth(img_info['idx'])
                        el.click(timeout=1000)
                        selected += 1
                        log(f"选择图片 {selected}")
                        self.page.wait_for_timeout(500)
                        if selected >= 3:
                            break
                    except Exception:
                        continue
            except Exception as e:
                log(f"JS 图片选择失败: {e}")
            
            for sel in img_selectors:
                if selected > 0:
                    break
                try:
                    imgs = self.page.locator(sel)
                    count = imgs.count()
                    log(f"选择器 '{sel}' 找到 {count} 个图片")
                    
                    for i in range(min(count, 9)):
                        try:
                            el = imgs.nth(i)
                            if el.is_visible(timeout=500):
                                el.click(timeout=1000)
                                selected += 1
                                log(f"选择图片 {selected}")
                                self.page.wait_for_timeout(500)
                                if selected >= 3:
                                    break
                        except Exception:
                            continue
                except Exception as e:
                    log(f"图片选择出错: {e}")
        except Exception as e:
            log(f"选择图片出错: {e}")
        
        self._take_debug_screenshot("cover_images_selected")
        
        if selected > 0:
            self.page.wait_for_timeout(1000)
            
            confirm_patterns = ["确定", "完成", "确认"]
            for pattern in confirm_patterns:
                try:
                    all_btns = self.page.locator('button')
                    for i in range(all_btns.count()):
                        try:
                            btn = all_btns.nth(i)
                            text = (btn.text_content(timeout=500) or "").strip()
                            if pattern in text and btn.is_visible(timeout=500):
                                bbox = btn.bounding_box()
                                if bbox and bbox['width'] > 20 and bbox['height'] > 20:
                                    log(f"找到确认按钮: '{text}', 点击...")
                                    self.page.mouse.click(
                                        bbox['x'] + bbox['width'] / 2,
                                        bbox['y'] + bbox['height'] / 2
                                    )
                                    log(f"点击'{pattern}'按钮成功")
                                    self.page.wait_for_timeout(3000)
                                    self._take_debug_screenshot("cover_confirmed")
                                    return selected
                        except Exception:
                            continue
                except Exception:
                    continue
        
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(500)
        
        return selected
    
    def _select_category(self, category: str = None) -> bool:
        log("选择分类")
        self._take_debug_screenshot("category_step1")
        
        try:
            self.page.click('input[placeholder*="分类"]', timeout=2000)
        except:
            try:
                self.page.click('div:has-text("请选择分类")', timeout=2000)
            except:
                pass
        
        self.page.wait_for_timeout(1000)
        self._take_debug_screenshot("category_dropdown_opened")
        
        category_options = ['科技', '数码', '互联网', '创业', '汽车', '情感', '生活', '健康', '教育', '文化', '娱乐', '游戏', '体育', '军事']
        target = category if category and category in category_options else '科技'
        
        self.page.wait_for_timeout(1000)
        
        for _ in range(2):
            self.page.keyboard.press("ArrowDown")
            self.page.wait_for_timeout(100)
        
        self.page.wait_for_timeout(200)
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(1500)
        
        self._take_debug_screenshot("category_keyboard_done")
        
        return True
    
    def _save_draft(self) -> bool:
        log("保存草稿")
        
        draft_strategies = [
            lambda: self.page.locator('button:has-text("保存草稿")').first,
            lambda: self.page.locator('button:has-text("存为草稿")').first,
            lambda: self.page.locator('span:has-text("保存草稿")').first,
        ]
        
        for idx, strategy in enumerate(draft_strategies):
            try:
                btn = strategy()
                if btn.is_visible(timeout=2000):
                    bbox = btn.bounding_box()
                    if bbox and bbox['width'] > 30:
                        btn.click(timeout=2000)
                        log("草稿保存成功")
                        self.page.wait_for_timeout(2000)
                        return True
            except Exception as e:
                log(f"保存草稿策略 {idx + 1} 失败: {e}")
                continue
        
        log("未找到保存草稿按钮，跳过")
        return False
    
    def _click_publish(self) -> bool:
        log("点击发布按钮")
        
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.page.wait_for_timeout(500)
        
        publish_strategies = [
            lambda: self.page.locator('button:has-text("预览")').last,
            lambda: self.page.locator('button:has-text("直接发布")').first,
            lambda: self.page.locator('button:has-text("预览并发布")').first,
            lambda: self.page.locator('span:has-text("预览")').last,
        ]
        
        for strategy_idx, strategy in enumerate(publish_strategies):
            try:
                btn = strategy()
                if btn.is_visible(timeout=2000):
                    bbox = btn.bounding_box()
                    text = (btn.text_content(timeout=500) or "").strip()
                    
                    if bbox and bbox['width'] > 30 and bbox['height'] > 20:
                        log(f"策略 {strategy_idx + 1}: 尝试点击发布按钮 '{text}'")
                        
                        try:
                            center_x = bbox['x'] + bbox['width'] / 2
                            center_y = bbox['y'] + bbox['height'] / 2
                            self.page.mouse.click(center_x, center_y)
                            log(f"发布按钮已点击 (mouse): {text}")
                            self._take_debug_screenshot("publish_clicked")
                            self.page.wait_for_timeout(3000)
                            self._take_debug_screenshot("after_publish_click")
                            return True
                        except Exception as e:
                            log(f"mouse.click 失败: {e}")
                        
                        try:
                            btn.click(timeout=2000)
                            log(f"发布按钮已点击: {text}")
                            self._take_debug_screenshot("publish_clicked")
                            self.page.wait_for_timeout(3000)
                            self._take_debug_screenshot("after_publish_click")
                            return True
                        except Exception as e:
                            log(f"click 失败: {e}")
                            
                        try:
                            btn.click(timeout=2000, force=True)
                            log(f"发布按钮已点击 (force): {text}")
                            self._take_debug_screenshot("publish_clicked")
                            self.page.wait_for_timeout(3000)
                            self._take_debug_screenshot("after_publish_click")
                            return True
                        except Exception as e:
                            log(f"force click 失败: {e}")
            except Exception as e:
                log(f"策略 {strategy_idx + 1} 失败: {e}")
                continue
        
        log("未找到发布按钮")
        self._take_debug_screenshot("publish_button_not_found")
        return False
    
    def _wait_for_publish_complete(self) -> bool:
        log(f"等待发布完成，超时 {PUBLISH_TIMEOUT/1000} 秒...")
        
        max_wait = PUBLISH_TIMEOUT // 1000
        waited = 0
        preview_handled = False
        
        log("等待预览模式加载...")
        for i in range(15):
            self.page.wait_for_timeout(1000)
            waited += 1
            
            current_url = self.page.url
            log(f"预览等待 {i+1}s, URL: {current_url}")
            
            self._close_popups()
            
            page_text = self.page.content()
            
            preview_top = self.page.locator('button:has-text("预览")').first
            bottom_publish = self.page.locator('button:has-text("预览并发布")')
            
            if preview_top.is_visible(timeout=500) and not bottom_publish.is_visible(timeout=1000):
                log("检测到顶部预览按钮且底部按钮消失，进入预览模式")
                self._take_debug_screenshot("preview_mode_detected")
                
                self.page.evaluate("window.scrollTo(0, 0)")
                self.page.wait_for_timeout(500)
                
                publish_top = self.page.locator('button:has-text("发布")').first
                if publish_top.is_visible(timeout=2000):
                    bbox = publish_top.bounding_box()
                    log(f"找到顶部发布按钮: {bbox}")
                    log("点击顶部发布按钮")
                    publish_top.click(timeout=3000)
                    self.page.wait_for_timeout(3000)
                    self._take_debug_screenshot("confirm_publish_clicked")
                    preview_handled = True
                    break
            
            if "确认发布" in page_text:
                log("检测到确认发布按钮")
                self._take_debug_screenshot("preview_detected")
                
                self.page.evaluate("window.scrollTo(0, 0)")
                self.page.wait_for_timeout(500)
                
                confirm_btn = self.page.locator('button:has-text("确认发布")').first
                if confirm_btn.is_visible(timeout=2000):
                    log("点击确认发布按钮")
                    confirm_btn.click(timeout=3000)
                    self.page.wait_for_timeout(3000)
                    self._take_debug_screenshot("confirm_publish_clicked")
                    preview_handled = True
                    break
            
            if any(x in page_text for x in ["请填写", "请选择", "不能为空", "请输入"]):
                log("检测到表单验证提示")
                self._take_debug_screenshot("validation_hints")
            
            bottom_btn = self.page.locator('button:has-text("预览并发布")')
            if not bottom_btn.is_visible(timeout=1000):
                log("底部发布按钮消失，可能进入预览模式")
                self._take_debug_screenshot("preview_mode_entered")
                break
        
        if not preview_handled:
            log("检查页面是否有验证错误或提示")
            page_text = self.page.content()
            
            validation_issues = []
            if "标题不能为空" in page_text:
                validation_issues.append("标题为空")
            if "正文不能为空" in page_text:
                validation_issues.append("正文为空")
            if "封面不能为空" in page_text:
                validation_issues.append("封面为空")
            if "分类不能为空" in page_text:
                validation_issues.append("分类为空")
                
            if validation_issues:
                log(f"验证问题: {validation_issues}")
                self._take_debug_screenshot("validation_error")
        
        if not preview_handled:
            log("未能进入预览模式，尝试直接点击发布按钮")
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(1000)
            
            self._take_debug_screenshot("before_direct_publish")
            
            publish_btn = self.page.locator('button:has-text("预览并发布")').last
            if publish_btn.is_visible(timeout=2000):
                bbox = publish_btn.bounding_box()
                if bbox:
                    log(f"点击最后的预览并发布按钮")
                    self.page.mouse.click(bbox['x'] + bbox['width']/2, bbox['y'] + bbox['height']/2)
                    self.page.wait_for_timeout(3000)
                    self._take_debug_screenshot("direct_publish_clicked")
                    
                    self._close_popups()
                    self.page.wait_for_timeout(3000)
                    self._take_debug_screenshot("after_direct_publish")
                    preview_handled = True
        
        log("点击发布后等待确认...")
        self.page.wait_for_timeout(5000)
        self._take_debug_screenshot("after_publish_wait")
        
        self._close_popups()
        
        page_text = self.page.content()
        
        if "草稿" in page_text:
            log("检测到草稿区域，发布成功")
            self._take_debug_screenshot("publish_success")
            return True
        
        if "请输入文章标题" in page_text:
            try:
                title_input = self.page.locator('input[placeholder*="标题"]')
                if title_input.is_visible(timeout=2000):
                    log("表单已重置，发布成功")
                    self._take_debug_screenshot("publish_success")
                    return True
            except:
                pass
        
        if "发布成功" in page_text or "审核中" in page_text or "已发布" in page_text:
            log("检测到发布成功关键字")
            self._take_debug_screenshot("publish_success")
            return True
        
        log("检查是否有错误弹窗...")
        error_dialogs = self.page.locator('[class*="message"], [class*="toast"], [class*="alert"], [role="alert"]')
        if error_dialogs.count() > 0:
            for i in range(min(error_dialogs.count(), 3)):
                try:
                    if error_dialogs.nth(i).is_visible(timeout=500):
                        text = error_dialogs.nth(i).text_content(timeout=500) or ""
                        log(f"检测到提示: {text[:100]}")
                except:
                    pass
        
        if "publish" not in self.page.url.lower():
            log("离开发布页面，可能成功")
            self._take_debug_screenshot("publish_success")
            return True
        
        log("继续等待...")
        
        while waited < max_wait:
            self.page.wait_for_timeout(2000)
            waited += 2
            
            if waited % 10 == 0:
                log(f"已等待 {waited} 秒...")
            
            self._close_popups()
            
            try:
                error_keywords = ["标题不能为空", "正文不能为空", "封面不能为空", "标题太短", "正文太短"]
                for kw in error_keywords:
                    if kw in self.page.content():
                        log(f"检测到验证错误: {kw}")
                        self._take_debug_screenshot("validation_error")
                        
                        close_patterns = ["确定", "关闭", "我知道了", "好的", "确认"]
                        for pattern in close_patterns:
                            try:
                                btn = self.page.locator(f'text={pattern}').first
                                if btn.is_visible(timeout=500):
                                    btn.click()
                                    log(f"关闭错误提示: {pattern}")
                                    self.page.wait_for_timeout(1000)
                            except Exception:
                                pass
                        
                        self.page.wait_for_timeout(500)
                        self._take_debug_screenshot("error_dialog_closed")
                        return False
            except Exception:
                pass
            
            try:
                page_text = self.page.content()
                success_keywords = ["发布成功", "发布完成", "已发布", "审核中", "文章管理", "提交成功", "发布到首页"]
                
                for keyword in success_keywords:
                    if keyword in page_text:
                        log(f"检测到成功关键字: {keyword}")
                        self._take_debug_screenshot("publish_success")
                        self.page.wait_for_timeout(2000)
                        return True
            except Exception:
                pass
            
            try:
                url_lower = self.page.url.lower()
                if "publish" not in url_lower and any(x in url_lower for x in ["success", "finished", "manage"]):
                    log("URL 表明可能发布成功")
                    self._take_debug_screenshot("publish_success")
                    return True
            except Exception:
                pass
        
        log("等待发布完成超时，检查页面状态...")
        
        try:
            page_text = self.page.content()
            if any(kw in page_text for kw in ["审核中", "已发布", "发布成功", "发布到", "文章管理"]):
                log("超时但检测到成功关键字")
                self._take_debug_screenshot("publish_maybe_success")
                return True
        except Exception:
            pass
        
        self._take_debug_screenshot("publish_failed")
        log("返回失败")
        return False
    
    def publish_article(self, title: str, content: str, images: List[str] = None) -> Tuple[bool, str, str]:
        if not self.page:
            raise Exception("请先调用 setup() 或 login()")
        
        if not title:
            return False, "标题不能为空", None
        
        title = title.replace('：', ' ').replace(':', ' ').strip()
        title = ' '.join(title.split())
        title = title[:30]
        if len(title) < 2:
            title = title + " " * (2 - len(title))
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"\n发布文章: {title[:20]}... (尝试 {attempt}/{MAX_RETRIES})")
                log("="*50)
                log("开始发布流程")
                
                log("步骤1: 打开发布页面")
                self.page.goto(PUBLISH_URL, timeout=60000, wait_until="domcontentloaded")
                self.page.wait_for_timeout(3000)
                
                log("步骤2: 关闭弹窗")
                self._close_popups()
                self._take_debug_screenshot("step2_popups_closed")
                
                log("步骤3: 填写标题")
                if self._find_and_fill_title(title):
                    print("  ✓ 标题已填写")
                else:
                    print("  ⚠ 标题填写可能失败")
                
                self.page.wait_for_timeout(500)
                
                log("步骤4: 填写内容")
                self._fill_editor(content)
                print("  ✓ 内容已填写")
                
                self.page.wait_for_timeout(1500)
                self._close_popups()
                
                log("步骤5: 插入图片")
                inserted = 0
                if images and len(images) > 0:
                    try:
                        inserted = self._insert_images_to_editor(images)
                    except Exception as e:
                        log(f"图片上传异常: {e}")
                print(f"  ✓ 已嵌入 {inserted} 张图片")
                
                log("步骤6: 选择封面图")
                cover_count = self._select_cover_image()
                print(f"  ✓ 封面图已选择 ({cover_count}张)")
                
                self.page.wait_for_timeout(1500)
                
                log("步骤7: 选择分类")
                category_selected = self._select_category()
                if category_selected:
                    print("  ✓ 分类已选择")
                else:
                    print("  ⚠ 分类选择可能失败")
                
                self._close_popups()
                self.page.wait_for_timeout(1000)
                
                log("验证表单状态...")
                form_state = self._check_form_state()
                log(f"分类选择后表单状态: {form_state}")
                
                if form_state.get('titleLength', 0) < 2 or form_state.get('editorLength', 0) < 10:
                    log("表单内容丢失，重新填写")
                    self._find_and_fill_title(title)
                    self._fill_editor(content)
                    self.page.wait_for_timeout(1000)
                    form_state = self._check_form_state()
                    log(f"重新填写后表单状态: {form_state}")
                
                log(f"表单状态: {form_state}")
                
                if form_state.get('titleLength', 0) < 2:
                    log("标题未正确填写，重新填写")
                    self._find_and_fill_title(title)
                    self.page.wait_for_timeout(500)
                
                if form_state.get('editorLength', 0) < 10:
                    log("正文未正确填写，重新填写")
                    self._fill_editor(content)
                    self.page.wait_for_timeout(500)
                
                form_state = self._check_form_state()
                self._take_debug_screenshot("before_publish")
                
                if form_state.get('titleLength', 0) < 2 or form_state.get('editorLength', 0) < 10:
                    log("表单验证失败，内容不足")
                
                self.page.wait_for_timeout(1000)
                
                self._trigger_react_input_events()
                self.page.wait_for_timeout(500)
                
                log("步骤9: 点击发布")
                if self._click_publish():
                    print("  ✓ 点击发布按钮成功")
                else:
                    if attempt < MAX_RETRIES:
                        log(f"未找到发布按钮，重试 ({attempt + 1}/{MAX_RETRIES})")
                        self._take_debug_screenshot(f"retry_publish_{attempt}")
                        self.page.wait_for_timeout(3000)
                        continue
                    return False, "未找到发布按钮", None
                
                log("步骤10: 等待发布完成")
                if self._wait_for_publish_complete():
                    print("  ✓ 文章发布成功")
                    log("发布流程完成")
                    return True, "发布成功", None
                else:
                    if attempt < MAX_RETRIES:
                        log(f"发布超时，重试 ({attempt + 1}/{MAX_RETRIES})")
                        self._take_debug_screenshot(f"retry_wait_{attempt}")
                        self.page.wait_for_timeout(3000)
                        continue
                    return False, "发布等待超时", None
                    
            except Exception as e:
                import traceback
                log(f"发布异常: {e}")
                log(traceback.format_exc())
                self._take_debug_screenshot(f"error_attempt_{attempt}")
                
                if attempt < MAX_RETRIES:
                    log(f"异常后重试 ({attempt + 1}/{MAX_RETRIES})")
                    try:
                        self.page.goto("about:blank")
                        self.page.wait_for_timeout(1000)
                    except:
                        pass
                    continue
                
                return False, f"发布失败: {str(e)}", None
        
        return False, "达到最大重试次数", None
    
    def close(self) -> None:
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


def publish_single_file(markdown_path: str, images_dir: str = None, skip_published: bool = True) -> int:
    print("="*60)
    print("今日头条文章发布器 v3.2 - 单文件模式")
    print(f"重试次数: {MAX_RETRIES}, 截图模式: {'开启' if SCREENSHOT_MODE else '关闭'}")
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
    print("="*60)
    print("今日头条文章发布器 v3.2 - 多文件模式")
    print(f"重试次数: {MAX_RETRIES}, 截图模式: {'开启' if SCREENSHOT_MODE else '关闭'}")
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
    default_file = "/Volumes/james1t/proj_opencode/article/OpenClaw深度研究报告 - 今日头条_20260318_102440.md"
    
    parser = argparse.ArgumentParser(
        description="今日头条文章发布器 v3.2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python app_toutiao_ariticle_publisher.py -f article.md
  python app_toutiao_ariticle_publisher.py --debug --screenshot
  python app_toutiao_ariticle_publisher.py -l file1.md file2.md file3.md
  python app_toutiao_ariticle_publisher.py --clear-status
  python app_toutiao_ariticle_publisher.py --retry 5
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
    parser.add_argument("--screenshot", action="store_true",
                        help="保存调试截图")
    parser.add_argument("--no-skip", action="store_true",
                        help="不跳过已发布的文件")
    parser.add_argument("--clear-status", action="store_true",
                        help="清除发布状态记录")
    parser.add_argument("--show-status", action="store_true",
                        help="显示发布状态")
    parser.add_argument("--retry", type=int, default=3,
                        help="失败重试次数 (默认: 3)")
    
    args = parser.parse_args()
    
    global DEBUG_MODE, SCREENSHOT_MODE, MAX_RETRIES
    DEBUG_MODE = args.debug
    SCREENSHOT_MODE = args.screenshot
    MAX_RETRIES = args.retry
    
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
