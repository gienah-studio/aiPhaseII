from sqlalchemy import Column, String, Integer, DateTime, Text
from shared.database.session import Base
from datetime import datetime

class StudentTask(Base):
    """学生任务提交表模型"""
    __tablename__ = "studenttask"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    content = Column(Text, nullable=True, comment="提交的图片地址")
    name = Column(String(255), nullable=True, comment="提交用户的姓名")
    user_id = Column(Integer, nullable=True, comment="用户ID")
    task_id = Column(Integer, nullable=True, comment="任务Id")
    message = Column(String(255), nullable=True, comment="反馈信息")
    feedback_img = Column(Text, nullable=True, comment="反馈图片")
    status = Column(String(255), nullable=True, comment="判断当前任务状态")
    is_read = Column(Integer, nullable=True, comment="客服反馈后判断学员已读未读，0是未读，1是已读")
    created_at = Column(DateTime, nullable=True, comment="反馈时间")
    is_new = Column(Integer, nullable=True, comment="是否是最新的，0是新的，1是旧的")
    creation_time = Column(String(255), nullable=True, comment="创建时间")
    feedback_msg = Column(String(255), nullable=True, comment="反馈信息内容")

    def __repr__(self):
        return f"<StudentTask(id={self.id}, task_id={self.task_id}, user_id={self.user_id}, status='{self.status}')>"
