import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from shared.database.session import SessionLocal
from shared.models.tasks import Tasks
from shared.models.virtual_order_pool import VirtualOrderPool
from .virtual_order_service import VirtualOrderService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VirtualOrderTaskScheduler:
    """虚拟订单定时任务调度器"""

    def __init__(self):
        self.is_running = False
        # 设置执行间隔：每10分钟执行一次
        self.check_interval_minutes = 10
    
    async def start_scheduler(self):
        """启动定时任务调度器"""
        self.is_running = True
        logger.info(f"虚拟订单定时任务调度器已启动，每{self.check_interval_minutes}分钟执行一次")

        while self.is_running:
            try:
                # 执行过期任务检查
                if self.is_running:
                    await self.check_expired_tasks()

                # 等待指定间隔时间
                wait_seconds = self.check_interval_minutes * 60
                logger.info(f"下次执行时间: {(datetime.now() + timedelta(seconds=wait_seconds)).strftime('%Y-%m-%d %H:%M:%S')}, 等待 {wait_seconds} 秒")
                await asyncio.sleep(wait_seconds)

            except Exception as e:
                logger.error(f"定时任务执行出错: {str(e)}")
                # 出错后等待5分钟再重试
                await asyncio.sleep(300)
    
    def stop_scheduler(self):
        """停止定时任务调度器"""
        self.is_running = False
        logger.info("虚拟订单定时任务调度器已停止")

    def get_next_run_time(self) -> datetime:
        """计算下次执行时间"""
        # 现在改为间隔执行，直接返回当前时间加上间隔时间
        return datetime.now() + timedelta(minutes=self.check_interval_minutes)
    
    async def check_expired_tasks(self):
        """检查并处理过期的虚拟任务"""
        db = SessionLocal()
        try:
            logger.info("开始检查过期的虚拟任务...")

            # 查找接单截止时间已过的虚拟任务，排除状态为1、2、4的任务
            current_time = datetime.now()

            expired_tasks = db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual == True,
                    Tasks.status.notin_(['1', '2', '4']),  # 排除状态为1、2、4的任务
                    Tasks.end_date <= current_time  # 接单截止时间已过
                )
            ).all()

            if not expired_tasks:
                logger.info("没有发现需要处理的过期虚拟任务")
                return

            logger.info(f"发现 {len(expired_tasks)} 个需要处理的过期虚拟任务")

            # 按学生分组处理过期任务
            student_expired_tasks = {}
            for task in expired_tasks:
                # 使用target_student_id来关联学生
                student_id = task.target_student_id
                if student_id and student_id not in student_expired_tasks:
                    student_expired_tasks[student_id] = []
                if student_id:
                    student_expired_tasks[student_id].append(task)

            service = VirtualOrderService(db)

            for student_id, tasks in student_expired_tasks.items():
                try:
                    await self.process_expired_tasks_for_student(db, service, student_id, tasks)
                except Exception as e:
                    logger.error(f"处理学生 {student_id} 的过期任务失败: {str(e)}")

            db.commit()
            logger.info("过期任务处理完成")

        except Exception as e:
            db.rollback()
            logger.error(f"检查过期任务失败: {str(e)}")
        finally:
            db.close()
    
    async def process_expired_tasks_for_student(self, db: Session, service: VirtualOrderService, 
                                              student_id: int, expired_tasks: List[Tasks]):
        """处理单个学生的过期任务"""
        try:
            # 获取学生补贴池
            pool = db.query(VirtualOrderPool).filter(
                VirtualOrderPool.student_id == student_id
            ).first()
            
            if not pool:
                logger.warning(f"未找到学生 {student_id} 的补贴池")
                return
            
            # 计算过期任务的总金额
            expired_amount = sum(task.commission for task in expired_tasks)
            
            # 记录过期任务的状态信息
            task_status_info = {}
            for task in expired_tasks:
                status = task.status
                if status not in task_status_info:
                    task_status_info[status] = 0
                task_status_info[status] += 1

            logger.info(f"学生 {pool.student_name} 有 {len(expired_tasks)} 个过期任务，总金额: {expired_amount}")
            logger.info(f"任务状态分布: {task_status_info}")

            # 删除过期任务（排除状态为1、2、4的任务）
            for task in expired_tasks:
                logger.info(f"删除过期任务: ID={task.id}, 状态={task.status}, 金额={task.commission}")
                db.delete(task)

            # 将过期金额从已分配金额中减去，返还到剩余可分配金额
            pool.allocated_amount -= expired_amount
            pool.remaining_amount += expired_amount
            pool.updated_at = datetime.now()

            # 重新生成任务（使用当前剩余可分配金额）
            if pool.remaining_amount > 0:
                new_tasks = service.generate_virtual_tasks_for_student(
                    student_id, pool.student_name, pool.remaining_amount
                )

                # 计算新任务的总金额
                new_tasks_total_amount = sum(task.commission for task in new_tasks)

                # 保存新任务
                for task in new_tasks:
                    db.add(task)

                # 更新补贴池状态：新任务金额从剩余金额转移到已分配金额
                pool.remaining_amount -= new_tasks_total_amount
                pool.allocated_amount += new_tasks_total_amount
                pool.last_allocation_at = datetime.now()

                logger.info(f"为学生 {pool.student_name} 重新生成了 {len(new_tasks)} 个任务，总金额: {new_tasks_total_amount}")
                logger.info(f"补贴池状态更新 - 总补贴: {pool.total_subsidy}, 已分配: {pool.allocated_amount}, 剩余: {pool.remaining_amount}, 已完成: {pool.completed_amount}")
            
        except Exception as e:
            logger.error(f"处理学生 {student_id} 的过期任务时出错: {str(e)}")
            raise
    
    async def manual_check_expired_tasks(self):
        """手动触发过期任务检查（用于测试或手动执行）"""
        logger.info("手动触发过期任务检查")
        await self.check_expired_tasks()

# 全局调度器实例
scheduler = VirtualOrderTaskScheduler()

async def start_background_tasks():
    """启动后台任务"""
    await scheduler.start_scheduler()

def stop_background_tasks():
    """停止后台任务"""
    scheduler.stop_scheduler()

async def manual_check_expired():
    """手动检查过期任务的接口"""
    await scheduler.manual_check_expired_tasks()
