# 服务器部署备忘

适用分支：`sp8-engineering`

当前已验证可用提交：

```text
72bce79
```

部署路径：

```text
/opt/JSVOC
```

## 已知部署注意事项

1. Docker Hub 拉镜像可能超时

   在 Alibaba Cloud Linux 服务器上执行 `docker compose up -d --build` 时，可能出现：

   ```text
   Get "https://registry-1.docker.io/v2/": context deadline exceeded
   ```

   或：

   ```text
   net/http: request canceled while waiting for connection
   ```

2. 需要配置阿里云镜像加速器

   建议在服务器 `/etc/docker/daemon.json` 配置阿里云 ACR 镜像加速器，然后重启 Docker：

   ```bash
   systemctl daemon-reload
   systemctl restart docker
   ```

   配置后用以下命令验证：

   ```bash
   docker info | grep -A 10 "Registry Mirrors"
   docker run --rm hello-world
   ```

3. 基础镜像可使用 `docker.1ms.run` 代理

   如果配置阿里云镜像加速器后仍然无法稳定拉取 Docker Hub 镜像，可以在 `.env` 中使用已经验证过的代理镜像：

   ```env
   POSTGRES_IMAGE=docker.1ms.run/library/postgres:16
   PYTHON_IMAGE=docker.1ms.run/library/python:3.11-slim
   NODE_IMAGE=docker.1ms.run/library/node:20-alpine
   NGINX_IMAGE=docker.1ms.run/library/nginx:1.27-alpine
   ```

4. 8000 端口可能被旧 `jlao` 进程占用

   如果 backend 容器启动时报：

   ```text
   listen tcp4 0.0.0.0:8000: bind: address already in use
   ```

   先检查占用进程：

   ```bash
   ss -ltnp | grep ':8000'
   ```

   本次部署曾发现旧进程：

   ```text
   /opt/jlao/backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

   确认不是当前 JSVOC 服务后，可以停止该旧进程，再重新启动 Docker Compose。

5. Alembic 文件必须在 GitHub `sp8-engineering` 中

   backend Dockerfile 会复制并执行 Alembic：

   ```text
   backend/alembic.ini
   backend/alembic/
   ```

   如果这些文件没有推送到 GitHub，服务器重新 clone 后会在 Docker build 阶段失败。当前提交 `72bce79` 已包含这些文件。

6. 推荐部署路径固定为 `/opt/JSVOC`

   常用部署命令：

   ```bash
   cd /opt
   rm -rf JSVOC
   git clone -b sp8-engineering git@github.com:chuyu111/JSVOC.git JSVOC
   cd /opt/JSVOC
   cp .env.example .env
   docker compose up -d --build
   ```

7. 当前可用提交是 `72bce79`

   如果需要确认服务器代码版本：

   ```bash
   cd /opt/JSVOC
   git log --oneline -1
   ```

   预期看到：

   ```text
   72bce79 docs: record server deployment notes
   ```

## 快速验收

启动后检查：

```bash
cd /opt/JSVOC
docker compose ps
curl http://localhost:8000/health
curl http://localhost:5173/health
```

预期：

```text
postgres healthy
backend healthy
frontend healthy
{"status":"ok"}
{"status":"ok"}
```
