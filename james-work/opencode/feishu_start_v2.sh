#!/bin/bash
# 启动飞书机器人服务 (v2 - 使用 lark_oapi SDK)

# 安装依赖
echo "Installing dependencies..."
pip install -r feishu_requirements.txt

# 启动服务
echo "Starting Feishu Channel API v2..."
cd "$(dirname "$0")"
python api_opencode_feishu_v2.py
