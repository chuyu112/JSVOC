# JSVOC Multi-User Assets Design

## Goal

把 JSVOC 从“预留 user_id 但实际无用户系统”的单体 MVP，演进为支持真实用户、项目原地保存、策略覆盖、创作资产沉淀、OSS 媒体存储和双层导航的控制台式产品。

## Scope

本次需求覆盖四个相关但可分阶段实现的子系统：

1. 认证与用户归属
2. 项目与策略生命周期
3. 数字资产与 OSS 媒体沉淀
4. 顶栏全局导航 + 项目内二级导航重构

由于四块彼此关联，但改动面较大，本设计按阶段落地，而不是单次大爆炸重构。

## Product Decisions

- 顶栏全局入口固定为：`项目` / `数字资产` / `生成历史`
- `项目`页是全局主工作台，且走“项目列表优先”
- 项目详情页改为项目内二级导航，并按组展示：
  - `策略`：账号包装、执行计划
  - `创作`：选题生成、文案生成
  - `媒体`：图片生成、视频生成
  - `其他`：内容发布
- 项目编辑改成原地保存，不再另存为新版本
- 重新生成策略时，只保留最新一版
- 文案 / 图片 / 视频继续累计保留
- 删除项目后，只删除项目及项目型上下文；数字资产继续保留在用户维度下
- 图片 / 视频文件本体落阿里云 OSS 私有桶，前端通过签名 URL 访问
- 登录体系采用：
  - `users` 存用户主体
  - `auth_accounts` 存登录方式
  - 当前 MVP 先支持 `username` / `email` + `password`
  - 未来可扩展 `phone` / `wechat`

## Architecture

### 1. User Domain

新增用户域：

- `users`
  - 用户主体资料
- `auth_accounts`
  - 与用户关联的认证方式
  - 字段包括：`provider_type`、`provider_key`、`password_hash`、`is_primary`

当前 MVP 的 provider 仅包括：

- `username`
- `email`

后续扩展：

- `phone`
- `wechat`

登录态采用服务端签名 Cookie，会话由后端签发和校验。

### 2. Project Domain

`projects` 保留为工作上下文，不再承载“版本管理”职责。

新规则：

- `PUT /api/projects/{id}` 直接更新当前项目记录
- 项目更新不会自动清理 topics / scripts / assets
- 只有当用户重新生成“账号包装/执行计划”时，才清理旧策略数据

### 3. Strategy Lifecycle

策略类数据包括：

- `account_strategy_contexts`
- 对应模块的 `generation_records`

新规则：

- 每次重新生成策略前，先删除旧 `account_strategy_context`
- 同时删除旧策略相关 `generation_records`
- 最终只保留最新一版策略结果

### 4. Digital Assets Domain

新增 `digital_assets` 聚合表，统一承载用户资产入口。

资产类型：

- `script`
- `image`
- `video`

核心字段：

- `user_id`
- `asset_type`
- `source_project_id`（可空）
- `project_snapshot`
- `title`
- `preview_text`
- `generation_record_id`
- `oss_object_key`
- `mime_type`
- `file_size`
- `asset_metadata`
- `created_at`

删除项目后：

- `source_project_id` 可以失效或置空
- `project_snapshot` 保留原项目名称 / 行业 / 产品等快照
- 资产仍可在 `数字资产` 中按用户维度查看

### 5. Media Storage

图片 / 视频不再只存在模型返回 JSON 中。

新流程：

1. 生成图片/视频结果
2. 后端拉取或接收二进制内容
3. 上传到阿里云 OSS 私有桶
4. 数据库只保存对象键、元数据和可签名访问的信息

前端访问流程：

1. 请求资产详情
2. 后端生成临时签名 URL
3. 前端使用签名 URL 预览或下载

### 6. Navigation Language

视觉风格参考阿里云控制台系：

- 浅色背景
- 白色卡片
- 统一描边和圆角
- 低饱和强调色
- 弱化多彩功能按钮

目标不是逐像素模仿，而是采用其“企业控制台工作台”的组织语言。

## Delivery Phases

### Phase 1

- 用户与认证基础
- 注册 / 登录 / 登出 / 当前用户接口
- 项目原地保存，移除另存逻辑

### Phase 2

- 项目归属真正绑定到当前用户
- 各业务接口按用户过滤
- 策略重生成覆盖旧策略记录

### Phase 3

- `digital_assets` 建模
- 文案资产沉淀
- 删除项目后保留资产

### Phase 4

- 图片 / 视频接入阿里云 OSS 私有桶
- 签名 URL 访问

### Phase 5

- 顶栏全局导航
- 项目详情分组式二级导航
- `数字资产` 页面

## Risks

- 若直接一次性强制所有接口鉴权，现有测试和前端流程会大面积失效
- 若不新增独立资产域，只靠 `generation_records` 承接“数字资产”，后续检索和项目删除语义会变脆弱
- 若 OSS 设计为公开读，会简化开发，但与正式产品安全目标冲突

## Recommended Implementation Order

先打基础，再接资产，再改界面：

1. 认证基础
2. 项目更新语义修正
3. 用户归属与策略覆盖
4. 数字资产域
5. OSS
6. 导航改版
