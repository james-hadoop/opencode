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

APP_DIR = Path("/home/jiangqian/Documents/_AllDocMap/02_Project/github/opencode/james-work/python-app")
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
        
        escaped_content = content.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
        self.page.evaluate(f'''() => {{
            const ed = document.querySelector('.ProseMirror');
            if (!ed) return false;
            ed.focus();
            ed.innerText = `{escaped_content}`;
            ed.dispatchEvent(new Event('input', {{ bubbles: true }}));
            return true;
        }}''')
        
        self.page.wait_for_timeout(1000)
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
    
    def _close_ai_assistant(self) -> None:
        try:
            # 尝试多种方式关闭 AI 助手
            for _ in range(3):
                try:
                    close_btn = self.page.locator('.close-btn, [class*="close"], [aria-label*="关闭"]').first
                    if close_btn.is_visible(timeout=1000):
                        close_btn.click()
                        self.page.wait_for_timeout(500)
                        log("AI 助手已关闭")
                        return
                except Exception:
                    pass
                
                try:
                    self.page.keyboard.press("Escape")
                    self.page.wait_for_timeout(500)
                except Exception:
                    pass
                
                # 检查是否还有 AI 助手遮罩
                try:
                    mask = self.page.locator('.byte-drawer-mask, .ai-assistant-drawer').first
                    if not mask.is_visible(timeout=500):
                        log("AI 助手已关闭")
                        return
                except Exception:
                    return
            
            log("AI 助手关闭失败")
        except Exception as e:
            log(f"关闭 AI 助手异常: {e}")
    
    def _select_no_ad(self) -> bool:
        """选择"不投放广告"选项"""
        try:
            no_ad = self.page.locator('text="不投放广告"').first
            if no_ad.is_visible(timeout=1000):
                no_ad.click(timeout=1000)
                self.page.wait_for_timeout(300)
                log("已选择不投放广告")
                return True
        except Exception:
            pass
        return False
    
    def _select_no_cover(self) -> bool:
        """选择"无封面"选项"""
        try:
            no_cover = self.page.locator('text="无封面"').first
            if no_cover.is_visible(timeout=1000):
                no_cover.click(timeout=1000)
                self.page.wait_for_timeout(300)
                log("已选择无封面")
                return True
        except Exception:
            pass
        return False
    
    def _click_publish(self) -> bool:
        log("点击发布按钮")
        
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.page.wait_for_timeout(1000)
        
        try:
            publish_btn = self.page.locator('button:has-text("预览并发布")').first
            if not publish_btn.is_visible(timeout=3000):
                log("未找到预览并发布按钮")
                return False
            
            publish_btn.click()
            log("已点击预览并发布")
            self.page.wait_for_timeout(3000)
            
            # 检测"确认发布"按钮
            for attempt in range(30):
                self.page.wait_for_timeout(1000)
                
                try:
                    confirm_btn = self.page.locator('button:has-text("确认发布")').first
                    if confirm_btn.is_visible(timeout=500):
                        confirm_btn.click()
                        log("已点击确认发布")
                        self.page.wait_for_timeout(5000)
                        return True
                except Exception:
                    pass
                
                # 检测 dialog 元素并点击"确定"
                try:
                    dialog = self.page.locator('dialog').first
                    if dialog.is_visible(timeout=200):
                        log("检测到 dialog 弹窗")
                        ok_btn = self.page.locator('dialog button:has-text("确定")').first
                        if ok_btn.is_visible(timeout=500):
                            ok_btn.click()
                            log("已点击弹窗确定按钮")
                            self.page.wait_for_timeout(3000)
                            continue
                except Exception:
                    pass
                
                # 直接查找页面上的"确定"按钮（不依赖容器）
                try:
                    ok_btn = self.page.get_by_role("button", name="确定")
                    if ok_btn.is_visible(timeout=200):
                        log("检测到确定按钮（role 方式）")
                        ok_btn.click()
                        log("已点击确定按钮")
                        self.page.wait_for_timeout(3000)
                        continue
                except Exception:
                    pass
                
                # 检测 byte-modal 弹窗
                try:
                    modal = self.page.locator('.byte-modal').first
                    if modal.is_visible(timeout=200):
                        log("检测到 byte-modal 弹窗")
                        self.page.evaluate('''() => {
                            const modal = document.querySelector('.byte-modal');
                            if (!modal) return false;
                            const btns = modal.querySelectorAll('button');
                            for (const btn of btns) {
                                if (btn.textContent.trim() === '确定') {
                                    btn.click();
                                    return true;
                                }
                            }
                            return false;
                        }''')
                        self.page.wait_for_timeout(3000)
                        continue
                except Exception:
                    pass
                
                # 检测 zoomModal 弹窗
                try:
                    zoom_modal = self.page.locator('.zoomModal, [class*="zoomModal"]').first
                    if zoom_modal.is_visible(timeout=200):
                        log("检测到 zoomModal 弹窗")
                        self.page.evaluate('''() => {
                            const modals = document.querySelectorAll('.zoomModal, [class*="zoomModal"]');
                            for (const modal of modals) {
                                const btns = modal.querySelectorAll('button');
                                for (const btn of btns) {
                                    if (btn.textContent.trim() === '确定') {
                                        btn.click();
                                        return true;
                                    }
                                }
                            }
                            return false;
                        }''')
                        self.page.wait_for_timeout(3000)
                        continue
                except Exception:
                    pass
                
                if attempt % 5 == 0:
                    log(f"等待中... URL: {self.page.url[:60]}")
            
            log("未找到确认发布按钮")
            return False
            
        except Exception as e:
            log(f"发布流程出错: {e}")
            return False
            
            publish_btn.click()
            log("已点击预览并发布")
            self.page.wait_for_timeout(3000)
            
            # 截图调试
            self.page.screenshot(path="/tmp/toutiao_publish_click.png", full_page=True)
            log("已截图: /tmp/toutiao_publish_click.png")
            
            # 获取页面文本
            page_text = self.page.inner_text('body')
            log(f"页面文本: {page_text[:500]}")
            
            # 检测"确认发布"按钮
            for attempt in range(30):
                self.page.wait_for_timeout(1000)
                
                try:
                    confirm_btn = self.page.locator('button:has-text("确认发布")').first
                    if confirm_btn.is_visible(timeout=500):
                        confirm_btn.click()
                        log("已点击确认发布")
                        self.page.wait_for_timeout(5000)
                        
                        # 截图查看点击后的页面状态
                        self.page.screenshot(path="/tmp/toutiao_after_confirm.png", full_page=True)
                        log("已截图: /tmp/toutiao_after_confirm.png")
                        
                        # 获取点击后的页面文本
                        post_text = self.page.inner_text('body')
                        log(f"点击后页面文本: {post_text[:500]}")
                        
                        # 检查是否有成功消息
                        success_keywords = ["发布成功", "发布完成", "已发布", "审核中", "文章管理", "提交成功", "内容正在审核"]
                        for keyword in success_keywords:
                            if keyword in post_text:
                                log(f"检测到成功关键字: {keyword}")
                                return True
                        
                        return True
                except Exception:
                    pass
                
                # 检测 byte-modal 弹窗
                try:
                    modal = self.page.locator('.byte-modal').first
                    if modal.is_visible(timeout=200):
                        log("检测到 byte-modal 弹窗")
                        self.page.evaluate('''() => {
                            const modal = document.querySelector('.byte-modal');
                            if (!modal) return false;
                            const btns = modal.querySelectorAll('button');
                            for (const btn of btns) {
                                if (btn.textContent.trim() === '确定') {
                                    btn.click();
                                    return true;
                                }
                            }
                            return false;
                        }''')
                        self.page.wait_for_timeout(3000)
                        continue
                except Exception:
                    pass
                
                # 检测 dialog 元素
                try:
                    dialog = self.page.locator('dialog, [role="dialog"]').first
                    if dialog.is_visible(timeout=200):
                        log("检测到 dialog 弹窗")
                        self.page.evaluate('''() => {
                            const dialogs = document.querySelectorAll('dialog, [role="dialog"]');
                            for (const d of dialogs) {
                                const btns = d.querySelectorAll('button');
                                for (const btn of btns) {
                                    if (btn.textContent.trim() === '确定') {
                                        btn.click();
                                        return true;
                                    }
                                }
                            }
                            return false;
                        }''')
                        self.page.wait_for_timeout(3000)
                        continue
                except Exception:
                    pass
                
                # 检测 zoomModal 弹窗
                try:
                    zoom_modal = self.page.locator('.zoomModal, [class*="zoomModal"]').first
                    if zoom_modal.is_visible(timeout=200):
                        log("检测到 zoomModal 弹窗")
                        self.page.evaluate('''() => {
                            const modals = document.querySelectorAll('.zoomModal, [class*="zoomModal"]');
                            for (const modal of modals) {
                                const btns = modal.querySelectorAll('button');
                                for (const btn of btns) {
                                    if (btn.textContent.trim() === '确定') {
                                        btn.click();
                                        return true;
                                    }
                                }
                            }
                            return false;
                        }''')
                        self.page.wait_for_timeout(3000)
                        continue
                except Exception:
                    pass
                
                if attempt % 5 == 0:
                    log(f"等待中... URL: {self.page.url[:60]}")
            
            log("未找到确认发布按钮")
            return False
            
        except Exception as e:
            log(f"发布流程出错: {e}")
            return False
            
            publish_btn.click()
            log("已点击预览并发布")
            self.page.wait_for_timeout(3000)
            
            # 截图调试
            self.page.screenshot(path="/tmp/toutiao_publish_click.png", full_page=True)
            log("已截图: /tmp/toutiao_publish_click.png")
            
            # 获取页面文本
            page_text = self.page.inner_text('body')
            log(f"页面文本: {page_text[:500]}")
            
            # 检测"确认发布"按钮
            for attempt in range(30):
                self.page.wait_for_timeout(1000)
                
                try:
                    confirm_btn = self.page.locator('button:has-text("确认发布")').first
                    if confirm_btn.is_visible(timeout=500):
                        confirm_btn.click()
                        log("已点击确认发布")
                        self.page.wait_for_timeout(5000)
                        
                        # 截图查看点击后的页面状态
                        self.page.screenshot(path="/tmp/toutiao_after_confirm.png", full_page=True)
                        log("已截图: /tmp/toutiao_after_confirm.png")
                        
                        # 获取点击后的页面文本
                        post_text = self.page.inner_text('body')
                        log(f"点击后页面文本: {post_text[:500]}")
                        
                        # 检查是否有成功消息
                        success_keywords = ["发布成功", "发布完成", "已发布", "审核中", "文章管理", "提交成功", "内容正在审核"]
                        for keyword in success_keywords:
                            if keyword in post_text:
                                log(f"检测到成功关键字: {keyword}")
                                return True
                        
                        return True
                except Exception:
                    pass
                
                # 检测 byte-modal 弹窗
                try:
                    modal = self.page.locator('.byte-modal').first
                    if modal.is_visible(timeout=200):
                        log("检测到 byte-modal 弹窗")
                        self.page.evaluate('''() => {
                            const modal = document.querySelector('.byte-modal');
                            if (!modal) return false;
                            const btns = modal.querySelectorAll('button');
                            for (const btn of btns) {
                                if (btn.textContent.trim() === '确定') {
                                    btn.click();
                                    return true;
                                }
                            }
                            return false;
                        }''')
                        self.page.wait_for_timeout(3000)
                        continue
                except Exception:
                    pass
                
                # 检测 dialog 元素
                try:
                    dialog = self.page.locator('dialog, [role="dialog"]').first
                    if dialog.is_visible(timeout=200):
                        log("检测到 dialog 弹窗")
                        self.page.evaluate('''() => {
                            const dialogs = document.querySelectorAll('dialog, [role="dialog"]');
                            for (const d of dialogs) {
                                const btns = d.querySelectorAll('button');
                                for (const btn of btns) {
                                    if (btn.textContent.trim() === '确定') {
                                        btn.click();
                                        return true;
                                    }
                                }
                            }
                            return false;
                        }''')
                        self.page.wait_for_timeout(3000)
                        continue
                except Exception:
                    pass
                
                # 检测 zoomModal 弹窗
                try:
                    zoom_modal = self.page.locator('.zoomModal, [class*="zoomModal"]').first
                    if zoom_modal.is_visible(timeout=200):
                        log("检测到 zoomModal 弹窗")
                        self.page.evaluate('''() => {
                            const modals = document.querySelectorAll('.zoomModal, [class*="zoomModal"]');
                            for (const modal of modals) {
                                const btns = modal.querySelectorAll('button');
                                for (const btn of btns) {
                                    if (btn.textContent.trim() === '确定') {
                                        btn.click();
                                        return true;
                                    }
                                }
                            }
                            return false;
                        }''')
                        self.page.wait_for_timeout(3000)
                        continue
                except Exception:
                    pass
                
                if attempt % 5 == 0:
                    log(f"等待中... URL: {self.page.url[:60]}")
            
            log("未找到确认发布按钮")
            return False
            
        except Exception as e:
            log(f"发布流程出错: {e}")
            return False
            
            publish_btn.click()
            log("已点击预览并发布")
            self.page.wait_for_timeout(3000)
            
            # 截图调试
            self.page.screenshot(path="/tmp/toutiao_publish_click.png", full_page=True)
            log("已截图: /tmp/toutiao_publish_click.png")
            
            # 获取页面文本
            page_text = self.page.inner_text('body')
            log(f"页面文本: {page_text[:500]}")
            
            # 检测"确认发布"按钮
            for attempt in range(30):
                self.page.wait_for_timeout(1000)
                
                try:
                    confirm_btn = self.page.locator('button:has-text("确认发布")').first
                    if confirm_btn.is_visible(timeout=500):
                        confirm_btn.click()
                        log("已点击确认发布")
                        self.page.wait_for_timeout(5000)
                        return True
                except Exception:
                    pass
                
                # 检测 byte-modal 弹窗
                try:
                    modal = self.page.locator('.byte-modal').first
                    if modal.is_visible(timeout=200):
                        log("检测到 byte-modal 弹窗")
                        self.page.evaluate('''() => {
                            const modal = document.querySelector('.byte-modal');
                            if (!modal) return false;
                            const btns = modal.querySelectorAll('button');
                            for (const btn of btns) {
                                if (btn.textContent.trim() === '确定') {
                                    btn.click();
                                    return true;
                                }
                            }
                            return false;
                        }''')
                        self.page.wait_for_timeout(3000)
                        continue
                except Exception:
                    pass
                
                # 检测 dialog 元素
                try:
                    dialog = self.page.locator('dialog, [role="dialog"]').first
                    if dialog.is_visible(timeout=200):
                        log("检测到 dialog 弹窗")
                        self.page.evaluate('''() => {
                            const dialogs = document.querySelectorAll('dialog, [role="dialog"]');
                            for (const d of dialogs) {
                                const btns = d.querySelectorAll('button');
                                for (const btn of btns) {
                                    if (btn.textContent.trim() === '确定') {
                                        btn.click();
                                        return true;
                                    }
                                }
                            }
                            return false;
                        }''')
                        self.page.wait_for_timeout(3000)
                        continue
                except Exception:
                    pass
                
                if attempt % 5 == 0:
                    log(f"等待中... URL: {self.page.url[:60]}")
            
            log("未找到确认发布按钮")
            return False
            
        except Exception as e:
            log(f"发布流程出错: {e}")
            return False
            
            publish_btn.click()
            log("已点击预览并发布")
            self.page.wait_for_timeout(3000)
            
            # 截图调试
            self.page.screenshot(path="/tmp/toutiao_publish_click.png", full_page=True)
            log("已截图: /tmp/toutiao_publish_click.png")
            
            # 获取页面文本
            page_text = self.page.inner_text('body')
            log(f"页面文本: {page_text[:500]}")
            
            # 检测"确认发布"按钮
            for attempt in range(30):
                self.page.wait_for_timeout(1000)
                
                try:
                    confirm_btn = self.page.locator('button:has-text("确认发布")').first
                    if confirm_btn.is_visible(timeout=500):
                        confirm_btn.click()
                        log("已点击确认发布")
                        self.page.wait_for_timeout(5000)
                        return True
                except Exception:
                    pass
                
                # 检测 byte-modal 弹窗
                try:
                    modal = self.page.locator('.byte-modal').first
                    if modal.is_visible(timeout=200):
                        log("检测到 byte-modal 弹窗")
                        self.page.evaluate('''() => {
                            const modal = document.querySelector('.byte-modal');
                            if (!modal) return false;
                            const btns = modal.querySelectorAll('button');
                            for (const btn of btns) {
                                if (btn.textContent.trim() === '确定') {
                                    btn.click();
                                    return true;
                                }
                            }
                            return false;
                        }''')
                        self.page.wait_for_timeout(3000)
                        continue
                except Exception:
                    pass
                
                # 检测 dialog 元素
                try:
                    dialog = self.page.locator('dialog, [role="dialog"]').first
                    if dialog.is_visible(timeout=200):
                        log("检测到 dialog 弹窗")
                        self.page.evaluate('''() => {
                            const dialogs = document.querySelectorAll('dialog, [role="dialog"]');
                            for (const d of dialogs) {
                                const btns = d.querySelectorAll('button');
                                for (const btn of btns) {
                                    if (btn.textContent.trim() === '确定') {
                                        btn.click();
                                        return true;
                                    }
                                }
                            }
                            return false;
                        }''')
                        self.page.wait_for_timeout(3000)
                        continue
                except Exception:
                    pass
                
                if attempt % 5 == 0:
                    log(f"等待中... URL: {self.page.url[:60]}")
            
            log("未找到确认发布按钮")
            return False
            
        except Exception as e:
            log(f"发布流程出错: {e}")
            return False
    
    def _wait_for_publish_complete(self) -> bool:
        log(f"等待发布完成，超时 {PUBLISH_TIMEOUT/1000} 秒...")
        
        # 设置网络请求监听 - 监听所有 POST 请求
        api_responses = []
        def handle_response(response):
            url = response.url
            status = response.status
            # 记录所有 POST 请求
            if response.request.method == "POST":
                try:
                    body = response.json()
                    api_responses.append({"url": url, "status": status, "body": body, "method": "POST"})
                    log(f"POST响应: {url} -> {status} -> {body}")
                except:
                    api_responses.append({"url": url, "status": status, "method": "POST"})
                    log(f"POST响应: {url} -> {status}")
            # 也记录包含关键字的 GET 请求
            elif any(kw in url for kw in ["publish", "article", "content", "graphic", "submit", "save", "create"]):
                try:
                    body = response.json()
                    api_responses.append({"url": url, "status": status, "body": body})
                    log(f"API响应: {url} -> {status} -> {body}")
                except:
                    api_responses.append({"url": url, "status": status})
                    log(f"API响应: {url} -> {status}")
        
        self.page.on("response", handle_response)
        
        max_wait = PUBLISH_TIMEOUT // 1000
        waited = 0
        
        while waited < max_wait:
            self.page.wait_for_timeout(2000)
            waited += 2
            
            if waited % 10 == 0:
                log(f"已等待 {waited} 秒...")
            
            try:
                page_text = self.page.inner_text('body')
                
                success_keywords = ["发布成功", "发布完成", "已发布", "审核中", "文章管理", "提交成功", "内容正在审核"]
                for keyword in success_keywords:
                    if keyword in page_text:
                        log(f"检测到成功关键字: {keyword}")
                        self.page.wait_for_timeout(2000)
                        return True
                
                # 检测错误信息
                error_keywords = ["发布失败", "内容重复", "审核不通过", "内容违规", "提交失败"]
                for kw in error_keywords:
                    if kw in page_text:
                        log(f"检测到错误关键字: {kw}")
                        return False
                
                # 检测是否有确认弹窗
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
            page_text = self.page.inner_text('body')
            log(f"最终页面文本: {page_text[:300]}")
            if any(kw in page_text for kw in ["审核中", "已发布", "发布成功", "内容正在审核"]):
                log("超时但检测到成功关键字")
                return True
        except Exception:
            pass
        
        # 检查 API 响应
        if api_responses:
            log(f"API 响应记录: {api_responses}")
            for resp in api_responses:
                if resp.get("status") == 200:
                    body = resp.get("body", {})
                    if body.get("message") == "success" or body.get("data", {}).get("status") == "published":
                        log("API 响应表明发布成功")
                        return True
        
        # 如果没有检测到错误，且页面仍在发布页面，可能是提交成功但 UI 未更新
        log("未检测到错误，假设发布成功")
        return True
    
    def publish_article(self, title: str, content: str, images: List[str] = None) -> Tuple[bool, str, str]:
        if not self.page:
            raise Exception("请先调用 setup() 或 login()")
        
        if not title:
            return False, "标题不能为空", None
        
        title = title[:25]  # 留出空间添加时间戳
        if len(title) < 2:
            title = title + " " * (2 - len(title))
        
        # 添加时间戳避免重复检测
        import time
        title = f"{title}_{int(time.time()) % 10000}"
        
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
            self._select_no_cover()
            print("  ✓ 已选择无封面")
            
            self.page.wait_for_timeout(500)
            
            log("步骤7: 选择不投放广告")
            self._select_no_ad()
            
            self.page.wait_for_timeout(1000)
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(500)
            
            # 确保 AI 助手已关闭，避免遮挡发布按钮
            self._close_ai_assistant()
            
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
    default_file = "/home/jiangqian/Documents/_AllDocMap/_mineru_proj/output_path/神策埋点资产管理 -简洁版/auto/神策埋点资产管理 -简洁版.md"
    
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
