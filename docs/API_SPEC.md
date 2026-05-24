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

## 4. 账号包装

POST /api/strategy/account-package/generate

请求：

{"project_id": 1}

返回 data 包含：

account_positioning、persona、account_names、bios、content_columns、trust_design、conversion_path。

## 5. 执行计划

POST /api/strategy/execution-plan/generate

请求：

{"project_id": 1, "cycle": "30天", "daily_time": "2小时"}

返回 data 包含：

cycle、weekly_plan、daily_plan。

## 6. 选题生成

POST /api/creation/topics/generate

请求：

{"project_id": 1, "platform": "抖音", "goal": "获客", "count": 20}

返回 data 包含 topics 数组。

每个 topic 包含 title、content_type、platform、goal、user_pain_point、hook、shooting_suggestion、conversion_method、score。

## 7. 文案生成

POST /api/creation/scripts/generate

请求：

{"project_id": 1, "topic_id": 1, "platform": "抖音", "script_type": "聊观点", "duration": "60秒", "goal": "私信获客"}

返回 data 包含：

title、hook、script_content、shot_suggestions、subtitle_points、conversion_script。

## 8. 生成历史

GET /api/generation-records

支持查询参数 project_id、module_name。
