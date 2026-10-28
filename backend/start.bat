@echo off
chcp 936 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [错误] 虚拟环境不存在，请先运行：uv venv ^&^& uv pip install -e ".[dev]"
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo [启动] Studio System Backend 服务器 http://127.0.0.1:8302
echo [配置] 使用默认 .env
uvicorn app.main:app --host 127.0.0.1 --port 8302

pause
