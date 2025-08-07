from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from shared.models.user import User

from shared.models.login_log import LoginLog
from shared.utils.security import verify_password
from shared.exceptions import BusinessException, ErrorCode

def authenticate_user(db: Session, username: str, password: str) -> User:
    """验证用户"""
    user = db.query(User).filter(User.account == username).first()
    print(user, username, password)
    if not user:
        raise BusinessException(
            code=ErrorCode.INVALID_PASSWORD,
            message="账号或密码错误"
        )
    if not verify_password(password, user.password):
        raise BusinessException(
            code=ErrorCode.INVALID_PASSWORD,
            message="账号或密码错误"
        )
    if user.status == 0:
        raise BusinessException(
            code=ErrorCode.USER_DISABLED,
            message="账号已被禁用"
        )
        
    # 注：在认证模板中，我们简化了企业检查逻辑
    # 实际项目中可以根据需要添加企业状态检查
            
    return user

def log_user_login(db: Session, user_id: int, ip: str) -> None:
    """记录用户登录"""
    login_log = LoginLog(
        user_id=user_id,
        login_time=datetime.now(),
        ip=ip
    )
    db.add(login_log)
    db.commit() 