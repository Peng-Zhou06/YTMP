from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.models import User, Student

# 登录表单
class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired('用户名不能为空'), Length(min=3, max=50)])
    password = PasswordField('密码', validators=[DataRequired('密码不能为空'), Length(min=6)])
    remember = BooleanField('记住我')
    submit = SubmitField('登录')

# 注册表单
class RegisterForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired('用户名不能为空'), Length(min=3, max=50)])
    name = StringField('姓名', validators=[DataRequired('姓名不能为空'), Length(min=2, max=50)])
    email = StringField('邮箱', validators=[DataRequired('邮箱不能为空'), Email('请输入有效的邮箱地址')])
    phone = StringField('电话', validators=[Length(min=0, max=20)])
    password = PasswordField('密码', validators=[DataRequired('密码不能为空'), Length(min=6)], default='123456')
    confirm_password = PasswordField('确认密码', validators=[DataRequired('请确认密码'), EqualTo('password', '两次输入的密码不一致')], default='123456')
    role = SelectField('角色', validators=[DataRequired('角色不能为空')],
                       choices=[('admin', '管理员'), ('teacher', '教师'), ('student', '学生')])
    submit = SubmitField('注册')
    
    def __init__(self, *args, **kwargs):
        # 保存当前用户ID，用于编辑用户时的验证
        self.user_id = kwargs.pop('user_id', None)
        super(RegisterForm, self).__init__(*args, **kwargs)
    
    # 验证用户名是否已存在
    def validate_username(self, username):
        if self.user_id:
            # 编辑用户时，排除当前用户自己
            user = User.query.filter(User.username == username.data, User.id != self.user_id).first()
        else:
            # 添加用户时，检查所有用户
            user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('该用户名已被使用')
    
    # 验证邮箱是否已存在（同时检查用户表和学生表）
    def validate_email(self, email):
        # 检查用户表
        user = User.query.filter_by(email=email.data).first()
        if user and user.id != self.user_id:
            raise ValidationError('该邮箱已被使用')
        
        # 检查学生表
        if self.user_id:
            # 编辑用户时，排除当前用户对应的学生记录（如果有的话）
            current_user = User.query.get(self.user_id)
            student = Student.query.filter_by(student_id=current_user.username).first()
            if student:
                # 找到当前用户对应的学生记录，排除它
                other_student = Student.query.filter(Student.email == email.data, Student.id != student.id).first()
            else:
                # 当前用户不是学生，检查所有学生记录
                other_student = Student.query.filter_by(email=email.data).first()
        else:
            # 添加用户时，检查所有学生记录
            other_student = Student.query.filter_by(email=email.data).first()
        
        if other_student:
            raise ValidationError('该邮箱已被使用')