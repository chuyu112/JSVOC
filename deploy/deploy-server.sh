#!/bin/bash
# 服务器部署脚本（在 8.152.2.222 上执行）
# 部署前端 standalone + 配置 nginx + 启动 frps

set -e

PROJECT_DIR="/opt/JSVOC/current"
DOMAIN="JSVOC.jadejinyuxuan.com"
FRONTEND_PORT=3000

echo "========================================"
echo "  JSVOC 服务器部署"
echo "  域名: $DOMAIN"
echo "========================================"

# 1. 进入项目目录
cd "$PROJECT_DIR"

# 2. 拉取最新代码（如果是 git 仓库）
if [ -d ".git" ]; then
    echo "[1/6] 拉取最新代码..."
    git pull origin master
fi

# 3. 构建前端
echo "[2/6] 构建前端..."
cd "$PROJECT_DIR/frontend-v2"

# 安装依赖
npm ci

# 构建 standalone（API 代理到本地 frp 端口）
# 前端服务器端会把 /api/* 请求转发到 http://127.0.0.1:8000
API_BASE_URL="http://127.0.0.1:8000" npm run build

# 4. 使用 PM2 启动前端
echo "[3/6] 启动前端服务..."
pm2 delete jsvoc-frontend 2>/dev/null || true

# standalone 模式会生成 .next/standalone 目录
# 需要把 public 静态资源复制过去
cp -r "$PROJECT_DIR/frontend-v2/public" "$PROJECT_DIR/frontend-v2/.next/standalone/" 2>/dev/null || true

pm2 start "$PROJECT_DIR/frontend-v2/.next/standalone/server.js" \
    --name "jsvoc-frontend" \
    --env PORT=$FRONTEND_PORT

# 5. 配置 Nginx
echo "[4/6] 配置 Nginx..."
cp "$PROJECT_DIR/deploy/nginx-jsvoc.conf" /etc/nginx/sites-available/jsvoc

# 确保配置文件正确
sed -i "s|root /opt/JSVOC/current/frontend-v2/dist|# root not needed for proxy|g" /etc/nginx/sites-available/jsvoc 2>/dev/null || true

# 如果前端是 standalone 模式，nginx 需要反代到 Node.js 端口
cat > /etc/nginx/sites-available/jsvoc << 'EOF'
server {
    listen 80;
    server_name JSVOC.jadejinyuxuan.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name JSVOC.jadejinyuxuan.com;

    ssl_certificate /etc/letsencrypt/live/JSVOC.jadejinyuxuan.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/JSVOC.jadejinyuxuan.com/privkey.pem;

    # 前端 Next.js standalone（PM2 运行在 3000 端口）
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    # 健康检查（直接走 frp 到本地后端）
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_read_timeout 10s;
    }

    # WebSocket 支持
    location /ws/ {
        proxy_pass http://127.0.0.1:3000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

ln -sf /etc/nginx/sites-available/jsvoc /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# 6. 确保 frps 运行
echo "[5/6] 启动 frp 服务端..."
systemctl start frps 2>/dev/null || true

# 7. 保存 PM2 配置
echo "[6/6] 保存 PM2 配置..."
pm2 save
pm2 startup systemd 2>/dev/null || true

echo "========================================"
echo "  服务器部署完成"
echo "========================================"
echo ""
echo "服务状态:"
pm2 status
echo ""
echo "访问地址:"
echo "  前端: https://$DOMAIN"
echo "  frp监控: http://$DOMAIN:7500 (admin/jsvoc-admin-2026)"
echo ""
echo "注意："
echo "  本地电脑需要启动 frpc + 后端"
echo "  运行: D:\\JSVOC\\start_local.bat"
echo ""
