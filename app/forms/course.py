from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, IntegerField, SelectField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError
from app.models import Course, Project, Student
from datetime import date

# 课程表单
class CourseForm(FlaskForm):
    course_code = StringField('课程代码', validators=[Length(max=20)])
    course_name = StringField('课程名称', validators=[DataRequired('课程名称不能为空'), Length(max=100)])
    credits = FloatField('学分', validators=[DataRequired('学分不能为空'), NumberRange(min=0.5, max=10)])
    teacher_id = SelectField('授课教师', coerce=int)
    semester = StringField('学期', validators=[DataRequired('学期不能为空'), Length(max=20)])
    year = IntegerField('学年', validators=[DataRequired('学年不能为空')])
    classroom = StringField('教室', validators=[Length(max=50)])
    hours = IntegerField('学时', validators=[DataRequired('学时不能为空'), NumberRange(min=1)])
    submit = SubmitField('提交')
    
    def __init__(self, *args, **kwargs):
        super(CourseForm, self).__init__(*args, **kwargs)
        from app.models import User
        teachers = User.query.filter_by(role='teacher').all()
        self.teacher_id.choices = [(t.id, t.name) for t in teachers]
    
    # 验证课程代码是否已存在
    def validate_course_code(self, field):
        if not field.data:
            return  # 自动生成时不验证
        if hasattr(self, '_obj') and self._obj:
            # 编辑模式：排除当前课程
            existing = Course.query.filter_by(course_code=field.data).first()
            if existing and existing.id != self._obj.id:
                raise ValidationError('该课程代码已被使用')
        else:
            # 添加模式：检查是否存在
            existing = Course.query.filter_by(course_code=field.data).first()
            if existing:
                raise ValidationError('该课程代码已被使用')

# 项目表单
class ProjectForm(FlaskForm):
    project_code = StringField('项目编号', validators=[DataRequired('项目编号不能为空'), Length(max=50)])
    name = StringField('项目名称', validators=[DataRequired('项目名称不能为空'), Length(max=100)])
    description = TextAreaField('项目简介')
    course_id = SelectField('所属课程', coerce=int, validators=[DataRequired('请选择所属课程')])
    template_id = SelectField('项目模板', coerce=int)
    teacher_id = SelectField('指导教师', coerce=int, validators=[DataRequired('请选择指导教师')])
    leader_id = SelectField('项目负责人', coerce=int)
    start_date = DateField('开始时间', validators=[DataRequired('开始时间不能为空')])
    end_date = DateField('结束时间', validators=[DataRequired('结束时间不能为空')])
    status = SelectField('项目状态', choices=[
        ('planning', '规划中'),
        ('ongoing', '进行中'),
        ('completed', '已完成'),
        ('archived', '已归档')
    ], default='planning')
    tech_stack = StringField('技术栈', validators=[Length(max=255)])
    evaluation_criteria = TextAreaField('评分规则')
    deploy_url = StringField('部署地址', validators=[Length(max=255)])
    max_team_size = IntegerField('最大小组人数', validators=[NumberRange(min=1, max=20)], default=5)
    requirements = TextAreaField('项目要求')
    submit = SubmitField('提交')
    
    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        from app.models import User, ProjectTemplate
        try:
            # 获取教师列表
            teachers = User.query.filter_by(role='teacher').all()
            self.teacher_id.choices = [(t.id, t.name) for t in teachers]
            
            # 获取学生列表（作为项目负责人）
            students = Student.query.all()
            self.leader_id.choices = [(s.id, f'{s.name} ({s.student_id})') for s in students]
            self.leader_id.choices.insert(0, (0, '无'))
            
            # 获取项目模板列表
            templates = ProjectTemplate.query.filter_by(is_active=True).all()
            self.template_id.choices = [(t.id, t.name) for t in templates]
            self.template_id.choices.insert(0, (0, '无模板'))
            
            # 获取课程列表
            courses = Course.query.all()
            self.course_id.choices = [(c.id, c.course_name) for c in courses]
        except Exception as e:
            print(f"[ERROR] ProjectForm初始化失败: {str(e)}")
            # 设置空选项，避免崩溃
            self.teacher_id.choices = []
            self.leader_id.choices = [(0, '无')]
            self.template_id.choices = [(0, '无模板')]
            self.course_id.choices = []
    
    # 验证项目编号是否已存在
    def validate_project_code(self, field):
        if hasattr(self, '_obj') and self._obj:
            # 编辑模式：排除当前项目
            existing = Project.query.filter_by(project_code=field.data).first()
            if existing and existing.id != self._obj.id:
                raise ValidationError('该项目编号已被使用')
        else:
            # 添加模式：检查是否存在
            existing = Project.query.filter_by(project_code=field.data).first()
            if existing:
                raise ValidationError('该项目编号已被使用')
    
    # 验证结束时间不能早于开始时间
    def validate_end_date(self, field):
        if self.start_date.data and field.data:
            if field.data < self.start_date.data:
                raise ValidationError('结束时间不能早于开始时间')