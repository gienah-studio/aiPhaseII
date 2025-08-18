from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from shared.schemas.base import CamelCaseModel, BaseResponseModel, BaseRequestModel

class UploadTypeEnum(str, Enum):
    single = "single"
    batch = "batch"

class UploadStatusEnum(str, Enum):
    uploading = "uploading"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class UsageStatusEnum(str, Enum):
    available = "available"
    used = "used"
    disabled = "disabled"

# ===== 请求数据模型 =====

class UploadRequest(BaseRequestModel):
    """上传请求模型"""
    category_id: int = Field(..., description="分类ID")
    upload_notes: Optional[str] = Field(None, max_length=1000, description="上传备注")
    
    @validator('category_id')
    def validate_category_id(cls, v):
        if v <= 0:
            raise ValueError('分类ID必须大于0')
        return v

class ImageStatusUpdateRequest(BaseRequestModel):
    """图片状态更新请求模型"""
    status: UsageStatusEnum = Field(..., description="新状态")
    reason: Optional[str] = Field(None, max_length=500, description="更新原因")

class BatchDeleteRequest(BaseRequestModel):
    """批量删除请求模型"""
    image_ids: List[int] = Field(..., description="图片ID列表")
    delete_reason: Optional[str] = Field(None, max_length=500, description="删除原因")
    
    @validator('image_ids')
    def validate_image_ids(cls, v):
        if not v:
            raise ValueError('图片ID列表不能为空')
        if len(v) > 100:
            raise ValueError('单次最多删除100张图片')
        return v

class ImageQueryParams(BaseRequestModel):
    """图片查询参数模型"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页数量")
    category_id: Optional[int] = Field(None, description="分类ID筛选")
    status: Optional[UsageStatusEnum] = Field(None, description="状态筛选")
    search_keyword: Optional[str] = Field(None, max_length=100, description="搜索关键词")
    start_date: Optional[str] = Field(None, description="开始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="结束日期 YYYY-MM-DD")

class MarkImageUsedRequest(BaseRequestModel):
    """标记图片已使用请求模型"""
    image_id: int = Field(..., description="图片ID")
    task_id: int = Field(..., description="任务ID")

class BatchMoveCategoryRequest(BaseRequestModel):
    """批量移动分类请求模型"""
    image_ids: List[int] = Field(..., description="图片ID列表")
    target_category_id: int = Field(..., description="目标分类ID")
    move_reason: Optional[str] = Field(None, max_length=500, description="移动原因")
    
    @validator('image_ids')
    def validate_image_ids(cls, v):
        if not v:
            raise ValueError('图片ID列表不能为空')
        if len(v) > 100:
            raise ValueError('单次最多移动100张图片')
        return v
    
    @validator('target_category_id')
    def validate_target_category_id(cls, v):
        if v <= 0:
            raise ValueError('目标分类ID必须大于0')
        return v

# ===== 响应数据模型 =====

class CategoryResponse(BaseResponseModel):
    """分类响应模型"""
    id: int
    category_code: str
    category_name: str
    description: Optional[str]
    is_active: bool
    sort_order: int
    created_at: datetime

class BatchResponse(BaseResponseModel):
    """上传批次响应模型"""
    id: int
    batch_code: str
    category_id: int
    category_name: Optional[str]
    upload_type: str
    original_filename: Optional[str]
    total_files: int
    processed_files: int
    failed_files: int
    upload_status: str
    uploader_id: int
    uploader_name: str
    upload_notes: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

class ImageResponse(BaseResponseModel):
    """图片响应模型"""
    id: int
    batch_id: int
    category_id: int
    category_name: Optional[str]
    image_code: str
    original_filename: str
    stored_filename: str
    file_path: str
    file_url: str
    file_size: int
    image_width: Optional[int]
    image_height: Optional[int]
    file_format: str
    file_hash: Optional[str]
    usage_status: str
    used_at: Optional[datetime]
    used_in_task_id: Optional[int]
    quality_score: Optional[float]
    tags: Optional[List[str]]
    upload_notes: Optional[str]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    
    @validator('usage_status', pre=True)
    def convert_usage_status(cls, v):
        """转换枚举为字符串"""
        if hasattr(v, 'value'):
            return v.value
        return v

class ImageListResponse(BaseModel):
    """图片列表响应模型"""
    items: List[ImageResponse]
    total: int
    page: int
    size: int
    pages: int

class UploadResult(BaseModel):
    """单个文件上传结果"""
    success: bool
    filename: str
    image_id: Optional[int] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    error: Optional[str] = None
    is_duplicate: bool = False  # 是否为重复文件
    is_recovered: bool = False  # 是否为恢复的文件

class UploadResponse(BaseModel):
    """上传响应模型"""
    success: bool
    batch_id: int
    batch_code: str
    total_files: int
    success_files: int
    failed_files: int
    upload_results: List[UploadResult]
    error_message: Optional[str] = None

class ResourceStatsResponse(BaseModel):
    """资源统计响应模型"""
    total_images: int
    available_images: int
    used_images: int
    disabled_images: int
    total_size: int  # 字节
    categories_stats: List[Dict[str, Any]]
    recent_uploads: List[Dict[str, Any]]

class CategoryDetailStats(BaseModel):
    """分类详细统计项"""
    total: int
    available: int
    used: int
    rate: float

class CategoryDetailedStatsResponse(BaseModel):
    """分类详细统计响应模型"""
    avatar_redesign: CategoryDetailStats
    room_decoration: CategoryDetailStats
    photo_extension: CategoryDetailStats

class AvailableImageResponse(BaseModel):
    """可用图片响应模型"""
    success: bool
    image_id: Optional[int] = None
    file_url: Optional[str] = None
    image_code: Optional[str] = None
    category_code: Optional[str] = None
    original_filename: Optional[str] = None
    used_at: Optional[datetime] = None
    message: Optional[str] = None

# ===== 通用响应模型 =====

class ApiResponse(BaseModel):
    """统一API响应模型"""
    code: int = Field(200, description="状态码")
    msg: str = Field("success", description="消息")
    data: Optional[Any] = Field(None, description="数据")

class ErrorResponse(BaseModel):
    """错误响应模型"""
    code: int
    msg: str
    data: Optional[Dict[str, Any]] = None

# ===== 文件上传相关 =====

class FileUploadInfo(BaseModel):
    """文件上传信息"""
    filename: str
    content_type: str
    file_size: int
    file_hash: str

class ProcessedFileInfo(BaseModel):
    """处理后的文件信息"""
    original_filename: str
    stored_filename: str
    file_path: str
    file_url: str
    file_size: int
    image_width: Optional[int]
    image_height: Optional[int]
    file_format: str
    quality_score: Optional[float]
    file_hash: str