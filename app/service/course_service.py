from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models import Course, User, Score
from app.data.db_utils import DBUtils
import io

class CourseService:
    """
    课程服务层
    处理课程相关的业务逻辑，包括课程CRUD、教师关联等功能
    """
    
    def __init__(self, db_url: str):
        """
        初始化课程服务层
        
        参数:
            db_url: 数据库连接URL
        """
        self.db_utils = DBUtils(db_url, Course)
    
    def create_course(self, db: Session, data: Dict[str, Any]) -> Course:
        """
        创建课程
        
        参数:
            db: 数据库会话
            data: 课程数据
            
        返回:
            Course: 创建成功的课程实例
            
        异常:
            ValueError: 参数验证失败时抛出
            SQLAlchemyError: 数据库操作失败时抛出
        """
        # 验证必填字段
        required_fields = ['course_code', 'course_name', 'credits', 'teacher_id', 'semester', 'year', 'hours']
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValueError(f'缺少必填字段: {field}')
        
        # 验证教师是否存在
        teacher = db.query(User).filter(User.id == data['teacher_id']).first()
        if not teacher or teacher.role != 'teacher':
            raise ValueError('无效的教师ID')
        
        # 创建课程
        return self.db_utils.create(db, data)
    
    def get_course(self, db: Session, course_id: int) -> Optional[Course]:
        """
        根据ID获取课程
        
        参数:
            db: 数据库会话
            course_id: 课程ID
            
        返回:
            Optional[Course]: 找到的课程实例，找不到则返回None
        """
        return self.db_utils.get(db, course_id)
    
    def get_course_by_code(self, db: Session, course_code: str) -> Optional[Course]:
        """
        根据课程代码获取课程
        
        参数:
            db: 数据库会话
            course_code: 课程代码
            
        返回:
            Optional[Course]: 找到的课程实例，找不到则返回None
        """
        result = self.db_utils.query(db, filters={'course_code': course_code})
        return result['items'][0] if result and result['items'] else None
    
    def update_course(self, db: Session, course_id: int, data: Dict[str, Any]) -> Optional[Course]:
        """
        更新课程信息
        
        参数:
            db: 数据库会话
            course_id: 课程ID
            data: 要更新的课程数据
            
        返回:
            Optional[Course]: 更新后的课程实例，找不到则返回None
            
        异常:
            ValueError: 参数验证失败时抛出
            SQLAlchemyError: 数据库操作失败时抛出
        """
        # 如果包含教师ID，验证教师是否存在
        if 'teacher_id' in data:
            teacher = db.query(User).filter(User.id == data['teacher_id']).first()
            if not teacher or teacher.role != 'teacher':
                raise ValueError('无效的教师ID')
        
        return self.db_utils.update(db, course_id, data)
    
    def delete_course(self, db: Session, course_id: int) -> bool:
        """
        删除课程
        
        参数:
            db: 数据库会话
            course_id: 课程ID
            
        返回:
            bool: 删除成功返回True，找不到课程返回False
            
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        return self.db_utils.delete(db, course_id)
    
    def query_courses(self, db: Session, filters: Dict[str, Any] = None, 
                     sort_by: str = 'id', sort_order: str = 'asc', 
                     page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """
        多条件查询课程
        
        参数:
            db: 数据库会话
            filters: 查询条件字典
            sort_by: 排序字段
            sort_order: 排序顺序，'asc'表示升序，'desc'表示降序
            page: 页码
            per_page: 每页记录数
            
        返回:
            Dict[str, Any]: 包含查询结果和总记录数的字典
                            {'items': [Course], 'total': total_count}
        """
        return self.db_utils.query(db, filters=filters, sort_by=sort_by, sort_order=sort_order, page=page, per_page=per_page)
    
    def get_teacher_courses(self, db: Session, teacher_id: int) -> List[Course]:
        """
        获取教师教授的所有课程
        
        参数:
            db: 数据库会话
            teacher_id: 教师ID
            
        返回:
            List[Course]: 教师的课程列表
        """
        result = self.db_utils.query(db, filters={'teacher_id': teacher_id})
        return result['items']
    
    def get_course_scores(self, db: Session, course_id: int) -> List[Score]:
        """
        获取课程的所有成绩
        
        参数:
            db: 数据库会话
            course_id: 课程ID
            
        返回:
            List[Score]: 课程的成绩列表
        """
        course = self.get_course(db, course_id)
        return course.scores if course else []
    
    def get_course_score_statistics(self, db: Session, course_id: int) -> Dict[str, Any]:
        """
        获取课程的成绩统计信息
        
        参数:
            db: 数据库会话
            course_id: 课程ID
            
        返回:
            Dict[str, Any]: 课程的成绩统计信息
                            {'total_students': 总学生数, 'average_score': 平均分, 'highest_score': 最高分, 'lowest_score': 最低分,
                             'pass_rate': 通过率, 'grade_distribution': 成绩分布}
        """
        course = self.get_course(db, course_id)
        if not course:
            return {
                'total_students': 0,
                'average_score': 0,
                'highest_score': 0,
                'lowest_score': 0,
                'pass_rate': 0,
                'grade_distribution': {}
            }
        
        scores = [score.score for score in course.scores]
        if not scores:
            return {
                'total_students': 0,
                'average_score': 0,
                'highest_score': 0,
                'lowest_score': 0,
                'pass_rate': 0,
                'grade_distribution': {}
            }
        
        # 计算通过率（60分及以上）
        pass_count = sum(1 for score in scores if score >= 60)
        pass_rate = pass_count / len(scores)
        
        # 成绩分布
        grade_distribution = {
            '90-100': sum(1 for score in scores if score >= 90),
            '80-89': sum(1 for score in scores if 80 <= score < 90),
            '70-79': sum(1 for score in scores if 70 <= score < 80),
            '60-69': sum(1 for score in scores if 60 <= score < 70),
            '<60': sum(1 for score in scores if score < 60)
        }
        
        return {
            'total_students': len(scores),
            'average_score': sum(scores) / len(scores),
            'highest_score': max(scores),
            'lowest_score': min(scores),
            'pass_rate': pass_rate,
            'grade_distribution': grade_distribution
        }
    
    def batch_create_courses(self, db: Session, data_list: List[Dict[str, Any]]) -> List[Course]:
        """
        批量创建课程
        
        参数:
            db: 数据库会话
            data_list: 课程数据列表
            
        返回:
            List[Course]: 创建成功的课程实例列表
            
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        # 验证所有课程的教师ID
        teacher_ids = {data.get('teacher_id') for data in data_list}
        valid_teachers = set(
            teacher.id for teacher in db.query(User.id).filter(User.id.in_(teacher_ids), User.role == 'teacher').all()
        )
        
        for data in data_list:
            if data.get('teacher_id') not in valid_teachers:
                raise ValueError(f'课程数据中包含无效的教师ID: {data.get("teacher_id")}')
        
        return self.db_utils.batch_create(db, data_list)
    
    def batch_delete_courses(self, db: Session, course_ids: List[int]) -> int:
        """
        批量删除课程
        
        参数:
            db: 数据库会话
            course_ids: 课程ID列表
            
        返回:
            int: 成功删除的课程数
            
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        return self.db_utils.batch_delete(db, course_ids)
    
    def export_courses(self, db: Session, filters: Dict[str, Any] = None) -> bytes:
        """
        导出课程数据到Excel
        
        参数:
            db: 数据库会话
            filters: 查询条件字典
            
        返回:
            bytes: 包含Excel数据的字节流
        """
        return self.db_utils.export_to_excel(db, filters=filters).getvalue()
    
    def import_courses(self, db: Session, file_content: bytes) -> Dict[str, Any]:
        """
        从Excel导入课程数据
        
        参数:
            db: 数据库会话
            file_content: 包含Excel数据的字节流
            
        返回:
            Dict[str, Any]: 导入结果统计
                            {'success': 成功导入数量, 'failed': 导入失败数量, 'errors': 错误信息列表}
        """
        return self.db_utils.import_from_excel(db, io.BytesIO(file_content))
    
    def get_course_statistics(self, db: Session) -> Dict[str, Any]:
        """
        获取课程统计信息
        
        参数:
            db: 数据库会话
            
        返回:
            Dict[str, Any]: 课程统计信息
                            {'total': 总课程数, 'by_year': 按学年统计, 'by_semester': 按学期统计}
        """
        # 总课程数
        total = self.db_utils.query(db, page=1, per_page=1)['total']
        
        # 按学年统计
        from sqlalchemy import func
        year_statistics = db.query(
            Course.year,
            func.count(Course.id).label('count')
        ).group_by(Course.year).all()
        by_year = {stat.year: stat.count for stat in year_statistics}
        
        # 按学期统计
        semester_statistics = db.query(
            Course.semester,
            func.count(Course.id).label('count')
        ).group_by(Course.semester).all()
        by_semester = {stat.semester: stat.count for stat in semester_statistics}
        
        return {
            'total': total,
            'by_year': by_year,
            'by_semester': by_semester
        }