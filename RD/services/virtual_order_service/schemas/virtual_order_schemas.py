from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, date
from decimal import Decimal

# 基础响应模型
class BaseResponse(BaseModel):
    code: int = 200
    message: str = "成功"
    data: Optional[dict] = None

# 学生补贴导入请求
class StudentSubsidyImportRequest(BaseModel):
    """学生补贴导入请求"""
    pass  # 文件上传通过FastAPI的UploadFile处理

# 学生补贴导入响应
class StudentSubsidyImportResponse(BaseModel):
    """学生补贴导入响应"""
    import_batch: str = Field(..., description="导入批次号")
    total_students: int = Field(..., description="导入学生总数")
    total_subsidy: Decimal = Field(..., description="总补贴金额")
    generated_tasks: int = Field(..., description="生成的虚拟任务数量")

# 专用客服导入响应
class CustomerServiceImportResponse(BaseModel):
    """专用客服导入响应"""
    total_imported: int = Field(..., description="成功导入数量")
    failed_count: int = Field(..., description="失败数量")
    failed_details: Optional[List[str]] = Field(None, description="失败详情")

# 虚拟订单统计响应
class VirtualOrderStatsResponse(BaseModel):
    """虚拟订单统计响应"""
    total_students: int = Field(..., description="总学生数")
    total_subsidy: Decimal = Field(..., description="总补贴金额")
    total_tasks_generated: int = Field(..., description="生成的任务总数")
    total_tasks_completed: int = Field(..., description="完成的任务数")
    completion_rate: float = Field(..., description="完成率")

# 学生补贴池信息
class StudentPoolInfo(BaseModel):
    """学生补贴池信息"""
    id: int
    student_id: int
    student_name: str
    total_subsidy: Decimal
    remaining_amount: Decimal
    allocated_amount: Decimal
    completed_amount: Decimal
    status: str
    import_batch: Optional[str]
    created_at: datetime
    last_allocation_at: Optional[datetime]

    class Config:
        from_attributes = True

# 学生补贴池列表响应
class StudentPoolListResponse(BaseModel):
    """学生补贴池列表响应"""
    items: List[StudentPoolInfo]
    total: int
    page: int
    size: int

# 重新分配任务请求
class ReallocateTasksRequest(BaseModel):
    """重新分配任务请求"""
    student_id: int = Field(..., description="学生ID")

# 重新分配任务响应
class ReallocateTasksResponse(BaseModel):
    """重新分配任务响应"""
    student_id: int
    remaining_amount: Decimal
    new_tasks_count: int

# 报表生成请求
class GenerateReportRequest(BaseModel):
    """报表生成请求"""
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    student_ids: Optional[List[int]] = Field(None, description="指定学生ID列表，为空则包含所有学生")

# 报表生成响应
class GenerateReportResponse(BaseModel):
    """报表生成响应"""
    report_url: str = Field(..., description="报表下载链接")
    total_records: int = Field(..., description="报表记录总数")

# 虚拟任务创建模型
class VirtualTaskCreate(BaseModel):
    """虚拟任务创建模型"""
    student_id: int
    task_commission: Decimal
    task_summary: str
    task_requirement: str
    task_source: str
    reference_images: Optional[str] = None
    commission_unit: str = "元"
    end_date: datetime
    delivery_date: datetime

# 分页查询参数
class PageParams(BaseModel):
    """分页查询参数"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页数量")

# 虚拟客服相关模型
class VirtualCustomerServiceCreate(BaseModel):
    """创建虚拟客服请求"""
    name: str = Field(..., description="客服姓名")
    account: str = Field(..., description="客服账号")
    initial_password: str = Field("123456", description="初始密码")

class VirtualCustomerServiceResponse(BaseModel):
    """虚拟客服响应"""
    id: int
    user_id: int
    name: str
    account: str
    level: str
    status: str
    initial_password: str

class VirtualCustomerServiceInfo(BaseModel):
    """虚拟客服信息"""
    id: int
    user_id: int
    name: str
    account: str
    level: str
    status: str
    last_login_time: Optional[datetime]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class VirtualCustomerServiceListResponse(BaseModel):
    """虚拟客服列表响应"""
    items: List[VirtualCustomerServiceInfo]
    total: int
    page: int
    size: int

class VirtualCustomerServiceUpdate(BaseModel):
    """更新虚拟客服请求"""
    name: Optional[str] = Field(None, description="客服姓名")
    status: Optional[str] = Field(None, description="状态：active-活跃, inactive-停用")

class VirtualCustomerServiceUpdateResponse(BaseModel):
    """更新虚拟客服响应"""
    id: int
    name: str
    account: str
    status: str
    updated_fields: List[str]

class VirtualCustomerServiceDeleteResponse(BaseModel):
    """删除虚拟客服响应"""
    id: int
    name: str
    account: str
    deleted: bool

# 学生收入导出相关模型
class StudentIncomeExportRequest(BaseModel):
    """学生收入导出请求"""
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    student_ids: Optional[List[int]] = Field(None, description="指定学生ID列表")

class StudentIncomeExportResponse(BaseModel):
    """学生收入导出响应"""
    filename: str = Field(..., description="文件名")
    download_url: str = Field(..., description="下载链接")
    total_records: int = Field(..., description="导出记录数")
    export_time: str = Field(..., description="导出时间")

class StudentIncomeSummaryResponse(BaseModel):
    """学生收入汇总响应"""
    total_students: int = Field(..., description="学生总数")
    total_tasks: int = Field(..., description="任务总数")
    total_amount: float = Field(..., description="总金额")
    completed_tasks: int = Field(..., description="已完成任务数")
    completed_amount: float = Field(..., description="已完成金额")
    completion_rate: float = Field(..., description="完成率")
    export_time: str = Field(..., description="统计时间")

# 学生收入导出相关模型
class StudentIncomeExportRequest(BaseModel):
    """学生收入导出请求"""
    start_date: Optional[str] = Field(None, description="开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")
    student_ids: Optional[List[int]] = Field(None, description="指定学生ID列表，为空则导出所有学生")

class StudentIncomeStatsResponse(BaseModel):
    """学生收入统计响应"""
    total_students: int = Field(..., description="学生总数")
    total_tasks: int = Field(..., description="任务总数")
    total_income: float = Field(..., description="总收入")
    average_income_per_student: float = Field(..., description="学生平均收入")
    average_income_per_task: float = Field(..., description="任务平均收入")
    date_range: dict = Field(..., description="日期范围")
