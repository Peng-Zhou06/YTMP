from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from app import db
from app.models import Course, User, Score, Project, Student
from app.forms.course import CourseForm, ProjectForm
from app.utils.decorators import roles_required
from app.utils.logs import log_action
import pandas as pd
import io
from datetime import datetime
from sqlalchemy import func

# 创建蓝图
course_bp = Blueprint('course', __name__)

# 课程列表（管理员可查看所有课程，教师可查看自己的课程）
@course_bp.route('/courses', methods=['GET', 'POST'])
@login_required
def courses_list():
    # 根据角色确定查询范围
    if current_user.role == 'admin':
        query = Course.query
    else:
        query = Course.query.filter_by(teacher_id=current_user.id)
    
    # 查询参数
    course_code = request.args.get('course_code')
    course_name = request.args.get('course_name')
    semester = request.args.get('semester')
    year = request.args.get('year', type=int)
    teacher_id = request.args.get('teacher_id', type=int)
    
    if course_code:
        query = query.filter(Course.course_code.like(f'%{course_code}%'))
    if course_name:
        query = query.filter(Course.course_name.like(f'%{course_name}%'))
    if semester:
        query = query.filter_by(semester=semester)
    if year:
        query = query.filter_by(year=year)
    if teacher_id:
        query = query.filter_by(teacher_id=teacher_id)
    
    # 分页
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(Course.id.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    courses = pagination.items
    
    # 为每门课程添加学生数量
    for course in courses:
        # 计算该课程的学生数量（通过Score表统计）
        student_count = Score.query.filter_by(course_id=course.id).count()
        course.student_count = student_count
    
    # 教师列表（用于筛选）
    teachers = User.query.filter_by(role='teacher').all()
    
    return render_template('course/courses_list.html', courses=courses, pagination=pagination, teachers=teachers)

# 教师课程列表
@course_bp.route('/teacher/courses')
@login_required
@roles_required('teacher')
def teacher_courses():
    # 基础查询
    query = Course.query.filter_by(teacher_id=current_user.id)
    
    # 查询参数
    course_code = request.args.get('course_code')
    course_name = request.args.get('course_name')
    semester = request.args.get('semester')
    year = request.args.get('year', type=int)
    
    if course_code:
        query = query.filter(Course.course_code.like(f'%{course_code}%'))
    if course_name:
        query = query.filter(Course.course_name.like(f'%{course_name}%'))
    if semester:
        query = query.filter_by(semester=semester)
    if year:
        query = query.filter_by(year=year)
    
    # 分页
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(Course.id.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    courses = pagination.items
    
    # 为每门课程添加学生数量
    for course in courses:
        # 计算该课程的学生数量（通过Score表统计）
        student_count = Score.query.filter_by(course_id=course.id).count()
        course.student_count = student_count
    
    return render_template('course/teacher_courses.html', courses=courses, pagination=pagination)

# 学生我的课程
@course_bp.route('/my-courses')
@login_required
def my_courses():
    from app.models import Student
    
    student = Student.query.filter_by(student_id=current_user.username).first()
    if not student:
        flash('未找到您的学生信息', 'warning')
        return redirect(url_for('auth.profile'))
    
    # 获取学生已加入的课程（通过成绩表关联）
    scores = Score.query.filter_by(student_id=student.id).all()
    course_ids = [s.course_id for s in scores]
    courses = Course.query.filter(Course.id.in_(course_ids)).all() if course_ids else []
    
    return render_template('course/my_courses.html', courses=courses)

# 学生加入课程
@course_bp.route('/courses/join', methods=['POST'])
@login_required
def join_course():
    from app.models import Student
    
    student = Student.query.filter_by(student_id=current_user.username).first()
    if not student:
        flash('未找到您的学生信息', 'warning')
        return redirect(url_for('course.my_courses'))
    
    course_code = request.form.get('course_code')
    course = Course.query.filter_by(course_code=course_code).first()
    
    if not course:
        flash('课程编号不存在', 'danger')
        return redirect(url_for('course.my_courses'))
    
    # 检查是否已加入
    existing = Score.query.filter_by(student_id=student.id, course_id=course.id).first()
    if existing:
        flash('您已加入该课程', 'warning')
        return redirect(url_for('course.my_courses'))
    
    # 添加成绩记录（初始成绩为0）
    new_score = Score(
        student_id=student.id,
        course_id=course.id,
        score=0,
        semester=course.semester,
        year=course.year
    )
    db.session.add(new_score)
    db.session.commit()
    
    log_action(current_user.id, 'create', 'scores', f'学生{student.name}通过课程编号加入课程{course.course_name}')
    
    flash(f'成功加入课程：{course.course_name}', 'success')
    return redirect(url_for('course.my_courses'))

# 课程详情
@course_bp.route('/courses/<int:course_id>')
@login_required
def course_detail(course_id):
    from app.models import CourseDocument, Department, Major
    import json
    
    course = Course.query.get_or_404(course_id)
    
    # 获取该课程的所有成绩记录
    scores = Score.query.filter_by(course_id=course.id).all()
    
    # 按班级统计学生
    from app.models import Student
    class_students = {}
    for score in scores:
        student = Student.query.get(score.student_id)
        if student:
            class_name = student.class_name or '未分班'
            if class_name not in class_students:
                class_students[class_name] = []
            class_students[class_name].append({
                'student': student,
                'score': score.score
            })
    
    # 获取课程资料
    documents = CourseDocument.query.filter_by(course_id=course.id).order_by(CourseDocument.created_at.desc()).all()
    
    # 按 学院-专业-班级 分组所有学生（用于添加班级时选择）
    all_classes = {}
    all_students = Student.query.order_by(Student.department, Student.major, Student.class_name, Student.name).all()
    for student in all_students:
        dept = student.department or '未分学院'
        major = student.major or '未分专业'
        class_key = student.class_name or '未分班'
        full_key = f"{dept} - {major} - {class_key}班"
        if full_key not in all_classes:
            all_classes[full_key] = []
        all_classes[full_key].append({
            'name': student.name,
            'student_id': student.student_id
        })
    
    # 转换为JSON供前端使用
    all_classes_json = json.dumps(all_classes)
    
    # 获取所有学院和专业（用于筛选）
    departments = Department.query.filter_by(is_active=True).order_by(Department.sort_order).all()
    dept_majors = {}
    for dept in departments:
        dept_majors[dept.name] = [m.name for m in dept.majors if m.is_active]
    dept_majors_json = json.dumps(dept_majors)
    
    # 获取讨论（只获取主讨论，不包括回复）
    from app.models import CourseDiscussion
    discussions = CourseDiscussion.query.filter_by(course_id=course.id, parent_id=None).order_by(CourseDiscussion.created_at.desc()).all()
    
    return render_template('course/course_detail.html', course=course, class_students=class_students, documents=documents, all_classes=all_classes, all_classes_json=all_classes_json, dept_majors_json=dept_majors_json, discussions=discussions)

# 添加学生到课程
@course_bp.route('/courses/<int:course_id>/add_student', methods=['POST'])
@login_required
@roles_required('admin', 'teacher')
def add_student_to_course(course_id):
    from app.models import Student
    
    course = Course.query.get_or_404(course_id)
    
    # 检查权限
    if current_user.role == 'teacher' and course.teacher_id != current_user.id:
        flash('没有权限添加学生到该课程', 'danger')
        return redirect(url_for('course.course_detail', course_id=course_id))
    
    student_id = request.form.get('student_id', type=int)
    
    if not student_id:
        flash('请选择学生', 'warning')
        return redirect(url_for('course.course_detail', course_id=course_id))
    
    # 检查学生是否存在
    student = Student.query.get(student_id)
    if not student:
        flash('学生不存在', 'danger')
        return redirect(url_for('course.course_detail', course_id=course_id))
    
    # 检查是否已存在
    existing = Score.query.filter_by(student_id=student_id, course_id=course_id).first()
    if existing:
        flash('该学生已在该课程中', 'warning')
        return redirect(url_for('course.course_detail', course_id=course_id))
    
    # 添加成绩记录（初始成绩为0，后续在成绩管理处录入）
    new_score = Score(
        student_id=student_id,
        course_id=course_id,
        score=0,
        semester=course.semester,
        year=course.year
    )
    db.session.add(new_score)
    db.session.commit()
    
    log_action(current_user.id, 'create', 'scores', f'为学生{student.name}（{student.student_id}）添加课程{course.course_name}的成绩')
    
    flash(f'成功添加学生{student.name}到课程', 'success')
    return redirect(url_for('course.course_detail', course_id=course_id))

# 添加班级到课程
@course_bp.route('/courses/<int:course_id>/add_class', methods=['POST'])
@login_required
@roles_required('admin', 'teacher')
def add_class_to_course(course_id):
    from app.models import Student
    
    course = Course.query.get_or_404(course_id)
    
    # 检查权限
    if current_user.role == 'teacher' and course.teacher_id != current_user.id:
        flash('没有权限添加班级到该课程', 'danger')
        return redirect(url_for('course.course_detail', course_id=course_id))
    
    class_key = request.form.get('class_key')
    
    if not class_key:
        flash('请选择班级', 'warning')
        return redirect(url_for('course.course_detail', course_id=course_id))
    
    # 解析class_key格式："学院 - 专业 - 班级班"
    # 提取班级名称（去掉"班"字）
    parts = class_key.split(' - ')
    if len(parts) >= 3:
        department = parts[0]
        major = parts[1]
        class_name = parts[2].replace('班', '')
    else:
        # 兼容旧格式
        class_name = class_key
        department = None
        major = None
    
    # 查找该班级的所有学生（优先使用完整条件，如果没找到则只用班级名称）
    if department and major:
        students = Student.query.filter_by(department=department, major=major, class_name=class_name).all()
        # 如果没找到，尝试只用班级名称查询
        if not students:
            students = Student.query.filter_by(class_name=class_name).all()
    else:
        students = Student.query.filter_by(class_name=class_name).all()
    
    if not students:
        flash('该班级暂无学生', 'warning')
        return redirect(url_for('course.course_detail', course_id=course_id))
    
    added_count = 0
    skipped_count = 0
    
    for student in students:
        # 检查是否已存在
        existing = Score.query.filter_by(student_id=student.id, course_id=course_id).first()
        if existing:
            skipped_count += 1
            continue
        
        # 添加成绩记录（初始成绩为0）
        new_score = Score(
            student_id=student.id,
            course_id=course_id,
            score=0,
            semester=course.semester,
            year=course.year
        )
        db.session.add(new_score)
        added_count += 1
    
    db.session.commit()
    
    log_action(current_user.id, 'create', 'scores', f'为班级{class_key}添加课程{course.course_name}，成功{added_count}人，跳过{skipped_count}人')
    
    message = f'成功添加班级 {class_key} 到课程，共 {added_count} 人'
    if skipped_count > 0:
        message += f'，{skipped_count} 人已存在'
    flash(message, 'success')
    return redirect(url_for('course.course_detail', course_id=course_id))

# 添加讨论
@course_bp.route('/courses/<int:course_id>/discussion/add', methods=['POST'])
@login_required
def add_discussion(course_id):
    from app.models import CourseDiscussion
    
    course = Course.query.get_or_404(course_id)
    content = request.form.get('content')
    parent_id = request.form.get('parent_id', type=int)
    
    if not content:
        flash('请输入讨论内容', 'warning')
        return redirect(url_for('course.course_detail', course_id=course_id))
    
    discussion = CourseDiscussion(
        course_id=course_id,
        user_id=current_user.id,
        content=content,
        parent_id=parent_id
    )
    db.session.add(discussion)
    db.session.commit()
    
    log_action(current_user.id, 'create', 'discussions', f'在课程{course.course_name}中发表讨论')
    
    flash('发表成功', 'success')
    return redirect(url_for('course.course_detail', course_id=course_id))

# 删除讨论
@course_bp.route('/courses/discussion/delete/<int:discussion_id>')
@login_required
def delete_discussion(discussion_id):
    from app.models import CourseDiscussion
    
    discussion = CourseDiscussion.query.get_or_404(discussion_id)
    course_id = discussion.course_id
    
    # 权限检查：只有作者或管理员可以删除
    if current_user.role != 'admin' and discussion.user_id != current_user.id:
        flash('没有权限删除该讨论', 'danger')
        return redirect(url_for('course.course_detail', course_id=course_id))
    
    # 删除所有回复
    CourseDiscussion.query.filter_by(parent_id=discussion_id).delete()
    
    db.session.delete(discussion)
    db.session.commit()
    
    flash('删除成功', 'success')
    return redirect(url_for('course.course_detail', course_id=course_id))

# 上传课程资料
@course_bp.route('/courses/<int:course_id>/document/upload', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'teacher')
def upload_document(course_id):
    from app.models import CourseDocument
    import os
    from werkzeug.utils import secure_filename
    
    course = Course.query.get_or_404(course_id)
    
    # 检查权限：教师只能上传自己课程的资料
    if current_user.role == 'teacher' and course.teacher_id != current_user.id:
        flash('没有权限上传该课程的资料', 'danger')
        return redirect(url_for('course.course_detail', course_id=course_id))
    
    if request.method == 'POST':
        title = request.form.get('title')
        file = request.files.get('file')
        
        if not file or not title:
            flash('请填写资料标题并选择文件', 'warning')
            return redirect(url_for('course.upload_document', course_id=course_id))
        
        # 确保上传目录存在
        upload_dir = os.path.join('app', 'static', 'uploads', 'courses', str(course_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # 保存文件
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # 获取文件大小和类型
        file_size = os.path.getsize(file_path)
        file_type = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'unknown'
        
        # 创建资料记录
        doc = CourseDocument(
            course_id=course_id,
            title=title,
            file_path=f'uploads/courses/{course_id}/{filename}',
            file_size=file_size,
            file_type=file_type,
            uploaded_by=current_user.id
        )
        db.session.add(doc)
        db.session.commit()
        
        log_action(current_user.id, 'create', 'course_documents', f'为课程{course.course_name}上传资料：{title}')
        
        flash('资料上传成功', 'success')
        return redirect(url_for('course.course_detail', course_id=course_id))
    
    return render_template('course/upload_document.html', course=course, title='上传课程资料')

# 下载课程资料
@course_bp.route('/courses/document/download/<int:doc_id>')
@login_required
def download_document(doc_id):
    from app.models import CourseDocument
    import os
    
    doc = CourseDocument.query.get_or_404(doc_id)
    file_path = os.path.join('/app/app/static', doc.file_path)
    
    if not os.path.exists(file_path):
        flash('文件不存在', 'danger')
        return redirect(url_for('course.course_detail', course_id=doc.course_id))
    
    return send_file(file_path, as_attachment=True, download_name=doc.title)

# 删除课程资料
@course_bp.route('/courses/document/delete/<int:doc_id>')
@login_required
@roles_required('admin', 'teacher')
def delete_document(doc_id):
    from app.models import CourseDocument
    import os
    
    doc = CourseDocument.query.get_or_404(doc_id)
    course_id = doc.course_id
    course = Course.query.get_or_404(course_id)
    
    # 检查权限
    if current_user.role == 'teacher' and course.teacher_id != current_user.id:
        flash('没有权限删除该课程的资料', 'danger')
        return redirect(url_for('course.course_detail', course_id=course_id))
    
    # 删除文件
    file_path = os.path.join('/app/app/static', doc.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # 删除记录
    db.session.delete(doc)
    db.session.commit()
    
    log_action(current_user.id, 'delete', 'course_documents', f'删除课程{course.course_name}的资料：{doc.title}')
    
    flash('资料删除成功', 'success')
    return redirect(url_for('course.course_detail', course_id=course_id))

# 班级学生列表
@course_bp.route('/courses/<int:course_id>/class/<class_name>')
@login_required
def class_students(course_id, class_name):
    from app.models import Student
    
    course = Course.query.get_or_404(course_id)
    
    # 获取该课程中属于该班级的学生（通过成绩表关联）
    scores = Score.query.filter_by(course_id=course_id).all()
    
    students = []
    student_scores = {}
    for score in scores:
        student = Student.query.get(score.student_id)
        if student and student.class_name == class_name:
            students.append(student)
            student_scores[student.id] = score.score
    
    return render_template('course/class_students.html', course=course, class_name=class_name, students=students, student_scores=student_scores)

# 添加课程
@course_bp.route('/courses/add', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def add_course():
    form = CourseForm()
    if form.validate_on_submit():
        try:
            # 生成不重复的6位随机课程编号
            import random
            while True:
                course_code = str(random.randint(100000, 999999))
                if not Course.query.filter_by(course_code=course_code).first():
                    break
            
            # 创建课程对象
            course = Course(
                course_code=course_code,
                course_name=form.course_name.data,
                credits=form.credits.data,
                teacher_id=form.teacher_id.data,
                semester=form.semester.data,
                year=form.year.data,
                classroom=form.classroom.data,
                hours=form.hours.data
            )
            db.session.add(course)
            
            # 记录日志
            from app.models import Log
            from datetime import datetime
            log = Log(
                user_id=current_user.id,
                action='create',
                resource='courses',
                detail=f'添加课程：{course.course_name}（代码：{course.course_code}）',
                created_at=datetime.utcnow()
            )
            db.session.add(log)
            
            # 一次性提交所有更改
            db.session.commit()
            flash(f'课程添加成功，课程编号：{course_code}', 'success')
            return redirect(url_for('course.courses_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'课程添加失败: {str(e)}', 'danger')
            print(f"课程添加失败: {str(e)}")
    
    return render_template('course/courses_add.html', form=form, title='添加课程')

# 编辑课程
@course_bp.route('/courses/edit/<int:course_id>', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # 权限检查：管理员或课程所属教师
    if current_user.role != 'admin' and current_user.id != course.teacher_id:
        flash('没有访问权限', 'danger')
        return redirect(url_for('course.courses_list'))
    
    form = CourseForm(obj=course)
    
    # 设置表单对象引用，用于验证
    form._obj = course
    
    if form.validate_on_submit():
        form.populate_obj(course)
        
        # 记录日志（不提交事务）
        try:
            from app.models import Log
            from datetime import datetime
            log = Log(
                user_id=current_user.id,
                action='update',
                resource='courses',
                detail=f'编辑课程：{course.course_name}（代码：{course.course_code}）',
                created_at=datetime.utcnow()
            )
            db.session.add(log)
        except Exception as e:
            # 日志记录失败不影响课程编辑
            print(f"日志记录失败: {str(e)}")
        
        # 一次性提交所有更改
        try:
            db.session.commit()
            flash('课程信息更新成功', 'success')
            return redirect(url_for('course.courses_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'课程更新失败: {str(e)}', 'danger')
            print(f"课程更新失败: {str(e)}")
    
    return render_template('course/courses_edit.html', form=form, course=course, title='编辑课程')

# 删除课程
@course_bp.route('/courses/delete/<int:course_id>')
@login_required
@roles_required('admin')
def delete_course(course_id):
    from app.models import Score, CourseDocument
    from sqlalchemy import text
    
    course = Course.query.get_or_404(course_id)
    name = course.course_name
    code = course.course_code
    
    # 先删除关联的课程文档
    CourseDocument.query.filter_by(course_id=course.id).delete()
    
    # 删除关联的成绩记录
    Score.query.filter_by(course_id=course.id).delete()
    
    # 使用原生SQL删除课程讨论（先解除自引用外键，再删除）
    db.session.execute(text('UPDATE course_discussions SET parent_id = NULL WHERE course_id = :course_id'), {'course_id': course.id})
    db.session.execute(text('DELETE FROM course_discussions WHERE course_id = :course_id'), {'course_id': course.id})
    
    # 记录日志（在删除前记录，避免对象被删除后无法访问属性）
    try:
        from app.models import Log
        from datetime import datetime
        log = Log(
            user_id=current_user.id,
            action='delete',
            resource='courses',
            detail=f'删除课程：{name}（代码：{code}）',
            created_at=datetime.utcnow()
        )
        db.session.add(log)
    except Exception as e:
        # 日志记录失败不影响课程删除
        print(f"日志记录失败: {str(e)}")
    
    # 删除课程
    db.session.delete(course)
    
    # 一次性提交所有更改
    try:
        db.session.commit()
        flash('课程删除成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'课程删除失败: {str(e)}', 'danger')
        print(f"课程删除失败: {str(e)}")
    
    return redirect(url_for('course.courses_list'))

# 批量删除课程
@course_bp.route('/courses/batch_delete', methods=['POST'])
@login_required
@roles_required('admin')
def courses_batch_delete():
    ids = request.form.getlist('ids', type=int)
    if not ids:
        flash('请选择要删除的课程', 'warning')
        return redirect(url_for('course.courses_list'))
    
    try:
        courses_to_delete = Course.query.filter(Course.id.in_(ids)).all()
        
        # 记录日志（在删除前记录）
        try:
            from app.models import Log
            from datetime import datetime
            log = Log(
                user_id=current_user.id,
                action='batch_delete',
                resource='courses',
                detail=f'批量删除课程，共{len(ids)}条记录',
                created_at=datetime.utcnow()
            )
            db.session.add(log)
        except Exception as e:
            # 日志记录失败不影响课程删除
            print(f"日志记录失败: {str(e)}")
        
        # 删除所有选中的课程
        for course in courses_to_delete:
            db.session.delete(course)
        
        # 一次性提交所有更改
        db.session.commit()
        flash(f'成功删除{len(ids)}门课程', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'批量删除失败：{str(e)}', 'danger')
    
    return redirect(url_for('course.courses_list'))

# 导出课程模板
@course_bp.route('/courses/export_template')
@login_required
@roles_required('admin')
def export_template():
    # 创建模板数据
    template_data = {
        '课程代码': ['C001', 'C002'],
        '课程名称': ['高等数学', '大学物理'],
        '学分': [4.0, 3.0],
        '授课教师': ['张三', '李四'],
        '学期': ['秋季', '春季'],
        '学年': [2024, 2024],
        '教室': ['教101', '教202'],
        '学时': [64, 48]
    }
    
    df = pd.DataFrame(template_data)
    
    # 生成Excel文件
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='课程模板')
    
    output.seek(0)
    
    # 记录日志
    log_action(current_user.id, 'export_template', 'courses', '导出课程导入模板')
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f'课程导入模板_{datetime.now().strftime("%Y%m%d")}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# 导出课程数据
@course_bp.route('/courses/export')
@login_required
@roles_required('admin')
def export_courses():
    courses = Course.query.all()
    
    # 准备导出数据
    data = {
        '课程代码': [c.course_code for c in courses],
        '课程名称': [c.course_name for c in courses],
        '学分': [c.credits for c in courses],
        '授课教师': [c.teacher.name for c in courses],
        '学期': [c.semester for c in courses],
        '学年': [c.year for c in courses],
        '教室': [c.classroom for c in courses],
        '学时': [c.hours for c in courses],
        '创建时间': [c.created_at.strftime('%Y-%m-%d %H:%M:%S') for c in courses]
    }
    
    df = pd.DataFrame(data)
    
    # 生成Excel文件
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='课程信息')
    
    output.seek(0)
    
    # 记录日志
    log_action(current_user.id, 'export', 'courses', f'导出课程数据，共{len(courses)}条')
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f'课程信息_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# 导入课程数据
@course_bp.route('/courses/import', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def import_courses():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('请选择文件', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('请选择文件', 'danger')
            return redirect(request.url)
        
        try:
            # 读取Excel文件
            df = pd.read_excel(file)
            
            # 验证必要列
            required_columns = ['课程代码', '课程名称', '学分', '授课教师', '学期', '学年', '学时']
            for col in required_columns:
                if col not in df.columns:
                    flash(f'文件缺少必要列：{col}', 'danger')
                    return redirect(request.url)
            
            # 导入数据
            imported_count = 0
            for index, row in df.iterrows():
                # 检查课程代码是否已存在
                if not Course.query.filter_by(course_code=row['课程代码']).first():
                    # 查找教师ID
                    teacher = User.query.filter_by(name=row['授课教师'], role='teacher').first()
                    if not teacher:
                        flash(f'行{index+2}：未找到教师{row["授课教师"]}', 'warning')
                        continue
                    
                    course = Course(
                        course_code=row['课程代码'],
                        course_name=row['课程名称'],
                        credits=row['学分'],
                        teacher_id=teacher.id,
                        semester=row['学期'],
                        year=row['学年'],
                        classroom=row['教室'] if '教室' in df.columns and pd.notna(row['教室']) else None,
                        hours=row['学时']
                    )
                    db.session.add(course)
                    imported_count += 1
            
            db.session.commit()
            
            # 记录日志
            log_action(current_user.id, 'import', 'courses', f'导入课程数据，成功导入{imported_count}条')
            
            flash(f'导入成功，共导入{imported_count}条课程信息', 'success')
        except Exception as e:
            flash(f'导入失败：{str(e)}', 'danger')
        
        return redirect(url_for('course.courses_list'))
    
    return render_template('course/import.html')

# ==================== 项目管理功能 ====================

# 项目列表
@course_bp.route('/projects', methods=['GET', 'POST'])
@login_required
def projects_list():
    # 根据角色确定查询范围
    if current_user.role == 'admin':
        # 管理员可以看到所有项目
        query = Project.query
    elif current_user.role == 'teacher':
        # 教师可以看到自己负责的项目
        query = Project.query.filter_by(teacher_id=current_user.id)
    else:
        # 学生可以看到所有项目（用于查看和参与）
        query = Project.query
    
    # 查询参数
    project_code = request.args.get('project_code')
    name = request.args.get('name')
    course_id = request.args.get('course_id', type=int)
    status = request.args.get('status')
    teacher_id = request.args.get('teacher_id', type=int)
    
    if project_code:
        query = query.filter(Project.project_code.like(f'%{project_code}%'))
    if name:
        query = query.filter(Project.name.like(f'%{name}%'))
    if course_id:
        query = query.filter_by(course_id=course_id)
    if status:
        query = query.filter_by(status=status)
    if teacher_id:
        query = query.filter_by(teacher_id=teacher_id)
    
    # 分页
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(Project.id.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    projects = pagination.items
    
    # 为每个项目添加小组数量和学生数量
    for project in projects:
        from app.models import Team, TeamMember
        team_count = Team.query.filter_by(project_id=project.id).count()
        student_count = db.session.query(TeamMember.student_id).join(Team).filter(Team.project_id==project.id).distinct().count()
        project.team_count = team_count
        project.student_count = student_count
    
    # 课程列表（用于筛选）
    courses = Course.query.all()
    teachers = User.query.filter_by(role='teacher').all()
    
    return render_template('course/projects_list.html', projects=projects, pagination=pagination, 
                         courses=courses, teachers=teachers)

# 添加项目
@course_bp.route('/projects/add', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'teacher')
def add_project():
    try:
        form = ProjectForm()
    except Exception as e:
        print(f"[ERROR] 创建ProjectForm失败: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'加载表单失败：{str(e)}', 'danger')
        return redirect(url_for('course.projects_list'))
    
    if form.validate_on_submit():
        try:
            print(f"[DEBUG ADD PROJECT] 表单验证通过")
            print(f"[DEBUG ADD PROJECT] 表单数据: {form.data}")
            
            # 处理leader_id，如果选择“无”则设为None
            leader_id = form.leader_id.data if form.leader_id.data != 0 else None
            template_id = form.template_id.data if form.template_id.data != 0 else None
            
            project = Project(
                project_code=form.project_code.data,
                name=form.name.data,
                description=form.description.data,
                course_id=form.course_id.data,
                template_id=template_id,
                teacher_id=form.teacher_id.data,
                leader_id=leader_id,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                status=form.status.data,
                tech_stack=form.tech_stack.data,
                evaluation_criteria=form.evaluation_criteria.data,
                deploy_url=form.deploy_url.data,
                max_team_size=form.max_team_size.data,
                requirements=form.requirements.data
            )
            db.session.add(project)
            
            db.session.commit()
            
            # 记录日志
            log_action(current_user.id, 'create', 'projects', f'添加项目：{project.name}（编号：{project.project_code}）')
            
            flash('项目添加成功', 'success')
            return redirect(url_for('course.projects_list'))
        except Exception as e:
            db.session.rollback()
            print(f"[DEBUG ADD PROJECT] 保存失败: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'添加项目失败：{str(e)}', 'danger')
    else:
        if request.method == 'POST':
            print(f"[DEBUG ADD PROJECT] 表单验证失败")
            print(f"[DEBUG ADD PROJECT] 表单错误: {form.errors}")
    
    # 获取模板列表供选择
    from app.models import ProjectTemplate
    templates = ProjectTemplate.query.filter_by(is_active=True).order_by(ProjectTemplate.created_at.desc()).all()
    
    return render_template('course/projects_add.html', form=form, title='添加项目', templates=templates)

# 编辑项目
@course_bp.route('/projects/edit/<int:project_id>', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    # 权限检查：管理员或项目指导教师
    if current_user.role != 'admin' and current_user.id != project.teacher_id:
        flash('没有访问权限', 'danger')
        return redirect(url_for('course.projects_list'))
    
    try:
        form = ProjectForm(obj=project)
    except Exception as e:
        print(f"[ERROR] 创建ProjectForm失败: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'加载表单失败：{str(e)}', 'danger')
        return redirect(url_for('course.projects_list'))
    
    # 设置表单对象引用，用于验证
    form._obj = project
    
    # 处理leader_id和template_id的默认值
    if project.leader_id is None:
        form.leader_id.data = 0
    if project.template_id is None:
        form.template_id.data = 0
    
    if form.validate_on_submit():
        try:
            print(f"[DEBUG EDIT PROJECT] 表单验证通过")
            print(f"[DEBUG EDIT PROJECT] 表单数据: {form.data}")
            
            # 处理leader_id，如果选择“无”则设为None
            leader_id = form.leader_id.data if form.leader_id.data != 0 else None
            template_id = form.template_id.data if form.template_id.data != 0 else None
            
            form.populate_obj(project)
            project.leader_id = leader_id
            project.template_id = template_id
            
            db.session.commit()
            
            # 记录日志
            log_action(current_user.id, 'update', 'projects', f'编辑项目：{project.name}（编号：{project.project_code}）')
            
            flash('项目信息更新成功', 'success')
            return redirect(url_for('course.projects_list'))
        except Exception as e:
            db.session.rollback()
            print(f"[DEBUG EDIT PROJECT] 保存失败: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'更新项目信息失败：{str(e)}', 'danger')
    else:
        if request.method == 'POST':
            print(f"[DEBUG EDIT PROJECT] 表单验证失败")
            print(f"[DEBUG EDIT PROJECT] 表单错误: {form.errors}")
    
    # 获取模板列表供选择
    from app.models import ProjectTemplate
    templates = ProjectTemplate.query.filter_by(is_active=True).order_by(ProjectTemplate.created_at.desc()).all()
    
    return render_template('course/projects_edit.html', form=form, project=project, title='编辑项目', templates=templates)

# 删除项目
@course_bp.route('/projects/delete/<int:project_id>')
@login_required
@roles_required('admin', 'teacher')
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    name = project.name
    code = project.project_code
    
    # 验证权限：只有项目创建者或管理员可以删除
    if current_user.role != 'admin' and project.teacher_id != current_user.id:
        flash('您没有权限删除此项目', 'danger')
        return redirect(url_for('course.projects_list'))
    
    try:
        # 先删除该项目下的所有小组的成员记录
        from app.models import Team, TeamMember
        teams = Team.query.filter_by(project_id=project_id).all()
        for team in teams:
            TeamMember.query.filter_by(team_id=team.id).delete()
        
        # 再删除项目（会级联删除小组、任务等）
        db.session.delete(project)
        db.session.commit()
        
        # 记录日志
        log_action(current_user.id, 'delete', 'projects', f'删除项目：{name}（编号：{code}）')
        
        flash('项目删除成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除项目失败：{str(e)}', 'danger')
    
    return redirect(url_for('course.projects_list'))

# 项目详情
@course_bp.route('/projects/detail/<int:project_id>')
@login_required
def project_detail(project_id):
    """项目详情页"""
    from app.models import Team, Task, Bug, CodeCommit
    
    project = Project.query.get_or_404(project_id)
    
    # 获取该项目的所有小组
    teams = Team.query.filter_by(project_id=project_id).all()
    
    # 统计信息
    total_teams = len(teams)
    total_tasks = 0
    completed_tasks = 0
    in_progress_tasks = 0
    total_bugs = 0
    open_bugs = 0
    total_commits = 0
    
    for team in teams:
        # 任务统计
        tasks = Task.query.filter_by(team_id=team.id).all()
        total_tasks += len(tasks)
        completed_tasks += sum(1 for t in tasks if t.status == 'done')
        in_progress_tasks += sum(1 for t in tasks if t.status == 'in_progress')
        
        # Bug统计
        bugs = Bug.query.filter_by(team_id=team.id).all()
        total_bugs += len(bugs)
        open_bugs += sum(1 for b in bugs if b.status in ['open', 'in_progress'])
        
        # 代码提交统计
        commits = CodeCommit.query.filter_by(team_id=team.id).all()
        total_commits += len(commits)
    
    # 计算进度
    progress = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    stats = {
        'total_teams': total_teams,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'in_progress_tasks': in_progress_tasks,
        'total_bugs': total_bugs,
        'open_bugs': open_bugs,
        'total_commits': total_commits,
        'progress': progress
    }
    
    return render_template('project/project_detail.html', 
                         project=project, 
                         stats=stats, 
                         teams=teams)