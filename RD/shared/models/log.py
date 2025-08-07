from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from shared.database.session import Base
from shared.models.base_model import BaseModel
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from shared.database import Base
import datetime

class Log(Base, BaseModel):
    __tablename__ = "logs"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="用户ID")
    action = Column(String(100), nullable=False, comment="操作类型")
    resource = Column(String(100), nullable=False, comment="资源类型")
    resource_id = Column(Integer, nullable=True, comment="资源ID")
    details = Column(Text, nullable=True, comment="详细信息")
    ip_address = Column(String(50), nullable=True, comment="IP地址")
    user_agent = Column(String(255), nullable=True, comment="用户代理")
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False, comment="所属组织ID")

    # 关系
    user = relationship("User", back_populates="logs")
class UserLoginLog(Base):
    __tablename__ = "user_login_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    login_time = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String)
    user_agent = Column(String)
    status = Column(String)  # success/failed
    
    class Config:
        orm_mode = True