# 多阶段构建 - 生产环境
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    FLASK_DEBUG=0

RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    gcc \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --no-cache-dir gunicorn pymysql email_validator \
    -i https://mirrors.aliyun.com/pypi/simple/

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/app/static/uploads \
    /var/log/YTMP

# 设置权限
RUN chmod -R 755 /app

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "-c", "from main import app; app.run(host='0.0.0.0', port=5000)"]
