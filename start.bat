@echo off
chcp 65001 > nul
echo Đang khởi động hệ thống PostgreSQL Handbook...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" dev.py
) else (
    python dev.py
)
pause
