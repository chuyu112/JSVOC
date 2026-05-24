# AGENTS.md

## 项目名称

AI 短视频账号策略与内容创作系统

## 项目目标

基于 Vue 3 + FastAPI + PostgreSQL + 本地大模型中转层，开发一个 AI 短视频运营工具。

核心功能分为两大类：

1. 策划：行业、账号、人设、执行、变现、拍摄、直播、私域
2. 创作：选题、文案、解析、获客、呈现形式

MVP 第一版只开发：

1. 项目档案
2. 账号包装方案生成
3. 执行计划生成
4. 选题生成
5. 文案生成
6. 生成历史

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
- 本地 LLM Gateway
- 支持 DeepSeek、通义、豆包、OpenAI、Ollama 等模型供应商
- 所有模型调用必须通过统一 llm_gateway，不允许业务模块直接调用模型 API

部署：
- Docker Compose
- backend、frontend、postgres 三个服务

## 重要文档

开始写代码前必须先阅读：

- docs/PRD.md
- docs/ARCHITECTURE.md
- docs/API_SPEC.md
- docs/DB_SCHEMA.md
- docs/TASKS.md
- docs/ACCEPTANCE.md

## 开发原则

1. 不要一次性开发完整产品，必须按 docs/TASKS.md 的阶段开发。
2. 每个模块先完成可运行的 MVP，再做增强。
3. 后端接口必须有 Pydantic Schema。
4. 数据库变更必须通过 Alembic migration。
5. AI 输出必须尽量使用 JSON Schema 校验。
6. 前端页面要先能跑通主流程，不追求复杂 UI。
7. 所有密钥必须从环境变量读取，不允许写死在代码里。
8. .env 文件不得提交，只提交 .env.example。
9. 每完成一个阶段，需要运行测试或至少运行启动命令验证。
10. 修改代码前先说明计划，修改后说明改了哪些文件、如何运行、下一步建议。

## MVP 主流程

用户创建项目：

- 行业
- 产品/服务
- 个人简介
- 目标客户
- 平台
- 账号阶段

然后依次生成：

1. 账号包装方案
2. 30 天执行计划
3. 选题列表
4. 点击选题生成文案

## 后端目录约定

backend/
├── app/
│   ├── main.py
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── prompts/
│   └── llm/
├── alembic/
├── tests/
├── requirements.txt
└── Dockerfile

## 前端目录约定

frontend/
├── src/
│   ├── api/
│   ├── router/
│   ├── stores/
│   ├── views/
│   ├── components/
│   ├── types/
│   └── main.ts
├── package.json
└── Dockerfile

## 运行命令

后端：

```bash
cd backend
uvicorn app.main:app --reload