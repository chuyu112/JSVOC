# LLM Gateway 频道说明

本文档用于记录当前项目里的模型渠道分类、用途和当前实际使用方式。

## 当前支持的渠道

当前代码里支持 5 个渠道：

- `mock`
- `openai_compatible`
- `anthropic_compatible`
- `moyu`
- `dataeye`

补充：

- `gpt-api` 只是兼容别名，不是独立渠道
- 代码会把 `gpt-api` 自动映射成 `openai_compatible`

## 各渠道用途

### 1. `mock`

用途：

- 用来测试接口流程
- 不走真实模型
- 没有真实外部数据返回

典型配置：

```env
LLM_PROVIDER=mock
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=mock-model
```

### 2. `openai_compatible`

用途：

- 走 OpenAI 兼容协议
- 当前用于接 `sub2api` 中转

当前确认的中转地址：

```text
http://api.kakayiduo.cloud/v1
```

说明：

- 这个地址当前走的是 GPT，不是 DeepSeek 官方
- 后续如果换成绑定域名访问，也仍然可以视为同一个中转渠道
- 只要本质上还是这条 OpenAI-compatible 中转链路，就归类为 `openai_compatible`

当前实际配置示例：

```env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://api.kakayiduo.cloud/v1
LLM_MODEL=gpt-5.5
LLM_TIMEOUT_SECONDS=180
ACCOUNT_PACKAGE_MODEL=
EXECUTION_PLAN_MODEL=
```

### 3. `anthropic_compatible`

用途：

- 走 Anthropic 兼容协议
- 当前用于自用 DeepSeek API

典型配置：

```env
LLM_PROVIDER=anthropic_compatible
LLM_BASE_URL=https://api.deepseek.com/anthropic
```

说明：

- 这是 DeepSeek 官方 Anthropic 兼容入口
- 后端会自动拼成最终请求地址：

```text
https://api.deepseek.com/anthropic/v1/messages
```

### 4. `moyu`

用途：

- 中转渠道
- 复用 OpenAI-compatible 请求格式

### 5. `dataeye`

用途：

- 中转渠道
- 复用 OpenAI-compatible 请求格式

## 模块覆盖规则

如果希望账号包装和执行计划直接跟随主模型，不被模块默认值覆盖，配置应写成：

```env
ACCOUNT_PACKAGE_MODEL=
EXECUTION_PLAN_MODEL=
```

说明：

- 留空表示回退使用 `LLM_MODEL`
- 这样可以避免被默认的 `deepseek-v4-flash` 抢先覆盖

## 当前理解结论

- `http://api.kakayiduo.cloud/v1` 归类为 `openai_compatible`
- 这条链路当前走 GPT
- 它不是 DeepSeek 官方地址
- DeepSeek 自用 API 归类在 `anthropic_compatible`

## 当前模块统一约定

当前这 4 个业务模块统一按 `openai_compatible` 处理：

- 账号包装
- 执行计划
- 文案生成
- 出图

当前统一配置基线：

```env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://api.kakayiduo.cloud/v1
LLM_MODEL=gpt-5.5
ACCOUNT_PACKAGE_MODEL=
EXECUTION_PLAN_MODEL=
```

模块说明：

- 账号包装：走 `LLMGateway` 的 `openai_compatible`
- 执行计划：走 `LLMGateway` 的 `openai_compatible`
- 文案生成：走 `LLMGateway` 的 `openai_compatible`
- 出图：同样走 `openai_compatible`，只是请求地址会从 `LLM_BASE_URL` 派生为图片接口

出图接口派生规则：

```text
http://api.kakayiduo.cloud/v1/images/generations
http://api.kakayiduo.cloud/v1/images/edits
```

补充：

- 这 4 个模块当前都不按 `anthropic_compatible` 写
- 这 4 个模块当前也不按 `moyu`、`dataeye` 单独写
