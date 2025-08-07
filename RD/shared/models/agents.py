from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from shared.database.session import Base
from datetime import datetime

class Agents(Base):
    """代理表模型"""
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agent_rebate = Column(String(255), nullable=True, comment="返佣比例")
    student_commission = Column(String(255), nullable=True, comment="学员佣金")
    rebate = Column(String(255), nullable=True, comment="返佣")
    status = Column(String(255), nullable=True, comment="状态: 0-待审核, 1-正常, 2-禁用")
    approvalsNumber = Column(Integer, nullable=False, default=0, comment="审批数量")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    direct_students_count = Column(Integer, nullable=True, comment="直接学员数量")
    is_read = Column(Integer, nullable=False, default=0, comment="是否已读")
    isDeleted = Column(Boolean, default=False, comment="是否删除")

    # 关联关系
    userinfos = relationship("UserInfo", back_populates="agent")
