from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from shared.models.user import User
from shared.database import get_db
from sqlalchemy.orm import Session
import logging

from shared.config import settings
from shared.schemas.token import TokenPayload

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 配置密码上下文
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # 设置bcrypt加密轮数
    bcrypt__ident="2b",  # 显式指定bcrypt版本标识符
    bcrypt__min_rounds=12,  # 最小轮数
    bcrypt__max_rounds=12,  # 最大轮数
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        logger.debug(f"Verifying password - Plain password length: {len(plain_password)}")
        logger.debug(f"Hashed password: {hashed_password}")
        
        # 生成测试哈希，看看格式是否一致
        test_hash = pwd_context.hash(plain_password)
        logger.debug(f"Test hash for same password: {test_hash}")
        
        # 验证密码
        result = pwd_context.verify(plain_password, hashed_password)
        logger.debug(f"Password verification result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in password verification: {str(e)}")
        return False

def get_password_hash(password: str) -> str:
    """获取密码哈希值"""
    try:
        hashed = pwd_context.hash(password)
        logger.debug(f"Generated hash for new password: {hashed}")
        return hashed
    except Exception as e:
        logger.error(f"Error generating password hash: {str(e)}")
        raise

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.account == username).first()
    if user is None:
        raise credentials_exception
    return user

def decode_access_token(token: str) -> Optional[TokenPayload]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(
            user_id=payload.get("user_id"),
            account=payload.get("account"),
            user_type=payload.get("user_type"),
            organization_id=payload.get("organization_id"),
            enterprise_id=payload.get("enterprise_id"),
            exp=payload.get("exp")
        )
        
        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            return None
            
        return token_data
    except JWTError:
        return None
