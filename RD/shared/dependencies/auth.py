# shared/dependencies/auth.py
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import ValidationError
from sqlalchemy.orm import Session

from shared.exceptions import BusinessException
from shared.models.user import User
from shared.models.original_user import OriginalUser
from shared.config import settings
from shared.database.session import get_db
from shared.schemas.common import ResponseSchema
from shared.utils.jwt import decode_jwt_token

# OAuth2 配置
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

class CustomHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        try:
            return await super().__call__(request)
        except HTTPException:
            # raise HTTPException(
            #     status_code=status.HTTP_200_OK,
            #     detail=ResponseSchema(
            #         code=401,
            #         message="无法验证凭据",
            #         data=None
            #     ).dict()
            # )
            raise BusinessException(
                code=401,
                message="无法验证凭据",
                data=None
            )

security = CustomHTTPBearer()

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db)
) -> User:
    """
    从JWT令牌中获取当前用户
    """
    try:
        print(f"[AUTH] 开始解析Token: {token[:20]}...")
        # 解码JWT令牌
        token_data = decode_jwt_token(token)
        print(f"[AUTH] 令牌解析成功，用户ID: {token_data.user_id}")
        
        # 从数据库获取用户
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if user is None:
            print(f"[AUTH] 用户不存在: {token_data.user_id}")
            raise BusinessException(
                code=401,
                message="用户不存在，请重新登录",
                data={"error_type": "user_not_found"}
            )
            
        # 检查用户状态
        if user.status != 1:  # 1表示启用状态
            print(f"[AUTH] 用户已被禁用: {user.id}, 状态: {user.status}")
            raise BusinessException(
                code=401,
                message="账户已被禁用，请联系管理员",
                data={"error_type": "user_disabled"}
            )
            
        # 将token添加到用户对象，方便后续使用
        # 这种方式不会影响数据库中的用户对象
        setattr(user, 'token', token)
        print(f"[AUTH] 用户{user.id}认证成功，已将token添加到user对象")
        print(f"[AUTH] 检查token是否成功附加: {hasattr(user, 'token')}")
            
        return user
        
    except Exception as e:
        print(f"[AUTH] 认证失败: {str(e)}")
        raise BusinessException(
            code=401,
            message="无法验证凭据",
            data=None
        )

async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> OriginalUser:
    """获取当前活跃用户

    Args:
        credentials: HTTP认证凭据
        db: 数据库会话

    Returns:
        OriginalUser: 当前用户对象

    Raises:
        HTTPException: 认证失败时抛出
    """
    try:
        # 解码token
        token = credentials.credentials
        token_data = decode_jwt_token(token)

        # 从数据库获取用户（使用OriginalUser表）
        user = db.query(OriginalUser).filter(OriginalUser.id == token_data.user_id).first()
        if user is None:
            raise BusinessException(
                code=401,
                message="用户不存在",
                data=None
            )

        # 检查用户是否被删除
        if user.isDeleted:
            raise BusinessException(
                code=401,
                message="用户已被删除",
                data=None
            )

        # 将token添加到用户对象，方便后续使用
        # 这种方式不会影响数据库中的用户对象
        setattr(user, 'token', token)

        return user
        
    except Exception as e:
        # raise HTTPException(
        #     status_code=status.HTTP_200_OK,
        #     detail=ResponseSchema(
        #         code=401,
        #         message="无法验证凭据",
        #         data=None
        #     ).dict()
        # )
        raise BusinessException(
            code=401,
            message="无法验证凭据",
            data=None
        )
