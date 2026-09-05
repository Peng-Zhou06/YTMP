from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User
from app.forms.auth import LoginForm, RegisterForm
from app.utils.logs import log_action
import os
from werkzeug.utils import secure_filename

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        logout_user()
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'y'
        if not username or not password:
            flash('请输入用户名和密码', 'warning')
            return redirect(url_for('auth.login'))
        user = User.query.filter_by(username=username).first()
        if not user:
            flash('用户名或密码错误', 'danger')
            return redirect(url_for('auth.login'))
        if not user.is_active:
            flash('该账号已被禁用，请联系管理员', 'danger')
            return redirect(url_for('auth.login'))
        if user.is_locked():
            flash('账号已被锁定，请10分钟后再试或联系管理员', 'danger')
            return redirect(url_for('auth.login'))
        if not user.verify_password(password):
            user.increment_login_attempts()
            remaining_attempts = 5 - user.login_attempts
            if remaining_attempts > 0:
                flash(f'用户名或密码错误，还剩{remaining_attempts}次尝试机会', 'danger')
            else:
                flash('登录失败次数过多，账号已被锁定10分钟', 'danger')
            return redirect(url_for('auth.login'))
        login_user(user, remember=remember)
        user.reset_login_attempts()
        log_action(user.id, 'login', 'users', f'用户{user.username}登录系统', ip_address=request.remote_addr, user_agent=request.user_agent.string)
        flash('登录成功', 'success')
        role_routes = {'admin': 'system.dashboard', 'teacher': 'project.teacher_dashboard', 'student': 'project.student_stats'}
        return redirect(url_for(role_routes.get(user.role, 'system.dashboard')))
    return render_template('auth/login.html', form=LoginForm())

@auth_bp.route('/logout')
@login_required
def logout():
    user_id = current_user.id
    username = current_user.username
    logout_user()
    log_action(user_id, 'logout', 'users', f'用户{username}退出系统', ip_address=request.remote_addr, user_agent=request.user_agent.string)
    flash('已成功登出', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if 'avatar' in request.files:
            avatar_file = request.files['avatar']
            if avatar_file and avatar_file.filename:
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                filename = secure_filename(avatar_file.filename)
                if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                    flash('只支持 PNG、JPG、JPEG、GIF 格式的图片', 'warning')
                else:
                    import uuid
                    ext = filename.rsplit('.', 1)[1].lower()
                    unique_filename = uuid.uuid4().hex + '.' + ext
                    upload_folder = os.path.join(current_app.static_folder, 'avatars')
                    os.makedirs(upload_folder, exist_ok=True)
                    filepath = os.path.join(upload_folder, unique_filename)
                    avatar_file.save(filepath)
                    if current_user.avatar:
                        old_avatar_path = os.path.join(current_app.static_folder, current_user.avatar)
                        if os.path.exists(old_avatar_path):
                            os.remove(old_avatar_path)
                    current_user.avatar = 'avatars/' + unique_filename
                    db.session.commit()
                    log_action(current_user.id, 'upload_avatar', 'users', '用户上传头像', ip_address=request.remote_addr)
                    flash('头像上传成功', 'success')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        if name: current_user.name = name
        if email: current_user.email = email
        if phone: current_user.phone = phone
        db.session.commit()
        log_action(current_user.id, 'update_profile', 'users', '用户更新个人资料', ip_address=request.remote_addr)
        flash('个人资料更新成功', 'success')
        return redirect(url_for('auth.profile'))
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if not current_user.verify_password(old_password):
            flash('原密码错误', 'danger')
            return redirect(url_for('auth.change_password'))
        if len(new_password) < 6:
            flash('新密码长度不能少于6位', 'danger')
            return redirect(url_for('auth.change_password'))
        if new_password != confirm_password:
            flash('两次输入的新密码不一致', 'danger')
            return redirect(url_for('auth.change_password'))
        current_user.password = new_password
        db.session.commit()
        log_action(current_user.id, 'change_password', 'users', '用户修改密码', ip_address=request.remote_addr)
        flash('密码修改成功', 'success')
        return redirect(url_for('auth.profile'))
    return render_template('auth/change_password.html')
