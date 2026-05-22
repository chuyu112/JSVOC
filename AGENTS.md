# AGENTS.md

## 项目名称
AI 短视频账号策略与内容创作系统

## 项目目标
基于 Vue 3 + FastAPI + PostgreSQL + 本地大模型中转层，开发一个 AI 短视频运营工具。

核心功能分为两大类：

1. 策划：行业、账号、人设、执行、变现、拍摄、直播、私域

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
- 支持 mock provider
- 支持 OpenAI Compatible API
- 所有 AI 调用必须经过 backend/app/llm/llm_gateway.py

## 重要文档

开始写代码前必须阅读：

- docs/PRD.md
- docs/ARCHITECTURE.md
- docs/API_SPEC.md
- docs/DB_SCHEMA.md
- docs/TASKS.md
- docs/ACCEPTANCE.md

## 开发原则

1. 按 docs/TASKS.md 分 Sprint 开发。
7. 每完成一个 Sprint，需要说明修改文件、启动方式和验证方式。

## MVP 主流程

用户创建项目，然后生成账号包装方案、执行计划、选题列表、文案，并查看生成历史。
