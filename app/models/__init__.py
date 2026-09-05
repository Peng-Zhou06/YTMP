from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship, backref
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# 用户角色枚举
class UserRole(Enum):
    ADMIN = 'admin'
    TEACHER = 'teacher'
    STUDENT = 'student'

# 性别枚举
class Gender(Enum):
    MALE = 'male'
    FEMALE = 'female'

# 登录用户加载函数
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 用户表
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(10), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20))
    avatar = Column(String(255))  # 头像路径
    is_active = Column(db.Boolean, default=True)  # 账号是否激活/禁用
    login_attempts = Column(Integer, default=0)  # 登录失败次数
    last_login_attempt = Column(DateTime)  # 最后一次登录尝试时间
    last_login_at = Column(DateTime)  # 最后登录时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    courses = relationship('Course', backref='teacher', lazy=True)
    logs = relationship('Log', backref='user', lazy=True)
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def increment_login_attempts(self):
        """增加登录失败次数"""
        self.login_attempts += 1
        self.last_login_attempt = datetime.utcnow()
        db.session.commit()
    
    def reset_login_attempts(self):
        """重置登录失败次数"""
        self.login_attempts = 0
        self.last_login_attempt = None
        self.last_login_at = datetime.utcnow()
        db.session.commit()
    
    def is_locked(self):
        """检查账号是否被锁定（登录失败超过5次）"""
        if self.login_attempts >= 5 and self.last_login_attempt:
            # 如果最后尝试时间在10分钟内，则锁定
            from datetime import timedelta
            if datetime.utcnow() - self.last_login_attempt < timedelta(minutes=10):
                return True
        return False

# 学生表
class Student(db.Model):
    __tablename__ = 'students'
    
    id = Column(Integer, primary_key=True)
    student_id = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False, index=True)
    gender = Column(String(10), nullable=False)
    grade = Column(String(20), nullable=False, index=True)
    birthday = Column(DateTime)
    class_name = Column(String(50), nullable=False, index=True)
    major = Column(String(100), nullable=False, index=True)
    department = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20))
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    scores = relationship('Score', backref='student', lazy=True)
    team_memberships = relationship('TeamMember', back_populates='student', lazy=True)
    led_teams = relationship('Team', primaryjoin='Student.id==Team.leader_id', back_populates='leader', lazy=True)
    assigned_tasks = relationship('Task', primaryjoin='Student.id==Task.assigned_to', back_populates='assignee', lazy=True)
    work_logs = relationship('WorkLog', back_populates='student', lazy=True)
    daily_reports = relationship('DailyReport', back_populates='student', lazy=True)
    reported_bugs = relationship('Bug', foreign_keys='Bug.reported_by', back_populates='reporter', lazy=True)
    assigned_bugs = relationship('Bug', foreign_keys='Bug.assigned_to', back_populates='assignee', lazy=True)
    code_commits = relationship('CodeCommit', back_populates='student', lazy=True)
    crawl_tasks = relationship('CrawlTask', back_populates='creator', lazy=True)
    ai_records = relationship('AIAssistRecord', back_populates='student', lazy=True)
    deployments = relationship('Deployment', back_populates='deployer', lazy=True)
    documents = relationship('ProjectDocument', back_populates='uploader', lazy=True)
    
    @property
    def user(self):
        """获取关联的User对象"""
        return User.query.filter_by(username=self.student_id).first()

# 课程表
class Course(db.Model):
    __tablename__ = 'courses'
    
    id = Column(Integer, primary_key=True)
    course_code = Column(String(20), unique=True, nullable=False, index=True)
    course_name = Column(String(100), nullable=False, index=True)
    credits = Column(Float, nullable=False)
    teacher_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    semester = Column(String(20), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    classroom = Column(String(50))
    hours = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    scores = relationship('Score', backref='course', lazy=True)
    projects = relationship('Project', backref='course', lazy=True)
    documents = relationship('CourseDocument', backref='course', lazy=True)

# 课程资料表
class CourseDocument(db.Model):
    __tablename__ = 'course_documents'
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(200), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(50))
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    uploader = relationship('User', backref='course_documents', lazy=True)

# 课程讨论表
class CourseDiscussion(db.Model):
    __tablename__ = 'course_discussions'
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    parent_id = Column(Integer, ForeignKey('course_discussions.id'), nullable=True)  # 评论的父ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    course = relationship('Course', backref='discussions', lazy=True)
    user = relationship('User', backref='course_discussions', lazy=True)
    replies = relationship('CourseDiscussion', backref=db.backref('parent', remote_side=[id]), lazy=True)

# 成绩表
class Score(db.Model):
    __tablename__ = 'scores'
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    score = Column(Float, nullable=False)
    semester = Column(String(20), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 复合唯一约束
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='_student_course_uc'),)

# 日志表
class Log(db.Model):
    __tablename__ = 'logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=False)
    detail = Column(Text)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# 系统设置表
class SystemSettings(db.Model):
    __tablename__ = 'system_settings'
    
    id = Column(Integer, primary_key=True)
    site_name = Column(String(100), default='云智实训管理平台')
    site_description = Column(String(255), default='一个功能完善的云智实训管理平台')
    site_keywords = Column(String(255), default='云智实训,项目管理,实训平台,教学管理')
    contact_email = Column(String(100), default='admin@example.com')
    contact_phone = Column(String(20), default='13800138000')
    max_upload_size = Column(Integer, default=16)  # MB
    per_page = Column(Integer, default=10)  # 每页显示记录数
    bcrypt_log_rounds = Column(Integer, default=13)  # 密码加密强度
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ==================== 云智实训管理平台新增模型 ====================

# 项目模板表
class ProjectTemplate(db.Model):
    __tablename__ = 'project_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    tech_stack = Column(String(255))  # 技术栈，如：Flask,React,Vue等
    difficulty_level = Column(String(20), default='medium')  # easy, medium, hard
    estimated_hours = Column(Integer)  # 预计工时
    template_config = Column(Text)  # JSON格式的项目配置
    is_active = Column(db.Boolean, default=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    projects = relationship('Project', backref='template', lazy=True)
    creator = relationship('User', backref='created_templates', lazy=True)

# 实训项目表
class Project(db.Model):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)
    project_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)  # 项目简介
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    template_id = Column(Integer, ForeignKey('project_templates.id'))
    teacher_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    leader_id = Column(Integer, ForeignKey('students.id'))  # 项目负责人（学生）
    start_date = Column(DateTime, nullable=False)  # 项目开始时间
    end_date = Column(DateTime, nullable=False)  # 项目结束时间
    status = Column(String(20), default='planning', index=True)  # planning, ongoing, completed, archived
    tech_stack = Column(String(255))  # 技术栈
    evaluation_criteria = Column(Text)  # 项目评分规则
    deploy_url = Column(String(255))  # 项目部署地址
    max_team_size = Column(Integer, default=5)
    requirements = Column(Text)  # 项目要求
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    teams = relationship('Team', backref='project', lazy=True)
    announcements = relationship('Announcement', backref='project', lazy=True)
    leader = relationship('Student', foreign_keys=[leader_id], backref='led_projects', lazy=True)
    teacher = relationship('User', foreign_keys=[teacher_id], backref='taught_projects', lazy=True)

# 小组表
class Team(db.Model):
    __tablename__ = 'teams'
    
    id = Column(Integer, primary_key=True)
    team_name = Column(String(100), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    leader_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    description = Column(Text)
    github_repo = Column(String(255))  # GitHub仓库地址
    status = Column(String(20), default='active')  # active, completed, disbanded
    score = Column(Float)  # 小组得分
    teacher_comment = Column(Text)  # 教师评语
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    members = relationship('TeamMember', backref='team', lazy=True)
    tasks = relationship('Task', backref='team', lazy=True)
    daily_reports = relationship('DailyReport', backref='team', lazy=True)
    bugs = relationship('Bug', backref='team', lazy=True)
    code_commits = relationship('CodeCommit', backref='team', lazy=True)
    crawler_data = relationship('CrawlerData', backref='team', lazy=True)
    ai_records = relationship('AIAssistRecord', backref='team', lazy=True)
    deployments = relationship('Deployment', backref='team', lazy=True)
    leader = relationship('Student', primaryjoin='Team.leader_id==Student.id', back_populates='led_teams')

# 小组成员表
class TeamMember(db.Model):
    __tablename__ = 'team_members'
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    role = Column(String(50), default='member')  # leader, frontend, backend, tester, etc.
    join_date = Column(DateTime, default=datetime.utcnow)
    contribution_score = Column(Float)  # 贡献度分数
    status = Column(String(20), default='active')  # active, inactive
    
    # 关系
    student = relationship('Student', back_populates='team_memberships')
    __table_args__ = (db.UniqueConstraint('team_id', 'student_id', name='_team_student_uc'),)

# 任务表
class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    task_code = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    assigned_to = Column(Integer, ForeignKey('students.id'))  # 负责人（学生ID）
    priority = Column(String(20), default='medium')  # high, medium, low
    status = Column(String(20), default='todo', index=True)  # todo, in_progress, review, done, delayed, closed
    progress = Column(Integer, default=0)  # 进度百分比 0-100
    estimated_hours = Column(Float)  # 预估工时
    actual_hours = Column(Float)  # 实际工时
    start_date = Column(DateTime)
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    completion_note = Column(Text)  # 完成说明
    screenshots = Column(Text)  # 相关截图，JSON格式
    related_bug_ids = Column(String(255))  # 关联Bug ID，逗号分隔
    tags = Column(String(255))  # 标签，逗号分隔
    attachments = Column(Text)  # 附件路径，JSON格式
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    assignee = relationship('Student', primaryjoin='Task.assigned_to==Student.id', back_populates='assigned_tasks')
    work_logs = relationship('WorkLog', backref='task', lazy=True)

# 工作日志表（任务进度记录）
class WorkLog(db.Model):
    __tablename__ = 'work_logs'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    work_date = Column(DateTime, default=datetime.utcnow)
    hours_spent = Column(Float)  # 花费工时
    description = Column(Text)  # 工作内容描述
    progress_delta = Column(Integer)  # 进度变化
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    student = relationship('Student', back_populates='work_logs')

# 日报表
class DailyReport(db.Model):
    __tablename__ = 'daily_reports'
    
    id = Column(Integer, primary_key=True)
    report_date = Column(DateTime, nullable=False, index=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    today_work = Column(Text)  # 今日工作内容
    tomorrow_plan = Column(Text)  # 明日计划
    issues = Column(Text)  # 遇到的问题
    solutions = Column(Text)  # 解决方案
    mood = Column(String(20))  # 心情指数：happy, normal, stressed
    working_hours = Column(Float)  # 工作时长
    is_submitted = Column(db.Boolean, default=False)
    teacher_review = Column(Text)  # 教师评语
    reviewed_by = Column(Integer, ForeignKey('users.id'))
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    student = relationship('Student', back_populates='daily_reports')
    reviewer = relationship('User', backref='reviewed_reports', lazy=True)
    __table_args__ = (db.UniqueConstraint('report_date', 'student_id', name='_date_student_uc'),)

# Bug表
class Bug(db.Model):
    __tablename__ = 'bugs'
    
    id = Column(Integer, primary_key=True)
    bug_code = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    reported_by = Column(Integer, ForeignKey('students.id'), nullable=False)
    assigned_to = Column(Integer, ForeignKey('students.id'))
    severity = Column(String(20), default='medium')  # critical, high, medium, low
    priority = Column(String(20), default='medium')  # low, medium, high, urgent
    status = Column(String(20), default='open', index=True)  # open, in_progress, fixed, verified, closed
    reproduction_steps = Column(Text)  # 复现步骤
    expected_result = Column(Text)  # 期望结果
    actual_result = Column(Text)  # 实际结果
    environment = Column(String(255))  # 环境信息
    screenshots = Column(Text)  # 截图路径，JSON格式
    fixed_at = Column(DateTime)
    verified_at = Column(DateTime)
    closed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    reporter = relationship('Student', foreign_keys=[reported_by], back_populates='reported_bugs')
    assignee = relationship('Student', foreign_keys=[assigned_to], back_populates='assigned_bugs')
    comments = relationship('BugComment', backref='bug', lazy=True)

# Bug评论表
class BugComment(db.Model):
    __tablename__ = 'bug_comments'
    
    id = Column(Integer, primary_key=True)
    bug_id = Column(Integer, ForeignKey('bugs.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    user = relationship('User', backref='bug_comments', lazy=True)

# 代码提交表
class CodeCommit(db.Model):
    __tablename__ = 'code_commits'
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    commit_hash = Column(String(100), nullable=False, index=True)
    commit_message = Column(Text, nullable=False)
    branch = Column(String(100), default='main')
    files_changed = Column(Integer)  # 变更文件数
    additions = Column(Integer)  # 新增行数
    deletions = Column(Integer)  # 删除行数
    commit_url = Column(String(255))  # 提交链接
    committed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    student = relationship('Student', back_populates='code_commits')

# 爬虫数据表
class CrawlerData(db.Model):
    __tablename__ = 'crawler_data'
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    source_url = Column(String(500), nullable=False)
    source_type = Column(String(50))  # 数据源类型
    data_title = Column(String(200))
    data_content = Column(Text)  # 爬取的数据内容
    data_format = Column(String(20), default='json')  # json, csv, html
    file_path = Column(String(255))  # 存储文件路径
    record_count = Column(Integer)  # 记录数量
    status = Column(String(20), default='success')  # success, failed, partial
    error_message = Column(Text)
    crawled_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

# 爬虫任务表
class CrawlTask(db.Model):
    __tablename__ = 'crawl_tasks'
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    name = Column(String(100), nullable=False)
    target_url = Column(String(500), nullable=False)
    crawl_frequency = Column(String(20), default='once')  # once, hourly, daily, weekly
    schedule_time = Column(String(50))  # 定时时间表达式
    is_active = Column(db.Boolean, default=True)
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    config = Column(Text)  # JSON格式的爬虫配置
    created_by = Column(Integer, ForeignKey('students.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    creator = relationship('Student', back_populates='crawl_tasks')

# 招聘岗位数据表
class JobPosting(db.Model):
    __tablename__ = 'job_postings'
    
    id = Column(Integer, primary_key=True)
    job_title = Column(String(200), nullable=False)  # 岗位名称
    company_name = Column(String(200))  # 公司名称
    company_type = Column(String(100))  # 公司类型（国企/民营/外企等）
    location = Column(String(100))  # 工作地点
    salary = Column(String(100))  # 薪资范围
    experience = Column(String(100))  # 经验要求
    education = Column(String(100))  # 学历要求
    tags = Column(Text)  # 技能标签，JSON格式
    description = Column(Text)  # 岗位职责描述
    requirements = Column(Text)  # 任职要求
    source_url = Column(String(500), nullable=False)  # 来源链接
    source_website = Column(String(100))  # 来源网站
    posted_date = Column(DateTime)  # 发布日期
    crawled_at = Column(DateTime, default=datetime.utcnow)  # 爬取时间
    is_processed = Column(db.Boolean, default=False)  # 是否已处理
    is_duplicate = Column(db.Boolean, default=False)  # 是否重复数据
    
    # 索引
    __table_args__ = (
        db.Index('idx_job_title', job_title),
        db.Index('idx_source_url', source_url),
        db.Index('idx_crawled_at', crawled_at),
    )

# 爬虫配置表
class CrawlerConfig(db.Model):
    __tablename__ = 'crawler_configs'
    
    id = Column(Integer, primary_key=True)
    keyword = Column(String(100), nullable=False)  # 采集关键词
    source_type = Column(String(50), nullable=False)  # 数据源类型
    target_url = Column(String(500))  # 目标URL模板
    enabled = Column(db.Boolean, default=True)  # 是否启用
    max_pages = Column(Integer, default=10)  # 最大采集页数
    interval = Column(Integer, default=3)  # 请求间隔（秒）
    last_run = Column(DateTime)  # 上次运行时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# AI辅助开发记录表
class AIAssistRecord(db.Model):
    __tablename__ = 'ai_assist_records'
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    ai_tool = Column(String(50))  # AI工具名称：通义灵码, 豆包, ChatGPT, Copilot, Claude等
    usage_type = Column(String(50))  # 使用场景类型
    usage_scene = Column(String(100))  # 使用场景描述
    prompt = Column(Text)  # 输入提示词
    response_summary = Column(Text)  # AI返回结果摘要
    code_snippet = Column(Text)  # 生成的代码片段
    applied = Column(db.Boolean, default=False)  # 是否直接采用
    modified = Column(db.Boolean, default=False)  # 是否进行了修改
    effectiveness = Column(String(20))  # 最终解决效果：excellent, good, fair, poor
    related_files = Column(String(500))  # 相关代码文件，逗号分隔
    risk_note = Column(Text)  # 风险说明
    time_saved = Column(Float)  # 节省的时间（小时）
    notes = Column(Text)  # 备注
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    student = relationship('Student', back_populates='ai_records')

# AI使用场景常量
AI_USAGE_SCENES = [
    '生成数据库表结构',
    '生成 Flask 路由',
    '解释报错',
    '优化页面样式',
    '生成测试用例',
    '编写 Dockerfile',
    '编写 docker-compose.yml',
    '生成部署文档',
    '分析日志',
    '生成项目总结',
    '其他'
]

# AI工具名称常量
AI_TOOLS = [
    '通义灵码',
    '豆包',
    'ChatGPT',
    'GitHub Copilot',
    'Claude',
    'Gemini',
    '其他'
]

# 效果评价常量
EFFECTIVENESS_CHOICES = [
    ('excellent', '优秀'),
    ('good', '良好'),
    ('fair', '一般'),
    ('poor', '较差')
]

# 部署状态表
class Deployment(db.Model):
    __tablename__ = 'deployments'
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    environment = Column(String(20), nullable=False)  # development, staging, production
    version = Column(String(50), nullable=False)
    deploy_status = Column(String(20), default='pending')  # pending, deploying, success, failed, rolled_back
    deploy_url = Column(String(255))  # 部署URL
    commit_hash = Column(String(100))  # 对应的commit hash
    deployed_by = Column(Integer, ForeignKey('students.id'), nullable=False)
    deploy_started_at = Column(DateTime)
    deploy_finished_at = Column(DateTime)
    rollback_reason = Column(Text)  # 回滚原因
    notes = Column(Text)  # 部署说明
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    deployer = relationship('Student', back_populates='deployments')

# 学院表
class Department(db.Model):
    __tablename__ = 'departments'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    icon = Column(String(50), default='fa-building')  # 图标
    sort_order = Column(Integer, default=0)  # 排序
    is_active = Column(db.Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    majors = relationship('Major', back_populates='department', order_by='Major.sort_order')

# 专业表
class Major(db.Model):
    __tablename__ = 'majors'
    
    id = Column(Integer, primary_key=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    sort_order = Column(Integer, default=0)  # 排序
    is_active = Column(db.Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    department = relationship('Department', back_populates='majors')
    
    __table_args__ = (
        db.UniqueConstraint('department_id', 'name', name='_dept_major_uc'),
    )

# 公告表
class Announcement(db.Model):
    __tablename__ = 'announcements'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'))
    published_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    priority = Column(String(20), default='normal')  # low, normal, high, urgent
    is_pinned = Column(db.Boolean, default=False)  # 是否置顶
    is_active = Column(db.Boolean, default=True)
    publish_at = Column(DateTime, default=datetime.utcnow)
    expire_at = Column(DateTime)  # 过期时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    publisher = relationship('User', backref='announcements', lazy=True)

# 项目文档表
class ProjectDocument(db.Model):
    __tablename__ = 'project_documents'
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    title = Column(String(200), nullable=False)
    doc_type = Column(String(50))  # requirement, design, api, test, manual, other
    file_path = Column(String(255), nullable=False)
    file_size = Column(Integer)  # 文件大小（字节）
    version = Column(String(20), default='1.0')
    uploaded_by = Column(Integer, ForeignKey('students.id'), nullable=False)
    download_count = Column(Integer, default=0)
    is_latest = Column(db.Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    uploader = relationship('Student', back_populates='documents')

# 消息通知表
class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    type = Column(String(50), default='info', index=True)  # info, warning, success, error, task, announcement
    link = Column(String(255))  # 点击跳转链接
    is_read = Column(db.Boolean, default=False, index=True)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # 发送者（可选）
    related_type = Column(String(50))  # 关联类型：task, score, bug, announcement等
    related_id = Column(Integer)  # 关联ID
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    user = relationship('User', foreign_keys='Notification.user_id', backref='notifications', lazy=True)
    sender = relationship('User', foreign_keys='Notification.sender_id', backref='sent_notifications', lazy=True)