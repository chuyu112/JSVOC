# LLM Gateway 渠道说明

本文档记录当前项目里的模型渠道命名、用途和配置方式。所有业务 AI 调用必须经过后端统一网关或对应的图片/视频服务，不允许业务模块直接调用外部模型 API。

## 当前支持的 provider

- `mock`
- `openai_compatible`
- `kakayiduo`
- `anthropic_compatible`
- `moyu`
- `moyu_image`
- `dataeye`
- `seedance`
- `seedance_video`

## 兼容别名

- `gpt-api` -> `openai_compatible`
- `kakayiduo-chat` / `kakayiduo_chat` -> `kakayiduo`
- `kakayiduo-image` / `kakayiduo_image` -> `kakayiduo`
- `moyu-pic` / `moyu_pic` -> `moyu_image`
- `ark-video` / `ark_video` -> `seedance_video`

## kakayiduo

统一 provider 写作：

```env
LLM_PROVIDER=kakayiduo
LLM_BASE_URL=https://api.kakayiduo.cloud/v1
LLM_MODEL=gpt5.5
ACCOUNT_PACKAGE_MODEL=
EXECUTION_PLAN_MODEL=
```

Chat 可选模型：

- `gpt5.5`
- `gpt5.4-mini`

接口地址：

```text
https://api.kakayiduo.cloud/v1/chat/completions
https://api.kakayiduo.cloud/v1/images/generations
https://api.kakayiduo.cloud/v1/images/edits
```

## 其他渠道

`openai_compatible` 用于 Ollama、自建中转或其他 OpenAI-compatible 服务。

`anthropic_compatible` 当前用于 Anthropic-compatible 接口，例如 DeepSeek Anthropic 兼容地址。

`moyu` 用于 Moyu chat-compatible 渠道；`moyu_image` 用于 Moyu 图片渠道。

`seedance_video` 用于 Seedance 视频生成渠道。

## 数据库备份

Docker Compose 会启动 `postgres-backup` 服务，默认每 86400 秒执行一次 `pg_dump`，备份到：

```text
./backups/postgres
```

可通过 `.env` 调整：

```env
POSTGRES_BACKUP_INTERVAL_SECONDS=86400
POSTGRES_BACKUP_RETENTION_DAYS=14
```
