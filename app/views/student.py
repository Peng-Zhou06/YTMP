from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from app import db
from app.models import Student, User, Department, Major
from app.forms.student import StudentForm, ImportForm
from app.utils.decorators import roles_required
from app.utils.logs import log_action
import pandas as pd
import io
from datetime import datetime
from collections import defaultdict

# 创建蓝图
student_bp = Blueprint('student', __name__)

# 学生列表（管理员和教师可访问）
@student_bp.route('/students', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'teacher')
def students_list():
    # 获取所有学院和专业
    departments = Department.query.filter_by(is_active=True).order_by(Department.sort_order, Department.name).all()
    
    # 获取所有学生
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = Student.query.order_by(Student.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    students = pagination.items
    
    # 按 学院 -> 专业 -> 年级 -> 班级 组织数据
    dept_students = {}
    for dept in departments:
        dept_students[dept.name] = {'total': 0, 'id': dept.id, 'icon': dept.icon}
        for major in dept.majors:
            if major.is_active:
                dept_students[dept.name][major.name] = {
                    'total': 0,
                    'id': major.id,
                    'grades': defaultdict(lambda: {'total': 0, 'classes': defaultdict(int)})
                }
    
    for student in students:
        dept = student.department or ''
        major = student.major or ''
        grade = student.grade or '未分级'
        class_name = student.class_name or '未分班'
        
        if dept in dept_students and major in dept_students[dept]:
            # 学院总数
            dept_students[dept]['total'] += 1
            # 专业总数
            dept_students[dept][major]['total'] += 1
            # 年级数据
            grade_data = dept_students[dept][major]['grades'][grade]
            grade_data['total'] += 1
            grade_data['classes'][class_name] += 1
    
    return render_template('student/students_groups.html', departments=departments, dept_students=dept_students)

# 按班级查看学生
@student_bp.route('/students/class/<department>/<major>/<class_name>')
@login_required
@roles_required('admin', 'teacher')
def students_by_class(department, major, class_name):
    # 获取该班级的所有学生
    students = Student.query.filter_by(department=department, major=major, class_name=class_name).order_by(Student.id.desc()).all()
    
    return render_template('student/students_list.html', students=students,
                         department=department, major=major, class_name=class_name)

# 添加学生
@student_bp.route('/students/add', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def add_student():
    form = StudentForm()
    if form.validate_on_submit():
        try:
            print(f"[DEBUG ADD] 表单验证通过")
            print(f"[DEBUG ADD] 表单数据: {form.data}")
            
            student = Student(
                student_id=form.student_id.data,
                name=form.name.data,
                gender=form.gender.data,
                grade=form.grade.data,
                birthday=form.birthday.data,
                class_name=form.class_name.data,
                major=form.major.data,
                department=form.department.data,
                email=form.email.data,
                phone=form.phone.data,
                address=form.address.data
            )
            db.session.add(student)
            
            # 创建对应的用户记录
            # 检查邮箱是否已存在
            existing_user = User.query.filter_by(email=form.email.data).first()
            if existing_user:
                # 如果邮箱已存在，使用学号+@student.com作为替代邮箱
                user_email = f"{form.student_id.data}@student.com"
            else:
                user_email = form.email.data
            
            print(f"[DEBUG ADD] 准备创建User记录，邮箱: {user_email}")
            
            user = User(
                username=form.student_id.data,
                role='student',
                name=form.name.data,
                email=user_email
            )
            user.password = '123456'  # 显式设置默认密码
            db.session.add(user)
            
            db.session.commit()
            
            # 记录日志
            log_action(current_user.id, 'create', 'students', f'添加学生：{student.name}（学号：{student.student_id}）')
            
            flash('学生添加成功', 'success')
            return redirect(url_for('student.students_list'))
        except Exception as e:
            db.session.rollback()
            print(f"[DEBUG ADD] 保存失败: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'添加学生失败：{str(e)}', 'danger')
    else:
        if request.method == 'POST':
            print(f"[DEBUG ADD] 表单验证失败")
            print(f"[DEBUG ADD] 表单错误: {form.errors}")
    
    # 构建学院专业JSON供前端使用
    import json
    departments_data = {}
    for dept in Department.query.filter_by(is_active=True).order_by(Department.sort_order, Department.name).all():
        departments_data[dept.name] = [m.name for m in dept.majors if m.is_active]
    departments_json = json.dumps(departments_data)
    return render_template('student/students_add.html', form=form, departments_json=departments_json)

# 编辑学生
@student_bp.route('/students/edit/<int:student_id>', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    form = StudentForm(obj=student)
    
    # 设置表单对象引用，用于验证
    form._obj = student
    
    if form.validate_on_submit():
        try:
            print(f"[DEBUG EDIT] 表单验证通过")
            print(f"[DEBUG EDIT] 表单数据: {form.data}")
            
            form.populate_obj(student)
            
            # 更新对应的用户记录
            user = User.query.filter_by(username=student.student_id).first()
            if user:
                user.name = form.name.data
                
                # 检查邮箱是否已被其他用户使用
                existing_user = User.query.filter(User.email == form.email.data, User.id != user.id).first()
                if existing_user:
                    # 如果邮箱已存在，使用学号+@student.com作为替代邮箱
                    user.email = f"{student.student_id}@student.com"
                else:
                    user.email = form.email.data
            
            db.session.commit()
            
            # 记录日志
            log_action(current_user.id, 'update', 'students', f'编辑学生：{student.name}（学号：{student.student_id}）')
            
            flash('学生信息更新成功', 'success')
            return redirect(url_for('student.students_list'))
        except Exception as e:
            db.session.rollback()
            print(f"[DEBUG EDIT] 保存失败: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'更新学生信息失败：{str(e)}', 'danger')
    else:
        if request.method == 'POST':
            print(f"[DEBUG EDIT] 表单验证失败")
            print(f"[DEBUG EDIT] 表单错误: {form.errors}")
    
    import json
    departments_data = {}
    for dept in Department.query.filter_by(is_active=True).order_by(Department.sort_order, Department.name).all():
        departments_data[dept.name] = [m.name for m in dept.majors if m.is_active]
    departments_json = json.dumps(departments_data)
    return render_template('student/students_edit.html', form=form, student=student, departments_json=departments_json)

# 删除学生
@student_bp.route('/students/delete/<int:student_id>')
@login_required
@roles_required('admin')
def delete_student(student_id):
    from app.models import TeamMember, Score, DailyReport, WorkLog, Bug, CodeCommit, AIAssistRecord, Deployment
    
    student = Student.query.get_or_404(student_id)
    name = student.name
    student_id_str = student.student_id
    
    # 先删除关联的成绩记录
    Score.query.filter_by(student_id=student.id).delete()
    
    # 删除关联的日报记录
    DailyReport.query.filter_by(student_id=student.id).delete()
    
    # 删除关联的工作日志
    WorkLog.query.filter_by(student_id=student.id).delete()
    
    # 删除关联的Bug（报告的）
    Bug.query.filter_by(reported_by=student.id).delete()
    
    # 删除关联的Bug（分配的）
    Bug.query.filter_by(assigned_to=student.id).delete()
    
    # 删除关联的代码提交记录
    CodeCommit.query.filter_by(student_id=student.id).delete()
    
    # 删除关联的AI辅助记录
    AIAssistRecord.query.filter_by(student_id=student.id).delete()
    
    # 删除关联的部署记录
    Deployment.query.filter_by(deployed_by=student.id).delete()
    
    # 删除关联的小组成员记录
    TeamMember.query.filter_by(student_id=student.id).delete()
    
    # 删除对应的用户记录
    user = User.query.filter_by(username=student_id_str).first()
    if user:
        db.session.delete(user)
    
    # 删除学生
    db.session.delete(student)
    db.session.commit()
    
    # 记录日志
    log_action(current_user.id, 'delete', 'students', f'删除学生：{name}（学号：{student_id_str}）')
    
    flash('学生删除成功', 'success')
    return redirect(url_for('student.students_list'))

# 导出学生数据
@student_bp.route('/students/export')
@login_required
@roles_required('admin')
def export_students():
    students = Student.query.all()
    
    # 准备导出数据
    data = {
        '学号': [s.student_id for s in students],
        '姓名': [s.name for s in students],
        '性别': [s.gender for s in students],
        '出生日期': [s.birthday.strftime('%Y-%m-%d') if s.birthday else '' for s in students],
        '班级': [s.class_name for s in students],
        '专业': [s.major for s in students],
        '学院': [s.department for s in students],
        '邮箱': [s.email for s in students],
        '电话': [s.phone for s in students],
        '地址': [s.address for s in students],
        '创建时间': [s.created_at.strftime('%Y-%m-%d %H:%M:%S') for s in students]
    }
    
    df = pd.DataFrame(data)
    
    # 生成Excel文件
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='学生信息')
    
    output.seek(0)
    
    # 记录日志
    log_action(current_user.id, 'export', 'students', f'导出学生数据，共{len(students)}条')
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f'学生信息_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# 批量删除学生
@student_bp.route('/students/batch_delete', methods=['POST'])
@login_required
@roles_required('admin')
def students_batch_delete():
    ids = request.form.getlist('ids', type=int)
    if not ids:
        flash('请选择要删除的学生', 'warning')
        return redirect(url_for('student.students_list'))
    
    try:
        students_to_delete = Student.query.filter(Student.id.in_(ids)).all()
        for student in students_to_delete:
            # 删除对应的用户记录
            user = User.query.filter_by(username=student.student_id).first()
            if user:
                db.session.delete(user)
            # 删除学生记录
            db.session.delete(student)
        db.session.commit()
        
        # 记录日志
        log_action(current_user.id, 'batch_delete', 'students', f'批量删除学生，共{len(ids)}条记录')
        
        flash(f'成功删除{len(ids)}名学生', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'批量删除失败：{str(e)}', 'danger')
    
    return redirect(url_for('student.students_list'))

# 导入学生数据
@student_bp.route('/students/import', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def import_students():
    form = ImportForm()
    if form.validate_on_submit():
        file = form.file.data
        overwrite = form.overwrite.data
        
        try:
            # 读取Excel文件
            df = pd.read_excel(file)
            
            # 验证必要列
            required_columns = ['学号', '姓名', '性别', '年级', '出生日期', '班级', '专业', '学院', '邮箱']
            for col in required_columns:
                if col not in df.columns:
                    flash(f'文件缺少必要列：{col}', 'danger')
                    return redirect(request.url)
            
            # 导入数据
            imported_count = 0
            updated_count = 0
            for index, row in df.iterrows():
                # 检查学号是否已存在
                existing_student = Student.query.filter_by(student_id=row['学号']).first()
                
                if existing_student:
                    if overwrite:
                        # 更新现有学生信息
                        existing_student.name = row['姓名']
                        existing_student.gender = row['性别']
                        existing_student.grade = row['年级'] if '年级' in df.columns and pd.notna(row['年级']) else existing_student.grade
                        existing_student.birthday = pd.to_datetime(row['出生日期']).date() if pd.notna(row['出生日期']) else None
                        existing_student.class_name = row['班级']
                        existing_student.major = row['专业']
                        existing_student.department = row['学院']
                        existing_student.email = row['邮箱']
                        existing_student.phone = row['电话'] if '电话' in df.columns and pd.notna(row['电话']) else None
                        existing_student.address = row['地址'] if '地址' in df.columns and pd.notna(row['地址']) else None
                        updated_count += 1
                        
                        # 更新对应的用户记录
                        user = User.query.filter_by(username=row['学号']).first()
                        if user:
                            user.name = row['姓名']
                            user.email = row['邮箱']
                else:
                    # 添加新学生
                    student = Student(
                        student_id=row['学号'],
                        name=row['姓名'],
                        gender=row['性别'],
                        grade=row['年级'] if '年级' in df.columns and pd.notna(row['年级']) else '',
                        birthday=pd.to_datetime(row['出生日期']).date() if pd.notna(row['出生日期']) else None,
                        class_name=row['班级'],
                        major=row['专业'],
                        department=row['学院'],
                        email=row['邮箱'],
                        phone=row['电话'] if '电话' in df.columns and pd.notna(row['电话']) else None,
                        address=row['地址'] if '地址' in df.columns and pd.notna(row['地址']) else None
                    )
                    db.session.add(student)
                    imported_count += 1
                    
                    # 创建对应的用户记录
                    try:
                        # 检查邮箱是否已存在
                        existing_user = User.query.filter_by(email=row['邮箱']).first()
                        if existing_user:
                            # 如果邮箱已存在，使用学号+@student.com作为替代邮箱
                            user_email = f"{row['学号']}@student.com"
                        else:
                            user_email = row['邮箱']
                        
                        user = User(
                            username=row['学号'],
                            role='student',
                            name=row['姓名'],
                            email=user_email
                        )
                        user.password = '123456'  # 显式设置默认密码
                        db.session.add(user)
                    except Exception as e:
                        # 如果仍然失败，使用学号+@student.com作为替代邮箱
                        user_email = f"{row['学号']}@student.com"
                        user = User(
                            username=row['学号'],
                            role='student',
                            name=row['姓名'],
                            email=user_email
                        )
                        user.password = '123456'  # 显式设置默认密码
                        db.session.add(user)
            
            db.session.commit()
            
            # 记录日志
            log_action(current_user.id, 'import', 'students', f'导入学生数据，成功导入{imported_count}条，更新{updated_count}条')
            
            flash(f'导入成功，共导入{imported_count}条，更新{updated_count}条学生信息', 'success')
        except Exception as e:
            flash(f'导入失败：{str(e)}', 'danger')
        
        return redirect(url_for('student.students_list'))
    
    return render_template('student/students_import.html', form=form)

# 导出学生导入模板
@student_bp.route('/students/export_template')
@login_required
@roles_required('admin')
def export_students_template():
    # 创建模板数据
    template_data = {
        '学号': ['S001', 'S002'],
        '姓名': ['张三', '李四'],
        '性别': ['男', '女'],
        '出生日期': ['2000-01-01', '2000-02-02'],
        '班级': ['计算机1班', '计算机2班'],
        '专业': ['计算机科学与技术', '软件工程'],
        '学院': ['信息学院', '信息学院'],
        '邮箱': ['zhangsan@example.com', 'lisi@example.com'],
        '电话': ['13800138001', '13900139001'],
        '地址': ['北京市海淀区', '上海市浦东新区']
    }
    
    df = pd.DataFrame(template_data)
    
    # 生成Excel文件
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='学生模板')
    
    output.seek(0)
    
    # 记录日志
    log_action(current_user.id, 'export_template', 'students', '导出学生导入模板')
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f'学生导入模板_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )