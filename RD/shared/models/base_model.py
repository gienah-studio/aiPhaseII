from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from shared.database.session import Base

class BaseModel:
    """所有模型的基类，提供通用字段"""
    id = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime, default=func.now(), nullable=False)
    update_time = Column(DateTime, onupdate=func.now())
