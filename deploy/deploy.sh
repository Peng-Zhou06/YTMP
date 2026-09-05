#!/bin/bash
# ============================================
# 阿里云服务器部署脚本（精简版）
# 适用于 Ubuntu 20.04/22.04
# 前提：MySQL已安装，hnkj数据库和表结构已创建
# ============================================

set -e  # 遇到错误立即退出

echo "=========================================="
echo "YTMP 云智实训管理平台 - 阿里云部署脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否以root运行
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用 sudo 运行此脚本${NC}"
    exit 1
fi

# ============================================
# 1. 更新系统
# ============================================
echo -e "\n${GREEN}[1/7] 更新系统...${NC}"
apt update && apt upgrade -y

# ============================================
# 2. 安装必要软件（跳过MySQL）
# ============================================
echo -e "\n${GREEN}[2/7] 安装必要软件...${NC}"
apt install -y python3 python3-pip python3-venv
apt install -y nginx
apt install -y git curl wget

# ============================================
# 3. 创建应用目录
# ============================================
echo -e "\n${GREEN}[3/7] 创建应用目录...${NC}"
mkdir -p /var/www/YTMP
mkdir -p /var/www/YTMP/app/static/uploads
mkdir -p /var/log/YTMP

# ============================================
# 4. 创建虚拟环境并安装依赖
# ============================================
echo -e "\n${GREEN}[4/7] 创建Python虚拟环境并安装依赖...${NC}"
cd /var/www/YTMP
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# 如果有requirements.txt
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
else
    pip install flask flask-login flask-sqlalchemy flask-wtf flask-migrate pymysql gunicorn
    pip install requests beautifulsoup4 lxml python-dotenv
fi

# ============================================
# 5. 配置环境变量
# ============================================
echo -e "\n${GREEN}[5/7] 配置环境变量...${NC}"
if [ ! -f /var/www/YTMP/.env ]; then
    cat > /var/www/YTMP/.env << 'EOF'
# 生产环境配置
SECRET_KEY=change-this-to-random-key
FLASK_ENV=production
FLASK_DEBUG=False

# 数据库配置（修改为你的MySQL密码）
DATABASE_URL=mysql+pymysql://root:你的MySQL密码@localhost:3306/hnkj

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=5000

# 文件上传路径
UPLOAD_FOLDER=/var/www/YTMP/app/static/uploads
EOF
    echo -e "${YELLOW}⚠️  请编辑 /var/www/YTMP/.env 文件，修改MySQL密码和SECRET_KEY${NC}"
    echo -e "${YELLOW}   nano /var/www/YTMP/.env${NC}"
    read -p "按回车继续..."
else
    echo -e "${GREEN}.env 文件已存在${NC}"
fi

# ============================================
# 6. 配置Nginx
# ============================================
echo -e "\n${GREEN}[6/7] 配置Nginx...${NC}"
# 备份默认配置
cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.bak 2>/dev/null || true

# 创建YTMP配置
cat > /etc/nginx/sites-available/YTMP << 'EOF'
server {
    listen 80;
    server_name _;
    
    access_log /var/log/nginx/YTMP_access.log;
    error_log /var/log/nginx/YTMP_error.log;
    
    location /static {
        alias /var/www/YTMP/app/static;
        expires 30d;
    }
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 启用配置
ln -sf /etc/nginx/sites-available/YTMP /etc/nginx/sites-enabled/YTMP
rm -f /etc/nginx/sites-enabled/default

# 测试Nginx配置
nginx -t
systemctl restart nginx
systemctl enable nginx

# ============================================
# 7. 配置Systemd服务
# ============================================
echo -e "\n${GREEN}[7/7] 配置Systemd服务...${NC}"
cat > /etc/systemd/system/YTMP.service << 'EOF'
[Unit]
Description=YTMP 云智实训管理平台
After=network.target mysql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/YTMP
Environment=PATH=/var/www/YTMP/venv/bin
ExecStart=/var/www/YTMP/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 --timeout 120 --access-logfile /var/log/YTMP/access.log --error-logfile /var/log/YTMP/error.log main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 重新加载systemd
systemctl daemon-reload
systemctl enable YTMP
systemctl start YTMP

# ============================================
# 设置权限
# ============================================
echo -e "\n${GREEN}设置文件权限...${NC}"
chown -R www-data:www-data /var/www/YTMP
chown -R www-data:www-data /var/log/YTMP
chmod -R 755 /var/www/YTMP

# ============================================
# 完成
# ============================================
echo -e "\n${GREEN}==========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo "服务状态检查："
echo "  systemctl status YTMP"
echo "  systemctl status nginx"
echo "  systemctl status mysql"
echo ""
echo "查看日志："
echo "  tail -f /var/log/YTMP/error.log"
echo "  tail -f /var/log/nginx/YTMP_error.log"
echo ""
echo "重启服务："
echo "  systemctl restart YTMP"
echo "  systemctl restart nginx"
echo ""
echo -e "${YELLOW}请确保：${NC}"
echo "1. 已编辑 .env 文件，修改MySQL密码"
echo "2. 已生成随机SECRET_KEY"
echo "3. 阿里云安全组已开放 80 端口"
echo ""