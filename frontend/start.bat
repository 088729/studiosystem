@echo off
chcp 936 >nul
cd /d "%~dp0"

if not exist "node_modules" (
    echo [错误] node_modules 不存在，请先运行：npm install
    pause
    exit /b 1
)

echo [启动] Studio System Frontend 开发服务器 http://localhost:5173
npm run dev

pause
