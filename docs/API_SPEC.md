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

## 6.2 图片生成 / 图生图

POST /api/creation/images/generate/async

请求：

{"project_id": 1, "prompt": "生成一张翡翠手镯产品图", "size": "1536x1024", "quality": "medium", "n": 1}

POST /api/creation/images/edit/async

请求：

{"project_id": 1, "prompt": "@图片1 和 @图片2 一起去 @图片3 吃饭", "reference_images": [{"reference_image_type": "persona", "reference_image_name": "@图片1", "source_image_base64": "...", "source_image_mime": "image/png", "source_image_filename": "person-a.png"}], "size": "1536x1024", "quality": "medium", "n": 1}

说明：

- `reference_image_type` 可选 `persona`、`product`、`location`，分别表示人设、货品、场景参考图。
- `reference_image_name` 用于前端和提示词绑定，建议使用 `@图片1`、`@图片2` 这类全局编号。
- 图生图至少需要 1 张参考图；每类参考图最多 3 张。

## 6.3 视频生成

POST /api/creation/videos/generate/async

请求：

{"project_id": 1, "prompt": "@图片1 跟 @图片2 打架，镜头稳定跟拍，动作激烈但不血腥", "options": {"mode": "reference", "ratio": "16:9", "resolution": "720p", "duration_mode": "seconds", "duration_seconds": 5, "count": 1}, "reference_images": ["data:image/png;base64,..."], "reference_image_names": ["@图片1", "@图片2"], "reference_videos": []}

说明：

- `reference_image_names` 与 `reference_images` 按顺序一一对应，用于把提示词里的 `@图片1`、`@图片2` 绑定到具体参考图。
- 前端只提交选中或被 `@图片N` 引用的素材。
- 上传的本地参考图片/视频会先转存 OSS，再提交给视频模型；未配置 OSS 时不能使用本地上传素材。

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
