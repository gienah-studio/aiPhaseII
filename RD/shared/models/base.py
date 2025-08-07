from datetime import datetime
from sqlalchemy import Column, DateTime

class BaseModel:
    """基础模型类，包含通用字段"""
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True, comment="更新时间")
    # Removing created_by, updated_by, deleted_at, deleted_by as they don't exist in the database 