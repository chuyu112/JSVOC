@echo off
chcp 65001 >nul
title JSVOC 本地启动 (后端 + frp 穿透)
cd /d "%~dp0"

set BACKEND_DIR=%CD%\backend
set FRP_DIR=C:\frp
set FRP_CONFIG=%CD%\deploy\frpc.toml

echo.
echo ================================================
echo   JSVOC 本地启动脚本
echo   后端: FastAPI + RTX 5070 Ti
echo   穿透: frp → 8.152.2.222:8000
echo ================================================
echo.

REM --- 1. 检查 frpc ---
echo [1/4] 检查 frp 客户端...
if not exist "%FRP_DIR%\frpc.exe" (
    echo [X] frpc.exe 未找到
    echo     请下载 frp Windows 版到 %FRP_DIR%
    echo     https://github.com/fatedier/frp/releases
    pause
    exit /b 1
)
echo [OK] frpc 就绪

REM --- 2. 启动 frpc（后台）---
echo.
echo [2/4] 启动 frp 穿透...
start "frpc" /min cmd /c "cd /d %FRP_DIR% && frpc.exe -c %FRP_CONFIG%"
timeout /t 2 /nobreak >nul
echo [OK] frpc 已启动（窗口最小化）

REM --- 3. 激活虚拟环境 ---
echo.
echo [3/4] 激活虚拟环境...
call "%BACKEND_DIR%\.venv\Scripts\activate.bat"

REM --- 4. 启动后端 ---
echo.
echo [4/4] 启动 FastAPI 后端...
echo.
echo ================================================
echo   服务状态:
echo     frpc:     运行中（最小化窗口）
echo     Backend:  http://127.0.0.1:8000
echo     公网入口: http://8.152.2.222:8000
echo   按 Ctrl+C 停止后端
echo ================================================
echo.

cd /d "%BACKEND_DIR%"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

REM 清理：关闭 frpc
echo.
echo [*] 正在关闭 frpc...
taskkill /F /IM frpc.exe >nul 2>&1
echo [OK] 已退出

pause
