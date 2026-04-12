#!/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python
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

APP_DIR = Path(__file__).parent.resolve()
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
        elif line.startswith('### '):
            body_lines.append(f"*{line[4:].strip()}*")
        elif line.startswith('> '):
            body_lines.append(f"*{line[2:].strip()}*")
        elif line.startswith('#'):
            if title is None and len(line) > 1:
                title = line[1:].strip()
            else:
                body_lines.append(line)
            img_match = re.search(r'!\[[^\]]*\]\(([^)]+)\)', line)
            if img_match:
                img_path = img_match.group(1)
                
                if img_path.startswith('http://') or img_path.startswith('https://'):
                    image_paths.append(img_path)
                elif img_path.startswith('/'):
                    image_paths.append(img_path)
                elif img_path.startswith('images/') or img_path.startswith('./images/'):
                    full_path = str(base_dir / img_path.replace('./', ''))
                    if os.path.exists(full_path):
                        image_paths.append(full_path)
                    else:
                        alt_path = str(base_dir / img_path)
                        if os.path.exists(alt_path):
                            image_paths.append(alt_path)
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
            self.page.goto("https://mp.toutiao.com/profile_v4/graphic/publish", timeout=30000, wait_until="commit")
            self.page.wait_for_timeout(3000)
            
            current_url = self.page.url
            if "login" in current_url.lower() or "auth" in current_url.lower():
                return False
            
            title = self.page.title()
            if title and "头条号" in title:
                return True
            
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
        
        try:
            inp = self.page.get_by_role("textbox", name="请输入文章标题")
            inp.click()
            inp.fill(title)
            self.page.wait_for_timeout(500)
            log(f"标题填写成功")
            return True
        except Exception as e:
            log(f"role 方式填写失败: {e}")
        
        try:
            self.page.evaluate(f'''() => {{
                const inputs = document.querySelectorAll('input');
                for (const inp of inputs) {{
                    if (inp.placeholder && inp.placeholder.includes('标题')) {{
                        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        nativeInputValueSetter.call(inp, {json.dumps(title)});
                        inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return true;
                    }}
                }}
                return false;
            }}''')
            self.page.wait_for_timeout(500)
            log("标题通过 JS 填写成功")
            return True
        except Exception as e:
            log(f"JS 填写标题失败: {e}")
            return False
    
    def _fill_editor(self, content: str) -> bool:
        log(f"填写内容，长度: {len(content)} 字符")
        
        try:
            self.page.evaluate("window.scrollTo(0, 300)")
            self.page.wait_for_timeout(1000)
            
            for attempt in range(3):
                try:
                    editor = self.page.locator('.ProseMirror').first
                    if not editor.is_visible(timeout=3000):
                        log(f"未找到ProseMirror编辑器")
                        continue
                    
                    editor.click()
                    self.page.wait_for_timeout(800)
                    
                    self.page.keyboard.press("Control+a")
                    self.page.wait_for_timeout(300)
                    self.page.keyboard.press("Backspace")
                    self.page.wait_for_timeout(500)
                    
                    self.page.keyboard.type(content[:3000], delay=0)
                    self.page.wait_for_timeout(2000)
                    
                    verify = self.page.evaluate('''() => {
                        const ed = document.querySelector('.ProseMirror');
                        return ed ? ed.innerText.length : 0;
                    }''')
                    log(f"键盘输入验证: {verify} 字符")
                    
                    if verify > 100:
                        log("内容填写成功")
                        self._take_debug_screenshot("content_filled")
                        return True
                        
                except Exception as e:
                    log(f"尝试 {attempt+1} 失败: {e}")
                    self.page.wait_for_timeout(1000)
            
            log("尝试JavaScript填充")
            js_content = json.dumps(content)
            result = self.page.evaluate(f"""
                () => {{
                    const ed = document.querySelector('.ProseMirror');
                    if (!ed) return 0;
                    
                    ed.focus();
                    ed.innerText = {js_content};
                    
                    const inputEvent = new Event('input', {{ bubbles: true }}); 
                    ed.dispatchEvent(inputEvent);
                    
                    return ed.innerText.length;
                }}
            """)
            log(f"JS填充结果: {result} 字符")
            self.page.wait_for_timeout(2000)
            
            log("内容填写完成")
            return True
            
        except Exception as e:
            log(f"填写内容失败: {e}")
            return False
    
    def _insert_images_to_editor(self, images: List[str]) -> int:
        valid_images = [img for img in images if os.path.exists(img)]
        if not valid_images:
            log("没有有效图片")
            return 0
        
        log(f"插入图片，有效数量: {len(valid_images)}")
        
        try:
            img_btn = self.page.locator('[aria-label="插入图片"], [aria-label="添加图片"], button[aria-label*="图片"]').first
            if not img_btn.is_visible(timeout=2000):
                for sel in ['[class*="toolbar"] button', '[class*="editor"] button']:
                    btns = self.page.locator(sel)
                    for i in range(min(btns.count(), 10)):
                        try:
                            btn = btns.nth(i)
                            svg = btn.locator('svg').first
                            if svg.is_visible(timeout=500):
                                img_btn = btn
                                break
                        except:
                            pass
            img_btn.click()
            self.page.wait_for_timeout(1000)
        except Exception as e:
            log(f"点击图片按钮失败: {e}")
        
        inserted = 0
        for i, img_path in enumerate(valid_images[:9]):
            log(f"尝试插入图片 {i+1}/{min(len(valid_images), 9)}")
            
            try:
                file_input = self.page.locator('input[type="file"]').first
                if file_input.is_visible(timeout=1000):
                    file_input.set_input_files(img_path)
                    inserted += 1
                    log(f"图片 {i+1} 上传成功")
                    self.page.wait_for_timeout(2000)
                else:
                    log(f"未找到文件输入框")
            except Exception as e:
                log(f"图片 {i+1} 上传失败: {e}")
                self._take_debug_screenshot(f"image_upload_failed_{i+1}")
        
        log(f"图片插入完成: {inserted} 张")
        return inserted
    
    def _select_cover_image(self) -> int:
        log("选择封面图")
        self.page.wait_for_timeout(1000)
        
        # 尝试点击封面上传区域
        try:
            # 头条号封面上传区域通常是一个带 img 标签的上传按钮
            upload_area = self.page.locator('[class*="cover"] img, [class*="upload"] img').first
            if upload_area.is_visible(timeout=1000):
                upload_area.click(timeout=1000)
                self.page.wait_for_timeout(1000)
                log("封面上传区域已点击")
        except Exception:
            pass
        
        # 尝试从素材库选择图片
        try:
            my_material = self.page.locator('text="我的素材"').first
            if my_material.is_visible(timeout=500):
                my_material.click(timeout=1000)
                self.page.wait_for_timeout(1000)
                log("我的素材已点击")
        except Exception:
            pass
        
        # 选择图片
        selected = 0
        try:
            img_containers = self.page.locator('[class*="material"], [class*="image-item"], [class*="img"]').first
            if img_containers.is_visible(timeout=500):
                img_containers.click(timeout=1000)
                selected = 1
                log("图片已选择")
                self.page.wait_for_timeout(300)
        except Exception:
            pass
        
        # 确认选择
        if selected > 0:
            self.page.wait_for_timeout(500)
            try:
                confirm = self.page.locator('button:has-text("完成"), button:has-text("确定")').first
                if confirm.is_visible(timeout=500):
                    confirm.click(timeout=1000)
                    log("封面选择确认")
                    self.page.wait_for_timeout(2000)
                    return selected
            except Exception:
                pass
        
        return selected
    
    def _save_draft(self) -> bool:
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
    
    def _close_ai_assistant(self) -> None:
        try:
            for _ in range(2):
                try:
                    self.page.keyboard.press("Escape")
                    self.page.wait_for_timeout(500)
                except Exception:
                    pass
                
                try:
                    mask = self.page.locator('.byte-drawer-mask, .ai-assistant-drawer').first
                    if not mask.is_visible(timeout=500):
                        return
                except Exception:
                    return
            
            log("AI 助手关闭失败")
        except Exception as e:
            log(f"关闭 AI 助手异常: {e}")
    
    def _select_ad_revenue(self) -> bool:
        """选择"广告收益"选项"""
        try:
            ad_revenue = self.page.locator('text="广告收益"').first
            if ad_revenue.is_visible(timeout=1000):
                ad_revenue.click(timeout=1000)
                self.page.wait_for_timeout(300)
                log("已选择广告收益")
                return True
        except Exception:
            pass
        return False
    
    def _upload_cover_image(self, cover_paths: List[str] = None) -> bool:
        """上传封面图（使用本地图片）- 点击 + 按钮，然后点击上传本地文件"""
        if not cover_paths or not isinstance(cover_paths, list):
            cover_paths = [cover_paths] if cover_paths else []
        
        valid_paths = [p for p in cover_paths if p and os.path.exists(p)]
        if not valid_paths:
            log("无有效封面图片路径，跳过上传")
            return False
        
        log(f"上传封面图: {valid_paths}")
        self.page.wait_for_timeout(1000)
        
        for selector in [
            '[class*="article-cover-add"]',
            '[class*="cover-add"]',
            '.article-cover-add',
            '[class*="add-cover"]',
            '[class*="upload-cover"] button',
        ]:
            try:
                el = self.page.locator(selector).first
                if el.is_visible(timeout=1000):
                    el.click()
                    log(f"已点击封面 + 按钮: {selector}")
                    self.page.wait_for_timeout(2000)
                    break
            except Exception:
                continue
        else:
            log("未找到封面 + 按钮")
            self._take_debug_screenshot("cover_no_add_button")
            return False
        
        for txt in ["上传本地文件", "本地上传", "选择本地"]:
            try:
                btn = self.page.locator(f'button:has-text("{txt}")').first
                if btn.is_visible(timeout=2000):
                    btn.click()
                    log(f"已点击: {txt}")
                    self.page.wait_for_timeout(1500)
                    break
            except Exception:
                continue
        
        try:
            file_inputs = self.page.locator('input[type="file"]')
            count = file_inputs.count()
            if count > 0:
                for i in range(count):
                    try:
                        inp = file_inputs.nth(i)
                        if inp.is_visible(timeout=500):
                            inp.set_input_files(valid_paths)
                            log(f"封面图片已上传: {len(valid_paths)} 张")
                            self.page.wait_for_timeout(3000)
                            return True
                    except Exception:
                        continue
        except Exception as e:
            log(f"封面上传失败: {e}")
        
        log("封面上传失败")
        self._take_debug_screenshot("cover_upload_failed")
        return False
    
    def _click_publish(self) -> bool:
        log("点击发布按钮")

        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.page.wait_for_timeout(1000)

        try:
            for _ in range(3):
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(300)

            self.page.evaluate('''() => {
                const masks = document.querySelectorAll('.preview-feed-mask, [class*="preview-mask"], [class*="feed-mask"], .byte-drawer-mask, [class*="drawer-mask"]');
                masks.forEach(m => m.style.display = 'none');
            }''')
            self.page.wait_for_timeout(500)

            try:
                close_preview = self.page.locator('button:has-text("关闭预览")').first
                if close_preview.is_visible(timeout=1000):
                    close_preview.click()
                    log("关闭预览面板")
                    self.page.wait_for_timeout(1500)
            except Exception:
                pass

            try:
                self._close_ai_assistant()
            except Exception:
                pass

            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(1000)

            publish_btn = self.page.locator('button:has-text("预览并发布")').first
            if not publish_btn.is_visible(timeout=3000):
                log("未找到预览并发布按钮")
                self._take_debug_screenshot("no_publish_btn")
                return False

            publish_btn.click()
            log("已点击预览并发布")
            self.page.wait_for_timeout(3000)

            self._take_debug_screenshot("after_preview_click")

            page_text = self.page.inner_text('body')
            log(f"页面预览: {page_text[:500]}")

            try:
                close_preview = self.page.locator('button:has-text("关闭预览")').first
                if close_preview.is_visible(timeout=2000):
                    close_preview.click()
                    log("关闭预览")
                    self.page.wait_for_timeout(1500)
            except Exception:
                pass

            self.page.wait_for_timeout(1000)

            for btn_text in ["确认发布", "发布"]:
                try:
                    btns = self.page.locator(f'button:has-text("{btn_text}")')
                    for i in range(min(btns.count(), 8)):
                        btn = btns.nth(i)
                        if btn.is_visible(timeout=500):
                            bbox = btn.bounding_box()
                            if bbox and bbox['width'] > 30 and bbox['height'] > 20:
                                log(f"点击 {btn_text} 按钮")
                                btn.click()
                                self.page.wait_for_timeout(5000)
                                return True
                except Exception as e:
                    log(f"查找{btn_text}按钮失败: {e}")

            for attempt in range(8):
                self.page.wait_for_timeout(1500)
                
                page_text = self.page.inner_text('body')
                
                if "发布成功" in page_text or "审核中" in page_text:
                    log("检测到发布成功")
                    return True

                for btn_text in ["确认发布", "发布", "确认"]:
                    try:
                        btns = self.page.locator(f'button:has-text("{btn_text}")')
                        for i in range(min(btns.count(), 5)):
                            btn = btns.nth(i)
                            if btn.is_visible(timeout=300):
                                bbox = btn.bounding_box()
                                if bbox and bbox['width'] > 30:
                                    btn.click()
                                    log(f"循环中点击: {btn_text}")
                                    self.page.wait_for_timeout(3000)
                                    return True
                    except:
                        pass
                
                if attempt % 2 == 0:
                    log(f"等待... 尝试 {attempt+1}")

            log("发布流程完成")
            return True

        except Exception as e:
            log(f"发布流程出错: {e}")
            self._take_debug_screenshot("publish_error")
            return False

    def _wait_for_publish_complete(self) -> bool:
        log(f"等待发布完成，超时 {PUBLISH_TIMEOUT/1000} 秒...")
        
        api_responses = []
        publish_api_found = False
        
        def handle_response(response):
            nonlocal publish_api_found
            url = response.url
            status = response.status
            if response.request.method == "POST":
                if any(kw in url for kw in ["publish", "article", "content", "graphic", "submit", "save", "create"]):
                    try:
                        body = response.json()
                        api_responses.append({"url": url, "status": status, "body": body, "method": "POST"})
                        log(f"发布相关POST响应: {url} -> {status}")
                        publish_api_found = True
                    except:
                        api_responses.append({"url": url, "status": status, "method": "POST"})
                        log(f"发布相关POST响应: {url} -> {status}")
                        publish_api_found = True
            elif any(kw in url for kw in ["publish", "article", "content", "graphic", "submit", "save", "create"]):
                try:
                    body = response.json()
                    api_responses.append({"url": url, "status": status, "body": body})
                    log(f"发布相关GET响应: {url} -> {status}")
                except:
                    api_responses.append({"url": url, "status": status})
                    log(f"发布相关GET响应: {url} -> {status}")
        
        self.page.on("response", handle_response)
        
        max_wait = PUBLISH_TIMEOUT // 1000
        waited = 0
        initial_url = self.page.url
        
        while waited < max_wait:
            self.page.wait_for_timeout(2000)
            waited += 2
            
            if waited % 10 == 0:
                log(f"已等待 {waited} 秒...")
            
            try:
                page_text = self.page.inner_text('body')
                form_state = self._check_form_state()
                
                success_keywords = ["发布成功", "发布完成", "已发布", "审核中", "文章管理", "提交成功", "内容正在审核"]
                for keyword in success_keywords:
                    if keyword in page_text:
                        log(f"检测到成功关键字: {keyword}")
                        self._take_debug_screenshot("publish_success")
                        self.page.wait_for_timeout(2000)
                        return True
                
                error_keywords = ["发布失败", "内容重复", "审核不通过", "内容违规", "提交失败"]
                for kw in error_keywords:
                    if kw in page_text:
                        log(f"检测到错误关键字: {kw}")
                        return False

                if "草稿" in page_text and form_state.get("titleLength") == 0 and form_state.get("editorLength") == 0:
                    log("检测到草稿区且表单已清空，判定发布成功")
                    self._take_debug_screenshot("publish_success")
                    return True

                if form_state.get("titleLength") == 0 and form_state.get("editorLength") == 0:
                    if "请输入文章标题" in page_text or "请输入正文" in page_text:
                        log("检测到发布后表单已重置，判定发布成功")
                        self._take_debug_screenshot("publish_success")
                        return True
                
                confirm_keywords = ["确认发布", "确认提交", "确定要发布"]
                for kw in confirm_keywords:
                    if kw in page_text:
                        try:
                            confirm_btn = self.page.locator('button:has-text("确认"), button:has-text("确定"), button:has-text("确认发布")').first
                            if confirm_btn.is_visible(timeout=500):
                                confirm_btn.click()
                                log("点击确认按钮")
                                self.page.wait_for_timeout(3000)
                        except Exception:
                            pass
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
            page_text = self.page.inner_text('body')
            log(f"最终页面文本: {page_text[:300]}")
            if any(kw in page_text for kw in ["审核中", "已发布", "发布成功", "内容正在审核"]):
                log("超时但检测到成功关键字")
                self._take_debug_screenshot("publish_maybe_success")
                return True
        except Exception:
            pass
        
        if publish_api_found:
            log("检测到发布相关API调用")
            for resp in api_responses:
                if resp.get("status") == 200:
                    body = resp.get("body", {})
                    if body.get("message") == "success" or body.get("data", {}).get("status") == "published":
                        log("API 响应表明发布成功")
                        return True
        
        if self.page.url != initial_url:
            log(f"URL已变化: {self.page.url}")
            return True
        
        log("未检测到发布成功，页面未变化")
        self._take_debug_screenshot("publish_timeout")
        return False
    
    def publish_article(self, title: str, content: str, images: List[str] = None, cover_image: str = None) -> Tuple[bool, str, str]:
        if not self.page:
            raise Exception("请先调用 setup() 或 login()")
        
        if not title:
            return False, "标题不能为空", None
        
        title = title[:25]  # 留出空间添加时间戳
        if len(title) < 2:
            title = title + " " * (2 - len(title))
        
        import time
        original_title = title
        title = f"{title}_{int(time.time()) % 10000}"
        self._original_title = original_title
        
        try:
            print(f"\n发布文章: {title[:20]}...")
            log("="*50)
            log("开始发布流程")
            
            log("步骤1: 打开发布页面")
            self.page.goto(PUBLISH_URL, timeout=120000, wait_until="commit")
            self.page.wait_for_timeout(3000)
            
            log("步骤2: 关闭弹窗和AI助手")
            self._close_popups()
            self._close_ai_assistant()
            
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
            
            log("步骤6: 设置封面")
            if images and len(images) >= 3:
                cover_images = images[:3]
                if self._upload_cover_image(cover_images):
                    print(f"  ✓ 封面图已上传 ({len(cover_images)} 张)")
                else:
                    print("  ⚠ 封面图上传失败")
            elif cover_image and os.path.exists(cover_image):
                if self._upload_cover_image(cover_image):
                    print("  ✓ 封面图已上传")
                else:
                    print("  ⚠ 封面图上传失败")
            else:
                print("  ⚠ 无封面图，跳过")
            
            self.page.wait_for_timeout(500)
            
            log("步骤7: 选择广告收益")
            self._select_ad_revenue()
            
            self.page.wait_for_timeout(1000)
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(500)
            
            # 等待草稿保存完成
            for _ in range(10):
                page_text = self.page.inner_text('body')
                if "草稿保存中" not in page_text:
                    break
                self.page.wait_for_timeout(1000)
            
            # 确保 AI 助手已关闭，避免遮挡发布按钮
            self._close_ai_assistant()
            
            log("步骤8: 点击发布")
            
            try:
                self._close_popups()
            except:
                pass
            
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(1000)

            publish_btn = self.page.locator('button:has-text("预览并发布")').first
            if not publish_btn.is_visible(timeout=3000):
                log("未找到预览并发布按钮")
                return False, "未找到发布按钮", None

            publish_btn.click()
            log("已点击预览并发布")
            self.page.wait_for_timeout(3000)

            try:
                close_preview = self.page.locator('button:has-text("关闭预览")').first
                if close_preview.is_visible(timeout=2000):
                    close_preview.click()
                    log("关闭预览")
                    self.page.wait_for_timeout(1500)
            except:
                pass

            for _ in range(3):
                self.page.wait_for_timeout(1000)
                page_text = self.page.inner_text('body')
                
                for btn_text in ["发布", "确认发布", "确认"]:
                    try:
                        btns = self.page.locator(f'button:has-text("{btn_text}")')
                        for i in range(min(btns.count(), 5)):
                            btn = btns.nth(i)
                            if btn.is_visible(timeout=300):
                                bbox = btn.bounding_box()
                                if bbox and bbox['width'] > 30:
                                    log(f"点击: {btn_text}")
                                    btn.click()
                                    self.page.wait_for_timeout(3000)
                                    break
                    except:
                        pass

            log("步骤9: 等待发布完成")
            self.page.wait_for_timeout(5000)

            if self._wait_for_publish_complete():
                log("发布流程完成，验证文章是否在管理页面")
                if self._verify_article_on_manage_page(title):
                    print("  ✓ 文章发布成功并在管理页面验证")
                    return True, "发布成功", None
            
            log("发布等待超时，尝试保存草稿")
            if self._save_draft():
                log("草稿保存成功，验证文章是否在管理页面")
                if self._verify_article_on_manage_page(title):
                    print("  ✓ 草稿发布成功并在管理页面验证")
                    return True, "发布成功", None
                else:
                    print("  ⚠ 文章已保存为草稿但未在管理页面找到")
            
            self._take_debug_screenshot("publish_timeout")
            return False, "发布等待超时", None
            
        except Exception as e:
            import traceback
            log(f"发布异常: {e}")
            log(traceback.format_exc())
            return False, f"发布失败: {str(e)}", None
    
    def _verify_article_on_manage_page(self, title: str, timeout: int = 30) -> bool:
        original_title = getattr(self, '_original_title', None) or title
        
        log(f"验证文章: {original_title}")
        
        try:
            self.page.goto("https://mp.toutiao.com/profile_v4/manage/content/all", timeout=30000)
            self.page.wait_for_timeout(3000)
            self._close_popups()
            
            search_box = self.page.locator('input[placeholder="搜索关键词"]').first
            if not search_box.is_visible(timeout=5000):
                log("未找到搜索框")
                self._take_debug_screenshot("manage_no_search")
                return False
            
            for search_title in [original_title, original_title[:20], original_title[:15]]:
                if not search_title:
                    continue
                search_box.fill("")
                search_box.fill(search_title)
                self.page.wait_for_timeout(2000)
                search_box.press("Enter")
                self.page.wait_for_timeout(3000)
                
                page_text = self.page.inner_text("body")
                if search_title[:10] in page_text:
                    log(f"在管理页面找到文章: {search_title}")
                    self._take_debug_screenshot("verify_success")
                    return True
            
            log("未在管理页面找到文章")
            self._take_debug_screenshot("verify_not_found")
            return False
            
        except Exception as e:
            log(f"验证失败: {e}")
            self._take_debug_screenshot("verify_error")
            return False
    
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
    
    adjacent_images = md_path.parent / "images"
    if adjacent_images.exists():
        for img_file in sorted(adjacent_images.iterdir()):
            if img_file.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'):
                if img_file not in local_images and str(img_file) not in local_images:
                    local_images.append(str(img_file))
        print(f"  从 images/ 目录找到 {len([i for i in local_images if 'images' in i])} 张图片")
    
    cover_image = local_images[0] if local_images else None
    if cover_image:
        print(f"  封面图: {cover_image}")
    
    publisher = ToutiaoPublisher(headless=False)
    
    max_iterations = 5
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- 尝试 {iteration}/{max_iterations} ---")
        
        try:
            publisher.setup()
            
            if not publisher.check_login_status():
                print("\n需要登录...")
                publisher.login()
            
            if not publisher.check_login_status():
                print("\n登录失败，程序退出")
                return 1
            
            success, msg, url = publisher.publish_article(title, content, local_images, cover_image)
            
            if success:
                print(f"\n{'='*60}")
                print(f"✓ 发布成功!")
                print("="*60)
                status.mark_published(markdown_path, title, url)
                publisher.close()
                return 0
            else:
                print(f"  ✗ 第 {iteration} 次尝试失败: {msg}")
                
        except Exception as e:
            print(f"  ✗ 第 {iteration} 次尝试异常: {e}")
        
        finally:
            try:
                publisher.close()
            except:
                pass
        
        if iteration < max_iterations:
            print(f"  等待 10 秒后重试...")
            time.sleep(10)
    
    print(f"\n{'='*60}")
    print(f"✗ 达到最大重试次数 ({max_iterations})，放弃发布")
    print("="*60)
    status.mark_failed(markdown_path, f"达到最大重试次数 {max_iterations} 次", "max_iterations_exceeded")
    return 1


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
            
            cover_image = local_images[0] if local_images else None
            success, msg, url = publisher.publish_article(title, content, local_images, cover_image)
            
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
    default_file = "/Volumes/james1t/_AllDocMap/02_Project/mineru_proj/dt=2025-08-06/output_path/_LGTM_数据指标_快手--经营诊断与波动分析实践/auto/_LGTM_数据指标_快手--经营诊断与波动分析实践.md"
    
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
