#!/usr/bin/env bash
# JSVOC 一键部署脚本
# 用法: ./deploy.sh [SSH密码]
# 或设置环境变量: DEPLOY_PASSWORD=xxx ./deploy.sh

set -euo pipefail

SERVER="root@8.152.2.222"
DEPLOY_DIR="/opt/JSVOC"
PASSWORD="${1:-${DEPLOY_PASSWORD:-}}"

if [[ -z "$PASSWORD" ]]; then
    echo "用法: ./deploy.sh <SSH密码>"
    echo "或:   DEPLOY_PASSWORD=<密码> ./deploy.sh"
    exit 1
fi

echo "=== JSVOC 部署开始 ==="
echo "目标服务器: $SERVER"
echo "部署目录: $DEPLOY_DIR"
echo ""

# 检查 sshpass
check_sshpass() {
    if command -v sshpass &> /dev/null; then
        return 0
    fi
    echo "sshpass 未安装，尝试安装..."
    if command -v apt-get &> /dev/null; then
        apt-get update && apt-get install -y sshpass
    elif command -v yum &> /dev/null; then
        yum install -y sshpass
    elif command -v brew &> /dev/null; then
        brew install sshpass
    elif command -v choco &> /dev/null; then
        choco install sshpass -y
    else
        echo "无法自动安装 sshpass。请手动安装后重试："
        echo "  Windows: https://github.com/xaksis/vue-good-links/releases (或使用 Git Bash + pacman -S sshpass)"
        echo "  Ubuntu:  apt-get install sshpass"
        echo "  CentOS:  yum install sshpass"
        echo "  macOS:   brew install sshpass"
        exit 1
    fi
}

# 执行远程命令
remote_exec() {
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$SERVER" "$1"
}

check_sshpass

echo "[1/5] 检查正在运行的生成任务..."
RUNNING_TASKS=$(remote_exec "cd $DEPLOY_DIR && docker compose exec -T postgres psql -U postgres -d short_video_ops -t -c \"select count(*) from generation_tasks where status in ('queued','running');\"" 2>/dev/null | tr -d '[:space:]')
if [[ "${RUNNING_TASKS:-0}" != "0" && -n "$RUNNING_TASKS" ]]; then
    echo "警告: 当前有 $RUNNING_TASKS 个生成任务正在运行。"
    echo "建议等任务完成后再部署，避免中断。"
    read -p "是否继续部署? (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "已取消部署"
        exit 0
    fi
fi

echo ""
echo "[2/5] 拉取最新代码..."
remote_exec "cd $DEPLOY_DIR && git fetch origin && git reset --hard origin/main"

echo ""
echo "[3/5] Docker 构建并重启..."
remote_exec "cd $DEPLOY_DIR && docker compose --progress plain up -d --build"

echo ""
echo "[4/5] 检查服务状态..."
remote_exec "cd $DEPLOY_DIR && docker compose ps"

echo ""
echo "[5/5] 健康检查..."
HEALTH=$(remote_exec "curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health" 2>/dev/null || echo "000")
if [[ "$HEALTH" == "200" ]]; then
    echo "后端健康检查通过 (200)"
else
    echo "后端健康检查失败 (HTTP $HEALTH)，请检查日志:"
    echo "  ssh $SERVER 'cd $DEPLOY_DIR && docker compose logs -f backend'"
fi

FRONTEND=$(remote_exec "curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:5173/projects" 2>/dev/null || echo "000")
if [[ "$FRONTEND" == "200" || "$FRONTEND" == "307" ]]; then
    echo "前端页面检查通过 ($FRONTEND)"
else
    echo "前端页面检查异常 (HTTP $FRONTEND)"
fi

echo ""
echo "=== 部署完成 ==="
echo "线上地址: https://JSVOC.jadejinyuxuan.com"
echo ""
echo "常用排查命令:"
echo "  后端日志: ssh $SERVER 'cd $DEPLOY_DIR && docker compose logs -f backend'"
echo "  前端日志: ssh $SERVER 'cd $DEPLOY_DIR && docker compose logs -f frontend-v2'"
echo "  查看任务: ssh $SERVER 'cd $DEPLOY_DIR && docker compose exec -T postgres psql -U postgres -d short_video_ops -c \"select id, task_type, status from generation_tasks order by id desc limit 10;'\""
