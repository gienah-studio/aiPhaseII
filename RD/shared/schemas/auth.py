from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None

class PhoneVerificationRequest(BaseModel):
    phone: str
    verification_code: str

class PasswordResetRequest(BaseModel):
    email: EmailStr
    verification_code: str
    new_password: str



class UserLogin(BaseModel):
    """用户登录请求模型"""
    account: str
    password: str

class TokenResponse(BaseModel):
    """Token响应模型"""
    access_token: str = Field(..., alias="accessToken")
    token_type: str = Field(default="bearer", alias="tokenType")
    user_id: int = Field(..., alias="userId")
    account: str
    name: Optional[str] = None
    role: str
    status: str
    enterprise_id: Optional[int] = Field(None, alias="enterpriseId")
    phone: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None

    class Config:
        """配置模型"""
        orm_mode = True  # 允许从ORM模型创建
        allow_population_by_field_name = True
        alias_generator = lambda field_name: ''.join(word.capitalize() if i else word for i, word in enumerate(field_name.split('_')))

class SimpleTokenResponse(BaseModel):
    access_token: str = Field(..., alias="accessToken")

    class Config:
        allow_population_by_field_name = True
        alias_generator = lambda field_name: ''.join(word.capitalize() if i else word for i, word in enumerate(field_name.split('_')))