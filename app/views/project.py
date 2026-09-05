from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db, csrf
from app.models import Project, Team, Task, DailyReport, Bug, CodeCommit, CrawlerData, AIAssistRecord, Deployment, Announcement, Student, Course, TeamMember, CrawlTask, ProjectTemplate, JobPosting, CrawlerConfig
from app.forms.project import ProjectForm, TeamForm, TaskForm, DailyReportForm, BugForm, AIAssistRecordForm, DeploymentForm, CrawlTaskForm, ProjectTemplateForm
from app.service.project_service import ProjectService, TeamService, TaskService, DailyReportService, BugService, AIAssistService, DeploymentService
from app.service.crawler_service import CrawlerService
from app.utils.decorators import role_required, roles_required
from app.utils.logs import log_action
from datetime import datetime, timedelta
from sqlalchemy import func

# 创建蓝图
project_bp = Blueprint('project', __name__)


# ==================== 教师数据驾驶舱 ====================

@project_bp.route('/teacher/dashboard')
@login_required
@role_required('teacher')
def teacher_dashboard():
    """教师数据驾驶舱首页"""
    # 获取教师的所有项目
    teacher_projects = Project.query.filter_by(teacher_id=current_user.id).all()
    project_ids = [p.id for p in teacher_projects]
    
    # 获取这些项目的所有团队
    if project_ids:
        teacher_teams = Team.query.filter(Team.project_id.in_(project_ids)).all()
        team_ids = [t.id for t in teacher_teams]
    else:
        teacher_teams = []
        team_ids = []
    
    # 基础统计
    total_projects = len(teacher_projects)
    total_teams = len(teacher_teams)
    total_students = db.session.query(Student.id).join(TeamMember).filter(
        TeamMember.team_id.in_(team_ids) if team_ids else False
    ).distinct().count() if team_ids else 0
    
    # 任务统计
    if team_ids:
        total_tasks = Task.query.filter(Task.team_id.in_(team_ids)).count()
        todo_tasks = Task.query.filter(Task.team_id.in_(team_ids), Task.status == 'todo').count()
        in_progress_tasks = Task.query.filter(Task.team_id.in_(team_ids), Task.status == 'in_progress').count()
        review_tasks = Task.query.filter(Task.team_id.in_(team_ids), Task.status == 'review').count()
        done_tasks = Task.query.filter(Task.team_id.in_(team_ids), Task.status == 'done').count()
        delayed_tasks = Task.query.filter(Task.team_id.in_(team_ids), Task.status == 'delayed').count()
    else:
        total_tasks = todo_tasks = in_progress_tasks = review_tasks = done_tasks = delayed_tasks = 0
    
    # Bug统计
    if team_ids:
        total_bugs = Bug.query.filter(Bug.team_id.in_(team_ids)).count()
        open_bugs = Bug.query.filter(Bug.team_id.in_(team_ids), Bug.status.in_(['open', 'in_progress'])).count()
        fixed_bugs = Bug.query.filter(Bug.team_id.in_(team_ids), Bug.status == 'fixed').count()
        closed_bugs = Bug.query.filter(Bug.team_id.in_(team_ids), Bug.status == 'closed').count()
    else:
        total_bugs = open_bugs = fixed_bugs = closed_bugs = 0
    
    # 日报统计（本周）
    week_start = datetime.now() - timedelta(days=datetime.now().weekday())
    if team_ids:
        week_reports = DailyReport.query.filter(
            DailyReport.team_id.in_(team_ids),
            DailyReport.report_date >= week_start,
            DailyReport.is_submitted == True
        ).count()
        # 日报提交率 = 已提交日报 / 应提交日报总数
        total_expected_reports = DailyReport.query.filter(
            DailyReport.team_id.in_(team_ids),
            DailyReport.report_date >= week_start
        ).count()
        report_submission_rate = round((week_reports / total_expected_reports * 100), 1) if total_expected_reports > 0 else 0
    else:
        week_reports = 0
        report_submission_rate = 0
    
    # 代码提交统计
    if team_ids:
        total_commits = CodeCommit.query.filter(CodeCommit.team_id.in_(team_ids)).count()
    else:
        total_commits = 0
    
    # AI使用次数统计
    if team_ids:
        total_ai_records = AIAssistRecord.query.filter(
            AIAssistRecord.team_id.in_(team_ids)
        ).count()
    else:
        total_ai_records = 0
    
    # 部署记录统计
    if team_ids:
        total_deployments = Deployment.query.filter(
            Deployment.team_id.in_(team_ids)
        ).count()
        success_deployments = Deployment.query.filter(
            Deployment.team_id.in_(team_ids),
            Deployment.deploy_status == 'success'
        ).count()
        deployment_success_rate = round((success_deployments / total_deployments * 100), 1) if total_deployments > 0 else 0
    else:
        total_deployments = 0
        deployment_success_rate = 0
    
    stats = {
        'total_projects': total_projects,
        'total_teams': total_teams,
        'total_students': total_students,
        'total_tasks': total_tasks,
        'todo_tasks': todo_tasks,
        'in_progress_tasks': in_progress_tasks,
        'review_tasks': review_tasks,
        'done_tasks': done_tasks,
        'delayed_tasks': delayed_tasks,
        'total_bugs': total_bugs,
        'open_bugs': open_bugs,
        'fixed_bugs': fixed_bugs,
        'closed_bugs': closed_bugs,
        'week_reports': week_reports,
        'total_commits': total_commits,
        'report_submission_rate': report_submission_rate,
        'total_ai_records': total_ai_records,
        'total_deployments': total_deployments,
        'deployment_success_rate': deployment_success_rate
    }
    
    # 项目进度数据（用于图表）
    project_names = []
    project_progress_data = []
    for project in teacher_projects[:10]:
        project_names.append(project.name[:8] + '..' if len(project.name) > 8 else project.name)
        teams = Team.query.filter_by(project_id=project.id).all()
        team_ids_for_project = [t.id for t in teams]
        if team_ids_for_project:
            tasks = Task.query.filter(Task.team_id.in_(team_ids_for_project)).all()
            if tasks:
                completed = sum(1 for t in tasks if t.status == 'done')
                progress = round((completed / len(tasks)) * 100, 1)
            else:
                progress = 0
        else:
            progress = 0
        project_progress_data.append({
            'name': project.name,
            'progress': progress
        })
    
    # 任务状态分布数据
    task_status_data = [
        {'value': todo_tasks, 'name': '待开始'},
        {'value': in_progress_tasks, 'name': '进行中'},
        {'value': review_tasks, 'name': '待测试'},
        {'value': done_tasks, 'name': '已完成'},
        {'value': delayed_tasks, 'name': '已延期'}
    ]
    
    # Bug状态分布数据
    bug_status_data = [
        {'value': open_bugs, 'name': '待处理'},
        {'value': fixed_bugs, 'name': '已修复'},
        {'value': closed_bugs, 'name': '已关闭'}
    ]
    
    # 各小组任务完成情况
    team_task_data = []
    for team in teacher_teams[:10]:
        tasks = Task.query.filter_by(team_id=team.id).all()
        if tasks:
            completed = sum(1 for t in tasks if t.status == 'done')
            progress = round((completed / len(tasks)) * 100, 1)
        else:
            progress = 0
        team_task_data.append({
            'name': team.team_name[:8] + '..' if len(team.team_name) > 8 else team.team_name,
            'progress': progress
        })
    
    # 近7天日报提交趋势
    daily_report_trend = []
    for i in range(6, -1, -1):
        date = datetime.now() - timedelta(days=i)
        if team_ids:
            count = DailyReport.query.filter(
                DailyReport.team_id.in_(team_ids),
                func.date(DailyReport.report_date) == date.date(),
                DailyReport.is_submitted == True
            ).count()
        else:
            count = 0
        daily_report_trend.append({
            'date': date.strftime('%m-%d'),
            'count': count
        })
    
    # 近7天任务完成趋势
    task_completion_trend = []
    for i in range(6, -1, -1):
        date = datetime.now() - timedelta(days=i)
        if team_ids:
            count = Task.query.filter(
                Task.team_id.in_(team_ids),
                func.date(Task.completed_at) == date.date(),
                Task.status == 'done'
            ).count()
        else:
            count = 0
        task_completion_trend.append({
            'date': date.strftime('%m-%d'),
            'count': count
        })
    
    # 优先级分布
    if team_ids:
        high_priority = Task.query.filter(Task.team_id.in_(team_ids), Task.priority == 'high').count()
        medium_priority = Task.query.filter(Task.team_id.in_(team_ids), Task.priority == 'medium').count()
        low_priority = Task.query.filter(Task.team_id.in_(team_ids), Task.priority == 'low').count()
    else:
        high_priority = medium_priority = low_priority = 0
    
    priority_data = [
        {'value': high_priority, 'name': '高优先级'},
        {'value': medium_priority, 'name': '中优先级'},
        {'value': low_priority, 'name': '低优先级'}
    ]
    
    # 最近项目
    recent_projects = sorted(teacher_projects, key=lambda x: x.created_at, reverse=True)[:5]
    
    # 最近未提交日报
    if team_ids:
        unsubmitted_reports = DailyReport.query.filter(
            DailyReport.team_id.in_(team_ids),
            DailyReport.is_submitted == False
        ).order_by(DailyReport.report_date.desc()).limit(5).all()
    else:
        unsubmitted_reports = []
    
    return render_template('project/teacher_dashboard.html',
                         stats=stats,
                         project_names=[p['name'] for p in project_progress_data],
                         project_progress=[p['progress'] for p in project_progress_data],
                         task_status_data=task_status_data,
                         bug_status_data=bug_status_data,
                         team_task_data=team_task_data,
                         daily_report_trend=daily_report_trend,
                         task_completion_trend=task_completion_trend,
                         priority_data=priority_data,
                         recent_projects=recent_projects,
                         unsubmitted_reports=unsubmitted_reports)


# ==================== 学生个人统计 ====================

@project_bp.route('/student/stats')
@login_required
@role_required('student')
def student_stats():
    """学生个人统计页面"""
    # 获取学生信息
    student = Student.query.filter_by(student_id=current_user.username).first()
    if not student:
        flash('未找到学生信息', 'danger')
        return redirect(url_for('index'))
    
    # 获取学生参与的团队
    team_memberships = TeamMember.query.filter_by(student_id=student.id).all()
    team_ids = [m.team_id for m in team_memberships]
    teams = Team.query.filter(Team.id.in_(team_ids)).all() if team_ids else []
    
    # 基础统计
    total_teams = len(teams)
    
    # 任务统计
    my_tasks = Task.query.filter_by(assigned_to=student.id).all()
    total_tasks = len(my_tasks)
    todo_tasks = sum(1 for t in my_tasks if t.status == 'todo')
    in_progress_tasks = sum(1 for t in my_tasks if t.status == 'in_progress')
    review_tasks = sum(1 for t in my_tasks if t.status == 'review')
    done_tasks = sum(1 for t in my_tasks if t.status == 'done')
    delayed_tasks = sum(1 for t in my_tasks if t.status == 'delayed')
    
    # 计算任务完成率
    task_completion_rate = round((done_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0
    
    # 日报统计
    my_reports = DailyReport.query.filter_by(student_id=student.id).all()
    total_reports = len(my_reports)
    submitted_reports = sum(1 for r in my_reports if r.is_submitted)
    
    # 本周日报
    week_start = datetime.now() - timedelta(days=datetime.now().weekday())
    week_reports = DailyReport.query.filter(
        DailyReport.student_id == student.id,
        DailyReport.report_date >= week_start,
        DailyReport.is_submitted == True
    ).count()
    
    # Bug处理数统计
    reported_bugs = Bug.query.filter_by(reported_by=student.id).all()
    assigned_bugs = Bug.query.filter_by(assigned_to=student.id).all()
    total_reported_bugs = len(reported_bugs)
    total_assigned_bugs = len(assigned_bugs)
    fixed_assigned_bugs = sum(1 for b in assigned_bugs if b.status in ['fixed', 'closed'])
    total_bugs_handled = fixed_assigned_bugs  # 已处理的Bug数
    
    # 代码提交统计
    my_commits = CodeCommit.query.filter_by(student_id=student.id).all()
    total_commits = len(my_commits)
    total_additions = sum(c.additions or 0 for c in my_commits)
    total_deletions = sum(c.deletions or 0 for c in my_commits)
    
    # AI辅助记录统计
    my_ai_records = AIAssistRecord.query.filter_by(student_id=student.id).all()
    total_ai_records = len(my_ai_records)
    total_time_saved = sum(r.time_saved or 0 for r in my_ai_records)
    
    # 计算项目贡献度（基于完成任务数、代码提交数、Bug处理数等综合计算）
    # 贡献度 = (完成任务数 * 30% + 代码提交数 * 20% + Bug处理数 * 25% + 日报提交数 * 15% + AI使用次数 * 10%)
    # 归一化到0-100分
    task_score = min(done_tasks * 10, 30)  # 最多30分
    commit_score = min(total_commits * 2, 20)  # 最多20分
    bug_score = min(total_bugs_handled * 10, 25)  # 最多25分
    report_score = min(submitted_reports * 2, 15)  # 最多15分
    ai_score = min(total_ai_records * 2, 10)  # 最多10分
    contribution_score = round(task_score + commit_score + bug_score + report_score + ai_score, 1)
    
    stats = {
        'total_teams': total_teams,
        'total_tasks': total_tasks,
        'todo_tasks': todo_tasks,
        'in_progress_tasks': in_progress_tasks,
        'review_tasks': review_tasks,
        'done_tasks': done_tasks,
        'delayed_tasks': delayed_tasks,
        'task_completion_rate': task_completion_rate,
        'total_reports': total_reports,
        'submitted_reports': submitted_reports,
        'week_reports': week_reports,
        'total_reported_bugs': total_reported_bugs,
        'total_assigned_bugs': total_assigned_bugs,
        'total_bugs_handled': total_bugs_handled,
        'fixed_assigned_bugs': fixed_assigned_bugs,
        'total_commits': total_commits,
        'total_additions': total_additions,
        'total_deletions': total_deletions,
        'total_ai_records': total_ai_records,
        'total_time_saved': total_time_saved,
        'contribution_score': contribution_score
    }
    
    # 我的任务状态分布
    task_status_data = [
        {'value': todo_tasks, 'name': '待开始'},
        {'value': in_progress_tasks, 'name': '进行中'},
        {'value': review_tasks, 'name': '待测试'},
        {'value': done_tasks, 'name': '已完成'},
        {'value': delayed_tasks, 'name': '已延期'}
    ]
    
    # 我的任务优先级分布
    high_priority = sum(1 for t in my_tasks if t.priority == 'high')
    medium_priority = sum(1 for t in my_tasks if t.priority == 'medium')
    low_priority = sum(1 for t in my_tasks if t.priority == 'low')
    
    priority_data = [
        {'value': high_priority, 'name': '高优先级'},
        {'value': medium_priority, 'name': '中优先级'},
        {'value': low_priority, 'name': '低优先级'}
    ]
    
    # 近7天任务完成情况
    task_completion_trend = []
    for i in range(6, -1, -1):
        date = datetime.now() - timedelta(days=i)
        count = sum(1 for t in my_tasks 
                   if t.completed_at and t.completed_at.date() == date.date())
        task_completion_trend.append({
            'date': date.strftime('%m-%d'),
            'count': count
        })
    
    # 近7天日报提交情况
    daily_report_trend = []
    for i in range(6, -1, -1):
        date = datetime.now() - timedelta(days=i)
        count = sum(1 for r in my_reports 
                   if r.report_date.date() == date.date() and r.is_submitted)
        daily_report_trend.append({
            'date': date.strftime('%m-%d'),
            'count': count
        })
    
    # Bug状态分布（我报告的）
    open_reported = sum(1 for b in reported_bugs if b.status in ['open', 'in_progress'])
    fixed_reported = sum(1 for b in reported_bugs if b.status == 'fixed')
    closed_reported = sum(1 for b in reported_bugs if b.status == 'closed')
    
    reported_bug_status = [
        {'value': open_reported, 'name': '待处理'},
        {'value': fixed_reported, 'name': '已修复'},
        {'value': closed_reported, 'name': '已关闭'}
    ]
    
    # Bug状态分布（分配给我的）
    open_assigned = sum(1 for b in assigned_bugs if b.status in ['open', 'in_progress'])
    fixed_assigned = sum(1 for b in assigned_bugs if b.status == 'fixed')
    closed_assigned = sum(1 for b in assigned_bugs if b.status == 'closed')
    
    assigned_bug_status = [
        {'value': open_assigned, 'name': '待处理'},
        {'value': fixed_assigned, 'name': '已修复'},
        {'value': closed_assigned, 'name': '已关闭'}
    ]
    
    # 最近任务
    recent_tasks = sorted(my_tasks, key=lambda x: x.created_at, reverse=True)[:10]
    
    # 最近日报
    recent_reports = sorted(my_reports, key=lambda x: x.report_date, reverse=True)[:5]
    
    # 最近Bug（我报告的）
    recent_reported_bugs = sorted(reported_bugs, key=lambda x: x.created_at, reverse=True)[:5]
    
    # 最近Bug（分配给我的）
    recent_assigned_bugs = sorted(assigned_bugs, key=lambda x: x.created_at, reverse=True)[:5]
    
    return render_template('project/student_stats.html',
                         student=student,
                         stats=stats,
                         task_status_data=task_status_data,
                         priority_data=priority_data,
                         task_completion_trend=task_completion_trend,
                         daily_report_trend=daily_report_trend,
                         reported_bug_status=reported_bug_status,
                         assigned_bug_status=assigned_bug_status,
                         recent_tasks=recent_tasks,
                         recent_reports=recent_reports,
                         recent_reported_bugs=recent_reported_bugs,
                         recent_assigned_bugs=recent_assigned_bugs)


# ==================== 项目管理 ====================

@project_bp.route('/projects')
@login_required
def projects_list():
    """项目列表"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status')
    
    # 根据角色过滤
    if current_user.role == 'teacher':
        pagination = ProjectService.get_all_projects(
            status=status, 
            teacher_id=current_user.id,
            page=page, 
            per_page=10
        )
    elif current_user.role == 'student':
        # 学生查看参与的项目
        student = Student.query.filter_by(student_id=current_user.username).first()
        if student:
            teams = Team.query.join(TeamMember).filter(
                TeamMember.student_id == student.id
            ).all()
            project_ids = [t.project_id for t in teams]
            query = Project.query.filter(Project.id.in_(project_ids))
            pagination = query.order_by(Project.created_at.desc()).paginate(
                page=page, per_page=10, error_out=False
            )
        else:
            pagination = None
    else:
        pagination = ProjectService.get_all_projects(status=status, page=page, per_page=10)
    
    return render_template('project/projects_list.html', pagination=pagination)


@project_bp.route('/projects/<int:project_id>')
@login_required
def project_detail(project_id):
    """项目详情"""
    project = ProjectService.get_project_by_id(project_id)
    stats = ProjectService.get_project_statistics(project_id)
    teams = Team.query.filter_by(project_id=project_id).all()
    
    return render_template('project/project_detail.html', 
                         project=project, 
                         stats=stats, 
                         teams=teams)


@project_bp.route('/projects/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'teacher')
def add_project():
    """添加项目"""
    form = ProjectForm()
    
    if form.validate_on_submit():
        try:
            data = {
                'project_code': form.project_code.data,
                'name': form.name.data,
                'description': form.description.data,
                'course_id': form.course_id.data,
                'template_id': form.template_id.data,
                'teacher_id': form.teacher_id.data,
                'start_date': form.start_date.data,
                'end_date': form.end_date.data,
                'max_team_size': form.max_team_size.data,
                'requirements': form.requirements.data,
                'evaluation_criteria': form.evaluation_criteria.data
            }
            
            project = ProjectService.create_project(data)
            log_action(current_user.id, 'create', 'projects', f'创建项目：{project.name}')
            flash('项目创建成功', 'success')
            return redirect(url_for('project.projects_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建项目失败：{str(e)}', 'danger')
    
    # 获取课程列表
    courses = Course.query.all()
    
    return render_template('project/project_add.html', form=form, courses=courses)


@project_bp.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'teacher')
def edit_project(project_id):
    """编辑项目"""
    project = ProjectService.get_project_by_id(project_id)
    form = ProjectForm(obj=project)
    
    if form.validate_on_submit():
        try:
            data = {
                'name': form.name.data,
                'description': form.description.data,
                'start_date': form.start_date.data,
                'end_date': form.end_date.data,
                'max_team_size': form.max_team_size.data,
                'requirements': form.requirements.data,
                'evaluation_criteria': form.evaluation_criteria.data,
                'status': request.form.get('status')
            }
            
            ProjectService.update_project(project_id, data)
            log_action(current_user.id, 'update', 'projects', f'更新项目：{project.name}')
            flash('项目更新成功', 'success')
            return redirect(url_for('project.project_detail', project_id=project_id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新项目失败：{str(e)}', 'danger')
    
    return render_template('project/project_edit.html', form=form, project=project)


# ==================== 小组管理 ====================

@project_bp.route('/teams')
@login_required
def teams_list():
    """小组列表"""
    project_id = request.args.get('project_id', type=int)
    page = request.args.get('page', 1, type=int)
    
    if project_id:
        pagination = TeamService.get_teams_by_project(project_id, page=page, per_page=10)
        project = Project.query.get_or_404(project_id)
    else:
        # 如果没有指定项目，显示所有小组
        query = Team.query
        
        # 根据角色过滤
        if current_user.role == 'teacher':
            # 教师只看自己项目的团队
            projects = Project.query.filter_by(teacher_id=current_user.id).all()
            project_ids = [p.id for p in projects]
            if project_ids:
                query = query.filter(Team.project_id.in_(project_ids))
            else:
                query = query.filter(Team.project_id == -1)  # 无结果
        elif current_user.role == 'student':
            # 学生只看自己参与的团队
            student = Student.query.filter_by(student_id=current_user.username).first()
            if student:
                member_teams = TeamMember.query.filter_by(student_id=student.id).all()
                team_ids = [m.team_id for m in member_teams]
                if team_ids:
                    query = query.filter(Team.id.in_(team_ids))
                else:
                    query = query.filter(Team.id == -1)  # 无结果
        
        pagination = query.order_by(Team.created_at.desc()).paginate(
            page=page, per_page=10, error_out=False
        )
        project = None
    
    # 获取所有项目用于筛选
    projects = Project.query.all()
    
    return render_template('project/teams_list.html', 
                         pagination=pagination, 
                         project=project,
                         projects=projects)


@project_bp.route('/teams/<int:team_id>')
@login_required
def team_detail(team_id):
    """小组详情"""
    team = TeamService.get_team_by_id(team_id)
    stats = TeamService.get_team_statistics(team_id)
    tasks = Task.query.filter_by(team_id=team_id).order_by(Task.created_at.desc()).all()
    
    # 获取所有学生用于添加成员
    students = Student.query.all()
    
    return render_template('project/team_detail.html', 
                         team=team, 
                         stats=stats, 
                         tasks=tasks,
                         students=students)


@project_bp.route('/teams/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'teacher')
def add_team():
    """添加小组"""
    form = TeamForm()
    
    # 设置项目和学生的选项
    projects = Project.query.all()
    students = Student.query.all()
    form.project_id.choices = [(p.id, p.name) for p in projects]
    form.leader_id.choices = [(s.id, f'{s.name} ({s.student_id})') for s in students]
    
    if form.validate_on_submit():
        try:
            data = {
                'team_name': form.team_name.data,
                'project_id': form.project_id.data,
                'leader_id': form.leader_id.data,
                'description': form.description.data,
                'github_repo': form.github_repo.data
            }
            
            team = TeamService.create_team(data)
            log_action(current_user.id, 'create', 'teams', f'创建小组：{team.team_name}')
            flash('小组创建成功', 'success')
            return redirect(url_for('project.team_detail', team_id=team.id))
        except Exception as e:
            db.session.rollback()
            flash(f'创建小组失败：{str(e)}', 'danger')
    
    return render_template('project/team_add.html', form=form, projects=projects, students=students)


@project_bp.route('/teams/<int:team_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'teacher')
def edit_team(team_id):
    """编辑小组"""
    team = TeamService.get_team_by_id(team_id)
    form = TeamForm(obj=team)
    
    # 设置项目和学生的选项
    projects = Project.query.all()
    students = Student.query.all()
    form.project_id.choices = [(p.id, p.name) for p in projects]
    form.leader_id.choices = [(s.id, f'{s.name} ({s.student_id})') for s in students]
    
    if form.validate_on_submit():
        try:
            team.team_name = form.team_name.data
            team.description = form.description.data
            team.github_repo = form.github_repo.data
            
            db.session.commit()
            log_action(current_user.id, 'update', 'teams', f'编辑小组：{team.team_name}')
            flash('小组信息更新成功', 'success')
            return redirect(url_for('project.team_detail', team_id=team.id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新小组失败：{str(e)}', 'danger')
    
    project = Project.query.get_or_404(team.project_id)
    return render_template('project/team_edit.html', form=form, team=team, project=project)


@project_bp.route('/teams/<int:team_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def delete_team(team_id):
    """删除小组"""
    team = TeamService.get_team_by_id(team_id)
    team_name = team.team_name
    project_id = team.project_id
    
    try:
        # 先删除该小组的所有成员记录（避免外键约束错误）
        from app.models import TeamMember, Task, DailyReport, Bug, CodeCommit, CrawlerData, AIAssistRecord, Deployment
        
        # 删除关联的任务
        Task.query.filter_by(team_id=team_id).delete()
        
        # 删除关联的日报
        DailyReport.query.filter_by(team_id=team_id).delete()
        
        # 删除关联的Bug
        Bug.query.filter_by(team_id=team_id).delete()
        
        # 删除关联的代码提交记录
        CodeCommit.query.filter_by(team_id=team_id).delete()
        
        # 删除关联的爬虫数据
        CrawlerData.query.filter_by(team_id=team_id).delete()
        
        # 删除关联的AI辅助记录
        AIAssistRecord.query.filter_by(team_id=team_id).delete()
        
        # 删除关联的部署记录
        Deployment.query.filter_by(team_id=team_id).delete()
        
        # 删除小组成员
        TeamMember.query.filter_by(team_id=team_id).delete()
        
        # 再删除小组
        db.session.delete(team)
        db.session.commit()
        log_action(current_user.id, 'delete', 'teams', f'删除小组：{team_name}')
        flash('小组删除成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除小组失败：{str(e)}', 'danger')
    
    return redirect(url_for('project.teams_list', project_id=project_id))


# ==================== 小组成员管理 ====================

@project_bp.route('/teams/<int:team_id>/members/add', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
@csrf.exempt
def add_team_member(team_id):
    """添加小组成员"""
    team = TeamService.get_team_by_id(team_id)
    student_id = request.form.get('student_id', type=int)
    role = request.form.get('role', 'member')
    
    if not student_id:
        flash('请选择学生', 'danger')
        return redirect(url_for('project.team_detail', team_id=team_id))
    
    try:
        result = TeamService.add_member(team_id, student_id, role)
        if result:
            student = Student.query.get(student_id)
            log_action(current_user.id, 'add_member', 'teams', 
                      f'为小组{team.team_name}添加成员：{student.name}')
            flash('成员添加成功', 'success')
        else:
            flash('该学生已经是小组成员', 'warning')
    except Exception as e:
        flash(f'添加成员失败：{str(e)}', 'danger')
    
    return redirect(url_for('project.team_detail', team_id=team_id))


@project_bp.route('/teams/<int:team_id>/members/<int:student_id>/remove', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
@csrf.exempt
def remove_team_member(team_id, student_id):
    """移除小组成员"""
    team = TeamService.get_team_by_id(team_id)
    
    # 检查是否为组长
    if team.leader_id == student_id:
        flash('不能移除组长', 'danger')
        return redirect(url_for('project.team_detail', team_id=team_id))
    
    try:
        result = TeamService.remove_member(team_id, student_id)
        if result:
            student = Student.query.get(student_id)
            log_action(current_user.id, 'remove_member', 'teams', 
                      f'从小组{team.team_name}移除成员：{student.name}')
            flash('成员移除成功', 'success')
        else:
            flash('该学生不是小组成员', 'warning')
    except Exception as e:
        flash(f'移除成员失败：{str(e)}', 'danger')
    
    return redirect(url_for('project.team_detail', team_id=team_id))


@project_bp.route('/teams/<int:team_id>/members/<int:student_id>/update_role', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
@csrf.exempt
def update_member_role(team_id, student_id):
    """更新成员角色"""
    from app.models import TeamMember
    
    role = request.form.get('role', 'member')
    member = TeamMember.query.filter_by(team_id=team_id, student_id=student_id).first()
    
    if not member:
        flash('该学生不是小组成员', 'danger')
        return redirect(url_for('project.team_detail', team_id=team_id))
    
    try:
        old_role = member.role
        member.role = role
        db.session.commit()
        
        student = Student.query.get(student_id)
        team = Team.query.get(team_id)
        log_action(current_user.id, 'update_role', 'teams', 
                  f'更新{student.name}在小组{team.team_name}的角色：{old_role} -> {role}')
        flash('成员角色更新成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'更新角色失败：{str(e)}', 'danger')
    
    return redirect(url_for('project.team_detail', team_id=team_id))


# ==================== 任务管理 ====================

@project_bp.route('/tasks')
@login_required
def tasks_list():
    """任务列表（看板视图）"""
    team_id = request.args.get('team_id', type=int)
    status = request.args.get('status')
    priority = request.args.get('priority')
    assigned_to = request.args.get('assigned_to', type=int)  # 按负责人筛选
    page = request.args.get('page', 1, type=int)
    
    if team_id:
        # 获取小组信息
        team = Team.query.get_or_404(team_id)
        
        # 构建查询
        query = Task.query.filter_by(team_id=team_id)
        
        # 按状态筛选
        if status:
            query = query.filter_by(status=status)
        
        # 按优先级筛选
        if priority:
            query = query.filter_by(priority=priority)
        
        # 按负责人筛选
        if assigned_to:
            query = query.filter_by(assigned_to=assigned_to)
        
        # 排序：优先级高的在前，然后按创建时间降序
        query = query.order_by(
            db.case(
                (Task.priority == 'high', 1),
                (Task.priority == 'medium', 2),
                (Task.priority == 'low', 3)
            ),
            Task.created_at.desc()
        )
        
        pagination = query.paginate(page=page, per_page=50, error_out=False)
        
        # 按状态分组任务
        tasks_by_status = {
            'todo': [],
            'in_progress': [],
            'review': [],
            'done': [],
            'delayed': [],
            'closed': []
        }
        
        for task in pagination.items:
            if task.status in tasks_by_status:
                tasks_by_status[task.status].append(task)
        
        # 获取该小组的所有学生用于筛选
        team_members = TeamMember.query.filter_by(team_id=team_id).all()
        students_in_team = [m.student for m in team_members]
        projects = None  # 有team时不需要显示项目列表
        
        # 计算任务统计数据
        all_tasks = Task.query.filter_by(team_id=team_id).all()
        task_stats = {
            'todo': len([t for t in all_tasks if t.status == 'todo']),
            'in_progress': len([t for t in all_tasks if t.status == 'in_progress']),
            'review': len([t for t in all_tasks if t.status == 'review']),
            'done': len([t for t in all_tasks if t.status == 'done']),
            'delayed': len([t for t in all_tasks if t.status == 'delayed']),
            'closed': len([t for t in all_tasks if t.status == 'closed'])
        }
        
        # 计算进度分布
        progress_ranges = [0, 0, 0, 0, 0]  # 0-20%, 21-40%, 41-60%, 61-80%, 81-100%
        for task in all_tasks:
            p = task.progress or 0
            if p <= 20:
                progress_ranges[0] += 1
            elif p <= 40:
                progress_ranges[1] += 1
            elif p <= 60:
                progress_ranges[2] += 1
            elif p <= 80:
                progress_ranges[3] += 1
            else:
                progress_ranges[4] += 1
        progress_distribution = progress_ranges
    else:
        pagination = None
        team = None
        tasks_by_status = {}
        students_in_team = []
        task_stats = None
        progress_distribution = None
        # 获取所有项目用于显示可选的小组列表
        if current_user.role == 'teacher':
            # 教师只看自己项目的团队
            projects = Project.query.filter_by(teacher_id=current_user.id).all()
        elif current_user.role == 'student':
            # 学生只看自己参与的项目
            student = Student.query.filter_by(student_id=current_user.username).first()
            if student:
                teams = Team.query.join(TeamMember).filter(
                    TeamMember.student_id == student.id
                ).all()
                project_ids = list(set([t.project_id for t in teams]))
                projects = Project.query.filter(Project.id.in_(project_ids)).all() if project_ids else []
            else:
                projects = []
        else:
            # 管理员看所有项目
            projects = Project.query.all()
    
    return render_template('project/tasks_list.html', 
                         pagination=pagination, 
                         team=team,
                         tasks_by_status=tasks_by_status,
                         students_in_team=students_in_team,
                         projects=projects,
                         task_stats=task_stats,
                         progress_distribution=progress_distribution,
                         now=datetime.now)


# 教师任务总览
@project_bp.route('/tasks/overview')
@login_required
@roles_required('admin', 'teacher')
def tasks_overview():
    """教师任务总览"""
    # 获取教师负责的所有项目
    if current_user.role == 'teacher':
        projects = Project.query.filter_by(teacher_id=current_user.id).all()
        project_ids = [p.id for p in projects]
        teams = Team.query.filter(Team.project_id.in_(project_ids)).all()
        team_ids = [t.id for t in teams]
        all_tasks = Task.query.filter(Task.team_id.in_(team_ids)).all() if team_ids else []
    else:
        # 管理员看所有
        all_tasks = Task.query.all()
        teams = Team.query.all()
        projects = Project.query.all()
    
    # 按状态统计
    status_counts = {
        'todo': len([t for t in all_tasks if t.status == 'todo']),
        'in_progress': len([t for t in all_tasks if t.status == 'in_progress']),
        'review': len([t for t in all_tasks if t.status == 'review']),
        'done': len([t for t in all_tasks if t.status == 'done']),
        'delayed': len([t for t in all_tasks if t.status == 'delayed']),
        'closed': len([t for t in all_tasks if t.status == 'closed'])
    }
    
    # 按优先级统计
    priority_counts = {
        'high': len([t for t in all_tasks if t.priority == 'high']),
        'medium': len([t for t in all_tasks if t.priority == 'medium']),
        'low': len([t for t in all_tasks if t.priority == 'low'])
    }
    
    # 完成率
    total = len(all_tasks)
    completed = status_counts['done'] + status_counts['closed']
    completion_rate = (completed / total * 100) if total > 0 else 0
    
    # 按小组统计任务数
    team_task_stats = []
    for team in teams:
        team_tasks = [t for t in all_tasks if t.team_id == team.id]
        team_completed = len([t for t in team_tasks if t.status in ['done', 'closed']])
        team_total = len(team_tasks)
        team_rate = (team_completed / team_total * 100) if team_total > 0 else 0
        team_task_stats.append({
            'team': team,
            'total': team_total,
            'completed': team_completed,
            'rate': team_rate
        })
    
    return render_template('project/tasks_overview.html',
                         status_counts=status_counts,
                         priority_counts=priority_counts,
                         completion_rate=completion_rate,
                         total_tasks=total,
                         team_task_stats=team_task_stats,
                         projects=projects)


@project_bp.route('/tasks/<int:task_id>')
@login_required
def task_detail(task_id):
    """任务详情"""
    from datetime import datetime
    task = TaskService.get_task_by_id(task_id)
    work_logs = task.work_logs
    
    return render_template('project/task_detail.html', task=task, work_logs=work_logs, now=datetime.now)


@project_bp.route('/tasks/add', methods=['GET', 'POST'])
@login_required
def add_task():
    """添加任务"""
    form = TaskForm()
    
    # 获取所有团队和学生用于表单选项
    teams = Team.query.all()
    students = Student.query.all()
    
    # 设置团队选项
    form.team_id.choices = [(t.id, t.team_name) for t in teams]
    
    if form.validate_on_submit():
        try:
            data = {
                'task_code': form.task_code.data,
                'title': form.title.data,
                'description': form.description.data,
                'team_id': form.team_id.data,
                'assigned_to': form.assigned_to.data if form.assigned_to.data else None,
                'priority': form.priority.data,
                'status': form.status.data,
                'progress': form.progress.data or 0,
                'estimated_hours': form.estimated_hours.data,
                'actual_hours': form.actual_hours.data,
                'start_date': form.start_date.data,
                'due_date': form.due_date.data,
                'completion_note': form.completion_note.data,
                'screenshots': form.screenshots.data,
                'related_bug_ids': form.related_bug_ids.data,
                'tags': form.tags.data
            }
            
            task = TaskService.create_task(data)
            log_action(current_user.id, 'create', 'tasks', f'创建任务：{task.title}')
            flash('任务创建成功', 'success')
            return redirect(url_for('project.task_detail', task_id=task.id))
        except Exception as e:
            db.session.rollback()
            flash(f'创建任务失败：{str(e)}', 'danger')
    
    return render_template('project/task_add.html', form=form, teams=teams, students=students)


@project_bp.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    """编辑任务"""
    task = TaskService.get_task_by_id(task_id)
    
    # 获取所有团队和学生用于表单选项
    teams = Team.query.all()
    students = Student.query.all()
    
    form = None
    
    # 如果是GET请求，需要转换日期格式为HTML5 datetime-local格式
    if request.method == 'GET':
        form = TaskForm(obj=task)
        # 将datetime对象转换为HTML5 datetime-local格式字符串
        # 注意：这里不直接修改form.data，而是在模板中处理
        start_date_str = task.start_date.strftime('%Y-%m-%dT%H:%M') if task.start_date else None
        due_date_str = task.due_date.strftime('%Y-%m-%dT%H:%M') if task.due_date else None
    else:
        form = TaskForm()
        start_date_str = None
        due_date_str = None
        # POST请求时也需要转换日期格式（如果用户修改了日期）
        if form.start_date.data and isinstance(form.start_date.data, str):
            try:
                form.start_date.data = datetime.strptime(form.start_date.data, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        if form.due_date.data and isinstance(form.due_date.data, str):
            try:
                form.due_date.data = datetime.strptime(form.due_date.data, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
    
    if form.validate_on_submit():
        try:
            data = {
                'task_code': form.task_code.data,
                'title': form.title.data,
                'description': form.description.data,
                'team_id': form.team_id.data,
                'assigned_to': form.assigned_to.data,
                'priority': form.priority.data,
                'status': form.status.data,
                'progress': form.progress.data,
                'estimated_hours': form.estimated_hours.data,
                'actual_hours': form.actual_hours.data,
                'start_date': form.start_date.data,
                'due_date': form.due_date.data,
                'completion_note': form.completion_note.data,
                'screenshots': form.screenshots.data,
                'related_bug_ids': form.related_bug_ids.data,
                'tags': form.tags.data
            }
            
            TaskService.update_task(task_id, data)
            log_action(current_user.id, 'update', 'tasks', f'更新任务：{task.title}')
            flash('任务更新成功', 'success')
            return redirect(url_for('project.task_detail', task_id=task_id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新任务失败：{str(e)}', 'danger')
    
    return render_template('project/task_edit.html', 
                         form=form, 
                         task=task, 
                         teams=teams, 
                         students=students,
                         start_date_str=start_date_str,
                         due_date_str=due_date_str)


@project_bp.route('/tasks/<int:task_id>/update_status', methods=['POST'])
@login_required
def update_task_status(task_id):
    """更新任务状态"""
    status = request.form.get('status')
    progress = request.form.get('progress', type=int)
    
    try:
        task = TaskService.update_task_status(task_id, status, progress)
        log_action(current_user.id, 'update', 'tasks', f'更新任务状态：{task.title} -> {status}')
        flash('任务状态更新成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'更新失败：{str(e)}', 'danger')
    
    return redirect(url_for('project.task_detail', task_id=task_id))


@project_bp.route('/tasks/<int:task_id>/update_status_ajax', methods=['POST'])
@login_required
def update_task_status_ajax(task_id):
    """AJAX更新任务状态（用于看板拖拽）"""
    data = request.get_json()
    status = data.get('status')
    progress = data.get('progress')
    
    if not status:
        return jsonify({'success': False, 'message': '缺少状态参数'}), 400
    
    try:
        # 根据状态自动设置进度
        if status == 'todo':
            auto_progress = 0
        elif status == 'in_progress':
            auto_progress = 50
        elif status == 'review':
            auto_progress = 80
        elif status == 'done':
            auto_progress = 100
        else:
            auto_progress = progress or 0
        
        task = TaskService.update_task_status(task_id, status, auto_progress)
        log_action(current_user.id, 'update', 'tasks', f'更新任务状态：{task.title} -> {status}')
        
        return jsonify({
            'success': True,
            'message': '任务状态更新成功',
            'task': {
                'id': task.id,
                'status': task.status,
                'progress': task.progress
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'}), 500


@project_bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def delete_task(task_id):
    """删除任务"""
    from app.models import Task
    
    task = Task.query.get_or_404(task_id)
    task_title = task.title
    team_id = task.team_id
    
    try:
        # 检查是否有外键关联的记录需要先删除
        # 删除工作日志
        for work_log in task.work_logs:
            db.session.delete(work_log)
        
        # 删除日报关联（如果有）
        # 删除Bug关联（如果有）
        
        # 最后删除任务本身
        db.session.delete(task)
        db.session.commit()
        
        log_action(current_user.id, 'delete', 'tasks', f'删除任务：{task_title}')
        flash('任务删除成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除任务失败：{str(e)}', 'danger')
    
    return redirect(url_for('project.tasks_list', team_id=team_id))


# ==================== 日报管理 ====================

@project_bp.route('/daily_reports')
@login_required
def daily_reports_list():
    """日报列表"""
    from datetime import date
    team_id = request.args.get('team_id', type=int)
    student_id = request.args.get('student_id', type=int)
    report_date = request.args.get('report_date')
    page = request.args.get('page', 1, type=int)
    
    # 根据角色过滤
    if current_user.role == 'student':
        # 学生只能查看自己的日报
        student = Student.query.filter_by(student_id=current_user.username).first()
        if student:
            query = DailyReport.query.filter_by(student_id=student.id)
        else:
            query = DailyReport.query.filter_by(id=-1)  # 返回空结果
    else:
        # 教师/管理员可以查看所有日报
        query = DailyReport.query
        if student_id:
            query = query.filter_by(student_id=student_id)
    
    # 小组筛选（教师可用）
    if team_id and current_user.role in ['admin', 'teacher']:
        query = query.filter_by(team_id=team_id)
    
    # 日期筛选
    if report_date:
        query = query.filter(DailyReport.report_date == report_date)
    
    pagination = query.order_by(DailyReport.report_date.desc(), DailyReport.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # 获取可选的小组列表（教师可用）
    teams = []
    if current_user.role in ['admin', 'teacher']:
        teams = Team.query.all()
    
    # 获取可选的学生列表（教师可用）
    students = []
    if current_user.role in ['admin', 'teacher']:
        students = Student.query.all()
    
    # 日报提交率统计（今日）
    today = date.today()
    if current_user.role in ['admin', 'teacher']:
        total_students_with_team = db.session.query(Student.id).join(TeamMember).distinct().count()
        today_reports = DailyReport.query.filter(
            db.func.date(DailyReport.report_date) == today,
            DailyReport.is_submitted == True
        ).count()
        daily_report_rate = (today_reports / total_students_with_team) * 100 if total_students_with_team > 0 else 0
        submitted_count = today_reports
        unsubmitted_count = total_students_with_team - today_reports
        
        # 近7天提交趋势
        from datetime import timedelta
        weekly_dates = []
        weekly_counts = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            weekly_dates.append(day.strftime('%m-%d'))
            count = DailyReport.query.filter(
                db.func.date(DailyReport.report_date) == day,
                DailyReport.is_submitted == True
            ).count()
            weekly_counts.append(count)
    else:
        daily_report_rate = None
        submitted_count = 0
        unsubmitted_count = 0
        weekly_dates = []
        weekly_counts = []
    
    return render_template('project/daily_reports_list.html', 
                         pagination=pagination, 
                         teams=teams, 
                         students=students,
                         daily_report_rate=daily_report_rate,
                         submitted_count=submitted_count,
                         unsubmitted_count=unsubmitted_count,
                         weekly_dates=weekly_dates,
                         weekly_counts=weekly_counts)


@project_bp.route('/daily_reports/add', methods=['GET', 'POST'])
@login_required
def add_daily_report():
    """添加日报"""
    from datetime import date
    form = DailyReportForm()
    today = date.today()
    
    # 获取当前用户对应的学生信息
    student = Student.query.filter_by(student_id=current_user.username).first()
    
    if current_user.role == 'student':
        if not student:
            flash('未找到您的学生信息，请联系管理员', 'danger')
            return redirect(url_for('project.daily_reports_list'))
        
        # 检查今天是否已提交日报
        existing_report = DailyReport.query.filter(
            DailyReport.student_id == student.id,
            db.func.date(DailyReport.report_date) == today
        ).first()
        
        if existing_report:
            # 如果已存在，跳转到编辑页面
            return redirect(url_for('project.edit_daily_report', report_id=existing_report.id))
    
    if form.validate_on_submit():
        try:
            data = {
                'report_date': form.report_date.data or today,
                'team_id': form.team_id.data,
                'student_id': form.student_id.data if current_user.role in ['admin', 'teacher'] else student.id,
                'today_work': form.today_work.data,
                'tomorrow_plan': form.tomorrow_plan.data,
                'issues': form.issues.data,
                'solutions': form.solutions.data,
                'mood': form.mood.data,
                'working_hours': form.working_hours.data,
                'is_submitted': form.is_submitted.data
            }
            
            report = DailyReportService.create_report(data)
            flash('日报提交成功', 'success')
            return redirect(url_for('project.daily_reports_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'提交失败：{str(e)}', 'danger')
    
    # 获取学生所在的小组（学生只能选择自己所在的小组）
    teams = []
    if student:
        teams = Team.query.join(TeamMember).filter(TeamMember.student_id == student.id).all()
    
    # 教师和管理员可以选择所有小组和学生
    if current_user.role in ['admin', 'teacher']:
        teams = Team.query.all()
        students = Student.query.all()
    else:
        # 学生只能选择自己
        students = [student] if student else []
    
    return render_template('project/daily_report_add.html', form=form, teams=teams, students=students, today=today)


@project_bp.route('/daily_reports/<int:report_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_daily_report(report_id):
    """编辑日报"""
    from datetime import date
    report = DailyReport.query.get_or_404(report_id)
    today = date.today()
    
    # 获取当前用户对应的学生信息
    student = Student.query.filter_by(student_id=current_user.username).first()
    
    # 权限检查：学生只能编辑自己当天的日报
    if current_user.role == 'student':
        if not student or report.student_id != student.id:
            flash('您只能编辑自己的日报', 'danger')
            return redirect(url_for('project.daily_reports_list'))
        
        # 只能修改当天的日报
        if report.report_date.date() != today:
            flash('只能修改当天的日报', 'danger')
            return redirect(url_for('project.daily_reports_list'))
    
    form = DailyReportForm(obj=report)
    
    if form.validate_on_submit():
        try:
            report.report_date = form.report_date.data or report.report_date
            report.team_id = form.team_id.data
            report.today_work = form.today_work.data
            report.tomorrow_plan = form.tomorrow_plan.data
            report.issues = form.issues.data
            report.solutions = form.solutions.data
            report.mood = form.mood.data
            report.working_hours = form.working_hours.data
            report.is_submitted = form.is_submitted.data
            report.updated_at = datetime.now()
            
            db.session.commit()
            flash('日报更新成功', 'success')
            return redirect(url_for('project.daily_reports_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'danger')
    
    # 获取学生所在的小组（学生只能选择自己所在的小组）
    teams = []
    if student:
        teams = Team.query.join(TeamMember).filter(TeamMember.student_id == student.id).all()
    
    # 教师可以选择所有小组和学生
    if current_user.role in ['admin', 'teacher']:
        teams = Team.query.all()
        students = Student.query.all()
    else:
        students = []
    
    return render_template('project/daily_report_edit.html', form=form, report=report, teams=teams, students=students)


@project_bp.route('/daily_reports/<int:report_id>/review', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def review_daily_report(report_id):
    """审核日报"""
    review_text = request.form.get('review_text')
    
    try:
        DailyReportService.review_report(report_id, current_user.id, review_text)
        flash('日报审核完成', 'success')
    except Exception as e:
        flash(f'审核失败：{str(e)}', 'danger')
    
    return redirect(url_for('project.daily_reports_list'))


@project_bp.route('/daily_reports/unsubmitted')
@login_required
@role_required('admin', 'teacher')
def unsubmitted_reports():
    """未提交日报提醒列表"""
    from datetime import date
    today = date.today()
    
    # 获取所有有小组的学生
    students_with_team = db.session.query(Student).join(TeamMember).distinct().all()
    
    # 获取今天已提交日报的学生ID
    submitted_student_ids = [r.student_id for r in DailyReport.query.filter(
        db.func.date(DailyReport.report_date) == today,
        DailyReport.is_submitted == True
    ).all()]
    
    # 未提交日报的学生
    unsubmitted_students = [s for s in students_with_team if s.id not in submitted_student_ids]
    
    # 按小组分组
    unsubmitted_by_team = {}
    for student in unsubmitted_students:
        team_memberships = TeamMember.query.filter_by(student_id=student.id).all()
        for tm in team_memberships:
            team = tm.team
            if team.id not in unsubmitted_by_team:
                unsubmitted_by_team[team.id] = {'team': team, 'students': []}
            unsubmitted_by_team[team.id]['students'].append(student)
    
    return render_template('project/daily_reports_unsubmitted.html', 
                         unsubmitted_by_team=unsubmitted_by_team,
                         today=today)


# ==================== Bug管理 ====================

@project_bp.route('/bugs')
@login_required
def bugs_list():
    """Bug列表"""
    team_id = request.args.get('team_id', type=int)
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    
    query = Bug.query
    if team_id:
        query = query.filter_by(team_id=team_id)
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(Bug.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('project/bugs_list.html', pagination=pagination)


@project_bp.route('/bugs/add', methods=['GET', 'POST'])
@login_required
def add_bug():
    """添加Bug"""
    form = BugForm()
    
    if form.validate_on_submit():
        try:
            data = {
                'bug_code': form.bug_code.data,
                'title': form.title.data,
                'description': form.description.data,
                'team_id': form.team_id.data,
                'reported_by': form.reported_by.data,
                'assigned_to': form.assigned_to.data,
                'severity': form.severity.data,
                'priority': form.priority.data,
                'reproduction_steps': form.reproduction_steps.data,
                'expected_result': form.expected_result.data,
                'actual_result': form.actual_result.data,
                'environment': form.environment.data
            }
            
            bug = BugService.create_bug(data)
            flash('Bug报告成功', 'success')
            return redirect(url_for('project.bugs_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'提交失败：{str(e)}', 'danger')
    
    teams = Team.query.all()
    students = Student.query.all()
    
    return render_template('project/bug_add.html', form=form, teams=teams, students=students)


@project_bp.route('/bugs/<int:bug_id>/update_status', methods=['POST'])
@login_required
def update_bug_status(bug_id):
    """更新Bug状态"""
    status = request.form.get('status')
    assigned_to = request.form.get('assigned_to', type=int)
    
    try:
        BugService.update_bug_status(bug_id, status, assigned_to)
        flash('Bug状态更新成功', 'success')
    except Exception as e:
        flash(f'更新失败：{str(e)}', 'danger')
    
    return redirect(url_for('project.bugs_list'))


# ==================== AI辅助记录 ====================

@project_bp.route('/ai_records')
@login_required
def ai_records_list():
    """AI辅助记录列表"""
    team_id = request.args.get('team_id', type=int)
    student_id = request.args.get('student_id', type=int)
    page = request.args.get('page', 1, type=int)
    
    query = AIAssistRecord.query
    if team_id:
        query = query.filter_by(team_id=team_id)
    if student_id:
        query = query.filter_by(student_id=student_id)
    
    pagination = query.order_by(AIAssistRecord.recorded_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # 统计数据
    stats = AIAssistService.get_statistics(team_id=team_id, student_id=student_id)
    
    return render_template('project/ai_records_list.html', pagination=pagination, stats=stats)


@project_bp.route('/ai_records/add', methods=['GET', 'POST'])
@login_required
def add_ai_record():
    """添加AI辅助记录"""
    form = AIAssistRecordForm()
    
    # 获取当前用户对应的学生信息
    student = Student.query.filter_by(student_id=current_user.username).first()
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            team_id = request.form.get('team_id', type=int)
            student_id = request.form.get('student_id', type=int)
            ai_tool = request.form.get('ai_tool')
            usage_scene = request.form.get('usage_scene')
            prompt = request.form.get('prompt')
            response_summary = request.form.get('response_summary')
            code_snippet = request.form.get('code_snippet')
            applied = request.form.get('applied') == 'true'
            modified = request.form.get('modified') == 'true'
            effectiveness = request.form.get('effectiveness')
            related_files = request.form.get('related_files')
            risk_note = request.form.get('risk_note')
            time_saved = request.form.get('time_saved', type=float)
            notes = request.form.get('notes')
            
            # 学生角色自动设置student_id
            if current_user.role == 'student':
                if not student:
                    flash('未找到您的学生信息，请联系管理员', 'danger')
                    return redirect(url_for('project.ai_records_list'))
                student_id = student.id
                
                # 学生自动选择所在小组
                if not team_id:
                    team_member = TeamMember.query.filter_by(student_id=student.id).first()
                    if team_member:
                        team_id = team_member.team_id
                    else:
                        flash('您还未加入任何小组，请先加入小组后再添加AI记录', 'warning')
                        return redirect(url_for('project.ai_records_list'))
            
            # 验证必填字段
            if not team_id:
                flash('请选择小组', 'danger')
                return render_template('project/ai_record_add.html', form=form, teams=teams, students=students)
            
            if not student_id:
                flash('请选择学生', 'danger')
                return render_template('project/ai_record_add.html', form=form, teams=teams, students=students)
            
            if not ai_tool:
                flash('请选择AI工具', 'danger')
                return render_template('project/ai_record_add.html', form=form, teams=teams, students=students)
            
            if not usage_scene:
                flash('请选择使用场景', 'danger')
                return render_template('project/ai_record_add.html', form=form, teams=teams, students=students)
            
            if not prompt:
                flash('请输入提示词', 'danger')
                return render_template('project/ai_record_add.html', form=form, teams=teams, students=students)
            
            if not response_summary:
                flash('请输入AI返回结果摘要', 'danger')
                return render_template('project/ai_record_add.html', form=form, teams=teams, students=students)
            
            if not effectiveness:
                flash('请选择最终解决效果', 'danger')
                return render_template('project/ai_record_add.html', form=form, teams=teams, students=students)
            
            # 创建记录
            data = {
                'team_id': team_id,
                'student_id': student_id,
                'ai_tool': ai_tool,
                'usage_type': 'code_generation',
                'usage_scene': usage_scene,
                'prompt': prompt,
                'response_summary': response_summary,
                'code_snippet': code_snippet,
                'applied': applied,
                'modified': modified,
                'effectiveness': effectiveness,
                'related_files': related_files,
                'risk_note': risk_note,
                'time_saved': time_saved,
                'notes': notes
            }
            
            record = AIAssistService.create_record(data)
            flash('AI辅助记录添加成功', 'success')
            return redirect(url_for('project.ai_records_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'添加失败：{str(e)}', 'danger')
    
    # 根据角色获取可选的小组和学生
    if current_user.role == 'student':
        if student:
            # 学生只能看到自己所在的小组
            team_members = TeamMember.query.filter_by(student_id=student.id).all()
            teams = [tm.team for tm in team_members]
            students = [student]
        else:
            teams = []
            students = []
    else:
        # 教师和管理员可以看到所有小组和学生
        teams = Team.query.all()
        students = Student.query.all()
    
    return render_template('project/ai_record_add.html', form=form, teams=teams, students=students)


# ==================== 部署管理 ====================

@project_bp.route('/deployments')
@login_required
def deployments_list():
    """部署列表"""
    team_id = request.args.get('team_id', type=int)
    page = request.args.get('page', 1, type=int)
    
    query = Deployment.query
    if team_id:
        query = query.filter_by(team_id=team_id)
    
    pagination = query.order_by(Deployment.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    teams = Team.query.all()
    
    return render_template('project/deployments_list.html', pagination=pagination, teams=teams)


@project_bp.route('/deployments/add', methods=['GET', 'POST'])
@login_required
def add_deployment():
    """添加部署记录"""
    form = DeploymentForm()
    
    if form.validate_on_submit():
        try:
            data = {
                'team_id': form.team_id.data,
                'environment': form.environment.data,
                'version': form.version.data,
                'deploy_url': form.deploy_url.data,
                'commit_hash': form.commit_hash.data,
                'deployed_by': form.deployed_by.data,
                'notes': form.notes.data
            }
            
            deployment = DeploymentService.create_deployment(data)
            flash('部署记录添加成功', 'success')
            return redirect(url_for('project.deployments_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'添加失败：{str(e)}', 'danger')
    
    teams = Team.query.all()
    students = Student.query.all()
    
    return render_template('project/deployment_add.html', form=form, teams=teams, students=students)


# ==================== 爬虫管理 ====================

@project_bp.route('/crawler')
@login_required
def crawler_data_list():
    """爬虫数据列表"""
    team_id = request.args.get('team_id', type=int)
    page = request.args.get('page', 1, type=int)
    
    query = CrawlerData.query
    if team_id:
        query = query.filter_by(team_id=team_id)
    
    pagination = query.order_by(CrawlerData.crawled_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # 统计信息
    if team_id:
        stats = CrawlerService.get_crawler_statistics(team_id)
    else:
        stats = None
    
    # 获取所有小组供选择
    teams = Team.query.all()
    
    return render_template('project/crawler_list.html', pagination=pagination, stats=stats, teams=teams)


@project_bp.route('/crawler/simple', methods=['POST'])
@login_required
def simple_crawl():
    """简单爬取"""
    url = request.form.get('url')
    team_id = request.form.get('team_id', type=int)
    
    if not url or not team_id:
        flash('请提供URL和小组ID', 'danger')
        return redirect(url_for('project.crawler_data_list'))
    
    result, error = CrawlerService.simple_crawl(url, team_id)
    
    if error:
        flash(f'爬取失败：{error}', 'danger')
    else:
        flash('爬取成功', 'success')
    
    return redirect(url_for('project.crawler_data_list'))


@project_bp.route('/crawler/tasks')
@login_required
def crawl_tasks_list():
    """爬虫任务列表"""
    team_id = request.args.get('team_id', type=int)
    
    query = CrawlTask.query
    if team_id:
        query = query.filter_by(team_id=team_id)
    
    tasks = query.order_by(CrawlTask.created_at.desc()).all()
    
    return render_template('project/crawl_tasks_list.html', tasks=tasks)


@project_bp.route('/crawler/tasks/add', methods=['GET', 'POST'])
@login_required
def add_crawl_task():
    """添加爬虫任务"""
    form = CrawlTaskForm()
    
    if form.validate_on_submit():
        try:
            data = {
                'name': form.name.data,
                'target_url': form.target_url.data,
                'team_id': form.team_id.data,
                'crawl_frequency': form.crawl_frequency.data,
                'schedule_time': form.schedule_time.data,
                'config': form.config.data,
                'created_by': form.created_by.data
            }
            
            task = CrawlerService.create_crawl_task(data)
            flash('爬虫任务创建成功', 'success')
            return redirect(url_for('project.crawl_tasks_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'danger')
    
    teams = Team.query.all()
    students = Student.query.all()
    
    return render_template('project/crawl_task_add.html', form=form, teams=teams, students=students)


# ==================== 招聘岗位采集模块 ====================

@project_bp.route('/jobs')
@login_required
def job_postings_list():
    """招聘岗位列表"""
    keyword = request.args.get('keyword')
    location = request.args.get('location')
    salary = request.args.get('salary')
    experience = request.args.get('experience')
    
    jobs = CrawlerService.search_jobs(keyword=keyword, location=location, salary=salary, experience=experience)
    
    # 获取筛选选项
    locations = db.session.query(JobPosting.location).filter_by(is_duplicate=False).distinct().all()
    salaries = db.session.query(JobPosting.salary).filter_by(is_duplicate=False).distinct().all()
    experiences = db.session.query(JobPosting.experience).filter_by(is_duplicate=False).distinct().all()
    
    # 预设常用城市列表（如果数据库中没有数据）
    common_cities = ['北京', '上海', '杭州', '深圳', '广州', '成都', '武汉', '西安', '南京', '重庆', '天津', '苏州']
    db_locations = [l[0] for l in locations if l[0]]
    # 合并并去重
    all_locations = list(set(db_locations + common_cities))
    all_locations.sort()
    
    return render_template('project/job_postings_list.html', 
                         jobs=jobs,
                         locations=all_locations,
                         salaries=[s[0] for s in salaries if s[0]],
                         experiences=[e[0] for e in experiences if e[0]],
                         keyword=keyword,
                         selected_location=location,
                         selected_salary=salary,
                         selected_experience=experience)


@project_bp.route('/jobs/statistics')
@login_required
def job_statistics():
    """岗位统计分析"""
    stats = CrawlerService.get_job_statistics()
    wordcloud_data = CrawlerService.get_skill_wordcloud_data()
    
    # 转换数据格式供ECharts使用
    city_labels = [item[0] for item in stats['city_stats']]
    city_values = [item[1] for item in stats['city_stats']]
    
    salary_labels = [item[0] for item in stats['salary_stats']]
    salary_values = [item[1] for item in stats['salary_stats']]
    
    exp_labels = [item[0] for item in stats['exp_stats']]
    exp_values = [item[1] for item in stats['exp_stats']]
    
    # 技能排名
    skill_items = sorted(stats['skill_counts'].items(), key=lambda x: x[1], reverse=True)[:10]
    skill_labels = [item[0] for item in skill_items]
    skill_values = [item[1] for item in skill_items]
    
    return render_template('project/job_statistics.html',
                         stats=stats,
                         wordcloud_data=wordcloud_data,
                         city_labels=city_labels,
                         city_values=city_values,
                         salary_labels=salary_labels,
                         salary_values=salary_values,
                         exp_labels=exp_labels,
                         exp_values=exp_values,
                         skill_labels=skill_labels,
                         skill_values=skill_values)


@project_bp.route('/jobs/crawl', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def crawl_jobs():
    """执行岗位采集"""
    keywords = request.form.get('keywords', 'Python,Flask,爬虫,AI,Docker')
    keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
    
    try:
        total, saved, duplicate, errors = CrawlerService.crawl_job_postings(keywords=keyword_list)
        
        if total > 0:
            flash(f'采集完成，共获取 {total} 条岗位信息，新增 {saved} 条，重复 {duplicate} 条', 'success')
        else:
            if errors:
                flash(f'未采集到岗位数据，原因：{"；".join(errors[:3])}', 'warning')
            else:
                flash('未采集到岗位数据，建议生成模拟数据', 'warning')
    except Exception as e:
        flash(f'采集失败：{str(e)}', 'danger')
    
    return redirect(url_for('project.job_postings_list'))


@project_bp.route('/jobs/generate_mock', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def generate_mock_jobs():
    """生成模拟数据"""
    count = int(request.form.get('count', 50))
    
    try:
        saved, duplicate = CrawlerService.generate_mock_jobs(count=count)
        flash(f'生成完成，新增 {saved} 条，重复 {duplicate} 条', 'success')
    except Exception as e:
        flash(f'生成失败：{str(e)}', 'danger')
    
    return redirect(url_for('project.job_postings_list'))


@project_bp.route('/jobs/deduplicate', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def deduplicate_jobs():
    """执行去重"""
    try:
        count = CrawlerService.deduplicate_jobs()
        flash(f'去重完成，标记 {count} 条重复数据', 'success')
    except Exception as e:
        flash(f'去重失败：{str(e)}', 'danger')
    
    return redirect(url_for('project.job_postings_list'))


@project_bp.route('/jobs/config')
@login_required
@role_required('admin', 'teacher')
def crawler_config_list():
    """爬虫配置列表"""
    configs = CrawlerService.get_all_configs()
    return render_template('project/crawler_config_list.html', configs=configs)


@project_bp.route('/jobs/config/add', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def add_crawler_config():
    """添加爬虫配置"""
    keyword = request.form.get('keyword')
    source_type = request.form.get('source_type', 'lagou')
    max_pages = int(request.form.get('max_pages', 10))
    interval = int(request.form.get('interval', 3))
    
    if not keyword:
        flash('关键词不能为空', 'danger')
        return redirect(url_for('project.crawler_config_list'))
    
    try:
        CrawlerService.add_crawler_config(keyword=keyword, source_type=source_type, max_pages=max_pages, interval=interval)
        flash('配置添加成功', 'success')
    except Exception as e:
        flash(f'添加失败：{str(e)}', 'danger')
    
    return redirect(url_for('project.crawler_config_list'))


@project_bp.route('/jobs/config/<int:config_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def delete_crawler_config(config_id):
    """删除爬虫配置"""
    try:
        CrawlerService.delete_crawler_config(config_id)
        flash('配置删除成功', 'success')
    except Exception as e:
        flash(f'删除失败：{str(e)}', 'danger')
    
    return redirect(url_for('project.crawler_config_list'))


# ==================== 公告管理 ====================

@project_bp.route('/announcements')
@login_required
def announcements_list():
    """公告列表"""
    project_id = request.args.get('project_id', type=int)
    
    query = Announcement.query.filter_by(is_active=True)
    if project_id:
        query = query.filter_by(project_id=project_id)
    
    announcements = query.order_by(
        Announcement.is_pinned.desc(),
        Announcement.publish_at.desc()
    ).all()
    
    return render_template('project/announcements_list.html', announcements=announcements)


@project_bp.route('/announcements/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'teacher')
def add_announcement():
    """添加公告"""
    title = request.form.get('title')
    content = request.form.get('content')
    project_id = request.form.get('project_id', type=int)
    priority = request.form.get('priority', 'normal')
    is_pinned = request.form.get('is_pinned') == 'on'
    
    if not title or not content:
        flash('标题和内容不能为空', 'danger')
        return redirect(url_for('project.announcements_list'))
    
    announcement = Announcement(
        title=title,
        content=content,
        project_id=project_id,
        published_by=current_user.id,
        priority=priority,
        is_pinned=is_pinned
    )
    
    db.session.add(announcement)
    db.session.commit()
    
    flash('公告发布成功', 'success')
    return redirect(url_for('project.announcements_list'))


# ==================== 项目模板管理 ====================

@project_bp.route('/templates')
@login_required
@role_required('admin', 'teacher')
def templates_list():
    """项目模板列表"""
    page = request.args.get('page', 1, type=int)
    difficulty = request.args.get('difficulty')
    is_active = request.args.get('is_active')
    
    query = ProjectTemplate.query
    
    if difficulty:
        query = query.filter_by(difficulty_level=difficulty)
    if is_active is not None:
        query = query.filter_by(is_active=(is_active == 'true'))
    
    pagination = query.order_by(ProjectTemplate.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('project/templates_list.html', pagination=pagination)


@project_bp.route('/templates/<int:template_id>')
@login_required
def template_detail(template_id):
    """项目模板详情"""
    template = ProjectTemplate.query.get_or_404(template_id)
    
    # 统计使用该模板的项目数量
    projects_count = Project.query.filter_by(template_id=template_id).count()
    
    return render_template('project/template_detail.html', 
                         template=template, 
                         projects_count=projects_count)


@project_bp.route('/templates/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'teacher')
def add_template():
    """添加项目模板"""
    form = ProjectTemplateForm()
    
    if form.validate_on_submit():
        try:
            data = {
                'name': form.name.data,
                'description': form.description.data,
                'tech_stack': form.tech_stack.data,
                'difficulty_level': form.difficulty_level.data,
                'estimated_hours': form.estimated_hours.data,
                'template_config': form.template_config.data,
                'is_active': form.is_active.data,
                'created_by': current_user.id
            }
            
            from app.service.project_service import TemplateService
            template = TemplateService.create_template(data)
            log_action(current_user.id, 'create', 'templates', f'创建项目模板：{template.name}')
            flash('项目模板创建成功', 'success')
            return redirect(url_for('project.templates_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建模板失败：{str(e)}', 'danger')
    
    return render_template('project/template_add.html', form=form)


@project_bp.route('/templates/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'teacher')
def edit_template(template_id):
    """编辑项目模板"""
    template = ProjectTemplate.query.get_or_404(template_id)
    form = ProjectTemplateForm(obj=template)
    
    if form.validate_on_submit():
        try:
            data = {
                'name': form.name.data,
                'description': form.description.data,
                'tech_stack': form.tech_stack.data,
                'difficulty_level': form.difficulty_level.data,
                'estimated_hours': form.estimated_hours.data,
                'template_config': form.template_config.data,
                'is_active': form.is_active.data
            }
            
            from app.service.project_service import TemplateService
            TemplateService.update_template(template_id, data)
            log_action(current_user.id, 'update', 'templates', f'更新项目模板：{template.name}')
            flash('项目模板更新成功', 'success')
            return redirect(url_for('project.template_detail', template_id=template_id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新模板失败：{str(e)}', 'danger')
    
    return render_template('project/template_edit.html', form=form, template=template)


@project_bp.route('/templates/<int:template_id>/delete')
@login_required
@role_required('admin', 'teacher')
def delete_template(template_id):
    """删除项目模板"""
    template = ProjectTemplate.query.get_or_404(template_id)
    
    # 检查是否有项目使用该模板
    projects_using = Project.query.filter_by(template_id=template_id).count()
    if projects_using > 0:
        flash(f'该模板已被{projects_using}个项目使用，无法删除', 'danger')
        return redirect(url_for('project.templates_list'))
    
    db.session.delete(template)
    db.session.commit()
    
    log_action(current_user.id, 'delete', 'templates', f'删除项目模板：{template.name}')
    flash('项目模板删除成功', 'success')
    return redirect(url_for('project.templates_list'))