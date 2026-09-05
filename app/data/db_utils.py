from typing import List, Dict, Any, Optional, Type, TypeVar, Generic
from sqlalchemy import create_engine, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.declarative import DeclarativeMeta
import pandas as pd
import io
import re
from app.models import Base

# 定义泛型类型
T = TypeVar('T', bound=Base)

class DBUtils(Generic[T]):
    """
    数据库工具类
    提供通用的CRUD操作、多条件查询、批量操作、导入导出等功能
    支持SQL注入防护和XSS防护
    """
    
    def __init__(self, db_url: str, model: Type[T]):
        """
        初始化数据库工具类
        
        参数:
            db_url: 数据库连接URL
            model: 对应的ORM模型类
        """
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.model = model
    
    def create(self, db: Session, data: Dict[str, Any]) -> T:
        """
        创建新记录
        
        参数:
            db: 数据库会话
            data: 要创建的记录数据
            
        返回:
            T: 创建成功的模型实例
            
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        try:
            # XSS防护：对输入数据进行过滤
            sanitized_data = self._sanitize_data(data)
            db_obj = self.model(**sanitized_data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            db.rollback()
            raise e
    
    def get(self, db: Session, record_id: int) -> Optional[T]:
        """
        根据ID获取单条记录
        
        参数:
            db: 数据库会话
            record_id: 记录ID
            
        返回:
            Optional[T]: 找到的模型实例，找不到则返回None
        """
        return db.query(self.model).filter(self.model.id == record_id).first()
    
    def update(self, db: Session, record_id: int, data: Dict[str, Any]) -> Optional[T]:
        """
        更新记录
        
        参数:
            db: 数据库会话
            record_id: 记录ID
            data: 要更新的数据
            
        返回:
            Optional[T]: 更新后的模型实例，找不到则返回None
            
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        try:
            db_obj = self.get(db, record_id)
            if not db_obj:
                return None
            
            # XSS防护：对输入数据进行过滤
            sanitized_data = self._sanitize_data(data)
            
            # 更新字段
            for key, value in sanitized_data.items():
                setattr(db_obj, key, value)
            
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            db.rollback()
            raise e
    
    def delete(self, db: Session, record_id: int) -> bool:
        """
        删除记录
        
        参数:
            db: 数据库会话
            record_id: 记录ID
            
        返回:
            bool: 删除成功返回True，找不到记录返回False
            
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        try:
            db_obj = self.get(db, record_id)
            if not db_obj:
                return False
            
            db.delete(db_obj)
            db.commit()
            return True
        except SQLAlchemyError as e:
            db.rollback()
            raise e
    
    def query(self, db: Session, filters: Dict[str, Any] = None, 
              sort_by: str = 'id', sort_order: str = 'asc', 
              page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """
        多条件查询
        支持模糊查询、IN查询、比较查询等
        
        参数:
            db: 数据库会话
            filters: 查询条件字典
            sort_by: 排序字段
            sort_order: 排序顺序，'asc'表示升序，'desc'表示降序
            page: 页码
            per_page: 每页记录数
            
        返回:
            Dict[str, Any]: 包含查询结果和总记录数的字典
                            {'items': [model_instances], 'total': total_count}
        """
        query = db.query(self.model)
        
        # 应用过滤条件
        if filters:
            for field, value in filters.items():
                if field.endswith('_like'):
                    # 模糊查询
                    actual_field = field[:-5]
                    if hasattr(self.model, actual_field):
                        query = query.filter(getattr(self.model, actual_field).like(f'%{value}%'))
                elif field.endswith('_in'):
                    # IN查询
                    actual_field = field[:-3]
                    if hasattr(self.model, actual_field) and isinstance(value, list):
                        query = query.filter(getattr(self.model, actual_field).in_(value))
                elif field.endswith('_gt'):
                    # 大于查询
                    actual_field = field[:-3]
                    if hasattr(self.model, actual_field):
                        query = query.filter(getattr(self.model, actual_field) > value)
                elif field.endswith('_lt'):
                    # 小于查询
                    actual_field = field[:-3]
                    if hasattr(self.model, actual_field):
                        query = query.filter(getattr(self.model, actual_field) < value)
                elif field.endswith('_gte'):
                    # 大于等于查询
                    actual_field = field[:-4]
                    if hasattr(self.model, actual_field):
                        query = query.filter(getattr(self.model, actual_field) >= value)
                elif field.endswith('_lte'):
                    # 小于等于查询
                    actual_field = field[:-4]
                    if hasattr(self.model, actual_field):
                        query = query.filter(getattr(self.model, actual_field) <= value)
                else:
                    # 精确查询
                    if hasattr(self.model, field):
                        query = query.filter(getattr(self.model, field) == value)
        
        # 计算总记录数
        total = query.count()
        
        # 排序
        if hasattr(self.model, sort_by):
            if sort_order == 'desc':
                query = query.order_by(getattr(self.model, sort_by).desc())
            else:
                query = query.order_by(getattr(self.model, sort_by).asc())
        
        # 分页
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        
        return {'items': items, 'total': total}
    
    def batch_create(self, db: Session, data_list: List[Dict[str, Any]]) -> List[T]:
        """
        批量创建记录
        
        参数:
            db: 数据库会话
            data_list: 要创建的记录数据列表
            
        返回:
            List[T]: 创建成功的模型实例列表
            
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        try:
            # XSS防护：对输入数据进行过滤
            sanitized_data_list = [self._sanitize_data(data) for data in data_list]
            
            # 创建模型实例
            db_objs = [self.model(**data) for data in sanitized_data_list]
            
            # 批量添加
            db.add_all(db_objs)
            db.commit()
            
            # 刷新实例以获取ID等自动生成的字段
            for obj in db_objs:
                db.refresh(obj)
            
            return db_objs
        except SQLAlchemyError as e:
            db.rollback()
            raise e
    
    def batch_delete(self, db: Session, record_ids: List[int]) -> int:
        """
        批量删除记录
        
        参数:
            db: 数据库会话
            record_ids: 要删除的记录ID列表
            
        返回:
            int: 成功删除的记录数
            
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        try:
            result = db.query(self.model).filter(self.model.id.in_(record_ids)).delete(synchronize_session=False)
            db.commit()
            return result
        except SQLAlchemyError as e:
            db.rollback()
            raise e
    
    def export_to_excel(self, db: Session, filters: Dict[str, Any] = None) -> io.BytesIO:
        """
        导出数据到Excel
        
        参数:
            db: 数据库会话
            filters: 查询条件字典
            
        返回:
            io.BytesIO: 包含Excel数据的字节流
        """
        # 查询数据
        query_result = self.query(db, filters=filters, page=1, per_page=1000000)  # 导出所有数据
        
        # 转换为DataFrame
        data = []
        for item in query_result['items']:
            row = {}
            for col in item.__table__.columns:
                # 获取字段值
                value = getattr(item, col.name)
                # 处理特殊类型
                if hasattr(value, 'isoformat'):  # 处理日期时间类型
                    value = value.isoformat()
                row[col.name] = value
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # 导出到Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=self.model.__tablename__)
        
        output.seek(0)
        return output
    
    def import_from_excel(self, db: Session, file_content: io.BytesIO) -> Dict[str, Any]:
        """
        从Excel导入数据
        
        参数:
            db: 数据库会话
            file_content: 包含Excel数据的字节流
            
        返回:
            Dict[str, Any]: 导入结果统计
                            {'success': 成功导入数量, 'failed': 导入失败数量, 'errors': 错误信息列表}
        """
        success_count = 0
        failed_count = 0
        errors = []
        
        try:
            # 读取Excel文件
            df = pd.read_excel(file_content)
            
            # 转换为字典列表
            data_list = df.to_dict('records')
            
            # 批量导入
            for i, data in enumerate(data_list):
                try:
                    # 移除空值
                    data = {k: v for k, v in data.items() if pd.notna(v)}
                    
                    # 验证必填字段
                    required_fields = [col.name for col in self.model.__table__.columns if not col.nullable and col.name != 'id']
                    for field in required_fields:
                        if field not in data:
                            raise ValueError(f'缺少必填字段: {field}')
                    
                    # XSS防护：对输入数据进行过滤
                    sanitized_data = self._sanitize_data(data)
                    
                    # 创建记录
                    db_obj = self.model(**sanitized_data)
                    db.add(db_obj)
                    success_count += 1
                except Exception as e:
                    failed_count += 1
                    errors.append(f'第{i+1}行导入失败: {str(e)}')
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            errors.append(f'Excel读取失败: {str(e)}')
        
        return {
            'success': success_count,
            'failed': failed_count,
            'errors': errors
        }
    
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        XSS防护：过滤HTML标签
        
        参数:
            data: 原始数据
            
        返回:
            Dict[str, Any]: 过滤后的数据
        """
        # 移除HTML标签的正则表达式
        html_tag_pattern = re.compile(r'<[^>]+>')
        
        return {
            k: html_tag_pattern.sub('', v) if isinstance(v, str) else v
            for k, v in data.items()
        }
    
    def get_statistics(self, db: Session, field: str, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取字段的统计信息
        
        参数:
            db: 数据库会话
            field: 要统计的字段名
            filters: 查询条件字典
            
        返回:
            Dict[str, Any]: 统计结果，包含count、sum、avg、min、max
        """
        # 验证字段是否存在
        if not hasattr(self.model, field):
            return {
                'count': 0,
                'sum': 0,
                'avg': 0,
                'min': 0,
                'max': 0
            }
        
        query = db.query(
            func.count(getattr(self.model, field)).label('count'),
            func.sum(getattr(self.model, field)).label('sum'),
            func.avg(getattr(self.model, field)).label('avg'),
            func.min(getattr(self.model, field)).label('min'),
            func.max(getattr(self.model, field)).label('max')
        )
        
        # 应用过滤条件
        if filters:
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    query = query.filter(getattr(self.model, field_name) == value)
        
        result = query.first()
        
        return {
            'count': result.count or 0,
            'sum': float(result.sum) if result.sum else 0,
            'avg': float(result.avg) if result.avg else 0,
            'min': float(result.min) if result.min else 0,
            'max': float(result.max) if result.max else 0
        }