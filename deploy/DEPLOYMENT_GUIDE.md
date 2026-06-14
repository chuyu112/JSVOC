# JSVOC 生产部署指南

> 架构：前端（服务器）+ 后端（本地 RTX 5070 Ti）通过 frp 内网穿透连接

---

## 架构图

```
用户浏览器
    ↓ HTTPS
https://JSVOC.jadejinyuxuan.com
    ↓
Nginx (443)
    ↓
Next.js standalone (3000端口，服务器)
    ↓ /api/* rewrites
frp 客户端 ←──── 隧道 ────→ frp 服务端 (7000)
(你的本地电脑)                           (8.152.2.222)
    ↓                                        ↓
FastAPI (8000)                        公网入口 (8000)
RTX 5070 Ti ASR
```

---

## 第一步：服务器初始化（只做一次）

SSH 登录服务器：

```bash
ssh root@8.152.2.222

# 运行初始化脚本
cd /opt/JSVOC/current
bash deploy/setup-server.sh
```

这会安装：Nginx、Certbot、Node.js、PM2、frp、防火墙

---

## 第二步：配置 frp 服务端

```bash
# 复制配置文件
cp /opt/JSVOC/current/deploy/frps.toml /opt/frp/frps.toml

# 启动 frps
systemctl start frps
systemctl enable frps
```

---

## 第三步：本地电脑配置 frp 客户端

在你的 Windows 电脑（RTX 5070 Ti）上：

1. 下载 frp Windows 版：https://github.com/fatedier/frp/releases
2. 解压到 `C:\frp`
3. 复制 `deploy/frpc.toml` 到 `C:\frp\frpc.toml`

---

## 第四步：部署前端到服务器

```bash
ssh root@8.152.2.222
cd /opt/JSVOC/current
bash deploy/deploy-server.sh
```

---

## 第五步：启动本地后端（你的电脑）

双击运行：

```
D:\JSVOC\start_local.bat
```

这会同时启动：
- frpc（内网穿透客户端）
- FastAPI 后端（RTX 5070 Ti ASR）

---

## 验证

| 检查项 | 命令/操作 |
|--------|-----------|
| frp 隧道 | `http://8.152.2.222:8000/health` |
| 前端页面 | `https://JSVOC.jadejinyuxuan.com` |
| frp 监控 | `http://8.152.2.222:7500` (admin/jsvoc-admin-2026) |
| ASR 测试 | 前端粘贴抖音链接 → 点击转写 |
| GPU 负载 | 本地运行 `nvidia-smi` |

---

## 文件清单

| 文件 | 用途 |
|------|------|
| `deploy/frps.toml` | frp 服务端配置 |
| `deploy/frpc.toml` | frp 客户端配置（你的电脑） |
| `deploy/setup-server.sh` | 服务器环境初始化 |
| `deploy/deploy-server.sh` | 前端构建部署 |
| `deploy/nginx-jsvoc.conf` | Nginx 反向代理配置 |
| `start_local.bat` | 本地启动（后端 + frpc） |
| `start_backend.bat` | 仅启动后端（如果 frpc 已在运行） |
| `backend/app/services/gpu_worker_client.py` | faster-whisper ASR |

---

## 故障排查

### frpc 连接失败
```
检查服务器防火墙：ufw status
检查 frps 是否运行：systemctl status frps
检查 token 是否一致：frps.toml 和 frpc.toml
```

### ASR 模型下载慢
```
设置镜像：set HF_ENDPOINT=https://hf-mirror.com
或设置缓存目录：set WHISPER_MODEL_DIR=D:\models
```

### RTX 5070 Ti 报错
```
如果 faster-whisper 不兼容 Blackwell：
1. 代码已自动 fallback 到 float16
2. 如果还报错，临时切换 CPU：
   修改 .env：ASR_DEVICE=cpu, ASR_COMPUTE_TYPE=int8
```

### SSL 证书过期
```
certbot renew
```
