import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    # 应用配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-me'
    
    # 数据库配�?    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://root:password@localhost:3306/yunzhi_training'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = None  # 16MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar'}
    
    # 日志配置
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    
    # 密码加密配置
    BCRYPT_LOG_ROUNDS = 13
    
    # 分页配置
    PER_PAGE = 10
    
    # APScheduler配置
    SCHEDULER_API_ENABLED = True
