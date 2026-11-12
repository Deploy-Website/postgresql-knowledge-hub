#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL Handbook - Admin Web Server & API (Port 8001)
Hỗ trợ đầy đủ:
- Xác thực đăng nhập (vinh.nt / Setup12345a@)
- Toggle đóng/mở chuyên mục (mặc định là đóng)
- Tạo bài viết mới & Xóa bài viết
- Chỉnh sửa nội dung bài viết Markdown & Tiêu đề (Edit Article)
- Đổi tên chuyên mục chính & mục con (Rename Category)
"""

import json
import sys
import secrets
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Import các hàm nghiệp vụ từ new_article.py
from new_article import (
    load_mkdocs_config,
    format_full_nav,
    get_nav_categories,
    get_all_articles_flat,
    create_article,
    delete_article,
    update_article,
    rename_category,
    delete_category,
    slugify,
    DOCS_DIR,
    MKDOCS_FILE
)

PORT = 8001

# Thông tin tài khoản quản trị
AUTH_USERNAME = "vinh.nt"
AUTH_PASSWORD = "Setup12345a@"

# Quản lý phiên đăng nhập hợp lệ trong bộ nhớ
ACTIVE_SESSIONS = {}


def update_article_title_in_nav(tree, rel_path, new_title):
    """Cập nhật tiêu đề bài viết trong nav của mkdocs.yml."""
    rel_clean = rel_path.replace("\\", "/").lstrip("/")
    for item in tree:
        if isinstance(item, dict):
            for k, v in list(item.items()):
                if isinstance(v, str):
                    if v.replace("\\", "/").lstrip("/") == rel_clean:
                        if k != new_title:
                            del item[k]
                            item[new_title] = v
                            return True
                elif isinstance(v, list):
                    if update_article_title_in_nav(v, rel_clean, new_title):
                        return True
    return False


def rename_category_in_nav(nav_data, old_name, new_name, parent_cat=None):
    """Đổi tên chuyên mục chính hoặc mục con trong mkdocs.yml."""
    if not parent_cat:
        for item in nav_data:
            if isinstance(item, dict) and old_name in item:
                val = item.pop(old_name)
                item[new_name] = val
                return True
    else:
        for item in nav_data:
            if isinstance(item, dict) and parent_cat in item:
                sub_list = item[parent_cat]
                if isinstance(sub_list, list):
                    for sub in sub_list:
                        if isinstance(sub, dict) and old_name in sub:
                            val = sub.pop(old_name)
                            sub[new_name] = val
                            return True
    return False


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Quản Trị Bài Viết - PostgreSQL Handbook</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --danger: #ef4444;
      --danger-hover: #dc2626;
      --warning: #f59e0b;
      --success: #10b981;
      --accent: #38bdf8;
      --input-bg: #0f172a;
      --site-divider: #334155;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, sans-serif;
      background-color: var(--bg);
      color: var(--text-main);
      line-height: 1.5;
      padding: 1.5rem;
      min-height: 100vh;
    }

    .container {
      max-width: 1180px;
      margin: 0 auto;
    }

    /* LOGIN VIEW */
    #loginView {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 80vh;
    }

    .login-card {
      width: 100%;
      max-width: 440px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 2.25rem 2rem;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
      animation: fadeIn 0.25s ease;
    }

    .login-header {
      text-align: center;
      margin-bottom: 2rem;
    }
    .login-icon {
      font-size: 2.8rem;
      margin-bottom: 0.5rem;
      display: inline-block;
    }
    .login-title {
      font-size: 1.45rem;
      font-weight: 800;
      letter-spacing: -0.02em;
    }
    .login-desc {
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: 0.25rem;
    }

    .login-error {
      display: none;
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid var(--danger);
      color: #fca5a5;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      font-size: 0.85rem;
      margin-bottom: 1.25rem;
      text-align: center;
    }

    .login-btn {
      width: 100%;
      padding: 0.75rem;
      font-size: 0.95rem;
      font-weight: 700;
      border-radius: 10px;
      margin-top: 0.5rem;
    }

    /* DASHBOARD VIEW */
    #dashboardView {
      display: none;
      animation: fadeIn 0.25s ease;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid var(--site-divider);
      margin-bottom: 2rem;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .brand-icon {
      font-size: 2rem;
    }
    .brand h1 {
      font-size: 1.45rem;
      font-weight: 800;
      letter-spacing: -0.02em;
    }
    .brand p {
      font-size: 0.8rem;
      color: var(--text-muted);
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-wrap: wrap;
    }

    .user-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.4rem 0.85rem;
      background: rgba(56, 189, 248, 0.1);
      border: 1px solid rgba(56, 189, 248, 0.25);
      border-radius: 9999px;
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--accent);
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.55rem 1.1rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: all 0.15s ease;
      text-decoration: none;
    }
    .btn-primary {
      background: var(--primary);
      color: #ffffff;
    }
    .btn-primary:hover { background: var(--primary-hover); transform: translateY(-1px); }

    .btn-danger {
      background: var(--danger);
      color: #ffffff;
    }
    .btn-danger:hover { background: var(--danger-hover); }

    .btn-outline {
      background: transparent;
      border: 1px solid var(--card-border);
      color: var(--text-main);
    }
    .btn-outline:hover {
      border-color: var(--accent);
      color: var(--accent);
    }

    .btn-sm {
      padding: 0.3rem 0.65rem;
      font-size: 0.75rem;
      border-radius: 6px;
    }

    .btn-icon {
      padding: 0.2rem 0.45rem;
      font-size: 0.75rem;
      border-radius: 4px;
      opacity: 0.75;
      background: rgba(255, 255, 255, 0.05);
      color: var(--text-muted);
      border: 1px solid var(--card-border);
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .btn-icon:hover {
      opacity: 1;
      color: var(--text-main);
      border-color: var(--accent);
    }

    /* Controls Bar */
    .controls-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
      margin-bottom: 1.5rem;
    }

    .search-box {
      flex: 1;
      max-width: 380px;
      position: relative;
    }
    .search-box input {
      width: 100%;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      padding: 0.6rem 0.9rem;
      border-radius: 8px;
      color: var(--text-main);
      font-size: 0.88rem;
      outline: none;
    }
    .search-box input:focus {
      border-color: var(--primary);
    }

    .controls-right {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-wrap: wrap;
    }

    .stats-chips {
      display: flex;
      gap: 0.6rem;
      font-size: 0.82rem;
      color: var(--text-muted);
    }
    .stat-chip {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      padding: 0.35rem 0.8rem;
      border-radius: 9999px;
    }
    .stat-chip b { color: var(--accent); }

    /* Category Cards & Accordion */
    .category-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      margin-bottom: 1.25rem;
      overflow: hidden;
      transition: border-color 0.15s ease;
    }
    .category-card:hover {
      border-color: rgba(56, 189, 248, 0.4);
    }

    .category-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.9rem 1.25rem;
      background: rgba(255, 255, 255, 0.02);
      border-bottom: 1px solid transparent;
      cursor: pointer;
      user-select: none;
      transition: background 0.15s ease, border-color 0.15s ease;
    }
    .category-header:hover {
      background: rgba(255, 255, 255, 0.05);
    }
    .category-header.open {
      border-bottom-color: var(--site-divider);
      background: rgba(255, 255, 255, 0.04);
    }

    .category-title {
      font-size: 1.08rem;
      font-weight: 750;
      display: flex;
      align-items: center;
      gap: 0.65rem;
    }

    .toggle-btn {
      width: 24px;
      height: 24px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.08);
      color: var(--accent);
      font-size: 0.72rem;
      transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), background 0.15s ease;
    }
    .category-header:hover .toggle-btn {
      background: var(--primary);
      color: #ffffff;
    }
    .category-header.open .toggle-btn {
      transform: rotate(90deg);
    }

    .header-actions-right {
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }

    .badge {
      font-size: 0.7rem;
      padding: 0.15rem 0.55rem;
      border-radius: 9999px;
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.25);
    }

    .category-content {
      display: none;
      animation: expandDown 0.2s ease;
    }
    .category-content.open {
      display: block;
    }

    @keyframes expandDown {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .subcategory-block {
      padding: 0.85rem 1.25rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    }
    .subcategory-block:last-child {
      border-bottom: none;
    }
    .subcategory-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.6rem;
    }
    .subcategory-title {
      font-size: 0.85rem;
      font-weight: 650;
      color: var(--accent);
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }

    .article-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.65rem 0.85rem;
      border-radius: 8px;
      transition: background 0.15s ease;
      margin-bottom: 0.25rem;
    }
    .article-row:hover {
      background: rgba(255, 255, 255, 0.04);
    }

    .article-info {
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
    }
    .article-title {
      font-size: 0.9rem;
      font-weight: 600;
      color: var(--text-main);
    }
    .article-path {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .article-actions {
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }

    /* Modals */
    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(4px);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
      z-index: 1000;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.2s ease;
    }
    .modal-backdrop.active {
      opacity: 1;
      pointer-events: auto;
    }

    .modal {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      width: 100%;
      max-width: 540px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.5);
      overflow: hidden;
      transform: scale(0.95);
      transition: transform 0.2s ease;
    }
    .modal-lg {
      max-width: 940px;
      width: 95%;
      max-height: 92vh;
      display: flex;
      flex-direction: column;
    }
    .modal-lg .modal-body {
      overflow-y: auto;
      max-height: calc(92vh - 130px);
      padding: 1.25rem 1.5rem;
    }
    .modal-backdrop.active .modal {
      transform: scale(1);
    }

    .form-row-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }
    @media (max-width: 680px) {
      .form-row-2 {
        grid-template-columns: 1fr;
      }
    }

    .editor-view-tabs {
      display: flex;
      background: rgba(0, 0, 0, 0.35);
      border-radius: 6px;
      padding: 2px;
      gap: 3px;
      border: 1px solid var(--card-border);
    }
    .view-tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 0.25rem 0.65rem;
      font-size: 0.75rem;
      font-weight: 600;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .view-tab-btn.active {
      background: var(--primary);
      color: #ffffff;
    }
    .editor-preview-pane {
      display: none;
      min-height: 380px;
      max-height: 520px;
      overflow-y: auto;
      padding: 1.1rem 1.35rem;
      background: #0b1120;
      color: #e2e8f0;
      font-size: 0.88rem;
      line-height: 1.6;
      border-radius: 8px;
      border: 1px solid var(--card-border);
    }
    .editor-preview-pane h1 { font-size: 1.35rem; color: #f8fafc; margin: 0.5rem 0 0.4rem; padding-bottom: 0.3rem; border-bottom: 1px solid rgba(255,255,255,0.08); }
    .editor-preview-pane h2 { font-size: 1.15rem; color: #f1f5f9; margin: 1.2rem 0 0.4rem; padding-bottom: 0.25rem; border-bottom: 1px solid rgba(255,255,255,0.06); }
    .editor-preview-pane h3 { font-size: 1rem; color: #e2e8f0; margin: 1rem 0 0.3rem; }
    .editor-preview-pane pre {
      background: #1e293b;
      padding: 0.75rem 1rem;
      border-radius: 6px;
      overflow-x: auto;
      font-family: 'JetBrains Mono', monospace;
      margin: 0.75rem 0;
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .editor-preview-pane code {
      font-family: 'JetBrains Mono', monospace;
      background: rgba(255, 255, 255, 0.08);
      padding: 0.15rem 0.35rem;
      border-radius: 4px;
      color: #38bdf8;
      font-size: 0.85em;
    }
    .editor-preview-pane pre code {
      background: transparent;
      padding: 0;
      color: #f8fafc;
    }
    .editor-preview-pane p {
      margin-bottom: 0.75rem;
    }
    .editor-preview-pane ul, .editor-preview-pane ol {
      margin-left: 1.5rem;
      margin-bottom: 0.75rem;
    }

    .modal-header {
      padding: 1.25rem 1.5rem;
      border-bottom: 1px solid var(--site-divider);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .modal-header h3 {
      font-size: 1.15rem;
      font-weight: 700;
    }
    .modal-close {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 1.3rem;
      cursor: pointer;
    }

    .modal-body {
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.1rem;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }
    .form-group label {
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .form-group input, .form-group select, .form-group textarea {
      background: var(--input-bg);
      border: 1px solid var(--card-border);
      padding: 0.65rem 0.85rem;
      border-radius: 8px;
      color: var(--text-main);
      font-size: 0.88rem;
      outline: none;
    }
    .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
      border-color: var(--primary);
    }

    /* Editor Toolbar */
    .editor-toolbar {
      display: flex;
      gap: 0.4rem;
      flex-wrap: wrap;
      background: rgba(0, 0, 0, 0.25);
      padding: 0.4rem 0.6rem;
      border-radius: 6px;
      border: 1px solid var(--card-border);
    }
    .tb-btn {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 0.25rem 0.55rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .tb-btn:hover {
      background: var(--primary);
      border-color: var(--primary);
    }

    .editor-textarea {
      font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace !important;
      font-size: 0.86rem !important;
      line-height: 1.6 !important;
      min-height: 420px;
      resize: vertical;
      white-space: pre;
    }

    .path-preview {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.78rem;
      color: var(--accent);
      background: var(--input-bg);
      padding: 0.5rem 0.8rem;
      border-radius: 6px;
      border: 1px dashed var(--card-border);
    }

    .modal-footer {
      padding: 1rem 1.5rem;
      background: rgba(0, 0, 0, 0.2);
      border-top: 1px solid var(--site-divider);
      display: flex;
      justify-content: flex-end;
      gap: 0.75rem;
      align-items: center;
    }

    /* Toast */
    .toast-container {
      position: fixed;
      bottom: 1.5rem;
      right: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      z-index: 2000;
    }
    .toast {
      padding: 0.75rem 1.25rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      box-shadow: 0 10px 25px rgba(0,0,0,0.4);
      display: flex;
      align-items: center;
      gap: 0.5rem;
      animation: slideIn 0.2s ease;
    }
    .toast-success { background: #065f46; color: #a7f3d0; border: 1px solid #059669; }
    .toast-error { background: #991b1b; color: #fecaca; border: 1px solid #dc2626; }

    @keyframes slideIn {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
  </style>
</head>
<body>
  <!-- 1. LOGIN SCREEN -->
  <div id="loginView">
    <div class="login-card">
      <div class="login-header">
        <span class="login-icon">🐘</span>
        <h2 class="login-title">Đăng Nhập Quản Trị</h2>
        <p class="login-desc">PostgreSQL Handbook &bull; Xác thực để quản lý bài viết</p>
      </div>

      <div class="login-error" id="loginErrorMsg">
        Tên đăng nhập hoặc mật khẩu không chính xác!
      </div>

      <form onsubmit="handleLoginSubmit(event)">
        <div class="form-group" style="margin-bottom: 1rem;">
          <label>Tài khoản</label>
          <input type="text" id="usernameInput" placeholder="vinh.nt" required autocomplete="username">
        </div>

        <div class="form-group" style="margin-bottom: 1.5rem;">
          <label>Mật khẩu</label>
          <input type="password" id="passwordInput" placeholder="••••••••••••" required autocomplete="current-password">
        </div>

        <button type="submit" class="btn btn-primary login-btn" id="loginSubmitBtn">
          <span>Đăng Nhập</span>
        </button>
      </form>
    </div>
  </div>

  <!-- 2. DASHBOARD SCREEN -->
  <div id="dashboardView">
    <div class="container">
      <header class="header">
        <div class="brand">
          <span class="brand-icon">🐘</span>
          <div>
            <h1>Quản Trị Bài Viết</h1>
            <p>PostgreSQL Handbook &bull; Thêm, sửa, xóa và đồng bộ menu tự động</p>
          </div>
        </div>
        <div class="header-actions">
          <span class="user-badge">
            <span>👤</span> <span id="currentUserName">vinh.nt</span>
          </span>
          <a href="http://127.0.0.1:8000/" target="_blank" class="btn btn-outline">
            <span>Xem Handbook ↗</span>
          </a>
          <button class="btn btn-outline" onclick="openAddCategoryModal()">
            <span>📁 Thêm chuyên mục</span>
          </button>
          <button class="btn btn-primary" onclick="openCreateModal()">
            <span>➕ Tạo bài viết mới</span>
          </button>
          <button class="btn btn-outline" onclick="handleLogout()" title="Đăng xuất khỏi hệ thống">
            <span>🚪 Đăng xuất</span>
          </button>
        </div>
      </header>

      <div class="controls-bar">
        <div class="search-box">
          <input type="text" id="searchInput" placeholder="🔍 Tìm kiếm bài viết theo tiêu đề hoặc file..." oninput="filterArticles()">
        </div>
        <div class="controls-right">
          <div class="stats-chips">
            <div class="stat-chip">Tổng số bài: <b id="totalArticles">0</b></div>
            <div class="stat-chip">Chuyên mục: <b id="totalCategories">0</b></div>
          </div>
          <button class="btn btn-outline btn-sm" onclick="expandAllCategories()">
            <span>▶ Mở tất cả</span>
          </button>
          <button class="btn btn-outline btn-sm" onclick="collapseAllCategories()">
            <span>▼ Đóng tất cả</span>
          </button>
        </div>
      </div>

      <div id="categoriesContainer">
        <div style="text-align: center; padding: 3rem; color: var(--text-muted);">
          Đang tải danh sách bài viết...
        </div>
      </div>
    </div>
  </div>

  <!-- MODAL: TẠO BÀI VIẾT -->
  <div class="modal-backdrop" id="createModal">
    <div class="modal">
      <div class="modal-header">
        <h3>Tạo Bài Viết Mới</h3>
        <button class="modal-close" onclick="closeCreateModal()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label>Chuyên mục chính</label>
          <select id="mainCatSelect" onchange="onMainCatChange()"></select>
          <input type="text" id="customMainCatInput" placeholder="Nhập tên chuyên mục mới..." style="display: none; margin-top: 0.4rem;">
        </div>

        <div class="form-group" id="subCatGroup">
          <label>Mục con (Subcategory)</label>
          <select id="subCatSelect" onchange="updatePreviewPath()"></select>
          <input type="text" id="customSubCatInput" placeholder="Nhập tên mục con mới..." style="display: none; margin-top: 0.4rem;" oninput="updatePreviewPath()">
        </div>

        <div class="form-group">
          <label>Tiêu đề bài viết</label>
          <input type="text" id="articleTitleInput" placeholder="Ví dụ: Tối ưu Partitioning trong PostgreSQL" oninput="onTitleInput()">
        </div>

        <div class="form-group">
          <label>Tên file markdown [.md]</label>
          <input type="text" id="articleFilenameInput" placeholder="toi-uu-partitioning.md" oninput="updatePreviewPath()">
        </div>

        <div class="form-group">
          <label>Đường dẫn lưu dự kiến</label>
          <div class="path-preview" id="previewPathDisplay">docs/...</div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-outline" onclick="closeCreateModal()">Hủy</button>
        <button class="btn btn-primary" onclick="submitCreateArticle()">Tạo bài viết</button>
      </div>
    </div>
  </div>

  <!-- MODAL: CHỈNH SỬA BÀI VIẾT (EDIT ARTICLE) -->
  <div class="modal-backdrop" id="editArticleModal">
    <div class="modal modal-lg">
      <div class="modal-header">
        <div>
          <h3>✏️ Chỉnh Sửa Bài Viết</h3>
          <span style="font-size: 0.75rem; color: var(--accent); font-family: 'JetBrains Mono', monospace;" id="editArticlePathDisplay">docs/...</span>
        </div>
        <button class="modal-close" onclick="closeEditModal()">&times;</button>
      </div>
      <div class="modal-body">
        <!-- Chuyên mục & Mục con -->
        <div class="form-row-2">
          <div class="form-group">
            <label>Chuyên mục chính</label>
            <select id="editArticleMainCat" onchange="onEditMainCatChange()"></select>
            <input type="text" id="editCustomMainCat" placeholder="Nhập tên chuyên mục mới..." style="display: none; margin-top: 0.4rem;">
          </div>
          <div class="form-group" id="editSubCatGroup">
            <label>Mục con (Subcategory)</label>
            <select id="editArticleSubCat" onchange="updateEditPreviewPath()"></select>
            <input type="text" id="editCustomSubCat" placeholder="Nhập tên mục con mới..." style="display: none; margin-top: 0.4rem;" oninput="updateEditPreviewPath()">
          </div>
        </div>

        <!-- Tiêu đề & Tên file -->
        <div class="form-row-2">
          <div class="form-group">
            <label>Tiêu đề bài viết</label>
            <input type="text" id="editArticleTitle" placeholder="Tiêu đề bài viết..." oninput="onEditTitleInput()">
          </div>
          <div class="form-group">
            <label>Tên file markdown [.md]</label>
            <input type="text" id="editArticleFilename" placeholder="ten-bai-viet.md" oninput="updateEditPreviewPath()">
          </div>
        </div>

        <!-- Đường dẫn lưu dự kiến -->
        <div class="form-group">
          <label>Đường dẫn lưu dự kiến</label>
          <div class="path-preview" id="editArticlePreviewPath">docs/...</div>
        </div>

        <!-- Editor & Preview -->
        <div class="form-group">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.2rem;">
            <label style="margin: 0;">Nội dung Markdown</label>
            <div class="editor-view-tabs">
              <button type="button" class="view-tab-btn active" id="tabBtnEdit" onclick="switchEditorTab('edit')">🖊️ Soạn thảo</button>
              <button type="button" class="view-tab-btn" id="tabBtnPreview" onclick="switchEditorTab('preview')">👁️ Xem trước (Preview)</button>
            </div>
          </div>

          <!-- Quick Toolbar -->
          <div class="editor-toolbar" id="editorToolbar">
            <button type="button" class="tb-btn" onclick="insertMarkdown('**', '**', 'Chữ đậm')"><b>B</b> In đậm</button>
            <button type="button" class="tb-btn" onclick="insertMarkdown('*', '*', 'Chữ nghiêng')"><i>I</i> Nghiêng</button>
            <button type="button" class="tb-btn" onclick="insertMarkdown('\n## ', '\n', 'Tiêu đề mục (H2)')">H2</button>
            <button type="button" class="tb-btn" onclick="insertMarkdown('\n### ', '\n', 'Tiêu đề con (H3)')">H3</button>
            <button type="button" class="tb-btn" onclick="insertMarkdown('`', '`', 'code')">Code</button>
            <button type="button" class="tb-btn" onclick="insertMarkdown('\n```sql\n', '\n```\n', 'SELECT * FROM table;')">💻 SQL</button>
            <button type="button" class="tb-btn" onclick="insertMarkdown('\n!!! tip \"Lưu ý\"\n    ', '\n', 'Nội dung ghi chú...')">💡 Tip</button>
            <button type="button" class="tb-btn" onclick="insertMarkdown('\n| Cột 1 | Cột 2 |\n|---|---|\n| Dữ liệu 1 | Dữ liệu 2 |\n', '', '')">📊 Bảng</button>
            <button type="button" class="tb-btn" onclick="insertMarkdown('[', '](url)', 'Liên kết')">🔗 Link</button>
          </div>

          <textarea id="editArticleContent" class="editor-textarea" placeholder="Nhập nội dung Markdown tại đây..." oninput="updateContentCounts()"></textarea>
          <div id="editArticlePreviewPane" class="editor-preview-pane"></div>
        </div>
      </div>
      <div class="modal-footer">
        <span style="font-size: 0.75rem; color: var(--text-muted); margin-right: auto;" id="editorCharCount">
          💡 Mẹo: Nhấn <b>Ctrl + S</b> để lưu nhanh
        </span>
        <button class="btn btn-outline" onclick="closeEditModal()">Hủy</button>
        <button class="btn btn-primary" onclick="submitSaveArticleContent()" id="saveArticleBtn">
          <span>💾 Lưu thay đổi</span>
        </button>
      </div>
    </div>
  </div>

  <!-- MODAL: ĐỔI TÊN CHUYÊN MỤC / MỤC CON -->
  <div class="modal-backdrop" id="renameModal">
    <div class="modal">
      <div class="modal-header">
        <h3 id="renameModalTitle">✏️ Đổi Tên Chuyên Mục</h3>
        <button class="modal-close" onclick="closeRenameModal()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label>Tên hiện tại</label>
          <input type="text" id="renameOldNameDisplay" disabled style="opacity: 0.6;">
        </div>
        <div class="form-group">
          <label>Tên mới</label>
          <input type="text" id="renameNewNameInput" placeholder="Nhập tên mới...">
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-outline" onclick="closeRenameModal()">Hủy</button>
        <button class="btn btn-primary" onclick="submitRenameCategory()">Lưu tên mới</button>
      </div>
    </div>
  </div>

  <!-- MODAL: THÊM CHUYÊN MỤC MỚI -->
  <div class="modal-backdrop" id="addCategoryModal">
    <div class="modal">
      <div class="modal-header">
        <h3>📁 Thêm Chuyên Mục Mới</h3>
        <button class="modal-close" onclick="closeAddCategoryModal()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label>Tên chuyên mục chính</label>
          <input type="text" id="newCategoryName" placeholder="Ví dụ: Architecture" oninput="onNewCatNameInput()">
        </div>
        <div class="form-group">
          <label>Thư mục lưu trữ [docs/...]</label>
          <input type="text" id="newCategoryDir" placeholder="architecture">
        </div>
        <div class="form-group">
          <label>Tiêu đề bài viết mở đầu (index.md)</label>
          <input type="text" id="newCategoryInitialTitle" value="Tổng quan">
        </div>
        <p style="font-size: 0.78rem; color: var(--text-muted);">
          ℹ️ Hệ thống sẽ tự động tạo file <code>index.md</code> trong thư mục và chèn chuyên mục vào menu điều hướng của MkDocs.
        </p>
      </div>
      <div class="modal-footer">
        <button class="btn btn-outline" onclick="closeAddCategoryModal()">Hủy</button>
        <button class="btn btn-primary" onclick="submitAddCategory()">Tạo chuyên mục</button>
      </div>
    </div>
  </div>

  <!-- MODAL: XÁC NHẬN XÓA CHUYÊN MỤC -->
  <div class="modal-backdrop" id="deleteCategoryModal">
    <div class="modal">
      <div class="modal-header">
        <h3 style="color: var(--danger);">Xác Nhận Xóa Chuyên Mục</h3>
        <button class="modal-close" onclick="closeDeleteCategoryModal()">&times;</button>
      </div>
      <div class="modal-body">
        <p>Bạn có chắc chắn muốn xóa chuyên mục sau khỏi menu điều hướng?</p>
        <div style="background: var(--input-bg); padding: 0.85rem; border-radius: 8px; border: 1px solid var(--card-border);">
          <div style="font-weight: 700; font-size: 1rem;" id="deleteCategoryNameDisplay"></div>
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.3rem;" id="deleteCategoryTypeDisplay"></div>
        </div>
        <p style="font-size: 0.82rem; color: var(--danger);">⚠️ Thao tác này sẽ gỡ chuyên mục khỏi menu <code>mkdocs.yml</code>.</p>
      </div>
      <div class="modal-footer">
        <button class="btn btn-outline" onclick="closeDeleteCategoryModal()">Hủy</button>
        <button class="btn btn-danger" onclick="submitDeleteCategory()">Xác nhận xóa</button>
      </div>
    </div>
  </div>

  <!-- MODAL: XÁC NHẬN XÓA -->
  <div class="modal-backdrop" id="deleteModal">
    <div class="modal">
      <div class="modal-header">
        <h3 style="color: var(--danger);">Xác Nhận Xóa Bài Viết</h3>
        <button class="modal-close" onclick="closeDeleteModal()">&times;</button>
      </div>
      <div class="modal-body">
        <p>Bạn có chắc chắn muốn xóa bài viết sau không?</p>
        <div style="background: var(--input-bg); padding: 0.85rem; border-radius: 8px; border: 1px solid var(--card-border);">
          <div style="font-weight: 700; font-size: 1rem;" id="deleteTitleDisplay"></div>
          <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--accent); margin-top: 0.3rem;" id="deletePathDisplay"></div>
        </div>
        <p style="font-size: 0.82rem; color: var(--danger);">⚠️ Thao tác này sẽ xóa vĩnh viễn file trên đĩa và gỡ khỏi menu của Handbook.</p>
      </div>
      <div class="modal-footer">
        <button class="btn btn-outline" onclick="closeDeleteModal()">Hủy</button>
        <button class="btn btn-danger" onclick="submitDeleteArticle()">Xác nhận xóa</button>
      </div>
    </div>
  </div>

  <!-- Toast Container -->
  <div class="toast-container" id="toastContainer"></div>

  <script>
    let appData = { categories: [], flatArticles: [] };
    let deleteTarget = null;
    let editTarget = null;
    let renameTarget = null;
    let categoryOpenStates = {};

    function getAuthToken() {
      return localStorage.getItem('pg_handbook_token');
    }
    function setAuthToken(token) {
      if (token) localStorage.setItem('pg_handbook_token', token);
      else localStorage.removeItem('pg_handbook_token');
    }

    async function authFetch(url, options = {}) {
      const token = getAuthToken();
      options.headers = options.headers || {};
      if (token) {
        options.headers['Authorization'] = 'Bearer ' + token;
      }
      const res = await fetch(url, options);
      if (res.status === 401) {
        setAuthToken(null);
        showLoginView();
        throw new Error('Phiên làm việc hết hạn. Vui lòng đăng nhập lại.');
      }
      return res;
    }

    function showLoginView() {
      document.getElementById('loginView').style.display = 'flex';
      document.getElementById('dashboardView').style.display = 'none';
      document.getElementById('passwordInput').value = '';
    }

    function showDashboardView(username) {
      document.getElementById('loginView').style.display = 'none';
      document.getElementById('dashboardView').style.display = 'block';
      if (username) document.getElementById('currentUserName').innerText = username;
      fetchArticles();
    }

    async function handleLoginSubmit(e) {
      e.preventDefault();
      const username = document.getElementById('usernameInput').value.trim();
      const password = document.getElementById('passwordInput').value;
      const errorDiv = document.getElementById('loginErrorMsg');
      const submitBtn = document.getElementById('loginSubmitBtn');

      errorDiv.style.display = 'none';
      submitBtn.disabled = true;
      submitBtn.innerText = 'Đang kiểm tra...';

      try {
        const res = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (data.status === 'success' && data.token) {
          setAuthToken(data.token);
          showToast('Đăng nhập thành công!');
          showDashboardView(data.username);
        } else {
          errorDiv.innerText = data.message || 'Tên đăng nhập hoặc mật khẩu không đúng!';
          errorDiv.style.display = 'block';
        }
      } catch (err) {
        errorDiv.innerText = 'Lỗi kết nối tới server: ' + err.message;
        errorDiv.style.display = 'block';
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerText = 'Đăng Nhập';
      }
    }

    async function handleLogout() {
      try {
        await authFetch('/api/logout', { method: 'POST' });
      } catch (e) {}
      setAuthToken(null);
      showToast('Đã đăng xuất.');
      showLoginView();
    }

    async function checkAuthSession() {
      const token = getAuthToken();
      if (!token) {
        showLoginView();
        return;
      }
      try {
        const res = await authFetch('/api/auth-check');
        const data = await res.json();
        if (data.status === 'success' && data.authenticated) {
          showDashboardView(data.username);
        } else {
          showLoginView();
        }
      } catch (err) {
        showLoginView();
      }
    }

    function showToast(msg, isError = false) {
      const container = document.getElementById('toastContainer');
      const toast = document.createElement('div');
      toast.className = `toast ${isError ? 'toast-error' : 'toast-success'}`;
      toast.innerHTML = `<span>${isError ? '❌' : '✅'}</span> <span>${msg}</span>`;
      container.appendChild(toast);
      setTimeout(() => toast.remove(), 4000);
    }

    function slugify(text) {
      return text.toLowerCase()
        .replace(/đ/g, 'd').replace(/Đ/g, 'd')
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .replace(/[^\w\s-]/g, '')
        .trim().replace(/[-\s]+/g, '-');
    }

    async function fetchArticles() {
      try {
        const res = await authFetch('/api/articles');
        const data = await res.json();
        if (data.status === 'success') {
          appData = data;
          renderArticles();
          updateStats();
        } else {
          showToast(data.message || 'Lỗi khi tải dữ liệu', true);
        }
      } catch (err) {
        if (getAuthToken()) {
          showToast('Lỗi khi tải dữ liệu bài viết: ' + err.message, true);
        }
      }
    }

    function updateStats() {
      document.getElementById('totalArticles').innerText = appData.flatArticles ? appData.flatArticles.length : 0;
      document.getElementById('totalCategories').innerText = appData.categories ? appData.categories.length : 0;
    }

    function toggleCategory(catIdx) {
      const isOpen = !!categoryOpenStates[catIdx];
      setCategoryState(catIdx, !isOpen);
    }

    function setCategoryState(catIdx, open) {
      categoryOpenStates[catIdx] = open;
      const header = document.getElementById(`cat-header-${catIdx}`);
      const content = document.getElementById(`cat-content-${catIdx}`);
      if (header && content) {
        if (open) {
          header.classList.add('open');
          content.classList.add('open');
        } else {
          header.classList.remove('open');
          content.classList.remove('open');
        }
      }
    }

    function expandAllCategories() {
      if (appData.categories) {
        appData.categories.forEach((_, idx) => setCategoryState(idx, true));
      }
    }

    function collapseAllCategories() {
      if (appData.categories) {
        appData.categories.forEach((_, idx) => setCategoryState(idx, false));
      }
    }

    function renderArticles(filter = '') {
      const container = document.getElementById('categoriesContainer');
      if (!appData.categories || appData.categories.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 2rem;">Chưa có bài viết nào.</div>';
        return;
      }

      const q = filter.trim().toLowerCase();
      let html = '';

      appData.categories.forEach((cat, catIdx) => {
        let catHtml = '';
        let matchedCount = 0;

        if (cat.subcategories && cat.subcategories.length > 0) {
          cat.subcategories.forEach(sub => {
            const matchedArticles = sub.articles.filter(a => 
              !q || a.title.toLowerCase().includes(q) || a.path.toLowerCase().includes(q)
            );

            if (matchedArticles.length > 0) {
              matchedCount += matchedArticles.length;
              catHtml += `
                <div class="subcategory-block">
                  <div class="subcategory-header">
                    <div class="subcategory-title">
                      <span>📁</span> <span>${escapeHtml(sub.name)}</span>
                      <span class="badge">${matchedArticles.length} bài</span>
                    </div>
                    <button class="btn-icon" onclick="event.stopPropagation(); openRenameModal('sub', '${escapeHtml(sub.name)}', '${escapeHtml(cat.name)}')" title="Đổi tên mục con">
                      ✏️ Đổi tên
                    </button>
                  </div>
                  <div>
                    ${matchedArticles.map(a => renderArticleRow(a)).join('')}
                  </div>
                </div>
              `;
            }
          });
        }

        if (cat.direct_articles && cat.direct_articles.length > 0) {
          const matchedDirect = cat.direct_articles.filter(a => 
            !q || a.title.toLowerCase().includes(q) || a.path.toLowerCase().includes(q)
          );

          if (matchedDirect.length > 0) {
            matchedCount += matchedDirect.length;
            catHtml += `
              <div class="subcategory-block">
                <div>
                  ${matchedDirect.map(a => renderArticleRow(a)).join('')}
                </div>
              </div>
            `;
          }
        }

        if (matchedCount > 0) {
          const isOpen = q ? true : !!categoryOpenStates[catIdx];
          categoryOpenStates[catIdx] = isOpen;

          html += `
            <div class="category-card" id="cat-card-${catIdx}">
              <div class="category-header ${isOpen ? 'open' : ''}" id="cat-header-${catIdx}" onclick="toggleCategory(${catIdx})">
                <div class="category-title">
                  <span class="toggle-btn">▶</span>
                  <span>📂</span>
                  <span>${escapeHtml(cat.name)}</span>
                  <span class="badge">${matchedCount} bài</span>
                </div>
                <div class="header-actions-right">
                  <button class="btn-icon" onclick="event.stopPropagation(); openRenameModal('main', '${escapeHtml(cat.name)}')" title="Đổi tên chuyên mục">
                    ✏️ Đổi tên
                  </button>
                </div>
              </div>
              <div class="category-content ${isOpen ? 'open' : ''}" id="cat-content-${catIdx}">
                ${catHtml}
              </div>
            </div>
          `;
        }
      });

      if (!html) {
        container.innerHTML = '<div style="text-align: center; padding: 3rem; color: var(--text-muted);">Không tìm thấy bài viết nào khớp với từ khóa tìm kiếm.</div>';
      } else {
        container.innerHTML = html;
      }
    }

    function renderArticleRow(art) {
      const viewUrl = `http://127.0.0.1:8000/${art.path.replace(/\.md$/, '/')}`;
      return `
        <div class="article-row">
          <div class="article-info">
            <span class="article-title">${escapeHtml(art.title)}</span>
            <span class="article-path">docs/${escapeHtml(art.path)}</span>
          </div>
          <div class="article-actions">
            <button class="btn btn-outline btn-sm" onclick="event.stopPropagation(); openEditArticleModal('${escapeHtml(art.title)}', '${escapeHtml(art.path)}')">✏️ Sửa bài</button>
            <a href="${viewUrl}" target="_blank" class="btn btn-outline btn-sm">👁️ Xem</a>
            <button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); openDeleteModal('${escapeHtml(art.title)}', '${escapeHtml(art.path)}')">🗑️ Xóa</button>
          </div>
        </div>
      `;
    }

    function escapeHtml(text) {
      return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }

    function escapeAttr(text) {
      return String(text).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function filterArticles() {
      const q = document.getElementById('searchInput').value;
      renderArticles(q);
    }

    function renderArticles(filter = '') {
      const container = document.getElementById('categoriesContainer');
      if (!appData.categories || appData.categories.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 2rem;">Chưa có bài viết nào.</div>';
        return;
      }

      const q = filter.trim().toLowerCase();
      let html = '';

      appData.categories.forEach((cat, catIdx) => {
        let catHtml = '';
        let matchedCount = 0;

        if (cat.subcategories && cat.subcategories.length > 0) {
          cat.subcategories.forEach((sub, subIdx) => {
            const matchedArticles = sub.articles.filter(a => 
              !q || a.title.toLowerCase().includes(q) || a.path.toLowerCase().includes(q)
            );

            if (matchedArticles.length > 0) {
              matchedCount += matchedArticles.length;
              catHtml += `
                <div class="subcategory-block">
                  <div class="subcategory-header">
                    <div class="subcategory-title">
                      <span>📁</span> <span>${escapeHtml(sub.name)}</span>
                      <span class="badge">${matchedArticles.length} bài</span>
                    </div>
                    <div class="header-actions-right">
                      <button class="btn-icon" onclick="event.stopPropagation(); openRenameModal('sub', ${catIdx}, ${subIdx})" title="Đổi tên mục con">
                        ✏️ Đổi tên
                      </button>
                      <button class="btn-icon" onclick="event.stopPropagation(); openDeleteCategoryModal('sub', ${catIdx}, ${subIdx})" title="Xóa mục con khỏi menu" style="color: var(--danger);">
                        🗑️ Xóa
                      </button>
                    </div>
                  </div>
                  <div>
                    ${matchedArticles.map(a => renderArticleRow(a)).join('')}
                  </div>
                </div>
              `;
            }
          });
        }

        if (cat.direct_articles && cat.direct_articles.length > 0) {
          const matchedDirect = cat.direct_articles.filter(a => 
            !q || a.title.toLowerCase().includes(q) || a.path.toLowerCase().includes(q)
          );

          if (matchedDirect.length > 0) {
            matchedCount += matchedDirect.length;
            catHtml += `
              <div class="subcategory-block">
                <div>
                  ${matchedDirect.map(a => renderArticleRow(a)).join('')}
                </div>
              </div>
            `;
          }
        }

        if (matchedCount > 0) {
          const isOpen = q ? true : !!categoryOpenStates[catIdx];
          categoryOpenStates[catIdx] = isOpen;

          html += `
            <div class="category-card" id="cat-card-${catIdx}">
              <div class="category-header ${isOpen ? 'open' : ''}" id="cat-header-${catIdx}" onclick="toggleCategory(${catIdx})">
                <div class="category-title">
                  <span class="toggle-btn">▶</span>
                  <span>📂</span>
                  <span>${escapeHtml(cat.name)}</span>
                  <span class="badge">${matchedCount} bài</span>
                </div>
                <div class="header-actions-right">
                  <button class="btn-icon" onclick="event.stopPropagation(); openRenameModal('main', ${catIdx})" title="Đổi tên chuyên mục">
                    ✏️ Đổi tên
                  </button>
                  <button class="btn-icon" onclick="event.stopPropagation(); openDeleteCategoryModal('main', ${catIdx})" title="Xóa chuyên mục khỏi menu" style="color: var(--danger);">
                    🗑️ Xóa
                  </button>
                </div>
              </div>
              <div class="category-content ${isOpen ? 'open' : ''}" id="cat-content-${catIdx}">
                ${catHtml}
              </div>
            </div>
          `;
        }
      });

      if (!html) {
        container.innerHTML = '<div style="text-align: center; padding: 3rem; color: var(--text-muted);">Không tìm thấy bài viết nào khớp với từ khóa tìm kiếm.</div>';
      } else {
        container.innerHTML = html;
      }
    }

    function renderArticleRow(art) {
      const viewUrl = `http://127.0.0.1:8000/${art.path.replace(/\.md$/, '/')}`;
      return `
        <div class="article-row">
          <div class="article-info">
            <span class="article-title">${escapeHtml(art.title)}</span>
            <span class="article-path">docs/${escapeHtml(art.path)}</span>
          </div>
          <div class="article-actions">
            <button class="btn btn-outline btn-sm" onclick="event.stopPropagation(); openEditArticleModal('${escapeAttr(art.path)}')">✏️ Sửa bài</button>
            <a href="${viewUrl}" target="_blank" class="btn btn-outline btn-sm">👁️ Xem</a>
            <button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); openDeleteModal('${escapeAttr(art.path)}')">🗑️ Xóa</button>
          </div>
        </div>
      `;
    }

    /* ==========================================================================
       EDIT ARTICLE (SOẠN THẢO VÀ CHỈNH SỬA BÀI VIẾT)
       ========================================================================== */
    async function openEditArticleModal(path) {
      const art = appData.flatArticles ? appData.flatArticles.find(a => a.path === path) : null;
      editTarget = { path, originalMain: art ? art.main_category : '', originalSub: art ? art.subcategory : '' };
      
      const currentTitle = art ? art.title : '';
      const currentFilename = path.split('/').pop();
      const currentMain = art ? (art.main_category || '') : '';
      const currentSub = art ? (art.subcategory || '') : '';

      document.getElementById('editArticleTitle').value = currentTitle;
      document.getElementById('editArticleFilename').value = currentFilename;
      document.getElementById('editArticlePathDisplay').innerText = 'docs/' + path;
      document.getElementById('editArticleContent').value = 'Đang tải nội dung...';

      populateEditCategoryDropdowns(currentMain, currentSub);
      updateEditPreviewPath();
      switchEditorTab('edit');
      document.getElementById('editArticleModal').classList.add('active');

      try {
        const res = await authFetch(`/api/article-content?path=${encodeURIComponent(path)}`);
        const data = await res.json();
        if (data.status === 'success') {
          document.getElementById('editArticleContent').value = data.content || '';
          if (data.title) {
            document.getElementById('editArticleTitle').value = data.title;
          }
          if (data.main_category) {
            editTarget.originalMain = data.main_category;
            editTarget.originalSub = data.subcategory || '';
            populateEditCategoryDropdowns(data.main_category, data.subcategory);
          }
          updateEditPreviewPath();
          updateContentCounts();
        } else {
          showToast(data.message || 'Lỗi khi tải bài viết', true);
        }
      } catch (err) {
        showToast('Lỗi kết nối: ' + err.message, true);
      }
    }

    function closeEditModal() {
      document.getElementById('editArticleModal').classList.remove('active');
      editTarget = null;
    }

    function populateEditCategoryDropdowns(selectedMain, selectedSub) {
      const mainSelect = document.getElementById('editArticleMainCat');
      mainSelect.innerHTML = '';

      if (appData.categories) {
        appData.categories.forEach(c => {
          const opt = document.createElement('option');
          opt.value = c.name;
          opt.innerText = c.name;
          if (c.name === selectedMain) opt.selected = true;
          mainSelect.appendChild(opt);
        });
      }

      const newOpt = document.createElement('option');
      newOpt.value = '__new__';
      newOpt.innerText = '➕ Thêm chuyên mục mới...';
      mainSelect.appendChild(newOpt);

      onEditMainCatChange(selectedSub);
    }

    function onEditMainCatChange(targetSub) {
      const mainVal = document.getElementById('editArticleMainCat').value;
      const customMainInput = document.getElementById('editCustomMainCat');
      const subGroup = document.getElementById('editSubCatGroup');
      const subSelect = document.getElementById('editArticleSubCat');

      if (mainVal === '__new__') {
        customMainInput.style.display = 'block';
        subGroup.style.display = 'none';
      } else {
        customMainInput.style.display = 'none';
        subGroup.style.display = 'flex';

        const catObj = appData.categories ? appData.categories.find(c => c.name === mainVal) : null;
        subSelect.innerHTML = '<option value="__none__">(Không dùng mục con - trực tiếp trong chuyên mục)</option>';

        if (catObj && catObj.subcategories) {
          catObj.subcategories.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.name;
            opt.innerText = s.name;
            if (targetSub && s.name === targetSub) opt.selected = true;
            subSelect.appendChild(opt);
          });
        }

        const newSubOpt = document.createElement('option');
        newSubOpt.value = '__new__';
        newSubOpt.innerText = '➕ Thêm mục con mới...';
        subSelect.appendChild(newSubOpt);

        subSelect.onchange = onEditSubCatChange;
        onEditSubCatChange();
      }
      updateEditPreviewPath();
    }

    function onEditSubCatChange() {
      const subVal = document.getElementById('editArticleSubCat').value;
      const customSubInput = document.getElementById('editCustomSubCat');
      if (subVal === '__new__') {
        customSubInput.style.display = 'block';
      } else {
        customSubInput.style.display = 'none';
      }
      updateEditPreviewPath();
    }

    function onEditTitleInput() {
      updateEditPreviewPath();
    }

    function updateEditPreviewPath() {
      if (!editTarget) return;
      const mainVal = document.getElementById('editArticleMainCat').value;
      let mainName = mainVal === '__new__' ? document.getElementById('editCustomMainCat').value.trim() : mainVal;
      mainName = mainName || 'category';

      const catObj = appData.categories ? appData.categories.find(c => c.name === mainName) : null;
      let baseDir = catObj ? catObj.dir_hint : slugify(mainName);
      let targetDir = baseDir;

      if (mainVal !== '__new__') {
        const subVal = document.getElementById('editArticleSubCat').value;
        if (subVal && subVal !== '__none__') {
          if (subVal === '__new__') {
            const customSub = document.getElementById('editCustomSubCat').value.trim();
            targetDir += '/' + (slugify(customSub) || 'subcategory');
          } else {
            const subObj = catObj && catObj.subcategories ? catObj.subcategories.find(s => s.name === subVal) : null;
            targetDir = (subObj && subObj.dir_hint) ? subObj.dir_hint : targetDir + '/' + slugify(subVal);
          }
        }
      }

      let filename = document.getElementById('editArticleFilename').value.trim() || 'article.md';
      if (!filename.endsWith('.md')) filename += '.md';

      const newPath = `${targetDir}/${filename}`;
      const displayEl = document.getElementById('editArticlePreviewPath');

      if (newPath !== editTarget.path) {
        displayEl.innerHTML = `docs/${escapeHtml(newPath)} <span style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.72rem; margin-left: 0.5rem;">⚠️ File sẽ được chuyển vị trí / đổi tên</span>`;
      } else {
        displayEl.innerText = `docs/${newPath}`;
      }
    }

    function switchEditorTab(mode) {
      const tabEdit = document.getElementById('tabBtnEdit');
      const tabPrev = document.getElementById('tabBtnPreview');
      const tb = document.getElementById('editorToolbar');
      const ta = document.getElementById('editArticleContent');
      const pv = document.getElementById('editArticlePreviewPane');

      if (mode === 'preview') {
        tabEdit.classList.remove('active');
        tabPrev.classList.add('active');
        tb.style.display = 'none';
        ta.style.display = 'none';
        pv.style.display = 'block';
        pv.innerHTML = renderMarkdownToHtml(ta.value);
      } else {
        tabEdit.classList.add('active');
        tabPrev.classList.remove('active');
        tb.style.display = 'flex';
        ta.style.display = 'block';
        pv.style.display = 'none';
      }
    }

    function renderMarkdownToHtml(md) {
      if (!md) return '<p style="color: var(--text-muted); font-style: italic;">(Nội dung bài viết trống)</p>';
      let text = String(md).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

      text = text.replace(/```([a-zA-Z0-9_-]*)\r?\n([\s\S]*?)```/g, function(match, lang, code) {
        return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
      });

      text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
      text = text.replace(/^####\s+(.*$)/gim, '<h4>$1</h4>');
      text = text.replace(/^###\s+(.*$)/gim, '<h3>$1</h3>');
      text = text.replace(/^##\s+(.*$)/gim, '<h2>$1</h2>');
      text = text.replace(/^#\s+(.*$)/gim, '<h1>$1</h1>');
      text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
      text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');

      text = text.replace(/^!!!\s*([a-z]+)\s*(?:&quot;([^&]+)&quot;|"([^"]+)")?\r?\n([\s\S]*?)(?=\r?\n\r?\n|\r?\n[^\s]|$)/gim, function(match, type, title1, title2, content) {
        const title = title1 || title2 || type.toUpperCase();
        return `<div style="border-left: 4px solid var(--accent); background: rgba(56,189,248,0.08); padding: 0.75rem 1rem; border-radius: 6px; margin: 0.85rem 0;">
          <div style="font-weight: 700; color: var(--accent); margin-bottom: 0.25rem;">💡 ${title}</div>
          <div>${content.replace(/^\s{4}/gm, '').trim()}</div>
        </div>`;
      });

      text = text.replace(/^&gt;\s?(.*$)/gim, '<blockquote style="border-left: 3px solid #64748b; padding-left: 0.75rem; color: #94a3b8; margin: 0.5rem 0;">$1</blockquote>');
      text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" style="color: var(--accent); text-decoration: underline;">$1</a>');

      text = text.replace(/((?:\|[^\n]+\|\r?\n)+)/g, function(match, tableBlock) {
        const rows = tableBlock.trim().split(/\r?\n/);
        if (rows.length < 2) return tableBlock;
        let tableHtml = '<table style="width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.85rem;">';
        rows.forEach((row, rIdx) => {
          if (rIdx === 1 && row.includes('---')) return;
          const cells = row.split('|').filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
          tableHtml += '<tr>';
          cells.forEach(cell => {
            const tag = rIdx === 0 ? 'th' : 'td';
            const style = rIdx === 0 
              ? 'padding: 0.5rem 0.75rem; background: rgba(255,255,255,0.06); border: 1px solid var(--card-border); text-align: left; font-weight: 600;' 
              : 'padding: 0.5rem 0.75rem; border: 1px solid var(--card-border);';
            tableHtml += `<${tag} style="${style}">${cell.trim()}</${tag}>`;
          });
          tableHtml += '</tr>';
        });
        tableHtml += '</table>';
        return tableHtml;
      });

      text = text.replace(/^\s*-\s+(.*$)/gim, '<li style="margin-left: 1.25rem;">$1</li>');

      const blocks = text.split(/\r?\n\r?\n/);
      return blocks.map(b => {
        b = b.trim();
        if (!b) return '';
        if (b.startsWith('<h') || b.startsWith('<pre') || b.startsWith('<table') || b.startsWith('<div') || b.startsWith('<blockquote') || b.startsWith('<li')) {
          return b;
        }
        return `<p style="margin-bottom: 0.75rem;">${b.replace(/\r?\n/g, '<br>')}</p>`;
      }).join('\n');
    }

    function updateContentCounts() {
      const val = document.getElementById('editArticleContent').value;
      const chars = val.length;
      const words = val.trim() ? val.trim().split(/\s+/).length : 0;
      const countEl = document.getElementById('editorCharCount');
      if (countEl) {
        countEl.innerHTML = `Số ký tự: <b>${chars}</b> | Số từ: <b>${words}</b> &bull; 💡 Mẹo: Nhấn <b>Ctrl + S</b> để lưu nhanh`;
      }
    }

    function insertMarkdown(prefix, suffix, placeholder) {
      const ta = document.getElementById('editArticleContent');
      const start = ta.selectionStart;
      const end = ta.selectionEnd;
      const selText = ta.value.substring(start, end) || placeholder;
      const replacement = prefix + selText + suffix;
      ta.value = ta.value.substring(0, start) + replacement + ta.value.substring(end);
      ta.focus();
      ta.setSelectionRange(start + prefix.length, start + prefix.length + selText.length);
      updateContentCounts();
    }

    async function submitSaveArticleContent() {
      if (!editTarget) return;
      const newTitle = document.getElementById('editArticleTitle').value.trim();
      const newContent = document.getElementById('editArticleContent').value;
      const btn = document.getElementById('saveArticleBtn');

      if (!newTitle) {
        alert('Tiêu đề bài viết không được để trống!');
        return;
      }

      const mainVal = document.getElementById('editArticleMainCat').value;
      const category = mainVal === '__new__' ? document.getElementById('editCustomMainCat').value.trim() : mainVal;
      if (!category) {
        alert('Vui lòng chọn hoặc nhập chuyên mục chính!');
        return;
      }

      let subcategory = null;
      if (mainVal !== '__new__') {
        const subVal = document.getElementById('editArticleSubCat').value;
        if (subVal === '__new__') {
          subcategory = document.getElementById('editCustomSubCat').value.trim();
        } else if (subVal !== '__none__') {
          subcategory = subVal;
        }
      }

      const filename = document.getElementById('editArticleFilename').value.trim();

      btn.disabled = true;
      btn.innerText = 'Đang lưu...';

      try {
        const res = await authFetch('/api/article-content', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            path: editTarget.path,
            title: newTitle,
            category: category,
            subcategory: subcategory,
            filename: filename,
            content: newContent
          })
        });
        const data = await res.json();
        if (data.status === 'success') {
          showToast(data.message || 'Đã lưu thay đổi bài viết thành công!');
          closeEditModal();
          await fetchArticles();
        } else {
          showToast(data.message, true);
        }
      } catch (err) {
        showToast('Lỗi khi lưu bài viết: ' + err.message, true);
      } finally {
        btn.disabled = false;
        btn.innerText = '💾 Lưu thay đổi';
      }
    }

    // Lắng nghe Ctrl + S khi đang trong khung soạn thảo
    document.addEventListener('keydown', function(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        const modal = document.getElementById('editArticleModal');
        if (modal && modal.classList.contains('active')) {
          e.preventDefault();
          submitSaveArticleContent();
        }
      }
    });

    document.addEventListener('DOMContentLoaded', function() {
      const editArea = document.getElementById('editArticleContent');
      if (editArea) {
        editArea.addEventListener('keydown', function(e) {
          if (e.key === 'Tab') {
            e.preventDefault();
            const start = this.selectionStart;
            const end = this.selectionEnd;
            this.value = this.value.substring(0, start) + '  ' + this.value.substring(end);
            this.selectionStart = this.selectionEnd = start + 2;
          }
        });
      }
    });

    /* ==========================================================================
       CATEGORY MANAGEMENT (THÊM / ĐỔI TÊN / XÓA CHUYÊN MỤC)
       ========================================================================== */
    function openRenameModal(type, catIdx, subIdx = -1) {
      const cat = appData.categories ? appData.categories[catIdx] : null;
      if (!cat) return;

      let oldName = '';
      let parentCat = '';
      if (type === 'main') {
        oldName = cat.name;
      } else {
        const sub = (cat.subcategories && cat.subcategories[subIdx]) ? cat.subcategories[subIdx] : null;
        if (!sub) return;
        oldName = sub.name;
        parentCat = cat.name;
      }

      renameTarget = { type, oldName, parentCat };
      const titleEl = document.getElementById('renameModalTitle');
      titleEl.innerText = type === 'main' ? `✏️ Đổi Tên Chuyên Mục "${oldName}"` : `✏️ Đổi Tên Mục Con "${oldName}"`;
      document.getElementById('renameOldNameDisplay').value = oldName;
      document.getElementById('renameNewNameInput').value = oldName;
      document.getElementById('renameModal').classList.add('active');
      setTimeout(() => document.getElementById('renameNewNameInput').focus(), 50);
    }

    function closeRenameModal() {
      document.getElementById('renameModal').classList.remove('active');
      renameTarget = null;
    }

    async function submitRenameCategory() {
      if (!renameTarget) return;
      const newName = document.getElementById('renameNewNameInput').value.trim();
      if (!newName) {
        alert('Tên mới không được để trống!');
        return;
      }
      if (newName === renameTarget.oldName) {
        closeRenameModal();
        return;
      }

      try {
        const res = await authFetch('/api/category-rename', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: renameTarget.type,
            old_name: renameTarget.oldName,
            new_name: newName,
            parent_cat: renameTarget.parentCat
          })
        });
        const data = await res.json();
        if (data.status === 'success') {
          showToast(data.message || 'Đã đổi tên thành công!');
          closeRenameModal();
          await fetchArticles();
        } else {
          showToast(data.message, true);
        }
      } catch (err) {
        showToast('Lỗi khi đổi tên: ' + err.message, true);
      }
    }

    function openAddCategoryModal() {
      document.getElementById('newCategoryName').value = '';
      document.getElementById('newCategoryDir').value = '';
      document.getElementById('newCategoryInitialTitle').value = 'Tổng quan';
      document.getElementById('addCategoryModal').classList.add('active');
      setTimeout(() => document.getElementById('newCategoryName').focus(), 50);
    }

    function closeAddCategoryModal() {
      document.getElementById('addCategoryModal').classList.remove('active');
    }

    function onNewCatNameInput() {
      const val = document.getElementById('newCategoryName').value;
      document.getElementById('newCategoryDir').value = slugify(val);
    }

    async function submitAddCategory() {
      const name = document.getElementById('newCategoryName').value.trim();
      const dir_name = document.getElementById('newCategoryDir').value.trim() || slugify(name);
      const initial_title = document.getElementById('newCategoryInitialTitle').value.trim() || 'Tổng quan';

      if (!name) {
        alert('Vui lòng nhập tên chuyên mục!');
        return;
      }

      try {
        const res = await authFetch('/api/categories', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, dir_name, initial_title })
        });
        const data = await res.json();
        if (data.status === 'success') {
          showToast(data.message || 'Đã tạo chuyên mục thành công!');
          closeAddCategoryModal();
          await fetchArticles();
        } else {
          showToast(data.message, true);
        }
      } catch (err) {
        showToast('Lỗi khi tạo chuyên mục: ' + err.message, true);
      }
    }

    let deleteCategoryTarget = null;

    function openDeleteCategoryModal(type, catIdx, subIdx = -1) {
      const cat = appData.categories ? appData.categories[catIdx] : null;
      if (!cat) return;

      let name = '';
      let parentCat = '';
      let count = 0;

      if (type === 'main') {
        name = cat.name;
        count = (cat.direct_articles ? cat.direct_articles.length : 0);
        if (cat.subcategories) {
          cat.subcategories.forEach(s => { count += (s.articles ? s.articles.length : 0); });
        }
      } else {
        const sub = (cat.subcategories && cat.subcategories[subIdx]) ? cat.subcategories[subIdx] : null;
        if (!sub) return;
        name = sub.name;
        parentCat = cat.name;
        count = sub.articles ? sub.articles.length : 0;
      }

      deleteCategoryTarget = { type, name, parentCat };
      document.getElementById('deleteCategoryNameDisplay').innerText = name;
      document.getElementById('deleteCategoryTypeDisplay').innerText = type === 'main'
        ? `Chuyên mục chính (Đang chứa ${count} bài viết)`
        : `Mục con trong "${parentCat}" (Đang chứa ${count} bài viết)`;
      document.getElementById('deleteCategoryModal').classList.add('active');
    }

    function closeDeleteCategoryModal() {
      document.getElementById('deleteCategoryModal').classList.remove('active');
      deleteCategoryTarget = null;
    }

    async function submitDeleteCategory() {
      if (!deleteCategoryTarget) return;

      try {
        const res = await authFetch('/api/categories', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(deleteCategoryTarget)
        });
        const data = await res.json();
        if (data.status === 'success') {
          showToast(data.message || 'Đã xóa chuyên mục thành công!');
          closeDeleteCategoryModal();
          await fetchArticles();
        } else {
          showToast(data.message, true);
        }
      } catch (err) {
        showToast('Lỗi khi xóa chuyên mục: ' + err.message, true);
      }
    }

    /* ==========================================================================
       CREATE ARTICLE MODAL
       ========================================================================== */
    function openCreateModal() {
      const mainSelect = document.getElementById('mainCatSelect');
      mainSelect.innerHTML = '';
      
      appData.categories.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.name;
        opt.innerText = c.name;
        mainSelect.appendChild(opt);
      });

      const newOpt = document.createElement('option');
      newOpt.value = '__new__';
      newOpt.innerText = '➕ Thêm chuyên mục mới...';
      mainSelect.appendChild(newOpt);

      onMainCatChange();
      document.getElementById('articleTitleInput').value = '';
      document.getElementById('articleFilenameInput').value = '';
      updatePreviewPath();

      document.getElementById('createModal').classList.add('active');
    }

    function closeCreateModal() {
      document.getElementById('createModal').classList.remove('active');
    }

    function onMainCatChange() {
      const mainVal = document.getElementById('mainCatSelect').value;
      const customMainInput = document.getElementById('customMainCatInput');
      const subGroup = document.getElementById('subCatGroup');
      const subSelect = document.getElementById('subCatSelect');

      if (mainVal === '__new__') {
        customMainInput.style.display = 'block';
        subGroup.style.display = 'none';
      } else {
        customMainInput.style.display = 'none';
        subGroup.style.display = 'flex';

        const catObj = appData.categories.find(c => c.name === mainVal);
        subSelect.innerHTML = '<option value="__none__">(Không dùng mục con - thêm trực tiếp)</option>';

        if (catObj && catObj.subcategories) {
          catObj.subcategories.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.name;
            opt.innerText = s.name;
            subSelect.appendChild(opt);
          });
        }

        const newSubOpt = document.createElement('option');
        newSubOpt.value = '__new__';
        newSubOpt.innerText = '➕ Thêm mục con mới...';
        subSelect.appendChild(newSubOpt);

        subSelect.onchange = onSubCatChange;
        onSubCatChange();
      }
      updatePreviewPath();
    }

    function onSubCatChange() {
      const subVal = document.getElementById('subCatSelect').value;
      const customSubInput = document.getElementById('customSubCatInput');
      if (subVal === '__new__') {
        customSubInput.style.display = 'block';
      } else {
        customSubInput.style.display = 'none';
      }
      updatePreviewPath();
    }

    function onTitleInput() {
      const title = document.getElementById('articleTitleInput').value;
      const fileInput = document.getElementById('articleFilenameInput');
      if (title) {
        fileInput.value = slugify(title) + '.md';
      }
      updatePreviewPath();
    }

    function updatePreviewPath() {
      const mainVal = document.getElementById('mainCatSelect').value;
      let mainName = mainVal === '__new__' ? document.getElementById('customMainCatInput').value : mainVal;
      mainName = mainName || 'category';

      const catObj = appData.categories.find(c => c.name === mainName);
      let baseDir = catObj ? catObj.dir_hint : slugify(mainName);

      const subVal = document.getElementById('subCatSelect').value;
      let targetDir = baseDir;

      if (mainVal !== '__new__' && subVal && subVal !== '__none__') {
        if (subVal === '__new__') {
          const customSub = document.getElementById('customSubCatInput').value;
          targetDir += '/' + (slugify(customSub) || 'subcategory');
        } else {
          const subObj = catObj && catObj.subcategories ? catObj.subcategories.find(s => s.name === subVal) : null;
          targetDir = (subObj && subObj.dir_hint) ? subObj.dir_hint : targetDir + '/' + slugify(subVal);
        }
      }

      let filename = document.getElementById('articleFilenameInput').value.trim() || 'bai-viet-moi.md';
      if (!filename.endsWith('.md')) filename += '.md';

      document.getElementById('previewPathDisplay').innerText = `docs/${targetDir}/${filename}`;
    }

    async function submitCreateArticle() {
      const title = document.getElementById('articleTitleInput').value.trim();
      if (!title) {
        alert('Vui lòng nhập tiêu đề bài viết!');
        return;
      }

      const mainVal = document.getElementById('mainCatSelect').value;
      const category = mainVal === '__new__' ? document.getElementById('customMainCatInput').value.trim() : mainVal;
      if (!category) {
        alert('Vui lòng chọn hoặc nhập chuyên mục chính!');
        return;
      }

      let subcategory = null;
      if (mainVal !== '__new__') {
        const subVal = document.getElementById('subCatSelect').value;
        if (subVal === '__new__') {
          subcategory = document.getElementById('customSubCatInput').value.trim();
        } else if (subVal !== '__none__') {
          subcategory = subVal;
        }
      }

      const filename = document.getElementById('articleFilenameInput').value.trim();

      try {
        const res = await authFetch('/api/articles', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, category, subcategory, filename })
        });
        const result = await res.json();
        if (result.status === 'success') {
          showToast(result.message);
          closeCreateModal();
          await fetchArticles();
        } else {
          showToast(result.message, true);
        }
      } catch (err) {
        showToast('Lỗi khi gửi yêu cầu đến server: ' + err.message, true);
      }
    }

    /* ==========================================================================
       DELETE ARTICLE MODAL
       ========================================================================== */
    function openDeleteModal(titleOrPath, maybePath) {
      let title = titleOrPath;
      let path = maybePath;
      if (!maybePath) {
        path = titleOrPath;
        const art = appData.flatArticles ? appData.flatArticles.find(a => a.path === path) : null;
        title = art ? art.title : path;
      }
      deleteTarget = { title, path };
      document.getElementById('deleteTitleDisplay').innerText = title;
      document.getElementById('deletePathDisplay').innerText = 'docs/' + path;
      document.getElementById('deleteModal').classList.add('active');
    }

    function closeDeleteModal() {
      document.getElementById('deleteModal').classList.remove('active');
      deleteTarget = null;
    }

    async function submitDeleteArticle() {
      if (!deleteTarget) return;

      try {
        const res = await authFetch('/api/articles', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: deleteTarget.path })
        });
        const result = await res.json();
        if (result.status === 'success') {
          showToast(result.message);
          closeDeleteModal();
          await fetchArticles();
        } else {
          showToast(result.message, true);
        }
      } catch (err) {
        showToast('Lỗi khi xóa bài viết: ' + err.message, true);
      }
    }

    checkAuthSession();
  </script>
</body>
</html>
"""


class HandbookAdminHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler phục vụ REST API và Web UI có bảo vệ xác thực."""

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def check_authenticated(self) -> bool:
        """Kiểm tra token Bearer từ header Authorization."""
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token in ACTIVE_SESSIONS:
                return True
        return False

    def send_unauthorized(self):
        """Phản hồi lỗi 401 khi chưa đăng nhập."""
        self.send_response(401)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "error",
            "message": "Yêu cầu đăng nhập để truy cập tính năng quản trị."
        }, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)

        # API: Kiểm tra trạng thái đăng nhập
        if parsed.path == "/api/auth-check":
            if self.check_authenticated():
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "authenticated": True,
                    "username": AUTH_USERNAME
                }).encode("utf-8"))
            else:
                self.send_unauthorized()
            return

        # API: Lấy nội dung chi tiết bài viết Markdown (GET /api/article-content?path=...)
        if parsed.path == "/api/article-content":
            if not self.check_authenticated():
                self.send_unauthorized()
                return

            qs = parse_qs(parsed.query)
            rel_path = qs.get("path", [""])[0].strip().replace("\\", "/").lstrip("/")

            if not rel_path or ".." in rel_path:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Đường dẫn không hợp lệ"}).encode("utf-8"))
                return

            full_p = DOCS_DIR / rel_path
            if not full_p.exists():
                self.send_response(404)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Không tìm thấy file"}).encode("utf-8"))
                return

            content = full_p.read_text(encoding="utf-8")

            # Lấy thông tin bài viết từ nav
            _, nav_data = load_mkdocs_config()
            found_art = None
            for art in get_all_articles_flat(nav_data):
                if art["path"] == rel_path:
                    found_art = art
                    break

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "path": rel_path,
                "title": found_art["title"] if found_art else "",
                "main_category": found_art.get("main_category", "") if found_art else "",
                "subcategory": found_art.get("subcategory", "") if found_art else "",
                "content": content
            }, ensure_ascii=False).encode("utf-8"))
            return

        # API: Danh sách bài viết
        if parsed.path == "/api/articles":
            if not self.check_authenticated():
                self.send_unauthorized()
                return

            try:
                _, nav_data = load_mkdocs_config()
                cat_structure = get_nav_categories(nav_data)
                flat_articles = get_all_articles_flat(nav_data)

                formatted_categories = []
                for cat_name, info in cat_structure.items():
                    sub_list = []
                    for sname, sinfo in info["subcategories"].items():
                        arts = []
                        for item in sinfo["items"]:
                            if isinstance(item, dict):
                                for k, v in item.items():
                                    if isinstance(v, str):
                                        arts.append({
                                            "title": k,
                                            "path": v.replace("\\", "/"),
                                            "main_category": cat_name,
                                            "subcategory": sname,
                                            "exists": (DOCS_DIR / v).exists()
                                        })
                        sub_list.append({
                            "name": sname,
                            "dir_hint": sinfo["dir_hint"],
                            "articles": arts
                        })

                    direct_arts = []
                    for item in info["direct_items"]:
                        if isinstance(item, dict):
                            for k, v in item.items():
                                if isinstance(v, str):
                                    direct_arts.append({
                                        "title": k,
                                        "path": v.replace("\\", "/"),
                                        "main_category": cat_name,
                                        "subcategory": "",
                                        "exists": (DOCS_DIR / v).exists()
                                    })

                    formatted_categories.append({
                        "name": cat_name,
                        "dir_hint": info["dir_hint"],
                        "subcategories": sub_list,
                        "direct_articles": direct_arts
                    })

                response_data = {
                    "status": "success",
                    "categories": formatted_categories,
                    "flatArticles": flat_articles
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        # UI HTML
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)

        # API: Đăng nhập
        if parsed.path == "/api/login":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body.decode("utf-8"))

                username = data.get("username", "").strip()
                password = data.get("password", "").strip()

                if username == AUTH_USERNAME and password == AUTH_PASSWORD:
                    token = secrets.token_hex(24)
                    ACTIVE_SESSIONS[token] = {
                        "username": username,
                        "created_at": time.time()
                    }
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "success",
                        "token": token,
                        "username": username
                    }).encode("utf-8"))
                else:
                    self.send_response(401)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "error",
                        "message": "Tên đăng nhập hoặc mật khẩu không chính xác!"
                    }, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        # API: Đăng xuất
        if parsed.path == "/api/logout":
            auth_header = self.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
                ACTIVE_SESSIONS.pop(token, None)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "Đã đăng xuất"}).encode("utf-8"))
            return

        # API: Lưu nội dung bài viết Markdown & Tiêu đề & Chuyên mục (POST /api/article-content)
        if parsed.path in ["/api/article-content", "/api/articles/update"]:
            if not self.check_authenticated():
                self.send_unauthorized()
                return

            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body.decode("utf-8"))

                old_rel_path = data.get("path", "").strip().replace("\\", "/").lstrip("/")
                new_title = data.get("title", "").strip()
                new_content = data.get("content", "")
                main_cat = data.get("category", "").strip()
                sub_cat = data.get("subcategory")
                if sub_cat:
                    sub_cat = sub_cat.strip()
                    if sub_cat in ["__none__", ""]:
                        sub_cat = None
                filename = data.get("filename", "").strip()

                if not old_rel_path or ".." in old_rel_path or not new_title:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "Thông tin bài viết không hợp lệ"}).encode("utf-8"))
                    return

                header_text, nav_data = load_mkdocs_config()
                cat_structure = get_nav_categories(nav_data)

                if main_cat:
                    if not filename:
                        filename = Path(old_rel_path).name
                    if not filename.endswith(".md"):
                        filename += ".md"

                    if main_cat in cat_structure:
                        cat_info = cat_structure[main_cat]
                        if sub_cat and sub_cat in cat_info["subcategories"]:
                            target_dir = cat_info["subcategories"][sub_cat]["dir_hint"] or f"{cat_info['dir_hint']}/{slugify(sub_cat)}"
                        elif sub_cat:
                            target_dir = f"{cat_info['dir_hint']}/{slugify(sub_cat)}"
                        else:
                            target_dir = cat_info["dir_hint"]
                    else:
                        if sub_cat:
                            target_dir = f"{slugify(main_cat)}/{slugify(sub_cat)}"
                        else:
                            target_dir = slugify(main_cat)

                    new_rel_path = f"{target_dir}/{filename}".replace("\\", "/")
                else:
                    new_rel_path = old_rel_path
                    main_cat = ""
                    sub_cat = None

                ok, msg = update_article(
                    old_rel_path=old_rel_path,
                    new_title=new_title,
                    new_main_cat=main_cat,
                    new_sub_cat=sub_cat,
                    new_rel_path=new_rel_path,
                    new_content=new_content
                )

                if ok:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "success",
                        "message": msg,
                        "path": new_rel_path
                    }, ensure_ascii=False).encode("utf-8"))
                else:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": msg}, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        # API: Đổi tên chuyên mục chính hoặc mục con (POST /api/category-rename)
        if parsed.path in ["/api/category-rename", "/api/categories/rename"]:
            if not self.check_authenticated():
                self.send_unauthorized()
                return

            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body.decode("utf-8"))

                cat_type = data.get("type", "main")
                old_name = data.get("old_name", "").strip()
                new_name = data.get("new_name", "").strip()
                parent_cat = data.get("parent_cat", "").strip() if cat_type == "sub" else None

                ok, msg = rename_category(old_name, new_name, main_cat=parent_cat)
                status_code = 200 if ok else 400

                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success" if ok else "error",
                    "message": msg
                }, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        # API: Tạo chuyên mục mới (POST /api/categories)
        if parsed.path == "/api/categories":
            if not self.check_authenticated():
                self.send_unauthorized()
                return

            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body.decode("utf-8"))

                cat_name = data.get("name", "").strip()
                dir_name = data.get("dir_name", "").strip() or slugify(cat_name)
                initial_title = data.get("initial_title", "").strip() or "Tổng quan"

                if not cat_name:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "Tên chuyên mục không được để trống"}).encode("utf-8"))
                    return

                header_text, nav_data = load_mkdocs_config()
                for item in nav_data:
                    if isinstance(item, dict) and cat_name in item:
                        self.send_response(400)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": f"Chuyên mục '{cat_name}' đã tồn tại!"}).encode("utf-8"))
                        return

                rel_index = f"{dir_name}/index.md"
                full_index = DOCS_DIR / rel_index
                if not full_index.exists():
                    full_index.parent.mkdir(parents=True, exist_ok=True)
                    full_index.write_text(f"---\ntitle: {cat_name}\n---\n\n# {cat_name}\n\nTổng quan nội dung chuyên mục {cat_name}.\n", encoding="utf-8")

                new_cat_entry = {cat_name: [{initial_title: rel_index}]}
                inserted = False
                for idx, item in enumerate(nav_data):
                    if isinstance(item, dict) and list(item.keys())[0].lower() in ["quản trị", "admin"]:
                        nav_data.insert(idx, new_cat_entry)
                        inserted = True
                        break
                if not inserted:
                    nav_data.append(new_cat_entry)

                backup_file = MKDOCS_FILE.with_suffix(".yml.bak")
                backup_file.write_text(MKDOCS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
                new_nav_text = format_full_nav(nav_data)
                MKDOCS_FILE.write_text(header_text + new_nav_text, encoding="utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "message": f"Đã tạo chuyên mục '{cat_name}' thành công!"
                }, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        # API: Tạo bài viết mới
        if parsed.path == "/api/articles":
            if not self.check_authenticated():
                self.send_unauthorized()
                return

            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body.decode("utf-8"))

                title = data.get("title", "").strip()
                main_cat = data.get("category", "").strip()
                sub_cat = data.get("subcategory")
                if sub_cat:
                    sub_cat = sub_cat.strip()
                filename = data.get("filename", "").strip()

                if not title or not main_cat:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "Thiếu tiêu đề hoặc chuyên mục"}).encode("utf-8"))
                    return

                if not filename:
                    filename = f"{slugify(title)}.md"
                if not filename.endswith(".md"):
                    filename += ".md"

                _, nav_data = load_mkdocs_config()
                cat_structure = get_nav_categories(nav_data)

                if main_cat in cat_structure:
                    cat_info = cat_structure[main_cat]
                    if sub_cat and sub_cat in cat_info["subcategories"]:
                        target_dir = cat_info["subcategories"][sub_cat]["dir_hint"] or f"{cat_info['dir_hint']}/{slugify(sub_cat)}"
                    elif sub_cat:
                        target_dir = f"{cat_info['dir_hint']}/{slugify(sub_cat)}"
                    else:
                        target_dir = cat_info["dir_hint"]
                else:
                    if sub_cat:
                        target_dir = f"{slugify(main_cat)}/{slugify(sub_cat)}"
                    else:
                        target_dir = slugify(main_cat)

                rel_md_path = f"{target_dir}/{filename}".replace("\\", "/")
                full_md_path = DOCS_DIR / rel_md_path

                create_article(title, main_cat, sub_cat, rel_md_path, full_md_path)

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "message": f"Đã tạo bài viết '{title}' thành công!",
                    "path": rel_md_path
                }, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_PUT(self):
        """Hỗ trợ RESTful PUT bằng cách định tuyến tương ứng qua do_POST."""
        return self.do_POST()

    def do_DELETE(self):
        """API xóa bài viết hoặc chuyên mục (Yêu cầu đăng nhập)."""
        parsed = urlparse(self.path)
        if parsed.path == "/api/articles":
            if not self.check_authenticated():
                self.send_unauthorized()
                return

            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body.decode("utf-8"))
                rel_path = data.get("path", "").strip()

                if not rel_path:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "Thiếu đường dẫn bài viết"}).encode("utf-8"))
                    return

                ok, msg = delete_article(rel_path)
                status_code = 200 if ok else 400

                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success" if ok else "error",
                    "message": msg
                }, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        if parsed.path in ["/api/categories", "/api/category"]:
            if not self.check_authenticated():
                self.send_unauthorized()
                return

            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body.decode("utf-8"))

                cat_type = data.get("type", "main")
                name = data.get("name", "").strip()
                parent_cat = data.get("parentCat", "").strip() if cat_type == "sub" else None

                ok, msg = delete_category(name, parent_cat=parent_cat)
                status_code = 200 if ok else 400

                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success" if ok else "error",
                    "message": msg
                }, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()


def run_server(port=PORT):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, HandbookAdminHandler)
    print("=" * 65)
    print(f" 🐘 POSTGRESQL HANDBOOK ADMIN SERVER ĐANG CHẠY")
    print(f" 🌐 Địa chỉ Web UI: http://127.0.0.1:{port}/")
    print(f" 🔐 Tài khoản: {AUTH_USERNAME} | Mật khẩu: {AUTH_PASSWORD}")
    print("=" * 65)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng Admin Server.")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port)
