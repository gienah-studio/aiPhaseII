"""
基础仓库类，提供通用的数据库操作方法
"""
from typing import TypeVar, Type, List, Optional, Dict, Any, Generic, Tuple
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """基础仓库类，提供通用的数据库操作方法"""
    
    def __init__(self, session: AsyncSession):
        """
        初始化仓库
        
        参数:
            session: 异步SQLAlchemy会话
        """
        self.session = session
        
    async def get_by_id(self, model_class: Type[T], id_value: int) -> Optional[T]:
        """
        通过ID获取实体
        
        参数:
            model_class: 模型类
            id_value: ID值
            
        返回:
            查询到的实体，如果不存在则返回None
        """
        query = select(model_class).where(model_class.id == id_value)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_field(self, model_class: Type[T], field: str, value: Any) -> Optional[T]:
        """
        通过字段获取实体
        
        参数:
            model_class: 模型类
            field: 字段名
            value: 字段值
            
        返回:
            查询到的实体，如果不存在则返回None
        """
        query = select(model_class).where(getattr(model_class, field) == value)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(self, model_class: Type[T]) -> List[T]:
        """
        获取所有实体
        
        参数:
            model_class: 模型类
            
        返回:
            实体列表
        """
        query = select(model_class)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def create(self, entity: T) -> T:
        """
        创建实体
        
        参数:
            entity: 实体对象
            
        返回:
            创建的实体
        """
        self.session.add(entity)
        await self.session.flush()
        return entity
    
    async def update(self, entity: T) -> T:
        """
        更新实体
        
        参数:
            entity: 实体对象
            
        返回:
            更新后的实体
        """
        self.session.add(entity)
        await self.session.flush()
        return entity
    
    async def delete(self, entity: T) -> None:
        """
        删除实体
        
        参数:
            entity: 实体对象
        """
        await self.session.delete(entity)
        await self.session.flush()
    
    async def delete_by_id(self, model_class: Type[T], id_value: int) -> None:
        """
        通过ID删除实体
        
        参数:
            model_class: 模型类
            id_value: ID值
        """
        entity = await self.get_by_id(model_class, id_value)
        if entity:
            await self.delete(entity)
    
    async def search(
        self, 
        model_class: Type[T], 
        filters: Dict[str, Any], 
        page: int = 1, 
        page_size: int = 10,
        order_by: str = None,
        desc_order: bool = True
    ) -> Tuple[List[T], int]:
        """
        通用搜索方法，支持过滤、分页和排序
        
        参数:
            model_class: 模型类
            filters: 过滤条件字典
            page: 页码
            page_size: 每页大小
            order_by: 排序字段
            desc_order: 是否降序排序
            
        返回:
            实体列表和总数
        """
        query = select(model_class)
        
        # 应用过滤条件
        conditions = []
        for key, value in filters.items():
            if hasattr(model_class, key) and value is not None:
                if isinstance(value, str) and '%' in value:
                    conditions.append(getattr(model_class, key).like(value))
                elif isinstance(value, list):
                    conditions.append(getattr(model_class, key).in_(value))
                else:
                    conditions.append(getattr(model_class, key) == value)
                
        if conditions:
            query = query.where(and_(*conditions))
        
        # 应用排序
        if order_by and hasattr(model_class, order_by):
            if desc_order:
                query = query.order_by(desc(getattr(model_class, order_by)))
            else:
                query = query.order_by(getattr(model_class, order_by))
        
        # 执行总数查询
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)
        
        # 应用分页
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # 执行查询
        result = await self.session.execute(query)
        entities = result.scalars().all()
        
        return entities, total 