from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from shared.database.session import Base
from shared.models.base_model import BaseModel
import enum

class UserStatus(enum.Enum):
    """用户状态枚举"""
    pending_approval = "pending_approval"
    active = "active"
    rejected = "rejected"
    suspended = "suspended"

class UserRole(enum.Enum):
    """用户角色枚举"""
    admin = "admin"
    provider = "provider"
    consumer = "consumer"

class User(Base, BaseModel):
    __tablename__ = "users"

    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=True, comment="所属企业ID, NULL表示个体用户")
    account = Column(String(50), unique=True, nullable=False, comment="登录账号")
    name = Column(String(50), nullable=True, comment="用户真实姓名")
    phone = Column(String(20), index=True, comment="手机号")
    email = Column(String(100), unique=True, nullable=True, comment="邮箱")
    password = Column(String(255), nullable=False, comment="加密后的密码")
    avatar = Column(String(255), nullable=True, comment="头像URL")
    role = Column(Enum(UserRole), nullable=False, comment="平台核心角色: admin-管理员, provider-API提供者, consumer-API使用者")
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.pending_approval, comment="账户状态")
    remark = Column(String(255), nullable=True, comment="备注")

    # 添加反向关系，使用字符串引用
    login_logs = relationship("LoginLog", back_populates="user")