import os
import subprocess
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models import Log, User
from app.data.db_utils import DBUtils
import io

class SystemService:
    """
    系统服务层
    处理系统相关的业务逻辑，包括操作日志记录、数据备份恢复等功能
    """
    
    def __init__(self, db_url: str):
        """
        初始化系统服务层
        
        参数:
            db_url: 数据库连接URL
        """
        self.db_utils = DBUtils(db_url, Log)
    
    def record_log(self, db: Session, user_id: Optional[int], action: str, resource: str, 
                  detail: Optional[str] = None, ip_address: Optional[str] = None, 
                  user_agent: Optional[str] = None) -> bool:
        """
        记录操作日志
        
        参数:
            db: 数据库会话
            user_id: 操作用户ID
            action: 操作类型
            resource: 操作资源
            detail: 操作详情
            ip_address: IP地址
            user_agent: 用户代理
            
        返回:
            bool: 记录成功返回True，否则返回False
        """
        try:
            log_data = {
                'user_id': user_id,
                'action': action,
                'resource': resource,
                'detail': detail,
                'ip_address': ip_address,
                'user_agent': user_agent
            }
            self.db_utils.create(db, log_data)
            return True
        except Exception:
            return False
    
    def get_logs(self, db: Session, filters: Dict[str, Any] = None, 
                sort_by: str = 'created_at', sort_order: str = 'desc', 
                page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        查询操作日志
        
        参数:
            db: 数据库会话
            filters: 查询条件字典
            sort_by: 排序字段
            sort_order: 排序顺序，'asc'表示升序，'desc'表示降序
            page: 页码
            per_page: 每页记录数
            
        返回:
            Dict[str, Any]: 包含查询结果和总记录数的字典
                            {'items': [Log], 'total': total_count}
        """
        return self.db_utils.query(db, filters=filters, sort_by=sort_by, sort_order=sort_order, page=page, per_page=per_page)
    
    def backup_database(self, db_config: Dict[str, str], backup_dir: str) -> Dict[str, Any]:
        """
        备份数据库
        
        参数:
            db_config: 数据库配置
            backup_dir: 备份目录
            
        返回:
            Dict[str, Any]: 备份结果
                            {'success': 是否成功, 'filename': 备份文件名, 'message': 消息}
        """
        try:
            # 确保备份目录存在
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            # 生成备份文件名
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"{db_config['db']}_backup_{timestamp}.sql"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # 构建mysqldump命令
            mysqldump_cmd = [
                'mysqldump',
                '-h', db_config['host'],
                '-P', db_config['port'],
                '-u', db_config['user'],
                f"--password={db_config['password']}",
                db_config['db'],
                '--single-transaction',
                '--quick',
                '--lock-tables=false',
                '--result-file', backup_path
            ]
            
            # 执行备份命令
            result = subprocess.run(mysqldump_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'filename': None,
                    'message': f'备份失败: {result.stderr}'
                }
            
            return {
                'success': True,
                'filename': backup_filename,
                'message': f'数据库备份成功，备份文件: {backup_path}'
            }
        except Exception as e:
            return {
                'success': False,
                'filename': None,
                'message': f'备份失败: {str(e)}'
            }
    
    def restore_database(self, db_config: Dict[str, str], backup_file: str) -> Dict[str, Any]:
        """
        恢复数据库
        
        参数:
            db_config: 数据库配置
            backup_file: 备份文件路径
            
        返回:
            Dict[str, Any]: 恢复结果
                            {'success': 是否成功, 'message': 消息}
        """
        try:
            # 检查备份文件是否存在
            if not os.path.exists(backup_file):
                return {
                    'success': False,
                    'message': f'备份文件不存在: {backup_file}'
                }
            
            # 构建mysql命令
            mysql_cmd = [
                'mysql',
                '-h', db_config['host'],
                '-P', db_config['port'],
                '-u', db_config['user'],
                f"--password={db_config['password']}",
                db_config['db']
            ]
            
            # 执行恢复命令
            with open(backup_file, 'r') as f:
                result = subprocess.run(mysql_cmd, stdin=f, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'message': f'恢复失败: {result.stderr}'
                }
            
            return {
                'success': True,
                'message': '数据库恢复成功'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'恢复失败: {str(e)}'
            }
    
    def export_logs(self, db: Session, filters: Dict[str, Any] = None) -> bytes:
        """
        导出操作日志到Excel
        
        参数:
            db: 数据库会话
            filters: 查询条件字典
            
        返回:
            bytes: 包含Excel数据的字节流
        """
        return self.db_utils.export_to_excel(db, filters=filters).getvalue()
    
    def clear_old_logs(self, db: Session, days: int = 30) -> bool:
        """
        清理指定天数之前的日志
        
        参数:
            db: 数据库会话
            days: 保留天数，默认30天
            
        返回:
            bool: 清理成功返回True，否则返回False
        """
        try:
            from sqlalchemy import func
            import datetime
            
            # 计算删除时间点
            delete_before = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            
            # 删除旧日志
            result = db.query(Log).filter(Log.created_at < delete_before).delete(synchronize_session=False)
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
    
    def get_system_statistics(self, db: Session) -> Dict[str, Any]:
        """
        获取系统统计信息
        
        参数:
            db: 数据库会话
            
        返回:
            Dict[str, Any]: 系统统计信息
                            {'user_count': 用户总数, 'student_count': 学生总数, 'course_count': 课程总数,
                             'score_count': 成绩总数, 'log_count': 日志总数}
        """
        from sqlalchemy import func
        
        # 获取用户总数
        user_count = db.query(func.count(User.id)).scalar()
        
        # 获取学生总数
        from app.models import Student
        student_count = db.query(func.count(Student.id)).scalar()
        
        # 获取课程总数
        from app.models import Course
        course_count = db.query(func.count(Course.id)).scalar()
        
        # 获取成绩总数
        from app.models import Score
        score_count = db.query(func.count(Score.id)).scalar()
        
        # 获取日志总数
        log_count = db.query(func.count(Log.id)).scalar()
        
        return {
            'user_count': user_count,
            'student_count': student_count,
            'course_count': course_count,
            'score_count': score_count,
            'log_count': log_count
        }