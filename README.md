# YTMP 云智实训管理平台

基于 Flask 的实训教学管理平台，面向管理员、教师和学生提供课程、学生、成绩、项目与通知等日常教学管理能力。

## 功能概览

- 角色登录与权限控制：管理员、教师、学生。
- 学生、院系、课程与班级管理，支持数据导入。
- 成绩录入、统计与学生成绩查询。
- 课程项目、实训任务与文件上传管理。
- 公告与站内通知。
- 系统用户、日志和基础设置管理。
- AI 助手与定时任务基础能力。
- `/health` 健康检查接口，便于部署监控。

## 技术栈

- Python 3、Flask、SQLAlchemy、Flask-Migrate、Flask-Login
- MySQL（通过 PyMySQL 连接）
- Jinja2、Bootstrap 风格前端模板
- pandas / openpyxl（Excel 数据处理）
- Docker、Gunicorn、Nginx（生产部署）

## 本地运行

### 1. 准备环境

建议使用 Python 3.10 或更高版本，并准备一个 MySQL 数据库。

```bash
git clone https://github.com/Peng-Zhou06/YTMP.git
cd YTMP

python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Linux / macOS
# source .venv/bin/activate

pip install -r requirements.txt
```

### 2. 配置环境变量

复制示例文件并按实际环境填写数据库连接与应用密钥：

```bash
cp .env.example .env
```

至少需要配置：

```dotenv
SECRET_KEY=请替换为随机且保密的字符串
DATABASE_URL=mysql+pymysql://用户名:密码@localhost:3306/数据库名
```

如需启用 AI 助手，请额外配置服务商提供的密钥，例如：

```dotenv
ZHIPU_API_KEY=你的服务商密钥
```

请勿提交 `.env`、生产环境配置或数据库备份到 Git 仓库。

### 3. 初始化数据库并启动

使用 Alembic 执行已有迁移：

```bash
flask --app main db upgrade
python main.py
```

默认开发地址为 `http://127.0.0.1:5000`。应用还提供 `http://127.0.0.1:5000/health` 健康检查接口。

> `create_admin.py` 会创建默认管理员示例账号。仅限开发或首次初始化时使用，并请在首次登录后立即修改默认密码。

## Docker 部署

项目包含 `Dockerfile` 与 `docker-compose.yml`。部署前请在终端或 CI/CD 环境中设置所需环境变量，特别是：

```bash
export MYSQL_ROOT_PASSWORD='你的 MySQL 密码'
export SECRET_KEY='随机且保密的应用密钥'
export ZHIPU_API_KEY='你的 AI 服务密钥'
docker compose up -d --build
```

更多 Nginx、Gunicorn 与 systemd 部署说明见 [deploy/DEPLOY_GUIDE.md](deploy/DEPLOY_GUIDE.md)。

## 项目结构

```text
app/          Flask 蓝图、模型、服务、表单、模板与静态资源
config/       应用配置
migrations/   数据库迁移脚本
deploy/       Nginx、systemd、Docker 部署文件与部署说明
main.py       开发环境启动入口
wsgi.py       WSGI 生产入口
```

## 安全说明

- 公开仓库不包含生产环境配置或数据库备份。
- 密钥、数据库密码与令牌必须通过环境变量或受控的密钥管理服务注入。
- 如果密钥曾被提交到公开历史，应立即在对应服务后台撤销并重新生成。

## 许可证

当前未附带开源许可证。使用、修改或分发前请先取得项目维护者授权。
