from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv
import logging

from jose import JWTError, jwt
from fastapi import HTTPException, status
from pydantic import BaseModel

from shared.exceptions import BusinessException
from shared.schemas.common import ResponseSchema

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# JWT配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")  # 从环境变量获取密钥
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 默认24小时

class TokenData(BaseModel):
    """Token数据模型
    
    用于定义JWT token中包含的数据结构
    
    Attributes:
        user_id: 用户ID
        account: 用户账号
        user_type: 用户类型
        organization_id: 组织ID
        enterprise_id: 企业ID
        exp: 过期时间
    """
    user_id: int
    account: str
    user_type: int
    organization_id: Optional[int] = None
    enterprise_id: Optional[int] = None
    exp: datetime

def create_jwt_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT token
    
    Args:
        data: 要编码到token中的数据,必须包含user_id,account,user_type等字段
        expires_delta: token过期时间间隔,如不指定则使用默认值
        
    Returns:
        str: 生成的JWT token
        
    Raises:
        Exception: token创建失败时抛出
    """
    to_encode = data.copy()
    
    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    try:
        # 使用密钥创建JWT token
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        raise Exception(f"Failed to create token: {str(e)}")

def decode_jwt_token(token: str) -> TokenData:
    """解码JWT token
    
    Args:
        token: JWT token字符串
        
    Returns:
        TokenData: 解码后的token数据
        
    Raises:
        BusinessException: token无效或已过期时抛出
    """
    try:
        logger.debug(f"开始解析token: {token}")
        logger.debug(f"使用的SECRET_KEY: {SECRET_KEY}")
        logger.debug(f"使用的ALGORITHM: {ALGORITHM}")
        
        # 解码token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug(f"解码后的payload: {payload}")
        
        # 提取必要字段
        user_id = payload.get("user_id")
        account = payload.get("account")
        user_type = payload.get("user_type")
        exp = payload.get("exp")
        
        logger.debug(f"提取的字段: user_id={user_id}, account={account}, user_type={user_type}, exp={exp}")
        
        # 检查必要字段
        if not all([isinstance(user_id, int), isinstance(account, str), isinstance(user_type, int), isinstance(exp, int)]):
            logger.error("缺少必要字段或字段类型错误")
            raise BusinessException(
                code=401,
                message="无效的认证凭据",
                data=None
            )
        
        # 检查token是否过期
        exp_datetime = datetime.fromtimestamp(exp)
        now = datetime.now()
        logger.debug(f"Token过期时间: {exp_datetime}, 当前时间: {now}")
        
        if exp_datetime < now:
            logger.error("Token已过期")
            raise BusinessException(
                code=401,
                message="登录已过期，请重新登录",
                data="token_expired"
            )
        
        # 创建TokenData对象
        token_data = TokenData(
            user_id=user_id,
            account=account,
            user_type=user_type,
            organization_id=payload.get("organization_id"),
            enterprise_id=payload.get("enterprise_id"),
            exp=exp_datetime
        )
        logger.debug(f"创建的TokenData对象: {token_data}")
        return token_data
        
    except JWTError as e:
        logger.error(f"JWT解析错误: {str(e)}")
        # 检查是否是过期错误
        if "expired" in str(e).lower():
            raise BusinessException(
                code=401,
                message="登录已过期，请重新登录",
                data="token_expired"
            )
        else:
            raise BusinessException(
                code=401,
                message="无效的认证凭据",
                data="token_invalid"
            )
    except Exception as e:
        logger.error(f"其他错误: {str(e)}")
        raise BusinessException(
            code=401,
            message="认证失败，请重新登录",
            data="auth_failed"
        )