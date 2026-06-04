@echo off
chcp 65001 >nul
title JSVOC 后端全家桶启动
cd /d "%~dp0"

set BACKEND_DIR=%CD%\backend
set FRP_DIR=C:\frp
set FRP_CONFIG=%CD%\deploy\frpc.toml
set COZYVOICE_DIR=C:\CozyVoice
set HEYGEM_DIR=C:\HeyGem.ai
set SOCIAL_UPLOAD_DIR=C:\social-auto-upload

echo.
echo ================================================
echo   JSVOC 后端全家桶启动
echo   一键启动所有服务
echo ================================================
echo.

REM --- 1. Python 环境 ---
echo [1/7] Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python 未安装，请安装 3.11+
    pause
    exit /b 1
)
if not exist "%BACKEND_DIR%\.venv" (
    python -m venv "%BACKEND_DIR%\.venv"
)
call "%BACKEND_DIR%\.venv\Scripts\activate.bat" >nul
pip install -r "%BACKEND_DIR%\requirements.txt" -q
echo [OK]

REM --- 2. frp 穿透 ---
echo [2/7] frp 穿透...
if exist "%FRP_DIR%\frpc.exe" (
    tasklist /FI "IMAGENAME eq frpc.exe" 2>nul | find /I "frpc.exe" >nul
    if errorlevel 1 (
        start "frpc" /min cmd /c "cd /d %FRP_DIR% && frpc.exe -c %FRP_CONFIG%"
        timeout /t 2 /nobreak >nul
    )
)
echo [OK]

REM --- 3. CozyVoice ---
echo [3/7] CozyVoice...
if exist "%COZYVOICE_DIR%\api.py" (
    tasklist /FI "WINDOWTITLE eq CozyVoice*" 2>nul | find /I "python" >nul
    if errorlevel 1 (
        start "CozyVoice" /min cmd /c "cd /d %COZYVOICE_DIR% && python api.py --port 50000"
        timeout /t 3 /nobreak >nul
    )
    echo [OK] http://127.0.0.1:50000
) else (
    echo [跳过] 未安装: %COZYVOICE_DIR%
)

REM --- 4. HeyGem ---
echo [4/7] HeyGem...
if exist "%HEYGEM_DIR%\docker-compose.yml" (
    docker ps | findstr "heygem" >nul
    if errorlevel 1 (
        start "HeyGem" /min cmd /c "cd /d %HEYGEM_DIR% && docker-compose up -d"
        timeout /t 5 /nobreak >nul
    )
    echo [OK] http://127.0.0.1:3000
) else (
    echo [跳过] 未安装: %HEYGEM_DIR%
)

REM --- 5. Social Auto Upload ---
echo [5/7] Social Auto Upload...
if exist "%SOCIAL_UPLOAD_DIR%\social_auto_upload" (
    echo [OK] 已安装
) else (
    echo [跳过] 未安装: %SOCIAL_UPLOAD_DIR%
)

REM --- 6. GPU 状态 ---
echo [5/7] GPU...
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>nul || echo [跳过] 无 NVIDIA GPU
echo [OK]

REM --- 6. 数据库 ---
echo [6/7] 数据库...
cd /d "%BACKEND_DIR%"
alembic upgrade head >nul 2>&1
echo [OK]

REM --- 7. FastAPI ---
echo [7/7] FastAPI...
echo.
echo ================================================
echo   服务状态:
echo     FastAPI       http://127.0.0.1:8000
echo     frpc          8.152.2.222:8000
echo     CozyVoice     http://127.0.0.1:50000
echo     HeyGem        http://127.0.0.1:3000
echo     Whisper       内置 (RTX 5070 Ti)
echo     FFmpeg        内置
echo     SocialUpload  库调用 (无需常驻)
echo   按 Ctrl+C 停止
echo ================================================
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

REM 退出清理
taskkill /F /IM frpc.exe >nul 2>&1
echo [OK] 已退出
pause
