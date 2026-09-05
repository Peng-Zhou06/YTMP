from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models import User, UserRole
from app.data.db_utils import DBUtils

class UserService:
    """
    用户服务层
    处理用户相关的业务逻辑，包括权限校验、用户CRUD等功能
    """
    
    def __init__(self, db_url: str):
        """
        初始化用户服务层
        
        参数:
            db_url: 数据库连接URL
        """
        self.db_utils = DBUtils(db_url, User)
    
    def create_user(self, db: Session, data: Dict[str, Any]) -> User:
        """
        创建用户
        
        参数:
            db: 数据库会话
            data: 用户数据
            
        返回:
            User: 创建成功的用户实例
            
        异常:
            ValueError: 参数验证失败时抛出
            SQLAlchemyError: 数据库操作失败时抛出
        """
        # 验证必填字段
        required_fields = ['username', 'password', 'role', 'name', 'email']
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValueError(f'缺少必填字段: {field}')
        
        # 验证角色合法性
        if data['role'] not in [role.value for role in UserRole]:
            raise ValueError(f'无效的用户角色: {data["role"]}')
        
        # 创建用户
        return self.db_utils.create(db, data)
    
    def get_user(self, db: Session, user_id: int) -> Optional[User]:
        """
        根据ID获取用户
        
        参数:
            db: 数据库会话
            user_id: 用户ID
            
        返回:
            Optional[User]: 找到的用户实例，找不到则返回None
        """
        return self.db_utils.get(db, user_id)
    
    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        """
        根据用户名获取用户
        
        参数:
            db: 数据库会话
            username: 用户名
            
        返回:
            Optional[User]: 找到的用户实例，找不到则返回None
        """
        result = self.db_utils.query(db, filters={'username': username})
        return result['items'][0] if result and result['items'] else None
    
    def update_user(self, db: Session, user_id: int, data: Dict[str, Any]) -> Optional[User]:
        """
        更新用户信息
        
        参数:
            db: 数据库会话
            user_id: 用户ID
            data: 要更新的用户数据
            
        返回:
            Optional[User]: 更新后的用户实例，找不到则返回None
            
        异常:
            ValueError: 参数验证失败时抛出
            SQLAlchemyError: 数据库操作失败时抛出
        """
        # 如果包含角色信息，验证角色合法性
        if 'role' in data:
            if data['role'] not in [role.value for role in UserRole]:
                raise ValueError(f'无效的用户角色: {data["role"]}')
        
        # 更新用户
        return self.db_utils.update(db, user_id, data)
    
    def delete_user(self, db: Session, user_id: int) -> bool:
        """
        删除用户
        
        参数:
            db: 数据库会话
            user_id: 用户ID
            
        返回:
            bool: 删除成功返回True，找不到用户返回False
            
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        return self.db_utils.delete(db, user_id)
    
    def query_users(self, db: Session, filters: Dict[str, Any] = None, 
                    sort_by: str = 'id', sort_order: str = 'asc', 
                    page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """
        多条件查询用户
        
        参数:
            db: 数据库会话
            filters: 查询条件字典
            sort_by: 排序字段
            sort_order: 排序顺序，'asc'表示升序，'desc'表示降序
            page: 页码
            per_page: 每页记录数
            
        返回:
            Dict[str, Any]: 包含查询结果和总记录数的字典
                            {'items': [User], 'total': total_count}
        """
        return self.db_utils.query(db, filters=filters, sort_by=sort_by, sort_order=sort_order, page=page, per_page=per_page)
    
    def verify_password(self, user: User, password: str) -> bool:
        """
        验证用户密码
        
        参数:
            user: 用户实例
            password: 待验证的密码
            
        返回:
            bool: 密码正确返回True，否则返回False
        """
        return user.verify_password(password)
    
    def check_permission(self, user: User, required_roles: List[str]) -> bool:
        """
        检查用户是否具有指定角色权限
        
        参数:
            user: 用户实例
            required_roles: 要求的角色列表
            
        返回:
            bool: 具有权限返回True，否则返回False
        """
        return user.role in required_roles
    
    def get_user_statistics(self, db: Session) -> Dict[str, Any]:
        """
        获取用户统计信息
        
        参数:
            db: 数据库会话
            
        返回:
            Dict[str, Any]: 包含各角色用户数量的统计信息
        """
        # 统计管理员数量
        admin_count = self.db_utils.query(db, filters={'role': UserRole.ADMIN.value})['total']
        
        # 统计教师数量
        teacher_count = self.db_utils.query(db, filters={'role': UserRole.TEACHER.value})['total']
        
        # 统计学生数量
        student_count = self.db_utils.query(db, filters={'role': UserRole.STUDENT.value})['total']
        
        # 总用户数
        total_count = admin_count + teacher_count + student_count
        
        return {
            'total': total_count,
            'admin': admin_count,
            'teacher': teacher_count,
            'student': student_count
        }
    
    def export_users(self, db: Session, filters: Dict[str, Any] = None) -> bytes:
        """
        导出用户数据到Excel
        
        参数:
            db: 数据库会话
            filters: 查询条件字典
            
        返回:
            bytes: 包含Excel数据的字节流
        """
        return self.db_utils.export_to_excel(db, filters=filters).getvalue()
    
    def import_users(self, db: Session, file_content: bytes) -> Dict[str, Any]:
        """
        从Excel导入用户数据
        
        参数:
            db: 数据库会话
            file_content: 包含Excel数据的字节流
            
        返回:
            Dict[str, Any]: 导入结果统计
                            {'success': 成功导入数量, 'failed': 导入失败数量, 'errors': 错误信息列表}
        """
        import io
        return self.db_utils.import_from_excel(db, io.BytesIO(file_content))