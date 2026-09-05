from flask_wtf import FlaskForm
from wtforms import SelectField, FloatField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from app.models import Student, Course

# 成绩表单
class ScoreForm(FlaskForm):
    student_id = SelectField('学生', validators=[DataRequired('请选择学生')], coerce=int)
    course_id = SelectField('课程', validators=[DataRequired('请选择课程')], coerce=int)
    score = FloatField('成绩', validators=[
        DataRequired('成绩不能为空'), 
        NumberRange(min=0, max=100, message='成绩必须在0-100之间')
    ])
    submit = SubmitField('提交')
    
    def __init__(self, course_id=None, *args, **kwargs):
        super(ScoreForm, self).__init__(*args, **kwargs)
        
        # 加载学生选项
        self.student_id.choices = [(s.id, f'{s.name}（{s.student_id}）') 
                                  for s in Student.query.all()]
        
        # 如果指定了课程ID，只显示该课程
        if course_id:
            course = Course.query.get(course_id)
            self.course_id.choices = [(course.id, f'{course.course_name}（{course.course_code}）')]
            self.course_id.default = course.id
            self.process()
        else:
            # 加载所有课程选项
            self.course_id.choices = [(c.id, f'{c.course_name}（{c.course_code}）') 
                                      for c in Course.query.all()]

# 成绩批量录入表单
class BatchScoreForm(FlaskForm):
    course_id = SelectField('课程', validators=[DataRequired('请选择课程')], coerce=int)
    submit = SubmitField('加载学生列表')
    
    def __init__(self, course_id=None, *args, **kwargs):
        super(BatchScoreForm, self).__init__(*args, **kwargs)
        # 加载课程选项
        self.course_id.choices = [(c.id, f'{c.course_name}（{c.course_code}）') 
                                  for c in Course.query.all()]
        
        # 如果指定了课程ID，设置默认值
        if course_id:
            self.course_id.default = course_id
            self.process()
