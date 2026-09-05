"""WSGI entry point for production deployment"""
import os
from app import create_app

# 设置环境变量
os.environ.setdefault('FLASK_APP', 'main.py')
os.environ.setdefault('FLASK_ENV', 'production')

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    app.run()