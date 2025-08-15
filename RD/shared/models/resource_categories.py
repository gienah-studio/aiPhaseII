from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from shared.database.session import Base
from datetime import datetime

class ResourceCategories(Base):
    """资源库分类表模型"""
    __tablename__ = "resource_categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category_code = Column(String(50), nullable=False, unique=True, comment="分类代码")
    category_name = Column(String(100), nullable=False, comment="分类名称")
    description = Column(Text, comment="分类描述")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")