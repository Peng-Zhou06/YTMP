from flask import redirect, url_for, flash
from flask_login import current_user
from functools import wraps

# 角色检查装饰器（支持单个或多个角色）
def role_required(*roles):
    """
    角色权限检查装饰器
    用法：
        @role_required('admin')  # 单个角色
        @role_required('admin', 'teacher')  # 多个角色
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录', 'warning')
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash('没有访问权限', 'danger')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 多角色检查装饰器
def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录', 'warning')
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash('没有访问权限', 'danger')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
