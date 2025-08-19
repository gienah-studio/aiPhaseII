from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid
import logging
from datetime import datetime, date
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
import io

from shared.database.session import get_db
from shared.schemas.common import ResponseSchema
from shared.exceptions import BusinessException
from ..api.api_docs import VirtualOrderApiDocs
from ..schemas.virtual_order_schemas import (
    StudentSubsidyImportResponse,
    CustomerServiceImportResponse,
    VirtualOrderStatsResponse,
    StudentPoolListResponse,
    ReallocateTasksRequest,
    ReallocateTasksResponse,
    GenerateReportRequest,
    GenerateReportResponse,
    PageParams,
    VirtualCustomerServiceCreate,
    VirtualCustomerServiceResponse,
    VirtualCustomerServiceListResponse,
    VirtualCustomerServiceUpdate,
    VirtualCustomerServiceUpdateResponse,
    VirtualCustomerServiceDeleteResponse,
    StudentIncomeExportRequest,
    StudentIncomeExportResponse,
    StudentIncomeSummaryResponse,
    StudentPoolDeleteResponse
)
from ..service.virtual_order_service import VirtualOrderService
from ..utils.excel_utils import ExcelProcessor

router = APIRouter()

@router.post(
    "/import/studentSubsidy",
    response_model=ResponseSchema[StudentSubsidyImportResponse],
    **VirtualOrderApiDocs.IMPORT_STUDENT_SUBSIDY
)
async def import_student_subsidy(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """导入学生补贴表"""
    try:
        # 验证文件大小
        ExcelProcessor.validate_excel_file_size(file)
        
        # 读取Excel文件
        df = await ExcelProcessor.read_excel_file(file)
        
        # 验证数据
        valid_data, errors, filtered_count = ExcelProcessor.validate_student_subsidy_data(df)
        
        if errors:
            raise HTTPException(
                status_code=400,
                detail=f"数据验证失败: {'; '.join(errors[:5])}"  # 只显示前5个错误
            )
        
        if not valid_data:
            raise HTTPException(status_code=400, detail="没有有效的数据可导入")
        
        # 检查虚拟任务生成配置
        from ..service.config_service import ConfigService
        config_service = ConfigService(db)
        task_generation_config = config_service.get_virtual_task_generation_config()
        task_generation_enabled = task_generation_config.get('enabled', True)

        # 生成导入批次号
        import_batch = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

        # 执行导入（根据配置决定是否生成虚拟任务）
        service = VirtualOrderService(db)
        result = service.import_student_subsidy_data_with_service_allocation(
            valid_data, import_batch, use_service_allocation=True,
            generate_tasks=task_generation_enabled
        )
        
        # 构建成功消息，包含过滤信息和任务生成状态
        success_message = "导入成功"
        if filtered_count > 0:
            success_message += f"，已自动过滤 {filtered_count} 条补贴金额为0的记录"

        # 添加任务生成状态信息
        if not task_generation_enabled:
            success_message += "，虚拟任务生成功能已关闭，仅创建补贴池记录"
        elif result.get('generated_tasks', 0) == 0:
            success_message += "，未生成虚拟任务"
        else:
            success_message += f"，已生成 {result.get('generated_tasks', 0)} 个虚拟任务"

        return ResponseSchema[StudentSubsidyImportResponse](
            code=200,
            message=success_message,
            data=StudentSubsidyImportResponse(**result)
        )
        
    except HTTPException:
        raise
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")

@router.post(
    "/import/customerService",
    response_model=ResponseSchema[CustomerServiceImportResponse],
    **VirtualOrderApiDocs.IMPORT_CUSTOMER_SERVICE
)
async def import_customer_service(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """导入专用客服"""
    try:
        # 验证文件大小
        ExcelProcessor.validate_excel_file_size(file)
        
        # 读取Excel文件
        df = await ExcelProcessor.read_excel_file(file)
        
        # 验证数据
        valid_data, errors = ExcelProcessor.validate_customer_service_data(df)
        
        if errors:
            raise HTTPException(
                status_code=400,
                detail=f"数据验证失败: {'; '.join(errors[:5])}"
            )
        
        if not valid_data:
            raise HTTPException(status_code=400, detail="没有有效的数据可导入")
        
        # 执行导入
        service = VirtualOrderService(db)
        result = service.import_customer_service_data(valid_data)
        
        return ResponseSchema[CustomerServiceImportResponse](
            code=200,
            message="导入成功",
            data=CustomerServiceImportResponse(**result)
        )
        
    except HTTPException:
        raise
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")

@router.get(
    "/stats",
    response_model=ResponseSchema[VirtualOrderStatsResponse],
    **VirtualOrderApiDocs.GET_VIRTUAL_ORDER_STATS
)
async def get_virtual_order_stats(db: Session = Depends(get_db)):
    """获取虚拟订单统计"""
    try:
        service = VirtualOrderService(db)
        result = service.get_virtual_order_stats()
        
        return ResponseSchema[VirtualOrderStatsResponse](
            code=200,
            message="获取成功",
            data=VirtualOrderStatsResponse(**result)
        )
        
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")

@router.get(
    "/studentPools",
    response_model=ResponseSchema[StudentPoolListResponse],
    **VirtualOrderApiDocs.GET_STUDENT_POOLS
)
async def get_student_pools(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态过滤"),
    db: Session = Depends(get_db)
):
    """获取学生补贴池列表"""
    try:
        service = VirtualOrderService(db)
        result = service.get_student_pools(page, size, status)
        
        return ResponseSchema[StudentPoolListResponse](
            code=200,
            message="获取成功",
            data=StudentPoolListResponse(**result)
        )
        
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取学生补贴池列表失败: {str(e)}")

@router.post(
    "/reallocate/{student_id}",
    response_model=ResponseSchema[ReallocateTasksResponse],
    **VirtualOrderApiDocs.REALLOCATE_STUDENT_TASKS
)
async def reallocate_student_tasks(
    student_id: int,
    db: Session = Depends(get_db)
):
    """重新分配学生任务"""
    try:
        service = VirtualOrderService(db)
        result = service.reallocate_student_tasks_with_service_allocation(student_id)
        
        return ResponseSchema[ReallocateTasksResponse](
            code=200,
            message="重新分配成功",
            data=ReallocateTasksResponse(**result)
        )
        
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重新分配任务失败: {str(e)}")

@router.delete(
    "/studentPools/{pool_id}",
    response_model=ResponseSchema[StudentPoolDeleteResponse],
    summary="删除学生补贴池",
    description="软删除指定的学生补贴池记录，删除前会检查是否有未完成的虚拟任务"
)
async def delete_student_pool(
    pool_id: int,
    db: Session = Depends(get_db)
):
    """删除学生补贴池（软删除）"""
    try:
        service = VirtualOrderService(db)
        result = service.delete_student_pool(pool_id)
        
        return ResponseSchema[StudentPoolDeleteResponse](
            code=200,
            message="删除成功",
            data=StudentPoolDeleteResponse(**result)
        )
        
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除学生补贴池失败: {str(e)}")

# ==================== 虚拟客服管理接口 ====================

@router.post(
    "/customerService",
    response_model=ResponseSchema[VirtualCustomerServiceResponse],
    **VirtualOrderApiDocs.CREATE_VIRTUAL_CUSTOMER_SERVICE
)
async def create_virtual_customer_service(
    request: VirtualCustomerServiceCreate,
    db: Session = Depends(get_db)
):
    """创建虚拟客服"""
    try:
        service = VirtualOrderService(db)
        result = service.create_virtual_customer_service(
            name=request.name,
            account=request.account,
            initial_password=request.initial_password
        )

        return ResponseSchema[VirtualCustomerServiceResponse](
            code=200,
            message="创建成功",
            data=VirtualCustomerServiceResponse(**result)
        )

    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建虚拟客服失败: {str(e)}")

@router.get(
    "/customerService",
    response_model=ResponseSchema[VirtualCustomerServiceListResponse],
    **VirtualOrderApiDocs.GET_VIRTUAL_CUSTOMER_SERVICES
)
async def get_virtual_customer_services(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取虚拟客服列表"""
    try:
        service = VirtualOrderService(db)
        result = service.get_virtual_customer_services(page, size)

        return ResponseSchema[VirtualCustomerServiceListResponse](
            code=200,
            message="获取成功",
            data=VirtualCustomerServiceListResponse(**result)
        )

    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取虚拟客服列表失败: {str(e)}")

@router.put(
    "/customerService/{cs_id}",
    response_model=ResponseSchema[VirtualCustomerServiceUpdateResponse],
    **VirtualOrderApiDocs.UPDATE_VIRTUAL_CUSTOMER_SERVICE
)
async def update_virtual_customer_service(
    cs_id: int,
    request: VirtualCustomerServiceUpdate,
    db: Session = Depends(get_db)
):
    """更新虚拟客服信息"""
    try:
        service = VirtualOrderService(db)
        result = service.update_virtual_customer_service(
            cs_id, request.dict(exclude_unset=True)
        )

        return ResponseSchema[VirtualCustomerServiceUpdateResponse](
            code=200,
            message="更新成功",
            data=VirtualCustomerServiceUpdateResponse(**result)
        )

    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新虚拟客服失败: {str(e)}")

@router.delete(
    "/customerService/{cs_id}",
    response_model=ResponseSchema[VirtualCustomerServiceDeleteResponse],
    **VirtualOrderApiDocs.DELETE_VIRTUAL_CUSTOMER_SERVICE
)
async def delete_virtual_customer_service(
    cs_id: int,
    db: Session = Depends(get_db)
):
    """删除虚拟客服"""
    try:
        service = VirtualOrderService(db)
        result = service.delete_virtual_customer_service(cs_id)

        return ResponseSchema[VirtualCustomerServiceDeleteResponse](
            code=200,
            message="删除成功",
            data=VirtualCustomerServiceDeleteResponse(**result)
        )

    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除虚拟客服失败: {str(e)}")

# ==================== 学生收入管理接口 ====================

@router.get(
    "/studentIncome/export",
    **VirtualOrderApiDocs.EXPORT_STUDENT_INCOME
)
async def export_student_income(
    db: Session = Depends(get_db)
):
    """导出学生收入数据为Excel（导出所有数据，无需参数）"""
    try:
        service = VirtualOrderService(db)

        # 导出所有学生收入数据（不传任何过滤参数）
        excel_data = service.export_student_income_data()

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"student_income_all_{timestamp}.xlsx"

        # 返回Excel文件
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出学生收入数据失败: {str(e)}")

@router.get(
    "/studentIncome/summary",
    response_model=ResponseSchema[StudentIncomeSummaryResponse],
    **VirtualOrderApiDocs.GET_STUDENT_INCOME_SUMMARY
)
async def get_student_income_summary(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取学生收入汇总统计"""
    try:
        service = VirtualOrderService(db)

        # 转换日期格式
        start_date_str = start_date.isoformat() if start_date else None
        end_date_str = end_date.isoformat() if end_date else None

        # 获取汇总数据
        result = service.get_student_income_summary(
            start_date=start_date_str,
            end_date=end_date_str
        )

        return ResponseSchema[StudentIncomeSummaryResponse](
            code=200,
            message="获取成功",
            data=StudentIncomeSummaryResponse(**result)
        )

    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取学生收入汇总失败: {str(e)}")

# ==================== 虚拟任务完成状态同步接口 ====================

@router.post(
    "/sync/completedTasks",
    response_model=ResponseSchema[dict],
    summary="同步已完成虚拟任务",
    description="同步所有已完成的虚拟任务到学生补贴池，更新完成金额"
)
async def sync_completed_virtual_tasks(db: Session = Depends(get_db)):
    """同步已完成虚拟任务到学生补贴池"""
    try:
        service = VirtualOrderService(db)
        result = service.sync_completed_virtual_tasks()

        return ResponseSchema[dict](
            code=200,
            message="同步成功",
            data=result
        )

    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步已完成虚拟任务失败: {str(e)}")

@router.post(
    "/updateTaskCompletion/{task_id}",
    response_model=ResponseSchema[dict],
    summary="更新虚拟任务完成状态",
    description="更新指定虚拟任务的完成状态，同时更新学生补贴池"
)
async def update_virtual_task_completion(
    task_id: int,
    db: Session = Depends(get_db)
):
    """更新虚拟任务完成状态"""
    try:
        service = VirtualOrderService(db)
        result = service.update_virtual_task_completion(task_id)

        return ResponseSchema[dict](
            code=200,
            message="更新成功",
            data=result
        )

    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新虚拟任务完成状态失败: {str(e)}")

@router.post(
    "/manualCheckExpiredTasks",
    response_model=ResponseSchema[dict],
    summary="手动检查过期任务",
    description="手动触发过期虚拟任务检查和重新生成"
)
async def manual_check_expired_tasks():
    """手动检查过期任务"""
    try:
        from ..service.task_scheduler import manual_check_expired
        await manual_check_expired()

        return ResponseSchema[dict](
            code=200,
            message="过期任务检查完成",
            data={"status": "completed"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"手动检查过期任务失败: {str(e)}")

@router.post(
    "/manualCheckAutoConfirmTasks",
    response_model=ResponseSchema[dict],
    summary="手动检查自动确认任务",
    description="手动触发虚拟任务自动确认检查，确认提交超过1小时的任务"
)
async def manual_check_auto_confirm_tasks():
    """手动检查自动确认任务"""
    try:
        from ..service.task_scheduler import manual_check_auto_confirm
        await manual_check_auto_confirm()

        return ResponseSchema[dict](
            code=200,
            message="自动确认任务检查完成",
            data={"status": "completed"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"手动检查自动确认任务失败: {str(e)}")

@router.get(
    "/autoConfirmConfig",
    response_model=ResponseSchema[dict],
    summary="获取自动确认配置",
    description="获取虚拟任务自动确认的相关配置"
)
async def get_auto_confirm_config(db: Session = Depends(get_db)):
    """获取自动确认配置"""
    try:
        from ..service.config_service import ConfigService
        config_service = ConfigService(db)
        config = config_service.get_auto_confirm_config()

        return ResponseSchema[dict](
            code=200,
            message="获取配置成功",
            data=config
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取自动确认配置失败: {str(e)}")

@router.post(
    "/autoConfirmConfig",
    response_model=ResponseSchema[dict],
    summary="更新自动确认配置",
    description="更新虚拟任务自动确认的相关配置"
)
async def update_auto_confirm_config(
    enabled: bool = Query(True, description="是否启用自动确认"),
    interval_hours: float = Query(1.0, description="自动确认时间间隔（小时）"),
    max_batch_size: int = Query(100, description="单次处理最大数量"),
    db: Session = Depends(get_db)
):
    """更新自动确认配置"""
    try:
        from ..service.config_service import ConfigService
        config_service = ConfigService(db)

        # 更新配置
        config_service.set_config('auto_confirm_enabled', enabled, 'string', '是否启用虚拟任务自动确认功能')
        config_service.set_config('auto_confirm_interval_hours', interval_hours, 'number', '自动确认时间间隔（小时）')
        config_service.set_config('auto_confirm_max_batch_size', max_batch_size, 'number', '单次自动确认最大处理数量')

        return ResponseSchema[dict](
            code=200,
            message="配置更新成功",
            data={
                "enabled": enabled,
                "interval_hours": interval_hours,
                "max_batch_size": max_batch_size
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新自动确认配置失败: {str(e)}")

@router.get(
    "/virtualTaskGenerationConfig",
    response_model=ResponseSchema[dict],
    summary="获取虚拟任务生成配置",
    description="获取虚拟任务生成的相关配置"
)
async def get_virtual_task_generation_config(db: Session = Depends(get_db)):
    """获取虚拟任务生成配置"""
    try:
        from ..service.config_service import ConfigService
        config_service = ConfigService(db)
        config = config_service.get_virtual_task_generation_config()

        return ResponseSchema[dict](
            code=200,
            message="获取配置成功",
            data=config
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取虚拟任务生成配置失败: {str(e)}")

@router.post(
    "/virtualTaskGenerationConfig",
    response_model=ResponseSchema[dict],
    summary="更新虚拟任务生成配置",
    description="更新虚拟任务生成的相关配置"
)
async def update_virtual_task_generation_config(
    enabled: bool = Query(True, description="是否启用虚拟任务生成（总开关）"),
    daily_bonus_enabled: bool = Query(True, description="是否启用每日奖金池任务生成"),
    expired_task_regeneration_enabled: bool = Query(True, description="是否启用过期任务重新生成"),
    value_recycling_enabled: bool = Query(True, description="是否启用价值回收任务生成"),
    bonus_pool_task_enabled: bool = Query(True, description="是否启用奖金池任务生成"),
    db: Session = Depends(get_db)
):
    """更新虚拟任务生成配置"""
    try:
        from ..service.config_service import ConfigService
        config_service = ConfigService(db)

        # 更新配置
        config_service.set_config('virtual_task_generation_enabled', enabled, 'boolean', '是否启用虚拟任务生成功能（总开关）')
        config_service.set_config('virtual_task_daily_bonus_enabled', daily_bonus_enabled, 'boolean', '是否启用每日奖金池任务生成')
        config_service.set_config('virtual_task_expired_regeneration_enabled', expired_task_regeneration_enabled, 'boolean', '是否启用过期任务重新生成')
        config_service.set_config('virtual_task_value_recycling_enabled', value_recycling_enabled, 'boolean', '是否启用价值回收任务生成')
        config_service.set_config('virtual_task_bonus_pool_enabled', bonus_pool_task_enabled, 'boolean', '是否启用奖金池任务生成')

        return ResponseSchema[dict](
            code=200,
            message="配置更新成功",
            data={
                "enabled": enabled,
                "daily_bonus_enabled": daily_bonus_enabled,
                "expired_task_regeneration_enabled": expired_task_regeneration_enabled,
                "value_recycling_enabled": value_recycling_enabled,
                "bonus_pool_task_enabled": bonus_pool_task_enabled
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新虚拟任务生成配置失败: {str(e)}")

@router.post(
    "/resetStudentPool/{student_id}",
    response_model=ResponseSchema[dict],
    summary="重置学生补贴池",
    description="重置学生补贴池的完成状态，清空已完成金额和消耗补贴，重新生成任务"
)
async def reset_student_pool(
    student_id: int,
    db: Session = Depends(get_db)
):
    """重置学生补贴池"""
    try:
        service = VirtualOrderService(db)
        result = service.reset_student_pool(student_id)

        return ResponseSchema[dict](
            code=200,
            message="学生补贴池重置成功",
            data=result
        )

    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置学生补贴池失败: {str(e)}")

@router.post(
    "/processCompletedTaskRemainingValue/{task_id}",
    response_model=ResponseSchema[dict],
    summary="处理已完成任务的剩余价值",
    description="为已完成但没有处理剩余价值的任务重新生成新任务"
)
async def process_completed_task_remaining_value(
    task_id: int,
    db: Session = Depends(get_db)
):
    """处理已完成任务的剩余价值"""
    try:
        service = VirtualOrderService(db)
        result = service.process_completed_task_remaining_value(task_id)

        if result['success']:
            return ResponseSchema[dict](
                code=200,
                message=result['message'],
                data=result
            )
        else:
            return ResponseSchema[dict](
                code=400,
                message=result['message'],
                data=result
            )

    except Exception as e:
        logger.error(f"处理已完成任务剩余价值失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")
