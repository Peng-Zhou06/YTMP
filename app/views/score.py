from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Score, Student, Course, User
from app.forms.score import ScoreForm, BatchScoreForm
from app.utils.decorators import roles_required
from app.utils.logs import log_action
import pandas as pd
import io
from sqlalchemy import func, desc, case
from datetime import datetime

# 创建蓝图
score_bp = Blueprint('score', __name__)

# 成绩列表（管理员、教师和学生可访问）
@score_bp.route('/scores', methods=['GET', 'POST'])
@login_required
def scores_list():
    # 教师角色：显示自己教授的课程列表
    if current_user.role == 'teacher':
        courses = Course.query.filter_by(teacher_id=current_user.id).all()
        
        # 统计每门课程的学生数和班级数
        for course in courses:
            course.student_count = Score.query.filter_by(course_id=course.id).count()
            # 获取该课程涉及的所有班级
            scores = Score.query.filter_by(course_id=course.id).all()
            class_names = set()
            for s in scores:
                stu = Student.query.get(s.student_id)
                if stu and stu.class_name:
                    class_names.add(stu.class_name)
            course.class_count = len(class_names)
        
        return render_template('score/scores_courses.html', courses=courses)
    
    # 管理员：显示所有成绩
    query = Score.query
    
    # 查询参数
    student_id = request.args.get('student_id', type=int)
    course_id = request.args.get('course_id', type=int)
    semester = request.args.get('semester')
    year = request.args.get('year', type=int)
    student_name = request.args.get('student_name')
    teacher_id = request.args.get('teacher_id', type=int)
    
    if student_id:
        query = query.filter_by(student_id=student_id)
    if course_id:
        query = query.filter_by(course_id=course_id)
    if semester:
        query = query.filter_by(semester=semester)
    if year:
        query = query.filter_by(year=year)
    
    # 处理学生姓名搜索
    if student_name:
        matching_students = Student.query.filter(Student.name.like(f'%{student_name}%')).all()
        if matching_students:
            student_ids = [student.id for student in matching_students]
            query = query.filter(Score.student_id.in_(student_ids))
    
    # 处理教师筛选
    if teacher_id:
        matching_courses = Course.query.filter_by(teacher_id=teacher_id).all()
        if matching_courses:
            course_ids = [course.id for course in matching_courses]
            query = query.filter(Score.course_id.in_(course_ids))
    
    # 分页
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(Score.id.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    scores = pagination.items
    
    students = Student.query.all()
    courses = Course.query.all()
    teachers = User.query.filter_by(role='teacher').all()
    
    return render_template('score/scores_list.html', scores=scores, pagination=pagination, 
                         students=students, courses=courses, teachers=teachers)

# 教师查看课程的班级列表
@score_bp.route('/scores/course/<int:course_id>')
@login_required
def scores_course_classes(course_id):
    course = Course.query.get_or_404(course_id)
    
    # 权限检查
    if current_user.role == 'teacher' and course.teacher_id != current_user.id:
        flash('没有权限查看该课程', 'danger')
        return redirect(url_for('score.scores_list'))
    
    # 获取该课程的所有成绩
    scores = Score.query.filter_by(course_id=course_id).all()
    
    # 按班级分组
    class_students = {}
    for score in scores:
        student = Student.query.get(score.student_id)
        if student:
            class_name = student.class_name or '未分班'
            if class_name not in class_students:
                class_students[class_name] = []
            class_students[class_name].append({
                'student': student,
                'score': score
            })
    
    return render_template('score/scores_course_classes.html', course=course, class_students=class_students)

# 教师查看班级成绩
@score_bp.route('/scores/course/<int:course_id>/class/<class_name>')
@login_required
def scores_class_detail(course_id, class_name):
    course = Course.query.get_or_404(course_id)
    
    # 权限检查
    if current_user.role == 'teacher' and course.teacher_id != current_user.id:
        flash('没有权限查看该课程', 'danger')
        return redirect(url_for('score.scores_list'))
    
    # 获取该班级在该课程的所有学生成绩
    scores = Score.query.filter_by(course_id=course_id).all()
    
    class_scores = []
    for score in scores:
        student = Student.query.get(score.student_id)
        if student and student.class_name == class_name:
            class_scores.append({
                'student': student,
                'score': score
            })
    
    return render_template('score/scores_class_detail.html', course=course, class_name=class_name, class_scores=class_scores)

# 学生成绩查询
@score_bp.route('/student/scores')
@login_required
def student_scores():
    # 学生只能查看自己的成绩
    # 查找当前用户对应的学生记录
    student = Student.query.filter_by(student_id=current_user.username).first()
    
    if student:
        scores = Score.query.filter_by(student_id=student.id).all()
        
        # 计算总分和平均分
        total_score = sum(score.score * score.course.credits for score in scores) if scores else 0
        total_credits = sum(score.course.credits for score in scores) if scores else 0
        gpa = round(total_score / total_credits, 2) if total_credits > 0 else 0
        
        # 计算统计数据
        total_courses = len(scores)
        passed_courses = sum(1 for score in scores if score.score >= 60)
        pass_rate = round((passed_courses / total_courses * 100) if total_courses > 0 else 0, 2)
        avg_score = round(sum(score.score for score in scores) / total_courses, 2) if total_courses > 0 else 0
        
        # 构建统计数据字典
        stats = {
            'total_courses': total_courses,
            'total_credits': total_credits,
            'avg_score': avg_score,
            'pass_rate': f"{pass_rate}%"
        }
        
        # 加载筛选选项
        course_ids = [score.course_id for score in scores]
        courses = Course.query.filter(Course.id.in_(course_ids)).all()
        
        return render_template('score/student_scores.html', scores=scores, gpa=gpa, student=student, stats=stats, courses=courses)
    else:
        flash('未找到对应的学生信息', 'warning')
        return redirect(url_for('auth.login'))

# 添加成绩
@score_bp.route('/scores/add', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'teacher')
def add_score():
    # 如果从课程页面跳转过来，获取课程ID
    course_id = request.args.get('course_id', type=int)
    
    form = ScoreForm(course_id=course_id)
    if form.validate_on_submit():
        # 检查是否已存在该学生的该课程成绩
        existing_score = Score.query.filter_by(
            student_id=form.student_id.data,
            course_id=form.course_id.data
        ).first()
        
        if existing_score:
            flash('该学生的该课程成绩已存在', 'warning')
            return redirect(url_for('score.add_score', course_id=course_id))
        
        # 获取课程信息
        course = Course.query.get(form.course_id.data)
        
        score = Score(
            student_id=form.student_id.data,
            course_id=form.course_id.data,
            score=form.score.data,
            semester=course.semester,
            year=course.year
        )
        db.session.add(score)
        db.session.commit()
        
        # 记录日志
        student = Student.query.get(form.student_id.data)
        log_action(current_user.id, 'create', 'scores', 
                  f'为学生{student.name}（{student.student_id}）添加课程{course.course_name}的成绩')
        
        flash('成绩添加成功', 'success')
        
        # 如果是从课程页面跳转过来的，返回课程详情页
        if course_id:
            return redirect(url_for('score.course_scores', course_id=course_id))
        return redirect(url_for('score.scores_list'))
    
    return render_template('score/scores_add.html', form=form, title='添加成绩')

# 编辑成绩
@score_bp.route('/scores/edit/<int:score_id>', methods=['GET', 'POST'])
@login_required
def edit_score(score_id):
    score = Score.query.get_or_404(score_id)
    
    # 权限检查：管理员或课程所属教师
    if current_user.role != 'admin':
        course = Course.query.get(score.course_id)
        if current_user.id != course.teacher_id:
            flash('没有访问权限', 'danger')
            return redirect(url_for('score.scores_list'))
    
    form = ScoreForm(obj=score)
    
    # 禁用学生和课程选择（编辑时不允许修改）
    form.student_id.render_kw = {'disabled': True}
    form.course_id.render_kw = {'disabled': True}
    
    if form.validate_on_submit():
        score.score = form.score.data
        db.session.commit()
        
        # 记录日志
        student = Student.query.get(score.student_id)
        course = Course.query.get(score.course_id)
        log_action(current_user.id, 'update', 'scores', 
                  f'修改学生{student.name}（{student.student_id}）课程{course.course_name}的成绩')
        
        flash('成绩更新成功', 'success')
        return redirect(url_for('score.scores_list'))
    
    return render_template('score/scores_edit.html', form=form, title='编辑成绩', score=score)

# 删除成绩
@score_bp.route('/scores/delete/<int:score_id>')
@login_required
def delete_score(score_id):
    score = Score.query.get_or_404(score_id)
    
    # 权限检查：管理员或课程所属教师
    if current_user.role != 'admin':
        course = Course.query.get(score.course_id)
        if current_user.id != course.teacher_id:
            flash('没有访问权限', 'danger')
            return redirect(url_for('score.scores_list'))
    
    # 获取信息用于日志
    student = Student.query.get(score.student_id)
    course = Course.query.get(score.course_id)
    student_name = student.name
    student_id = student.student_id
    course_name = course.course_name
    
    db.session.delete(score)
    db.session.commit()
    
    # 记录日志
    log_action(current_user.id, 'delete', 'scores', 
              f'删除学生{student_name}（{student_id}）课程{course_name}的成绩')
    
    flash('成绩删除成功', 'success')
    return redirect(url_for('score.scores_list'))

# 课程成绩管理
@score_bp.route('/courses/<int:course_id>/scores', methods=['GET', 'POST'])
@login_required
def course_scores(course_id):
    course = Course.query.get_or_404(course_id)
    
    # 权限检查：管理员或课程所属教师
    if current_user.role != 'admin' and current_user.id != course.teacher_id:
        flash('没有访问权限', 'danger')
        return redirect(url_for('score.scores_list'))
    
    # 查询该课程的所有成绩
    scores = Score.query.filter_by(course_id=course_id).all()
    
    # 统计信息
    if scores:
        total_students = len(scores)
        avg_score = round(sum(s.score for s in scores) / total_students, 2)
        max_score = max(s.score for s in scores)
        min_score = min(s.score for s in scores)
        pass_rate = round(sum(1 for s in scores if s.score >= 60) / total_students * 100, 2)
    else:
        total_students = 0
        avg_score = 0
        max_score = 0
        min_score = 0
        pass_rate = 0
    
    return render_template('score/course_scores.html', course=course, scores=scores,
                         total_students=total_students, avg_score=avg_score,
                         max_score=max_score, min_score=min_score, pass_rate=pass_rate)

# 批量录入成绩
@score_bp.route('/scores/batch', methods=['GET'])
@login_required
@roles_required('admin', 'teacher')
def batch_score():
    course_id = request.args.get('course_id', type=int)
    
    if not course_id:
        flash('请选择课程', 'warning')
        return redirect(url_for('score.scores_list'))
    
    course = Course.query.get_or_404(course_id)
    
    # 权限检查
    if current_user.role == 'teacher' and course.teacher_id != current_user.id:
        flash('没有权限查看该课程', 'danger')
        return redirect(url_for('score.scores_list'))
    
    # 获取该课程的所有成绩
    scores = Score.query.filter_by(course_id=course_id).all()
    
    scores_data = []
    for score in scores:
        student = Student.query.get(score.student_id)
        if student:
            scores_data.append({
                'student_id': student.id,
                'student_name': student.name,
                'student_code': student.student_id,
                'class_name': student.class_name,
                'major': student.major,
                'score': score.score if score.score else '',
                'score_id': score.id
            })
    
    return render_template('score/batch.html', scores=scores_data, course=course)

# 保存批量成绩
@score_bp.route('/scores/save_batch', methods=['POST'])
@login_required
def save_batch_scores():
    data = request.get_json()
    course_id = data.get('course_id')
    scores = data.get('scores')
    
    if not course_id or not scores:
        return jsonify({'success': False, 'message': '缺少必要参数'})
    
    try:
        course = Course.query.get(course_id)
        
        for item in scores:
            student_id = item.get('student_id')
            score_value = item.get('score')
            score_id = item.get('score_id')
            
            if not student_id or score_value == '':
                continue
            
            # 转换成绩为浮点数
            try:
                score_value = float(score_value)
                if score_value < 0 or score_value > 100:
                    continue
            except ValueError:
                continue
            
            if score_id:
                # 更新已存在的成绩
                score = Score.query.get(score_id)
                if score:
                    score.score = score_value
                    db.session.add(score)
            else:
                # 添加新成绩
                existing_score = Score.query.filter_by(
                    student_id=student_id,
                    course_id=course_id
                ).first()
                
                if not existing_score:
                    score = Score(
                        student_id=student_id,
                        course_id=course_id,
                        score=score_value,
                        semester=course.semester,
                        year=course.year
                    )
                    db.session.add(score)
        
        db.session.commit()
        
        # 记录日志
        log_action(current_user.id, 'batch_update', 'scores', 
                  f'批量更新课程{course.course_name}的成绩')
        
        return jsonify({'success': True, 'message': '成绩保存成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# 成绩统计分析
@score_bp.route('/scores/statistics')
@login_required
@roles_required('admin', 'teacher')
def score_statistics():
    # 按课程统计
    course_stats = db.session.query(
        Course.course_name,
        Course.course_code,
        func.count(Score.id).label('student_count'),
        func.avg(Score.score).label('avg_score'),
        func.max(Score.score).label('max_score'),
        func.min(Score.score).label('min_score'),
        func.sum(case(
            (Score.score >= 60, 1),
            else_=0
        )).label('pass_count')
    ).join(Score, Course.id == Score.course_id).group_by(Course.id).order_by(desc('student_count')).all()
    
    # 计算及格率
    stats = []
    for cs in course_stats:
        pass_rate = round(cs.pass_count / cs.student_count * 100, 2) if cs.student_count > 0 else 0
        stats.append({
            'course_name': cs.course_name,
            'course_code': cs.course_code,
            'student_count': cs.student_count,
            'avg_score': round(float(cs.avg_score), 2) if cs.avg_score else 0,
            'max_score': float(cs.max_score) if cs.max_score else 0,
            'min_score': float(cs.min_score) if cs.min_score else 0,
            'pass_rate': pass_rate
        })
    
    return render_template('score/statistics.html', stats=stats)

# 导出成绩报表
@score_bp.route('/scores/export')
@login_required
@roles_required('admin', 'teacher')
def export_scores():
    # 获取查询参数
    course_id = request.args.get('course_id', type=int)
    semester = request.args.get('semester')
    year = request.args.get('year', type=int)
    
    # 构建查询
    query = db.session.query(
        Student.student_id,
        Student.name,
        Student.class_name,
        Student.major,
        Course.course_code,
        Course.course_name,
        Course.credits,
        User.name.label('teacher_name'),
        Score.score,
        Score.semester,
        Score.year
    ).join(Score, Student.id == Score.student_id).join(Course, Score.course_id == Course.id).join(User, Course.teacher_id == User.id)
    
    if course_id:
        query = query.filter(Course.id == course_id)
    if semester:
        query = query.filter(Score.semester == semester)
    if year:
        query = query.filter(Score.year == year)
    
    results = query.all()
    
    # 准备导出数据
    data = {
        '学号': [r.student_id for r in results],
        '姓名': [r.name for r in results],
        '班级': [r.class_name for r in results],
        '专业': [r.major for r in results],
        '课程代码': [r.course_code for r in results],
        '课程名称': [r.course_name for r in results],
        '学分': [r.credits for r in results],
        '授课教师': [r.teacher_name for r in results],
        '成绩': [r.score for r in results],
        '学期': [r.semester for r in results],
        '学年': [r.year for r in results]
    }
    
    df = pd.DataFrame(data)
    
    # 生成Excel文件
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='成绩报表')
    
    output.seek(0)
    
    # 记录日志
    log_action(current_user.id, 'export', 'scores', f'导出成绩报表，共{len(results)}条记录')
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f'成绩报表_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )