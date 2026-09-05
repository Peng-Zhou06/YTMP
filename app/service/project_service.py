from app.models import Project, Team, Task, DailyReport, Bug, CodeCommit, CrawlerData, AIAssistRecord, Deployment, ProjectTemplate, WorkLog, BugComment
from app import db
from datetime import datetime
from sqlalchemy import func


class ProjectService:
    """项目服务类"""
    
    @staticmethod
    def get_project_by_id(project_id):
        """根据ID获取项目"""
        return Project.query.get_or_404(project_id)
    
    @staticmethod
    def get_all_projects(status=None, course_id=None, teacher_id=None, page=1, per_page=10):
        """获取所有项目，支持筛选和分页"""
        query = Project.query
        
        if status:
            query = query.filter_by(status=status)
        if course_id:
            query = query.filter_by(course_id=course_id)
        if teacher_id:
            query = query.filter_by(teacher_id=teacher_id)
        
        pagination = query.order_by(Project.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return pagination
    
    @staticmethod
    def create_project(data):
        """创建新项目"""
        project = Project(
            project_code=data['project_code'],
            name=data['name'],
            description=data.get('description'),
            course_id=data['course_id'],
            template_id=data.get('template_id'),
            teacher_id=data['teacher_id'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            max_team_size=data.get('max_team_size', 5),
            requirements=data.get('requirements'),
            evaluation_criteria=data.get('evaluation_criteria')
        )
        db.session.add(project)
        db.session.commit()
        return project
    
    @staticmethod
    def update_project(project_id, data):
        """更新项目信息"""
        project = Project.query.get_or_404(project_id)
        
        for key, value in data.items():
            if hasattr(project, key):
                setattr(project, key, value)
        
        project.updated_at = datetime.utcnow()
        db.session.commit()
        return project
    
    @staticmethod
    def delete_project(project_id):
        """删除项目"""
        project = Project.query.get_or_404(project_id)
        db.session.delete(project)
        db.session.commit()
    
    @staticmethod
    def get_project_statistics(project_id):
        """获取项目统计数据"""
        project = Project.query.get_or_404(project_id)
        
        # 小组数量
        total_teams = Team.query.filter_by(project_id=project_id).count()
        
        # 任务统计
        tasks = Task.query.join(Team).filter(Team.project_id == project_id).all()
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status == 'done')
        in_progress_tasks = sum(1 for t in tasks if t.status == 'in_progress')
        
        # 日报统计
        reports = DailyReport.query.join(Team).filter(Team.project_id == project_id).all()
        total_reports = len(reports)
        
        # Bug统计
        bugs = Bug.query.join(Team).filter(Team.project_id == project_id).all()
        total_bugs = len(bugs)
        open_bugs = sum(1 for b in bugs if b.status in ['open', 'in_progress'])
        fixed_bugs = sum(1 for b in bugs if b.status == 'fixed')
        
        # 代码提交统计
        commits = CodeCommit.query.join(Team).filter(Team.project_id == project_id).all()
        total_commits = len(commits)
        
        stats = {
            'total_teams': total_teams,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'in_progress_tasks': in_progress_tasks,
            'total_reports': total_reports,
            'total_bugs': total_bugs,
            'open_bugs': open_bugs,
            'fixed_bugs': fixed_bugs,
            'total_commits': total_commits,
            'progress': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        }
        
        return stats


class TeamService:
    """小组服务类"""
    
    @staticmethod
    def get_team_by_id(team_id):
        """根据ID获取小组"""
        return Team.query.get_or_404(team_id)
    
    @staticmethod
    def get_teams_by_project(project_id, page=1, per_page=10):
        """根据项目获取所有小组"""
        pagination = Team.query.filter_by(project_id=project_id).order_by(
            Team.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        return pagination
    
    @staticmethod
    def create_team(data):
        """创建新小组"""
        team = Team(
            team_name=data['team_name'],
            project_id=data['project_id'],
            leader_id=data['leader_id'],
            description=data.get('description'),
            github_repo=data.get('github_repo')
        )
        db.session.add(team)
        db.session.commit()
        
        # 添加组长为小组成员
        from app.models import TeamMember
        member = TeamMember(
            team_id=team.id,
            student_id=data['leader_id'],
            role='leader'
        )
        db.session.add(member)
        db.session.commit()
        
        return team
    
    @staticmethod
    def add_member(team_id, student_id, role='member'):
        """添加小组成员"""
        from app.models import TeamMember
        
        # 检查是否已存在
        existing = TeamMember.query.filter_by(team_id=team_id, student_id=student_id).first()
        if existing:
            return False
        
        member = TeamMember(
            team_id=team_id,
            student_id=student_id,
            role=role
        )
        db.session.add(member)
        db.session.commit()
        return True
    
    @staticmethod
    def remove_member(team_id, student_id):
        """移除小组成员"""
        from app.models import TeamMember
        member = TeamMember.query.filter_by(team_id=team_id, student_id=student_id).first()
        if member:
            db.session.delete(member)
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def get_team_statistics(team_id):
        """获取小组统计数据"""
        team = Team.query.get_or_404(team_id)
        
        # 成员数量
        member_count = len(team.members)
        
        # 任务统计
        total_tasks = len(team.tasks)
        completed_tasks = sum(1 for t in team.tasks if t.status == 'done')
        task_completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # 日报统计
        total_reports = len(team.daily_reports)
        
        # Bug统计
        total_bugs = len(team.bugs)
        open_bugs = sum(1 for b in team.bugs if b.status in ['open', 'in_progress'])
        
        # 代码提交统计
        total_commits = len(team.code_commits)
        
        # AI辅助记录
        ai_records_count = len(team.ai_records)
        
        # 部署次数
        deployment_count = len(team.deployments)
        
        stats = {
            'member_count': member_count,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'task_completion_rate': task_completion_rate,
            'total_reports': total_reports,
            'total_bugs': total_bugs,
            'open_bugs': open_bugs,
            'total_commits': total_commits,
            'ai_records_count': ai_records_count,
            'deployment_count': deployment_count
        }
        
        return stats


class TaskService:
    """任务服务类"""
    
    @staticmethod
    def get_task_by_id(task_id):
        """根据ID获取任务"""
        return Task.query.get_or_404(task_id)
    
    @staticmethod
    def get_tasks_by_team(team_id, status=None, assignee_id=None, priority=None, page=1, per_page=20):
        """根据小组获取任务列表，支持多种筛选"""
        query = Task.query.filter_by(team_id=team_id)
        
        if status:
            query = query.filter_by(status=status)
        if assignee_id:
            query = query.filter_by(assigned_to=assignee_id)
        if priority:
            query = query.filter_by(priority=priority)
        
        # 排序：优先级高的在前，然后按创建时间降序
        query = query.order_by(
            db.case(
                (Task.priority == 'high', 1),
                (Task.priority == 'medium', 2),
                (Task.priority == 'low', 3)
            ),
            Task.created_at.desc()
        )
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return pagination
    
    @staticmethod
    def create_task(data):
        """创建新任务"""
        # 验证 assigned_to 是否存在（如果提供了学号）
        assigned_to = data.get('assigned_to')
        if assigned_to:
            from app.models import Student
            student = Student.query.get(assigned_to)
            if not student:
                raise ValueError(f'指定的学生ID {assigned_to} 不存在')
        
        task = Task(
            task_code=data['task_code'],
            title=data['title'],
            description=data.get('description'),
            team_id=data['team_id'],
            assigned_to=assigned_to,
            priority=data.get('priority', 'medium'),
            status=data.get('status', 'todo'),
            progress=data.get('progress', 0),
            estimated_hours=data.get('estimated_hours'),
            actual_hours=data.get('actual_hours'),
            start_date=data.get('start_date'),
            due_date=data.get('due_date'),
            completion_note=data.get('completion_note'),
            screenshots=data.get('screenshots'),
            related_bug_ids=data.get('related_bug_ids'),
            tags=data.get('tags')
        )
        db.session.add(task)
        db.session.commit()
        return task
    
    @staticmethod
    def update_task(task_id, data):
        """更新任务信息"""
        task = Task.query.get_or_404(task_id)
        
        for key, value in data.items():
            if hasattr(task, key) and value is not None:
                setattr(task, key, value)
        
        # 如果状态变为完成，设置完成时间
        if data.get('status') == 'done' and not task.completed_at:
            task.completed_at = datetime.utcnow()
        
        task.updated_at = datetime.utcnow()
        db.session.commit()
        return task
    
    @staticmethod
    def update_task_status(task_id, status, progress=None):
        """更新任务状态"""
        task = Task.query.get_or_404(task_id)
        task.status = status
        
        if progress is not None:
            task.progress = progress
        
        if status == 'done' and not task.completed_at:
            task.completed_at = datetime.utcnow()
        
        task.updated_at = datetime.utcnow()
        db.session.commit()
        return task
    
    @staticmethod
    def add_work_log(task_id, student_id, hours_spent, description, progress_delta=0):
        """添加工作日志"""
        work_log = WorkLog(
            task_id=task_id,
            student_id=student_id,
            hours_spent=hours_spent,
            description=description,
            progress_delta=progress_delta
        )
        db.session.add(work_log)
        
        # 更新任务进度
        task = Task.query.get_or_404(task_id)
        task.actual_hours = (task.actual_hours or 0) + hours_spent
        task.progress = min(100, task.progress + progress_delta)
        
        db.session.commit()
        return work_log


class DailyReportService:
    """日报服务类"""
    
    @staticmethod
    def create_report(data):
        """创建日报"""
        report = DailyReport(
            report_date=data['report_date'],
            team_id=data['team_id'],
            student_id=data['student_id'],
            today_work=data['today_work'],
            tomorrow_plan=data.get('tomorrow_plan'),
            issues=data.get('issues'),
            solutions=data.get('solutions'),
            mood=data.get('mood'),
            working_hours=data.get('working_hours'),
            is_submitted=data.get('is_submitted', True)
        )
        db.session.add(report)
        db.session.commit()
        return report
    
    @staticmethod
    def review_report(report_id, teacher_id, review_text):
        """审核日报"""
        report = DailyReport.query.get_or_404(report_id)
        report.teacher_review = review_text
        report.reviewed_by = teacher_id
        report.reviewed_at = datetime.utcnow()
        db.session.commit()
        return report
    
    @staticmethod
    def get_reports_by_student(student_id, start_date=None, end_date=None, page=1, per_page=20):
        """获取学生的日报列表"""
        query = DailyReport.query.filter_by(student_id=student_id)
        
        if start_date:
            query = query.filter(DailyReport.report_date >= start_date)
        if end_date:
            query = query.filter(DailyReport.report_date <= end_date)
        
        pagination = query.order_by(DailyReport.report_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return pagination


class BugService:
    """Bug管理服务类"""
    
    @staticmethod
    def create_bug(data):
        """创建Bug"""
        bug = Bug(
            bug_code=data['bug_code'],
            title=data['title'],
            description=data.get('description'),
            team_id=data['team_id'],
            reported_by=data['reported_by'],
            assigned_to=data.get('assigned_to'),
            severity=data.get('severity', 'medium'),
            priority=data.get('priority', 'medium'),
            reproduction_steps=data.get('reproduction_steps'),
            expected_result=data.get('expected_result'),
            actual_result=data.get('actual_result'),
            environment=data.get('environment')
        )
        db.session.add(bug)
        db.session.commit()
        return bug
    
    @staticmethod
    def update_bug_status(bug_id, status, assigned_to=None):
        """更新Bug状态"""
        bug = Bug.query.get_or_404(bug_id)
        bug.status = status
        
        if assigned_to:
            bug.assigned_to = assigned_to
        
        if status == 'fixed' and not bug.fixed_at:
            bug.fixed_at = datetime.utcnow()
        elif status == 'verified' and not bug.verified_at:
            bug.verified_at = datetime.utcnow()
        elif status == 'closed' and not bug.closed_at:
            bug.closed_at = datetime.utcnow()
        
        bug.updated_at = datetime.utcnow()
        db.session.commit()
        return bug
    
    @staticmethod
    def add_comment(bug_id, user_id, content):
        """添加Bug评论"""
        comment = BugComment(
            bug_id=bug_id,
            user_id=user_id,
            content=content
        )
        db.session.add(comment)
        db.session.commit()
        return comment


class AIAssistService:
    """AI辅助开发记录服务类"""
    
    @staticmethod
    def create_record(data):
        """创建AI辅助记录"""
        record = AIAssistRecord(
            team_id=data['team_id'],
            student_id=data['student_id'],
            ai_tool=data['ai_tool'],
            usage_type=data['usage_type'],
            usage_scene=data.get('usage_scene'),
            prompt=data.get('prompt'),
            response_summary=data.get('response_summary'),
            code_snippet=data.get('code_snippet'),
            applied=data.get('applied', False),
            modified=data.get('modified', False),
            effectiveness=data.get('effectiveness'),
            related_files=data.get('related_files'),
            risk_note=data.get('risk_note'),
            time_saved=data.get('time_saved'),
            notes=data.get('notes')
        )
        db.session.add(record)
        db.session.commit()
        return record
    
    @staticmethod
    def get_statistics(team_id=None, student_id=None):
        """获取AI使用统计"""
        query = AIAssistRecord.query
        
        if team_id:
            query = query.filter_by(team_id=team_id)
        if student_id:
            query = query.filter_by(student_id=student_id)
        
        records = query.all()
        
        total_records = len(records)
        total_time_saved = sum(r.time_saved or 0 for r in records)
        applied_count = sum(1 for r in records if r.applied)
        
        # 按工具分类
        tool_stats = {}
        for r in records:
            tool = r.ai_tool
            if tool not in tool_stats:
                tool_stats[tool] = {'count': 0, 'time_saved': 0}
            tool_stats[tool]['count'] += 1
            tool_stats[tool]['time_saved'] += r.time_saved or 0
        
        # 按类型分类
        type_stats = {}
        for r in records:
            usage_type = r.usage_type
            if usage_type not in type_stats:
                type_stats[usage_type] = 0
            type_stats[usage_type] += 1
        
        return {
            'total_records': total_records,
            'total_time_saved': total_time_saved,
            'applied_count': applied_count,
            'tool_stats': tool_stats,
            'type_stats': type_stats
        }


class DeploymentService:
    """部署管理服务类"""
    
    @staticmethod
    def create_deployment(data):
        """创建部署记录"""
        deployment = Deployment(
            team_id=data['team_id'],
            environment=data['environment'],
            version=data['version'],
            deploy_url=data.get('deploy_url'),
            commit_hash=data.get('commit_hash'),
            deployed_by=data['deployed_by'],
            notes=data.get('notes')
        )
        db.session.add(deployment)
        db.session.commit()
        return deployment
    
    @staticmethod
    def update_deployment_status(deployment_id, status, deploy_finished_at=None, rollback_reason=None):
        """更新部署状态"""
        deployment = Deployment.query.get_or_404(deployment_id)
        deployment.deploy_status = status
        
        if status == 'deploying' and not deployment.deploy_started_at:
            deployment.deploy_started_at = datetime.utcnow()
        elif status in ['success', 'failed', 'rolled_back']:
            deployment.deploy_finished_at = deploy_finished_at or datetime.utcnow()
        
        if rollback_reason:
            deployment.rollback_reason = rollback_reason
        
        deployment.updated_at = datetime.utcnow()
        db.session.commit()
        return deployment


class TemplateService:
    """项目模板服务类"""
    
    @staticmethod
    def get_template_by_id(template_id):
        """根据ID获取模板"""
        return ProjectTemplate.query.get_or_404(template_id)
    
    @staticmethod
    def get_all_templates(difficulty=None, is_active=None, page=1, per_page=10):
        """获取所有模板，支持筛选和分页"""
        query = ProjectTemplate.query
        
        if difficulty:
            query = query.filter_by(difficulty_level=difficulty)
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        
        pagination = query.order_by(ProjectTemplate.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return pagination
    
    @staticmethod
    def create_template(data):
        """创建新模板"""
        template = ProjectTemplate(
            name=data['name'],
            description=data.get('description'),
            tech_stack=data.get('tech_stack'),
            difficulty_level=data.get('difficulty_level', 'medium'),
            estimated_hours=data.get('estimated_hours'),
            template_config=data.get('template_config'),
            is_active=data.get('is_active', True),
            created_by=data['created_by']
        )
        db.session.add(template)
        db.session.commit()
        return template
    
    @staticmethod
    def update_template(template_id, data):
        """更新模板信息"""
        template = ProjectTemplate.query.get_or_404(template_id)
        
        for key, value in data.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.updated_at = datetime.utcnow()
        db.session.commit()
        return template
    
    @staticmethod
    def delete_template(template_id):
        """删除模板"""
        template = ProjectTemplate.query.get_or_404(template_id)
        
        # 检查是否有项目使用该模板
        projects_using = Project.query.filter_by(template_id=template_id).count()
        if projects_using > 0:
            raise ValueError(f'该模板已被{projects_using}个项目使用，无法删除')
        
        db.session.delete(template)
        db.session.commit()