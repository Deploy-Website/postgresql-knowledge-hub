#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL Handbook - Dev Launcher
Khởi động đồng thời cả MkDocs Dev Server (Port 8000) và Admin Server (Port 8001).
"""

import sys
import os
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def get_python_exe():
    venv_py = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable

def get_mkdocs_exe():
    venv_mkdocs = PROJECT_ROOT / ".venv" / "Scripts" / "mkdocs.exe"
    if venv_mkdocs.exists():
        return str(venv_mkdocs)
    return "mkdocs"

def main():
    print("=" * 65)
    print("      🚀 POSTGRESQL HANDBOOK - KHỞI ĐỘNG HỆ THỐNG")
    print("=" * 65)
    print(" 📖 Tài liệu Handbook : http://127.0.0.1:8000/")
    print(" ⚙️ Quản trị nội dung  : http://127.0.0.1:8001/ (hoặc tab 'Quản trị' trên port 8000)")
    print(" 🔐 Tài khoản admin   : vinh.nt | Mật khẩu: Setup12345a@")
    print("=" * 65)
    print(" Nhấn Ctrl+C để dừng toàn bộ hệ thống.\n")

    py_exe = get_python_exe()
    mkdocs_exe = get_mkdocs_exe()
    admin_script = str(PROJECT_ROOT / "admin_server.py")

    processes = []
    try:
        # 1. Khởi chạy MkDocs Serve
        p_mkdocs = subprocess.Popen([mkdocs_exe, "serve"], cwd=str(PROJECT_ROOT))
        processes.append(p_mkdocs)

        # 2. Khởi chạy Admin Server
        p_admin = subprocess.Popen([py_exe, admin_script], cwd=str(PROJECT_ROOT))
        processes.append(p_admin)

        # Giữ tiến trình chạy cho đến khi nhấn Ctrl+C
        while True:
            time.sleep(1)
            for p in processes:
                if p.poll() is not None:
                    print(f"Tiến trình {p.args} đã dừng với mã {p.returncode}")
                    return
    except KeyboardInterrupt:
        print("\n\nĐang tắt các server...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.wait()
        print("✅ Toàn bộ hệ thống đã dừng an toàn.")

if __name__ == "__main__":
    main()
