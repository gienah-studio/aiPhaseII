from sqlalchemy import Column, String, Integer, DateTime, Numeric, Text, Boolean
from sqlalchemy.orm import relationship
from shared.database.session import Base
from datetime import datetime

class VirtualOrderPool(Base):
    """虚拟订单资金池模型"""
    __tablename__ = "virtual_order_pool"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, nullable=False, comment="学生ID，关联userinfo表的roleId")
    student_name = Column(String(255), nullable=False, comment="学生姓名")
    total_subsidy = Column(Numeric(10, 2), nullable=False, comment="总补贴金额")
    remaining_amount = Column(Numeric(10, 2), nullable=False, comment="剩余可分配金额")
    allocated_amount = Column(Numeric(10, 2), default=0.00, comment="已分配金额")
    completed_amount = Column(Numeric(10, 2), default=0.00, comment="已完成任务金额")
    consumed_subsidy = Column(Numeric(10, 2), default=0.00, comment="当日实际消耗的补贴金额")
    bonus_pool_completed_amount = Column(Numeric(10, 2), default=0.00, comment="奖金池任务已完成金额")
    bonus_pool_consumed_subsidy = Column(Numeric(10, 2), default=0.00, comment="奖金池任务实际获得的补贴金额")
    status = Column(String(50), default='active', comment="状态：active-活跃, completed-已完成, expired-已过期")
    import_batch = Column(String(100), nullable=True, comment="导入批次号")
    is_deleted = Column(Boolean, default=False, comment="是否已删除")
    deleted_at = Column(DateTime, nullable=True, comment="删除时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    last_allocation_at = Column(DateTime, nullable=True, comment="最后分配时间")

    def __repr__(self):
        return f"<VirtualOrderPool(id={self.id}, student_name='{self.student_name}', total_subsidy={self.total_subsidy})>"
