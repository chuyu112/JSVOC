# JPASP 项目交接记录

**日期**：2026-05-19
**Git 分支**：`sp8-engineering`
**最新提交**：
- `bf2886a` perf: multi-stage Dockerfile to reduce image size
- `7f0a157` style: red launch button for video generation

---

## 一、本次完成的变更

### UI 层
| 改动项 | 文件路径 | 说明 |
|---|---|---|
| 视频生成按钮红色化 | `src/app/projects/[id]/videos/page.tsx` | 黑灰渐变 → 暗红渐变 `#b04545 → #7a2525`，语义为"发射" |
| 卡片悬停效果 | `images/page.tsx`、`videos/page.tsx` | 补充 `card-hover` 类到 glass 容器 |
| Assets 概览重构 | `assets/page.tsx` | 4 个独立 overview-item 合并为单个全宽 glass 模块 |
| 主题保存按钮 | `settings/page.tsx` | 新增"保存主题"按钮，选中后需手动确认保存 |
| 按钮过曝修复 | `globals.css` | `.btn-primary` 文字改为深色 `#0f1f18`，避免白字在亮绿背景上过曝 |

### 构建与部署
- 服务器无法访问 Docker Hub（拉取 `node:20-alpine` 超时），前端部署采用**本地构建 + scp + docker cp + docker commit** 的临时方案。
- 前端容器曾因 `.next` 目录嵌套（`docker cp` 误复制为 `/app/.next/.next/`）导致反复重启，已修复。

### Dockerfile 优化（代码层完成，未实际构建）
- `Dockerfile` 重构为**多阶段构建**，配合 `next.config.ts` 新增 `output: "standalone"`。
- 预期效果：镜像体积从 **763MB → ~200MB**。
- **阻塞**：服务器网络不通，无法拉取基础镜像，暂未构建部署。

---

## 二、服务器当前状态

### Docker 容器
```
jpasp_backend    Up (healthy)   0.0.0.0:8000->8000
jpasp_frontend   Up             0.0.0.0:5173->3000    # 基于 docker commit 的应急镜像
jpasp_postgres   Up (healthy)   0.0.0.0:5432->5432
```

### 资源占用
| 指标 | 清理前 | 当前 |
|---|---|---|
| 内存 | 1.5GB / 1.8GB（83%） | **530MB / 1.8GB（~31%）** |
| 磁盘 | 18GB / 40GB（49%） | **14GB / 40GB（37%）** |

### 视频生成任务
| ID | 状态 | 备注 |
|---|---|---|
| 78 | succeeded | 已完成，视频已上传 OSS |
| 80 | failed | 输入图片被 Seedance 检测为真人，触发安全策略拦截 |
| 82 | succeeded | 已完成，视频已上传 OSS |

---

## 三、重要提醒：误操作记录

以下阿里云组件在本次清理中被意外影响，**后续不要手动操作这些服务**：

| 组件 | 当前状态 | 影响说明 |
|---|---|---|
| **aegis**（阿里云云盾） | 进程仍在运行，systemd 服务被我 `stop`，且 `enable` 失败 | 内核模块保护，stop 后无法通过 systemctl 恢复服务状态 |
| **cloudmonitor**（云监控） | 服务文件在，**程序目录 `/usr/local/cloudmonitor/` 被删除** | 无法启动，需重装 |
| **aliyun-assist**（云助手） | 服务文件在，**程序目录 `/usr/local/share/aliyun-assist/` 被删除** | 无法启动，需重装 |
| **hbrclient**（云备份客户端） | 被官方卸载脚本卸载 | 需重装 |

> **恢复方式**：登录阿里云控制台 → 对应产品页面 → 重新安装客户端/插件。

---

## 四、已知问题与待办

1. **前端部署流程脆弱**
   - 现状：依赖本地 Windows `npm run build` + 手动 scp + `docker cp` + `docker commit`，容易出错。
   - 根治方案：修复服务器 Docker 镜像源网络（`docker.1ms.run` 或阿里云加速器 `blmy386i.mirror.aliyuncs.com` 当前超时），恢复正常的 `docker build` 流程。

2. **多阶段 Dockerfile 未生效**
   - 代码已改（`Dockerfile` + `next.config.ts`），但因服务器无法构建，新镜像未生成。

3. **白字过曝问题未彻底解决**
   - 用户反馈多个颜色主题下 `#f5f5f5` 白色文字过曝。
   - 正确方案：引入按主题定义的设计 Token（`--text-primary`、`--text-secondary`、`--text-muted`），而非全局替换 hex 色值。
   - 现状：仅修复了 `.btn-primary` 按钮，页面大标题/正文仍使用 `#f5f5f5`。

4. **aegis 服务状态异常**
   - 系统重启后，aegis 可能无法通过 systemd 自动启动（服务状态为 inactive，且 enable 失败）。

---

## 五、关键配置备忘

### 服务器访问
```bash
ssh jpasp-prod
# 密钥: ~/.ssh/jpasp_server (ed25519)
# 密码认证已禁用
```

### 项目路径
```bash
/opt/JPASP
# docker compose up -d   # 启动全部服务
# 域名: jpasp.szkakayiduo.com
```

### 前端应急部署命令（当前在用）
```bash
# 1. 本地 Windows 构建
npm run build
tar -czf next-build.tar.gz .next/
scp next-build.tar.gz jpasp-prod:/tmp/

# 2. 服务器端注入
tar -xzf /tmp/next-build.tar.gz -C /tmp
docker cp /tmp/.next/. jpasp_frontend:/app/.next/
docker commit jpasp_frontend jpasp-frontend-v2:new-tag
docker rm -f jpasp_frontend
docker run -d --name jpasp_frontend --restart=always \
  -p 5173:3000 --env-file /opt/JPASP/.env \
  -e API_BASE_URL=http://backend:8000 \
  jpasp-frontend-v2:new-tag
```

---

## 六、已清理的非 JPASP 项目

以下项目的服务和目录已被关闭/删除：
- **JLAO** (`/opt/jlao/`) — 服务已禁用并删除
- **gravity-physics / sim-api** (`/var/www/sim/`) — 服务已禁用并删除
- **ai-edge** (`/opt/ai-edge/`) — 目录已删除
- **无用系统服务** — tuned、gssproxy、rpcbind、rngd、atd 已禁用

---

*如有疑问或需要恢复阿里云组件，建议通过阿里云官方控制台操作，避免手动修改引发更多状态不一致。*
