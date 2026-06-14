@echo off
chcp 65001 >nul
title JSVOC 后端启动 (RTX 5070 Ti 本地版)
cd /d "%~dp0"

set BACKEND_DIR=%CD%\backend
set PYTHON=python
set PORT=8000
set HOST=0.0.0.0

echo.
echo ================================================
echo   JSVOC 后端启动脚本
echo   模式: 本地部署 / RTX 5070 Ti 加速
echo ================================================
echo.

REM --- 1. 检查 Python ---
echo [1/6] 检查 Python 环境...
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python 未安装或未加入 PATH
    echo     请安装 Python 3.11+ 并勾选 "Add to PATH"
    pause
    exit /b 1
)
for /f "tokens=2" %%a in ('%PYTHON% --version 2^>^&1') do set PYVER=%%a
echo [OK] Python %PYVER%

REM --- 2. 检查 CUDA / GPU ---
echo.
echo [2/6] 检查 GPU / CUDA...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo [!] nvidia-smi 未找到，CUDA 可能未安装
    echo     ASR 将使用 CPU 运行（速度较慢）
    goto :skip_gpu
)

for /f "tokens=*" %%a in ('nvidia-smi --query-gpu=name --format=csv,noheader 2^>nul') do set GPU_NAME=%%a
echo [OK] GPU: %GPU_NAME%

for /f "tokens=*" %%a in ('nvidia-smi ^| findstr "CUDA Version"') do (
    for /f "tokens=3" %%b in ("%%a") do set CUDA_VER=%%b
)
echo [OK] CUDA: %CUDA_VER%

REM 检测 RTX 50 系列
(echo %GPU_NAME% | findstr /i "RTX 50" >nul) && (
    echo [*] 检测到 Blackwell 架构显卡 (RTX 50 系列)
    echo     推荐配置: ASR_MODEL_SIZE=large-v3, ASR_COMPUTE_TYPE=float16
)

:skip_gpu

REM --- 3. 检查 / 创建虚拟环境 ---
echo.
echo [3/6] 检查虚拟环境...
if not exist "%BACKEND_DIR%\.venv" (
    echo [.] 创建虚拟环境...
    %PYTHON% -m venv "%BACKEND_DIR%\.venv"
    if errorlevel 1 (
        echo [X] 虚拟环境创建失败
        pause
        exit /b 1
    )
)
echo [OK] 虚拟环境就绪

REM --- 4. 安装依赖 ---
echo.
echo [4/6] 安装 / 更新依赖...
call "%BACKEND_DIR%\.venv\Scripts\activate.bat"

REM 检查 PyTorch 是否支持 Blackwell
%PYTHON% -c "import torch; cap=torch.cuda.get_device_capability() if torch.cuda.is_available() else (0,0); exit(0 if cap[0]<10 else 0)" >nul 2>&1

REM 升级 pip
%PYTHON% -m pip install --upgrade pip -q

REM 安装 requirements
pip install -r "%BACKEND_DIR%\requirements.txt" -q
if errorlevel 1 (
    echo [X] 依赖安装失败
    pause
    exit /b 1
)

REM 检查 faster-whisper
%PYTHON% -c "import faster_whisper" >nul 2>&1
if errorlevel 1 (
    echo [.] 安装 faster-whisper...
    pip install faster-whisper==1.1.1
)

REM 检查 PyTorch CUDA 是否可用
%PYTHON% -c "import torch; print('PyTorch CUDA:', torch.cuda.is_available())" 2>nul
echo [OK] 依赖就绪

REM --- 5. 检查 .env 配置 ---
echo.
echo [5/6] 检查环境配置...
if not exist "%BACKEND_DIR%\.env" (
    if exist "%CD%\.env" (
        copy "%CD%\.env" "%BACKEND_DIR%\.env" >nul
        echo [OK] 已复制 .env 到 backend
    ) else (
        echo [!] 未找到 .env 文件，使用默认配置
    )
)

REM --- 6. 数据库初始化 ---
echo.
echo [6/6] 初始化数据库...
cd /d "%BACKEND_DIR%"
alembic upgrade head >nul 2>&1
if errorlevel 1 (
    echo [!] Alembic 迁移失败，尝试直接创建表...
    %PYTHON% -c "from app.db.base import init_db; init_db()" >nul 2>&1
)
echo [OK] 数据库就绪

REM --- 启动服务 ---
echo.
echo ================================================
echo   正在启动后端服务...
echo   地址: http://%HOST%:%PORT%
echo   按 Ctrl+C 停止
echo ================================================
echo.

REM 检测是否有 ASR 模型，首次会下载
if not exist "%USERPROFILE%\.cache\huggingface\hub\*whisper*" (
    echo [*] 首次启动：正在下载 Whisper 模型（约 2-3GB）...
    echo     模型将缓存到: %USERPROFILE%\.cache\huggingface\hub
    echo     可设置 WHISPER_MODEL_DIR 环境变量更改路径
    echo.
)

%PYTHON% -m uvicorn app.main:app --reload --host %HOST% --port %PORT%

REM 退出时 deactivate
call deactivate
pause
