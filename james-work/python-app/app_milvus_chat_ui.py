#!/usr/bin/env python3

import json
import time
import uuid
import hashlib
from typing import Optional, Dict, Any, List
from threading import Thread

from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI(title="Milvus Chat Search", version="1.0.0")

TOKEN_STORE: Dict[str, Dict[str, Any]] = {}
VALID_CREDENTIALS = {"dev": "dEv#1234"}
TOKEN_EXPIRY_SECONDS = 24 * 60 * 60

MILVUS_CONFIG = {
    "host": "localhost",
    "port": "19530"
}

OLLAMA_CONFIG = {
    "base_url": "http://localhost:11434",
    "model": "qwen3.5:9b"
}


def generate_token(ak: str) -> str:
    raw_token = f"{ak}:{uuid.uuid4()}:{time.time()}"
    return hashlib.sha256(raw_token.encode()).hexdigest()


def verify_token(token: str) -> bool:
    if token not in TOKEN_STORE:
        return False
    token_info = TOKEN_STORE[token]
    if time.time() > token_info["expires_at"]:
        del TOKEN_STORE[token]
        return False
    return True


def get_ak_from_token(token: str) -> Optional[str]:
    if token in TOKEN_STORE:
        return TOKEN_STORE[token].get("ak")
    return None


class TokenRequest(BaseModel):
    ak: str
    sk: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    collection_name: str = "XiXiang_DiMian_2"
    top_k: int = 5
    text_field: Optional[str] = None
    vector_field: Optional[str] = None


async def verify_token_dependency(x_token: Optional[str] = Header(None)) -> str:
    if not x_token:
        raise HTTPException(status_code=401, detail="Missing token", headers={"X-Refresh-Token": "true"})
    if not verify_token(x_token):
        raise HTTPException(status_code=401, detail="Invalid or expired token", headers={"X-Refresh-Token": "true"})
    return x_token


HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Milvus 智能搜索助手</title>
    <style>
        :root {
            --tc-blue: #0091ea;
            --tc-cyan: #00c0e9;
            --tc-dark: #1a1a2e;
            --tc-light: #f5f7fa;
            --apple-bg: #ffffff;
            --apple-gray: #f2f2f7;
            --apple-dark: #1c1c1e;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.08);
            --shadow-md: 0 4px 16px rgba(0,0,0,0.12);
            --radius-lg: 20px;
            --radius-md: 12px;
            --radius-sm: 8px;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif;
        }

        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .app-container {
            width: 100%;
            max-width: 900px;
            height: 90vh;
            background: var(--apple-bg);
            border-radius: var(--radius-lg);
            box-shadow: 0 25px 80px rgba(0,0,0,0.25);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, var(--tc-blue) 0%, var(--tc-cyan) 100%);
            padding: 20px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo {
            width: 36px;
            height: 36px;
            background: rgba(255,255,255,0.2);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .logo svg {
            width: 22px;
            height: 22px;
            fill: white;
        }

        .header h1 {
            color: white;
            font-size: 18px;
            font-weight: 600;
            letter-spacing: -0.3px;
        }

        .header-right {
            display: flex;
            gap: 8px;
        }

        .header-btn {
            background: rgba(255,255,255,0.15);
            border: none;
            padding: 8px 14px;
            border-radius: 8px;
            color: white;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .header-btn:hover {
            background: rgba(255,255,255,0.25);
        }

        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            background: var(--apple-gray);
        }

        .message {
            display: flex;
            margin-bottom: 20px;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message.user {
            flex-direction: row-reverse;
        }

        .avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            margin: 0 12px;
        }

        .message.user .avatar {
            background: linear-gradient(135deg, var(--tc-blue), var(--tc-cyan));
        }

        .message.assistant .avatar {
            background: linear-gradient(135deg, #667eea, #764ba2);
        }

        .avatar svg {
            width: 18px;
            height: 18px;
            fill: white;
        }

        .message-content {
            max-width: 70%;
            padding: 14px 18px;
            border-radius: 18px;
            line-height: 1.5;
            font-size: 14px;
            position: relative;
        }

        .message.user .message-content {
            background: var(--tc-blue);
            color: white;
            border-bottom-right-radius: 4px;
        }

        .message.assistant .message-content {
            background: white;
            color: var(--apple-dark);
            border-bottom-left-radius: 4px;
            box-shadow: var(--shadow-sm);
        }

        .message.typing .message-content::after {
            content: '';
            display: inline-block;
            width: 6px;
            height: 6px;
            background: var(--tc-blue);
            border-radius: 50%;
            margin-left: 4px;
            animation: blink 1s infinite;
        }

        @keyframes blink {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 1; }
        }

        .welcome-message {
            text-align: center;
            padding: 60px 20px;
        }

        .welcome-icon {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, var(--tc-blue), var(--tc-cyan));
            border-radius: 24px;
            margin: 0 auto 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 12px 40px rgba(0,145,234,0.3);
        }

        .welcome-icon svg {
            width: 40px;
            height: 40px;
            fill: white;
        }

        .welcome-message h2 {
            font-size: 22px;
            color: var(--apple-dark);
            margin-bottom: 12px;
            font-weight: 600;
        }

        .welcome-message p {
            color: #8e8e93;
            font-size: 14px;
            max-width: 400px;
            margin: 0 auto;
            line-height: 1.6;
        }

        .input-container {
            padding: 20px 24px;
            background: white;
            border-top: 1px solid rgba(0,0,0,0.05);
        }

        .input-wrapper {
            display: flex;
            align-items: flex-end;
            background: var(--apple-gray);
            border-radius: 24px;
            padding: 12px 16px;
            gap: 12px;
        }

        .input-wrapper textarea {
            flex: 1;
            border: none;
            background: transparent;
            font-size: 15px;
            resize: none;
            outline: none;
            max-height: 120px;
            line-height: 1.5;
            color: var(--apple-dark);
        }

        .input-wrapper textarea::placeholder {
            color: #8e8e93;
        }

        .send-btn {
            width: 36px;
            height: 36px;
            border: none;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--tc-blue), var(--tc-cyan));
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            flex-shrink: 0;
        }

        .send-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 4px 16px rgba(0,145,234,0.4);
        }

        .send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .send-btn svg {
            width: 16px;
            height: 16px;
            fill: white;
        }

        .settings-panel {
            position: fixed;
            top: 0;
            right: -400px;
            width: 400px;
            height: 100%;
            background: white;
            box-shadow: -10px 0 40px rgba(0,0,0,0.15);
            transition: right 0.3s ease;
            z-index: 1000;
            display: flex;
            flex-direction: column;
        }

        .settings-panel.open {
            right: 0;
        }

        .settings-header {
            padding: 20px 24px;
            border-bottom: 1px solid rgba(0,0,0,0.08);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .settings-header h3 {
            font-size: 18px;
            color: var(--apple-dark);
        }

        .close-btn {
            background: none;
            border: none;
            font-size: 24px;
            color: #8e8e93;
            cursor: pointer;
            padding: 4px;
        }

        .settings-content {
            flex: 1;
            padding: 24px;
            overflow-y: auto;
        }

        .setting-group {
            margin-bottom: 24px;
        }

        .setting-group label {
            display: block;
            font-size: 13px;
            color: #8e8e93;
            margin-bottom: 8px;
            font-weight: 500;
        }

        .setting-group input, .setting-group select {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid rgba(0,0,0,0.1);
            border-radius: 10px;
            font-size: 14px;
            color: var(--apple-dark);
            background: var(--apple-gray);
            transition: all 0.2s;
        }

        .setting-group input:focus, .setting-group select:focus {
            outline: none;
            border-color: var(--tc-blue);
            box-shadow: 0 0 0 3px rgba(0,145,234,0.1);
        }

        .setting-row {
            display: flex;
            gap: 12px;
        }

        .setting-row .setting-group {
            flex: 1;
        }

        .settings-footer {
            padding: 20px 24px;
            border-top: 1px solid rgba(0,0,0,0.08);
        }

        .save-btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, var(--tc-blue), var(--tc-cyan));
            border: none;
            border-radius: 12px;
            color: white;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .save-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0,145,234,0.3);
        }

        .token-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 2000;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s;
        }

        .token-modal.show {
            opacity: 1;
            visibility: visible;
        }

        .token-modal-content {
            background: white;
            padding: 32px;
            border-radius: 20px;
            width: 90%;
            max-width: 400px;
            transform: scale(0.9);
            transition: transform 0.3s;
        }

        .token-modal.show .token-modal-content {
            transform: scale(1);
        }

        .token-modal h3 {
            font-size: 18px;
            color: var(--apple-dark);
            margin-bottom: 20px;
            text-align: center;
        }

        .token-modal input {
            width: 100%;
            padding: 14px 16px;
            border: 1px solid rgba(0,0,0,0.1);
            border-radius: 12px;
            font-size: 14px;
            margin-bottom: 12px;
        }

        .token-modal-btns {
            display: flex;
            gap: 12px;
            margin-top: 20px;
        }

        .token-modal-btns button {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .cancel-btn {
            background: var(--apple-gray);
            color: var(--apple-dark);
        }

        .login-btn {
            background: linear-gradient(135deg, var(--tc-blue), var(--tc-cyan));
            color: white;
        }

        .search-results {
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid rgba(0,0,0,0.08);
        }

        .search-result-item {
            background: rgba(0,145,234,0.05);
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 10px;
            font-size: 13px;
            color: var(--apple-dark);
            cursor: pointer;
            transition: all 0.2s;
        }

        .search-result-item:hover {
            background: rgba(0,145,234,0.1);
        }

        .search-result-item .score {
            font-size: 11px;
            color: #8e8e93;
            margin-top: 6px;
        }

        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #8e8e93;
        }

        .empty-state svg {
            width: 60px;
            height: 60px;
            fill: #d1d1d6;
            margin-bottom: 16px;
        }

        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 20px;
            background: rgba(255,255,255,0.15);
            color: white;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #34c759;
        }

        .status-dot.disconnected {
            background: #ff3b30;
        }
    </style>
</head>
<body>
    <div class="app-container">
        <div class="header">
            <div class="header-left">
                <div class="logo">
                    <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                </div>
                <h1>Milvus 智能搜索助手</h1>
            </div>
            <div class="header-right">
                <div class="status-indicator">
                    <span class="status-dot" id="statusDot"></span>
                    <span id="statusText">未连接</span>
                </div>
                <button class="header-btn" onclick="openSettings()">⚙️ 设置</button>
            </div>
        </div>

        <div class="chat-container" id="chatContainer">
            <div class="welcome-message" id="welcomeMessage">
                <div class="welcome-icon">
                    <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>
                </div>
                <h2>欢迎使用 Milvus 智能搜索</h2>
                <p>通过自然语言与您的向量数据库对话，快速检索相关信息</p>
            </div>
        </div>

        <div class="input-container">
            <div class="input-wrapper">
                <textarea id="messageInput" placeholder="输入您的问题..." rows="1"></textarea>
                <button class="send-btn" id="sendBtn" onclick="sendMessage()">
                    <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                </button>
            </div>
        </div>
    </div>

    <div class="settings-panel" id="settingsPanel">
        <div class="settings-header">
            <h3>⚙️ 连接设置</h3>
            <button class="close-btn" onclick="closeSettings()">×</button>
        </div>
        <div class="settings-content">
            <div class="setting-group">
                <label>Milvus 地址</label>
                <div class="setting-row">
                    <div class="setting-group">
                        <input type="text" id="milvusHost" placeholder="localhost" value="localhost">
                    </div>
                    <div class="setting-group">
                        <input type="text" id="milvusPort" placeholder="19530" value="19530">
                    </div>
                </div>
            </div>
            <div class="setting-group">
                <label>Collection 名称</label>
                <input type="text" id="collectionName" value="XiXiang_DiMian_2">
            </div>
            <div class="setting-group">
                <label>Ollama 地址</label>
                <input type="text" id="ollamaUrl" placeholder="http://localhost:11434" value="http://localhost:11434">
            </div>
            <div class="setting-group">
                <label>LLM 模型</label>
                <input type="text" id="ollamaModel" placeholder="qwen2.5:14b" value="qwen2.5:14b">
            </div>
            <div class="setting-group">
                <label>Top K</label>
                <input type="number" id="topK" value="5">
            </div>
            <div class="setting-group">
                <label>文本字段 (text_field)</label>
                <input type="text" id="textField" placeholder="如: content, description" value="content">
            </div>
            <div class="setting-group">
                <label>向量字段 (vector_field)</label>
                <input type="text" id="vectorField" placeholder="如: vector, embedding" value="vector">
            </div>
        </div>
        <div class="settings-footer">
            <button class="save-btn" onclick="saveSettings()">保存设置</button>
        </div>
    </div>

    <div class="token-modal" id="tokenModal">
        <div class="token-modal-content">
            <h3>🔐 请输入 Access Key</h3>
            <input type="text" id="akInput" placeholder="Access Key (dev)">
            <input type="password" id="skInput" placeholder="Secret Key (dEv#1234)">
            <div class="token-modal-btns">
                <button class="cancel-btn" onclick="closeTokenModal()">取消</button>
                <button class="login-btn" onclick="login()">登录</button>
            </div>
        </div>
    </div>

    <script>
        let token = localStorage.getItem('milvus_token') || '';
        let config = {
            milvusHost: 'localhost',
            milvusPort: '19530',
            collectionName: 'XiXiang_DiMian_2',
            ollamaUrl: 'http://localhost:11434',
            ollamaModel: 'qwen2.5:14b',
            topK: 5,
            textField: 'content',
            vectorField: 'vector'
        };

        function loadConfig() {
            const saved = localStorage.getItem('milvus_chat_config');
            if (saved) {
                config = JSON.parse(saved);
                document.getElementById('milvusHost').value = config.milvusHost;
                document.getElementById('milvusPort').value = config.milvusPort;
                document.getElementById('collectionName').value = config.collectionName;
                document.getElementById('ollamaUrl').value = config.ollamaUrl;
                document.getElementById('ollamaModel').value = config.ollamaModel;
                document.getElementById('topK').value = config.topK;
                document.getElementById('textField').value = config.textField || 'content';
                document.getElementById('vectorField').value = config.vectorField || 'vector';
            }
        }

        function saveSettings() {
            config.milvusHost = document.getElementById('milvusHost').value;
            config.milvusPort = document.getElementById('milvusPort').value;
            config.collectionName = document.getElementById('collectionName').value;
            config.ollamaUrl = document.getElementById('ollamaUrl').value;
            config.ollamaModel = document.getElementById('ollamaModel').value;
            config.topK = parseInt(document.getElementById('topK').value);
            config.textField = document.getElementById('textField').value;
            config.vectorField = document.getElementById('vectorField').value;
            localStorage.setItem('milvus_chat_config', JSON.stringify(config));
            closeSettings();
        }

        function openSettings() {
            document.getElementById('settingsPanel').classList.add('open');
        }

        function closeSettings() {
            document.getElementById('settingsPanel').classList.remove('open');
        }

        function showTokenModal() {
            document.getElementById('tokenModal').classList.add('show');
        }

        function closeTokenModal() {
            document.getElementById('tokenModal').classList.remove('show');
        }

        async function login() {
            const ak = document.getElementById('akInput').value;
            const sk = document.getElementById('skInput').value;
            
            try {
                const res = await fetch('/api/get_token', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ak, sk})
                });
                const data = await res.json();
                if (data.token) {
                    token = data.token;
                    localStorage.setItem('milvus_token', token);
                    localStorage.setItem('milvus_ak', ak);
                    localStorage.setItem('milvus_sk', sk);
                    closeTokenModal();
                    updateStatus(true);
                } else {
                    alert('登录失败: ' + (data.detail || '未知错误'));
                }
            } catch (e) {
                alert('登录失败: ' + e.message);
            }
        }

        function updateStatus(connected) {
            const dot = document.getElementById('statusDot');
            const text = document.getElementById('statusText');
            if (connected) {
                dot.classList.remove('disconnected');
                text.textContent = '已连接';
            } else {
                dot.classList.add('disconnected');
                text.textContent = '未连接';
            }
        }

        async function checkToken() {
            if (!token) {
                showTokenModal();
                return false;
            }
            return true;
        }

        function handleAuthError() {
            token = '';
            localStorage.removeItem('milvus_token');
            updateStatus(false);
            showTokenModal();
        }

        function addMessage(role, content, results = []) {
            const container = document.getElementById('chatContainer');
            const welcome = document.getElementById('welcomeMessage');
            if (welcome) welcome.style.display = 'none';

            const div = document.createElement('div');
            div.className = `message ${role}`;
            
            let avatarIcon = role === 'user' 
                ? '<svg viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>'
                : '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>';

            let html = `<div class="avatar">${avatarIcon}</div><div class="message-content">${content}</div>`;
            
            if (results && results.length > 0) {
                html += '<div class="search-results">';
                results.forEach(r => {
                    html += `<div class="search-result-item">${r.text || JSON.stringify(r)}<div class="score">距离: ${r.distance?.toFixed(4) || 'N/A'}</div></div>`;
                });
                html += '</div>';
            }
            
            div.innerHTML = html;
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;
        }

        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const btn = document.getElementById('sendBtn');
            const message = input.value.trim();
            
            if (!message) return;
            if (!await checkToken()) return;

            btn.disabled = true;
            input.value = '';

            addMessage('user', message);

            const typingDiv = document.createElement('div');
            typingDiv.className = 'message assistant typing';
            typingDiv.innerHTML = '<div class="avatar"><svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg></div><div class="message-content">正在思考...</div>';
            document.getElementById('chatContainer').appendChild(typingDiv);
            document.getElementById('chatContainer').scrollTop = document.getElementById('chatContainer').scrollHeight;

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Token': token
                    },
                    body: JSON.stringify({
                        message,
                        collection_name: config.collectionName,
                        top_k: config.topK,
                        text_field: config.textField || null,
                        vector_field: config.vectorField || null
                    })
                });
                const data = await res.json();
                
                typingDiv.remove();
                
                if (res.headers.get('X-Refresh-Token') === 'true') {
                    handleAuthError();
                    addMessage('assistant', '❌ 登录已过期，请重新登录');
                } else if (data.response) {
                    addMessage('assistant', data.response, data.results || []);
                } else if (data.detail) {
                    addMessage('assistant', '❌ ' + data.detail);
                }
            } catch (e) {
                typingDiv.remove();
                addMessage('assistant', '❌ 请求失败: ' + e.message);
            }

            btn.disabled = false;
        }

        document.getElementById('messageInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        loadConfig();

        async function autoLogin() {
            const savedAk = localStorage.getItem('milvus_ak');
            const savedSk = localStorage.getItem('milvus_sk');
            if (savedAk && savedSk && !token) {
                try {
                    const res = await fetch('/api/get_token', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ak: savedAk, sk: savedSk})
                    });
                    const data = await res.json();
                    if (data.token) {
                        token = data.token;
                        localStorage.setItem('milvus_token', token);
                        updateStatus(true);
                    }
                } catch (e) {}
            }
            if (token) updateStatus(true);
        }
        autoLogin();
    </script>
</body>
</html>
"""


@app.post("/api/get_token")
async def get_token(request: TokenRequest):
    valid_sk = VALID_CREDENTIALS.get(request.ak)
    if not valid_sk or valid_sk != request.sk:
        raise HTTPException(status_code=401, detail="Invalid AK/SK")
    
    # Check if token already exists for this AK and refresh it
    existing_token = None
    for tok, info in TOKEN_STORE.items():
        if info.get("ak") == request.ak:
            existing_token = tok
            break
    
    if existing_token:
        del TOKEN_STORE[existing_token]
    
    token = generate_token(request.ak)
    expires_at = time.time() + TOKEN_EXPIRY_SECONDS
    
    TOKEN_STORE[token] = {
        "ak": request.ak,
        "expires_at": expires_at,
        "created_at": time.time()
    }
    
    return {"token": token}


class CollectionSchemaRequest(BaseModel):
    collection_name: str


@app.post("/api/schema")
async def get_schema(
    request: CollectionSchemaRequest,
    x_token: str = Depends(verify_token_dependency)
):
    try:
        from pymilvus import connections, Collection
        
        connections.connect(
            alias="default",
            host=MILVUS_CONFIG["host"],
            port=MILVUS_CONFIG["port"]
        )
        
        coll = Collection(request.collection_name)
        schema = coll.schema
        
        fields_info = []
        for field in schema.fields:
            fields_info.append({
                "name": field.name,
                "dtype": str(field.dtype),
                "is_primary": field.is_primary if hasattr(field, 'is_primary') else False
            })
        
        return {
            "collection_name": request.collection_name,
            "fields": fields_info
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    x_token: str = Depends(verify_token_dependency)
):
    try:
        import requests as req
    except ImportError:
        raise HTTPException(status_code=500, detail="requests library not installed")

    results = []
    llm_response = ""
    text_field = None
    
    try:
        from pymilvus import connections, Collection
        
        connections.connect(
            alias="default",
            host=MILVUS_CONFIG["host"],
            port=MILVUS_CONFIG["port"]
        )
        
        coll = Collection(request.collection_name)
        coll.load()
        
        schema = coll.schema
        fields = schema.fields if hasattr(schema, 'fields') else []
        
        # Find all string fields
        string_fields = []
        vector_fields = []
        for field in fields:
            dtype_name = field.dtype.__class__.__name__ if hasattr(field.dtype, '__class__') else str(field.dtype)
            # Check for various dtype representations
            if any(x in dtype_name for x in ['VARCHAR', 'STRING', 'Text']) and field.name not in ['embedding', 'vector']:
                string_fields.append(field.name)
            # Detect vector field
            if 'FloatVector' in dtype_name or 'BinaryVector' in dtype_name or field.name in ['embedding', 'vector']:
                vector_fields.append(field.name)
        
        # Use user-specified field, or auto-detect
        text_field = request.text_field
        if not text_field:
            if string_fields:
                text_field = string_fields[0]
            else:
                text_field = 'content'
        
        # Auto-detect vector field if not specified
        vector_field = request.vector_field
        if not vector_field:
            if vector_fields:
                vector_field = vector_fields[0]
            else:
                vector_field = 'vector'
        
        # Verify the fields exist
        field_names = [f.name for f in fields]
        if text_field not in field_names:
            raise HTTPException(
                status_code=400, 
                detail=f"Field '{text_field}' not found. Available fields: {field_names}"
            )
        if vector_field not in field_names:
            raise HTTPException(
                status_code=400, 
                detail=f"Vector field '{vector_field}' not found. Available fields: {field_names}"
            )
        
        # Get vector dimension from field - try different ways
        vector_dim = 1536  # default based on error message
        for field in fields:
            if field.name == vector_field:
                # Try to get dimension from field properties
                if hasattr(field, 'params') and isinstance(field.params, dict):
                    vector_dim = field.params.get('dim', 1536)
                elif hasattr(field, 'dim'):
                    vector_dim = field.dim
                break
        
        query_embedding = [0.0] * vector_dim
        
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10}
        }
        
        output_fields = [text_field]
        
        search_results = coll.search(
            data=[query_embedding],
            anns_field=vector_field,
            param=search_params,
            limit=request.top_k,
            output_fields=output_fields
        )
        
        for hits in search_results:
            for hit in hits:
                entity = hit.entity._data if hasattr(hit.entity, '_data') else {}
                text_value = entity.get(text_field, "")
                results.append({
                    "id": hit.id,
                    "distance": hit.distance,
                    "text": str(text_value) if text_value else ""
                })
        
        if results:
            context = "\n\n".join([r.get("text", "")[:500] for r in results[:3]])
            prompt = f"""你是一个智能助手，请根据以下参考内容回答用户的问题。

参考内容：
{context}

用户问题：{request.message}

请给出回答："""
        else:
            prompt = f"""你是一个智能助手。请直接回答以下问题：

问题：{request.message}

回答："""

        try:
            ollama_res = req.post(
                f"{OLLAMA_CONFIG['base_url']}/api/generate",
                json={
                    "model": OLLAMA_CONFIG["model"],
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            if ollama_res.status_code == 200:
                llm_response = ollama_res.json().get("response", "")
            else:
                llm_response = f"[Ollama 响应失败: {ollama_res.status_code}]"
        except Exception as e:
            llm_response = f"[无法连接 Ollama: {str(e)}]"

    except ImportError:
        results = []
        llm_response = "pymilvus 未安装，无法连接 Milvus"
    except Exception as e:
        error_msg = str(e)
        if "connect" in error_msg.lower():
            results = []
            llm_response = f"无法连接 Milvus: {error_msg}"
        else:
            raise HTTPException(status_code=500, detail=str(e))

    return {
        "response": llm_response or "未找到相关结果",
        "results": results
    }


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18012)
