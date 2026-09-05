from datetime import datetime
from app import db
from app.models import Log
import logging
import traceback

logger = logging.getLogger('app.logs')

def log_action(user_id, action, resource, detail, ip_address=None, user_agent=None):
    try:
        log = Log(
            user_id=user_id,
            action=action,
            resource=resource,
            detail=detail,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        logger.info(f'操作日志: user_id={user_id}, action={action}, resource={resource}')
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f'日志记录失败: {str(e)}\n{traceback.format_exc()}')
        return False
