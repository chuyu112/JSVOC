# AI 短视频账号策略与内容创作系统

## 项目简介

这是一个基于 Vue 3 + FastAPI + PostgreSQL + 本地大模型中转层的 AI 短视频运营工具。

系统面向短视频账号运营场景，帮助用户围绕一个项目档案完成账号包装、执行计划、选题、文案和生成历史管理。所有 AI 生成请求都必须经过后端 `backend/app/llm/llm_gateway.py`，前端不直接调用大模型。

## MVP 功能列表

v0.1.0-mvp 已实现：

1. 项目档案 CRUD
2. 账号包装方案生成
3. 30 天执行计划生成
4. 短视频选题生成
5. 基于已保存选题的文案生成
6. 生成历史查询

暂不包含：爆款解析、获客内容、呈现形式、直播、私域、变现、多租户权限、自动发布、视频剪辑。

## 技术栈

前端：

- Vue 3
- TypeScript
- Vite
- Pinia
- Vue Router
- Element Plus
- Axios

后端：

- Python 3.11+
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- PostgreSQL

AI 层：

- LLM Gateway
- mock provider
- OpenAI Compatible API

## 本地开发启动方式

### 后端

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

### 前端

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

访问：

```text
http://127.0.0.1:5173
```

## 后端测试命令

```powershell
cd backend
python -m unittest discover -s tests
```

预期结果：

```text
OK
```

## 前端构建命令

```powershell
cd frontend
npm run build
```

预期结果：

```text
✓ built
```

Vite 可能提示 chunk size 警告，当前不影响 MVP 构建通过。

## mock 模型运行方式

mock provider 是默认模型提供方，适合本地开发和验收。

PowerShell 示例：

```powershell
$env:LLM_PROVIDER="mock"
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

mock provider 会返回可用的账号包装、执行计划、选题和文案示例，并写入 `generation_records`。

## openai_compatible 模型配置说明

当需要接入本地大模型中转层或 OpenAI Compatible API 时，配置以下环境变量：

```powershell
$env:LLM_PROVIDER="openai_compatible"
$env:LLM_BASE_URL="http://127.0.0.1:11434/v1"
$env:LLM_API_KEY="your-api-key"
$env:LLM_MODEL="your-model-name"
$env:LLM_TIMEOUT_SECONDS="60"
```

后端会调用：

```text
{LLM_BASE_URL}/chat/completions
```

注意：

- 所有 AI 调用仍必须通过 `backend/app/llm/llm_gateway.py`
- 前端不得直接调用模型服务
- 模型返回内容应尽量为纯 JSON，便于后端解析并保存历史记录

补充说明：
- `LLM_BASE_URL` 可以填写服务根地址，例如 `http://127.0.0.1:11434/v1`，后端会拼接 `/chat/completions`；如果已经填写到 `/chat/completions`，后端会直接使用。
- `LLM_TIMEOUT_SECONDS` 控制单次模型请求超时时间，默认 60 秒。

## Docker Compose

```powershell
docker compose up --build
```

Docker Compose 用于完整 MVP 联调，包含 PostgreSQL、FastAPI 后端和 nginx 前端。后端容器会等待 PostgreSQL 健康检查通过，执行 Alembic migration 后启动 FastAPI；前端容器监听 `5173`，并将 `/api` 反代到后端。

## 文档

- `docs/USER_GUIDE.md`：MVP 使用指南
- `docs/DEPLOYMENT.md`：部署和环境变量说明
- `docs/RELEASE_NOTES.md`：版本发布说明

## 数据库迁移

Sprint 8B 起，数据库结构由 Alembic 管理。首次启动或模型结构变更后，先执行迁移：

```powershell
cd backend
alembic upgrade head
```

本地 SQLite 默认使用：

```env
DATABASE_URL=sqlite:///./jpasp_dev.db
```

PostgreSQL 示例：

```powershell
$env:DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/short_video_ops"
cd backend
alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Docker Compose 会等待 PostgreSQL 健康检查通过，并在后端容器启动前执行 `alembic upgrade head`。
