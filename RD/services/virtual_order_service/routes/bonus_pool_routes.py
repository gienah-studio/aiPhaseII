from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime
import io

from shared.database.session import get_db
from shared.schemas.common import ResponseSchema
from shared.exceptions import BusinessException
from ..service.bonus_pool_service import BonusPoolService
from ..service.virtual_order_service import VirtualOrderService

router = APIRouter(prefix="/bonusPool", tags=["奖金池管理"])

@router.get("/status")
async def get_bonus_pool_status(
    pool_date: Optional[date] = Query(None, description="奖金池日期，默认为今天"),
    db: Session = Depends(get_db)
):
    """获取奖金池状态"""
    try:
        service = BonusPoolService(db)
        result = service.get_bonus_pool_status(pool_date)

        return ResponseSchema(
            code=200,
            message="获取成功",
            data=result
        )
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取奖金池状态失败: {str(e)}")

@router.get("/summary")
async def get_bonus_pool_summary(
    pool_date: Optional[date] = Query(None, description="奖金池日期，默认为今天"),
    db: Session = Depends(get_db)
):
    """获取奖金池汇总信息（累计金额和可抢人数）"""
    try:
        service = BonusPoolService(db)
        result = service.get_bonus_pool_summary(pool_date)

        return ResponseSchema(
            code=200,
            message="获取成功",
            data=result
        )
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取奖金池汇总信息失败: {str(e)}")

@router.get("/dailyStats")
async def get_daily_subsidy_stats(
    start_date: Optional[date] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期，格式：YYYY-MM-DD，默认为今天"),
    days: Optional[int] = Query(7, description="查询天数，当start_date和end_date都为空时使用，默认7天"),
    db: Session = Depends(get_db)
):
    """获取每日补贴统计数据

    返回数据包含：
    - 每天补贴总金额
    - 剩余金额
    - 实际获得金额
    - 每天完成率
    - 每天生成任务数
    - 完成数
    - 日期
    """
    try:
        service = BonusPoolService(db)
        result = service.get_daily_subsidy_stats(start_date, end_date, days)

        return ResponseSchema(
            code=200,
            message="获取成功",
            data=result
        )
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取每日补贴统计失败: {str(e)}")

@router.get("/dailyStats/export")
async def export_daily_subsidy_stats(
    start_date: Optional[date] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期，格式：YYYY-MM-DD，默认为今天"),
    days: Optional[int] = Query(7, description="查询天数，当start_date和end_date都为空时使用，默认7天"),
    db: Session = Depends(get_db)
):
    """导出每日补贴统计数据为Excel

    导出数据包含：
    - 每天补贴总金额
    - 剩余金额
    - 实际获得金额
    - 每天完成率
    - 每天生成任务数
    - 完成数
    - 日期
    - 奖金池相关数据
    - 学生达标统计
    """
    try:
        service = BonusPoolService(db)
        excel_data = service.export_daily_subsidy_stats(start_date, end_date, days)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_range = ""
        if start_date and end_date:
            date_range = f"_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        elif days:
            date_range = f"_最近{days}天"

        filename = f"每日补贴统计{date_range}_{timestamp}.xlsx"

        # 返回Excel文件 - 修复中文文件名编码问题
        from urllib.parse import quote
        encoded_filename = quote(filename, encoding='utf-8')
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )

    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出每日补贴统计失败: {str(e)}")

@router.post("/dailyTask")
async def run_daily_bonus_pool_task(
    process_date: Optional[date] = Query(None, description="要处理的日期（统计这一天的达标情况），默认为昨天"),
    db: Session = Depends(get_db)
):
    """手动执行每日奖金池任务
    
    注意：
    - process_date: 要统计达标情况的日期
    - 奖金池会创建在 process_date + 1 天
    - 例如：process_date=2025-08-08，会统计8月8日的达标情况，创建8月9日的奖金池
    """
    try:
        from datetime import timedelta
        
        service = BonusPoolService(db)
        
        # 如果没有指定日期，默认处理昨天
        if process_date is None:
            process_date = date.today() - timedelta(days=1)
        
        # 奖金池日期是处理日期的下一天
        pool_date = process_date + timedelta(days=1)
        
        # 1. 更新学生达标记录（处理指定日期）
        achievement_result = service.update_daily_achievements(process_date)
        
        # 2. 创建或更新奖金池（下一天的）
        pool = service.create_or_update_bonus_pool(pool_date)
        
        # 3. 生成奖金池任务
        generate_result = None
        if pool.remaining_amount > 0:
            generate_result = service.generate_bonus_pool_tasks(pool_date)
        
        return ResponseSchema(
            code=200,
            message="每日奖金池任务执行成功",
            data={
                "process_date": process_date.isoformat(),
                "pool_date": pool_date.isoformat(),
                "achievement": achievement_result,
                "pool": {
                    "date": pool.pool_date.isoformat(),
                    "total_amount": float(pool.total_amount),
                    "remaining_amount": float(pool.remaining_amount)
                },
                "generate_result": generate_result
            }
        )
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行每日任务失败: {str(e)}")

@router.post("/generateTasks")
async def generate_bonus_pool_tasks(
    pool_date: Optional[date] = Query(None, description="奖金池日期，默认为今天"),
    db: Session = Depends(get_db)
):
    """手动生成奖金池任务"""
    try:
        service = BonusPoolService(db)
        result = service.generate_bonus_pool_tasks(pool_date)
        
        return ResponseSchema(
            code=200,
            message=result.get('message', '操作完成'),
            data=result
        )
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成奖金池任务失败: {str(e)}")

@router.post("/processExpired")
async def process_expired_bonus_tasks(
    db: Session = Depends(get_db)
):
    """处理过期的奖金池任务"""
    try:
        service = BonusPoolService(db)
        result = service.process_expired_bonus_tasks()
        
        return ResponseSchema(
            code=200,
            message="过期任务处理成功",
            data=result
        )
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理过期任务失败: {str(e)}")

@router.get("/studentAchievement")
async def get_student_achievement(
    student_id: int = Query(..., description="学生ID"),
    achievement_date: Optional[date] = Query(None, description="查询日期，默认为昨天"),
    db: Session = Depends(get_db)
):
    """查询学生达标情况"""
    try:
        from datetime import timedelta
        
        if achievement_date is None:
            achievement_date = date.today() - timedelta(days=1)
        
        service = BonusPoolService(db)
        result = service.calculate_student_daily_achievement(student_id, achievement_date)
        
        # 检查今日是否有奖金池访问权限
        has_bonus_access = service.check_student_bonus_access(student_id)
        result['has_bonus_access_today'] = has_bonus_access
        
        return ResponseSchema(
            code=200,
            message="查询成功",
            data=result
        )
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询学生达标情况失败: {str(e)}")

@router.get("/studentTasks")
async def get_student_available_tasks(
    student_id: int = Query(..., description="学生ID"),
    include_bonus_pool: bool = Query(True, description="是否包含奖金池任务"),
    db: Session = Depends(get_db)
):
    """获取学生可见的任务列表"""
    try:
        service = VirtualOrderService(db)
        tasks = service.get_student_available_tasks(student_id, include_bonus_pool)
        
        # 添加统计信息
        personal_tasks = [t for t in tasks if t['type'] == 'personal']
        bonus_tasks = [t for t in tasks if t['type'] == 'bonus_pool']
        
        return ResponseSchema(
            code=200,
            message="获取成功",
            data={
                "tasks": tasks,
                "summary": {
                    "total": len(tasks),
                    "personal_count": len(personal_tasks),
                    "bonus_pool_count": len(bonus_tasks),
                    "personal_amount": sum(t['commission'] for t in personal_tasks),
                    "bonus_pool_amount": sum(t['commission'] for t in bonus_tasks)
                }
            }
        )
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")

@router.post("/acceptTask")
async def accept_task(
    task_id: int = Query(..., description="任务ID"),
    student_id: int = Query(..., description="学生ID"),
    db: Session = Depends(get_db)
):
    """学生接取任务"""
    try:
        service = VirtualOrderService(db)
        result = service.accept_task(task_id, student_id)
        
        return ResponseSchema(
            code=200,
            message="任务接取成功",
            data=result
        )
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"接取任务失败: {str(e)}")

@router.get("/config")
async def get_bonus_pool_config(
    db: Session = Depends(get_db)
):
    """获取奖金池配置"""
    try:
        service = BonusPoolService(db)
        
        config = {
            "daily_achievement_target": service.get_daily_target(),
            "bonus_pool_enabled": service.is_bonus_pool_enabled()
        }
        
        return ResponseSchema(
            code=200,
            message="获取成功",
            data=config
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")

@router.put("/config")
async def update_bonus_pool_config(
    daily_target: Optional[float] = Query(None, description="每日达标金额"),
    enabled: Optional[bool] = Query(None, description="是否启用奖金池"),
    db: Session = Depends(get_db)
):
    """更新奖金池配置"""
    try:
        from shared.models.system_config import SystemConfig
        
        updated = []
        
        if daily_target is not None:
            config = db.query(SystemConfig).filter(
                SystemConfig.config_key == 'daily_achievement_target'
            ).first()
            
            if config:
                config.config_value = str(daily_target)
            else:
                config = SystemConfig(
                    config_key='daily_achievement_target',
                    config_value=str(daily_target),
                    config_type='number',
                    description='虚拟任务每日达标金额'
                )
                db.add(config)
            updated.append('daily_achievement_target')
        
        if enabled is not None:
            config = db.query(SystemConfig).filter(
                SystemConfig.config_key == 'bonus_pool_enabled'
            ).first()
            
            if config:
                config.config_value = 'true' if enabled else 'false'
            else:
                config = SystemConfig(
                    config_key='bonus_pool_enabled',
                    config_value='true' if enabled else 'false',
                    config_type='string',
                    description='是否启用奖金池功能'
                )
                db.add(config)
            updated.append('bonus_pool_enabled')
        
        db.commit()
        
        return ResponseSchema(
            code=200,
            message="配置更新成功",
            data={
                "updated_fields": updated
            }
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")