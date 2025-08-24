import asyncio
import logging
from datetime import datetime, timedelta, date, time
from typing import List
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text

from shared.database.session import SessionLocal
from shared.models.tasks import Tasks
from shared.models.virtual_order_pool import VirtualOrderPool
from .virtual_order_service import VirtualOrderService
from .bonus_pool_service import BonusPoolService
from .bonus_pool_auto_confirm_manager import BonusPoolAutoConfirmManager

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
        # 添加每日任务执行标志，用于暂停其他定时任务
        self.daily_task_running = False

        # 固定配置：每天9点执行每日任务，8:55-24:00执行其他任务
        self.daily_task_hour = 8  # 早上8点
        self.daily_task_minute = 55
        self.window_start_hour = 8  # 任务窗口开始时间
        self.window_start_minute = 55
        logger.info(f"定时任务配置：每日任务{self.daily_task_hour}:{self.daily_task_minute:02d}执行，任务窗口{self.window_start_hour}:{self.window_start_minute:02d}-24:00，空窗期0:00-{self.window_start_hour}:{self.window_start_minute-1:02d}")

    async def start_scheduler(self):
        """启动定时任务调度器"""
        self.is_running = True
        logger.info(f"虚拟订单定时任务调度器已启动")
        logger.info(f"主任务循环：每{self.check_interval_minutes}分钟执行一次")
        logger.info(f"价值回收任务：每{self.value_recycling_interval_minutes}分钟执行一次，含补贴上限保护")

        # 启动独立的价值回收任务，含补贴上限检查
        value_recycling_task = asyncio.create_task(self._value_recycling_loop())

        try:
            while self.is_running:
                try:
                    current_time = datetime.now()

                    # 检查是否在空窗期（0:00-08:55）
                    if self.is_in_quiet_period(current_time):
                        logger.info(f"当前时间 {current_time.strftime('%H:%M')} 处于空窗期(00:00-08:55)，跳过所有定时任务")
                        # 空窗期内休眠5分钟后再检查
                        await asyncio.sleep(300)
                        continue

                    # 1. 检查是否需要执行每日任务（早上9点）
                    if self.should_run_daily_task(current_time):
                        await self.run_daily_bonus_pool_task()
                        self.last_daily_task_date = date.today()


                    # 3. 执行普通过期任务检查
                    if self.is_running:
                        await self.check_expired_tasks()

                    # 4. 执行自动确认任务检查（每5分钟）
                    if self.is_running:
                        await self.check_auto_confirm_tasks()
                    
                    # 5. 执行奖金池任务自动确认检查（每5分钟）
                    if self.is_running:
                        await self.check_bonus_pool_auto_confirm_tasks()

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
                current_time = datetime.now()

                # 检查是否在空窗期（0:00-16:29）
                if self.is_in_quiet_period(current_time):
                    logger.info(f"当前时间 {current_time.strftime('%H:%M')} 处于空窗期(00:00-08:55)，跳过价值回收任务")
                    # 空窗期内休眠2.5分钟后再检查
                    await asyncio.sleep(self.value_recycling_interval_minutes * 60)
                    continue

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
        # 检查是否正在执行每日任务
        if self.daily_task_running:
            logger.info("每日凌晨任务正在执行中，跳过过期任务检查")
            return

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

            logger.info(f"发现 {len(expired_tasks)} 个需要处理的过期任务")

            # 分别处理奖金池任务和学生任务
            bonus_pool_tasks = [task for task in expired_tasks if task.is_bonus_pool]
            student_tasks = [task for task in expired_tasks if not task.is_bonus_pool]

            logger.info(f"过期任务分类: 奖金池任务 {len(bonus_pool_tasks)} 个，学生任务 {len(student_tasks)} 个")

            service = VirtualOrderService(db)

            # 处理奖金池过期任务
            if bonus_pool_tasks:
                try:
                    await self.process_expired_bonus_pool_tasks(db, service, bonus_pool_tasks)
                except Exception as e:
                    logger.error(f"处理奖金池过期任务失败: {str(e)}")

            # 按学生分组处理学生过期任务
            student_expired_tasks = {}
            for task in student_tasks:
                student_id = task.target_student_id
                if student_id and student_id not in student_expired_tasks:
                    student_expired_tasks[student_id] = []
                if student_id:
                    student_expired_tasks[student_id].append(task)

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
                # 关键修复：检查学生是否已超过补贴上限
                if pool.consumed_subsidy >= pool.total_subsidy:
                    logger.info(f"学生 {pool.student_name} 已达到补贴上限: 上限={pool.total_subsidy}元, 已获得={pool.consumed_subsidy}元, 停止过期任务重新生成")
                    # 重置剩余金额为0，防止后续生成
                    pool.remaining_amount = Decimal('0')
                    pool.updated_at = datetime.now()
                    return

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

    async def process_expired_bonus_pool_tasks(self, db: Session, service: VirtualOrderService,
                                             expired_tasks: List[Tasks]):
        """处理奖金池过期任务"""
        try:
            from .bonus_pool_service import BonusPoolService
            bonus_service = BonusPoolService(db)

            # 计算过期任务总金额
            expired_amount = sum(task.commission for task in expired_tasks)
            logger.info(f"处理 {len(expired_tasks)} 个过期奖金池任务，总金额: {expired_amount}")

            # 删除过期任务并释放金额回奖金池
            for task in expired_tasks:
                logger.info(f"删除过期奖金池任务: ID={task.id}, 状态={task.status}, 金额={task.commission}")

                # 先清理图片引用，避免外键约束错误
                try:
                    from shared.models.resource_images import ResourceImages
                    db.query(ResourceImages).filter(
                        ResourceImages.used_in_task_id == task.id
                    ).update({
                        'used_in_task_id': None,
                        'updated_at': datetime.now()
                    })
                    db.flush()
                except Exception as img_error:
                    logger.warning(f"清理奖金池任务 {task.id} 的图片引用失败: {str(img_error)}")

                # 删除任务
                db.delete(task)

            # 释放金额回奖金池
            if expired_amount > 0:
                today_pool = bonus_service.get_today_bonus_pool()
                if today_pool:
                    today_pool.remaining_amount += expired_amount
                    today_pool.updated_at = datetime.now()
                    logger.info(f"释放过期奖金池任务金额 {expired_amount} 回奖金池")

                    # 1:1替换生成新的奖金池任务
                    generate_result = bonus_service.generate_bonus_pool_tasks(task_count=len(expired_tasks))
                    logger.info(f"奖金池过期任务1:1替换结果: {generate_result}")
                else:
                    logger.warning("未找到今日奖金池，无法释放过期任务金额")

        except Exception as e:
            logger.error(f"处理奖金池过期任务失败: {str(e)}")
            raise

    def is_in_quiet_period(self, current_time: datetime) -> bool:
        """
        检查当前时间是否在空窗期（0:00-8:55）

        Args:
            current_time: 当前时间

        Returns:
            bool: True表示在空窗期，False表示可以执行任务
        """
        # 获取当前时间的时分
        hour = current_time.hour
        minute = current_time.minute

        # 空窗期：0:00-8:55
        if hour < 8 or (hour == 8 and minute < 55):
            return True

        return False

    def is_in_time_window(self) -> bool:
        """
        检查当前时间是否在任务执行窗口内

        Returns:
            bool: True表示可以执行任务，False表示在空窗期
        """
        current_time = datetime.now().time()
        window_start = time(self.window_start_hour, self.window_start_minute)

        # 9:00-23:59:59 可以执行任务
        if current_time >= window_start:
            return True
        else:
            logger.debug(f"当前时间 {current_time} 在空窗期(0:00-8:55)，跳过任务执行")
            return False

    def should_run_daily_task(self, current_time: datetime) -> bool:
        """判断是否应该执行每日任务"""
        # 使用配置的时间检查是否应该执行每日任务
        start_time = time(self.daily_task_hour, self.daily_task_minute)
        # 处理分钟溢出的情况
        end_hour = self.daily_task_hour
        end_minute = self.daily_task_minute + 30
        if end_minute >= 60:
            end_hour = (end_hour + 1) % 24
            end_minute = end_minute - 60
        end_time = time(end_hour, end_minute)  # 30分钟窗口

        if current_time.time() >= start_time and current_time.time() <= end_time:
            # 从数据库检查今天是否已经有奖金池记录（持久化状态）
            try:
                from shared.models.bonus_pool import BonusPool
                db = SessionLocal()
                try:
                    today_pool = db.query(BonusPool).filter(
                        BonusPool.pool_date == date.today()
                    ).first()

                    # 如果今天还没有奖金池记录，说明还没执行过每日任务
                    return today_pool is None
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"检查每日任务执行状态失败: {str(e)}")
                # 发生异常时，回退到内存检查（兼容性）
                return self.last_daily_task_date != date.today()
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

        # 1. 常规过期任务（排除状态为1、2、3、4的任务，包含奖金池任务）
        regular_expired = db.query(Tasks).filter(
            and_(
                Tasks.is_virtual == True,
                func.date(Tasks.created_at) == today,  # 只检查今天的任务
                Tasks.status.notin_(['1', '2', '3', '4']),
                Tasks.end_date <= current_time
            )
        ).all()

        # 2. 状态为2的可能过期任务（使用交稿时间判断，包含奖金池任务）
        status_2_candidates = db.query(Tasks).filter(
            and_(
                Tasks.is_virtual == True,
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
                    Tasks.is_bonus_pool == False,  # 只处理普通虚拟任务，排除奖金池任务
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
                logger.info(f"已标记 {len(completed_tasks)} 个已完成任务为已回收状态")
            else:
                logger.info("没有发现需要标记的已完成任务")

        except Exception as e:
            logger.error(f"标记价值回收失败: {str(e)}")
            db.rollback()

    async def run_daily_bonus_pool_task(self):
        """执行每日奖金池任务"""
        # 修复1: 设置暂停标志，阻止其他定时任务执行
        self.daily_task_running = True
        start_time = datetime.now()
        logger.info("开始执行每日凌晨任务，暂停其他定时任务")

        db = SessionLocal()
        try:
            logger.info("开始执行每日奖金池任务...")

            # 检查虚拟任务生成是否启用
            from .config_service import ConfigService
            config_service = ConfigService(db)
            generation_config = config_service.get_virtual_task_generation_config()

            if not generation_config['enabled'] or not generation_config['daily_bonus_enabled']:
                logger.info("虚拟任务生成或每日奖金池任务已禁用，跳过每日奖金池任务")
                self.daily_task_running = False  # 重置标志
                return

            bonus_service = BonusPoolService(db)

            # 修复2: 调整执行顺序 - 先清理昨天数据，再重置今天数据

            # 1. 创建或更新今日奖金池（准备容器接收清理的金额）
            today_pool = bonus_service.create_or_update_bonus_pool()
            logger.info(f"今日奖金池已创建/更新: 总金额={today_pool.total_amount}")

            # 2. 处理昨天进行中的任务（status=1,2）
            yesterday = date.today() - timedelta(days=1)
            in_progress_cleanup_amount = await self._process_in_progress_tasks(db, yesterday)

            # 3. 删除昨天所有未接取的任务（status=0）
            unaccepted_cleanup_amount = await self._cleanup_unaccepted_tasks(db, yesterday)

            # 4. 更新奖金池金额（将清理的金额加入奖金池）
            total_cleanup_amount = in_progress_cleanup_amount + unaccepted_cleanup_amount
            if total_cleanup_amount > 0:
                await self._update_bonus_pool_with_cleanup_amount(db, today_pool, total_cleanup_amount)
                logger.info(f"昨日任务清理完成: 进行中任务清理 {in_progress_cleanup_amount} 元，未接取任务清理 {unaccepted_cleanup_amount} 元，总计 {total_cleanup_amount} 元")

            # 5. 更新昨天的学生达标记录
            achievement_result = bonus_service.update_daily_achievements(yesterday)
            logger.info(f"学生达标统计完成: {achievement_result}")

            # 6. 重置所有学生的当日完成金额（新的一天开始）- 在清理完昨天数据后执行
            from shared.models.virtual_order_pool import VirtualOrderPool
            pools = db.query(VirtualOrderPool).filter(
                VirtualOrderPool.status == 'active'
            ).all()
            for pool in pools:
                pool.completed_amount = Decimal('0')
                pool.consumed_subsidy = Decimal('0')  # 重置实际消耗的补贴
                pool.remaining_amount = pool.total_subsidy  # 重置为每日补贴金额
                logger.info(f"学生 {pool.student_name} 每日数据已重置: 每日补贴={pool.total_subsidy}")

            # 7. 为所有有补贴的学生生成个人补贴任务（使用虚拟客服分配策略）
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

            # 修复3: 添加超时检查
            elapsed_time = (datetime.now() - start_time).total_seconds()
            if elapsed_time > 1800:  # 30分钟超时
                logger.error(f"凌晨任务执行超时（已执行{elapsed_time:.1f}秒），强制结束")
                db.commit()  # 提交已完成的部分
                self.daily_task_running = False  # 重置标志
                logger.info("凌晨任务因超时结束，恢复其他定时任务")
                return

            # 8. 生成初始奖金池任务（按需生成1-2个）
            if today_pool.remaining_amount > 0:
                generate_result = bonus_service.generate_bonus_pool_tasks()
                logger.info(f"奖金池初始任务生成结果: {generate_result}")

            db.commit()

            # 记录执行时间
            total_execution_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"每日奖金池任务执行完成，耗时: {total_execution_time:.1f}秒")

        except Exception as e:
            logger.error(f"执行每日奖金池任务失败: {str(e)}")
            db.rollback()
        finally:
            db.close()
            # 修复1: 确保标志被重置，避免永久阻塞其他任务
            self.daily_task_running = False
            logger.info("每日凌晨任务结束，恢复其他定时任务")


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
        # 检查是否正在执行每日任务
        if self.daily_task_running:
            logger.info("每日凌晨任务正在执行中，跳过价值回收任务")
            return

        db = SessionLocal()
        try:
            logger.info("开始检查需要价值回收的已完成任务...")

            # 检查虚拟任务生成是否启用
            from .config_service import ConfigService
            config_service = ConfigService(db)
            generation_config = config_service.get_virtual_task_generation_config()

            if not generation_config['enabled'] or not generation_config['value_recycling_enabled']:
                logger.info("虚拟任务生成或价值回收任务生成已禁用，跳过价值回收任务生成")
                # 仍然需要标记任务为已回收，但不重新生成任务
                await self.mark_value_recycled_only(db)
                return

            # 查找所有未回收价值的已完成普通虚拟任务（排除奖金池任务）
            # 移除时间限制，确保服务中断后重启时能处理所有积压的任务
            completed_tasks = db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual == True,
                    Tasks.is_bonus_pool == False,  # 只处理普通虚拟任务，排除奖金池任务
                    Tasks.status == '4',  # 已完成状态
                    Tasks.value_recycled == False,  # 未回收价值
                    Tasks.target_student_id.isnot(None)  # 有目标学生的任务
                )
            ).order_by(Tasks.updated_at.asc()).limit(50).all()  # 限制批次大小，按时间顺序处理

            if not completed_tasks:
                logger.info("没有发现需要价值回收的已完成任务")
                return

            logger.info(f"发现 {len(completed_tasks)} 个需要价值回收的已完成普通虚拟任务（不包含奖金池任务）")

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

            # 关键修复：检查学生是否已超过补贴上限
            if pool.consumed_subsidy >= pool.total_subsidy:
                logger.info(f"学生 {pool.student_name} 已达到补贴上限: 上限={pool.total_subsidy}元, 已获得={pool.consumed_subsidy}元, 停止价值回收任务生成")
                # 重置剩余金额为0，防止后续生成
                pool.remaining_amount = Decimal('0')
                pool.updated_at = datetime.now()
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

    async def process_bonus_pool_value_recycling(self, db: Session, service: VirtualOrderService,
                                               bonus_pool_tasks: List[Tasks]):
        """处理奖金池价值回收"""
        try:
            from .bonus_pool_service import BonusPoolService
            bonus_service = BonusPoolService(db)

            total_recycled_value = Decimal('0')

            for task in bonus_pool_tasks:
                student_id = task.target_student_id

                # 计算回收价值
                rebate_rate = service.get_student_rebate_rate(student_id)
                student_income = task.commission * rebate_rate  # 学生实际获得的收益
                recycled_value = task.commission - student_income  # 回收的价值

                # 标记任务已回收
                task.value_recycled = True
                task.recycled_at = datetime.now()

                total_recycled_value += recycled_value

                logger.info(f"奖金池任务 {task.id} 价值回收: {recycled_value}元 (任务面值: {task.commission}, 学生收益: {student_income})")

            # 将回收的价值添加回奖金池
            if total_recycled_value > 0:
                today_pool = bonus_service.get_today_bonus_pool()
                if today_pool:
                    today_pool.remaining_amount += total_recycled_value
                    today_pool.updated_at = datetime.now()
                    logger.info(f"奖金池价值回收: 回收总价值 {total_recycled_value}元 到奖金池")

                    # 根据回收的价值生成新的奖金池任务
                    # 生成任务数量根据回收价值确定（每个任务平均金额作为参考）
                    if len(bonus_pool_tasks) > 0:
                        avg_task_amount = total_recycled_value / len(bonus_pool_tasks)
                        # 基于回收价值生成1-2个新任务
                        generate_result = bonus_service.generate_bonus_pool_tasks(
                            task_count=min(2, max(1, len(bonus_pool_tasks)))
                        )
                        logger.info(f"奖金池价值回收生成新任务结果: {generate_result}")
                else:
                    logger.warning("未找到今日奖金池，无法回收价值")

        except Exception as e:
            logger.error(f"处理奖金池价值回收失败: {str(e)}")
            raise


    async def check_auto_confirm_tasks(self):
        """检查并自动确认提交超过配置时间的虚拟任务（每5分钟执行）"""
        # 检查是否正在执行每日任务
        if self.daily_task_running:
            logger.info("每日凌晨任务正在执行中，跳过自动确认任务")
            return

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
                    Tasks.target_student_id.isnot(None),  # 只处理有目标学生的虚拟任务
                    Tasks.is_bonus_pool == False  # 排除奖金池任务，奖金池任务需要独立处理
                )
            ).limit(max_batch_size).all()  # 限制批次大小

            if not pending_submissions:
                logger.info("没有发现需要自动确认的任务")
                return

            logger.info(f"发现 {len(pending_submissions)} 个需要自动确认的任务（包含虚拟任务和奖金池任务）")

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
    
    async def check_bonus_pool_auto_confirm_tasks(self):
        """检查并自动确认奖金池任务（每5分钟执行）"""
        # 检查是否正在执行每日任务
        if self.daily_task_running:
            logger.info("每日凌晨任务正在执行中，跳过奖金池自动确认任务")
            return
        
        db = SessionLocal()
        try:
            logger.info("开始执行奖金池任务自动确认检查（5分钟周期）...")
            
            # 导入配置服务
            from .config_service import ConfigService
            
            # 获取配置
            config_service = ConfigService(db)
            auto_confirm_config = config_service.get_auto_confirm_config()
            
            # 检查是否启用自动确认
            if not auto_confirm_config['enabled']:
                logger.info("自动确认功能已禁用，跳过奖金池任务自动确认")
                return
            
            # 创建奖金池自动确认管理器
            bonus_auto_confirm_manager = BonusPoolAutoConfirmManager(db)
            
            # 执行奖金池任务自动确认
            result = await bonus_auto_confirm_manager.check_bonus_pool_auto_confirm_tasks(
                interval_hours=auto_confirm_config['interval_hours'],
                max_batch_size=auto_confirm_config['max_batch_size']
            )
            
            if result['success']:
                logger.info(f"奖金池任务自动确认完成: 成功确认{result['confirmed_count']}个任务，"
                           f"失败{result['failed_count']}个任务")
                if result['failed_count'] > 0 and result.get('failed_details'):
                    logger.warning(f"奖金池任务自动确认失败详情: {result['failed_details']}")
            else:
                logger.error(f"奖金池任务自动确认失败: {result['message']}")
            
        except Exception as e:
            logger.error(f"检查奖金池任务自动确认失败: {str(e)}")
        finally:
            db.close()
    
    async def manual_check_bonus_pool_auto_confirm_tasks(self):
        """手动触发奖金池任务自动确认检查（用于测试）"""
        logger.info("手动触发奖金池任务自动确认检查")
        await self.check_bonus_pool_auto_confirm_tasks()

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

async def manual_check_bonus_pool_auto_confirm():
    """手动检查奖金池任务自动确认的接口"""
    await scheduler.manual_check_bonus_pool_auto_confirm_tasks()
