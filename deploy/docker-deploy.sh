#!/bin/bash
# ============================================
# YTMP Docker 一键部署脚本
# ============================================

set -e

echo "=========================================="
echo "YTMP 云智实训管理平台 - Docker部署"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker未安装，请先安装Docker${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose未安装，请先安装Docker Compose${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker版本: $(docker --version)${NC}"
echo -e "${GREEN}✅ Docker Compose版本: $(docker-compose --version)${NC}"

# ============================================
# 1. 配置环境变量
# ============================================
echo -e "\n${GREEN}[1/4] 配置环境变量...${NC}"

if [ ! -f .env ]; then
    cat > .env << 'EOF'
# MySQL密码（如果服务器已有MySQL，修改为实际密码）
MYSQL_ROOT_PASSWORD=你的MySQL密码

# Flask密钥（生成随机密钥：python3 -c "import secrets; print(secrets.token_hex(32))"）
SECRET_KEY=change-this-to-random-key

# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_NAME=hnkj
DB_USER=root
EOF
    echo -e "${YELLOW}⚠️  请编辑 .env 文件，修改MySQL密码${NC}"
    echo -e "${YELLOW}   nano .env${NC}"
    read -p "按回车继续..."
else
    echo -e "${GREEN}✅ .env 文件已存在${NC}"
fi

# ============================================
# 2. 创建必要目录
# ============================================
echo -e "\n${GREEN}[2/4] 创建必要目录...${NC}"
mkdir -p logs
mkdir -p app/static/uploads

# ============================================
# 3. 构建并启动服务
# ============================================
echo -e "\n${GREEN}[3/4] 构建Docker镜像...${NC}"
docker-compose build

echo -e "\n${GREEN}[4/4] 启动服务...${NC}"
docker-compose up -d

# ============================================
# 完成
# ============================================
echo -e "\n${GREEN}==========================================${NC}"
echo -e "${GREEN}✅ Docker部署完成！${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo "查看服务状态："
echo "  docker-compose ps"
echo ""
echo "查看日志："
echo "  docker-compose logs -f web"
echo "  docker-compose logs -f nginx"
echo ""
echo "重启服务："
echo "  docker-compose restart"
echo ""
echo "停止服务："
echo "  docker-compose down"
echo ""
echo "更新服务："
echo "  docker-compose pull && docker-compose up -d"
echo ""
echo -e "${YELLOW}请确保：${NC}"
echo "1. 已配置 .env 文件中的MySQL密码"
echo "2. 阿里云安全组已开放 80 端口"
echo "3. 服务器MySQL已启动且hnkj数据库已创建"
echo ""