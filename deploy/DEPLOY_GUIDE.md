# YTMP 云智实训管理平台 - 阿里云部署指南

## 📋 部署前准备

### 1. 阿里云服务器要求
- **操作系统**: Ubuntu 20.04 或 22.04 LTS
- **配置建议**: 2核4G 或以上
- **存储空间**: 40GB 或以上
- **安全组**: 开放 80 (HTTP), 443 (HTTPS), 22 (SSH) 端口

### 2. 域名（可选）
- 购买域名并备案
- 将域名解析到服务器IP

---

## 🚀 快速部署步骤

### 步骤1: 上传项目到服务器

```bash
# 方法1: 使用SCP上传
scp -r E:\xiaozhou\kc\web\YTMP root@你的服务器IP:/var/www/YTMP

# 方法2: 使用Git（推荐）
cd /var/www
git clone <你的Git仓库地址> YTMP
```

### 步骤2: 登录服务器

```bash
ssh root@你的服务器IP
```

### 步骤3: 运行部署脚本

```bash
cd /var/www/YTMP/deploy
chmod +x deploy.sh
sudo ./deploy.sh
```

### 步骤4: 导入数据库

```bash
# 登录MySQL
mysql -u root -p

# 创建数据库
CREATE DATABASE hnkj DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hnkj;

# 导入表结构
source /var/www/YTMP/create_hnkj_database.sql;

# 退出
exit;
```

### 步骤5: 配置环境变量

```bash
cd /var/www/YTMP
cp .env.production .env
nano .env

# 修改以下配置：
# DATABASE_URL=mysql+pymysql://root:你的MySQL密码@localhost:3306/hnkj
# SECRET_KEY=生成一个随机密钥
```

### 步骤6: 安装Python依赖

```bash
cd /var/www/YTMP
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 步骤7: 启动服务

```bash
# 启动应用
systemctl start YTMP
systemctl enable YTMP

# 启动Nginx
systemctl start nginx
systemctl enable nginx

# 检查状态
systemctl status YTMP
systemctl status nginx
```

### 步骤8: 配置阿里云安全组

1. 登录阿里云控制台
2. 进入 ECS → 安全组
3. 添加入方向规则：
   - 端口 80 (HTTP)
   - 端口 443 (HTTPS)
   - 端口 22 (SSH)

### 步骤9: 访问应用

打开浏览器访问：`http://你的服务器IP`

---

## 🔧 手动部署（如果不使用脚本）

### 1. 安装系统依赖

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx mysql-server
```

### 2. 配置MySQL

```bash
sudo systemctl start mysql
sudo systemctl enable mysql
sudo mysql_secure_installation
```

### 3. 创建Python虚拟环境

```bash
cd /var/www/YTMP
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 配置Gunicorn

创建 `/var/www/YTMP/gunicorn.conf.py`:

```python
bind = "127.0.0.1:5000"
workers = 4
timeout = 120
accesslog = "/var/log/YTMP/access.log"
errorlog = "/var/log/YTMP/error.log"
```

### 5. 配置Nginx

```bash
sudo nano /etc/nginx/sites-available/YTMP
```

粘贴 `deploy/nginx.conf` 内容，然后：

```bash
sudo ln -s /etc/nginx/sites-available/YTMP /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. 配置Systemd服务

```bash
sudo nano /etc/systemd/system/YTMP.service
```

粘贴 `deploy/ytmp.service` 内容，然后：

```bash
sudo systemctl daemon-reload
sudo systemctl enable YTMP
sudo systemctl start YTMP
```

---

## 🔒 安全配置

### 1. 配置HTTPS（Let's Encrypt）

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 2. 防火墙配置

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 3. 修改SSH端口（可选）

```bash
sudo nano /etc/ssh/sshd_config
# 修改 Port 22 为其他端口，如 2222
sudo systemctl restart sshd
```

---

## 📊 运维管理

### 查看日志

```bash
# 应用日志
tail -f /var/log/YTMP/error.log
tail -f /var/log/YTMP/access.log

# Nginx日志
tail -f /var/log/nginx/YTMP_error.log
tail -f /var/log/nginx/YTMP_access.log

# 系统日志
journalctl -u YTMP -f
```

### 重启服务

```bash
systemctl restart YTMP
systemctl restart nginx
systemctl restart mysql
```

### 更新代码

```bash
cd /var/www/YTMP
git pull
source venv/bin/activate
pip install -r requirements.txt
systemctl restart YTMP
```

### 数据库备份

```bash
# 备份
mysqldump -u root -p hnkj > /backup/hnkj_$(date +%Y%m%d).sql

# 恢复
mysql -u root -p hnkj < /backup/hnkj_20260617.sql
```

---

## ❓ 常见问题

### 1. 502 Bad Gateway
- 检查YTMP服务是否运行：`systemctl status YTMP`
- 检查Gunicorn日志：`tail -f /var/log/YTMP/error.log`

### 2. 数据库连接失败
- 检查MySQL是否运行：`systemctl status mysql`
- 检查.env文件中的数据库配置
- 测试连接：`mysql -u root -p`

### 3. 静态文件404
- 检查Nginx配置中的static路径
- 确保文件权限正确：`chown -R www-data:www-data /var/www/YTMP`

### 4. 权限问题
```bash
sudo chown -R www-data:www-data /var/www/YTMP
sudo chmod -R 755 /var/www/YTMP
```

---

## 📞 技术支持

如遇到问题，请检查：
1. 服务状态：`systemctl status YTMP nginx mysql`
2. 日志文件：`/var/log/YTMP/` 和 `/var/log/nginx/`
3. 端口监听：`netstat -tlnp`
4. 防火墙状态：`ufw status`