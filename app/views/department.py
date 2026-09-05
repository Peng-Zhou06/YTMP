from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Department, Major
from app.utils.decorators import roles_required
from app.utils.logs import log_action

# 创建蓝图
dept_bp = Blueprint('dept', __name__)

# 学院专业管理首页
@dept_bp.route('/departments', methods=['GET'])
@login_required
@roles_required('admin')
def departments_list():
    departments = Department.query.order_by(Department.sort_order, Department.name).all()
    return render_template('system/departments.html', departments=departments)

# 添加学院
@dept_bp.route('/departments/add', methods=['POST'])
@login_required
@roles_required('admin')
def add_department():
    name = request.form.get('name', '').strip()
    icon = request.form.get('icon', 'fa-building').strip()
    sort_order = request.form.get('sort_order', 0, type=int)
    
    if not name:
        flash('学院名称不能为空', 'danger')
        return redirect(url_for('dept.departments_list'))
    
    # 检查是否已存在
    existing = Department.query.filter_by(name=name).first()
    if existing:
        flash('该学院已存在', 'warning')
        return redirect(url_for('dept.departments_list'))
    
    dept = Department(name=name, icon=icon, sort_order=sort_order)
    db.session.add(dept)
    db.session.commit()
    
    log_action(current_user.id, 'create', 'departments', f'添加学院：{name}')
    flash('学院添加成功', 'success')
    return redirect(url_for('dept.departments_list'))

# 编辑学院
@dept_bp.route('/departments/edit/<int:dept_id>', methods=['POST'])
@login_required
@roles_required('admin')
def edit_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    
    name = request.form.get('name', '').strip()
    icon = request.form.get('icon', 'fa-building').strip()
    sort_order = request.form.get('sort_order', 0, type=int)
    is_active = request.form.get('is_active') == 'on'
    
    if not name:
        flash('学院名称不能为空', 'danger')
        return redirect(url_for('dept.departments_list'))
    
    # 检查名称是否重复（排除自己）
    existing = Department.query.filter(Department.name == name, Department.id != dept_id).first()
    if existing:
        flash('该学院名称已存在', 'warning')
        return redirect(url_for('dept.departments_list'))
    
    old_name = dept.name
    dept.name = name
    dept.icon = icon
    dept.sort_order = sort_order
    dept.is_active = is_active
    db.session.commit()
    
    log_action(current_user.id, 'update', 'departments', f'编辑学院：{old_name} -> {name}')
    flash('学院修改成功', 'success')
    return redirect(url_for('dept.departments_list'))

# 删除学院
@dept_bp.route('/departments/delete/<int:dept_id>', methods=['POST'])
@login_required
@roles_required('admin')
def delete_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    
    # 检查是否有专业
    if dept.majors:
        flash('该学院下还有专业，请先删除专业', 'warning')
        return redirect(url_for('dept.departments_list'))
    
    name = dept.name
    db.session.delete(dept)
    db.session.commit()
    
    log_action(current_user.id, 'delete', 'departments', f'删除学院：{name}')
    flash('学院删除成功', 'success')
    return redirect(url_for('dept.departments_list'))

# 添加专业
@dept_bp.route('/departments/<int:dept_id>/majors/add', methods=['POST'])
@login_required
@roles_required('admin')
def add_major(dept_id):
    dept = Department.query.get_or_404(dept_id)
    
    name = request.form.get('name', '').strip()
    sort_order = request.form.get('sort_order', 0, type=int)
    
    if not name:
        flash('专业名称不能为空', 'danger')
        return redirect(url_for('dept.departments_list'))
    
    # 检查是否已存在
    existing = Major.query.filter_by(department_id=dept_id, name=name).first()
    if existing:
        flash('该专业已存在', 'warning')
        return redirect(url_for('dept.departments_list'))
    
    major = Major(department_id=dept_id, name=name, sort_order=sort_order)
    db.session.add(major)
    db.session.commit()
    
    log_action(current_user.id, 'create', 'majors', f'为学院{dept.name}添加专业：{name}')
    flash('专业添加成功', 'success')
    return redirect(url_for('dept.departments_list'))

# 编辑专业
@dept_bp.route('/majors/edit/<int:major_id>', methods=['POST'])
@login_required
@roles_required('admin')
def edit_major(major_id):
    major = Major.query.get_or_404(major_id)
    
    name = request.form.get('name', '').strip()
    sort_order = request.form.get('sort_order', 0, type=int)
    is_active = request.form.get('is_active') == 'on'
    
    if not name:
        flash('专业名称不能为空', 'danger')
        return redirect(url_for('dept.departments_list'))
    
    # 检查名称是否重复（排除自己）
    existing = Major.query.filter(Major.department_id == major.department_id, Major.name == name, Major.id != major_id).first()
    if existing:
        flash('该专业名称已存在', 'warning')
        return redirect(url_for('dept.departments_list'))
    
    old_name = major.name
    major.name = name
    major.sort_order = sort_order
    major.is_active = is_active
    db.session.commit()
    
    log_action(current_user.id, 'update', 'majors', f'编辑专业：{old_name} -> {name}')
    flash('专业修改成功', 'success')
    return redirect(url_for('dept.departments_list'))

# 删除专业
@dept_bp.route('/majors/delete/<int:major_id>', methods=['POST'])
@login_required
@roles_required('admin')
def delete_major(major_id):
    major = Major.query.get_or_404(major_id)
    
    name = major.name
    dept_name = major.department.name
    db.session.delete(major)
    db.session.commit()
    
    log_action(current_user.id, 'delete', 'majors', f'删除专业：{name}（{dept_name}）')
    flash('专业删除成功', 'success')
    return redirect(url_for('dept.departments_list'))

# 获取学院的专业列表（API）
@dept_bp.route('/api/departments/<int:dept_id>/majors')
@login_required
def get_majors(dept_id):
    majors = Major.query.filter_by(department_id=dept_id, is_active=True).order_by(Major.sort_order, Major.name).all()
    return jsonify([{'id': m.id, 'name': m.name} for m in majors])

# 获取所有学院专业（API）
@dept_bp.route('/api/departments')
@login_required
def get_all_departments():
    departments = Department.query.filter_by(is_active=True).order_by(Department.sort_order, Department.name).all()
    result = []
    for dept in departments:
        majors = Major.query.filter_by(department_id=dept.id, is_active=True).order_by(Major.sort_order, Major.name).all()
        result.append({
            'id': dept.id,
            'name': dept.name,
            'majors': [{'id': m.id, 'name': m.name} for m in majors]
        })
    return jsonify(result)