from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from shared.database.session import Base

class LoginLog(Base):
    """登录日志模型"""
    __tablename__ = "login_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    login_time = Column(DateTime, nullable=False, default=datetime.now)
    ip = Column(String(50), nullable=False)

    # 关联用户表
    user = relationship("User", back_populates="login_logs")