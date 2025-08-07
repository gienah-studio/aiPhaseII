from fastapi import APIRouter, Body, Depends, Request, File, UploadFile, status, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

import re
import random

from sqlalchemy import text

from shared.config import settings
from shared.database.session import get_db
from shared.models.user import User
from shared.models.original_user import OriginalUser
from shared.schemas.auth import SimpleTokenResponse, TokenResponse
from shared.schemas.common import ResponseSchema
from shared.dependencies.auth import get_current_active_user
from shared.schemas.user import UserResponse
from shared.exceptions import BusinessException
from ..api.api_docs import AuthApiDocs
from ..schemas.auth_schemas import (
    LoginRequest,
    FileUploadResponse,
    ChangePasswordRequest,
    LogoutRequest,
    UpdateUserInfoRequest,
    ResetPasswordRequest,
    StudentIncomeStatsResponse
)

from ..service.auth_service import AuthService

router = APIRouter()



@router.post(
    "/login",
    response_model=ResponseSchema[SimpleTokenResponse],
    **AuthApiDocs.LOGIN
)
def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
) -> ResponseSchema[SimpleTokenResponse]:
    """用户登录"""
    auth_service = AuthService(db)
    result = auth_service.login(
        username=login_data.username,
        password=login_data.password,
        client_ip=request.client.host
    )
    
    return ResponseSchema[SimpleTokenResponse](
        code=200,
        data=SimpleTokenResponse(**result),
        message="登录成功"
    )









@router.post(
    "/logout",
    response_model=ResponseSchema,
    **AuthApiDocs.LOGOUT
)
async def logout(
    request: Request,
    _: LogoutRequest = Body({}),  # 不需要参数，但保持一致性
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """退出登录"""
    # 从授权头中提取token
    auth_header = request.headers.get("Authorization", "")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        auth_service = AuthService(db)
        auth_service.logout(current_user.id, token)
    
    return ResponseSchema(
        code=200,
        message="退出登录成功"
    )

@router.get(
    "/profile",
    response_model=ResponseSchema[UserResponse],
    **AuthApiDocs.GET_PROFILE
)
def get_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ResponseSchema[UserResponse]:
    """获取当前登录用户的个人信息及权限"""
    auth_service = AuthService(db)
    result = auth_service.get_user_profile(current_user.id)
    
    return ResponseSchema[UserResponse](
        code=200,
        message="获取成功",
        data=UserResponse(**result)
    )

@router.post(
    "/upload",
    response_model=ResponseSchema[FileUploadResponse],
    **AuthApiDocs.UPLOAD_FILE
)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ResponseSchema[FileUploadResponse]:
    """上传文件"""
    auth_service = AuthService(db)
    result = await auth_service.upload_file(file, current_user.id)
    
    return ResponseSchema[FileUploadResponse](
        code=200,
        message="上传成功",
        data=FileUploadResponse(**result)
    )

@router.post(
    "/changePassword",
    response_model=ResponseSchema,
    **AuthApiDocs.CHANGE_PASSWORD
)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """使用原密码修改密码"""
    auth_service = AuthService(db)
    auth_service.change_password(
        user_id=current_user.id,
        old_password=request.old_password,
        new_password=request.new_password,
        confirm_password=request.new_password_confirm
    )

    return ResponseSchema(
        code=200,
        message="密码修改成功"
    )

@router.post(
    "/resetPassword",
    response_model=ResponseSchema,
    summary="重置密码",
    description="重置用户密码为123456"
)
def reset_password(
    request: ResetPasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """重置密码"""
    auth_service = AuthService(db)
    auth_service.reset_password(user_id=request.user_id)

    return ResponseSchema(
        code=200,
        message="密码重置成功"
    )

@router.put(
    "/profile",
    response_model=ResponseSchema[UserResponse],
    **AuthApiDocs.UPDATE_USER_INFO
)
def update_user_info(
    request: UpdateUserInfoRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新个人信息"""
    auth_service = AuthService(db)
    result = auth_service.update_user_info(
        user_id=current_user.id,
        user_data=request.dict(exclude_unset=True)
    )
    
    return ResponseSchema[UserResponse](
        code=200,
        message="更新成功",
        data=UserResponse(**result)
    )

@router.get(
    "/student/daily-income-stats",
    response_model=ResponseSchema[dict],
    summary="获取所有学员每日收入统计",
    description="获取所有学员前一天的收入统计列表（管理员功能）"
)
async def get_all_students_daily_income_stats(
    page: int = 1,
    size: int = 10,
    current_user: OriginalUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取所有学员每日收入统计"""
    try:
        auth_service = AuthService(db)
        result = auth_service.get_all_students_income_stats(page=page, size=size)

        return ResponseSchema[dict](
            code=200,
            message="获取成功",
            data=result
        )
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取学员收入统计失败: {str(e)}")