"""
AI 智能助手视图
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import AIAssistRecord, TeamMember, Student
from app.service.ai_assistant_service import AIAssistantService

ai_bp = Blueprint('ai_assistant', __name__, url_prefix='/ai')


@ai_bp.route('/chat')
@login_required
def chat_page():
    """AI 聊天页面"""
    student = None
    team = None
    
    if current_user.role == 'student':
        student = Student.query.filter_by(student_id=current_user.username).first()
        if student:
            team_member = TeamMember.query.filter_by(student_id=student.id).first()
            if team_member:
                team = team_member.team
    
    recent_records = []
    if student:
        recent_records = AIAssistRecord.query.filter_by(
            student_id=student.id
        ).order_by(AIAssistRecord.recorded_at.desc()).limit(10).all()
    
    return render_template('ai/chat.html', student=student, team=team, recent_records=recent_records)


@ai_bp.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """AI 对话 API"""
    data = request.get_json()
    message = data.get('message', '').strip()
    history = data.get('history', [])
    model = data.get('model', 'qwen-turbo')
    
    if not message:
        return jsonify({'success': False, 'error': '消息不能为空'}), 400
    
    result = AIAssistantService.chat(message, history, model)
    
    if result.get('success'):
        try:
            _save_ai_record(message, result)
        except Exception as e:
            print(f"保存 AI 记录失败: {e}")
    
    return jsonify(result)


@ai_bp.route('/api/analyze-code', methods=['POST'])
@login_required
def api_analyze_code():
    """代码分析 API"""
    data = request.get_json()
    code = data.get('code', '')
    question = data.get('question', '')
    
    if not code:
        return jsonify({'success': False, 'error': '代码不能为空'}), 400
    
    result = AIAssistantService.analyze_code(code, question)
    return jsonify(result)


@ai_bp.route('/api/explain-error', methods=['POST'])
@login_required
def api_explain_error():
    """错误解释 API"""
    data = request.get_json()
    error = data.get('error', '')
    code = data.get('code', '')
    
    if not error:
        return jsonify({'success': False, 'error': '错误信息不能为空'}), 400
    
    result = AIAssistantService.explain_error(error, code)
    return jsonify(result)


@ai_bp.route('/api/prompt-template/<scene>')
@login_required
def api_prompt_template(scene):
    """获取提示词模板"""
    template = AIAssistantService.generate_prompt_template(scene)
    return jsonify({'template': template})


@ai_bp.route('/history')
@login_required
def chat_history():
    """AI 使用历史"""
    student = Student.query.filter_by(student_id=current_user.username).first()
    
    if not student:
        return render_template('ai/history.html', records=[])
    
    page = request.args.get('page', 1, type=int)
    pagination = AIAssistRecord.query.filter_by(
        student_id=student.id
    ).order_by(AIAssistRecord.recorded_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('ai/history.html', pagination=pagination)


def _save_ai_record(prompt, result):
    """自动保存 AI 使用记录"""
    if current_user.role != 'student':
        return
    
    student = Student.query.filter_by(student_id=current_user.username).first()
    if not student:
        return
    
    team_member = TeamMember.query.filter_by(student_id=student.id).first()
    if not team_member:
        return
    
    record = AIAssistRecord(
        team_id=team_member.team_id,
        student_id=student.id,
        ai_tool=result.get('model', 'unknown'),
        usage_type='chat',
        usage_scene='智能助手对话',
        prompt=prompt[:1000],
        response_summary=result.get('response', '')[:500],
        applied=True,
        modified=False,
        effectiveness='good',
        time_saved=0.1
    )
    
    db.session.add(record)
    db.session.commit()