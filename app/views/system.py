from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Student, Course, Score, Log, SystemSettings
from app.forms.auth import RegisterForm
from app.utils.decorators import role_required, roles_required
from app.utils.logs import log_action
import os
import subprocess
from datetime import datetime
import io
import json

# 创建蓝图
system_bp = Blueprint('system', __name__)

# 系统仪表盘
@system_bp.route('/dashboard')
@roles_required('admin')
def dashboard():
    from app.models import Project, Team, Task, DailyReport, Bug, TeamMember
    
    # 统计数据
    total_students = Student.query.count()
    total_courses = Course.query.count()
    total_scores = Score.query.count()
    total_users = User.query.count()
    total_projects = Project.query.count()
    total_teams = Team.query.count()
    total_tasks = Task.query.count()
    completed_tasks = Task.query.filter_by(status='done').count()
    total_bugs = Bug.query.count()
    
    # 任务状态统计
    task_todo = Task.query.filter_by(status='todo').count()
    task_in_progress = Task.query.filter_by(status='in_progress').count()
    task_review = Task.query.filter_by(status='review').count()
    task_done = Task.query.filter_by(status='done').count()
    task_delayed = Task.query.filter_by(status='delayed').count()
    
    # 日报提交率统计（今日）
    from datetime import date
    today = date.today()
    total_students_with_team = db.session.query(Student.id).join(TeamMember).distinct().count()
    today_reports = DailyReport.query.filter(
        db.func.date(DailyReport.report_date) == today,
        DailyReport.is_submitted == True
    ).count()
    daily_report_rate = (today_reports / total_students_with_team) * 100 if total_students_with_team > 0 else 0
    
    # 统计数据对象
    stats = {
        'total_students': total_students,
        'total_courses': total_courses,
        'total_scores': total_scores,
        'total_users': total_users,
        'total_projects': total_projects,
        'total_teams': total_teams,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'total_bugs': total_bugs,
        'daily_report_rate': daily_report_rate,
        'task_todo': task_todo,
        'task_in_progress': task_in_progress,
        'task_review': task_review,
        'task_done': task_done,
        'task_delayed': task_delayed
    }
    
    # 最近添加的学生
    recent_students = Student.query.order_by(Student.created_at.desc()).limit(5).all()
    
    # 最近项目
    recent_projects = Project.query.order_by(Project.created_at.desc()).limit(5).all()
    
    # 项目进度数据（用于图表）
    project_names = []
    project_progress = []
    projects = Project.query.all()
    for project in projects[:10]:
        project_names.append(project.name[:10] + '...' if len(project.name) > 10 else project.name)
        team_ids = [t.id for t in project.teams]
        if team_ids:
            team_tasks = Task.query.filter(Task.team_id.in_(team_ids)).all()
        else:
            team_tasks = []
        if team_tasks:
            completed = sum(1 for t in team_tasks if t.status == 'done')
            progress = (completed / len(team_tasks)) * 100
        else:
            progress = 0
        project_progress.append(round(progress, 1))
    
    # 最近操作日志
    recent_logs = Log.query.order_by(Log.created_at.desc()).limit(10).all()
    
    return render_template('system/dashboard.html',
                         stats=stats,
                         recent_students=recent_students,
                         recent_projects=recent_projects,
                         recent_logs=recent_logs,
                         project_names=project_names,
                         project_progress=project_progress)

# 用户管理
@system_bp.route('/users')
@login_required
@role_required('admin')
def users_list():
    # 多条件查询
    query = User.query
    
    # 查询参数
    username = request.args.get('username')
    name = request.args.get('name')
    role = request.args.get('role')
    
    if username:
        query = query.filter(User.username.like(f'%{username}%'))
    if name:
        query = query.filter(User.name.like(f'%{name}%'))
    if role:
        query = query.filter_by(role=role)
    
    # 分页
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(User.id.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    users = pagination.items
    
    return render_template('system/users.html', users=users, pagination=pagination)

# 添加用户
@system_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_user():
    form = RegisterForm()
    
    # 打印表单数据和错误信息用于调试
    if request.method == 'POST':
        print(f"表单提交数据: {request.form}")
        print(f"表单验证状态: {form.validate()}")
        print(f"表单错误: {form.errors}")
    
    if form.validate_on_submit():
        try:
            user = User(
                username=form.username.data,
                password=form.password.data,  # 会自动加密
                role=form.role.data,
                name=form.name.data,
                email=form.email.data,
                phone=form.phone.data
            )
            db.session.add(user)
            db.session.commit()
            
            # 记录日志
            log_action(current_user.id, 'create', 'users', f'添加用户：{user.username}（角色：{user.role}）')
            
            flash('用户添加成功', 'success')
            return redirect(url_for('system.users_list'))
        except Exception as e:
            # 回滚事务
            db.session.rollback()
            # 记录详细错误
            print(f"添加用户时发生错误: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            # 向用户显示友好错误信息
            flash('添加用户失败，请检查输入信息是否正确', 'danger')
    
    return render_template('system/add_user.html', form=form, title='添加用户')

# 删除用户
@system_bp.route('/users/delete/<int:user_id>')
@login_required
@role_required('admin')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # 不能删除自己
    if user.id == current_user.id:
        flash('不能删除当前登录用户', 'danger')
        return redirect(url_for('system.users_list'))
    
    username = user.username
    role = user.role
    
    # 如果是学生用户，同时删除对应的学生记录
    if role == 'student':
        from app.models import Student
        student = Student.query.filter_by(student_id=username).first()
        if student:
            db.session.delete(student)
    
    db.session.delete(user)
    db.session.commit()
    
    # 记录日志
    log_action(current_user.id, 'delete', 'users', f'删除用户：{username}（角色：{role}）')
    
    flash('用户删除成功', 'success')
    return redirect(url_for('system.users_list'))

# 批量删除用户
@system_bp.route('/users/batch_delete', methods=['POST'])
@login_required
@role_required('admin')
def batch_delete_users():
    from app.models import Student, Score, DailyReport, WorkLog, Bug, CodeCommit, AIAssistRecord, Deployment
    
    data = request.get_json()
    user_ids = data.get('user_ids', [])
    
    if not user_ids:
        return jsonify({'success': False, 'message': '请选择要删除的用户'})
    
    deleted_count = 0
    failed_users = []
    
    for user_id in user_ids:
        try:
            user = User.query.get(user_id)
            if not user:
                continue
            
            # 不能删除自己
            if user.id == current_user.id:
                failed_users.append(f'{user.username}（当前登录用户）')
                continue
            
            username = user.username
            role = user.role
            
            # 如果是学生用户，同时删除对应的学生记录及其关联数据
            if role == 'student':
                student = Student.query.filter_by(student_id=username).first()
                if student:
                    # 删除关联的成绩记录
                    Score.query.filter_by(student_id=student.id).delete()
                    # 删除关联的日报记录
                    DailyReport.query.filter_by(student_id=student.id).delete()
                    # 删除关联的工作日志
                    WorkLog.query.filter_by(student_id=student.id).delete()
                    # 删除关联的Bug
                    Bug.query.filter_by(reported_by=student.id).delete()
                    Bug.query.filter_by(assigned_to=student.id).delete()
                    # 删除关联的代码提交记录
                    CodeCommit.query.filter_by(student_id=student.id).delete()
                    # 删除关联的AI辅助记录
                    AIAssistRecord.query.filter_by(student_id=student.id).delete()
                    # 删除关联的部署记录
                    Deployment.query.filter_by(deployed_by=student.id).delete()
                    # 删除小组成员记录
                    from app.models import TeamMember
                    TeamMember.query.filter_by(student_id=student.id).delete()
                    # 删除学生
                    db.session.delete(student)
            
            db.session.delete(user)
            deleted_count += 1
            log_action(current_user.id, 'delete', 'users', f'批量删除用户：{username}（角色：{role}）')
        except Exception as e:
            failed_users.append(f'{username}（错误：{str(e)}）')
    
    db.session.commit()
    
    message = f'成功删除 {deleted_count} 个用户'
    if failed_users:
        message += f'，失败 {len(failed_users)} 个：{", ".join(failed_users)}'
    
    return jsonify({'success': True, 'message': message})

# 编辑用户
@system_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = RegisterForm(obj=user, user_id=user_id)
    
    # 禁用密码字段和确认密码字段的验证
    form.password.validators = []
    form.confirm_password.validators = []
    
    # 打印表单数据和错误信息用于调试
    if request.method == 'POST':
        print(f"表单提交数据: {request.form}")
        print(f"表单验证状态: {form.validate()}")
        print(f"表单错误: {form.errors}")
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.name = form.name.data
        user.role = form.role.data
        user.email = form.email.data
        user.phone = form.phone.data
        
        # 只有当密码字段有值时才更新密码
        if form.password.data:
            user.password = form.password.data
        
        db.session.commit()
        
        # 记录日志
        log_action(current_user.id, 'update', 'users', f'编辑用户：{user.username}（角色：{user.role}）')
        
        flash('用户信息更新成功', 'success')
        return redirect(url_for('system.users_list'))
    
    # 设置初始值
    form.username.data = user.username
    form.name.data = user.name
    form.role.data = user.role
    form.email.data = user.email
    form.phone.data = user.phone
    
    return render_template('system/edit_user.html', form=form, user=user, title='编辑用户')

# 操作日志
@system_bp.route('/logs')
@login_required
@role_required('admin')
def logs_list():
    # 多条件查询
    query = Log.query
    
    # 查询参数
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action')
    resource = request.args.get('resource')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    if action:
        query = query.filter(Log.action.like(f'%{action}%'))
    if resource:
        query = query.filter(Log.resource.like(f'%{resource}%'))
    if start_date:
        query = query.filter(Log.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        # 加上一天，包含结束日期的所有记录
        end_date_dt = datetime.strptime(end_date, '%Y-%m-%d')
        end_date_dt = end_date_dt.replace(hour=23, minute=59, second=59)
        query = query.filter(Log.created_at <= end_date_dt)
    
    # 分页
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(Log.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    logs = pagination.items
    
    # 加载用户选项
    users = User.query.all()
    
    return render_template('system/logs.html', logs=logs, pagination=pagination, users=users)

# 数据备份
@system_bp.route('/backup')
@login_required
@role_required('admin')
def backup_data():
    try:
        # 从配置中获取数据库连接信息
        db_url = current_app.config['SQLALCHEMY_DATABASE_URI']
        
        # 解析数据库连接信息
        import urllib.parse
        result = urllib.parse.urlparse(db_url)
        db_name = result.path[1:]
        username = result.username
        password = result.password
        hostname = result.hostname
        port = result.port or 3306
        
        # 生成备份文件名
        backup_filename = f'backup_{db_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
        
        # 使用mysqldump命令备份数据库
        cmd = [
            'mysqldump',
            '-h', hostname,
            '-u', username,
            '-p' + password,  # 注意这里没有空格
            '-P', str(port),
            db_name,
            '--single-transaction',
            '--quick',
            '--lock-tables=false'
        ]
        
        # 执行备份命令
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            flash(f'备份失败：{stderr.decode("gbk")}', 'danger')
            return redirect(url_for('system.dashboard'))
        
        # 创建备份文件的BytesIO对象
        backup_io = io.BytesIO(stdout)
        backup_io.seek(0)
        
        # 记录日志
        log_action(current_user.id, 'backup', 'database', '数据库备份成功')
        
        # 提供下载
        return send_file(
            backup_io,
            as_attachment=True,
            download_name=backup_filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        flash(f'备份失败：{str(e)}', 'danger')
        return redirect(url_for('system.dashboard'))

# 数据恢复
@system_bp.route('/restore', methods=['POST'])
@login_required
@role_required('admin')
def restore_data():
    try:
        # 检查是否有文件上传
        if 'backup_file' not in request.files:
            flash('请选择备份文件', 'danger')
            return redirect(url_for('system.system_settings'))
        
        backup_file = request.files['backup_file']
        
        # 检查文件是否为空
        if backup_file.filename == '':
            flash('请选择备份文件', 'danger')
            return redirect(url_for('system.system_settings'))
        
        # 检查文件格式
        if not backup_file.filename.endswith('.sql'):
            flash('只支持.sql格式的备份文件', 'danger')
            return redirect(url_for('system.system_settings'))
        
        # 从配置中获取数据库连接信息
        db_url = current_app.config['SQLALCHEMY_DATABASE_URI']
        
        # 解析数据库连接信息
        import urllib.parse
        result = urllib.parse.urlparse(db_url)
        db_name = result.path[1:]
        username = result.username
        password = result.password
        hostname = result.hostname
        port = result.port or 3306
        
        # 使用mysql命令恢复数据库
        cmd = [
            'mysql',
            '-h', hostname,
            '-u', username,
            '-p' + password,  # 注意这里没有空格
            '-P', str(port),
            db_name
        ]
        
        # 读取备份文件内容
        backup_content = backup_file.read()
        
        # 执行恢复命令
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate(input=backup_content)
        
        if process.returncode != 0:
            flash(f'恢复失败：{stderr.decode("gbk")}', 'danger')
            return redirect(url_for('system.system_settings'))
        
        # 记录日志
        log_action(current_user.id, 'restore', 'database', '数据库恢复成功')
        
        flash('数据恢复成功', 'success')
        return redirect(url_for('system.system_settings'))
        
    except Exception as e:
        flash(f'恢复失败：{str(e)}', 'danger')
        return redirect(url_for('system.system_settings'))

# 系统设置
@system_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def system_settings():
    # 导入表单
    from app.forms.system import SystemSettingsForm
    
    # 获取或创建系统设置
    settings = SystemSettings.query.first()
    if not settings:
        settings = SystemSettings()
        db.session.add(settings)
        db.session.commit()
    
    form = SystemSettingsForm(obj=settings)
    
    if form.validate_on_submit():
        try:
            # 更新系统设置
            settings.site_name = form.site_name.data
            settings.site_description = form.site_description.data
            settings.site_keywords = form.site_keywords.data
            settings.contact_email = form.contact_email.data
            settings.contact_phone = form.contact_phone.data
            settings.max_upload_size = form.max_upload_size.data
            settings.per_page = form.per_page.data
            settings.bcrypt_log_rounds = form.bcrypt_log_rounds.data
            
            db.session.commit()
            
            # 更新应用配置
            current_app.config['PER_PAGE'] = settings.per_page
            current_app.config['BCRYPT_LOG_ROUNDS'] = settings.bcrypt_log_rounds
            current_app.config['MAX_CONTENT_LENGTH'] = settings.max_upload_size * 1024 * 1024
            
            flash('系统设置已更新', 'success')
            
            # 记录日志
            log_action(current_user.id, 'update', 'settings', '更新系统基本信息设置')
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新设置失败：{str(e)}', 'danger')
        
        return redirect(url_for('system.system_settings'))
    
    # 当前时间
    from datetime import datetime
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('system/settings.html', form=form, settings=settings, current_time=current_time)

# 系统信息
@system_bp.route('/info')
@login_required
def system_info():
    import platform
    import sys
    import pkg_resources
    
    # 系统信息
    system_info = {
        'os': f'{platform.system()} {platform.release()}',
        'python': sys.version,
        'flask': pkg_resources.get_distribution('flask').version,
        'sqlalchemy': pkg_resources.get_distribution('flask-sqlalchemy').version,
        'mysql': pkg_resources.get_distribution('pymysql').version,
        'bootstrap': '5.3.2',
        'jquery': '3.6.0'
    }
    
    return render_template('system/info.html', system_info=system_info)