@echo off
chcp 65001 >nul
title 安装 Social Auto Upload (多平台自动发布)

echo ================================================
echo   Social Auto Upload 安装脚本
 echo   GitHub: dreammis/social-auto-upload
echo ================================================
echo.

set INSTALL_DIR=C:\social-auto-upload

REM --- 1. 检查 Git ---
echo [1/5] 检查 Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo [X] Git 未安装
    echo     https://git-scm.com/download/win
    pause
    exit /b 1
)
echo [OK]

REM --- 2. 检查 Python ---
echo [2/5] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python 未安装
    pause
    exit /b 1
)
echo [OK]

REM --- 3. 克隆仓库 ---
echo [3/5] 克隆仓库...
if not exist "%INSTALL_DIR%" (
    git clone https://github.com/dreammis/social-auto-upload.git "%INSTALL_DIR%"
    if errorlevel 1 (
        echo [X] 克隆失败
        pause
        exit /b 1
    )
) else (
    echo [OK] 已存在
)

REM --- 4. 安装依赖 ---
echo [4/5] 安装依赖...
cd /d "%INSTALL_DIR%"
pip install -e . -q
pip install playwright -q
python -m playwright install chromium

echo [5/5] 创建启动脚本...
(
echo @echo off
 echo chcp 65001 >nul
 echo title Social Auto Upload API
 echo cd /d %INSTALL_DIR%
 echo python -m social_auto_upload.api
 echo pause
) > "%INSTALL_DIR%\start_server.bat"

echo.
echo ================================================
echo   安装完成
echo ================================================
echo.
echo 注意:
echo   - 首次使用各平台需要先手动登录一次
 echo   - Cookie 会保存在 accounts 目录下
echo   - 支持: 抖音、视频号、B站、小红书、快手、TikTok
echo.
pause