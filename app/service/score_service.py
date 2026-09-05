from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.models import Score, Student, Course
from app.data.db_utils import DBUtils
import io

class ScoreService:
    """
    成绩服务层
    处理成绩相关的业务逻辑，包括成绩录入/修改、查询统计等功能
    """
    
    def __init__(self, db_url: str):
        """
        初始化成绩服务层
        
        参数:
            db_url: 数据库连接URL
        """
        self.db_utils = DBUtils(db_url, Score)
    
    def create_score(self, db: Session, data: Dict[str, Any]) -> Score:
        """
        创建成绩记录
        
        参数:
            db: 数据库会话
            data: 成绩数据
            
        返回:
            Score: 创建成功的成绩实例
            
        异常:
            ValueError: 参数验证失败时抛出
            SQLAlchemyError: 数据库操作失败时抛出
        """
        # 验证必填字段
        required_fields = ['student_id', 'course_id', 'score', 'semester', 'year']
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValueError(f'缺少必填字段: {field}')
        
        # 验证分数范围
        if not (0 <= data['score'] <= 100):
            raise ValueError('分数必须在0-100之间')
        
        # 验证学生是否存在
        student = db.query(Student).filter(Student.id == data['student_id']).first()
        if not student:
            raise ValueError('无效的学生ID')
        
        # 验证课程是否存在
        course = db.query(Course).filter(Course.id == data['course_id']).first()
        if not course:
            raise ValueError('无效的课程ID')
        
        try:
            # 创建成绩记录
            return self.db_utils.create(db, data)
        except IntegrityError:
            db.rollback()
            raise ValueError('该学生的该门课程成绩已存在')
    
    def get_score(self, db: Session, score_id: int) -> Optional[Score]:
        """
        根据ID获取成绩记录
        
        参数:
            db: 数据库会话
            score_id: 成绩记录ID
            
        返回:
            Optional[Score]: 找到的成绩实例，找不到则返回None
        """
        return self.db_utils.get(db, score_id)
    
    def get_score_by_student_and_course(self, db: Session, student_id: int, course_id: int) -> Optional[Score]:
        """
        根据学生ID和课程ID获取成绩记录
        
        参数:
            db: 数据库会话
            student_id: 学生ID
            course_id: 课程ID
            
        返回:
            Optional[Score]: 找到的成绩实例，找不到则返回None
        """
        result = self.db_utils.query(db, filters={'student_id': student_id, 'course_id': course_id})
        return result['items'][0] if result and result['items'] else None
    
    def update_score(self, db: Session, score_id: int, data: Dict[str, Any]) -> Optional[Score]:
        """
        更新成绩记录
        
        参数:
            db: 数据库会话
            score_id: 成绩记录ID
            data: 要更新的成绩数据
            
        返回:
            Optional[Score]: 更新后的成绩实例，找不到则返回None
            
        异常:
            ValueError: 参数验证失败时抛出
            SQLAlchemyError: 数据库操作失败时抛出
        """
        # 如果包含分数，验证分数范围
        if 'score' in data:
            if not (0 <= data['score'] <= 100):
                raise ValueError('分数必须在0-100之间')
        
        return self.db_utils.update(db, score_id, data)
    
    def delete_score(self, db: Session, score_id: int) -> bool:
        """
        删除成绩记录
        
        参数:
            db: 数据库会话
            score_id: 成绩记录ID
            
        返回:
            bool: 删除成功返回True，找不到成绩记录返回False
            
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        return self.db_utils.delete(db, score_id)
    
    def query_scores(self, db: Session, filters: Dict[str, Any] = None, 
                    sort_by: str = 'id', sort_order: str = 'asc', 
                    page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """
        多条件查询成绩
        
        参数:
            db: 数据库会话
            filters: 查询条件字典
            sort_by: 排序字段
            sort_order: 排序顺序，'asc'表示升序，'desc'表示降序
            page: 页码
            per_page: 每页记录数
            
        返回:
            Dict[str, Any]: 包含查询结果和总记录数的字典
                            {'items': [Score], 'total': total_count}
        """
        return self.db_utils.query(db, filters=filters, sort_by=sort_by, sort_order=sort_order, page=page, per_page=per_page)
    
    def batch_create_scores(self, db: Session, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量创建成绩记录
        
        参数:
            db: 数据库会话
            data_list: 成绩数据列表
            
        返回:
            Dict[str, Any]: 批量导入结果
                            {'success': 成功导入数量, 'failed': 导入失败数量, 'errors': 错误信息列表}
        """
        success_count = 0
        failed_count = 0
        errors = []
        
        try:
            for i, data in enumerate(data_list):
                try:
                    # 验证必填字段
                    required_fields = ['student_id', 'course_id', 'score', 'semester', 'year']
                    for field in required_fields:
                        if field not in data or not data[field]:
                            raise ValueError(f'缺少必填字段: {field}')
                    
                    # 验证分数范围
                    if not (0 <= data['score'] <= 100):
                        raise ValueError('分数必须在0-100之间')
                    
                    # 验证学生和课程是否存在
                    student = db.query(Student).filter(Student.id == data['student_id']).first()
                    if not student:
                        raise ValueError('无效的学生ID')
                    
                    course = db.query(Course).filter(Course.id == data['course_id']).first()
                    if not course:
                        raise ValueError('无效的课程ID')
                    
                    # 创建成绩记录
                    score = Score(**data)
                    db.add(score)
                    success_count += 1
                except Exception as e:
                    failed_count += 1
                    errors.append(f'第{i+1}条记录导入失败: {str(e)}')
            
            db.commit()
        except Exception as e:
            db.rollback()
            errors.append(f'批量导入失败: {str(e)}')
        
        return {
            'success': success_count,
            'failed': failed_count,
            'errors': errors
        }
    
    def batch_update_scores(self, db: Session, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量更新成绩记录
        
        参数:
            db: 数据库会话
            data_list: 成绩数据列表，每条数据必须包含id字段
            
        返回:
            Dict[str, Any]: 批量更新结果
                            {'success': 成功更新数量, 'failed': 更新失败数量, 'errors': 错误信息列表}
        """
        success_count = 0
        failed_count = 0
        errors = []
        
        try:
            for i, data in enumerate(data_list):
                try:
                    # 验证ID字段
                    if 'id' not in data:
                        raise ValueError('缺少成绩记录ID')
                    
                    # 如果包含分数，验证分数范围
                    if 'score' in data:
                        if not (0 <= data['score'] <= 100):
                            raise ValueError('分数必须在0-100之间')
                    
                    # 更新成绩记录
                    score_id = data.pop('id')
                    if self.update_score(db, score_id, data):
                        success_count += 1
                    else:
                        raise ValueError('成绩记录不存在')
                except Exception as e:
                    failed_count += 1
                    errors.append(f'第{i+1}条记录更新失败: {str(e)}')
            
            db.commit()
        except Exception as e:
            db.rollback()
            errors.append(f'批量更新失败: {str(e)}')
        
        return {
            'success': success_count,
            'failed': failed_count,
            'errors': errors
        }
    
    def get_score_statistics(self, db: Session, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取成绩统计信息
        
        参数:
            db: 数据库会话
            filters: 查询条件字典
            
        返回:
            Dict[str, Any]: 成绩统计信息
                            {'total': 总记录数, 'average_score': 平均分, 'highest_score': 最高分, 'lowest_score': 最低分}
        """
        return self.db_utils.get_statistics(db, 'score', filters=filters)
    
    def export_scores(self, db: Session, filters: Dict[str, Any] = None) -> bytes:
        """
        导出成绩数据到Excel
        
        参数:
            db: 数据库会话
            filters: 查询条件字典
            
        返回:
            bytes: 包含Excel数据的字节流
        """
        return self.db_utils.export_to_excel(db, filters=filters).getvalue()
    
    def import_scores(self, db: Session, file_content: bytes) -> Dict[str, Any]:
        """
        从Excel导入成绩数据
        
        参数:
            db: 数据库会话
            file_content: 包含Excel数据的字节流
            
        返回:
            Dict[str, Any]: 导入结果统计
                            {'success': 成功导入数量, 'failed': 导入失败数量, 'errors': 错误信息列表}
        """
        return self.db_utils.import_from_excel(db, io.BytesIO(file_content))
    
    def get_course_score_statistics(self, db: Session, course_id: int) -> Dict[str, Any]:
        """
        获取课程成绩统计信息
        
        参数:
            db: 数据库会话
            course_id: 课程ID
            
        返回:
            Dict[str, Any]: 课程成绩统计信息
                            {'total_students': 总学生数, 'average_score': 平均分, 'highest_score': 最高分, 'lowest_score': 最低分,
                             'pass_rate': 通过率, 'grade_distribution': 成绩分布}
        """
        # 获取课程
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise ValueError('无效的课程ID')
        
        # 获取课程的所有成绩
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
    
    def get_student_score_statistics(self, db: Session, student_id: int) -> Dict[str, Any]:
        """
        获取学生成绩统计信息
        
        参数:
            db: 数据库会话
            student_id: 学生ID
            
        返回:
            Dict[str, Any]: 学生成绩统计信息
                            {'total_courses': 总课程数, 'average_score': 平均分, 'highest_score': 最高分, 'lowest_score': 最低分,
                             'pass_count': 通过课程数, 'pass_rate': 课程通过率}
        """
        # 获取学生
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise ValueError('无效的学生ID')
        
        # 获取学生的所有成绩
        scores = [score.score for score in student.scores]
        if not scores:
            return {
                'total_courses': 0,
                'average_score': 0,
                'highest_score': 0,
                'lowest_score': 0,
                'pass_count': 0,
                'pass_rate': 0
            }
        
        # 计算通过课程数（60分及以上）
        pass_count = sum(1 for score in scores if score >= 60)
        pass_rate = pass_count / len(scores)
        
        return {
            'total_courses': len(scores),
            'average_score': sum(scores) / len(scores),
            'highest_score': max(scores),
            'lowest_score': min(scores),
            'pass_count': pass_count,
            'pass_rate': pass_rate
        }