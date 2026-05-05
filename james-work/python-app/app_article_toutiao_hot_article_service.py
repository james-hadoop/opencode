#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse
import json
import hashlib
import secrets
import base64
import hmac
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config", "app_article_toutiao_hot_article_service.yaml")

sys.path.insert(0, "/Users/Shared/_AllDocMap/02_Project/gitee/python-app")
from python_app.config import Config

config = Config(CONFIG_PATH)

python_home = config.python_home
db_sql = config.get_db_sql()
db_config = config.get_db_config()

redis_host = config.redis_host
redis_port = config.redis_port
redis_db = config.redis_db
redis_articles_ttl = config.redis_articles_ttl
redis_categories_ttl = config.redis_categories_ttl
sources_config = config.sources_config
jwt_secret_key = config.jwt_secret_key
jwt_algorithm = config.jwt_algorithm
jwt_expires_hours = config.jwt_expires_hours

HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>热文聚合</title>
    <style>
        :root {
            --tc-red: #ff4757;
            --tc-dark: #1a1a2e;
            --tc-gray: #f5f7fa;
            --apple-bg: #ffffff;
            --apple-gray: #f2f2f7;
            --apple-dark: #1c1c1e;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.08);
            --shadow-md: 0 4px 16px rgba(0,0,0,0.12);
            --radius-lg: 16px;
            --radius-md: 12px;
            --radius-sm: 8px;
            --text-primary: #1c1c1e;
            --text-secondary: #8e8e93;
            --border-color: #e0e0e0;
        }

        [data-theme="dark"] {
            --tc-gray: #1c1c1e;
            --apple-bg: #2c2c2e;
            --apple-gray: #3a3a3c;
            --apple-dark: #f5f5f7;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.3);
            --shadow-md: 0 4px 16px rgba(0,0,0,0.4);
            --text-primary: #f5f5f7;
            --text-secondary: #ababab;
            --border-color: #3a3a3c;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif;
        }

        body {
            background: var(--tc-gray);
            min-height: 100vh;
            padding: 20px;
        }

        .header {
            background: linear-gradient(135deg, var(--tc-red) 0%, #ff6b81 100%);
            padding: 24px 28px;
            border-radius: var(--radius-lg);
            margin-bottom: 24px;
            box-shadow: 0 8px 32px rgba(255,71,87,0.25);
        }

        .header h1 {
            color: white;
            font-size: 24px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .header h1::before {
            content: '🔥';
            font-size: 28px;
        }

        .stats {
            color: rgba(255,255,255,0.85);
            font-size: 14px;
            margin-top: 8px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
        }

        .card {
            background: var(--apple-bg);
            border-radius: var(--radius-md);
            padding: 20px;
            box-shadow: var(--shadow-sm);
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            min-height: 180px;
        }

        .card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-md);
        }

        .card-category {
            display: inline-block;
            padding: 4px 10px;
            background: rgba(255,71,87,0.1);
            color: var(--tc-red);
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 12px;
            width: fit-content;
        }

        .card-title {
            font-size: 15px;
            font-weight: 600;
            color: var(--apple-dark);
            line-height: 1.5;
            margin-bottom: 10px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            flex: 1;
        }

        .card-abstract {
            font-size: 13px;
            color: #8e8e93;
            line-height: 1.6;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .card-footer {
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid rgba(0,0,0,0.06);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            color: #8e8e93;
        }

        .card-source {
            font-weight: 500;
        }

        .loading {
            text-align: center;
            padding: 60px 20px;
            color: #8e8e93;
        }

        .loading-spinner {
            width: 40px;
            height: 40px;
            border: 3px solid var(--apple-gray);
            border-top-color: var(--tc-red);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .empty {
            text-align: center;
            padding: 60px 20px;
            grid-column: 1 / -1;
        }

        .empty-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }

        .empty h3 {
            color: var(--apple-dark);
            margin-bottom: 8px;
        }

        .empty p {
            color: #8e8e93;
            font-size: 14px;
        }

        @media (max-width: 1200px) {
            .grid { grid-template-columns: repeat(3, 1fr); }
        }

        @media (max-width: 900px) {
            .grid { grid-template-columns: repeat(2, 1fr); }
        }

        @media (max-width: 600px) {
            .grid { grid-template-columns: 1fr; }
        }

        .filter-pill {
            display: inline-block;
            padding: 6px 12px;
            background: var(--apple-bg);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .filter-pill:hover {
            border-color: var(--tc-red);
            color: var(--tc-red);
        }

        .filter-pill.active {
            background: var(--tc-red);
            color: white;
            border-color: var(--tc-red);
        }

        .rank-badge {
            position: absolute;
            top: 8px;
            right: 8px;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
            color: white;
        }

        .rank-1 { background: linear-gradient(135deg, #FFD700, #FFA500); }
        .rank-2 { background: linear-gradient(135deg, #C0C0C0, #A0A0A0); }
        .rank-3 { background: linear-gradient(135deg, #CD7F32, #B87333); }

        .card { position: relative; }

        .auth-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }

        .auth-modal.show { display: flex; }

        .auth-box {
            background: var(--apple-bg);
            padding: 32px;
            border-radius: var(--radius-lg);
            width: 320px;
            box-shadow: var(--shadow-md);
        }

        .auth-box h2 {
            color: var(--text-primary);
            margin-bottom: 20px;
            text-align: center;
        }

        .auth-box input {
            width: 100%;
            padding: 12px;
            margin-bottom: 12px;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            font-size: 14px;
            background: var(--apple-bg);
            color: var(--text-primary);
        }

        .auth-box button {
            width: 100%;
            padding: 12px;
            background: var(--tc-red);
            color: white;
            border: none;
            border-radius: var(--radius-sm);
            font-size: 14px;
            cursor: pointer;
            margin-bottom: 8px;
        }

        .auth-box .toggle {
            text-align: center;
            font-size: 13px;
            color: var(--text-secondary);
        }

        .auth-box .toggle a {
            color: var(--tc-red);
            cursor: pointer;
        }

        .user-panel {
            display: none;
            align-items: center;
            gap: 12px;
        }

        .user-panel.show { display: flex; }

        .keyword-tag {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            background: var(--apple-gray);
            border-radius: 20px;
            font-size: 13px;
            margin: 4px;
        }

        .keyword-tag button {
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            padding: 0;
            font-size: 14px;
        }

        .filter-dropdown {
            position: relative;
            display: inline-block;
        }

        .filter-dropdown-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: var(--apple-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .filter-dropdown-btn:hover {
            border-color: var(--tc-red);
            color: var(--tc-red);
        }

        .filter-dropdown-btn.active {
            background: var(--tc-red);
            color: white;
            border-color: var(--tc-red);
        }

        .filter-dropdown-btn .badge {
            background: var(--tc-red);
            color: white;
            border-radius: 10px;
            padding: 2px 6px;
            font-size: 11px;
            font-weight: 600;
        }

        .filter-dropdown-btn.active .badge {
            background: white;
            color: var(--tc-red);
        }

        .filter-dropdown-menu {
            display: none;
            position: absolute;
            top: 100%;
            left: 0;
            margin-top: 4px;
            min-width: 180px;
            background: var(--apple-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            box-shadow: var(--shadow-md);
            z-index: 100;
            max-height: 300px;
            overflow-y: auto;
        }

        .filter-dropdown-menu.show {
            display: block;
        }

        .filter-option {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 12px;
            cursor: pointer;
            transition: background 0.15s;
        }

        .filter-option:hover {
            background: var(--apple-gray);
        }

        .filter-option.checked {
            background: rgba(255,71,87,0.08);
        }

        .filter-option input[type="checkbox"] {
            width: 16px;
            height: 16px;
            accent-color: var(--tc-red);
        }

        .filter-option-label {
            flex: 1;
            font-size: 13px;
        }

        .filter-option-count {
            font-size: 12px;
            color: var(--text-secondary);
        }

        .filter-dropdown-actions {
            display: flex;
            gap: 8px;
            padding: 8px 12px;
            border-top: 1px solid var(--border-color);
        }

        .filter-dropdown-actions button {
            flex: 1;
            padding: 6px 0;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
        }

        .filter-dropdown-actions .clear-btn {
            background: var(--apple-gray);
            color: var(--text-primary);
        }

        .filter-dropdown-actions .apply-btn {
            background: var(--tc-red);
            color: white;
        }

        .filter-dropdown-divider {
            height: 1px;
            background: var(--border-color);
            margin: 4px 0;
        }

        .dropdown-backdrop {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 99;
        }

        .dropdown-backdrop.show {
            display: block;
        }
    </style>
</head>
<body>
    <div class="header">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <h1>热文聚合</h1>
                <div class="stats" id="stats">加载中...</div>
            </div>
            <div style="text-align: right; display: flex; gap: 8px; flex-direction: column;">
                <div class="stats" id="lastUpdate" style="font-size: 12px; opacity: 0.8;"></div>
                <div style="display: flex; gap: 8px;">
                    <button onclick="toggleTheme()" id="themeBtn" style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">🌙</button>
                    <button onclick="refreshArticles()" style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">🔄 刷新</button>
                    <button onclick="showAuthModal()" id="loginBtn" style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">👤 登录</button>
                    <div id="userPanel" class="user-panel">
                        <span id="userEmail" style="color: white; font-size: 12px;"></span>
                        <button onclick="showKeywords()" style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">🔔 关键词</button>
                        <button onclick="logout()" style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">🚪 退出</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div style="margin-bottom: 20px; display: flex; gap: 12px; flex-wrap: wrap; align-items: center;">
        <div id="sourceFilterContainer">
            <div class="filter-dropdown" id="sourceFilterDropdown">
                <button class="filter-dropdown-btn" id="sourceFilterBtn" onclick="toggleSourceDropdown()">
                    <span>来源</span>
                    <span class="badge" id="sourceFilterBadge" style="display:none">0</span>
                </button>
                <div class="filter-dropdown-menu" id="sourceFilterMenu">
                    <div id="sourceFilterOptions"></div>
                    <div class="filter-dropdown-actions">
                        <button class="clear-btn" onclick="clearSourceFilters()">清除</button>
                        <button class="apply-btn" onclick="applySourceFilters()">应用</button>
                    </div>
                </div>
            </div>
        </div>
        <div id="categoryFilterContainer">
            <div class="filter-dropdown" id="categoryFilterDropdown">
                <button class="filter-dropdown-btn" id="categoryFilterBtn" onclick="toggleCategoryDropdown()">
                    <span>分类</span>
                    <span class="badge" id="categoryFilterBadge" style="display:none">0</span>
                </button>
                <div class="filter-dropdown-menu" id="categoryFilterMenu">
                    <div id="categoryFilterOptions"></div>
                    <div class="filter-dropdown-actions">
                        <button class="clear-btn" onclick="clearCategoryFilters()">清除</button>
                        <button class="apply-btn" onclick="applyCategoryFilters()">应用</button>
                    </div>
                </div>
            </div>
        </div>
        <div class="dropdown-backdrop" id="dropdownBackdrop" onclick="closeAllDropdowns()"></div>
        <div style="margin-left: auto; display: flex; gap: 8px; align-items: center;">
            <input type="text" id="searchInput" placeholder="搜索标题/摘要..." 
                   style="padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 8px; width: 200px; font-size: 14px; background: var(--apple-bg); color: var(--text-primary);"
                   onkeyup="if(event.key==='Enter')searchArticles()">
            <button onclick="searchArticles()" 
                    style="padding: 8px 16px; background: var(--tc-red); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px;">搜索</button>
        </div>
    </div>

    <div class="grid" id="grid">
        <div class="loading">
            <div class="loading-spinner"></div>
            <div>正在加载热文...</div>
        </div>
    </div>

    <div id="authModal" class="auth-modal">
        <div class="auth-box">
            <h2 id="authTitle">登录</h2>
            <input type="email" id="authEmail" placeholder="邮箱">
            <input type="password" id="authPassword" placeholder="密码">
            <button onclick="submitAuth()" id="authBtn">登录</button>
            <div class="toggle">
                <span id="authToggle">没有账号？<a onclick="toggleAuthMode()">注册</a></span>
            </div>
        </div>
    </div>

    <div id="keywordPanel" style="display: none; margin-top: 20px; padding: 20px; background: var(--apple-bg); border-radius: 12px;">
        <h3 style="color: var(--text-primary); margin-bottom: 12px;">我的关键词</h3>
        <div style="display: flex; gap: 8px; margin-bottom: 12px;">
            <input type="text" id="newKeyword" placeholder="添加关键词..." 
                   style="padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 8px; flex: 1; background: var(--apple-bg); color: var(--text-primary);"
                   onkeyup="if(event.key==='Enter')addKeyword()">
            <button onclick="addKeyword()" 
                    style="padding: 8px 16px; background: var(--tc-red); color: white; border: none; border-radius: 8px; cursor: pointer;">添加</button>
        </div>
        <div id="keywordList"></div>
    </div>

    <script>
        let articles = [];
        let autoRefreshInterval = null;
        let lastUpdateTime = null;
        let selectedSources = [];
        let selectedCategories = [];
        let searchQuery = '';
        let sources = [];
        let categories = [];
        let isSourceDropdownOpen = false;
        let isCategoryDropdownOpen = false;

        function formatTime(date) {
            return date.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit', second: '2-digit'});
        }

        function updateLastUpdateTime() {
            lastUpdateTime = new Date();
            document.getElementById('lastUpdate').textContent = '最后更新: ' + formatTime(lastUpdateTime);
        }

        async function loadCategories() {
            try {
                const res = await fetch('/api/categories');
                const data = await res.json();
                categories = data.categories || [];
                renderCategoryFilters(categories);
            } catch (e) {
                console.error('Failed to load categories:', e);
            }
        }

        async function loadSources() {
            try {
                const res = await fetch('/api/sources');
                const data = await res.json();
                sources = data.sources || [];
                renderSourceFilters();
            } catch (e) {
                console.error('Failed to load sources:', e);
            }
        }

        function renderSourceFilters() {
            const container = document.getElementById('sourceFilterOptions');
            let html = '';
            sources.forEach(src => {
                const isChecked = selectedSources.includes(src.source_id);
                html += `<div class="filter-option ${isChecked ? 'checked' : ''}" onclick="toggleSourceOption('${src.source_id}')">
                    <input type="checkbox" ${isChecked ? 'checked' : ''} onclick="event.stopPropagation()">
                    <span class="filter-option-label">${src.source_icon || ''} ${src.source_name}</span>
                </div>`;
            });
            container.innerHTML = html;
            updateFilterBadges();
        }

        function toggleSourceOption(sourceId) {
            const idx = selectedSources.indexOf(sourceId);
            if (idx >= 0) {
                selectedSources.splice(idx, 1);
            } else {
                selectedSources.push(sourceId);
            }
            renderSourceFilters();
        }

        function applySourceFilters() {
            closeAllDropdowns();
            loadArticles(true);
        }

        function clearSourceFilters() {
            selectedSources = [];
            renderSourceFilters();
        }

        function toggleSourceDropdown() {
            if (isCategoryDropdownOpen) {
                document.getElementById('categoryFilterMenu').classList.remove('show');
                document.getElementById('categoryFilterBtn').classList.remove('active');
                isCategoryDropdownOpen = false;
            }
            const menu = document.getElementById('sourceFilterMenu');
            const btn = document.getElementById('sourceFilterBtn');
            const backdrop = document.getElementById('dropdownBackdrop');
            isSourceDropdownOpen = !isSourceDropdownOpen;
            if (isSourceDropdownOpen) {
                menu.classList.add('show');
                btn.classList.add('active');
                backdrop.classList.add('show');
            } else {
                menu.classList.remove('show');
                btn.classList.remove('active');
                backdrop.classList.remove('show');
            }
        }

        function renderCategoryFilters(categories) {
            const container = document.getElementById('categoryFilterOptions');
            let html = '';
            categories.forEach(cat => {
                const isChecked = selectedCategories.includes(cat.category);
                html += `<div class="filter-option ${isChecked ? 'checked' : ''}" onclick="toggleCategoryOption('${cat.category}')">
                    <input type="checkbox" ${isChecked ? 'checked' : ''} onclick="event.stopPropagation()">
                    <span class="filter-option-label">${cat.category}</span>
                    <span class="filter-option-count">${cat.count}</span>
                </div>`;
            });
            container.innerHTML = html;
            updateFilterBadges();
        }

        function toggleCategoryOption(category) {
            const idx = selectedCategories.indexOf(category);
            if (idx >= 0) {
                selectedCategories.splice(idx, 1);
            } else {
                selectedCategories.push(category);
            }
            renderCategoryFilters(selectedCategories.length > 0 ? categories : []);
        }

        function applyCategoryFilters() {
            closeAllDropdowns();
            loadArticles(true);
        }

        function clearCategoryFilters() {
            selectedCategories = [];
            renderCategoryFilters([]);
        }

        function toggleCategoryDropdown() {
            if (isSourceDropdownOpen) {
                document.getElementById('sourceFilterMenu').classList.remove('show');
                document.getElementById('sourceFilterBtn').classList.remove('active');
                isSourceDropdownOpen = false;
            }
            const menu = document.getElementById('categoryFilterMenu');
            const btn = document.getElementById('categoryFilterBtn');
            const backdrop = document.getElementById('dropdownBackdrop');
            isCategoryDropdownOpen = !isCategoryDropdownOpen;
            if (isCategoryDropdownOpen) {
                menu.classList.add('show');
                btn.classList.add('active');
                backdrop.classList.add('show');
            } else {
                menu.classList.remove('show');
                btn.classList.remove('active');
                backdrop.classList.remove('show');
            }
        }

        function closeAllDropdowns() {
            document.getElementById('sourceFilterMenu').classList.remove('show');
            document.getElementById('sourceFilterBtn').classList.remove('active');
            document.getElementById('categoryFilterMenu').classList.remove('show');
            document.getElementById('categoryFilterBtn').classList.remove('active');
            document.getElementById('dropdownBackdrop').classList.remove('show');
            isSourceDropdownOpen = false;
            isCategoryDropdownOpen = false;
        }

        function updateFilterBadges() {
            const sourceBadge = document.getElementById('sourceFilterBadge');
            const categoryBadge = document.getElementById('categoryFilterBadge');
            sourceBadge.textContent = selectedSources.length;
            sourceBadge.style.display = selectedSources.length > 0 ? 'inline' : 'none';
            categoryBadge.textContent = selectedCategories.length;
            categoryBadge.style.display = selectedCategories.length > 0 ? 'inline' : 'none';
            const sourceBtn = document.getElementById('sourceFilterBtn');
            const categoryBtn = document.getElementById('categoryFilterBtn');
            sourceBtn.classList.toggle('active', selectedSources.length > 0);
            categoryBtn.classList.toggle('active', selectedCategories.length > 0);
        }

        function searchArticles() {
            const query = document.getElementById('searchInput').value.trim();
            if (query.length < 2) {
                alert('搜索词至少2个字符');
                return;
            }
            searchQuery = query;
            currentCategory = 'all';
            loadArticles(true);
        }

        function clearSearch() {
            searchQuery = '';
            document.getElementById('searchInput').value = '';
            currentCategory = 'all';
            loadArticles(true);
        }

        async function loadArticles(refresh = false) {
            try {
                let url = refresh ? '/api/articles?refresh=true' : '/api/articles';
                if (selectedCategories.length > 0) {
                    url += (url.includes('?') ? '&' : '?') + 'categories=' + encodeURIComponent(JSON.stringify(selectedCategories));
                }
                if (selectedSources.length > 0) {
                    url += (url.includes('?') ? '&' : '?') + 'sources=' + encodeURIComponent(JSON.stringify(selectedSources));
                }
                if (searchQuery) {
                    url = '/api/search?q=' + encodeURIComponent(searchQuery);
                }
                const res = await fetch(url);
                const data = await res.json();
                articles = data.articles || [];
                renderCards();
                updateLastUpdateTime();
                
                if (!searchQuery) {
                    loadCategories();
                }
            } catch (e) {
                document.getElementById('grid').innerHTML = `
                    <div class="empty">
                        <div class="empty-icon">❌</div>
                        <h3>加载失败</h3>
                        <p>${e.message}</p>
                    </div>
                `;
            }
        }

        function refreshArticles() {
            loadArticles(true);
        }

        function startAutoRefresh() {
            if (autoRefreshInterval) clearInterval(autoRefreshInterval);
            autoRefreshInterval = setInterval(() => {
                loadArticles(false);
            }, 60000);
        }

        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                if (autoRefreshInterval) {
                    clearInterval(autoRefreshInterval);
                    autoRefreshInterval = null;
                }
            } else {
                loadArticles(false);
                startAutoRefresh();
            }
        });

        loadArticles();
        startAutoRefresh();
        loadCategories();
        loadSources();
        initTheme();
        checkAuth();

        function initTheme() {
            const saved = localStorage.getItem('theme');
            if (saved) {
                document.documentElement.setAttribute('data-theme', saved);
                updateThemeBtn(saved);
            } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
                document.documentElement.setAttribute('data-theme', 'dark');
                updateThemeBtn('dark');
            }
        }

        function toggleTheme() {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
            updateThemeBtn(next);
        }

        function updateThemeBtn(theme) {
            document.getElementById('themeBtn').textContent = theme === 'dark' ? '☀️' : '🌙';
        }

        let authMode = 'login';
        let currentToken = localStorage.getItem('token') || null;
        let userEmail = localStorage.getItem('userEmail') || null;

        function checkAuth() {
            if (currentToken) {
                document.getElementById('loginBtn').style.display = 'none';
                document.getElementById('userPanel').classList.add('show');
                document.getElementById('userEmail').textContent = userEmail;
            } else {
                document.getElementById('loginBtn').style.display = 'inline-block';
                document.getElementById('userPanel').classList.remove('show');
            }
        }

        function showAuthModal() {
            document.getElementById('authModal').classList.add('show');
            authMode = 'login';
            updateAuthUI();
        }

        function hideAuthModal() {
            document.getElementById('authModal').classList.remove('show');
        }

        function toggleAuthMode() {
            authMode = authMode === 'login' ? 'register' : 'login';
            updateAuthUI();
        }

        function updateAuthUI() {
            document.getElementById('authTitle').textContent = authMode === 'login' ? '登录' : '注册';
            document.getElementById('authBtn').textContent = authMode === 'login' ? '登录' : '注册';
            document.getElementById('authToggle').innerHTML = authMode === 'login' 
                ? '没有账号？<a onclick="toggleAuthMode()">注册</a>' 
                : '已有账号？<a onclick="toggleAuthMode()">登录</a>';
        }

        async function submitAuth() {
            const email = document.getElementById('authEmail').value.trim();
            const password = document.getElementById('authPassword').value;
            
            if (!email || !password) {
                alert('请输入邮箱和密码');
                return;
            }

            const endpoint = authMode === 'login' ? '/api/auth/login' : '/api/auth/register';
            try {
                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email, password})
                });
                const data = await res.json();
                
                if (data.success) {
                    if (authMode === 'login') {
                        currentToken = data.token;
                        userEmail = email;
                        localStorage.setItem('token', currentToken);
                        localStorage.setItem('userEmail', userEmail);
                        hideAuthModal();
                        checkAuth();
                    } else {
                        alert('注册成功，请登录');
                        toggleAuthMode();
                    }
                } else {
                    alert(data.error || '操作失败');
                }
            } catch (e) {
                alert('网络错误');
            }
        }

        function logout() {
            currentToken = null;
            userEmail = null;
            localStorage.removeItem('token');
            localStorage.removeItem('userEmail');
            checkAuth();
            document.getElementById('keywordPanel').style.display = 'none';
        }

        async function showKeywords() {
            if (!currentToken) {
                showAuthModal();
                return;
            }
            document.getElementById('keywordPanel').style.display = 'block';
            await loadKeywords();
        }

        async function loadKeywords() {
            try {
                const res = await fetch('/api/user/keywords?token=' + currentToken);
                const data = await res.json();
                if (data.success) {
                    renderKeywords(data.keywords || []);
                }
            } catch (e) {
                console.error(e);
            }
        }

        function renderKeywords(keywords) {
            const container = document.getElementById('keywordList');
            container.innerHTML = keywords.map(k => `
                <span class="keyword-tag">
                    ${k.keyword}
                    <button onclick="deleteKeyword(${k.id})">×</button>
                </span>
            `).join('') || '<p style="color: var(--text-secondary);">暂无关键词</p>';
        }

        async function addKeyword() {
            if (!currentToken) {
                showAuthModal();
                return;
            }
            const keyword = document.getElementById('newKeyword').value.trim();
            if (!keyword) return;
            
            try {
                const res = await fetch('/api/user/keywords?token=' + currentToken, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({keyword})
                });
                const data = await res.json();
                if (data.success) {
                    document.getElementById('newKeyword').value = '';
                    loadKeywords();
                } else {
                    alert(data.error || '添加失败');
                }
            } catch (e) {
                alert('网络错误');
            }
        }

        async function deleteKeyword(id) {
            try {
                const res = await fetch('/api/user/keywords?token=' + currentToken + '&keyword_id=' + id, {
                    method: 'DELETE'
                });
                loadKeywords();
            } catch (e) {
                console.error(e);
            }
        }

        function renderCards() {
            const grid = document.getElementById('grid');
            document.getElementById('stats').textContent = `共 ${articles.length} 篇热文`;

            if (articles.length === 0) {
                grid.innerHTML = `
                    <div class="empty">
                        <div class="empty-icon">📭</div>
                        <h3>暂无热文</h3>
                        <p>数据库中暂无热文数据</p>
                    </div>
                `;
                return;
            }

            grid.innerHTML = articles.map((a, i) => {
                const sourceIcon = a.source_type === 'weibo' ? '📱' : a.source_type === 'bilibili' ? '📺' : '🔥';
                return `
                <div class="card" onclick="viewDetail(${a.id})">
                    ${a.rank && a.rank <= 3 ? `<div class="rank-badge rank-${a.rank}">🔥${a.rank}</div>` : ''}
                    <div class="card-category">${a.category || '热文'}</div>
                    <div class="card-title">${a.title || '无标题'}</div>
                    <div class="card-abstract">${a.abstract || '暂无摘要'}</div>
                    <div class="card-footer">
                        <span class="card-source">${sourceIcon} ${a.source || '未知来源'}</span>
                        <span style="text-align:right">${formatDateOnly(a.created_at)}</span>
                    </div>
                </div>
            `}).join('');
        }

        function viewDetail(id) {
            window.location.href = '/article/' + id;
        }

        function formatDate(dateStr) {
            if (!dateStr) return '';
            try {
                const d = new Date(dateStr);
                return d.toLocaleDateString('zh-CN');
            } catch {
                return dateStr;
            }
        }

        function formatDateOnly(dateStr) {
            if (!dateStr) return '';
            try {
                const d = new Date(dateStr);
                const y = d.getFullYear();
                const m = String(d.getMonth() + 1).padStart(2, '0');
                const day = String(d.getDate()).padStart(2, '0');
                return y + '-' + m + '-' + day;
            } catch {
                return dateStr;
            }
        }

        loadArticles();
    </script>
</body>
</html>
"""

DETAIL_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文章详情</title>
    <style>
        :root {
            --tc-red: #ff4757;
            --tc-dark: #1a1a2e;
            --tc-gray: #f5f7fa;
            --apple-bg: #ffffff;
            --apple-gray: #f2f2f7;
            --apple-dark: #1c1c1e;
            --shadow-md: 0 4px 16px rgba(0,0,0,0.12);
            --radius-lg: 16px;
            --radius-md: 12px;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif;
        }

        body {
            background: var(--tc-gray);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
        }

        .back-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: var(--tc-red);
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            margin-bottom: 20px;
            transition: opacity 0.2s;
        }

        .back-btn:hover {
            opacity: 0.7;
        }

        .article {
            background: var(--apple-bg);
            border-radius: var(--radius-lg);
            padding: 32px;
            box-shadow: var(--shadow-md);
        }

        .article-header {
            margin-bottom: 24px;
            padding-bottom: 24px;
            border-bottom: 1px solid rgba(0,0,0,0.08);
        }

        .article-category {
            display: inline-block;
            padding: 4px 12px;
            background: rgba(255,71,87,0.1);
            color: var(--tc-red);
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 12px;
        }

        .article-title {
            font-size: 24px;
            font-weight: 700;
            color: var(--apple-dark);
            line-height: 1.4;
            margin-bottom: 16px;
        }

        .article-meta {
            display: flex;
            gap: 20px;
            font-size: 13px;
            color: #8e8e93;
        }

        .article-meta span {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .article-content {
            font-size: 16px;
            line-height: 1.8;
            color: var(--apple-dark);
        }

        .article-content p {
            margin-bottom: 16px;
        }

        .article-url {
            margin-top: 24px;
            padding-top: 24px;
            border-top: 1px solid rgba(0,0,0,0.08);
        }

        .article-url a {
            color: var(--tc-red);
            text-decoration: none;
            word-break: break-all;
        }

        .article-url a:hover {
            text-decoration: underline;
        }

        .loading {
            text-align: center;
            padding: 60px 20px;
            color: #8e8e93;
        }

        .loading-spinner {
            width: 40px;
            height: 40px;
            border: 3px solid var(--apple-gray);
            border-top-color: var(--tc-red);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .not-found {
            text-align: center;
            padding: 60px 20px;
        }

        .not-found h2 {
            color: var(--apple-dark);
            margin-bottom: 12px;
        }

        .not-found p {
            color: #8e8e93;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="back-btn" onclick="window.location.href='/'">
            ← 返回热文列表
        </div>
        <div id="content">
            <div class="loading">
                <div class="loading-spinner"></div>
                <div>正在加载...</div>
            </div>
        </div>
    </div>

    <script>
        const articleId = window.location.pathname.split('/').pop();

        async function loadArticle() {
            try {
                const res = await fetch('/api/article/' + articleId);
                if (!res.ok) {
                    document.getElementById('content').innerHTML = `
                        <div class="not-found">
                            <h2>文章不存在</h2>
                            <p>找不到ID为 ${articleId} 的文章</p>
                        </div>
                    `;
                    return;
                }
                const a = await res.json();
                renderArticle(a);
            } catch (e) {
                document.getElementById('content').innerHTML = `
                    <div class="not-found">
                        <h2>加载失败</h2>
                        <p>${e.message}</p>
                    </div>
                `;
            }
        }

        function renderArticle(a) {
            document.title = a.title || '文章详情';
            
            const contentHtml = a.content 
                ? a.content.split('\\n').map(p => `<p>${p}</p>`).join('')
                : '<p>暂无正文内容</p>';

            document.getElementById('content').innerHTML = `
                <div class="article">
                    <div class="article-header">
                        <div class="article-category">${a.category || '热文'}</div>
                        <h1 class="article-title">${a.title || '无标题'}</h1>
                        <div class="article-meta">
                            <span>📰 ${a.source || '未知来源'}</span>
                            <span>📅 ${formatDate(a.publish_time)}</span>
                        </div>
                    </div>
                    <div class="article-content">
                        ${a.abstract ? `<p><strong>摘要：</strong>${a.abstract}</p>` : ''}
                        ${contentHtml}
                    </div>
                    ${a.url ? `
                        <div class="article-url">
                            <a href="${a.url}" target="_blank">🔗 原文链接</a>
                        </div>
                    ` : ''}
                </div>
            `;
        }

        function formatDate(dateStr) {
            if (!dateStr) return '';
            try {
                const d = new Date(dateStr);
                return d.toLocaleDateString('zh-CN') + ' ' + d.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'});
            } catch {
                return dateStr;
            }
        }

        loadArticle();
    </script>
</body>
</html>
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel as PydanticBaseModel
from fastapi import Request


class Article(PydanticBaseModel):
    id: int
    article_id: Optional[str] = None
    title: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    content: Optional[str] = None
    images: Optional[str] = None
    category: Optional[str] = None
    publish_time: Optional[str] = None
    created_at: Optional[str] = None
    created_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None


class AuthRequest(PydanticBaseModel):
    email: str
    password: str


class KeywordRequest(PydanticBaseModel):
    token: str
    keyword: str


class KeywordDeleteRequest(PydanticBaseModel):
    token: str
    keyword_id: int


app = FastAPI(title="今日头条热文", version="1.0.0")

_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True
            )
        except ImportError:
            return None
    return _redis_client

def cache_get(key: str) -> Optional[str]:
    r = get_redis()
    if r:
        try:
            return r.get(key)
        except:
            return None
    return None

def cache_set(key: str, value: str, ttl: int = 60):
    r = get_redis()
    if r:
        try:
            r.setex(key, ttl, value)
        except:
            pass


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_token(user_id: int) -> str:
    exp = datetime.utcnow() + timedelta(hours=jwt_expires_hours)
    payload = {
        "user_id": user_id,
        "exp": exp.timestamp()
    }
    import base64
    import hmac
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    signature = hmac.new(jwt_secret_key.encode(), encoded.encode(), digestmod='sha256').hexdigest()
    return f"{encoded}.{signature}"


def verify_token(token: str) -> Optional[int]:
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return None
        encoded, signature = parts
        expected_sig = hmac.new(jwt_secret_key.encode(), encoded.encode(), digestmod='sha256').hexdigest()
        if signature != expected_sig:
            return None
        payload = json.loads(base64.urlsafe_b64decode(encoded.encode()).decode())
        exp = payload.get("exp", 0)
        if datetime.utcnow().timestamp() > exp:
            return None
        return payload.get("user_id")
    except:
        return None


def ensure_user_tables():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hot_article_users (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_keywords (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id INT NOT NULL,
                    keyword VARCHAR(255) NOT NULL,
                    notify TINYINT DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_user_keyword (user_id, keyword)
                )
            """)
            conn.commit()
    finally:
        conn.close()


def register_user(email: str, password: str) -> Dict[str, Any]:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM hot_article_users WHERE email = %s", (email,))
            if cursor.fetchone():
                return {"success": False, "error": "邮箱已注册"}
            
            cursor.execute(
                "INSERT INTO hot_article_users (email, password_hash) VALUES (%s, %s)",
                (email, hash_password(password))
            )
            conn.commit()
            return {"success": True, "user_id": cursor.lastrowid}
    finally:
        conn.close()


def login_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, password_hash FROM hot_article_users WHERE email = %s",
                (email,)
            )
            user = cursor.fetchone()
            if not user or user["password_hash"] != hash_password(password):
                return None
            token = create_token(user["id"])
            return {"token": token, "user_id": user["id"]}
    finally:
        conn.close()


def get_user_keywords(user_id: int) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, keyword, notify FROM user_keywords WHERE user_id = %s",
                (user_id,)
            )
            return list(cursor.fetchall())
    finally:
        conn.close()


def add_user_keyword(user_id: int, keyword: str) -> Dict[str, Any]:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO user_keywords (user_id, keyword) VALUES (%s, %s)",
                (user_id, keyword)
            )
            conn.commit()
            return {"success": True}
    except:
        return {"success": False, "error": "关键词已存在"}
    finally:
        conn.close()


def delete_user_keyword(user_id: int, keyword_id: int) -> Dict[str, Any]:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_keywords WHERE id = %s AND user_id = %s",
                (keyword_id, user_id)
            )
            conn.commit()
            return {"success": True}
    finally:
        conn.close()


def get_db_connection():
    try:
        import pymysql
        return pymysql.connect(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"],
            charset=db_config.get("charset", "utf8mb4"),
            cursorclass=pymysql.cursors.DictCursor
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="pymysql 未安装")


def fetch_articles(force_db: bool = False, categories: List[str] = None, search: str = None, sources: List[str] = None) -> List[Dict[str, Any]]:
    cache_key = "articles:list"
    if categories and len(categories) > 0:
        cache_key = f"articles:cat:{','.join(sorted(categories))}"
    if search:
        cache_key = f"articles:search:{search[:20]}"
    if sources and len(sources) > 0:
        cache_key = f"articles:src:{','.join(sorted(sources))}"
    
    if not force_db:
        cached = cache_get(cache_key)
        if cached:
            articles = json.loads(cached)
            return add_ranks(articles)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = db_sql
            
            conditions = []
            params = []
            
            if categories and len(categories) > 0:
                cat_conditions = []
                for cat in categories:
                    cat_conditions.append("category = %s")
                    params.append(cat)
                conditions.append("(" + " OR ".join(cat_conditions) + ")")
            
            if search:
                conditions.append("(title LIKE %s OR abstract LIKE %s)")
                params.extend([f"%{search}%", f"%{search}%"])
            
            if sources and len(sources) > 0:
                src_conditions = []
                for src in sources:
                    src_conditions.append("source_type = %s")
                    params.append(src)
                conditions.append("(" + " OR ".join(src_conditions) + ")")
            
            if conditions:
                where_idx = sql.find("ORDER BY")
                if where_idx > 0:
                    sql = sql[:where_idx] + " WHERE " + " AND ".join(conditions) + " " + sql[where_idx:]
            
            cursor.execute(sql, params)
            articles = list(cursor.fetchall())
            
            articles = filter_short_abstracts(articles)
            articles = add_ranks(articles)
            
            ttl = redis_articles_ttl if not search else 30
            cache_set(cache_key, json.dumps(articles, default=str), ttl)
            
            return articles
    finally:
        conn.close()


def filter_short_abstracts(articles: List[Dict]) -> List[Dict]:
    return [a for a in articles if a.get('abstract') and len(str(a.get('abstract', ''))) >= 10]


def add_ranks(articles: List[Dict]) -> List[Dict]:
    for i, a in enumerate(articles):
        a['rank'] = i + 1
    return articles


def fetch_categories() -> List[Dict[str, Any]]:
    cache_key = "articles:categories"
    
    cached = cache_get(cache_key)
    if cached:
        return json.loads(cached)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT category, COUNT(*) as count 
                FROM (
                    SELECT category FROM app.t_app_article_toutiao_article_downloader
                    UNION ALL
                    SELECT category FROM app.t_app_article_weibo_hot
                    UNION ALL
                    SELECT category FROM app.t_app_article_zhihu_hot
                ) as all_cats
                GROUP BY category 
                ORDER BY count DESC
            """)
            categories = list(cursor.fetchall())
            
            cache_set(cache_key, json.dumps(categories, default=str), redis_categories_ttl)
            
            return categories
    finally:
        conn.close()


def fetch_article_by_id(article_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = db_sql.replace("ORDER BY created_at desc, category", "WHERE id = %s")
            sql = sql.replace("LIMIT 50", "LIMIT 1")
            cursor.execute(sql, (article_id,))
            return cursor.fetchone()
    finally:
        conn.close()


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.get("/article/{article_id}", response_class=HTMLResponse)
async def article_detail(article_id: int):
    return DETAIL_PAGE


@app.get("/api/articles", response_model=Dict[str, Any])
async def get_articles(refresh: bool = False, categories: str = None, search: str = None, sources: str = None):
    from typing import List
    cat_list: List[str] = []
    src_list: List[str] = []
    try:
        if categories:
            cat_list = json.loads(categories)
        if sources:
            src_list = json.loads(sources)
    except:
        pass
    try:
        articles = fetch_articles(force_db=refresh, categories=cat_list, search=search, sources=src_list)
        return {"articles": articles, "cached": not refresh}
    except ImportError:
        return {"articles": [], "error": "请安装 pymysql: pip install pymysql"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/categories", response_model=Dict[str, Any])
async def get_categories():
    try:
        categories = fetch_categories()
        return {"categories": categories}
    except ImportError:
        return {"categories": [], "error": "请安装 pymysql: pip install pymysql"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sources", response_model=Dict[str, Any])
async def get_sources():
    return {"sources": sources_config}


@app.get("/api/search", response_model=Dict[str, Any])
async def search_articles(q: str):
    if not q or len(q) < 2:
        return {"articles": [], "error": "搜索词至少2个字符"}
    try:
        articles = fetch_articles(search=q)
        return {"articles": articles, "query": q}
    except ImportError:
        return {"articles": [], "error": "请安装 pymysql: pip install pymysql"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/article/{article_id}", response_model=Dict[str, Any])
async def get_article(article_id: int):
    try:
        article = fetch_article_by_id(article_id)
        if not article:
            raise HTTPException(status_code=404, detail="文章不存在")
        return article
    except ImportError:
        raise HTTPException(status_code=500, detail="pymysql 未安装")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    ensure_user_tables()
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=Dict[str, Any])
async def register(request: AuthRequest):
    if not request.email or not request.password:
        return {"success": False, "error": "邮箱和密码不能为空"}
    if len(request.password) < 6:
        return {"success": False, "error": "密码至少6位"}
    return register_user(request.email, request.password)


@app.post("/api/auth/login", response_model=Dict[str, Any])
async def login(request: AuthRequest):
    result = login_user(request.email, request.password)
    if not result:
        return {"success": False, "error": "邮箱或密码错误"}
    return result


@app.get("/api/user/keywords", response_model=Dict[str, Any])
async def get_keywords(token: str):
    user_id = verify_token(token)
    if not user_id:
        return {"success": False, "error": "未登录", "keywords": []}
    keywords = get_user_keywords(user_id)
    return {"success": True, "keywords": keywords}


@app.post("/api/user/keywords", response_model=Dict[str, Any])
async def add_keyword(request: KeywordRequest):
    user_id = verify_token(request.token)
    if not user_id:
        return {"success": False, "error": "未登录"}
    if not request.keyword or len(request.keyword) < 2:
        return {"success": False, "error": "关键词至少2个字符"}
    return add_user_keyword(user_id, request.keyword)


@app.delete("/api/user/keywords", response_model=Dict[str, Any])
async def delete_keyword(request: KeywordDeleteRequest):
    user_id = verify_token(request.token)
    if not user_id:
        return {"success": False, "error": "未登录"}
    return delete_user_keyword(user_id, request.keyword_id)


if __name__ == "__main__":
    print(f"使用 Python: {python_home}")
    print(f"配置文件: {CONFIG_PATH}")
    print(f"启动服务: http://localhost:18001")
    
    subprocess.run([
        python_home, "-m", "uvicorn",
        "app_article_toutiao_hot_article_service:app",
        "--host", "0.0.0.0",
        "--port", "18001",
    ], cwd=SCRIPT_DIR)
