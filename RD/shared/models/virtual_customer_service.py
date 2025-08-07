from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from shared.database.session import Base
from datetime import datetime

class VirtualCustomerService(Base):
    """虚拟客服表模型"""
    __tablename__ = "virtual_customer_services"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, comment="关联的用户ID")
    name = Column(String(255), nullable=False, comment="客服姓名")
    account = Column(String(255), nullable=False, unique=True, comment="客服账号")
    initial_password = Column(String(255), nullable=False, comment="初始密码")
    level = Column(String(10), nullable=False, default='6', comment="客服级别，固定为6")
    status = Column(String(20), nullable=False, default='active', comment="状态：active-活跃, inactive-停用")
    last_login_time = Column(DateTime, nullable=True, comment="最后登录时间")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    is_deleted = Column(Boolean, nullable=False, default=False, comment="是否删除")

    # 关联关系
    user = relationship("OriginalUser", back_populates="virtual_customer_service")
