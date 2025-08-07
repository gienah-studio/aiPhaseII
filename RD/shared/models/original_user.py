from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.orm import relationship
from shared.database.session import Base
from datetime import datetime

class OriginalUser(Base):
    """原始用户表模型（兼容现有数据库结构）"""
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(255), nullable=False, comment="用户名")
    password = Column(String(255), nullable=False, comment="密码")
    role = Column(String(255), nullable=False, comment="角色")
    lastLoginTime = Column(DateTime, nullable=True, comment="最后登录时间")
    isDeleted = Column(Boolean, default=False, comment="是否删除")

    # 关联关系
    userinfo = relationship("UserInfo", back_populates="user", uselist=False)
    virtual_customer_service = relationship("VirtualCustomerService", back_populates="user", uselist=False)
