import asyncio
import logging
from datetime import datetime, timedelta, date, time
from typing import List
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, text

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
        # 价值回收检查间隔（2.5分钟）
        self.value_recycling_interval_minutes = 2.5
        self.last_value_recycling_check_time = None
        # 记录上次执行每日任务的日期
        self.last_daily_task_date = None
        # 奖金池任务检查间隔（3小时）
        self.bonus_pool_check_interval_hours = 3
        self.last_bonus_pool_check_time = None
    
    async def start_scheduler(self):
        """启动定时任务调度器"""
        self.is_running = True
        logger.info(f"虚拟订单定时任务调度器已启动")
        logger.info(f"主任务循环：每{self.check_interval_minutes}分钟执行一次")
        logger.info(f"价值回收任务：每{self.value_recycling_interval_minutes}分钟执行一次")

        # 启动独立的价值回收任务
        value_recycling_task = asyncio.create_task(self._value_recycling_loop())

        try:
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

                    # 4. 执行自动确认任务检查（每5分钟）
                    if self.is_running:
                        await self.check_auto_confirm_tasks()

                    # 等待指定间隔时间
                    wait_seconds = self.check_interval_minutes * 60
                    logger.info(f"主任务下次执行时间: {(datetime.now() + timedelta(seconds=wait_seconds)).strftime('%Y-%m-%d %H:%M:%S')}, 等待 {wait_seconds} 秒")
                    await asyncio.sleep(wait_seconds)

                except Exception as e:
                    logger.error(f"主任务循环执行出错: {str(e)}")
                    # 出错后等待5分钟再重试
                    await asyncio.sleep(300)
        finally:
            # 停止价值回收任务
            value_recycling_task.cancel()
            try:
                await value_recycling_task
            except asyncio.CancelledError:
                pass

    async def _value_recycling_loop(self):
        """独立的价值回收循环"""
        logger.info(f"价值回收任务循环已启动，每{self.value_recycling_interval_minutes}分钟执行一次")

        while self.is_running:
            try:
                await self.check_value_recycling()

                # 等待2.5分钟
                wait_seconds = self.value_recycling_interval_minutes * 60
                logger.info(f"价值回收下次执行时间: {(datetime.now() + timedelta(seconds=wait_seconds)).strftime('%Y-%m-%d %H:%M:%S')}, 等待 {wait_seconds} 秒")
                await asyncio.sleep(wait_seconds)

            except Exception as e:
                logger.error(f"价值回收任务执行出错: {str(e)}")
                # 出错后等待2.5分钟再重试
                await asyncio.sleep(self.value_recycling_interval_minutes * 60)
    
    def stop_scheduler(self):
        """停止定时任务调度器"""
        self.is_running = False
        logger.info("虚拟订单定时任务调度器已停止")

    def get_next_run_time(self) -> datetime:
        """计算下次执行时间"""
        # 现在改为间隔执行，直接返回当前时间加上间隔时间
        return datetime.now() + timedelta(minutes=self.check_interval_minutes)
    
    async def check_expired_tasks(self):
        """检查并处理过期的虚拟任务（每5分钟执行）"""
        db = SessionLocal()
        try:
            logger.info("开始执行定时过期任务检查（5分钟周期）...")

            # 检查虚拟任务生成是否启用
            from .config_service import ConfigService
            config_service = ConfigService(db)
            generation_config = config_service.get_virtual_task_generation_config()

            if not generation_config['enabled'] or not generation_config['expired_task_regeneration_enabled']:
                logger.info("虚拟任务生成或过期任务重新生成已禁用，跳过过期任务重新生成")
                # 仍然需要处理过期任务的状态更新，但不重新生成
                await self.mark_expired_tasks_only(db)
                return

            # 使用新的方法获取所有过期任务（包括状态2的特殊处理）
            current_time = datetime.now()
            expired_tasks = self._get_all_expired_virtual_tasks(db, current_time)

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

            # 删除过期任务并释放金额回补贴池
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

            # 释放过期任务金额回补贴池
            if expired_amount > 0:
                old_remaining = pool.remaining_amount
                # 修复：使用正确的计算公式，而不是简单加法
                # remaining_amount = total_subsidy - completed_amount
                pool.remaining_amount = pool.total_subsidy - pool.completed_amount

                # 确保剩余金额不超过总补贴金额
                if pool.remaining_amount > pool.total_subsidy:
                    pool.remaining_amount = pool.total_subsidy

                logger.info(f"释放过期任务金额 {expired_amount} 回补贴池，剩余金额: {old_remaining} → {pool.remaining_amount} (基于公式: {pool.total_subsidy} - {pool.completed_amount})")

            # 按需生成逻辑：过期任务1:1严格替换
            # 过期几个任务就生成几个任务，不考虑金额
            expired_task_count = len(expired_tasks)

            logger.info(f"学生 {pool.student_name} 过期任务重新生成: 过期 {expired_task_count} 个任务，将生成 {expired_task_count} 个新任务")

            # 重新生成任务（1:1替换）
            if expired_task_count > 0:
                # 过期任务重新生成使用与价值回收相同的规则
                # - 剩余补贴 < 8元：生成5元任务
                # - 剩余补贴 >= 8元：生成10元任务
                if pool.remaining_amount < Decimal('8'):
                    task_amount = Decimal('5')
                else:
                    task_amount = Decimal('10')

                logger.info(f"学生 {pool.student_name} 过期任务重新生成规则：剩余补贴 {pool.remaining_amount}元，生成 {task_amount}元 任务")

                # 按需生成指定数量的任务（1:1替换）
                generated_tasks_count = 0
                total_generated_amount = Decimal('0')

                for i in range(expired_task_count):
                    # 每次生成1个任务，使用虚拟客服分配策略
                    result = service.generate_virtual_tasks_with_service_allocation(
                        student_id, pool.student_name, task_amount, on_demand=True
                    )

                    if result['success'] and result['tasks']:
                        # 只取第一个任务的金额（确保1:1替换）
                        actual_task_amount = Decimal(str(result['tasks'][0]['amount']))
                        generated_tasks_count += 1
                        total_generated_amount += actual_task_amount

                        logger.info(f"为学生 {pool.student_name} 重新生成任务 {i+1}/{expired_task_count}，金额: {actual_task_amount}")
                    else:
                        logger.warning(f"为学生 {pool.student_name} 生成第 {i+1} 个任务失败")
                        break

                # 更新补贴池剩余金额
                if generated_tasks_count > 0:
                    pool.remaining_amount -= total_generated_amount

                    # 确保剩余金额不为负数
                    if pool.remaining_amount < 0:
                        pool.remaining_amount = Decimal('0')

                    pool.updated_at = datetime.now()

                    logger.info(f"为学生 {pool.student_name} 重新生成了 {generated_tasks_count} 个任务（1:1替换），总金额: {total_generated_amount}，剩余: {pool.remaining_amount}")
                else:
                    logger.warning(f"为学生 {pool.student_name} 过期任务重新生成失败")

                # 已分配金额不需要更新（始终等于总补贴金额）
                # pool.allocated_amount 保持不变
                pool.last_allocation_at = datetime.now()

                logger.info(f"补贴池状态更新 - 总补贴: {pool.total_subsidy}, 已分配: {pool.allocated_amount}, 剩余: {pool.remaining_amount}, 已完成: {pool.completed_amount}")
            else:
                logger.info(f"学生 {pool.student_name} 当日补贴额度已满，跳过过期任务重新生成")

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

    def _check_status_2_task_expired(self, db: Session, task: Tasks) -> bool:
        """
        检查状态为2的任务是否真的过期（保守策略）

        Args:
            db: 数据库会话
            task: 任务对象

        Returns:
            bool: 是否过期（只有没有提交记录且已过交稿时间才返回True）
        """
        # 检查交稿时间是否已过
        if not task.delivery_date or task.delivery_date > datetime.now():
            return False

        # 检查是否有提交记录
        from shared.models.studenttask import StudentTask
        submission = db.query(StudentTask).filter(
            StudentTask.task_id == task.id,
            StudentTask.content.isnot(None)
        ).first()

        if submission:
            # 有提交记录，记录日志但不删除，让自动确认机制处理
            from .config_service import ConfigService
            config_service = ConfigService(db)
            auto_confirm_config = config_service.get_auto_confirm_config()

            logger.warning(f"发现状态为2但有提交记录的任务: task_id={task.id}, "
                          f"submission_time={submission.creation_time}, "
                          f"delivery_date={task.delivery_date}, "
                          f"auto_confirm_enabled={auto_confirm_config['enabled']}, "
                          f"建议检查自动确认机制")
            return False
        else:
            # 没有提交记录且已过交稿时间，视为过期
            logger.info(f"状态为2的过期任务（无提交记录）: task_id={task.id}, "
                       f"delivery_date={task.delivery_date}")
            return True

    def _get_all_expired_virtual_tasks(self, db: Session, current_time: datetime) -> List[Tasks]:
        """
        获取所有过期的虚拟任务，包括状态为2但实际过期的任务
        注意：只检查今天的任务，昨天及更早的任务已在凌晨清理

        Args:
            db: 数据库会话
            current_time: 当前时间

        Returns:
            List[Tasks]: 过期任务列表
        """
        # 只检查今天的任务，昨天的任务已在凌晨清理
        today = current_time.date()

        # 1. 常规过期任务（排除状态为1、2、3、4的任务，排除奖金池任务）
        regular_expired = db.query(Tasks).filter(
            and_(
                Tasks.is_virtual == True,
                Tasks.is_bonus_pool == False,  # 排除奖金池任务
                func.date(Tasks.created_at) == today,  # 只检查今天的任务
                Tasks.status.notin_(['1', '2', '3', '4']),
                Tasks.end_date <= current_time
            )
        ).all()

        # 2. 状态为2的可能过期任务（使用交稿时间判断，排除奖金池任务）
        status_2_candidates = db.query(Tasks).filter(
            and_(
                Tasks.is_virtual == True,
                Tasks.is_bonus_pool == False,  # 排除奖金池任务
                func.date(Tasks.created_at) == today,  # 只检查今天的任务
                Tasks.status == '2',
                Tasks.delivery_date <= current_time
            )
        ).all()

        # 3. 验证状态为2的任务（保守策略：只删除无提交记录的）
        verified_status_2_expired = [
            task for task in status_2_candidates
            if self._check_status_2_task_expired(db, task)
        ]

        logger.info(f"过期任务统计: 常规过期={len(regular_expired)}, "
                   f"状态2候选={len(status_2_candidates)}, "
                   f"状态2确认过期={len(verified_status_2_expired)}")

        return regular_expired + verified_status_2_expired

    async def mark_expired_tasks_only(self, db: Session):
        """仅标记过期任务状态，不重新生成任务"""
        try:
            current_time = datetime.now()
            # 使用新的方法获取所有过期任务
            expired_tasks = self._get_all_expired_virtual_tasks(db, current_time)

            if expired_tasks:
                for task in expired_tasks:
                    task.status = '5'  # 标记为过期状态
                    task.updated_at = current_time

                db.commit()
                logger.info(f"已标记 {len(expired_tasks)} 个过期虚拟任务为过期状态")
            else:
                logger.info("没有发现需要标记的过期虚拟任务")

        except Exception as e:
            logger.error(f"标记过期任务失败: {str(e)}")
            db.rollback()

    async def mark_value_recycled_only(self, db: Session):
        """仅标记已完成任务为已回收，不重新生成任务"""
        try:
            five_minutes_ago = datetime.now() - timedelta(minutes=5)
            completed_tasks = db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual == True,
                    Tasks.is_bonus_pool == False,  # 排除奖金池任务
                    Tasks.status == '4',  # 已完成状态
                    Tasks.value_recycled == False,  # 未回收价值
                    Tasks.updated_at >= five_minutes_ago,  # 最近5分钟内更新的
                    Tasks.target_student_id.isnot(None)  # 有目标学生的任务
                )
            ).all()

            if completed_tasks:
                for task in completed_tasks:
                    task.value_recycled = True
                    task.updated_at = datetime.now()

                db.commit()
                logger.info(f"已标记 {len(completed_tasks)} 个已完成虚拟任务为已回收状态")
            else:
                logger.info("没有发现需要标记的已完成虚拟任务")

        except Exception as e:
            logger.error(f"标记价值回收失败: {str(e)}")
            db.rollback()

    async def run_daily_bonus_pool_task(self):
        """执行每日奖金池任务"""
        db = SessionLocal()
        try:
            logger.info("开始执行每日奖金池任务...")

            # 检查虚拟任务生成是否启用
            from .config_service import ConfigService
            config_service = ConfigService(db)
            generation_config = config_service.get_virtual_task_generation_config()

            if not generation_config['enabled'] or not generation_config['daily_bonus_enabled']:
                logger.info("虚拟任务生成或每日奖金池任务已禁用，跳过每日奖金池任务")
                return

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

            # 2.1 处理昨天进行中的任务（status=1,2）
            in_progress_cleanup_amount = await self._process_in_progress_tasks(db, yesterday)

            # 2.2 删除昨天所有未接取的任务（status=0）
            unaccepted_cleanup_amount = await self._cleanup_unaccepted_tasks(db, yesterday)

            # 2.3 更新奖金池金额（将清理的金额加入奖金池）
            total_cleanup_amount = in_progress_cleanup_amount + unaccepted_cleanup_amount
            if total_cleanup_amount > 0:
                await self._update_bonus_pool_with_cleanup_amount(db, today_pool, total_cleanup_amount)
                logger.info(f"昨日任务清理完成: 进行中任务清理 {in_progress_cleanup_amount} 元，未接取任务清理 {unaccepted_cleanup_amount} 元，总计 {total_cleanup_amount} 元")

            # 3. 为所有有补贴的学生生成个人补贴任务（使用虚拟客服分配策略）
            logger.info("开始为学生生成个人补贴任务...")
            from .virtual_order_service import VirtualOrderService
            virtual_service = VirtualOrderService(db)

            generated_personal_tasks = 0
            for pool in pools:
                if pool.remaining_amount > 0:
                    try:
                        # 使用虚拟客服分配策略生成个人补贴任务（按需生成）
                        result = virtual_service.generate_virtual_tasks_with_service_allocation(
                            pool.student_id, pool.student_name, pool.remaining_amount, on_demand=True
                        )

                        if result['success']:
                            generated_personal_tasks += len(result['tasks'])
                            logger.info(f"为学生 {pool.student_name} 生成了 {len(result['tasks'])} 个个人补贴任务")
                        else:
                            logger.error(f"为学生 {pool.student_name} 生成个人补贴任务失败: {result['message']}")

                    except Exception as e:
                        logger.error(f"为学生 {pool.student_name} 生成个人补贴任务失败: {str(e)}")
                        continue

            logger.info(f"个人补贴任务生成完成，共生成 {generated_personal_tasks} 个任务")

            # 4. 生成初始奖金池任务（按需生成1-2个）
            if today_pool.remaining_amount > 0:
                generate_result = bonus_service.generate_bonus_pool_tasks()
                logger.info(f"奖金池初始任务生成结果: {generate_result}")

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

            # 检查虚拟任务生成是否启用
            from .config_service import ConfigService
            config_service = ConfigService(db)
            generation_config = config_service.get_virtual_task_generation_config()

            if not generation_config['enabled'] or not generation_config['bonus_pool_task_enabled']:
                logger.info("虚拟任务生成或奖金池任务已禁用，跳过奖金池过期任务处理")
                return

            bonus_service = BonusPoolService(db)

            # 处理过期的奖金池任务（删除并重新生成）
            expired_result = bonus_service.process_expired_bonus_tasks()
            logger.info(f"过期奖金池任务处理结果: {expired_result}")

            # 处理已完成的奖金池任务（重新生成新任务）
            completed_result = bonus_service.process_completed_bonus_tasks()
            logger.info(f"已完成奖金池任务处理结果: {completed_result}")
            
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

            # 检查虚拟任务生成是否启用
            from .config_service import ConfigService
            config_service = ConfigService(db)
            generation_config = config_service.get_virtual_task_generation_config()

            if not generation_config['enabled'] or not generation_config['value_recycling_enabled']:
                logger.info("虚拟任务生成或价值回收任务生成已禁用，跳过价值回收任务生成")
                # 仍然需要标记任务为已回收，但不重新生成任务
                await self.mark_value_recycled_only(db)
                return

            # 查找所有未回收价值的已完成虚拟任务（排除奖金池任务）
            # 移除时间限制，确保服务中断后重启时能处理所有积压的任务
            completed_tasks = db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual == True,
                    Tasks.is_bonus_pool == False,  # 排除奖金池任务
                    Tasks.status == '4',  # 已完成状态
                    Tasks.value_recycled == False,  # 未回收价值
                    Tasks.target_student_id.isnot(None)  # 有目标学生的任务
                )
            ).order_by(Tasks.updated_at.asc()).limit(50).all()  # 限制批次大小，按时间顺序处理

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

            # 价值回收：基于补贴池剩余金额生成1-2个任务
            logger.info(f"学生 {pool.student_name} 价值回收: 剩余补贴 {pool.remaining_amount}")

            # 检查是否还有剩余补贴额度
            if pool.remaining_amount <= 0:
                logger.info(f"学生 {pool.student_name} 当日补贴已用完，跳过价值回收任务生成")
                return

            # 价值回收任务金额规则：
            # - 剩余补贴 < 8元：生成5元任务
            # - 剩余补贴 >= 8元：生成10元任务
            if pool.remaining_amount < Decimal('8'):
                task_amount = Decimal('5')
            else:
                task_amount = Decimal('10')

            logger.info(f"学生 {pool.student_name} 价值回收规则：剩余补贴 {pool.remaining_amount}元，生成 {task_amount}元 任务")

            # 使用虚拟客服分配策略生成指定金额的任务
            result = service.generate_virtual_tasks_with_service_allocation(
                student_id, pool.student_name, task_amount, on_demand=True
            )

            if result['success']:
                # 更新补贴池：减少剩余金额
                generated_amount = Decimal(str(result['total_amount']))
                pool.remaining_amount -= generated_amount

                # 确保剩余金额不为负数（价值回收可能超出剩余补贴）
                if pool.remaining_amount < 0:
                    pool.remaining_amount = Decimal('0')

                pool.updated_at = datetime.now()

                logger.info(f"为学生 {pool.student_name} 价值回收生成了 {len(result['tasks'])} 个任务，总金额: {generated_amount}，剩余补贴: {pool.remaining_amount}")
            else:
                logger.warning(f"为学生 {pool.student_name} 价值回收生成任务失败: {result['message']}")

        except Exception as e:
            logger.error(f"处理学生 {student_id} 的价值回收时出错: {str(e)}")
            raise
    
    async def manual_check_bonus_pool_tasks(self):
        """手动触发奖金池过期任务检查（用于测试）"""
        logger.info("手动触发奖金池过期任务检查")
        await self.check_expired_bonus_pool_tasks()
        self.last_bonus_pool_check_time = datetime.now()

    async def check_auto_confirm_tasks(self):
        """检查并自动确认提交超过配置时间的虚拟任务（每5分钟执行）"""
        db = SessionLocal()
        try:
            logger.info("开始执行定时自动确认检查（5分钟周期）...")

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
            from sqlalchemy import func

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

    async def _process_in_progress_tasks(self, db: Session, target_date: date) -> Decimal:
        """
        处理指定日期进行中的任务（status=1,2）

        Args:
            db: 数据库会话
            target_date: 目标日期

        Returns:
            Decimal: 清理的金额
        """
        try:
            from shared.models.studenttask import StudentTask
            from .virtual_order_service import VirtualOrderService

            # 查找指定日期status=1,2的虚拟任务
            in_progress_tasks = db.query(Tasks).filter(
                Tasks.is_virtual == True,
                func.date(Tasks.created_at) == target_date,
                Tasks.status.in_(['1', '2']),
                Tasks.target_student_id.isnot(None)
            ).all()

            if not in_progress_tasks:
                logger.info(f"{target_date} 没有发现进行中的虚拟任务")
                return Decimal('0')

            cleanup_amount = Decimal('0')
            auto_completed_count = 0
            deleted_count = 0

            service = VirtualOrderService(db)

            for task in in_progress_tasks:
                try:
                    # 检查是否有提交内容
                    latest_submission = db.query(StudentTask).filter(
                        StudentTask.task_id == task.id,
                        StudentTask.content.isnot(None)
                    ).order_by(StudentTask.created_at.desc()).first()

                    if latest_submission:
                        # 有提交 → 调用完整的任务完成逻辑
                        try:
                            result = service.update_virtual_task_completion(task.id)
                            logger.info(f"凌晨自动完成任务: task_id={task.id}, student_id={result.get('student_id')}, commission={result.get('task_commission')}")
                            auto_completed_count += 1
                        except Exception as e:
                            logger.error(f"凌晨自动完成任务失败: task_id={task.id}, error={str(e)}")
                            # 自动完成失败，按无提交处理
                            cleanup_amount += task.commission
                            # 处理图片关联
                            db.execute(
                                text("UPDATE resource_images SET used_in_task_id = NULL WHERE used_in_task_id = :task_id"),
                                {"task_id": task.id}
                            )
                            db.delete(task)
                            deleted_count += 1
                    else:
                        # 无提交 → 删除任务，金额进奖金池
                        cleanup_amount += task.commission
                        # 处理图片关联
                        db.execute(
                            text("UPDATE resource_images SET used_in_task_id = NULL WHERE used_in_task_id = :task_id"),
                            {"task_id": task.id}
                        )
                        db.delete(task)
                        deleted_count += 1

                except Exception as e:
                    logger.error(f"处理进行中任务失败: task_id={task.id}, error={str(e)}")
                    continue

            logger.info(f"{target_date} 进行中任务处理完成: 自动完成 {auto_completed_count} 个，删除 {deleted_count} 个，清理金额 {cleanup_amount} 元")
            return cleanup_amount

        except Exception as e:
            logger.error(f"处理进行中任务失败: {str(e)}")
            return Decimal('0')

    async def _cleanup_unaccepted_tasks(self, db: Session, target_date: date) -> Decimal:
        """
        删除指定日期所有未接取的任务（status=0）

        Args:
            db: 数据库会话
            target_date: 目标日期

        Returns:
            Decimal: 清理的金额
        """
        try:
            # 查找指定日期status=0的虚拟任务
            unaccepted_tasks = db.query(Tasks).filter(
                Tasks.is_virtual == True,
                func.date(Tasks.created_at) == target_date,
                Tasks.status == '0',
                Tasks.target_student_id.isnot(None)
            ).all()

            if not unaccepted_tasks:
                logger.info(f"{target_date} 没有发现未接取的虚拟任务")
                return Decimal('0')

            cleanup_amount = Decimal('0')
            deleted_count = 0

            for task in unaccepted_tasks:
                try:
                    cleanup_amount += task.commission
                    # 处理图片关联
                    db.execute(
                        text("UPDATE resource_images SET used_in_task_id = NULL WHERE used_in_task_id = :task_id"),
                        {"task_id": task.id}
                    )
                    db.delete(task)
                    deleted_count += 1

                except Exception as e:
                    logger.error(f"删除未接取任务失败: task_id={task.id}, error={str(e)}")
                    continue

            logger.info(f"{target_date} 未接取任务清理完成: 删除 {deleted_count} 个，清理金额 {cleanup_amount} 元")
            return cleanup_amount

        except Exception as e:
            logger.error(f"清理未接取任务失败: {str(e)}")
            return Decimal('0')

    async def _update_bonus_pool_with_cleanup_amount(self, db: Session, today_pool, cleanup_amount: Decimal):
        """
        将清理的金额加入奖金池

        Args:
            db: 数据库会话
            today_pool: 今日奖金池对象
            cleanup_amount: 清理的金额
        """
        try:
            if cleanup_amount > 0:
                # 将清理的金额加入new_expired_amount
                today_pool.new_expired_amount += cleanup_amount
                today_pool.total_amount += cleanup_amount
                today_pool.remaining_amount += cleanup_amount
                today_pool.updated_at = datetime.now()

                logger.info(f"奖金池更新: 新增清理金额 {cleanup_amount} 元，总金额 {today_pool.total_amount} 元")

        except Exception as e:
            logger.error(f"更新奖金池清理金额失败: {str(e)}")

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
