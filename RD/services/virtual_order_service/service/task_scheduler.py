import asyncio
import logging
from datetime import datetime, timedelta, date, time
from typing import List
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_

from shared.database.session import SessionLocal
from shared.models.tasks import Tasks
from shared.models.virtual_order_pool import VirtualOrderPool
from .virtual_order_service import VirtualOrderService
from .bonus_pool_service import BonusPoolService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VirtualOrderTaskScheduler:
    """虚拟订单定时任务调度器"""

    def __init__(self):
        self.is_running = False
        # 设置执行间隔：每5分钟执行一次
        self.check_interval_minutes = 5
        # 记录上次执行每日任务的日期
        self.last_daily_task_date = None
        # 奖金池任务检查间隔（3小时）
        self.bonus_pool_check_interval_hours = 3
        self.last_bonus_pool_check_time = None
    
    async def start_scheduler(self):
        """启动定时任务调度器"""
        self.is_running = True
        logger.info(f"虚拟订单定时任务调度器已启动，每{self.check_interval_minutes}分钟执行一次")

        while self.is_running:
            try:
                current_time = datetime.now()
                
                # 1. 检查是否需要执行每日任务（凌晨0点）
                if self.should_run_daily_task(current_time):
                    await self.run_daily_bonus_pool_task()
                    self.last_daily_task_date = date.today()
                
                # 2. 检查是否需要处理奖金池过期任务（每3小时）
                if self.should_run_bonus_pool_check(current_time):
                    await self.check_expired_bonus_pool_tasks()
                    self.last_bonus_pool_check_time = current_time
                
                # 3. 执行普通过期任务检查
                if self.is_running:
                    await self.check_expired_tasks()

                # 4. 执行价值回收任务检查（每5分钟）
                if self.is_running:
                    await self.check_value_recycling()

                # 5. 执行自动确认任务检查（每5分钟）
                if self.is_running:
                    await self.check_auto_confirm_tasks()

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
                    Tasks.status.notin_(['1', '2', '3', '4']),  # 排除状态为1、2、3、4的任务
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
            # 获取学生补贴池（只查询未删除的记录）
            pool = db.query(VirtualOrderPool).filter(
                VirtualOrderPool.student_id == student_id,
                VirtualOrderPool.is_deleted == False
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

                # 先清理图片引用，避免外键约束错误
                try:
                    from shared.models.resource_images import ResourceImages
                    # 将引用该任务的图片的used_in_task_id设为NULL
                    db.query(ResourceImages).filter(
                        ResourceImages.used_in_task_id == task.id
                    ).update({
                        'used_in_task_id': None,
                        'updated_at': datetime.now()
                    })
                    db.flush()  # 确保更新生效
                except Exception as img_error:
                    logger.warning(f"清理任务 {task.id} 的图片引用失败: {str(img_error)}")

                # 删除任务
                db.delete(task)

            # 重新计算剩余金额（基于实际消耗的补贴）
            pool.remaining_amount = pool.total_subsidy - pool.consumed_subsidy
            pool.updated_at = datetime.now()
            
            # 计算应该生成的任务金额（剩余金额）
            amount_to_generate = pool.remaining_amount
            
            # 重新生成任务
            if amount_to_generate > 0:
                # 优先使用新的虚拟客服分配策略
                try:
                    result = service.generate_virtual_tasks_with_service_allocation(
                        student_id, pool.student_name, amount_to_generate
                    )
                    
                    if result['success']:
                        new_tasks_count = len(result['tasks'])
                        new_tasks_total_amount = result['total_amount']
                        logger.info(f"使用虚拟客服分配策略为学生 {pool.student_name} 重新生成了 {new_tasks_count} 个任务，总金额: {new_tasks_total_amount}")
                    else:
                        # 如果新策略失败，回退到原有方式
                        logger.warning(f"虚拟客服分配策略失败: {result['message']}，回退到原有方式")
                        new_tasks = service.generate_virtual_tasks_for_student(
                            student_id, pool.student_name, amount_to_generate
                        )
                        
                        # 保存新任务
                        for task in new_tasks:
                            db.add(task)
                        
                        new_tasks_total_amount = sum(task.commission for task in new_tasks)
                        logger.info(f"使用原有方式为学生 {pool.student_name} 重新生成了 {len(new_tasks)} 个任务，总金额: {new_tasks_total_amount}")
                        
                except Exception as e:
                    # 如果新策略出错，回退到原有方式
                    logger.error(f"虚拟客服分配策略出错: {e}，回退到原有方式")
                    new_tasks = service.generate_virtual_tasks_for_student(
                        student_id, pool.student_name, amount_to_generate
                    )
                    
                    # 保存新任务
                    for task in new_tasks:
                        db.add(task)
                    
                    new_tasks_total_amount = sum(task.commission for task in new_tasks)
                    logger.info(f"使用原有方式为学生 {pool.student_name} 重新生成了 {len(new_tasks)} 个任务，总金额: {new_tasks_total_amount}")

                # 已分配金额不需要更新（始终等于总补贴金额）
                # pool.allocated_amount 保持不变
                pool.last_allocation_at = datetime.now()

                logger.info(f"补贴池状态更新 - 总补贴: {pool.total_subsidy}, 已分配: {pool.allocated_amount}, 剩余: {pool.remaining_amount}, 已完成: {pool.completed_amount}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"处理学生 {student_id} 的过期任务失败: {str(e)}")
            raise
    
    def should_run_daily_task(self, current_time: datetime) -> bool:
        """判断是否应该执行每日任务"""
        # 检查是否在凌晨0点到0点30分之间
        if current_time.time() >= time(0, 0) and current_time.time() <= time(0, 30):
            # 检查今天是否已经执行过
            if self.last_daily_task_date != date.today():
                return True
        return False
    
    def should_run_bonus_pool_check(self, current_time: datetime) -> bool:
        """判断是否应该检查奖金池过期任务"""
        if self.last_bonus_pool_check_time is None:
            return True
        
        # 检查距离上次执行是否超过3小时
        time_diff = current_time - self.last_bonus_pool_check_time
        if time_diff.total_seconds() >= self.bonus_pool_check_interval_hours * 3600:
            return True
        return False
    
    async def run_daily_bonus_pool_task(self):
        """执行每日奖金池任务"""
        db = SessionLocal()
        try:
            logger.info("开始执行每日奖金池任务...")
            bonus_service = BonusPoolService(db)
            
            # 0. 重置所有学生的当日完成金额（新的一天开始）
            from shared.models.virtual_order_pool import VirtualOrderPool
            pools = db.query(VirtualOrderPool).filter(
                VirtualOrderPool.status == 'active'
            ).all()
            for pool in pools:
                pool.completed_amount = Decimal('0')
                pool.consumed_subsidy = Decimal('0')  # 重置实际消耗的补贴
                pool.remaining_amount = pool.total_subsidy  # 重置为每日补贴金额
                logger.info(f"学生 {pool.student_name} 每日数据已重置: 每日补贴={pool.total_subsidy}")
            
            # 1. 更新昨天的学生达标记录
            yesterday = date.today() - timedelta(days=1)
            achievement_result = bonus_service.update_daily_achievements(yesterday)
            logger.info(f"学生达标统计完成: {achievement_result}")
            
            # 2. 创建或更新今日奖金池
            today_pool = bonus_service.create_or_update_bonus_pool()
            logger.info(f"今日奖金池已创建/更新: 总金额={today_pool.total_amount}")
            
            # 3. 生成奖金池任务
            if today_pool.remaining_amount > 0:
                generate_result = bonus_service.generate_bonus_pool_tasks()
                logger.info(f"奖金池任务生成结果: {generate_result}")
            
            db.commit()
            logger.info("每日奖金池任务执行完成")
            
        except Exception as e:
            logger.error(f"执行每日奖金池任务失败: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    async def check_expired_bonus_pool_tasks(self):
        """检查并处理过期的奖金池任务"""
        db = SessionLocal()
        try:
            logger.info("开始检查过期的奖金池任务...")
            bonus_service = BonusPoolService(db)
            
            # 处理过期的奖金池任务
            result = bonus_service.process_expired_bonus_tasks()
            logger.info(f"过期奖金池任务处理结果: {result}")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"处理过期奖金池任务失败: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    async def manual_check_expired_tasks(self):
        """手动触发过期任务检查（用于测试或手动执行）"""
        logger.info("手动触发过期任务检查")
        await self.check_expired_tasks()
    
    async def manual_run_daily_bonus_pool(self):
        """手动触发每日奖金池任务（用于测试）"""
        logger.info("手动触发每日奖金池任务")
        await self.run_daily_bonus_pool_task()
        self.last_daily_task_date = date.today()

    async def check_value_recycling(self):
        """检查并处理需要价值回收的已完成虚拟任务"""
        db = SessionLocal()
        try:
            logger.info("开始检查需要价值回收的已完成虚拟任务...")

            # 查找最近5分钟内完成且未回收价值的虚拟任务
            five_minutes_ago = datetime.now() - timedelta(minutes=5)

            completed_tasks = db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual == True,
                    Tasks.status == '4',  # 已完成状态
                    Tasks.value_recycled == False,  # 未回收价值
                    Tasks.updated_at >= five_minutes_ago,  # 最近5分钟内更新的
                    Tasks.target_student_id.isnot(None)  # 有目标学生的任务
                )
            ).all()

            if not completed_tasks:
                logger.info("没有发现需要价值回收的已完成虚拟任务")
                return

            logger.info(f"发现 {len(completed_tasks)} 个需要价值回收的已完成虚拟任务")

            # 按学生分组处理
            student_recycled_values = {}
            service = VirtualOrderService(db)

            for task in completed_tasks:
                student_id = task.target_student_id

                # 计算回收价值
                rebate_rate = service.get_student_rebate_rate(student_id)
                student_income = task.commission * rebate_rate  # 学生实际获得的收益
                recycled_value = task.commission - student_income  # 回收的价值

                # 标记任务已回收
                task.value_recycled = True
                task.recycled_at = datetime.now()

                # 累计该学生的回收价值
                if student_id not in student_recycled_values:
                    student_recycled_values[student_id] = {
                        'student_name': '',
                        'recycled_amount': Decimal('0'),
                        'task_count': 0
                    }

                student_recycled_values[student_id]['recycled_amount'] += recycled_value
                student_recycled_values[student_id]['task_count'] += 1

                logger.info(f"任务 {task.id} 回收价值: {recycled_value}元 (任务面值: {task.commission}, 学生收益: {student_income})")

            # 为每个学生重新生成任务
            for student_id, recycled_info in student_recycled_values.items():
                try:
                    await self.process_value_recycling_for_student(
                        db, service, student_id, recycled_info['recycled_amount']
                    )
                except Exception as e:
                    logger.error(f"处理学生 {student_id} 的价值回收失败: {str(e)}")

            db.commit()
            logger.info("价值回收处理完成")

        except Exception as e:
            db.rollback()
            logger.error(f"价值回收检查失败: {str(e)}")
        finally:
            db.close()

    async def process_value_recycling_for_student(self, db: Session, service: VirtualOrderService,
                                                student_id: int, recycled_amount: Decimal):
        """处理单个学生的价值回收"""
        try:
            # 获取学生补贴池
            pool = db.query(VirtualOrderPool).filter(
                VirtualOrderPool.student_id == student_id,
                VirtualOrderPool.is_deleted == False
            ).first()

            if not pool:
                logger.warning(f"未找到学生 {student_id} 的补贴池")
                return

            # 计算总可用金额：剩余补贴 + 回收价值
            total_available = pool.remaining_amount + recycled_amount

            logger.info(f"学生 {pool.student_name} 价值回收: 回收金额 {recycled_amount}, 剩余补贴 {pool.remaining_amount}, 总可用 {total_available}")

            # 如果总可用金额大于0，重新生成任务
            if total_available > 0:
                # 优先使用新的虚拟客服分配策略
                try:
                    result = service.generate_virtual_tasks_with_service_allocation(
                        student_id, pool.student_name, total_available
                    )

                    if result['success']:
                        # 更新补贴池：将回收价值加入剩余金额
                        pool.remaining_amount = total_available
                        pool.updated_at = datetime.now()

                        logger.info(f"使用虚拟客服分配策略为学生 {pool.student_name} 重新生成了 {len(result['tasks'])} 个任务，总金额: {result['total_amount']}")
                    else:
                        logger.error(f"虚拟客服分配策略失败: {result['message']}")

                except Exception as e:
                    # 如果新策略出错，回退到原有方式
                    logger.error(f"虚拟客服分配策略出错: {e}，回退到原有方式")
                    new_tasks = service.generate_virtual_tasks_for_student(
                        student_id, pool.student_name, total_available
                    )

                    # 保存新任务
                    for task in new_tasks:
                        db.add(task)

                    # 更新补贴池：将回收价值加入剩余金额
                    pool.remaining_amount = total_available
                    pool.updated_at = datetime.now()

                    new_tasks_total_amount = sum(task.commission for task in new_tasks)
                    logger.info(f"使用原有方式为学生 {pool.student_name} 重新生成了 {len(new_tasks)} 个任务，总金额: {new_tasks_total_amount}")

        except Exception as e:
            logger.error(f"处理学生 {student_id} 的价值回收时出错: {str(e)}")
            raise
    
    async def manual_check_bonus_pool_tasks(self):
        """手动触发奖金池过期任务检查（用于测试）"""
        logger.info("手动触发奖金池过期任务检查")
        await self.check_expired_bonus_pool_tasks()
        self.last_bonus_pool_check_time = datetime.now()

    async def check_auto_confirm_tasks(self):
        """检查并自动确认提交超过配置时间的虚拟任务"""
        db = SessionLocal()
        try:
            logger.info("开始检查需要自动确认的虚拟任务...")

            # 导入相关模型和服务
            from shared.models.studenttask import StudentTask
            from .config_service import ConfigService

            # 获取配置
            config_service = ConfigService(db)
            auto_confirm_config = config_service.get_auto_confirm_config()

            # 检查是否启用自动确认
            if not auto_confirm_config['enabled']:
                logger.info("自动确认功能已禁用")
                return

            # 获取配置的时间间隔
            interval_hours = auto_confirm_config['interval_hours']
            max_batch_size = auto_confirm_config['max_batch_size']

            # 计算截止时间点
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=interval_hours)
            logger.info(f"自动确认配置: 间隔={interval_hours}小时, 最大批次={max_batch_size}")
            logger.info(f"时间信息: 当前时间={current_time}, 截止时间={cutoff_time}")
            logger.info(f"逻辑说明: 只有提交时间 <= {cutoff_time} 的任务才会被处理")

            # 调试信息已移除，直接执行查询

            # 查找提交超过配置时间且对应虚拟任务未完成的记录
            # 注意：使用creation_time字段，需要转换为datetime进行比较
            from sqlalchemy import func, cast, DateTime

            pending_submissions = db.query(StudentTask).join(
                Tasks, StudentTask.task_id == Tasks.id
            ).filter(
                and_(
                    # 使用creation_time字段，转换为datetime进行比较
                    func.STR_TO_DATE(StudentTask.creation_time, '%Y-%m-%d %H:%i:%s') <= cutoff_time,
                    StudentTask.content.isnot(None),  # 确实有提交内容
                    Tasks.is_virtual == True,  # 是虚拟任务
                    Tasks.status.notin_(['4', '5']),  # 排除已完成(4)和终止(5)状态，其他状态都可以
                    Tasks.target_student_id.isnot(None)  # 有目标学生
                )
            ).limit(max_batch_size).all()  # 限制批次大小

            if not pending_submissions:
                logger.info("没有发现需要自动确认的虚拟任务")
                return

            logger.info(f"发现 {len(pending_submissions)} 个需要自动确认的虚拟任务")

            # 使用虚拟订单服务进行自动确认
            service = VirtualOrderService(db)
            confirmed_count = 0

            for submission in pending_submissions:
                try:
                    # 调用现有的任务完成方法
                    result = service.update_virtual_task_completion(submission.task_id)
                    logger.info(f"自动确认任务成功: task_id={submission.task_id}, student_id={result.get('student_id')}, commission={result.get('task_commission')}")
                    confirmed_count += 1

                except Exception as e:
                    logger.error(f"自动确认任务失败: task_id={submission.task_id}, error={str(e)}")
                    continue

            logger.info(f"自动确认任务完成，成功确认 {confirmed_count} 个任务")

        except Exception as e:
            logger.error(f"检查自动确认任务失败: {str(e)}")
        finally:
            db.close()

    async def manual_check_auto_confirm_tasks(self):
        """手动触发自动确认任务检查（用于测试）"""
        logger.info("手动触发自动确认任务检查")
        await self.check_auto_confirm_tasks()

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

async def manual_check_auto_confirm():
    """手动检查自动确认任务的接口"""
    await scheduler.manual_check_auto_confirm_tasks()
