from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Notification, Announcement, User
from app.service.notification_service import NotificationService
from datetime import datetime

notification_bp = Blueprint('notification', __name__, url_prefix='/notifications')
announcement_bp = Blueprint('announcement', __name__, url_prefix='/announcements')

# ==================== 通知相关路由 ====================

@notification_bp.route('/')
@login_required
def index():
    """通知列表页"""
    page = request.args.get('page', 1, type=int)
    filter_type = request.args.get('type', 'all')
    
    query = Notification.query.filter_by(user_id=current_user.id)
    
    if filter_type != 'all':
        query = query.filter_by(type=filter_type)
    
    pagination = query.order_by(Notification.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    unread_count = NotificationService.get_unread_count(current_user.id)
    stats = NotificationService.get_statistics(current_user.id)
    
    return render_template('notification/index.html',
                         pagination=pagination,
                         unread_count=unread_count,
                         stats=stats,
                         filter_type=filter_type)

@notification_bp.route('/unread-count')
@login_required
def unread_count():
    """获取未读通知数量（AJAX）"""
    count = NotificationService.get_unread_count(current_user.id)
    return jsonify({'count': count})

@notification_bp.route('/api/recent')
@login_required
def recent_notifications():
    """获取最近通知列表（AJAX）"""
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .limit(10).all()
    
    return jsonify({
        'notifications': [{
            'id': n.id,
            'title': n.title,
            'content': n.content,
            'type': n.type,
            'link': n.link,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M')
        } for n in notifications]
    })

@notification_bp.route('/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_read(notification_id):
    """标记通知为已读（AJAX）"""
    success = NotificationService.mark_as_read(notification_id, current_user.id)
    if success:
        return jsonify({'success': True, 'message': '已标记为已读'})
    return jsonify({'success': False, 'message': '通知不存在'}), 404

@notification_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    """标记所有通知为已读（AJAX）"""
    NotificationService.mark_all_as_read(current_user.id)
    return jsonify({'success': True, 'message': '所有通知已标记为已读'})

@notification_bp.route('/<int:notification_id>/delete', methods=['POST'])
@login_required
def delete(notification_id):
    """删除通知（AJAX）"""
    success = NotificationService.delete_notification(notification_id, current_user.id)
    if success:
        return jsonify({'success': True, 'message': '通知已删除'})
    return jsonify({'success': False, 'message': '通知不存在'}), 404

@notification_bp.route('/clear-all', methods=['POST'])
@login_required
def clear_all():
    """清空所有通知（AJAX）"""
    NotificationService.clear_all_notifications(current_user.id)
    return jsonify({'success': True, 'message': '所有通知已清空'})

# ==================== 公告相关路由 ====================

@announcement_bp.route('/')
@login_required
def index():
    """公告列表页"""
    page = request.args.get('page', 1, type=int)
    
    query = Announcement.query.filter_by(is_active=True)
    pagination = query.order_by(
        Announcement.is_pinned.desc(),
        Announcement.publish_at.desc()
    ).paginate(page=page, per_page=15, error_out=False)
    
    return render_template('announcement/index.html', pagination=pagination)

@announcement_bp.route('/<int:announcement_id>')
@login_required
def detail(announcement_id):
    """公告详情页"""
    announcement = Announcement.query.get_or_404(announcement_id)
    
    if not announcement.is_active:
        flash('该公告已下架', 'warning')
        return redirect(url_for('announcement.index'))
    
    # 自动标记相关公告通知为已读
    Notification.query.filter_by(
        user_id=current_user.id,
        related_type='announcement',
        related_id=announcement_id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    
    return render_template('announcement/detail.html', announcement=announcement)

@announcement_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """创建公告（仅管理员）"""
    if current_user.role != 'admin':
        flash('仅管理员可以发布公告', 'danger')
        return redirect(url_for('announcement.index'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        priority = request.form.get('priority', 'normal')
        is_pinned = request.form.get('is_pinned') == 'on'
        expire_at = request.form.get('expire_at')
        
        if not title or not content:
            flash('标题和内容不能为空', 'danger')
            return render_template('announcement/create.html')
        
        announcement = Announcement(
            title=title,
            content=content,
            published_by=current_user.id,
            priority=priority,
            is_pinned=is_pinned,
            expire_at=datetime.strptime(expire_at, '%Y-%m-%dT%H:%M') if expire_at else None
        )
        
        db.session.add(announcement)
        db.session.commit()
        
        # 发送通知给所有用户
        all_users = User.query.filter_by(is_active=True).all()
        user_ids = [u.id for u in all_users]
        NotificationService.notify_announcement(
            announcement_id=announcement.id,
            title=title,
            target_user_ids=user_ids,
            sender_id=current_user.id
        )
        
        flash('公告发布成功', 'success')
        return redirect(url_for('announcement.detail', announcement_id=announcement.id))
    
    return render_template('announcement/create.html')

@announcement_bp.route('/<int:announcement_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(announcement_id):
    """编辑公告（仅管理员）"""
    announcement = Announcement.query.get_or_404(announcement_id)
    
    if current_user.role != 'admin' or announcement.published_by != current_user.id:
        flash('仅公告发布者可以编辑', 'danger')
        return redirect(url_for('announcement.index'))
    
    if request.method == 'POST':
        announcement.title = request.form.get('title', '').strip()
        announcement.content = request.form.get('content', '').strip()
        announcement.priority = request.form.get('priority', 'normal')
        announcement.is_pinned = request.form.get('is_pinned') == 'on'
        announcement.updated_at = datetime.utcnow()
        
        expire_at = request.form.get('expire_at')
        announcement.expire_at = datetime.strptime(expire_at, '%Y-%m-%dT%H:%M') if expire_at else None
        
        if not announcement.title or not announcement.content:
            flash('标题和内容不能为空', 'danger')
            return render_template('announcement/edit.html', announcement=announcement)
        
        db.session.commit()
        flash('公告更新成功', 'success')
        return redirect(url_for('announcement.detail', announcement_id=announcement.id))
    
    return render_template('announcement/edit.html', announcement=announcement)

@announcement_bp.route('/<int:announcement_id>/delete', methods=['POST'])
@login_required
def delete_announcement(announcement_id):
    """删除公告（仅管理员）"""
    announcement = Announcement.query.get_or_404(announcement_id)
    
    if current_user.role != 'admin' or announcement.published_by != current_user.id:
        flash('仅管理员可以删除公告', 'danger')
        return redirect(url_for('announcement.index'))
    
    announcement.is_active = False
    db.session.commit()
    
    flash('公告已删除', 'success')
    return redirect(url_for('announcement.index'))