@echo off
chcp 65001 >nul
title 安装 CozyVoice (阿里通义 TTS + 声音克隆)

echo ================================================
echo   CozyVoice 本地安装脚本
echo   GitHub: https://github.com/FunAudioLLM/CosyVoice
echo ================================================
echo.

set INSTALL_DIR=C:\CozyVoice
set CONDA_ENV=cozyvoice

REM --- 1. 检查 Git ---
echo [1/6] 检查 Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo [X] Git 未安装
    echo     请下载安装: https://git-scm.com/download/win
    pause
    exit /b 1
)
echo [OK]

REM --- 2. 检查 Conda ---
echo [2/6] 检查 Conda...
conda --version >nul 2>&1
if errorlevel 1 (
    echo [X] Conda 未安装
    echo     推荐安装 Miniconda: https://docs.conda.io/en/latest/miniconda.html
    pause
    exit /b 1
)
echo [OK]

REM --- 3. 克隆仓库 ---
echo [3/6] 克隆 CozyVoice 仓库...
if not exist "%INSTALL_DIR%" (
    git clone https://github.com/FunAudioLLM/CosyVoice.git "%INSTALL_DIR%"
    if errorlevel 1 (
        echo [X] 克隆失败，检查网络
        pause
        exit /b 1
    )
) else (
    echo [OK] 已存在 %INSTALL_DIR%，跳过克隆
)

REM --- 4. 创建 Conda 环境 ---
echo [4/6] 创建 Python 环境...
cd /d "%INSTALL_DIR%"
conda env list | findstr "%CONDA_ENV%" >nul
if errorlevel 1 (
    conda create -n %CONDA_ENV% python=3.10 -y
) else (
    echo [OK] 环境 %CONDA_ENV% 已存在
)

echo [5/6] 安装依赖...
call conda activate %CONDA_ENV%
pip install -r requirements.txt -q

REM --- 5. 下载预训练模型 ---
echo [6/6] 下载模型 (约 3GB)...
echo     首次运行时会自动从 ModelScope 下载
echo     模型缓存位置: %%USERPROFILE%%\.cache\modelscope\hub
echo.

REM --- 6. 创建启动脚本 ---
echo 创建启动脚本...
(
echo @echo off
echo chcp 65001 >nul
echo title CozyVoice Server
echo cd /d %INSTALL_DIR%
echo call conda activate %CONDA_ENV%
echo python api.py --port 50000
echo pause
) > "%INSTALL_DIR%\start_server.bat"

echo.
echo ================================================
echo   CozyVoice 安装完成
echo ================================================
echo.
echo 启动方式:
echo   1. 自动: 运行 start_all.bat (JSVOC 全家桶)
echo   2. 手动: 运行 %INSTALL_DIR%\start_server.bat
echo.
echo API 地址: http://127.0.0.1:50000
echo 文档:     http://127.0.0.1:50000/docs
echo.
pause
