from app.models import Notification, User, Announcement
from app import db
from datetime import datetime

class NotificationService:
    """消息通知服务"""
    
    @staticmethod
    def create_notification(user_id, title, content, type='info', link=None, 
                           sender_id=None, related_type=None, related_id=None):
        """创建单条通知"""
        notification = Notification(
            user_id=user_id,
            title=title,
            content=content,
            type=type,
            link=link,
            sender_id=sender_id,
            related_type=related_type,
            related_id=related_id
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @staticmethod
    def create_batch_notifications(user_ids, title, content, type='info', link=None,
                                  sender_id=None, related_type=None, related_id=None):
        """批量创建通知"""
        notifications = []
        for user_id in user_ids:
            notification = Notification(
                user_id=user_id,
                title=title,
                content=content,
                type=type,
                link=link,
                sender_id=sender_id,
                related_type=related_type,
                related_id=related_id
            )
            notifications.append(notification)
        
        db.session.bulk_save_objects(notifications)
        db.session.commit()
        return notifications
    
    @staticmethod
    def get_user_notifications(user_id, page=1, per_page=20, is_read=None):
        """获取用户通知列表"""
        query = Notification.query.filter_by(user_id=user_id)
        
        if is_read is not None:
            query = query.filter_by(is_read=is_read)
        
        return query.order_by(Notification.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
    
    @staticmethod
    def get_unread_count(user_id):
        """获取未读通知数量"""
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()
    
    @staticmethod
    def mark_as_read(notification_id, user_id):
        """标记通知为已读"""
        notification = Notification.query.filter_by(
            id=notification_id, user_id=user_id
        ).first()
        
        if notification:
            notification.is_read = True
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def mark_all_as_read(user_id):
        """标记所有通知为已读"""
        Notification.query.filter_by(user_id=user_id, is_read=False).update(
            {'is_read': True}
        )
        db.session.commit()
    
    @staticmethod
    def delete_notification(notification_id, user_id):
        """删除通知"""
        notification = Notification.query.filter_by(
            id=notification_id, user_id=user_id
        ).first()
        
        if notification:
            db.session.delete(notification)
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def clear_all_notifications(user_id):
        """清空所有通知"""
        Notification.query.filter_by(user_id=user_id).delete()
        db.session.commit()
    
    @staticmethod
    def notify_task_assigned(task_id, task_title, assigned_to_student, sender_id=None):
        """任务分配通知"""
        if assigned_to_student and assigned_to_student.user:
            NotificationService.create_notification(
                user_id=assigned_to_student.user.id,
                title='新任务分配',
                content=f'你被分配了新任务：{task_title}',
                type='task',
                link=f'/project/tasks/{task_id}',
                sender_id=sender_id,
                related_type='task',
                related_id=task_id
            )
    
    @staticmethod
    def notify_score_published(student_id, course_name, score, sender_id=None):
        """成绩发布通知"""
        student = Student.query.get(student_id)
        if student and student.user:
            NotificationService.create_notification(
                user_id=student.user.id,
                title='成绩发布',
                content=f'你的《{course_name}》成绩已发布：{score}分',
                type='success',
                link='/score/my_scores',
                sender_id=sender_id,
                related_type='score',
                related_id=student_id
            )
    
    @staticmethod
    def notify_bug_assigned(bug_id, bug_title, assigned_to_student, sender_id=None):
        """Bug分配通知"""
        if assigned_to_student and assigned_to_student.user:
            NotificationService.create_notification(
                user_id=assigned_to_student.user.id,
                title='Bug分配',
                content=f'你被分配了Bug：{bug_title}',
                type='warning',
                link=f'/project/bugs/{bug_id}',
                sender_id=sender_id,
                related_type='bug',
                related_id=bug_id
            )
    
    @staticmethod
    def notify_daily_report_review(report_id, student_id, has_issues, sender_id=None):
        """日报审核通知"""
        student = Student.query.get(student_id)
        if student and student.user:
            status = '存在问题，请修改' if has_issues else '审核通过'
            notif_type = 'warning' if has_issues else 'success'
            NotificationService.create_notification(
                user_id=student.user.id,
                title='日报审核',
                content=f'你的日报已审核：{status}',
                type=notif_type,
                link=f'/project/daily_reports/{report_id}',
                sender_id=sender_id,
                related_type='daily_report',
                related_id=report_id
            )
    
    @staticmethod
    def notify_announcement(announcement_id, title, target_user_ids=None, sender_id=None):
        """公告通知"""
        if target_user_ids:
            NotificationService.create_batch_notifications(
                user_ids=target_user_ids,
                title='新公告',
                content=title,
                type='announcement',
                link=f'/announcements/{announcement_id}',
                sender_id=sender_id,
                related_type='announcement',
                related_id=announcement_id
            )
    
    @staticmethod
    def get_statistics(user_id):
        """获取通知统计"""
        total = Notification.query.filter_by(user_id=user_id).count()
        unread = Notification.query.filter_by(user_id=user_id, is_read=False).count()
        
        type_stats = {}
        for notif_type in ['info', 'warning', 'success', 'error', 'task', 'announcement']:
            count = Notification.query.filter_by(user_id=user_id, type=notif_type).count()
            type_stats[notif_type] = count
        
        return {
            'total': total,
            'unread': unread,
            'type_stats': type_stats
        }

from app.models import Student