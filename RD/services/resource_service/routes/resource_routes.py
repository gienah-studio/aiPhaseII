from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Union
import logging

from shared.dependencies.database import get_db
from shared.dependencies.auth import get_current_active_user
from shared.exceptions import BusinessException
from ..service.resource_service import ResourceService
from ..schemas.resource_schemas import (
    CategoryResponse, ImageResponse, ImageListResponse, UploadResponse,
    ResourceStatsResponse, AvailableImageResponse, ApiResponse,
    ImageStatusUpdateRequest, BatchDeleteRequest, MarkImageUsedRequest,
    BatchMoveCategoryRequest, CategoryDetailedStatsResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resources", tags=["资源库管理"])

@router.get("", summary="获取资源列表")
async def get_resources(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    category_id: Optional[int] = Query(None, description="分类ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选：available/used/disabled"),
    search_keyword: Optional[str] = Query(None, description="搜索关键词"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取资源列表，支持分页和多条件筛选（前端兼容接口）
    """
    try:
        service = ResourceService(db)
        result = service.get_resource_images(
            page=page,
            size=size,
            category_id=category_id,
            status=status,
            search_keyword=search_keyword,
            start_date=start_date,
            end_date=end_date
        )
        
        return {"code": 200, "msg": "获取成功", "data": result}
        
    except BusinessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        logger.error(f"获取资源列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/categories", summary="获取分类列表")
async def get_categories(db: Session = Depends(get_db)):
    """
    获取所有启用的图片分类列表
    """
    try:
        service = ResourceService(db)
        categories = service.get_categories()
        return {"code": 200, "msg": "获取成功", "data": {"categories": categories}}
    except BusinessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        logger.error(f"获取分类列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/tags", summary="获取标签列表")
async def get_tags(db: Session = Depends(get_db)):
    """
    获取所有资源标签列表
    """
    try:
        service = ResourceService(db)
        # 返回简单的标签列表，如果ResourceService没有get_tags方法，我们返回空数组
        tags = []  # 这里应该调用service的get_tags方法，暂时返回空数组
        return {"code": 200, "msg": "获取成功", "data": tags}
    except Exception as e:
        logger.error(f"获取标签列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.post("/upload", summary="上传资源文件")
async def upload_resources(
    categoryId: int = Form(..., description="分类ID"),
    description: Optional[str] = Form(None, description="上传备注"),
    files: List[UploadFile] = File(..., description="上传文件列表"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    统一上传接口，支持：
    - 单张图片上传
    - 多张图片批量上传  
    - ZIP压缩包上传（自动解压）
    
    支持的图片格式：jpg, jpeg, png, gif, bmp, webp, tiff
    """
    try:
        # 记录接收到的文件名（用于问题排查）
        for i, file in enumerate(files):
            if file.filename:
                logger.debug(f"接收文件 {i+1}: {file.filename}")

        # 验证上传文件数量
        if len(files) > 50:
            raise HTTPException(status_code=400, detail="单次最多上传50个文件")

        # 验证文件大小
        for file in files:
            if file.size and file.size > 100 * 1024 * 1024:  # 100MB
                raise HTTPException(status_code=400, detail=f"文件 {file.filename} 过大，单个文件最大100MB")
        
        # 获取用户信息
        uploader_id = current_user.id
        uploader_name = current_user.username
        
        # 如果存在关联的userinfo，使用userinfo的信息
        if hasattr(current_user, 'userinfo') and current_user.userinfo:
            uploader_id = current_user.userinfo.roleId
            if current_user.userinfo.name:
                uploader_name = current_user.userinfo.name
        
        service = ResourceService(db)
        result = service.upload_resources(
            category_id=categoryId,
            files=files,
            uploader_id=uploader_id,
            uploader_name=uploader_name,
            upload_notes=description
        )
        
        # 包装为标准API响应格式
        return {
            "code": 200,
            "msg": result.error_message,
            "data": {
                "batch_id": result.batch_id,
                "batch_code": result.batch_code,
                "total_files": result.total_files,
                "success_files": result.success_files,
                "failed_files": result.failed_files,
                "upload_results": result.upload_results
            }
        }
        
    except BusinessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传资源失败: {str(e)}")
        raise HTTPException(status_code=500, detail="上传失败，请重试")

@router.get("/images", response_model=ImageListResponse, summary="获取图片列表")
async def get_resource_images(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    category_id: Optional[int] = Query(None, description="分类ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选：available/used/disabled"),
    search_keyword: Optional[str] = Query(None, description="搜索关键词"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取资源图片列表，支持分页和多条件筛选
    """
    try:
        service = ResourceService(db)
        result = service.get_resource_images(
            page=page,
            size=size,
            category_id=category_id,
            status=status,
            search_keyword=search_keyword,
            start_date=start_date,
            end_date=end_date
        )
        
        return result
        
    except BusinessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        logger.error(f"获取图片列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/images/{image_id}", response_model=ImageResponse, summary="获取图片详情")
async def get_resource_image_detail(
    image_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取指定图片的详细信息
    """
    try:
        service = ResourceService(db)
        result = service.get_resource_image_detail(image_id)
        return result
        
    except BusinessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        logger.error(f"获取图片详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.put("/images/{image_id}/status", response_model=ApiResponse, summary="更新图片状态")
async def update_image_status(
    image_id: int,
    request: ImageStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    更新图片状态：available -> used/disabled
    注意：已使用的图片不能重新设为可用状态
    """
    try:
        service = ResourceService(db)
        result = service.update_image_status(
            image_id=image_id,
            status=request.status.value,
            reason=request.reason
        )
        
        return ApiResponse(
            code=200,
            msg="状态更新成功",
            data=result
        )
        
    except BusinessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        logger.error(f"更新图片状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.delete("/images/{image_id}", response_model=ApiResponse, summary="删除图片")
async def delete_resource_image(
    image_id: int,
    delete_reason: Optional[str] = Query(None, description="删除原因"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    删除指定图片（软删除）
    """
    try:
        service = ResourceService(db)
        result = service.delete_resource_image(
            image_id=image_id,
            delete_reason=delete_reason
        )
        
        return ApiResponse(
            code=200,
            msg="图片删除成功",
            data=result
        )
        
    except BusinessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        logger.error(f"删除图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.post("/images/batch-delete", response_model=ApiResponse, summary="批量删除图片")
async def batch_delete_images(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    批量删除图片（软删除）
    """
    try:
        service = ResourceService(db)
        result = service.batch_delete_images(
            image_ids=request.image_ids,
            delete_reason=request.delete_reason
        )
        
        return ApiResponse(
            code=200,
            msg="批量删除成功",
            data=result
        )
        
    except BusinessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        logger.error(f"批量删除图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.post("/images/batch-move-category", response_model=ApiResponse, summary="批量移动图片分类")
async def batch_move_category(
    request: BatchMoveCategoryRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    批量移动图片到指定分类
    """
    try:
        service = ResourceService(db)
        result = service.batch_move_category(
            image_ids=request.image_ids,
            target_category_id=request.target_category_id,
            move_reason=request.move_reason
        )
        
        return ApiResponse(
            code=200,
            msg="批量移动分类成功",
            data=result
        )
        
    except BusinessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        logger.error(f"批量移动分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/stats", summary="获取资源统计")
async def get_resource_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取资源库统计信息，包括：
    - 总图片数、可用数、已使用数、已禁用数
    - 总文件大小
    - 各分类统计
    - 最近上传记录
    """
    try:
        service = ResourceService(db)
        result = service.get_resource_stats()
        return {"code": 200, "msg": "获取成功", "data": result}
        
    except BusinessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        logger.error(f"获取资源统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/category-stats", summary="获取分类详细统计")
async def get_category_detailed_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取三类资源的详细统计信息：
    - avatar_redesign: 头像重设计
    - room_decoration: 房间装饰
    - photo_extension: 照片扩展
    
    返回每类的总数、可用数、已用数、使用率
    """
    try:
        service = ResourceService(db)
        result = service.get_category_detailed_stats()
        return {"code": 200, "msg": "获取成功", "data": result}
        
    except BusinessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        logger.error(f"获取分类详细统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

# ===== 内部API接口（供虚拟任务系统调用） =====

@router.get("/available-image/{category_code}", response_model=AvailableImageResponse, summary="获取可用图片")
async def get_available_image(
    category_code: str,
    db: Session = Depends(get_db)
):
    """
    为虚拟任务获取指定分类的可用图片
    内部接口，用于虚拟任务生成时自动选择参考图
    """
    try:
        service = ResourceService(db)
        result = service.get_available_image_for_task(category_code)
        return result
        
    except Exception as e:
        logger.error(f"获取可用图片失败: {str(e)}")
        return AvailableImageResponse(
            success=False,
            message=f"获取可用图片失败: {str(e)}"
        )

@router.post("/mark-used", response_model=ApiResponse, summary="标记图片已使用")
async def mark_image_used(
    request: MarkImageUsedRequest,
    db: Session = Depends(get_db)
):
    """
    标记图片为已使用状态
    内部接口，用于虚拟任务系统在使用图片后进行标记
    """
    try:
        service = ResourceService(db)
        result = service.mark_image_as_used(
            image_id=request.image_id,
            task_id=request.task_id
        )
        
        return ApiResponse(
            code=200,
            msg="图片已标记为使用状态",
            data=result
        )
        
    except BusinessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        logger.error(f"标记图片已使用失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/usage-stats", response_model=ApiResponse, summary="获取使用统计")
async def get_usage_stats(
    db: Session = Depends(get_db)
):
    """
    获取图片使用统计信息
    内部接口，用于虚拟任务系统的统计报表
    """
    try:
        service = ResourceService(db)
        stats = service.get_resource_stats()
        
        # 简化统计信息
        usage_stats = {
            'total_images': stats.total_images,
            'available_images': stats.available_images,
            'used_images': stats.used_images,
            'usage_rate': round((stats.used_images / max(stats.total_images, 1)) * 100, 2)
        }
        
        return ApiResponse(
            code=200,
            msg="获取使用统计成功",
            data=usage_stats
        )
        
    except Exception as e:
        logger.error(f"获取使用统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")