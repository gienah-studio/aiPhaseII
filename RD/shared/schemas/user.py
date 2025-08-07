from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
import re
from pydantic import validator

# 基础用户模式
class UserBase(BaseModel):
    enterprise_id: Optional[int] = None
    account: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar: Optional[str] = None
    role: str  # admin, provider, consumer
    status: str  # pending_approval, active, rejected, suspended
    remark: Optional[str] = None



# 更新用户时的模式
class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    remark: Optional[str] = None
    password: Optional[str] = None

# 数据库中的用户模式
class UserInDBBase(UserBase):
    id: int
    create_time: datetime
    update_time: Optional[datetime] = None

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }

# API响应中的用户模式
class User(UserInDBBase):
    pass

# 数据库中包含密码的用户模式
class UserInDB(UserInDBBase):
    password: str

class UserSchema(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }

class UserDetailSchema(UserSchema):
    # 可以添加更多详细信息字段
    last_login: Optional[datetime] = None

class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None

class DepartmentCreate(DepartmentBase):
    enterprise_id: int

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None

class DepartmentSchema(DepartmentBase):
    id: int
    enterprise_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }

class PositionLevelCreate(BaseModel):
    name: str
    level: int
    parent_level: Optional[int] = None
    timeout_hours: Optional[int] = None
    enterprise_id: int = Field(..., description="所属企业ID")

class PositionLevelSchema(BaseModel):
    id: int
    name: str
    level: int
    parent_level: Optional[int] = None
    timeout_hours: Optional[int] = None
    enterprise_id: int = Field(..., description="所属企业ID")

    class Config:
        orm_mode = True

class PositionLevelUpdate(BaseModel):
    name: Optional[str] = None
    level: Optional[int] = None
    parent_level: Optional[int] = None
    timeout_hours: Optional[int] = None
    enterprise_id: Optional[int] = Field(None, description="所属企业ID")

    class Config:
        orm_mode = True

class AdminUserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

    class Config:
        orm_mode = True

class OperationInfo(BaseModel):
    """操作权限信息"""
    id: int = Field(..., description="操作ID")
    name: str = Field(..., description="操作名称")
    code: str = Field(..., description="操作代码")
    checked: bool = Field(..., description="是否拥有该权限")

class ModulePermissionInfo(BaseModel):
    """模块权限信息"""
    moduleId: int = Field(..., description="模块ID", alias="module_id")
    moduleName: str = Field(..., description="模块名称", alias="module_name")
    code: str = Field(..., description="模块代码")
    type: int = Field(..., description="类型(0:目录,1:菜单)")
    parentId: Optional[int] = Field(None, description="父模块ID", alias="parent_id")
    path: Optional[str] = Field(None, description="前端路由路径")
    component: Optional[str] = Field(None, description="前端组件路径")
    redirect: Optional[str] = Field(None, description="重定向路径")
    icon: Optional[str] = Field(None, description="图标")
    hidden: Optional[bool] = Field(False, description="是否隐藏(false:显示,true:隐藏)")
    keepAlive: Optional[bool] = Field(False, description="是否缓存(false:不缓存,true:缓存)", alias="keep_alive")
    meta: Optional[Dict[str, Any]] = Field(None, description="路由元数据")
    operations: List[OperationInfo] = Field(default=[], description="操作权限列表")
    children: List['ModulePermissionInfo'] = Field(default=[], description="子模块列表")

    class Config:
        allow_population_by_field_name = True

class UserResponse(BaseModel):
    """用户响应模型"""
    id: int = Field(..., description="用户ID")
    enterpriseId: Optional[int] = Field(None, description="企业ID", alias="enterprise_id")
    account: str = Field(..., description="登录账号")
    name: Optional[str] = Field(None, description="用户真实姓名")
    phone: Optional[str] = Field(None, description="手机号")
    email: Optional[str] = Field(None, description="邮箱")
    avatar: Optional[str] = Field(None, description="头像URL")
    role: str = Field(..., description="平台角色: admin-管理员, provider-API提供者, consumer-API使用者")
    status: str = Field(..., description="账户状态: pending_approval-待审核, active-启用, rejected-拒绝, suspended-禁用")
    remark: Optional[str] = Field(None, description="备注")
    positionName: Optional[str] = Field(None, description="职位名称", alias="position_name")
    enterpriseId: Optional[int] = Field(None, description="所属企业ID", alias="enterprise_id")
    enterpriseName: Optional[str] = Field(None, description="企业名称", alias="enterprise_name")
    enterpriseRegionCode: Optional[str] = Field(None, description="企业所在地区编码", alias="enterprise_region_code")
    enterpriseRegionName: Optional[str] = Field(None, description="企业所在地区名称", alias="enterprise_region_name")
    enterpriseAddress: Optional[str] = Field(None, description="企业详细地址", alias="enterprise_address")
    createdAt: datetime = Field(..., description="创建时间", alias="create_time")
    updatedAt: Optional[datetime] = Field(None, description="更新时间", alias="update_time")
    permissions: List[ModulePermissionInfo] = Field(default=[], description="用户权限列表")
    roles: List[Dict[str, Any]] = Field(default=[], description="用户角色列表")

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

class CreateEmployeeRequest(BaseModel):
    """创建员工请求模型"""
    name: str = Field(..., description="员工姓名", max_length=50)
    departmentId: int = Field(..., description="部门ID，如果是根节点则为企业ID")
    phone: str = Field(..., description="手机号，将作为账号使用", max_length=20)
    positionName: str = Field(..., description="职级名称", max_length=50, alias="position_level")
    status: int = Field(1, description="状态(1:启用,2:禁用)")
    password: str = Field(..., description="初始密码", min_length=6, max_length=20)

    @validator('phone')
    def validate_phone(cls, v):
        # 简单的手机号格式验证
        if not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('无效的手机号格式')
        return v

    @validator('status')
    def validate_status(cls, v):
        if v not in [1, 2]:
            raise ValueError('状态只能是1(启用)或2(禁用)')
        return v

    class Config:
        allow_population_by_field_name = True

class UpdateEmployeeRequest(BaseModel):
    id: int = Field(..., description="员工ID", gt=0)
    name: str = Field(..., description="员工姓名", min_length=1, max_length=50)
    phone: str = Field(..., description="手机号", regex="^1[3-9]\d{9}$")
    departmentId: int = Field(..., description="部门ID", gt=0)
    positionName: str = Field(..., description="职级名称", min_length=1, max_length=50, alias="position_level")
    status: int = Field(..., description="状态(1:启用,2:禁用)", ge=1, le=2)  # 添加status字段
    remark: Optional[str] = Field(None, description="备注")

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "id": 1,
                "name": "张三",
                "phone": "13800138000",
                "departmentId": 1,
                "positionName": "经理",
                "status": 1,  # 1:启用, 2:禁用
                "remark": "备注"
            }
        }