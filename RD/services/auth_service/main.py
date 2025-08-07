from datetime import datetime, timedelta
from typing import Any, List, Optional
import os
import shutil
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status, File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import random
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware

# 添加shared目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.config import settings
from shared.database.session import get_db
from shared.models.user import User
from shared.models.log import UserLoginLog
from shared.schemas.user import UserSchema, UserUpdate, UserDetailSchema
from shared.schemas.auth import TokenSchema, PhoneVerificationRequest, PasswordResetRequest, UserLogin, TokenResponse
from shared.utils.security import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    decode_access_token
)
from shared.utils.redis_util import RedisUtil
from shared.exceptions import BusinessException, business_exception_handler, ErrorCode
from .routers import auth  # 使用相对导入

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Auth Service",
    description="认证服务",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    openapi_tags=[{"name": "Auth", "description": "认证相关接口"}]
)

# 首先添加异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求参数验证错误"""
    return JSONResponse(
        status_code=200,
        content={
            "code": ErrorCode.PARAM_ERROR,
            "message": "参数错误：" + str(exc.errors()),
            "data": None
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理HTTP异常"""
    return JSONResponse(
        status_code=200,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "data": None
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """处理所有未处理的异常"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=200,
        content={
            "code": ErrorCode.SERVER_ERROR,
            "message": "服务器内部错误",
            "data": None
        }
    )

# 然后添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加异常处理中间件
app.add_middleware(ExceptionMiddleware, handlers=app.exception_handlers)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app.include_router(auth.router, tags=["Auth"])

# 配置文件上传目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 挂载静态文件目录
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 允许的文件类型
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf', '.doc', '.docx', '.xls', '.xlsx'}

def validate_file_extension(filename: str) -> bool:
    """验证文件扩展名是否允许"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # 添加所有需要的 schemas
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}

    openapi_schema["components"]["schemas"].update({
        "UserLogin": UserLogin.schema(),
        "TokenResponse": TokenResponse.schema(),
        "HTTPValidationError": {
            "title": "HTTPValidationError",
            "type": "object",
            "properties": {
                "detail": {
                    "title": "Detail",
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/ValidationError"}
                }
            }
        },
        "ValidationError": {
            "title": "ValidationError",
            "type": "object",
            "properties": {
                "loc": {
                    "title": "Location",
                    "type": "array",
                    "items": {"type": "string"}
                },
                "msg": {"title": "Message", "type": "string"},
                "type": {"title": "Error Type", "type": "string"}
            },
            "required": ["loc", "msg", "type"]
        },
        "Body_login_login_post": UserLogin.schema()  # 添加这个schema
    })
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/health")
def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "auth"}

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """验证用户凭据"""
    user = db.query(User).filter(User.account == username).first()
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user

def log_user_login(db: Session, user_id: int, ip_address: str):
    """记录用户登录日志"""
    log = UserLoginLog(
        user_id=user_id,
        login_time=datetime.utcnow(),
        ip_address=ip_address,
        status="success"
    )
    db.add(log)
    db.commit()

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise BusinessException(
                code=ErrorCode.UNAUTHORIZED,
                message="无效的身份凭证"
            )
    except JWTError:
        raise BusinessException(
            code=ErrorCode.UNAUTHORIZED,
            message="无效的身份凭证"
        )
    
    user = db.query(User).filter(User.account == username).first()
    if user is None:
        raise BusinessException(
            code=ErrorCode.USER_NOT_FOUND,
            message="用户不存在"
        )
    
    if not user.is_active:
        raise BusinessException(
            code=ErrorCode.USER_DISABLED,
            message="用户已被禁用"
        )
    
    return user







@app.get("/users/me", response_model=UserSchema, tags=["用户"])
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取当前登录用户信息
    """
    return current_user

@app.put("/users/me", response_model=UserSchema, tags=["用户"])
async def update_current_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    更新当前用户信息
    """
    # 如果更新密码，需要验证旧密码
    if user_update.password and user_update.old_password:
        if not verify_password(user_update.old_password, current_user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="旧密码不正确"
            )
        user_update.password = get_password_hash(user_update.password)
    elif user_update.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="更新密码时必须提供旧密码"
        )
    
    # 更新用户信息
    update_data = user_update.dict(exclude_unset=True, exclude={"old_password"})
    for key, value in update_data.items():
        setattr(current_user, key, value)
    
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@app.get("/verify-token", tags=["认证"])
async def verify_token(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    验证令牌有效性并返回用户基本信息
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "account": current_user.account,
        "name": current_user.name,
        "user_type": current_user.user_type
    }

@app.get("/test")
async def test():
    return {"message": "Auth service is working"}

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

