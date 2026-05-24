@echo off
chcp 65001 >nul
title 初始化 FastAPI 后端项目

cd /d D:\JSVOC

echo.
echo ================================
echo 正在初始化 backend
echo ================================
echo.

if not exist backend (
    mkdir backend
)

if not exist backend\app (
    mkdir backend\app
)

if not exist backend\app\api (
    mkdir backend\app\api
)

if not exist backend\app\core (
    mkdir backend\app\core
)

if not exist backend\app\db (
    mkdir backend\app\db
)

if not exist backend\app\models (
    mkdir backend\app\models
)

if not exist backend\app\schemas (
    mkdir backend\app\schemas
)

if not exist backend\app\services (
    mkdir backend\app\services
)

if not exist backend\app\prompts (
    mkdir backend\app\prompts
)

if not exist backend\app\llm (
    mkdir backend\app\llm
)

type nul > backend\app\__init__.py
type nul > backend\app\api\__init__.py
type nul > backend\app\core\__init__.py
type nul > backend\app\db\__init__.py
type nul > backend\app\models\__init__.py
type nul > backend\app\schemas\__init__.py
type nul > backend\app\services\__init__.py
type nul > backend\app\prompts\__init__.py
type nul > backend\app\llm\__init__.py

echo 写入 requirements.txt
(
echo fastapi==0.115.6
echo uvicorn[standard]==0.34.0
echo sqlalchemy==2.0.36
echo alembic==1.14.0
echo psycopg2-binary==2.9.10
echo pydantic==2.10.4
echo pydantic-settings==2.7.0
echo python-dotenv==1.0.1
echo httpx==0.28.1
) > backend\requirements.txt

echo 写入 main.py
(
echo from fastapi import FastAPI
echo from fastapi.middleware.cors import CORSMiddleware
echo.
echo app = FastAPI^(title="AI Short Video Ops API"^)
echo.
echo app.add_middleware^(
echo     CORSMiddleware,
echo     allow_origins=["*"],
echo     allow_credentials=True,
echo     allow_methods=["*"],
echo     allow_headers=["*"],
echo ^)
echo.
echo @app.get^("/health"^)
echo def health_check^(^):
echo     return {"status": "ok"}
echo.
echo @app.get^("/"^)
echo def root^(^):
echo     return {"message": "AI Short Video Ops API is running"}
) > backend\app\main.py

echo 写入 Dockerfile
(
echo FROM python:3.11-slim
echo.
echo WORKDIR /app
echo.
echo COPY requirements.txt .
echo RUN pip install --no-cache-dir -r requirements.txt
echo.
echo COPY . .
echo.
echo EXPOSE 8000
echo.
echo CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
) > backend\Dockerfile

echo.
echo ================================
echo 后端初始化完成
echo ================================
echo.

echo 当前 backend 结构：
dir backend
echo.
dir backend\app

echo.
echo 现在可以运行：
echo cd /d D:\JSVOC\backend
echo pip install -r requirements.txt
echo uvicorn app.main:app --reload
echo.

pause