@echo off
chcp 65001 >nul
title 安装 HeyGem (硅基智能数字人)

echo ================================================
echo   HeyGem 本地安装脚本
echo   GitHub: https://github.com/GuijiAI/HeyGem.ai
echo ================================================
echo.

set INSTALL_DIR=C:\HeyGem.ai

REM --- 1. 检查 Git ---
echo [1/5] 检查 Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo [X] Git 未安装
    echo     请下载安装: https://git-scm.com/download/win
    pause
    exit /b 1
)
echo [OK]

REM --- 2. 检查 Docker ---
echo [2/5] 检查 Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [X] Docker 未安装
    echo     请下载 Docker Desktop: https://www.docker.com/products/docker-desktop
    echo     安装后确保 WSL2 已启用
    pause
    exit /b 1
)
echo [OK]

REM --- 3. 检查 WSL2 ---
echo [3/5] 检查 WSL2...
wsl --status >nul 2>&1
if errorlevel 1 (
    echo [!] WSL2 未配置，Docker Desktop 可能无法正常运行
    echo     请以管理员运行: wsl --install
)
echo [OK]

REM --- 4. 克隆仓库 ---
echo [4/5] 克隆 HeyGem 仓库...
if not exist "%INSTALL_DIR%" (
    git clone https://github.com/GuijiAI/HeyGem.ai.git "%INSTALL_DIR%"
    if errorlevel 1 (
        echo [X] 克隆失败，检查网络
        pause
        exit /b 1
    )
) else (
    echo [OK] 已存在 %INSTALL_DIR%，跳过克隆
)

REM --- 5. 拉取镜像并启动 ---
echo [5/5] 拉取 Docker 镜像并启动...
cd /d "%INSTALL_DIR%"
docker-compose pull
docker-compose up -d

REM --- 6. 创建启动脚本 ---
echo 创建启动脚本...
(
echo @echo off
echo chcp 65001 >nul
echo title HeyGem Server
echo cd /d %INSTALL_DIR%
echo docker-compose up -d
echo echo HeyGem 已启动
echo echo API: http://127.0.0.1:3000
echo pause
) > "%INSTALL_DIR%\start_server.bat"

echo.
echo ================================================
echo   HeyGem 安装完成
echo ================================================
echo.
echo 首次启动需要下载模型（约 5-10GB），请耐心等待
echo.
echo 启动方式:
echo   1. 自动: 运行 start_all.bat (JSVOC 全家桶)
echo   2. 手动: 运行 %INSTALL_DIR%\start_server.bat
echo.
echo API 地址: http://127.0.0.1:3000
echo 管理面板: Docker Desktop > Containers > HeyGem
echo.
echo 注意:
echo   - C盘需预留 100GB+ 空间
echo   - 确保 NVIDIA Docker 运行时已安装 (gpu support)
echo   - RTX 5070 Ti 16GB 显存完全够用
echo.
pause
