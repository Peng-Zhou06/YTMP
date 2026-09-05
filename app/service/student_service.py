from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models import Student, Score
from app.data.db_utils import DBUtils
import io

class StudentService:
    """
    学生服务层
    处理学生相关的业务逻辑，包括学生CRUD、导入导出等功能
    """
    
    def __init__(self, db_url: str):
        """
        初始化学生服务层
        
        参数:
            db_url: 数据库连接URL
        """
        self.db_utils = DBUtils(db_url, Student)
    
    def create_student(self, db: Session, data: Dict[str, Any]) -> Student:
        """
        创建学生
        
        参数:
            db: 数据库会话
            data: 学生数据
            
        返回:
            Student: 创建成功的学生实例
            
        异常:
            ValueError: 参数验证失败时抛出
            SQLAlchemyError: 数据库操作失败时抛出
        """
        # 验证必填字段
        required_fields = ['student_id', 'name', 'gender', 'class_name', 'major', 'department', 'email']
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValueError(f'缺少必填字段: {field}')
        
        # 创建学生
        return self.db_utils.create(db, data)
    
    def get_student(self, db: Session, student_id: int) -> Optional[Student]:
        """
        根据ID获取学生
        
        参数:
            db: 数据库会话
            student_id: 学生ID
            
        返回:
            Optional[Student]: 找到的学生实例，找不到则返回None
        """
        return self.db_utils.get(db, student_id)
    
    def get_student_by_student_id(self, db: Session, student_id: str) -> Optional[Student]:
        """
        根据学号获取学生
        
        参数:
            db: 数据库会话
            student_id: 学号
            
        返回:
            Optional[Student]: 找到的学生实例，找不到则返回None
        """
        result = self.db_utils.query(db, filters={'student_id': student_id})
        return result['items'][0] if result and result['items'] else None
    
    def update_student(self, db: Session, student_id: int, data: Dict[str, Any]) -> Optional[Student]:
        """
        更新学生信息
        
        参数:
            db: 数据库会话
            student_id: 学生ID
            data: 要更新的学生数据
            
        返回:
            Optional[Student]: 更新后的学生实例，找不到则返回None
            
        异常:
            ValueError: 参数验证失败时抛出
            SQLAlchemyError: 数据库操作失败时抛出
        """
        return self.db_utils.update(db, student_id, data)
    
    def delete_student(self, db: Session, student_id: int) -> bool:
        """
        删除学生
        
        参数:
            db: 数据库会话
            student_id: 学生ID
            
        返回:
            bool: 删除成功返回True，找不到学生返回False
            
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        return self.db_utils.delete(db, student_id)
    
    def query_students(self, db: Session, filters: Dict[str, Any] = None, 
                      sort_by: str = 'id', sort_order: str = 'asc', 
                      page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """
        多条件查询学生
        
        参数:
            db: 数据库会话
            filters: 查询条件字典
            sort_by: 排序字段
            sort_order: 排序顺序，'asc'表示升序，'desc'表示降序
            page: 页码
            per_page: 每页记录数
            
        返回:
            Dict[str, Any]: 包含查询结果和总记录数的字典
                            {'items': [Student], 'total': total_count}
        """
        return self.db_utils.query(db, filters=filters, sort_by=sort_by, sort_order=sort_order, page=page, per_page=per_page)
    
    def get_student_scores(self, db: Session, student_id: int) -> List[Score]:
        """
        获取学生的所有成绩
        
        参数:
            db: 数据库会话
            student_id: 学生ID
            
        返回:
            List[Score]: 学生的成绩列表
        """
        student = self.get_student(db, student_id)
        return student.scores if student else []
    
    def get_student_score_statistics(self, db: Session, student_id: int) -> Dict[str, Any]:
        """
        获取学生的成绩统计信息
        
        参数:
            db: 数据库会话
            student_id: 学生ID
            
        返回:
            Dict[str, Any]: 学生的成绩统计信息
                            {'total_courses': 总课程数, 'average_score': 平均分, 'highest_score': 最高分, 'lowest_score': 最低分}
        """
        student = self.get_student(db, student_id)
        if not student:
            return {
                'total_courses': 0,
                'average_score': 0,
                'highest_score': 0,
                'lowest_score': 0
            }
        
        scores = [score.score for score in student.scores]
        if not scores:
            return {
                'total_courses': 0,
                'average_score': 0,
                'highest_score': 0,
                'lowest_score': 0
            }
        
        return {
            'total_courses': len(scores),
            'average_score': sum(scores) / len(scores),
            'highest_score': max(scores),
            'lowest_score': min(scores)
        }
    
    def batch_create_students(self, db: Session, data_list: List[Dict[str, Any]]) -> List[Student]:
        """
        批量创建学生
        
        参数:
            db: 数据库会话
            data_list: 学生数据列表
            
        返回:
            List[Student]: 创建成功的学生实例列表
            
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        return self.db_utils.batch_create(db, data_list)
    
    def batch_delete_students(self, db: Session, student_ids: List[int]) -> int:
        """
        批量删除学生
        
        参数:
            db: 数据库会话
            student_ids: 学生ID列表
            
        返回:
            int: 成功删除的学生数
            
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        return self.db_utils.batch_delete(db, student_ids)
    
    def export_students(self, db: Session, filters: Dict[str, Any] = None) -> bytes:
        """
        导出学生数据到Excel
        
        参数:
            db: 数据库会话
            filters: 查询条件字典
            
        返回:
            bytes: 包含Excel数据的字节流
        """
        return self.db_utils.export_to_excel(db, filters=filters).getvalue()
    
    def import_students(self, db: Session, file_content: bytes) -> Dict[str, Any]:
        """
        从Excel导入学生数据
        
        参数:
            db: 数据库会话
            file_content: 包含Excel数据的字节流
            
        返回:
            Dict[str, Any]: 导入结果统计
                            {'success': 成功导入数量, 'failed': 导入失败数量, 'errors': 错误信息列表}
        """
        return self.db_utils.import_from_excel(db, io.BytesIO(file_content))
    
    def get_student_statistics(self, db: Session) -> Dict[str, Any]:
        """
        获取学生统计信息
        
        参数:
            db: 数据库会话
            
        返回:
            Dict[str, Any]: 学生统计信息
                            {'total': 总学生数, 'by_class': 按班级统计, 'by_department': 按院系统计}
        """
        # 总学生数
        total = self.db_utils.query(db, page=1, per_page=1)['total']
        
        # 按班级统计
        from sqlalchemy import func
        class_statistics = db.query(
            Student.class_name,
            func.count(Student.id).label('count')
        ).group_by(Student.class_name).all()
        by_class = {stat.class_name: stat.count for stat in class_statistics}
        
        # 按院系统计
        department_statistics = db.query(
            Student.department,
            func.count(Student.id).label('count')
        ).group_by(Student.department).all()
        by_department = {stat.department: stat.count for stat in department_statistics}
        
        return {
            'total': total,
            'by_class': by_class,
            'by_department': by_department
        }