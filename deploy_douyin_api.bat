@echo off
chcp 65001 >nul
title 部署抖音视频解析API (Douyin_TikTok_Download_API)
cd /d "%~dp0"

set INSTALL_DIR=C:\Douyin_TikTok_Download_API
set PORT=9000

echo ================================================
echo   部署抖音视频解析API
echo   GitHub: Evil0ctal/Douyin_TikTok_Download_API
echo ================================================
echo.

REM 1. 检查依赖
echo [1/5] 检查环境...
git --version >nul 2>&1
if errorlevel 1 (
    echo [X] Git 未安装
    pause
    exit /b 1
)
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python 未安装
    pause
    exit /b 1
)
echo [OK]

REM 2. 克隆仓库
echo [2/5] 克隆仓库...
if not exist "%INSTALL_DIR%" (
    git clone https://github.com/Evil0ctal/Douyin_TikTok_Download_API.git "%INSTALL_DIR%"
    if errorlevel 1 (
        echo [X] 克隆失败
        pause
        exit /b 1
    )
) else (
    echo [OK] 已存在，更新代码...
    cd /d "%INSTALL_DIR%"
    git pull
)

REM 3. 安装依赖
echo [3/5] 安装依赖...
cd /d "%INSTALL_DIR%"
pip install -r requirements.txt -q
echo [OK]

REM 4. 配置端口
echo [4/5] 配置端口 %PORT%...
(
echo # 启动配置
echo PORT=%PORT%
echo ) > "%INSTALL_DIR%\.env"

REM 5. 启动服务
echo [5/5] 启动服务...
echo.
echo ================================================
echo   部署完成
echo   API地址: http://127.0.0.1:%PORT%
echo   文档:    http://127.0.0.1:%PORT%/docs
echo ================================================
echo.
echo 正在启动...
python start.py

pause
