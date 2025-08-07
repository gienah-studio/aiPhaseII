from sqlalchemy import Column, String, Integer, DateTime, Numeric, Date
from sqlalchemy.orm import relationship
from shared.database.session import Base
from datetime import datetime

class VirtualOrderReports(Base):
    """虚拟订单统计报表模型"""
    __tablename__ = "virtual_order_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_date = Column(Date, nullable=False, comment="报表日期")
    student_id = Column(Integer, nullable=False, comment="学生ID")
    student_name = Column(String(255), nullable=False, comment="学生姓名")
    total_tasks_generated = Column(Integer, default=0, comment="当日生成虚拟任务总数")
    total_tasks_accepted = Column(Integer, default=0, comment="当日接取任务数")
    total_tasks_completed = Column(Integer, default=0, comment="当日完成任务数")
    total_tasks_expired = Column(Integer, default=0, comment="当日过期任务数")
    total_amount_generated = Column(Numeric(10, 2), default=0.00, comment="当日生成任务总金额")
    total_amount_accepted = Column(Numeric(10, 2), default=0.00, comment="当日接取任务总金额")
    total_amount_completed = Column(Numeric(10, 2), default=0.00, comment="当日完成任务总金额")
    total_amount_expired = Column(Numeric(10, 2), default=0.00, comment="当日过期任务总金额")
    remaining_subsidy = Column(Numeric(10, 2), default=0.00, comment="剩余补贴金额")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<VirtualOrderReports(id={self.id}, student_name='{self.student_name}', report_date={self.report_date})>"
