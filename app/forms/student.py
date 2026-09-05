from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, DateField, SelectField, TextAreaField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, ValidationError, Optional
from app.models import Student, Department, Major
from datetime import datetime

# 学生表单
class StudentForm(FlaskForm):
    student_id = StringField('学号', validators=[DataRequired('学号不能为空'), Length(min=5, max=20)])
    name = StringField('姓名', validators=[DataRequired('姓名不能为空'), Length(min=2, max=50)])
    gender = SelectField('性别', validators=[DataRequired('性别不能为空')], choices=[('male', '男'), ('female', '女')])
    grade = SelectField('年级', validators=[DataRequired('年级不能为空')])
    birthday = DateField('出生日期', format='%Y-%m-%d', validators=[DataRequired('出生日期不能为空')])
    department = SelectField('学院', validators=[DataRequired('学院不能为空')], choices=[])
    major = SelectField('专业', validators=[DataRequired('专业不能为空')], choices=[])
    class_name = StringField('班级', validators=[DataRequired('班级不能为空'), Length(max=50)])
    email = StringField('邮箱', validators=[DataRequired('邮箱不能为空'), Email('请输入有效的邮箱地址')])
    phone = StringField('电话', validators=[Length(max=20)])
    address = TextAreaField('地址', validators=[Length(max=255)])
    submit = SubmitField('提交')
    
    def __init__(self, *args, **kwargs):
        super(StudentForm, self).__init__(*args, **kwargs)
        current_year = datetime.now().year
        self.grade.choices = [(f'{y}级', f'{y}级') for y in range(current_year, current_year - 5, -1)]
        # 学院选项 - 从数据库加载
        departments = Department.query.filter_by(is_active=True).order_by(Department.sort_order, Department.name).all()
        self.department.choices = [(dept.name, dept.name) for dept in departments]
        # 专业选项 - 从数据库加载所有专业
        majors = Major.query.filter_by(is_active=True).order_by(Major.sort_order, Major.name).all()
        self.major.choices = [('', '请选择专业')] + [(m.name, m.name) for m in majors]
    
    # 验证学号是否已存在
    def validate_student_id(self, student_id):
        # 编辑时排除当前学生
        if hasattr(self, '_obj') and self._obj:
            # 编辑模式：排除当前学生
            existing = Student.query.filter_by(student_id=student_id.data).first()
            if existing and existing.id != self._obj.id:
                raise ValidationError('该学号已被使用')
        else:
            # 添加模式：检查是否存在
            existing = Student.query.filter_by(student_id=student_id.data).first()
            if existing:
                raise ValidationError('该学号已被使用')
    
    # 验证邮箱是否已存在
    def validate_email(self, email):
        # 编辑时排除当前学生
        if hasattr(self, '_obj') and self._obj:
            # 编辑模式：排除当前学生
            existing_student = Student.query.filter_by(email=email.data).first()
            if existing_student and existing_student.id != self._obj.id:
                raise ValidationError('该邮箱已被使用')
            
            # 同时检查用户表中的邮箱唯一性
            from app.models import User
            existing_user = User.query.filter_by(email=email.data).first()
            if existing_user:
                raise ValidationError('该邮箱已被使用')
        else:
            # 添加模式：检查学生表和用户表
            existing_student = Student.query.filter_by(email=email.data).first()
            if existing_student:
                raise ValidationError('该邮箱已被使用')
            
            from app.models import User
            existing_user = User.query.filter_by(email=email.data).first()
            if existing_user:
                raise ValidationError('该邮箱已被使用')
    
    # 验证出生日期是否合理
    def validate_birthday(self, birthday):
        if birthday.data > datetime.now().date():
            raise ValidationError('出生日期不能大于当前日期')

# 学生导入表单
class ImportForm(FlaskForm):
    file = FileField('Excel文件', validators=[
        FileRequired('请选择文件'),
        FileAllowed(['xlsx'], '只支持Excel 2007及以上版本(.xlsx)')
    ])
    overwrite = BooleanField('覆盖已存在的学生信息')
    submit = SubmitField('开始导入')