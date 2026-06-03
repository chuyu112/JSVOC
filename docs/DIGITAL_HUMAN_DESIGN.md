# JSVOC 数字人功能设计方案

> 基于图片中的 5 模块工作流：Whisper → CozyVoice → HeyGem → FFmpeg → DistScript

---

## 1. 功能定位

在项目内提供**一键生成数字人口播视频**能力：
- 选择已有文案（Script）
- 选择/克隆声音
- 选择数字人形象
- 生成带字幕+BGM 的成品视频

---

## 2. 页面设计

### 2.1 入口
- `/projects/{id}/digital-human` — 项目内数字人工作台
- `/digital-human` — 全局数字人视频库（预留）

### 2.2 工作流界面（4 步）

```
┌─────────────────────────────────────────────────────────────┐
│  数字人视频生成                                               │
│  Step 1/4 → Step 2/4 → Step 3/4 → Step 4/4                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Step 1: 选择文案                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                      │
│  │ 文案卡片1 │ │ 文案卡片2 │ │ + 从选题 │                      │
│  └──────────┘ └──────────┘ └──────────┘                      │
│                                                              │
│  Step 2: 选择声音                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                      │
│  │ 🎙️ 女声A │ │ 🎙️ 男声B │ │ + 克隆   │                      │
│  └──────────┘ └──────────┘ └──────────┘                      │
│                                                              │
│  Step 3: 选择形象                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                      │
│  │ 👤 形象1 │ │ 👤 形象2 │ │ 👤 形象3 │                      │
│  └──────────┘ └──────────┘ └──────────┘                      │
│                                                              │
│  Step 4: 生成配置                                             │
│  [x] 添加字幕    [x] 添加BGM    分辨率: [1080p ▼]              │
│  [生成视频] ← 显示预估积分消耗                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 生成结果页

```
┌─────────────────────────────────────────────────────────────┐
│  生成结果                                                     │
│  ┌────────────────────────────────────┐                     │
│  │                                    │                     │
│  │         [视频播放器]                │                     │
│  │                                    │                     │
│  └────────────────────────────────────┘                     │
│  状态: ✅ 完成    耗时: 3分24秒    消耗: 50积分               │
│  [下载视频] [复制文案] [进入发布]                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 后端架构

### 3.1 服务层

```
DigitalHumanService (协调)
    ├── CozyVoiceService      # TTS / 声音克隆
    ├── HeyGemService         # 数字人视频生成
    ├── VideoComposeService   # FFmpeg 字幕+BGM合成
    └── StorageService        # 视频存储到OSS
```

### 3.2 执行流程（异步任务）

```
用户提交生成请求
    ↓
创建 generation_task (status=queued)
    ↓
[Step 1] CozyVoiceService.tts()
    输入: 文案 + 声音样本
    输出: audio.wav
    ↓
[Step 2] HeyGemService.generate()
    输入: audio.wav + 数字人形象
    输出: raw_video.mp4
    ↓
[Step 3] VideoComposeService.compose()
    输入: raw_video.mp4 + 文案(字幕) + BGM
    输出: final_video.mp4
    ↓
上传 OSS → 更新 task status=succeeded
```

### 3.3 显存管理

RTX 5070 Ti 16GB 显存无法同时加载多个大模型，采用**串行执行**：

| 阶段 | 加载模型 | 显存占用 | 执行后 |
|------|---------|---------|--------|
| TTS | CozyVoice | ~6GB | 卸载，释放显存 |
| 数字人 | HeyGem | ~10GB | 卸载，释放显存 |
| 合成 | FFmpeg (CPU) | 0GB | 无需显存 |

---

## 4. 数据模型

### 4.1 digital_human_avatars（数字人形象库）

```sql
id              INT PK
name            VARCHAR(80)      -- 形象名称
avatar_type     VARCHAR(20)      -- preset / custom
thumbnail_url   VARCHAR(500)     -- 缩略图
video_url       VARCHAR(500)     -- 参考视频（用于HeyGem训练）
config_json     JSONB            -- HeyGem配置参数
gender          VARCHAR(10)      -- male / female
is_active       BOOLEAN
created_at      TIMESTAMP
```

### 4.2 digital_human_voices（声音库）

```sql
id              INT PK
name            VARCHAR(80)      -- 声音名称
voice_type      VARCHAR(20)      -- preset / cloned
sample_url      VARCHAR(500)     -- 3秒样本音频（克隆用）
config_json     JSONB            -- CozyVoice配置
gender          VARCHAR(10)
is_active       BOOLEAN
created_at      TIMESTAMP
```

### 4.3 digital_human_videos（生成记录）

```sql
id              INT PK
user_id         INT
project_id      INT              -- 关联项目
script_id       INT              -- 关联文案
voice_id        INT              -- 使用声音
avatar_id       INT              -- 使用形象
task_id         INT              -- 关联 generation_tasks
video_url       VARCHAR(500)     -- 成品视频
audio_url       VARCHAR(500)     -- 中间音频（可选）
duration        FLOAT            -- 视频时长
status          VARCHAR(20)      -- pending / generating / success / failed
config_json     JSONB            -- 生成配置
error_message   TEXT
created_at      TIMESTAMP
```

---

## 5. API 设计

### 5.1 形象管理

```
GET    /api/digital-human/avatars          # 形象列表
GET    /api/digital-human/avatars/{id}     # 形象详情
```

### 5.2 声音管理

```
GET    /api/digital-human/voices           # 声音列表
POST   /api/digital-human/voices/clone     # 上传3秒样本克隆声音
Body: { name, audio_file }
```

### 5.3 视频生成

```
POST   /api/digital-human/videos/generate  # 提交生成任务
Body: {
    project_id: 1,
    script_id: 5,           # 使用已有文案
    voice_id: 2,            # 选择声音
    avatar_id: 1,           # 选择形象
    with_subtitle: true,    # 是否加字幕
    with_bgm: true,         # 是否加BGM
    resolution: "1080p"     # 分辨率
}
Response: { task_id, status: "queued" }

GET    /api/digital-human/videos           # 视频列表
GET    /api/digital-human/videos/{id}      # 视频详情/下载
```

---

## 6. 本地部署方案（RTX 5070 Ti）

### 6.1 CozyVoice 部署

```bash
# 1. 克隆仓库
git clone https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice

# 2. 安装依赖
conda create -n cosyvoice python=3.10
conda activate cosyvoice
pip install -r requirements.txt

# 3. 下载预训练模型（约 3GB）
# 模型会自动下载到 ~/.cache/modelscope/hub

# 4. 启动 API 服务
python api.py --port 50000
```

### 6.2 HeyGem 部署

```bash
# HeyGem 使用 Docker 部署
git clone https://github.com/GuijiAI/HeyGem.ai.git
cd HeyGem.ai

# 按官方文档启动 Docker Compose
docker-compose up -d

# 默认 API 端口: 3000
```

### 6.3 JSVOC 连接配置

```env
# .env 新增
COZYVOICE_URL=http://127.0.0.1:50000
HEYGEM_URL=http://127.0.0.1:3000

# FFmpeg 已内置，无需额外配置
```

---

## 7. 与现有系统集成

### 7.1 复用组件
- **generation_tasks** — 异步任务队列（已有）
- **digital_assets** — 视频资产存储（已有）
- **credits** — 积分消耗（已有）
- **Whisper** — 文案输入来源（已有）

### 7.2 新增组件
- CozyVoice 本地服务
- HeyGem Docker 服务
- 数字人相关数据库表
- 前端数字人工作台页面

---

## 8. 积分消耗设计

| 环节 | 积分 | 说明 |
|------|------|------|
| TTS (CozyVoice) | 5 | 语音合成 |
| 数字人 (HeyGem) | 30 | 视频生成 |
| 字幕合成 (FFmpeg) | 0 | CPU处理，免费 |
| BGM | 0 | 预设BGM免费 |
| **合计** | **35** | 每段视频 |

---

## 9. 实现优先级

### P0（核心闭环）
1. 数据库表：avatars, voices, videos
2. 后端 API：视频生成 + 任务追踪
3. 前端页面：4步工作流 + 结果页
4. CozyVoice 本地接入
5. HeyGem 本地接入

### P1（增强）
6. 声音克隆（上传3秒样本）
7. 自定义数字人形象上传
8. 字幕样式配置
9. BGM选择

### P2（分发）
10. 一键发布（DistScript）
11. 多平台账号绑定

---

## 10. 风险点

| 风险 | 应对 |
|------|------|
| HeyGem Docker 在 Windows 上运行不稳定 | 准备 WSL2 + Docker Desktop |
| CozyVoice 首次启动慢 | 模型预加载 + 异步任务 |
| 16GB 显存同时被其他AI任务占用 | 显存管理（串行执行）|
| Blackwell 架构兼容性问题 | 准备 CPU fallback |
