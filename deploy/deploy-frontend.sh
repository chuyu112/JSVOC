#!/bin/bash
# 前端部署脚本（在服务器 8.152.2.222 上执行）

set -e

SERVER_DIR="/opt/JSVOC/current"
DOMAIN="JSVOC.jadejinyuxuan.com"

echo "========================================"
echo "  JSVOC 前端部署脚本"
echo "  目标服务器: $DOMAIN"
echo "========================================"

# 1. 确保目录存在
mkdir -p "$SERVER_DIR"

# 2. 构建前端（在本地构建后上传，或在服务器上构建）
# 这里假设前端代码已上传到服务器
cd "$SERVER_DIR"

# 3. 安装依赖并构建
npm install

# 构建时指定 API 地址（通过 frp 穿透后的地址）
NEXT_PUBLIC_API_BASE_URL="http://8.152.2.222:8000" npm run build

# 4. 使用 PM2 启动前端服务
pm2 delete jsvoc-frontend 2>/dev/null || true
pm2 start npm --name "jsvoc-frontend" -- start

echo "========================================"
echo "  前端部署完成"
echo "  访问: https://$DOMAIN"
echo "  API 地址: http://8.152.2.222:8000"
echo "========================================"
