from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, Email, NumberRange

class SystemSettingsForm(FlaskForm):
    site_name = StringField('网站名称', validators=[DataRequired(), Length(max=100)])
    site_description = StringField('网站描述', validators=[Length(max=255)])
    site_keywords = StringField('网站关键词', validators=[Length(max=255)])
    contact_email = StringField('联系邮箱', validators=[DataRequired(), Email(), Length(max=100)])
    contact_phone = StringField('联系电话', validators=[DataRequired(), Length(max=20)])
    max_upload_size = IntegerField('最大上传文件大小 (MB)', validators=[NumberRange(min=1, max=100)])
    per_page = IntegerField('每页显示记录数', validators=[NumberRange(min=5, max=100)])
    bcrypt_log_rounds = IntegerField('密码加密强度', validators=[NumberRange(min=4, max=31)])
    submit = SubmitField('保存设置')
