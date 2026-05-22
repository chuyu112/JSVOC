# 部署说明

## 1. 本地开发环境

### 环境要求

- Python 3.11+
- Node.js 20+
- npm
- PostgreSQL 16，可选
- Docker Desktop，可选

### 后端启动

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

### 前端启动

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

访问：

```text
http://127.0.0.1:5173
```

## 2. Docker Compose 环境

项目根目录提供 `docker-compose.yml`，包含：

- postgres
- backend
- frontend

启动：

```powershell
docker compose up --build
```

停止：

```powershell
docker compose down
```

清理 PostgreSQL 数据卷：

```powershell
docker compose down -v
```

说明：

- Docker Compose 已作为联调入口保留。
- 后端容器会等待 PostgreSQL 健康检查通过，执行 Alembic migration 后启动 FastAPI。

## 3. PostgreSQL 环境变量

推荐 PostgreSQL 连接格式：

```text
postgresql+psycopg2://postgres:postgres@localhost:5432/short_video_ops
```

本地 PowerShell：

```powershell
$env:DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/short_video_ops"
```

Docker Compose 示例：

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/short_video_ops
```

PostgreSQL 容器默认变量：

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=short_video_ops
```

## 4. LLM Gateway 环境变量

所有 AI 调用必须经过：

```text
backend/app/llm/llm_gateway.py
```

### mock provider

mock provider 适合本地开发、自动化测试和无模型环境验收。

```powershell
$env:LLM_PROVIDER="mock"
$env:LLM_MODEL="mock-model"
```

### openai_compatible provider

用于接入本地大模型中转层或 OpenAI Compatible API。

```powershell
$env:LLM_PROVIDER="openai_compatible"
$env:LLM_BASE_URL="http://127.0.0.1:11434/v1"
$env:LLM_API_KEY="your-api-key"
$env:LLM_MODEL="your-model-name"
$env:LLM_TIMEOUT_SECONDS="60"
```

请求地址由后端拼接为：

```text
{LLM_BASE_URL}/chat/completions
```

如果 `LLM_BASE_URL` 已经以 `/chat/completions` 结尾，后端会直接使用该地址。

`LLM_TIMEOUT_SECONDS` 控制单次模型请求超时时间，默认 60 秒。模型返回纯 JSON、Markdown JSON 代码块，或在文本中夹带首个 JSON 对象/数组时，Gateway 会尽量解析为结构化数据；解析失败时会保留原始文本到 `data.text`，并继续写入生成历史。

### 环境变量清单

```env
DATABASE_URL=sqlite:///./jpasp_dev.db
API_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
LLM_PROVIDER=mock
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=mock-model
LLM_TIMEOUT_SECONDS=60
```

## 5. 验收命令

后端：

```powershell
cd backend
python -m unittest discover -s tests
```

前端：

```powershell
cd frontend
npm run build
```

## 6. Alembic 数据库迁移

Sprint 8B 起，数据库结构由 Alembic 管理，不再依赖应用启动时自动 `Base.metadata.create_all`。

SQLite 本地开发：

```powershell
cd backend
$env:DATABASE_URL="sqlite:///./jpasp_dev.db"
alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

PostgreSQL 本地环境：

```powershell
cd backend
$env:DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/short_video_ops"
alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Docker Compose 环境：

```powershell
docker compose up --build
```

后端容器会使用 `postgresql+psycopg2://postgres:postgres@postgres:5432/short_video_ops`，等待 PostgreSQL 健康检查通过后执行 `alembic upgrade head`，再启动 FastAPI。

## 7. Docker Compose MVP 联调

Sprint 8C 起，Docker Compose 会启动完整 MVP 依赖：

- `postgres`：PostgreSQL 16，数据库名 `short_video_ops`
- `backend`：FastAPI，连接 Compose 内部 PostgreSQL，并在启动前执行 `alembic upgrade head`
- `frontend`：nginx 服务 Vite 构建产物，监听 `5173`，并将 `/api` 和 `/health` 反代到后端

启动：

```powershell
docker compose up --build
```

访问：

```text
前端：http://localhost:5173
后端健康检查：http://localhost:8000/health
前端反代健康检查：http://localhost:5173/health
```

手动验收：

1. 打开 `http://localhost:5173`。
2. 创建一个项目档案。
3. 从项目详情进入账号包装页面。
4. 使用默认 `LLM_PROVIDER=mock` 生成账号包装。
5. 确认生成结果展示，并可在生成历史中看到 `account_package` 记录。

停止：

```powershell
docker compose down
```

清理 PostgreSQL 数据卷：

```powershell
docker compose down -v
```
