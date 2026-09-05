from flask import Flask, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler
from config.config import Config
import logging
import json

# 初始化扩展
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
csrf = CSRFProtect()
scheduler = BackgroundScheduler()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # 注册自定义模板过滤器
    @app.template_filter('fromjson')
    def fromjson_filter(value):
        """将JSON字符串转换为Python对象"""
        if value is None:
            return []
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    
    # 配置日志
    if not app.debug:
        file_handler = logging.FileHandler('app.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('云智实训管理平台启动')
    
    # 导入蓝图
    from app.views.auth import auth_bp
    from app.views.student import student_bp
    from app.views.course import course_bp
    from app.views.score import score_bp
    from app.views.system import system_bp
    from app.views.project import project_bp
    from app.views.department import dept_bp
    from app.views.ai_assistant import ai_bp
    from app.views.notification import notification_bp, announcement_bp
    
    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(course_bp)
    app.register_blueprint(score_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(dept_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(announcement_bp)
    
    # 配置定时任务
    with app.app_context():
        # 在这里可以添加定时任务，例如：
        # scheduler.add_job(func=crawl_scheduled_tasks, trigger="interval", hours=1)
        if not scheduler.running:
            scheduler.start()
    
    # 注册上下文处理器
    @app.context_processor
    def inject_unread_count():
        """注入未读通知数量到所有模板"""
        from flask_login import current_user
        if current_user.is_authenticated:
            from app.service.notification_service import NotificationService
            return {'unread_count': NotificationService.get_unread_count(current_user.id)}
        return {'unread_count': 0}
    
    # 添加根路由 - 未登录用户重定向到登录页
    @app.route('/')
    def index():
        from flask_login import current_user
        if current_user.is_authenticated:
            # 已登录用户根据角色重定向
            if current_user.role == 'admin':
                return redirect(url_for('system.dashboard'))
            elif current_user.role == 'teacher':
                return redirect(url_for('course.teacher_courses'))
            elif current_user.role == 'student':
                return redirect(url_for('score.student_scores'))
            else:
                return redirect(url_for('system.dashboard'))
        else:
            # 未登录用户重定向到登录页
            return redirect(url_for('auth.login'))
    
    # 健康检查接口
    @app.route('/health')
    def health_check():
        """健康检查接口，用于监控服务和数据库状态"""
        import datetime
        health_status = {
            'status': 'ok',
            'timestamp': datetime.datetime.now().isoformat(),
            'service': 'YTMP',
            'database': 'unknown'
        }
        
        # 检查数据库连接
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            health_status['database'] = 'connected'
        except Exception as e:
            health_status['status'] = 'degraded'
            health_status['database'] = f'error: {str(e)}'
        
        return health_status, 200 if health_status['status'] == 'ok' else 503
    
    # 测试路由
    @app.route('/test')
    def test():
        return "<h1>Application is working!</h1><p>If you see this, Flask is running correctly.</p>"
    
    return app