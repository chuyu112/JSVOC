# API_SPEC

## 1. 通用返回结构

成功返回：

{"success": true, "data": {}, "message": ""}

失败返回：

{"success": false, "data": null, "message": "错误信息"}

## 2. 健康检查

GET /health

返回：

{"status": "ok"}

## 3. 项目档案

POST /api/projects

请求字段：

project_name、industry、sub_industry、product、personal_intro、target_audience、platforms、current_stage。

GET /api/projects 返回项目列表。

GET /api/projects/{project_id} 返回项目详情。

PUT /api/projects/{project_id} 更新项目。

DELETE /api/projects/{project_id} 删除项目。

## 4. 账号包装 + 执行计划一次生成

POST /api/strategy/account-package-execution-plan/generate

请求：

{"project_id": 1, "cycle": "30天", "daily_time": "2小时", "temperature": 0.2}

返回 data 包含：

account_package、execution_plan、context、generation_record_id、provider、model、usage、latency_ms。

说明：

该接口只发起一次 `LLMGateway` 调用，模块名为 `strategy_bundle`，当前使用 `openai_compatible` 渠道和 `gpt-5.5` 模型；账号包装和 30 天执行计划会同时返回。

## 5. 选题生成

POST /api/creation/topics/generate

请求：

{"project_id": 1, "platform": "抖音", "goal": "获客", "count": 20}

返回 data 包含 topics 数组。

每个 topic 包含 title、content_type、platform、goal、user_pain_point、hook、shooting_suggestion、conversion_method、score。

## 6. 文案生成

POST /api/creation/scripts/generate

请求：

{"project_id": 1, "topic_id": 1, "platform": "抖音", "script_type": "聊观点", "duration": "60秒", "goal": "私信获客"}

返回 data 包含：

title、hook、script_content、shot_suggestions、subtitle_points、conversion_script。

## 6.1 热门视频搜索

POST /api/creation/hot-videos/search

请求：

{"project_id": 1, "platform": "抖音", "keyword": "翡翠避坑", "search_focus": "同赛道热门视频", "count": 8}

返回 data 包含：

items、provider、model、usage、sources、latency_ms、generation_record_id。

说明：

- 该接口通过 `LLMGateway` 走联网搜索能力，用于公开视频素材研究和洗稿结构拆解。
- 返回的 `items` 包含标题、来源链接、公开指标、爆点判断、钩子、内容结构、二创角度、洗稿简报和风险提醒。
- 该接口不直接搬运原视频，只输出合规拆解和二创方向。

## 7. 生成历史

GET /api/generation-records

支持查询参数 project_id、module_name。

## 7.1 AI 聊天

POST /api/ai-chat

请求：

{"message": "账号定位怎么做？", "history": [], "web_search": false, "conversation_id": "uuid", "conversation_title": "账号定位"}

返回 data 包含 reply、provider、model、usage、sources、latency_ms、generation_record_id、conversation_id、conversation_title。

GET /api/ai-chat/conversations

返回当前用户的聊天话题列表，包含 conversation_id、title、last_user_message、last_assistant_message、turn_count、created_at、updated_at。

GET /api/ai-chat/conversations/{conversation_id}/history

返回指定聊天话题下的历史对话。旧版没有 conversation_id 的聊天记录统一归入 legacy / 历史聊天。

## 8. LLM 渠道说明

当前代码里实际支持 5 个模型渠道：

- `mock`
- `openai_compatible`
- `anthropic_compatible`
- `moyu`
- `dataeye`

兼容别名：

- `gpt-api`

说明：

- `gpt-api` 不是独立渠道，后端会自动映射为 `openai_compatible`
- `mock` 仅用于测试流程，不走真实模型，也没有真实外部数据
- `openai_compatible` 当前可接 `sub2api` 中转，`http://api.kakayiduo.cloud/v1` 属于这类
- `http://api.kakayiduo.cloud/v1` 当前走的是 GPT，不是 DeepSeek 官方地址
- 即使后续该中转改成绑定域名访问，也仍然归类为同一个 `openai_compatible` 中转渠道
- `anthropic_compatible` 当前用于自用 DeepSeek API，例如 `https://api.deepseek.com/anthropic`

## 9. 当前实际使用配置

当前账号包装测试配置如下：

```env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://api.kakayiduo.cloud/v1
LLM_MODEL=gpt-5.5
LLM_TIMEOUT_SECONDS=180
ACCOUNT_PACKAGE_MODEL=
EXECUTION_PLAN_MODEL=
```

补充说明：

- `ACCOUNT_PACKAGE_MODEL=` 留空，表示账号包装模块回退使用 `LLM_MODEL`
- `EXECUTION_PLAN_MODEL=` 留空，表示执行计划模块回退使用 `LLM_MODEL`
- 这样可以避免被默认的 `deepseek-v4-flash` 模块级配置优先覆盖

## 10. 当前模块渠道约定

当前以下模块统一走 `openai_compatible`：

- 账号包装
- 执行计划
- 文案生成
- 出图

说明：

- 账号包装、执行计划、文案生成通过 `LLMGateway` 走 `openai_compatible`
- 出图也按 `openai_compatible` 处理，只是由 `LLM_BASE_URL` 派生图片接口地址
- 当前出图地址可理解为：
  - `http://api.kakayiduo.cloud/v1/images/generations`
  - `http://api.kakayiduo.cloud/v1/images/edits`
