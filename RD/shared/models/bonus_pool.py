from sqlalchemy import Column, String, Integer, DateTime, Date, Numeric, Text
from shared.database.session import Base
from datetime import datetime

class BonusPool(Base):
    """奖金池主表"""
    __tablename__ = "bonus_pool"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pool_date = Column(Date, nullable=False, unique=True, comment="奖金池日期")
    carry_forward_amount = Column(Numeric(10, 2), nullable=False, default=0.00, comment="前日结转金额")
    new_expired_amount = Column(Numeric(10, 2), nullable=False, default=0.00, comment="当日新增过期金额（来自普通虚拟任务）")
    total_amount = Column(Numeric(10, 2), nullable=False, default=0.00, comment="奖金池总金额")
    generated_amount = Column(Numeric(10, 2), nullable=False, default=0.00, comment="已生成任务金额")
    completed_amount = Column(Numeric(10, 2), nullable=False, default=0.00, comment="已完成金额")
    remaining_amount = Column(Numeric(10, 2), nullable=False, default=0.00, comment="剩余金额")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<BonusPool(id={self.id}, pool_date={self.pool_date}, total_amount={self.total_amount})>"