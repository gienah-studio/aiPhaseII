from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from decimal import Decimal

# 登录请求模型
class LoginRequest(BaseModel):
    username: str = Field(..., description="账号")
    password: str = Field(..., description="密码")

# 学员收入统计响应模型
class StudentIncomeStatsResponse(BaseModel):
    yesterday_income: Decimal = Field(..., description="昨日总收入")
    yesterday_completed_orders: int = Field(..., description="昨日完成订单数")
    commission_rate: str = Field(..., description="分佣比例")
    actual_income: Decimal = Field(..., description="实际到手金额")
    student_id: int = Field(..., description="学员ID")
    student_name: str = Field(..., description="学员姓名")
    stat_date: str = Field(..., description="统计日期")

# 文件上传响应模型
class FileUploadResponse(BaseModel):
    url: str = Field(..., description="文件访问URL")
    filename: str = Field(..., description="原始文件名")
    content_type: str = Field(..., description="文件类型")

    class Config:
        allow_population_by_field_name = True

# 修改密码请求模型（使用原密码）
class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="原密码", alias="oldPassword")
    new_password: str = Field(..., min_length=6, max_length=16, description="新密码", alias="newPassword")
    new_password_confirm: str = Field(..., description="确认新密码", alias="newPasswordConfirm")

    class Config:
        allow_population_by_field_name = True
        alias_generator = lambda field_name: ''.join(word.capitalize() if i else word for i, word in enumerate(field_name.split('_')))

# 退出登录请求模型（无需参数）
class LogoutRequest(BaseModel):
    pass

# 更新用户信息请求模型
class UpdateUserInfoRequest(BaseModel):
    name: Optional[str] = Field(None, description="用户姓名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    avatar: Optional[str] = Field(None, description="头像URL")

    class Config:
        allow_population_by_field_name = True
        alias_generator = lambda field_name: ''.join(word.capitalize() if i else word for i, word in enumerate(field_name.split('_')))

# 重置密码请求模型
class ResetPasswordRequest(BaseModel):
    user_id: int = Field(..., description="用户ID")
