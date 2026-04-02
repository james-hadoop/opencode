#!/usr/bin/env python3
"""
今日头条视频下载器
使用 yt-dlp 下载视频并自动合并音视频
"""
import subprocess
import sys
import os
import json
import urllib.parse

VIDEO_URL = "https://www.toutiao.com/video/7585002732298174986/?app=news_article&category_new=__all__&module_name=Android_tt_others&share_did=MS4wLjACAAAAi_3K-Bdl8FxAtlKsQg3ZUlNX5x0E-d6L-7jrTpSdNG8&share_token=67ad0d00-81c6-43a8-8b8a-8a3c4ad65d60&share_uid=MS4wLjABAAAAKW63wJ9i-ORmR-N82xWxGChfXj21ZgMfuUztQ7WSN9MaNMYGLBiSm-2vWLjgi_b0&timestamp=1773557865&tt_from=sys_share&upstream_biz=Android_others&utm_campaign=client_share&utm_medium=toutiao_android&utm_source=sys_share&source=m_redirect"
OUTPUT_DIR = "/Volumes/james1t/proj_opencode/video/"
PYTHON_BIN = "/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_video_info(url):
    """获取视频信息"""
    cmd = [
        PYTHON_BIN, "-m", "yt_dlp",
        "--dump-json",
        "--no-download",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        print(f"Error getting video info: {result.stderr}")
        return None

def download_video(url, output_dir, quality="best"):
    """
    下载视频
    
    Args:
        url: 视频URL
        output_dir: 输出目录
        quality: 视频质量 (best, 1080p, 720p, 480p, 360p)
    
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
    
    output_template = os.path.join(output_dir, "%(title)s [%(id)s].%(ext)s")
    
    cmd = [
        PYTHON_BIN, "-m", "yt_dlp",
        "-f", format_spec,
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--no-update",
        url
    ]
    
    print(f"Downloading video from: {url}")
    print(f"Quality: {quality}")
    print(f"Output directory: {output_dir}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("Download completed successfully!")
        print(result.stdout)
        return True
    else:
        print(f"Download failed: {result.stderr}")
        return False

def get_video_formats(url):
    """获取可用视频格式"""
    cmd = [
        PYTHON_BIN, "-m", "yt_dlp",
        "--list-formats",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    return result.stdout

if __name__ == "__main__":
    print("=" * 60)
    print("今日头条视频下载器")
    print("=" * 60)
    
    print(f"\n[1] 获取视频信息...")
    video_info = get_video_info(VIDEO_URL)
    
    if video_info:
        print(f"\n视频标题: {video_info.get('title', 'N/A')}")
        print(f"视频ID: {video_info.get('id', 'N/A')}")
        print(f"时长: {video_info.get('duration_string', 'N/A')}")
        print(f"上传者: {video_info.get('uploader', 'N/A')}")
        print(f"播放量: {video_info.get('view_count', 'N/A')}")
        
        print(f"\n[2] 查看可用格式...")
        get_video_formats(VIDEO_URL)
        
        print(f"\n[3] 开始下载 (最高质量)...")
        success = download_video(VIDEO_URL, OUTPUT_DIR, quality="best")
        
        if success:
            print(f"\n下载完成!")
            print(f"视频保存目录: {OUTPUT_DIR}")
    else:
        print("获取视频信息失败!")
        sys.exit(1)
