#!/usr/bin/env python3
import os
import sys
import subprocess
import importlib.util

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_OUTPUT = "/Volumes/james1t/proj_opencode/video"
ARTICLE_OUTPUT = "/Volumes/james1t/proj_opencode/article"
PDF_PATH = "/Volumes/james1t/proj_feishu/收藏资源URL.pdf"


def load_module(path):
    spec = importlib.util.spec_from_file_location("pdf_extractor", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve_url(url):
    import requests
    try:
        resp = requests.head(url, allow_redirects=True, timeout=10)
        return resp.url
    except:
        return url


def download_video(url, output_path):
    python = sys.executable
    
    resolved = resolve_url(url)
    print(f"  -> resolved to: {resolved[:60]}...")
    
    if '/article/' in resolved or '/group/' in resolved or '/w/' in resolved:
        print(f"  -> actually an article page, trying article downloader instead")
        try:
            sys.path.insert(0, SCRIPT_DIR)
            from app_article_toutiao_article_downloader import download_article_from_toutiao
            return download_article_from_toutiao(resolved, output_path)[0]
        except Exception as e:
            print(f"  -> article fallback failed: {e}")
            return False
    
    cmd = [
        python, "-m", "yt_dlp",
        "-f", "bestvideo*+bestaudio/best",
        "--merge-output-format", "mp4",
        "-o", os.path.join(output_path, "%(title)s [%(id)s].%(ext)s"),
        "--no-update",
        "--no-warnings",
        "--extractor-retries", "3",
        resolved
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode != 0:
        print(f"  yt-dlp failed: {result.stderr[:200] if result.stderr else 'unknown error'}")
    
    return result.returncode == 0


def download_article(url, output_path):
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from app_article_toutiao_article_downloader import download_article_from_toutiao
        return download_article_from_toutiao(url, output_path)
    except Exception as e:
        print(f"Article download error: {e}")
        return False, None


def main():
    pdf_extractor = load_module(os.path.join(SCRIPT_DIR, "pdf_resource_extractor.py"))
    resources = pdf_extractor.extract_resources_from_pdf(PDF_PATH)
    
    videos = [r for r in resources if r['type'] == 'video']
    articles = [r for r in resources if r['type'] == 'article']
    
    print("=" * 60)
    print("Resource Processor")
    print("=" * 60)
    print(f"PDF: {PDF_PATH}")
    print(f"Total: {len(resources)} | Videos: {len(videos)} | Articles: {len(articles)}")
    print()
    
    os.makedirs(VIDEO_OUTPUT, exist_ok=True)
    os.makedirs(ARTICLE_OUTPUT, exist_ok=True)
    print(f"Video output: {VIDEO_OUTPUT}")
    print(f"Article output: {ARTICLE_OUTPUT}")
    print()
    
    print("-" * 60)
    print("Downloading videos...")
    print("-" * 60)
    for i, v in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}] {v['url'][:60]}...")
        success = download_video(v['url'], VIDEO_OUTPUT)
        print(f"  -> {'OK' if success else 'FAILED'}")
    
    print()
    print("-" * 60)
    print("Downloading articles...")
    print("-" * 60)
    for i, a in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {a['url'][:60]}...")
        success, _ = download_article(a['url'], ARTICLE_OUTPUT)
        print(f"  -> {'OK' if success else 'FAILED'}")
    
    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
