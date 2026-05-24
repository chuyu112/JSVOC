# JSVOC Docker 服务器部署手册

适用对象：服务器部署同事
适用系统：Alibaba Cloud Linux 3.2104 LTS 64 位
项目名称：JSVOC
仓库地址：git@github.com:chuyu111/JSVOC.git
部署分支：sp8-engineering
部署方式：Docker Compose

> 注意：`v0.1.0-mvp` 是功能 MVP 冻结标签，不建议直接用于 Docker 部署。Docker Compose、Nginx、PostgreSQL、openai_compatible 等工程化配置在 `sp8-engineering` 分支。

---

## 1. 部署目标

服务器上最终启动 3 个核心服务：

```text
postgres   PostgreSQL 数据库
backend    FastAPI 后端服务
frontend   Vue 前端 + Nginx
```

最终访问地址：

```text
前端页面：http://服务器IP:5173
后端健康检查：http://服务器IP:8000/health
前端反代健康检查：http://服务器IP:5173/health
```

---

## 2. 服务器基础检查

登录服务器：

```bash
ssh root@服务器IP
```

确认系统版本：

```bash
cat /etc/os-release
```

应看到类似：

```text
Alibaba Cloud Linux
VERSION="3.2104 LTS"
```

建议项目部署目录：

```text
/opt/JSVOC
```

---

## 3. 安装 Docker

如果服务器已经安装 Docker，并且以下命令能正常输出版本，可以跳过本节：

```bash
docker --version
docker compose version
```

### 3.1 安装 Docker Engine 和 Compose 插件

Alibaba Cloud Linux 3 使用 `dnf`，不要使用 Ubuntu 的 `apt`。

```bash
dnf clean all
dnf makecache

dnf -y install wget git

rm -f /etc/yum.repos.d/docker*.repo

dnf -y remove \
docker-ce \
containerd.io \
docker-ce-rootless-extras \
docker-buildx-plugin \
docker-ce-cli \
docker-compose-plugin

wget -O /etc/yum.repos.d/docker-ce.repo http://mirrors.cloud.aliyuncs.com/docker-ce/linux/centos/docker-ce.repo

sed -i 's|https://mirrors.aliyun.com|http://mirrors.cloud.aliyuncs.com|g' /etc/yum.repos.d/docker-ce.repo

dnf -y install dnf-plugin-releasever-adapter --repo alinux3-plus

dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl start docker
systemctl enable docker
```

验证安装：

```bash
docker --version
docker compose version
systemctl status docker --no-pager
```

---

## 4. 配置 Docker 镜像加速器

如果执行：

```bash
docker run --rm hello-world
```

出现类似错误：

```text
request canceled while waiting
Get "https://registry-1.docker.io/v2/"
```

说明服务器访问 Docker Hub 超时，需要配置镜像加速器。

### 4.1 获取阿里云镜像加速器地址

进入阿里云控制台：

```text
容器镜像服务 ACR
  ↓
镜像工具
  ↓
镜像加速器
```

复制类似下面的地址：

```text
https://xxxxxx.mirror.aliyuncs.com
```

### 4.2 写入 Docker daemon 配置

把下面命令里的：

```text
https://你的加速器地址
```

替换成真实地址。

```bash
mkdir -p /etc/docker

cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://你的加速器地址"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m"
  }
}
EOF

systemctl daemon-reload
systemctl restart docker
```

检查是否生效：

```bash
docker info | grep -A 10 "Registry Mirrors"
```

重新测试：

```bash
docker run --rm hello-world
```

看到以下内容说明 Docker 拉镜像正常：

```text
Hello from Docker!
```

---

## 5. 配置 GitHub SSH 权限

服务器已有 SSH key 的情况下，不需要重新生成。

### 5.1 查看服务器已有 SSH key

```bash
ls -la /root/.ssh
```

通常会看到类似：

```text
jsvoc_github
jsvoc_github.pub
```

注意：

```text
.pub 是公钥
不带 .pub 的是私钥
```

Git 拉代码时使用的是私钥，不是 `.pub` 文件。

### 5.2 配置 SSH 使用指定私钥

假设私钥是：

```text
/root/.ssh/jsvoc_github
```

执行：

```bash
chmod 700 /root/.ssh
chmod 600 /root/.ssh/jsvoc_github

cat > /root/.ssh/config <<'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile /root/.ssh/jsvoc_github
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
EOF

chmod 600 /root/.ssh/config
```

如果私钥不是 `jsvoc_github`，把配置里的这一行改成实际私钥路径：

```text
IdentityFile /root/.ssh/你的私钥文件名
```

### 5.3 测试 GitHub SSH

```bash
ssh -T git@github.com
```

正常会看到类似：

```text
You've successfully authenticated, but GitHub does not provide shell access.
```

继续测试仓库访问：

```bash
git ls-remote --heads git@github.com:chuyu111/JSVOC.git
```

如果能看到分支列表，说明服务器已经能访问仓库。

---

## 6. 拉取项目代码

进入 `/opt`：

```bash
cd /opt
rm -rf JSVOC
git clone -b sp8-engineering git@github.com:chuyu111/JSVOC.git JSVOC
cd /opt/JSVOC
```

确认项目文件：

```bash
ls -la
```

应看到：

```text
docker-compose.yml
.env.example
backend
frontend
README.md
docs
```

确认当前分支：

```bash
git branch --show-current
```

应输出：

```text
sp8-engineering
```

如果提示 `sp8-engineering` 分支不存在，说明该分支还没有推送到 GitHub，需要开发同事在本机执行：

```bash
cd /d D:\JSVOC
git checkout sp8-engineering
git push -u origin sp8-engineering
```

服务器再重新拉取。

---

## 7. 配置 .env

进入项目目录：

```bash
cd /opt/JSVOC
```

复制环境变量文件：

```bash
cp .env.example .env
```

编辑：

```bash
vi .env
```

测试阶段建议先使用 mock 模式，不接真实大模型：

```env
APP_ENV=production
DEBUG=false

POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=short_video_ops
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/short_video_ops

VITE_API_BASE_URL=/

LLM_PROVIDER=mock
LLM_MODEL=mock-model
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_API_KEY=change-me
LLM_TIMEOUT_SECONDS=60
```

保存退出：

```text
Esc
:wq
回车
```

检查关键环境变量：

```bash
grep -E "DATABASE_URL|LLM_PROVIDER|LLM_MODEL" .env
```

应看到：

```text
DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/short_video_ops
LLM_PROVIDER=mock
LLM_MODEL=mock-model
```

---

## 8. 检查 Docker Compose 配置

必须在项目目录执行：

```bash
cd /opt/JSVOC
docker compose config
```

如果报错：

```text
no configuration file provided
```

说明当前目录不对，先执行：

```bash
cd /opt/JSVOC
```

---

## 9. 启动项目

首次启动：

```bash
cd /opt/JSVOC
docker compose up -d --build
```

查看容器状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs postgres
docker compose logs backend
docker compose logs frontend
```

持续查看后端日志：

```bash
docker compose logs -f backend
```

后端容器启动时会自动执行：

```text
alembic upgrade head
```

然后启动 FastAPI。

---

## 10. 验证服务

### 10.1 后端健康检查

```bash
curl http://localhost:8000/health
```

预期：

```json
{"status":"ok"}
```

### 10.2 前端 Nginx 反向代理健康检查

```bash
curl http://localhost:5173/health
```

预期：

```json
{"status":"ok"}
```

### 10.3 浏览器访问

浏览器打开：

```text
http://服务器IP:5173
```

如果无法访问，需要检查阿里云安全组是否放行端口：

```text
TCP 5173
TCP 8000
```

测试阶段可以先放行 `5173` 和 `8000`。正式上线建议只暴露 `80` 和 `443`。

---

## 11. 验证核心业务链路

以下接口建议全部用 `localhost:5173/api/...` 测试，这样可以验证：

```text
frontend nginx → backend → postgres → LLM Gateway
```

### 11.1 创建项目

```bash
curl -X POST http://localhost:5173/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "四会翡翠账号",
    "industry": "珠宝",
    "sub_industry": "翡翠",
    "product": "翡翠手镯",
    "personal_intro": "在四会卖翡翠多年，为人靠谱",
    "target_audience": "喜欢翡翠，想买翡翠的人",
    "platforms": ["抖音", "视频号", "快手", "小红书"],
    "current_stage": "新号冷启动"
  }'
```

预期返回项目数据，包含：

```text
id
project_name
industry
product
```

记住返回的 `id`，下面假设项目 ID 是 `1`。

### 11.2 生成账号包装和执行计划

```bash
curl -X POST http://localhost:5173/api/strategy/account-package-execution-plan/generate \
  -H "Content-Type: application/json" \
  -d '{"project_id":1,"cycle":"30天","daily_time":"2小时"}'
```

预期返回：

```text
account_package
account_positioning
persona
account_names
bios
content_columns
trust_design
conversion_path
platform_strategies
execution_plan
weekly_plan
daily_plan
generation_record_id
```

### 11.3 生成选题

```bash
curl -X POST http://localhost:5173/api/creation/topics/generate \
  -H "Content-Type: application/json" \
  -d '{"project_id":1,"platform":"抖音","goal":"获客","count":20}'
```

预期返回：

```text
topics
generation_record_id
```

每个选题应包含：

```text
id
title
content_type
platform
goal
score
topic_data
```

记下其中一个 `topic_id`，下面假设选题 ID 是 `1`。

### 11.4 生成文案

```bash
curl -X POST http://localhost:5173/api/creation/scripts/generate \
  -H "Content-Type: application/json" \
  -d '{"project_id":1,"topic_id":1,"script_type":"聊观点","duration":"60秒","goal":"私信获客"}'
```

预期返回：

```text
title
hook
script_content
shot_suggestions
conversion_script
generation_record_id
```

### 11.5 查看生成历史

```bash
curl "http://localhost:5173/api/generation-records?project_id=1"
```

预期能看到 4 类记录：

```text
account_package
execution_plan
topics
script
```

---

## 12. 切换真实大模型 openai_compatible

先用 mock 跑通部署，再切真实模型。

编辑 `.env`：

```bash
cd /opt/JSVOC
vi .env
```

修改为：

```env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://你的模型中转地址/v1
LLM_API_KEY=你的key
LLM_MODEL=你的模型名
LLM_TIMEOUT_SECONDS=60
```

重启后端：

```bash
docker compose up -d --build backend
docker compose logs -f backend
```

---

## 13. openai_compatible 地址注意事项

### 13.1 大模型中转服务也在 Docker Compose 里

假设服务名叫：

```text
llm-gateway
```

则 `.env` 写：

```env
LLM_BASE_URL=http://llm-gateway:11434/v1
```

### 13.2 大模型中转服务跑在服务器宿主机

如果后端跑在 Docker 容器里，而模型中转服务跑在服务器宿主机上，容器内不能直接用：

```env
LLM_BASE_URL=http://127.0.0.1:11434/v1
```

因为容器里的 `127.0.0.1` 是容器自己。

Linux 服务器建议在 `docker-compose.yml` 的 `backend` 服务里确认有：

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

然后 `.env` 写：

```env
LLM_BASE_URL=http://host.docker.internal:11434/v1
```

修改后重启：

```bash
docker compose up -d --build backend
```

---

## 14. 常用运维命令

进入项目目录：

```bash
cd /opt/JSVOC
```

查看容器：

```bash
docker compose ps
```

查看全部日志：

```bash
docker compose logs
```

查看后端日志：

```bash
docker compose logs -f backend
```

查看前端日志：

```bash
docker compose logs -f frontend
```

查看数据库日志：

```bash
docker compose logs -f postgres
```

重启全部服务：

```bash
docker compose restart
```

重启后端：

```bash
docker compose restart backend
```

重新构建并启动：

```bash
docker compose up -d --build
```

停止服务但保留数据库数据：

```bash
docker compose down
```

不要随便执行：

```bash
docker compose down -v
```

因为 `-v` 会删除数据库 volume，可能导致数据丢失。

---

## 15. 更新代码部署

以后代码更新后：

```bash
cd /opt/JSVOC
git fetch origin
git checkout sp8-engineering
git pull origin sp8-engineering
docker compose up -d --build
```

查看状态：

```bash
docker compose ps
docker compose logs -f backend
```

---

## 16. 回滚版本

查看提交：

```bash
cd /opt/JSVOC
git log --oneline -10
```

切回某个提交：

```bash
git checkout 提交ID
docker compose up -d --build
```

如果要回到分支最新版本：

```bash
git checkout sp8-engineering
git pull origin sp8-engineering
docker compose up -d --build
```

---

## 17. 常见问题

### 17.1 `docker compose ps` 报 `no configuration file provided`

原因：当前目录不是项目目录。

解决：

```bash
cd /opt/JSVOC
docker compose ps
```

### 17.2 GitHub HTTPS 报 `Invalid username or token`

原因：GitHub 不支持账号密码直接进行 Git HTTPS 操作。

解决：使用 SSH：

```bash
git clone -b sp8-engineering git@github.com:chuyu111/JSVOC.git JSVOC
```

### 17.3 `ssh -T git@github.com` 失败

检查私钥配置：

```bash
ls -la /root/.ssh
cat /root/.ssh/config
```

测试指定私钥：

```bash
ssh -i /root/.ssh/你的私钥文件 -o IdentitiesOnly=yes -T git@github.com
```

### 17.4 Docker 拉镜像超时

检查 Docker 镜像加速器：

```bash
cat /etc/docker/daemon.json
systemctl restart docker
docker info | grep -A 10 "Registry Mirrors"
docker run --rm hello-world
```

### 17.5 backend 起不来

查看后端日志：

```bash
docker compose logs -f backend
```

常见原因：

```text
DATABASE_URL 错误
postgres 未 healthy
alembic migration 失败
Python 依赖安装失败
```

### 17.6 前端能打开，但 API 报错

检查 Nginx 代理：

```bash
curl http://localhost:5173/health
curl http://localhost:5173/api/projects
```

查看前端日志：

```bash
docker compose logs -f frontend
```

### 17.7 真实模型调用失败

先确认 mock 模式正常：

```env
LLM_PROVIDER=mock
```

再切换：

```env
LLM_PROVIDER=openai_compatible
```

查看后端日志：

```bash
docker compose logs -f backend
```

检查：

```env
LLM_BASE_URL
LLM_API_KEY
LLM_MODEL
LLM_TIMEOUT_SECONDS
```

---

## 18. 最终验收标准

部署完成后，需要确认以下项目全部通过：

```text
1. docker compose ps 显示 postgres、backend、frontend 都正常
2. http://服务器IP:8000/health 返回 ok
3. http://服务器IP:5173/health 返回 ok
4. 浏览器能打开 http://服务器IP:5173
5. 能创建项目
6. 能生成账号包装
7. 能生成执行计划
8. 能生成选题
9. 能从选题生成文案
10. 能查看生成历史
11. generation_records 有记录写入
12. mock 模式跑通后，再切真实 openai_compatible 模式
```

---

## 19. 最短部署命令版

如果 Docker 已安装、镜像加速器已配置、GitHub SSH 已通，可以直接执行：

```bash
cd /opt
rm -rf JSVOC
git clone -b sp8-engineering git@github.com:chuyu111/JSVOC.git JSVOC

cd /opt/JSVOC
cp .env.example .env

grep -E "LLM_PROVIDER|DATABASE_URL" .env

docker compose config
docker compose up -d --build

docker compose ps

curl http://localhost:8000/health
curl http://localhost:5173/health
```

浏览器打开：

```text
http://服务器IP:5173
```

---

## 20. 参考资料

- Alibaba Cloud Docker 部署说明：`https://www.alibabacloud.com/help/en/simple-application-server/use-cases/manually-deploy-docker`
- Alibaba Cloud Linux 3 Docker 安装说明：`https://help.aliyun.com/zh/document_detail/2842585.html`
- GitHub Deploy Keys 文档：`https://docs.github.com/v3/guides/managing-deploy-keys`
- GitHub Clone 文档：`https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository`
- Docker Registry Mirrors 文档：`https://docs.docker.com/docker-hub/image-library/mirror/`
