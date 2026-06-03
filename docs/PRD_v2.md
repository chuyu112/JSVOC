# JSVOC 产品需求文档 (PRD)

> **版本**: v1.0  
> **日期**: 2026-06-03  
> **状态**: 已上线运行中  
> **定位**: AI 短视频账号策略与内容创作系统

---

## 1. 产品概述

### 1.1 产品定位

JSVOC 是一个面向翡翠行业中小商家的 **AI 短视频获客工作台**，帮助没有专业运营团队的翡翠小老板快速完成账号定位、人设包装、内容策划、文案创作和多媒体生成，实现低成本（月成本 500-1000 元以内）的短视频获客。

### 1.2 目标用户

- **核心用户**: 翡翠行业中小商家老板（四会等翡翠集散地）
- **用户画像**: 
  - 手上有货品图片/短视频素材
  - 不会拍短视频、不会写文案
  - 不想请专业运营团队（成本敏感）
  - 以朋友圈和档口为基础获客场景
  - 抖音/视频号/小红书是增量获客渠道

### 1.3 核心价值主张

1. **降低门槛**: 不懂运营也能做出专业级短视频内容
2. **效率提升**: AI 一键生成账号包装、执行计划、选题、文案
3. **成本可控**: 月成本控制在 500-1000 元以内
4. **效果可见**: 快速做出演示内容，看到效果后再持续投入

---

## 2. 技术架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Frontend)                         │
│  Next.js 16 + React 19 + TypeScript + Tailwind CSS v4       │
│  Framer Motion + Phosphor Icons                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        后端 (Backend)                          │
│  FastAPI + SQLAlchemy + Alembic + Pydantic + PostgreSQL     │
│  Python 3.11+                                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        AI 层 (AI Layer)                        │
│  LLM Gateway → 多模型渠道 (OpenAI/DeepSeek/Anthropic/等)    │
│  图像生成 (GPT-image)                                        │
│  视频生成 (Seedance/Ark)                                   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Next.js | 16.2.6 | 全栈框架，App Router |
| React | 19.2.4 | UI 框架 |
| TypeScript | 5.x | 类型安全 |
| Tailwind CSS | 4.x | 样式框架 |
| Framer Motion | 12.38.0 | 动画效果 |
| Phosphor Icons | 2.1.10 | 图标库 |

### 2.3 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | - | Web 框架 |
| SQLAlchemy | - | ORM |
| Alembic | - | 数据库迁移 |
| Pydantic | - | 数据校验 |
| PostgreSQL | - | 主数据库 |
| SQLite | - | 本地开发 |

### 2.4 AI 模型渠道

| 渠道 | 用途 | 说明 |
|------|------|------|
| openai_compatible | 文本生成、账号包装、执行计划、文案 | 通过中转 API |
| anthropic_compatible | DeepSeek API | 兼容模式 |
| seedance | 视频生成 | Seedance/Ark 视频 |
| mock | 本地测试 | 返回示例数据 |

---

## 3. 功能模块

### 3.1 模块总览

```
┌─────────────────────────────────────────────────────────────────┐
│                         全局导航                                  │
│  AI爆款仿写 │ AI生图 │ AI生视频 │ 数字资产 │ AI聊天 │ 人设档案 │ 生成记录 │ 设置 │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐          ┌──────────┐          ┌──────────┐
   │ 内容创作  │          │ 多媒体生成 │          │ 账号管理  │
   │ (全局)   │          │ (全局)    │          │ (项目内)  │
   └─────────┘          └──────────┘          └──────────┘
   - AI爆款仿写          - AI生图              - 账号包装
   - AI聊天              - AI生视频            - 执行计划
   - 数字资产            - 数字人(预留)        - 选题生成
   - 生成记录                                  - 文案生成
                                               - 内容发布(预留)
```

---

## 4. 功能详细设计

### 4.1 认证与授权

#### 4.1.1 用户注册
- **入口**: `/login`
- **字段**: 显示名称、用户名、邮箱、密码
- **流程**: 注册 → 自动登录 → 跳转首页

#### 4.1.2 用户登录
- **入口**: `/login`
- **方式**: 用户名/邮箱 + 密码
- **会话**: Cookie-based (httponly, samesite)
- **跳转**: 支持 `?redirect=` 参数

#### 4.1.3 权限控制
- 未登录用户只能访问登录页
- 登录后自动跳转到 `/projects`
- 管理员 (`chuyu111`) 可访问设置页的 LLM 渠道管理

### 4.2 人设档案 (Projects)

#### 4.2.1 项目列表
- **路由**: `/projects`
- **功能**:
  - 展示所有项目卡片
  - 统计概览（项目数、平台数、阶段数）
  - 新建项目入口
  - 删除项目（确认弹窗）

#### 4.2.2 新建项目
- **路由**: `/projects/new`
- **字段**:
  - 项目名称（必填）
  - 行业（固定：珠宝）
  - 细分行业（固定：翡翠）
  - 产品/服务（必填）
  - 个人简介（必填）
  - 目标客户（必填）
  - 发布平台（多选：抖音/视频号/快手/小红书）
  - 当前阶段（单选：冷启动期/成长期/成熟期/衰退期）

#### 4.2.3 项目详情
- **路由**: `/projects/{id}`
- **功能**:
  - 展示项目基本信息（可编辑）
  - 账号包装预览（如已生成）
  - 工作流导航：账号包装 → 执行计划 → 选题生成 → 内容发布

### 4.3 账号包装 (Account Package)

#### 4.3.1 功能描述
基于项目档案，AI 一键生成完整的账号包装方案。

#### 4.3.2 路由
- `/projects/{id}/account-package`

#### 4.3.3 生成内容
| 字段 | 说明 |
|------|------|
| 账号核心定位 | 一句话定位 |
| 人设包装 | 人设标签、风格描述 |
| 目标用户画像 | 年龄、性别、消费特征 |
| 账号名称建议 | 3-5 个备选名称 |
| 各平台简介 | 抖音/视频号/快手/小红书适配 |
| 内容栏目 | 栏目名称 + 定位 |
| 信任背书 | 信任点设计 |
| 转化路径 | 从内容到成交的路径 |
| 30 天起号建议 | 阶段性目标 |

#### 4.3.4 平台适配策略
| 平台 | 策略重点 |
|------|----------|
| 抖音 | 强钩子、强转化 |
| 视频号 | 信任感、真实感 |
| 快手 | 真实接地气 |
| 小红书 | 审美、种草、避坑 |

#### 4.3.5 API
```
POST /api/strategy/account-package-execution-plan/generate
Body: { project_id, cycle, daily_time, temperature }
```

### 4.4 执行计划 (Execution Plan)

#### 4.4.1 功能描述
基于账号包装方案，生成 30 天执行计划。

#### 4.4.2 路由
- `/projects/{id}/execution-plan`

#### 4.4.3 生成内容
- 每周目标
- 每日任务
- 内容方向
- 拍摄任务
- 发布建议
- 复盘指标

#### 4.4.4 API
- 与账号包装共用接口，一次生成同时返回

### 4.5 选题生成 (Topics)

#### 4.5.1 功能描述
基于项目档案和账号策略，批量生成短视频选题。

#### 4.5.2 路由
- `/projects/{id}/topics`

#### 4.5.3 生成参数
- 平台（抖音/视频号/快手/小红书）
- 内容目标（获客/涨粉/信任建立/成交转化）
- 选题数量（10/20/30）
- 内容形式（视频口播/视频脚本/图片）

#### 4.5.4 选题卡片信息
- 标题
- 平台
- 内容类型
- 用户痛点
- 开头钩子
- 拍摄建议
- 转化方式
- 推荐评分（1-5 星）
- 多维评分（ER/SR/HP/QL/NA/AB/SAT）

#### 4.5.5 API
```
POST /api/creation/topics/generate
Body: { project_id, platform, goal, count }
```

### 4.6 文案生成 (Scripts)

#### 4.6.1 功能描述
基于选题，生成可直接拍摄的短视频文案。

#### 4.6.2 路由
- `/projects/{id}/topics/{topicId}/script`

#### 4.6.3 生成参数
- 写法（聊观点/讲故事/晒过程/教知识/辩认知/纯带货）
- 平台
- 视频时长（15秒/30秒/60秒/90秒/120秒/180秒/300秒）
- 转化目标

#### 4.6.4 输出内容
- 标题
- 开头钩子
- 正文口播
- 镜头建议
- 字幕重点
- 结尾转化
- 评论区引导
- 私信引导
- 多维评分（ER/SR/HP/QL/NA/AB/SAT）

#### 4.6.5 API
```
POST /api/creation/scripts/generate
Body: { project_id, topic_id, platform, script_type, duration, goal }
```

### 4.7 AI 爆款仿写 (Hot Copy)

#### 4.7.1 功能描述
分析爆款短视频的结构，并基于翡翠场景进行仿写。

#### 4.7.2 路由
- `/hot-copy`

#### 4.7.3 核心功能
1. **素材录入**
   - 手动输入：标题、文案、账号名、链接
   - 链接解析：输入抖音/视频号链接自动提取文案
   - 视频上传：上传视频文件自动转写
   - 抖音主页导入：导入对标账号主页视频

2. **结构分析**
   - 开头钩子
   - 内容结构
   - 爆点情绪
   - 信任支撑
   - 转化设计
   - 风险提醒
   - 可仿写简报

3. **仿写生成**
   - 轻度仿写（保留结构，替换内容）
   - 中度仿写（调整结构，翡翠场景）
   - 深度仿写（重构表达，原创风格）

4. **场景生成**
   - 基于仿写结果生成分镜图
   - 基于仿写结果生成视频

#### 4.7.4 API
```
POST /api/hot-copy/materials/manual       # 手动录入
POST /api/hot-copy/materials/auto         # 链接解析
POST /api/hot-copy/materials/auto-upload  # 视频上传
POST /api/hot-copy/analysis               # 结构分析
POST /api/hot-copy/rewrite                # 仿写
POST /api/hot-copy/scenes                  # 场景生成
POST /api/hot-copy/generate-video          # 视频生成
```

### 4.8 AI 生图 (Image Generation)

#### 4.8.1 功能描述
基于文本描述或参考图生成图片，支持文生图和图生图。

#### 4.8.2 路由
- `/images`

#### 4.8.3 生成模式
1. **文生图**: 输入描述文本生成图片
2. **图生图**: 上传参考图 + 编辑描述生成新图

#### 4.8.4 参数配置
- 尺寸：1024x1536/1024x1024/1536x1024/2048x1152/1152x2048/自动
- 质量：高清/标准/快速/自动
- 数量：1-4 张
- 参考图类型：人设参考图/货品参考图/场景参考图

#### 4.8.5 API
```
POST /api/images/generate    # 文生图
POST /api/images/edit       # 图生图
POST /api/images/enhance-prompt  # 提示词增强
```

### 4.9 AI 生视频 (Video Generation)

#### 4.9.1 功能描述
基于文本描述或参考图/视频生成短视频。

#### 4.9.2 路由
- `/videos`

#### 4.9.3 模型支持
- **Seedance 2.0**: 标准模式，支持 480p/720p/1080p
- **Seedance 2.0 Fast**: 快速模式，支持 480p/720p

#### 4.9.4 参数配置
- 模型选择
- 宽高比：16:9/9:16/1:1/4:3/3:4
- 分辨率：480p/720p/1080p
- 时长模式：秒数/智能
- 时长：5-10 秒
- 数量：1-4 个
- 是否带声音
- 参考媒体：图片/视频/音频

#### 4.9.5 API
```
POST /api/videos/generate    # 提交生成任务
GET  /api/videos/models      # 获取可用模型
POST /api/videos/enhance-prompt  # 提示词增强
```

### 4.10 AI 聊天 (AI Chat)

#### 4.10.1 功能描述
通用 AI 对话助手，支持联网搜索，可咨询短视频运营、账号策略、选题、文案、提示词、生图、生视频等问题。

#### 4.10.2 路由
- `/ai-chat`

#### 4.10.3 功能特性
- 多轮对话
- 联网搜索（可选）
- 对话历史管理
- 新话题创建

#### 4.10.4 API
```
POST /api/ai-chat                    # 发送消息
GET  /api/ai-chat/conversations      # 获取对话列表
GET  /api/ai-chat/conversations/{id}  # 获取对话历史
```

### 4.11 数字资产 (Digital Assets)

#### 4.11.1 功能描述
集中管理用户生成的所有数字内容资产。

#### 4.11.2 路由
- `/assets`

#### 4.11.3 资产类型
- 文案 (script)
- 图片 (image)
- 视频 (video)

#### 4.11.4 功能
- 按类型筛选
- 查看资产详情
- 复制提示词
- 查看预览

### 4.12 生成记录 (History)

#### 4.12.1 功能描述
查看所有 AI 生成任务的历史记录。

#### 4.12.2 路由
- `/history`（全局）
- `/projects/{id}/history`（项目内）

#### 4.12.3 记录类型
- 账号包装 (strategy_bundle)
- 选题 (topics)
- 文案 (script)
- 图片 (image_generate/image_edit)
- 视频 (video_generate)
- AI 聊天 (ai_chat)

#### 4.12.4 记录信息
- 模块名称
- 输入内容
- 输出内容
- 模型供应商
- 模型名称
- Token 消耗
- 响应耗时
- 创建时间
- 状态（成功/失败）

### 4.13 设置 (Settings)

#### 4.13.1 功能描述
用户个性化设置和系统管理。

#### 4.13.2 路由
- `/settings`

#### 4.13.3 功能
- **主题切换**: 7 种翡翠主题色（阳绿/帝王绿/苹果绿/紫罗兰/黄翡/红翡/墨翠）
- **LLM 渠道管理**（仅管理员）:
  - 创建/编辑/删除渠道
  - 按用途分类（聊天/生图/生视频）
  - 测试渠道连通性
  - 激活/停用渠道

### 4.14 积分系统 (Credits)

#### 4.14.1 功能描述
基于积分的用量控制系统。

#### 4.14.2 积分消耗
| 操作 | 积分消耗 |
|------|----------|
| 账号包装 + 执行计划 | 根据配置 |
| 选题生成 | 根据配置 |
| 文案生成 | 根据配置 |
| 图片生成 | 根据配置 |
| 视频生成 | 按秒计费（Seedance 2.0: ~7元/15秒） |
| AI 聊天 | 根据配置 |

#### 4.14.3 API
```
GET  /api/credits/balance    # 获取积分余额
POST /api/credits/consume    # 消耗积分（内部）
```

---

## 5. 数据模型

### 5.1 核心实体关系

```
┌─────────────┐       ┌─────────────────────┐       ┌─────────────┐
│    User     │       │      Project        │       │   Topic     │
├─────────────┤       ├─────────────────────┤       ├─────────────┤
│ id          │◄─────│ id                  │       │ id          │
│ username    │       │ user_id             │       │ project_id  │
│ display_name│       │ project_name        │       │ title       │
│ email       │       │ industry            │       │ platform    │
│ password    │       │ sub_industry        │       │ goal        │
│ credit      │       │ product             │       │ score       │
└─────────────┘       │ personal_intro      │       │ topic_data  │
                      │ target_audience     │       └─────────────┘
                      │ platforms           │             │
                      │ current_stage       │             ▼
                      └─────────────────────┘       ┌─────────────┐
                                │                   │   Script    │
                                ▼                   ├─────────────┤
                      ┌─────────────────────┐       │ id          │
                      │ AccountStrategyCtx  │       │ project_id  │
                      ├─────────────────────┤       │ topic_id    │
                      │ id                  │       │ title       │
                      │ project_id          │       │ script_type │
                      │ account_positioning │       │ platform    │
                      │ persona             │       │ content     │
                      │ target_user_profile │       │ shot_suggestions│
                      │ ...                 │       │ conversion  │
                      └─────────────────────┘       └─────────────┘
```

### 5.2 数据库表清单

| 表名 | 说明 |
|------|------|
| users | 用户表 |
| auth_accounts | 认证账户表 |
| projects | 项目档案表 |
| account_strategy_contexts | 账号策略上下文表 |
| topics | 选题表 |
| scripts | 文案表 |
| generation_records | 生成记录表 |
| generation_tasks | 生成任务表（异步） |
| digital_assets | 数字资产表 |
| credit_accounts | 积分账户表 |
| credit_transactions | 积分交易表 |
| llm_channels | LLM 渠道配置表 |
| hot_copy_materials | 爆款素材表 |
| hot_copy_rewrites | 爆款仿写表 |
| project_reference_images | 项目参考图片表 |

---

## 6. API 接口清单

### 6.1 认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 注册 |
| POST | /api/auth/login | 登录 |
| POST | /api/auth/logout | 登出 |
| GET | /api/auth/me | 获取当前用户 |

### 6.2 项目
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/projects | 项目列表 |
| POST | /api/projects | 创建项目 |
| GET | /api/projects/{id} | 项目详情 |
| PUT | /api/projects/{id} | 更新项目 |
| DELETE | /api/projects/{id} | 删除项目 |

### 6.3 策略
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/strategy/account-package-execution-plan/generate | 生成账号包装+执行计划 |

### 6.4 选题
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/projects/{id}/topics | 项目选题列表 |
| POST | /api/creation/topics/generate | 生成选题 |

### 6.5 文案
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/creation/scripts/generate | 生成文案 |

### 6.6 爆款仿写
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/hot-copy/materials/manual | 手动录入素材 |
| POST | /api/hot-copy/materials/auto | 链接解析素材 |
| POST | /api/hot-copy/materials/auto-upload | 上传视频素材 |
| POST | /api/hot-copy/analysis | 结构分析 |
| POST | /api/hot-copy/rewrite | 仿写 |
| POST | /api/hot-copy/scenes | 场景生成 |
| POST | /api/hot-copy/generate-video | 视频生成 |

### 6.7 图片生成
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/images/generate | 文生图 |
| POST | /api/images/edit | 图生图 |
| POST | /api/images/enhance-prompt | 提示词增强 |

### 6.8 视频生成
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/videos/models | 获取模型列表 |
| POST | /api/videos/generate | 提交生成任务 |
| GET | /api/videos/tasks/{id} | 获取任务状态 |

### 6.9 AI 聊天
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/ai-chat | 发送消息 |
| GET | /api/ai-chat/conversations | 对话列表 |
| GET | /api/ai-chat/conversations/{id} | 对话历史 |

### 6.10 生成记录
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/generation-records | 记录列表 |
| GET | /api/generation-records/{id} | 记录详情 |

### 6.11 积分
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/credits/balance | 积分余额 |

### 6.12 LLM 渠道
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/llm-channels | 渠道列表 |
| POST | /api/llm-channels | 创建渠道 |
| PUT | /api/llm-channels/{id} | 更新渠道 |
| DELETE | /api/llm-channels/{id} | 删除渠道 |
| POST | /api/llm-channels/{id}/activate | 激活渠道 |
| POST | /api/llm-channels/{id}/test | 测试渠道 |

---

## 7. 用户界面设计

### 7.1 设计风格

| 维度 | 规范 |
|------|------|
| **颜色** | Muted and postal, monochromatic. 低饱和邮政色调，单色系为主 |
| **排版** | Card based design with layered elements. 基于卡片的设计，带有分层元素 |
| **风格** | Neo-minimalism. 新极简主义 |
| **哲学** | Approachable sophistication. 平易近人的高级感 |

### 7.2 主题系统

7 种翡翠主题色，通过 CSS Variables 实现：

| 主题 | 主色 | 描述 |
|------|------|------|
| 阳绿 (yang) | #5a9b82 | 鲜亮明快，生机勃勃 |
| 帝王绿 (imperial) | #3a6b5a | 深沉华贵，顶级翡翠 |
| 苹果绿 (apple) | #6aaa92 | 清新自然，水润透亮 |
| 紫罗兰 (lavender) | #8a7ab0 | 浪漫神秘，春色翡翠 |
| 黄翡 (yellow) | #b8985a | 温暖富贵，金玉满堂 |
| 红翡 (red) | #b86868 | 热烈奔放，鸿运当头 |
| 墨翠 (black) | #b8a060 | 黑金相映，低调奢华 |

### 7.3 布局结构

```
┌─────────────────────────────────────────────────────────────┐
│  Header (Sticky)                                             │
│  [Logo]  [Nav: 仿写 生图 生视频 资产 聊天 人设 记录]  [用户 设置] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Page Content]                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Section Header                                      │    │
│  │  eyebrow label                                      │    │
│  │  Title                                              │    │
│  │  [Action Buttons]                                   │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Content Cards (Glassmorphism)                       │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  Mobile Bottom Nav                                           │
└─────────────────────────────────────────────────────────────┘
```

### 7.4 响应式断点

| 断点 | 宽度 | 说明 |
|------|------|------|
| sm | 640px | 小屏手机 |
| md | 768px | 平板/大屏手机 |
| lg | 1024px | 平板横屏/小笔记本 |
| xl | 1280px | 笔记本 |
| 2xl | 1536px | 大屏桌面 |

### 7.5 动画规范

| 场景 | 时长 | 缓动函数 |
|------|------|----------|
| 页面进入 | 600ms | [0.16, 1, 0.3, 1] |
| 卡片出现 | 500ms | [0.16, 1, 0.3, 1] |
| Hover 反馈 | 300ms | ease-out |
| 导航切换 | 300ms | ease-out |

---

## 8. 非功能性需求

### 8.1 性能要求

| 指标 | 目标 |
|------|------|
| 首屏加载 | < 3s |
| API 响应 | < 2s (普通请求) |
| AI 生成响应 | < 30s (同步) / 异步队列 |
| 页面切换 | < 500ms |

### 8.2 可用性要求

| 指标 | 目标 |
|------|------|
| 系统可用性 | 99.9% |
| 数据备份 | 每日自动备份 |
| 故障恢复 | < 5 分钟 |

### 8.3 安全要求

| 项目 | 措施 |
|------|------|
| 认证 | Cookie-based, httponly, samesite |
| 密码 | bcrypt 哈希存储 |
| API 鉴权 | 每个请求验证 session |
| 文件上传 | 限制大小，验证类型 |
| CORS | 白名单控制 |

### 8.4 部署要求

| 环境 | 配置 |
|------|------|
| 服务器 | 8.152.2.222 |
| 域名 | JSVOC.jadejinyuxuan.com |
| 容器化 | Docker Compose |
| 数据库 | PostgreSQL (生产) / SQLite (开发) |
| 对象存储 | 阿里云 OSS (jsvoc2) |

---

## 9. 附录

### 9.1 术语表

| 术语 | 说明 |
|------|------|
| JSVOC | Jade Short Video Operation Center |
| LLM | Large Language Model |
| OSS | Object Storage Service |
| ER | Engagement Rate (互动率) |
| SR | Share Rate (分享率) |
| HP | Hook Power (钩子强度) |
| QL | Quality Level (质量评分) |
| NA | Novelty & Authority (新颖性与权威性) |
| AB | Actionability (可操作性) |
| SAT | Sentiment Alignment (情感契合度) |

### 9.2 相关文档

| 文档 | 路径 |
|------|------|
| 架构文档 | docs/ARCHITECTURE.md |
| API 规范 | docs/API_SPEC.md |
| 数据库设计 | docs/DB_SCHEMA.md |
| 部署文档 | docs/DEPLOYMENT.md |
| 用户指南 | docs/USER_GUIDE.md |
| 发布说明 | docs/RELEASE_NOTES.md |

### 9.3 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v0.1.0-mvp | 2026-05-09 | MVP 版本，基础功能上线 |
| v1.0 | 2026-06-03 | 完整 PRD 文档 |
