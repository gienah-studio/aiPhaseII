from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Numeric, Date
from sqlalchemy.orm import relationship
from shared.database.session import Base
from datetime import datetime

class Tasks(Base):
    """任务表模型"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    summary = Column(String(255), nullable=True, comment="简介")
    requirement = Column(Text, nullable=True, comment="需求")
    reference_images = Column(Text, nullable=True, comment="参考图")
    source = Column(String(255), nullable=True, comment="来源")
    order_number = Column(String(255), nullable=True, comment="订单号")
    commission = Column(Numeric(10, 2), nullable=True, comment="佣金")
    commission_unit = Column(String(255), nullable=True, comment="佣金单位")
    end_date = Column(DateTime, nullable=True, comment="截止时间")
    delivery_date = Column(DateTime, nullable=True, comment="交稿时间")
    status = Column(String(255), nullable=True, comment="状态")
    task_style = Column(String(255), nullable=True, comment="风格")
    task_type = Column(String(255), nullable=True, comment="类型")
    created_at = Column(DateTime, nullable=True, comment="创建时间")
    updated_at = Column(DateTime, nullable=True, comment="更新时间")
    orders_number = Column(Integer, nullable=True, comment="接单总人数")
    order_received_number = Column(Integer, nullable=True, comment="已接单人数")
    founder = Column(String(255), nullable=True, comment="创建人")
    founder_id = Column(Integer, nullable=True, comment="创建id")
    message = Column(String(255), nullable=True, comment="终止任务原因")
    task_level = Column(String(255), nullable=True, comment="任务级别")
    accepted_by = Column(String(255), nullable=True, comment="保存接取任务的用户 ID")
    payment_status = Column(String(255), nullable=True, comment="支付状态: 0-待支付, 1-已支付, 2-待结算, 3-可结算, 4-已结算, 5-终止")
    accepted_name = Column(Text, nullable=True, comment="保存接取任务的用户名称")
    is_renew = Column(String(255), nullable=True, comment="任务更新，0未更新， 1更新")
    is_virtual = Column(Boolean, default=False, comment="是否为虚拟任务：0-普通任务，1-虚拟任务")
    target_student_id = Column(Integer, nullable=True, comment="目标学生ID，虚拟任务专用，限制只有指定学生可以接取")
    is_bonus_pool = Column(Boolean, default=False, comment="是否为奖金池任务：0-否，1-是")
    bonus_pool_date = Column(Date, nullable=True, comment="奖金池归属日期")
    value_recycled = Column(Boolean, default=False, comment="价值是否已回收（仅虚拟任务使用）")
    recycled_at = Column(DateTime, nullable=True, comment="价值回收时间（仅虚拟任务使用）")

    def __repr__(self):
        return f"<Tasks(id={self.id}, summary='{self.summary}', is_virtual={self.is_virtual}, is_bonus_pool={self.is_bonus_pool})>"
