#!/bin/bash
# 服务器环境初始化脚本（在 8.152.2.222 上执行）

set -e

DOMAIN="JSVOC.jadejinyuxuan.com"
EMAIL="admin@jadejinyuxuan.com"  # 用于 Let's Encrypt
PROJECT_DIR="/opt/JSVOC"

echo "========================================"
echo "  JSVOC 服务器环境初始化"
echo "  域名: $DOMAIN"
echo "========================================"

# 1. 系统更新
echo "[1/8] 更新系统..."
apt-get update && apt-get upgrade -y

# 2. 安装基础依赖
echo "[2/8] 安装基础依赖..."
apt-get install -y \
    curl wget git nginx certbot python3-certbot-nginx \
    nodejs npm pm2 \
    ufw fail2ban

# 3. 配置防火墙
echo "[3/8] 配置防火墙..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 7000/tcp   # frp
ufw allow 8000/tcp   # frp 映射
ufw --force enable

# 4. 创建项目目录
echo "[4/8] 创建项目目录..."
mkdir -p $PROJECT_DIR
chown -R root:root $PROJECT_DIR

# 5. 安装 frp
echo "[5/8] 安装 frp..."
if [ ! -d "/opt/frp" ]; then
    FRP_VERSION="0.61.0"
    wget -q "https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_amd64.tar.gz"
    tar -xzf "frp_${FRP_VERSION}_linux_amd64.tar.gz" -C /opt
    mv "/opt/frp_${FRP_VERSION}_linux_amd64" /opt/frp
    rm "frp_${FRP_VERSION}_linux_amd64.tar.gz"
fi

# 6. 配置 frps 服务
echo "[6/8] 配置 frp 服务..."
cat > /etc/systemd/system/frps.service << 'EOF'
[Unit]
Description=frp server
After=network.target

[Service]
Type=simple
ExecStart=/opt/frp/frps -c /opt/JSVOC/current/deploy/frps.toml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable frps

# 7. 配置 Nginx
echo "[7/8] 配置 Nginx..."
cp $PROJECT_DIR/current/deploy/nginx-jsvoc.conf /etc/nginx/sites-available/jsvoc
ln -sf /etc/nginx/sites-available/jsvoc /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# 8. 申请 SSL 证书
echo "[8/8] 申请 SSL 证书..."
certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m $EMAIL || true

echo "========================================"
echo "  服务器初始化完成"
echo "========================================"
echo ""
echo "下一步："
echo "  1. 上传代码到 $PROJECT_DIR/current"
echo "  2. 启动 frps: systemctl start frps"
echo "  3. 在你的本地电脑启动 frpc"
echo "  4. 构建并部署前端"
echo ""
