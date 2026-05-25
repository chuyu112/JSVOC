# 爆款口播仿写工厂设计

## 目标

在 JSVOC 中新增一个“爆款口播仿写”工作流，帮助用户把抖音爆款口播文案转成适合自己账号、产品和目标客户的原创口播脚本，并为后续一键生成口播视频打基础。

第一版先跑通核心闭环：

```text
手动输入爆款素材 -> 爆点拆解 -> 文案仿写 -> 保存结果 -> 后续进入视频生成
```

## 第一版范围

首版只做抖音场景，但不直接抓取抖音账号最近 30/50/100 条内容。用户手动输入或粘贴爆款素材，平台字段默认选择“抖音”。

首版包含：

- 手动录入爆款文案。
- 可选填写爆款视频链接、账号名、账号主页、封面链接。
- AI 拆解爆款文案结构。
- 基于用户项目/行业/产品/目标客户做文案仿写。
- 将拆解和仿写结果写入生成历史。
- 预留“JSVOC 每日热门搜索”入口，数据源命名为“热点宝”，但首版返回未接入状态。

首版不包含：

- 自动抓取抖音账号最近 30/50/100 条作品。
- 自动下载封面或视频。
- 热点宝真实 API 接入。
- 声音克隆和数字人口播视频的完整新链路。
- 平台批量采集、定时任务、榜单排序。

## 用户流程

1. 用户进入“爆款仿写”页面。
2. 选择“手动输入”。
3. 输入爆款标题、完整口播文案。
4. 可选填写来源链接、账号名、账号主页、封面链接。
5. 点击“拆解爆点”。
6. 系统输出：
   - 开头钩子
   - 内容结构
   - 情绪触发点
   - 信任背书
   - 转化话术
   - 可借鉴点
   - 侵权/洗稿风险提醒
7. 用户选择仿写配置：
   - 项目
   - 口播时长：30 秒、60 秒、90 秒
   - 仿写强度：轻度借鉴、中度仿写、强洗稿
   - 转化目标：涨粉、私信、加微信、直播间、成交
8. 点击“仿写文案”。
9. 系统输出适配用户账号的口播脚本。
10. 用户保存结果，后续可以进入现有视频生成链路。

## 页面设计

新增前端页面：

```text
/hot-copy
```

页面采用工作台布局，不做营销落地页。

顶部为入口标签：

- 手动输入
- 抖音链接识别（预留，首版可显示“下一步接入”）
- 每日热门搜索（热点宝预留）

主体为三栏：

- 左栏：爆款素材录入
- 中栏：爆点拆解结果
- 右栏：仿写配置和生成结果

底部操作：

- 保存素材
- 拆解爆点
- 仿写文案
- 去生成视频

“每日热门搜索”首版显示：

```text
热点宝数据源预留中，当前先使用手动输入爆款文案。
```

## 文案拆解输出

后端通过统一 `llm_gateway` 调用模型，模块名建议为：

```text
hot_copy_analysis
```

输出 JSON：

```json
{
  "hook": "开头钩子",
  "structure": ["结构步骤"],
  "emotion_triggers": ["情绪触发点"],
  "trust_builders": ["信任背书"],
  "conversion_points": ["转化话术"],
  "rewrite_angles": ["可仿写角度"],
  "risk_notes": ["风险提醒"]
}
```

## 文案仿写输出

后端通过统一 `llm_gateway` 调用模型，模块名建议为：

```text
hot_copy_rewrite
```

输出 JSON：

```json
{
  "title": "标题",
  "hook": "前 3 秒钩子",
  "script": "完整口播文案",
  "rhythm": ["分段节奏"],
  "subtitle_points": ["字幕重点"],
  "shot_suggestions": ["镜头建议"],
  "conversion_script": "结尾转化话术",
  "risk_notes": ["风险提醒"]
}
```

仿写要求：

- 必须结合项目档案、产品/服务、个人简介和目标客户。
- 不能逐句替换原文案。
- 要保留“结构”和“情绪逻辑”，替换成用户自己的行业和表达。
- 强洗稿模式也要输出风险提醒，避免直接复制原内容。

## 数据模型

新增表 `hot_copy_materials`：

```text
id
user_id
project_id nullable
platform
source_type              manual / douyin_link / redianbao
source_url nullable
account_name nullable
account_home_url nullable
cover_url nullable
title
original_script
metrics_json nullable
analysis_json nullable
created_at
updated_at
```

新增表 `hot_copy_rewrites`：

```text
id
material_id
user_id
project_id nullable
rewrite_mode             light / medium / strong
duration                 30s / 60s / 90s
conversion_goal
input_json
output_json
generation_record_id nullable
created_at
```

## API 设计

```text
POST /api/hot-copy/materials/manual
```

保存手动输入的爆款素材。

```text
GET /api/hot-copy/materials
```

读取当前用户的爆款素材列表。

```text
GET /api/hot-copy/materials/{material_id}
```

读取素材详情。

```text
POST /api/hot-copy/materials/{material_id}/analyze
```

拆解爆点，写入 `analysis_json`，同时写入生成历史。

```text
POST /api/hot-copy/materials/{material_id}/rewrite
```

基于素材和用户项目仿写文案，写入 `hot_copy_rewrites` 和生成历史。

```text
POST /api/hot-copy/search/redianbao
```

热点宝预留接口。首版返回：

```json
{
  "success": false,
  "data": null,
  "message": "热点宝数据源暂未接入，请先使用手动输入。"
}
```

## Provider 预留

后端保留 provider 边界：

```text
manual_provider
douyin_link_provider
redianbao_provider
```

首版只实现 `manual_provider`。`redianbao_provider` 保留接口和错误返回，不做真实请求。

后续接热点宝时，provider 输出统一为：

```json
{
  "platform": "抖音",
  "source_type": "redianbao",
  "source_url": "来源链接",
  "account_name": "账号名",
  "account_home_url": "账号主页",
  "cover_url": "封面",
  "title": "标题",
  "original_script": "文案",
  "metrics": {
    "like_count": 0,
    "comment_count": 0,
    "share_count": 0,
    "collect_count": 0
  }
}
```

## 生成历史

新增历史模块名：

```text
hot_copy_analysis
hot_copy_rewrite
```

历史记录需要保存：

- 输入素材
- 项目上下文
- 拆解或仿写输出
- provider/model
- 成功/失败状态
- 失败原因

## 错误处理

- 爆款文案为空：前端阻止提交，提示“请输入爆款口播文案”。
- 未选择项目也允许拆解；仿写时建议选择项目，否则要求手动填写行业、产品和目标客户。
- LLM 返回非 JSON：后端保存失败记录，前端展示“模型返回格式异常，请重试”。
- 热点宝入口：首版明确提示未接入，不允许用户误以为搜索失败。
- 强洗稿模式：结果中必须带风险提醒。

## 验收标准

- 用户可以手动保存一条抖音爆款文案。
- 用户可以对保存的爆款文案做爆点拆解。
- 用户可以选择项目后生成一条仿写文案。
- 拆解和仿写都能在生成历史中看到。
- 热点宝入口存在，但明确显示未接入。
- 所有 AI 调用必须通过 `llm_gateway`。
- 数据库变更通过 Alembic migration。
- 前端页面在桌面和移动端都能完整操作，不出现按钮被 loading 挡住的问题。

## 后续阶段

第二阶段：

- 抖音链接识别。
- 从链接中尽量提取账号、封面、标题和文案。
- 识别失败时回退到手动补全。

第三阶段：

- 接入热点宝热门搜索。
- 支持每日搜索和爆款池。
- 支持按行业、关键词、平台、互动数据筛选。

第四阶段：

- 选择仿写结果后一键进入视频生成。
- 复用现有生视频任务和生成历史。
- 后续再接个人声音和数字人口播能力。
