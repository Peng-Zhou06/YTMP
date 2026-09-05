from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, FloatField, DateTimeField, BooleanField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, URL


class ProjectForm(FlaskForm):
    """项目表单"""
    name = StringField('项目名称', validators=[DataRequired(), Length(1, 100)])
    project_code = StringField('项目编号', validators=[DataRequired(), Length(1, 50)])
    description = TextAreaField('项目描述')
    course_id = IntegerField('课程ID', validators=[DataRequired()])
    template_id = IntegerField('模板ID', validators=[Optional()])
    teacher_id = IntegerField('教师ID', validators=[DataRequired()])
    start_date = DateTimeField('开始时间', format='%Y-%m-%d %H:%M:%S', validators=[DataRequired()])
    end_date = DateTimeField('结束时间', format='%Y-%m-%d %H:%M:%S', validators=[DataRequired()])
    max_team_size = IntegerField('最大小组人数', validators=[NumberRange(min=1, max=20)], default=5)
    requirements = TextAreaField('项目要求')
    evaluation_criteria = TextAreaField('评分标准')
    submit = SubmitField('提交')


class TeamForm(FlaskForm):
    """小组表单"""
    team_name = StringField('小组名称', validators=[DataRequired(), Length(1, 100)])
    project_id = SelectField('项目ID', coerce=int, validators=[DataRequired()])
    leader_id = SelectField('组长ID', coerce=int, validators=[DataRequired()])
    description = TextAreaField('小组描述')
    github_repo = StringField('GitHub仓库', validators=[Optional(), URL()])
    submit = SubmitField('提交')


class TaskForm(FlaskForm):
    """任务表单"""
    title = StringField('任务标题', validators=[DataRequired(), Length(1, 200)])
    task_code = StringField('任务编号', validators=[DataRequired(), Length(1, 50)])
    description = TextAreaField('任务描述')
    team_id = IntegerField('小组ID', validators=[DataRequired()])
    assigned_to = IntegerField('负责人（学号）', validators=[Optional()])
    priority = SelectField('优先级', choices=[
        ('high', '高'),
        ('medium', '中'),
        ('low', '低')
    ], default='medium')
    status = SelectField('状态', choices=[
        ('todo', '待开始'),
        ('in_progress', '进行中'),
        ('review', '待测试'),
        ('done', '已完成'),
        ('delayed', '已延期'),
        ('closed', '已关闭')
    ], default='todo')
    progress = IntegerField('进度（%）', validators=[Optional(), NumberRange(min=0, max=100)], default=0)
    estimated_hours = FloatField('预估工时', validators=[Optional(), NumberRange(min=0)])
    actual_hours = FloatField('实际工时', validators=[Optional(), NumberRange(min=0)])
    start_date = DateTimeField('开始时间', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    due_date = DateTimeField('截止时间', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    completion_note = TextAreaField('完成说明')
    screenshots = StringField('相关截图（多个URL用逗号分隔）')
    related_bug_ids = StringField('关联Bug ID（多个ID用逗号分隔）')
    tags = StringField('标签（逗号分隔）')
    submit = SubmitField('提交')


class DailyReportForm(FlaskForm):
    """日报表单"""
    report_date = DateTimeField('日期', format='%Y-%m-%d', validators=[DataRequired()])
    team_id = IntegerField('小组ID', validators=[DataRequired()])
    student_id = IntegerField('学生ID', validators=[DataRequired()])
    today_work = TextAreaField('今日工作内容', validators=[DataRequired()])
    tomorrow_plan = TextAreaField('明日计划')
    issues = TextAreaField('遇到的问题')
    solutions = TextAreaField('解决方案')
    mood = SelectField('心情指数', choices=[
        ('happy', '开心'),
        ('normal', '一般'),
        ('stressed', '压力大')
    ], default='normal')
    working_hours = FloatField('工作时长（小时）', validators=[Optional(), NumberRange(min=0, max=24)])
    is_submitted = BooleanField('提交', default=True)
    submit = SubmitField('提交日报')


class BugForm(FlaskForm):
    """Bug表单"""
    title = StringField('Bug标题', validators=[DataRequired(), Length(1, 200)])
    bug_code = StringField('Bug编号', validators=[DataRequired(), Length(1, 50)])
    description = TextAreaField('Bug描述')
    team_id = IntegerField('小组ID', validators=[DataRequired()])
    reported_by = IntegerField('报告人ID', validators=[DataRequired()])
    assigned_to = IntegerField('指派人ID', validators=[Optional()])
    severity = SelectField('严重程度', choices=[
        ('critical', '严重'),
        ('high', '高'),
        ('medium', '中'),
        ('low', '低')
    ], default='medium')
    priority = SelectField('优先级', choices=[
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('urgent', '紧急')
    ], default='medium')
    reproduction_steps = TextAreaField('复现步骤')
    expected_result = TextAreaField('期望结果')
    actual_result = TextAreaField('实际结果')
    environment = StringField('环境信息')
    submit = SubmitField('提交')


class AIAssistRecordForm(FlaskForm):
    """AI辅助记录表单"""
    team_id = IntegerField('小组ID', validators=[DataRequired()])
    student_id = IntegerField('学生ID', validators=[DataRequired()])
    ai_tool = SelectField('AI工具', choices=[
        ('tongyi', '通义灵码'),
        ('doubao', '豆包'),
        ('ChatGPT', 'ChatGPT'),
        ('Copilot', 'GitHub Copilot'),
        ('Claude', 'Claude'),
        ('Gemini', 'Gemini'),
        ('Other', '其他')
    ], validators=[DataRequired()])
    usage_type = SelectField('使用类型', choices=[
        ('code_generation', '代码生成'),
        ('debugging', '调试问题'),
        ('documentation', '文档编写'),
        ('testing', '测试用例'),
        ('design', '设计建议'),
        ('other', '其他')
    ], validators=[DataRequired()])
    usage_scene = StringField('使用场景', validators=[DataRequired()])
    prompt = TextAreaField('输入提示词', validators=[DataRequired()])
    response_summary = TextAreaField('AI返回结果摘要', validators=[DataRequired()])
    code_snippet = TextAreaField('生成的代码片段')
    applied = BooleanField('是否直接采用', default=False)
    modified = BooleanField('是否进行了修改', default=False)
    effectiveness = SelectField('最终解决效果', choices=[
        ('excellent', '优秀'),
        ('good', '良好'),
        ('fair', '一般'),
        ('poor', '较差')
    ], validators=[DataRequired()])
    related_files = StringField('相关代码文件')
    risk_note = TextAreaField('风险说明')
    time_saved = FloatField('节省时间（小时）', validators=[Optional(), NumberRange(min=0)])
    notes = TextAreaField('备注')
    submit = SubmitField('提交记录')


class DeploymentForm(FlaskForm):
    """部署表单"""
    team_id = IntegerField('小组ID', validators=[DataRequired()])
    environment = SelectField('环境', choices=[
        ('development', '开发环境'),
        ('staging', '测试环境'),
        ('production', '生产环境')
    ], validators=[DataRequired()])
    version = StringField('版本号', validators=[DataRequired(), Length(1, 50)])
    deploy_url = StringField('部署URL', validators=[Optional(), URL()])
    commit_hash = StringField('Commit Hash')
    deployed_by = IntegerField('部署人ID', validators=[DataRequired()])
    notes = TextAreaField('部署说明')
    submit = SubmitField('提交部署')


class CrawlTaskForm(FlaskForm):
    """爬虫任务表单"""
    name = StringField('任务名称', validators=[DataRequired(), Length(1, 100)])
    target_url = StringField('目标URL', validators=[DataRequired(), URL()])
    team_id = IntegerField('小组ID', validators=[DataRequired()])
    crawl_frequency = SelectField('爬取频率', choices=[
        ('once', '一次性'),
        ('hourly', '每小时'),
        ('daily', '每天'),
        ('weekly', '每周')
    ], default='once')
    schedule_time = StringField('定时时间表达式')
    config = TextAreaField('配置（JSON格式）')
    created_by = IntegerField('创建人ID', validators=[DataRequired()])
    submit = SubmitField('创建任务')


class ProjectTemplateForm(FlaskForm):
    """项目模板表单"""
    name = StringField('模板名称', validators=[DataRequired(), Length(1, 100)])
    description = TextAreaField('模板描述')
    tech_stack = StringField('技术栈（逗号分隔）', validators=[Optional()])
    difficulty_level = SelectField('难度级别', choices=[
        ('easy', '简单'),
        ('medium', '中等'),
        ('hard', '困难')
    ], default='medium')
    estimated_hours = IntegerField('预计工时（小时）', validators=[Optional(), NumberRange(min=1)])
    template_config = TextAreaField('模板配置（JSON格式）')
    is_active = BooleanField('启用', default=True)
    submit = SubmitField('提交')