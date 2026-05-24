# ARCHITECTURE

## 1. 总体架构

Vue 3 前端 -> FastAPI 后端 -> Service 层 -> Prompt 层 -> LLM Gateway -> 大模型供应商 -> PostgreSQL

## 2. 前端架构

前端使用 Vue 3、TypeScript、Vite、Pinia、Vue Router、Element Plus、Axios。

## 3. 后端架构

后端使用 FastAPI、SQLAlchemy、Alembic、Pydantic、PostgreSQL。

后端目录：
- app/api
- app/core
- app/db
- app/models
- app/schemas
- app/services
- app/prompts
- app/llm

## 4. LLM Gateway 契约

所有 AI 生成必须调用 backend/app/llm/llm_gateway.py。

LLM Gateway 输入：
- module_name
- system_prompt
- user_prompt
- output_schema
- temperature
- metadata

LLM Gateway 输出：
- success
- provider
- model
- content
- data
- usage
- latency_ms
- error

MVP 阶段必须支持：

环境变量：
- LLM_PROVIDER
- LLM_BASE_URL
- LLM_API_KEY
- LLM_MODEL

## 5. 数据流

账号包装：前端选择项目 -> 后端读取项目档案 -> 组装 Prompt -> 调用 LLM Gateway -> 保存生成记录 -> 返回前端。

选题生成：前端输入平台和目标 -> 后端读取项目和账号策略上下文 -> 调用 LLM Gateway -> 保存 topics -> 返回前端。
