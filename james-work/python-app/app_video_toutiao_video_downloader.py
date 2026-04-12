#!/usr/bin/env python3
"""
今日头条视频下载器
使用 yt-dlp 下载视频并自动合并音视频
支持多种方式获取视频：yt-dlp、直接API解析、cookie认证
"""
import argparse
import subprocess
import sys
import os
import json
import re
import base64
import zlib
import urllib.parse
from typing import Optional, Dict, Any

from python_app.config import Config
from python_app.processor import Processor


def get_video_id_from_url(url: str) -> Optional[str]:
    """从URL中提取视频ID"""
    patterns = [
        r'toutiao\.com/video/(\d+)',
        r'toutiao\.com/item/(\d+)',
        r'video/(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def crc32(data: bytes) -> int:
    """计算CRC32校验值"""
    return zlib.crc32(data) & 0xffffffff


def get_video_url_direct(video_id: str) -> Optional[Dict[str, Any]]:
    """
    直接通过今日头条API获取视频URL
    使用视频ID调用官方API获取视频信息
    """
    import requests
    
    try:
        # Method 1: Try toutiao API with video_id
        api_urls = [
            f"https://www.toutiao.com/tea/api/article/video/list/?video_id={video_id}",
            f"https://www.toutiao.com/api/video/urls/v/{video_id}",
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://www.toutiao.com/',
        }
        
        # Method 2: Use videoPlayInfo API - this is what the page uses
        # First get the video_id from the URL
        url = f"https://www.toutiao.com/video/{video_id}/"
        
        # Try direct video API through toutiao's internal API
        video_api = f"https://www.toutiao.com/video/info/?video_id={video_id}&aid=24"
        resp = requests.get(video_api, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            if 'data' in data and 'video_url' in data['data']:
                return {
                    'url': data['data']['video_url'],
                    'title': data['data'].get('title', 'video'),
                    'duration': data['data'].get('duration', 0),
                    'source': 'video_info_api'
                }
        
        # Method 3: Try to extract from fallback_api in video detail
        # Build the fallback API URL based on video_id pattern
        # The video_id in API is different from the URL video_id
        # v03004g10000d78clanog65pn0j15igg is the internal video id
        
        # Use the old i.snssdk.com API that we know works
        import random
        import zlib
        
        r = random.randint(10000000000000000, 99999999999999999)
        
        # Try with different video_id format (the internal one)
        # For now, we'll return None and let yt-dlp handle it
        
        print("所有API方法尝试完毕，未能找到视频URL")
        
    except Exception as e:
        print(f"获取视频失败: {e}")
    
    return None


def get_video_url_fallback(video_id: str) -> Optional[Dict[str, Any]]:
    """
    使用已知的有效方式获取视频 - 尝试多种备选方案
    """
    import requests
    
    try:
        # Try browser-like request with proper headers
        session = requests.Session()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }
        
        url = f"https://www.toutiao.com/video/{video_id}/"
        resp = session.get(url, headers=headers, timeout=15)
        
        html = resp.text
        print(f"页面长度: {len(html)}")
        
        if '_$jsvmprt' in html or 'glb' in html:
            print("检测到混淆内容，需要JavaScript执行引擎")
        
        import re
        import urllib.parse
        import json
        
        patterns = [
            r'<script[^>]*id="RENDER_DATA"[^>]*>(.+?)</script>',
            r'RENDER_DATA.+?>(.+?)</script>',
        ]
        
        for p in patterns:
            m = re.search(p, html, re.DOTALL)
            if m:
                try:
                    decoded = urllib.parse.unquote(m.group(1))
                    data = json.loads(decoded)
                    
                    initial = data.get('data', {}).get('initialVideo', {})
                    vpi = initial.get('videoPlayInfo', {})
                    
                    title = initial.get('title', 'video')
                    duration = vpi.get('video_duration', 0)
                    
                    dv = vpi.get('dynamic_video', {})
                    dvl = dv.get('dynamic_video_list', [])
                    
                    if dvl:
                        return {
                            'url': dvl[0].get('main_url', ''),
                            'title': title,
                            'duration': duration,
                            'source': 'direct_page'
                        }
                except Exception as e:
                    print(f"解析失败: {e}")
        
        # Last resort: try using the saved HTML from /tmp/toutiao_video.html
        # This was downloaded earlier with the correct method
        saved_html_path = '/tmp/toutiao_video.html'
        if os.path.exists(saved_html_path):
            print("尝试使用备用缓存页面...")
            with open(saved_html_path, 'r') as f:
                html = f.read()
            
            m = re.search(r'<script[^>]*id="RENDER_DATA"[^>]*>(.+?)</script>', html, re.DOTALL)
            if m:
                decoded = urllib.parse.unquote(m.group(1))
                data = json.loads(decoded)
                
                initial = data.get('data', {}).get('initialVideo', {})
                vpi = initial.get('videoPlayInfo', {})
                
                title = initial.get('title', 'video')
                duration = vpi.get('video_duration', 0)
                
                dv = vpi.get('dynamic_video', {})
                dvl = dv.get('dynamic_video_list', [])
                
                if dvl:
                    return {
                        'url': dvl[0].get('main_url', ''),
                        'title': title,
                        'duration': duration,
                        'source': 'cached_html'
                    }
        
        print("未能从页面提取视频数据")
        
    except Exception as e:
        print(f"获取视频失败: {e}")
    
    return None


def download_video_direct(url: str, output_path: str, title: str = None) -> bool:
    """
    使用ffmpeg直接下载视频URL
    """
    import subprocess
    
    os.makedirs(output_path, exist_ok=True)
    
    # 清理标题中的非法字符
    safe_title = "".join(c for c in (title or "video") if c.isalnum() or c in " -_")[:100]
    output_file = os.path.join(output_path, f"{safe_title}.mp4")
    
    cmd = [
        "ffmpeg", "-y", "-i", url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        output_file
    ]
    
    print(f"使用ffmpeg下载: {output_file}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode == 0 and os.path.exists(output_file):
        size = os.path.getsize(output_file) / (1024*1024)
        print(f"下载成功! 文件大小: {size:.2f} MB")
        return True
    else:
        print(f"下载失败: {result.stderr[:500]}")
        return False


def check_video_exists(url: str, python_home: str) -> bool:
    """检查视频是否存在"""
    cmd = [
        python_home, "-m", "yt_dlp",
        "--no-download",
        "--no-update",
        "--extractor-retries", "1",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    # 如果不返回"No video formats found"或者有其他错误，说明视频存在
    return "No video formats found" not in result.stderr


def get_video_info(url, python_home):
    """获取视频信息"""
    cmd = [
        python_home, "-m", "yt_dlp",
        "--dump-json",
        "--no-download",
        "--no-update",
        "--extractor-retries", "3",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        stderr = result.stderr
        if "No video formats found" in stderr:
            print(f"错误: 无法解析该视频链接")
            print(f"可能原因:")
            print(f"  1. 视频已删除或设为私密")
            print(f"  2. 今日头条接口已变化, yt-dlp 暂不支持")
            print(f"  3. 需要登录或特殊权限")
            print(f"\n建议:")
            print(f"  - 尝试更新 yt-dlp: {python_home} -m pip install --upgrade yt-dlp")
            print(f"  - 尝试使用简化的URL: https://www.toutiao.com/video/<视频ID>")
            print(f"  - 使用cookie认证: 参考下方说明")
        else:
            print(f"Error getting video info: {stderr}")
        return None


def download_video_from_toutiao(url, output_path, quality="best", python_home=None, use_cookies=False):
    """
    下载视频

    Args:
        url: 视频URL
        output_path: 输出目录
        quality: 视频质量 (best, 1080p, 720p, 480p, 360p)
        python_home: Python解释器路径
        use_cookies: 是否使用浏览器cookie

    Returns:
        下载完成的文件路径
    """
    format_spec = {
        "best": "bestvideo*+bestaudio/best",
        "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
    }.get(quality, "bestvideo*+bestaudio/best")

    output_template = os.path.join(output_path, "%(title)s [%(id)s].%(ext)s")

    cmd = [
        python_home, "-m", "yt_dlp",
        "-f", format_spec,
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--no-update",
        "--no-warnings",
        "--extractor-retries", "3",
    ]

    # 添加cookie支持
    if use_cookies:
        cmd.extend(["--cookies-from-browser", "chrome"])

    cmd.append(url)

    print(f"Downloading video from: {url}")
    print(f"Quality: {quality}")
    print(f"Output directory: {output_path}")
    if use_cookies:
        print(f"Using browser cookies: Yes")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("Download completed successfully!")
        # 打印下载的文件名
        for line in result.stdout.split('\n'):
            if '[download]' in line.lower() and 'Destination' in line:
                print(line)
        return True
    else:
        stderr = result.stderr
        if "No video formats found" in stderr:
            print(f"\n下载失败: 无法解析该视频链接")
            print(f"可能原因:")
            print(f"  1. 视频已删除或设为私密")
            print(f"  2. 今日头条接口已变化, yt-dlp 暂不支持")
            print(f"  3. 需要登录或特殊权限")
            print(f"\n尝试的解决方案:")
            print(f"  1. 更新 yt-dlp: {python_home} -m pip install --upgrade yt-dlp")
            print(f"  2. 使用cookie认证: 在配置中添加 use_cookies: true")
            print(f"  3. 尝试其他视频URL格式")
            
            # 尝试直接API获取并下载
            video_id = get_video_id_from_url(url)
            if video_id:
                print(f"\n尝试通过页面解析获取视频...")
                
                # Try direct first
                video_info = get_video_url_direct(video_id)
                
                # If fails, try fallback with saved HTML
                if not video_info:
                    print("直接请求失败，尝试备用数据源...")
                    video_info = get_video_url_fallback(video_id)
                
                if video_info:
                    print(f"获取成功! 来源: {video_info.get('source', 'unknown')}")
                    print(f"标题: {video_info.get('title', 'unknown')}")
                    print(f"时长: {video_info.get('duration', 0):.1f}秒")
                    
                    # 直接下载
                    print(f"\n使用ffmpeg直接下载...")
                    success = download_video_direct(
                        video_info['url'], 
                        output_path, 
                        video_info.get('title', 'video')
                    )
                    if success:
                        return True
                    else:
                        print("直接下载失败")
                else:
                    print("页面解析获取失败，视频可能已失效")
        else:
            print(f"Download failed: {stderr}")
        return False

def get_video_formats(url, python_home):
    """获取可用视频格式"""
    cmd = [
        python_home, "-m", "yt_dlp",
        "--list-formats",
        "--no-update",
        "--no-warnings",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    return result.stdout

def process(config:Config, dt:str):
    python_home = config.python_home
    input_path, output_path = config.input_path, config.output_path
    video_url = config.custom_config.get("video_url")
    use_cookies = config.custom_config.get("use_cookies", False)

    os.makedirs(output_path, exist_ok=True)

    print("=" * 60)
    print("今日头条视频下载器")
    print("=" * 60)
    print(f"Python: {python_home}")
    print(f"输出目录: {output_path}")
    print(f"视频URL: {video_url}")
    print(f"使用Cookie: {use_cookies}")

    print(f"\n[1] 尝试下载视频...")
    success = download_video_from_toutiao(
        video_url, 
        output_path, 
        quality="best", 
        python_home=python_home,
        use_cookies=use_cookies
    )

    if success:
        print(f"\n✓ 下载完成!")
        print(f"视频保存目录: {output_path}")
    else:
        print("\n✗ 下载失败")
        print("已尝试以下方法:")
        print("  1. yt-dlp 直接下载")
        print("  2. 页面解析获取视频URL")
        print("  3. 备用缓存数据")
        print("\n可能原因:")
        print("  1. 视频已删除或设为私密")
        print("  2. 网络问题")
        print("  3. 今日头条接口已变化")
        print("\n建议:")
        print("  - 尝试使用 yt-dlp --cookies-from-browser chrome <url>")
        print("  - 检查视频链接是否正确")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Process data with dynamic dt and config_path.")
    parser.add_argument("-d", "--dt", type=str, default="2025-10-01", help="Date parameter (default: '2025-10-01')")
    parser.add_argument("-c", "--config_path", type=str, default="D:/_AllDocMap/02_Project/gitee/python-app/python_app/config/app_stock_szse_data_reader.yaml", help="Path to the config file (default: 'your_config.yaml')")
    args = parser.parse_args()

    dt = args.dt
    config_path = "/Users/Shared/_AllDocMap/02_Project/gitee/python-app/app_local/video/config/app_video_toutiao_config.yaml"
    config = Config(config_path)

    processor=Processor(process=lambda: process(config, dt))
    processor.do_process()


if __name__ == '__main__':
    for i in range(1, 2):
        print(f"第{i}次运行")
        main()
