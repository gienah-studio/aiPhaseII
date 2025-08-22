from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, case
import logging

logger = logging.getLogger(__name__)

from shared.models.bonus_pool import BonusPool
from shared.models.student_daily_achievement import StudentDailyAchievement
from shared.models.system_config import SystemConfig
from shared.models.tasks import Tasks
from shared.models.userinfo import UserInfo
from shared.models.agents import Agents
from shared.exceptions import BusinessException
from .virtual_order_service import VirtualOrderService

logger = logging.getLogger(__name__)

class BonusPoolService:
    """奖金池服务类"""

    def __init__(self, db: Session):
        self.db = db
        self.virtual_order_service = VirtualOrderService(db)

    def get_system_config(self, key: str, default_value: Any = None) -> Any:
        """获取系统配置"""
        config = self.db.query(SystemConfig).filter(
            SystemConfig.config_key == key
        ).first()

        if config:
            return config.get_value()
        return default_value

    def get_daily_target(self) -> Decimal:
        """获取每日达标金额"""
        return Decimal(str(self.get_system_config('daily_achievement_target', 50)))

    def is_bonus_pool_enabled(self) -> bool:
        """检查奖金池功能是否启用"""
        return self.get_system_config('bonus_pool_enabled', 'true') == 'true'

    def get_bonus_pool_summary(self, pool_date: date = None) -> Dict[str, Any]:
        """
        获取奖金池汇总信息（累计金额和可抢人数）

        Args:
            pool_date: 奖金池日期，默认为今天

        Returns:
            Dict: 包含累计金额和可抢人数的汇总信息
        """
        if pool_date is None:
            pool_date = date.today()

        # 获取奖金池信息
        bonus_pool = self.db.query(BonusPool).filter(
            BonusPool.pool_date == pool_date
        ).first()

        # 奖金池累计金额
        total_amount = float(bonus_pool.total_amount) if bonus_pool else 0.0
        remaining_amount = float(bonus_pool.remaining_amount) if bonus_pool else 0.0
        generated_amount = float(bonus_pool.generated_amount) if bonus_pool else 0.0
        completed_amount = float(bonus_pool.completed_amount) if bonus_pool else 0.0

        # 计算可抢奖金池人数（昨天达标的学生数量）
        yesterday = pool_date - timedelta(days=1)
        qualified_students_count = self.db.query(StudentDailyAchievement).filter(
            StudentDailyAchievement.achievement_date == yesterday,
            StudentDailyAchievement.is_achieved == True
        ).count()

        # 获取昨天达标学生的详细信息（可选）
        qualified_students = self.db.query(StudentDailyAchievement).filter(
            StudentDailyAchievement.achievement_date == yesterday,
            StudentDailyAchievement.is_achieved == True
        ).all()

        qualified_students_info = []
        for student in qualified_students:
            qualified_students_info.append({
                "student_id": student.student_id,
                "student_name": student.student_name,
                "completed_amount": float(student.completed_amount),
                "daily_target": float(student.daily_target)
            })

        return {
            "pool_date": pool_date.strftime('%Y-%m-%d'),
            "bonus_pool": {
                "total_amount": total_amount,
                "remaining_amount": remaining_amount,
                "generated_amount": generated_amount,
                "completed_amount": completed_amount,
                "exists": bonus_pool is not None
            },
            "qualified_students": {
                "count": qualified_students_count,
                "achievement_date": yesterday.strftime('%Y-%m-%d'),
                "students": qualified_students_info
            },
            "summary": {
                "pool_total": total_amount,
                "eligible_count": qualified_students_count,
                "average_per_person": round(total_amount / qualified_students_count, 2) if qualified_students_count > 0 else 0.0
            }
        }

    def calculate_student_daily_achievement(self, student_id: int, target_date: date) -> Dict[str, Any]:
        """
        计算学生某日的达标情况

        Args:
            student_id: 学生ID
            target_date: 目标日期

        Returns:
            Dict: 达标信息
        """
        # 获取学生信息
        student = self.db.query(UserInfo).filter(
            UserInfo.roleId == student_id,
            UserInfo.level == '3',  # 学生级别
            UserInfo.isDeleted == False
        ).first()

        if not student:
            raise BusinessException(code=404, msg="学生不存在")

        # 计算当日完成的虚拟任务金额（面值）
        # 只统计已完成的虚拟任务（与API收入统计保持一致）
        # 使用updated_at而不是created_at，因为我们关心的是完成时间
        completed_face_value = self.db.query(func.sum(Tasks.commission)).filter(
            Tasks.target_student_id == student_id,
            Tasks.is_virtual == True,
            Tasks.status == '4',  # 已完成
            func.date(Tasks.updated_at) == target_date
        ).scalar() or Decimal('0')

        # 获取学生的返佣比例
        rebate_rate = self.virtual_order_service.get_student_rebate_rate(student_id)

        # 计算实际消耗的补贴（面值 × 返佣比例）
        consumed_subsidy = completed_face_value * rebate_rate

        # 获取每日目标
        daily_target = self.get_daily_target()

        # 判断是否达标（基于实际消耗的补贴）
        is_achieved = consumed_subsidy >= daily_target

        return {
            'student_id': student_id,
            'student_name': student.name,
            'achievement_date': target_date,
            'daily_target': daily_target,
            'completed_face_value': completed_face_value,  # 任务面值
            'consumed_subsidy': consumed_subsidy,  # 实际消耗的补贴
            'rebate_rate': float(rebate_rate),  # 返佣比例
            'is_achieved': is_achieved
        }

    def update_daily_achievements(self, target_date: date = None) -> Dict[str, Any]:
        """
        更新所有学生的每日达标记录

        Args:
            target_date: 目标日期，默认为昨天

        Returns:
            Dict: 更新统计
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        # 获取所有学生
        students = self.db.query(UserInfo).filter(
            UserInfo.level == '3',  # 学生级别
            UserInfo.isDeleted == False
        ).all()

        total_students = 0
        achieved_students = 0

        for student in students:
            try:
                # 计算达标情况
                achievement_data = self.calculate_student_daily_achievement(
                    student.roleId, target_date
                )

                # 查找或创建记录
                achievement = self.db.query(StudentDailyAchievement).filter(
                    StudentDailyAchievement.student_id == student.roleId,
                    StudentDailyAchievement.achievement_date == target_date
                ).first()

                if achievement:
                    # 更新现有记录（使用实际消耗的补贴）
                    achievement.completed_amount = achievement_data['consumed_subsidy']
                    achievement.is_achieved = achievement_data['is_achieved']
                else:
                    # 创建新记录（使用实际消耗的补贴）
                    achievement = StudentDailyAchievement(
                        student_id=student.roleId,
                        student_name=achievement_data['student_name'],
                        achievement_date=target_date,
                        daily_target=achievement_data['daily_target'],
                        completed_amount=achievement_data['consumed_subsidy'],  # 使用实际消耗的补贴
                        is_achieved=achievement_data['is_achieved']
                    )
                    self.db.add(achievement)

                total_students += 1
                if achievement_data['is_achieved']:
                    achieved_students += 1

            except Exception as e:
                print(f"更新学生 {student.roleId} 达标记录失败: {str(e)}")
                continue

        self.db.commit()

        return {
            'date': target_date.isoformat(),
            'total_students': total_students,
            'achieved_students': achieved_students,
            'achievement_rate': f"{achieved_students/total_students*100:.2f}%" if total_students > 0 else "0%"
        }

    def check_student_bonus_access(self, student_id: int, check_date: date = None) -> bool:
        """
        检查学生是否有奖金池访问权限（前一天是否达标）

        Args:
            student_id: 学生ID
            check_date: 检查日期，默认为今天

        Returns:
            bool: 是否有权限
        """
        if check_date is None:
            check_date = date.today()

        # 检查前一天的达标情况
        yesterday = check_date - timedelta(days=1)

        achievement = self.db.query(StudentDailyAchievement).filter(
            StudentDailyAchievement.student_id == student_id,
            StudentDailyAchievement.achievement_date == yesterday,
            StudentDailyAchievement.is_achieved == True
        ).first()

        return achievement is not None

    def collect_unachieved_students_subsidy(self, target_date: date = None) -> Dict[str, Any]:
        """
        收集没达标学员的剩余补贴（基于补贴池实际剩余金额）

        Args:
            target_date: 目标日期，默认为昨天

        Returns:
            Dict: 剩余补贴统计
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        from shared.models.virtual_order_pool import VirtualOrderPool

        # 查询所有学员的达标记录
        achievements = self.db.query(StudentDailyAchievement).filter(
            StudentDailyAchievement.achievement_date == target_date
        ).all()

        total_remaining_subsidy = Decimal('0')
        unachieved_students = []
        achieved_students = []

        for achievement in achievements:
            # 查询该学员的补贴池信息
            student_pool = self.db.query(VirtualOrderPool).filter(
                VirtualOrderPool.student_id == achievement.student_id,
                VirtualOrderPool.is_deleted == False,
                VirtualOrderPool.status == 'active'
            ).first()

            if achievement.is_achieved:
                # 达标学员：剩余补贴为0（不进入奖金池）
                pool_remaining = float(student_pool.remaining_amount) if student_pool else 0.0
                achieved_students.append({
                    'student_id': achievement.student_id,
                    'student_name': achievement.student_name,
                    'consumed_subsidy': float(achievement.completed_amount),
                    'pool_remaining_amount': pool_remaining,
                    'remaining_subsidy': 0.0  # 达标学员不贡献奖金池
                })
            else:
                # 没达标学员：使用补贴池的剩余金额
                if student_pool and student_pool.remaining_amount > 0:
                    pool_remaining = student_pool.remaining_amount
                    total_remaining_subsidy += pool_remaining
                    unachieved_students.append({
                        'student_id': achievement.student_id,
                        'student_name': achievement.student_name,
                        'consumed_subsidy': float(achievement.completed_amount),
                        'pool_remaining_amount': float(pool_remaining),
                        'remaining_subsidy': float(pool_remaining)  # 使用补贴池剩余金额
                    })
                else:
                    # 没有补贴池或剩余金额为0
                    unachieved_students.append({
                        'student_id': achievement.student_id,
                        'student_name': achievement.student_name,
                        'consumed_subsidy': float(achievement.completed_amount),
                        'pool_remaining_amount': 0.0,
                        'remaining_subsidy': 0.0
                    })

        return {
            'target_date': target_date.isoformat(),
            'total_students': len(achievements),
            'achieved_students_count': len(achieved_students),
            'unachieved_students_count': len(unachieved_students),
            'total_remaining_subsidy': float(total_remaining_subsidy),
            'achieved_students': achieved_students,
            'unachieved_students': unachieved_students
        }

    def collect_expired_virtual_tasks(self, target_date: date = None) -> Dict[str, Any]:
        """
        收集过期的虚拟任务

        Args:
            target_date: 目标日期，默认为昨天

        Returns:
            Dict: 过期任务统计
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        # 查找昨天过期的普通虚拟任务
        # 注意：这里使用created_at是正确的，因为我们要找的是昨天创建但过期的任务
        expired_normal_tasks = self.db.query(Tasks).filter(
            Tasks.is_virtual == True,
            Tasks.is_bonus_pool == False,
            func.date(Tasks.created_at) == target_date,
            Tasks.status == '0',  # 未接取
            Tasks.end_date < datetime.now()  # 已过期
        ).all()

        # 查找昨天过期的奖金池任务
        expired_bonus_tasks = self.db.query(Tasks).filter(
            Tasks.is_virtual == True,
            Tasks.is_bonus_pool == True,
            Tasks.bonus_pool_date == target_date,
            Tasks.status == '0',  # 未接取
            Tasks.end_date < datetime.now()  # 已过期
        ).all()

        # 计算金额
        normal_amount = sum(task.commission for task in expired_normal_tasks)
        bonus_amount = sum(task.commission for task in expired_bonus_tasks)

        # 标记任务为已过期
        for task in expired_normal_tasks + expired_bonus_tasks:
            task.status = '5'  # 终止/过期状态
            task.message = '任务已过期，金额转入奖金池'

        self.db.commit()

        return {
            'date': target_date.isoformat(),
            'expired_normal_tasks': len(expired_normal_tasks),
            'expired_normal_amount': float(normal_amount),
            'expired_bonus_tasks': len(expired_bonus_tasks),
            'expired_bonus_amount': float(bonus_amount),
            'total_expired_amount': float(normal_amount + bonus_amount)
        }

    def create_or_update_bonus_pool(self, pool_date: date = None) -> BonusPool:
        """
        创建或更新奖金池

        Args:
            pool_date: 奖金池日期，默认为今天

        Returns:
            BonusPool: 奖金池对象
        """
        if pool_date is None:
            pool_date = date.today()

        # 收集昨天没达标学员的剩余补贴
        yesterday = pool_date - timedelta(days=1)
        subsidy_data = self.collect_unachieved_students_subsidy(yesterday)

        # 同时收集过期任务（保留原有逻辑）
        expired_data = self.collect_expired_virtual_tasks(yesterday)

        # 查找或创建今日奖金池
        bonus_pool = self.db.query(BonusPool).filter(
            BonusPool.pool_date == pool_date
        ).first()

        # 计算奖金池总金额：剩余补贴 + 过期任务金额
        total_subsidy_amount = Decimal(str(subsidy_data['total_remaining_subsidy']))
        total_expired_amount = Decimal(str(expired_data['total_expired_amount']))
        total_pool_amount = total_subsidy_amount + total_expired_amount

        if bonus_pool:
            # 更新现有奖金池
            bonus_pool.new_expired_amount = total_subsidy_amount  # 使用剩余补贴作为新增金额
            bonus_pool.carry_forward_amount += Decimal(str(expired_data['expired_bonus_amount']))  # 过期奖金池任务结转
            bonus_pool.total_amount = bonus_pool.new_expired_amount + bonus_pool.carry_forward_amount + Decimal(str(expired_data['expired_normal_amount']))
            bonus_pool.remaining_amount = bonus_pool.total_amount - bonus_pool.generated_amount
        else:
            # 创建新的奖金池
            bonus_pool = BonusPool(
                pool_date=pool_date,
                carry_forward_amount=Decimal(str(expired_data['expired_bonus_amount'])),  # 过期奖金池任务
                new_expired_amount=total_subsidy_amount,  # 没达标学员的剩余补贴
                total_amount=total_pool_amount,  # 总金额 = 剩余补贴 + 过期任务
                generated_amount=Decimal('0'),
                completed_amount=Decimal('0'),
                remaining_amount=total_pool_amount
            )
            self.db.add(bonus_pool)

        self.db.commit()
        return bonus_pool

    def _calculate_bonus_task_amount(self, remaining_amount: Decimal) -> Decimal:
        """
        计算奖金池任务金额（复用虚拟任务的按需生成规则）

        Args:
            remaining_amount: 奖金池剩余金额

        Returns:
            Decimal: 本次生成的任务金额
        """
        # 使用与普通虚拟任务相同的规则
        if remaining_amount < Decimal('8'):
            return Decimal('5')
        else:
            return Decimal('10')

    def generate_single_bonus_pool_task(self, pool_date: date = None) -> Dict[str, Any]:
        """
        生成单个奖金池任务（严格1:1替换专用）

        Args:
            pool_date: 奖金池日期，默认为今天

        Returns:
            Dict: 生成结果
        """
        if pool_date is None:
            pool_date = date.today()

        # 获取今日奖金池
        bonus_pool = self.db.query(BonusPool).filter(
            BonusPool.pool_date == pool_date
        ).first()

        if not bonus_pool:
            return {
                'success': False,
                'message': '奖金池不存在',
                'generated_tasks': 0
            }

        # 检查是否有剩余金额
        if bonus_pool.remaining_amount <= 0:
            return {
                'success': True,
                'message': '奖金池已分配完毕',
                'generated_tasks': 0
            }

        # 检查是否有达标学生
        yesterday = pool_date - timedelta(days=1)
        qualified_students = self.db.query(StudentDailyAchievement).filter(
            StudentDailyAchievement.achievement_date == yesterday,
            StudentDailyAchievement.is_achieved == True
        ).all()

        if not qualified_students:
            return {
                'success': False,
                'message': '没有达标学生，无法生成奖金池任务',
                'generated_tasks': 0
            }

        # 计算单个任务金额
        task_amount = self._calculate_bonus_task_amount(bonus_pool.remaining_amount)

        logger.info(f"奖金池单任务生成：剩余金额={bonus_pool.remaining_amount}，生成金额={task_amount}")

        # 直接生成单个任务，不使用按需生成逻辑
        generated_tasks = []
        now = datetime.now()

        try:
            # 生成任务内容
            task_content = self.virtual_order_service.generate_random_task_content()

            task = Tasks(
                summary=task_content['summary'],
                requirement=task_content['requirement'],
                reference_images='',
                source='奖金池',
                order_number=self.virtual_order_service.generate_order_number(),
                commission=task_amount,
                commission_unit='人民币',
                end_date=now + timedelta(hours=3),  # 3小时后过期
                delivery_date=now + timedelta(hours=3),
                status='0',  # 待接取
                task_style='其他',
                task_type='其他',
                created_at=now,
                updated_at=now,
                orders_number=1,
                order_received_number=0,
                founder='奖金池系统',
                founder_id=0,
                payment_status='1',
                task_level='D',
                is_virtual=True,
                is_bonus_pool=True,  # 标记为奖金池任务
                bonus_pool_date=pool_date,
                target_student_id=None,  # 不限定特定学生
                is_renew='0',
                virtual_service_id=None,
                virtual_service_name=None
            )

            self.db.add(task)
            generated_tasks.append(task)

        except Exception as e:
            logger.error(f"生成单个奖金池任务失败: {str(e)}")
            return {
                'success': False,
                'message': f'生成任务失败: {str(e)}',
                'generated_tasks': 0
            }

        # 更新奖金池时间戳
        bonus_pool.updated_at = datetime.now()
        self.db.commit()

        return {
            'success': True,
            'message': f'成功生成 1 个奖金池任务',
            'generated_tasks': 1,
            'total_amount': float(task_amount),
            'remaining_amount': float(bonus_pool.remaining_amount)
        }

    def generate_bonus_pool_tasks(self, pool_date: date = None) -> Dict[str, Any]:
        """
        按需生成奖金池任务（复用虚拟任务生成逻辑）

        Args:
            pool_date: 奖金池日期，默认为今天

        Returns:
            Dict: 生成结果
        """
        if pool_date is None:
            pool_date = date.today()

        # 获取今日奖金池
        bonus_pool = self.db.query(BonusPool).filter(
            BonusPool.pool_date == pool_date
        ).first()

        if not bonus_pool:
            return {
                'success': False,
                'message': '奖金池不存在',
                'generated_tasks': 0
            }

        # 检查是否有剩余金额
        if bonus_pool.remaining_amount <= 0:
            return {
                'success': True,
                'message': '奖金池已分配完毕',
                'generated_tasks': 0
            }

        # 检查是否有达标学生
        yesterday = pool_date - timedelta(days=1)
        qualified_students = self.db.query(StudentDailyAchievement).filter(
            StudentDailyAchievement.achievement_date == yesterday,
            StudentDailyAchievement.is_achieved == True
        ).all()

        if not qualified_students:
            return {
                'success': False,
                'message': '没有达标学生，无法生成奖金池任务',
                'generated_tasks': 0
            }

        # 计算本次生成的任务金额（按需生成1-2个任务）
        task_amount = self._calculate_bonus_task_amount(bonus_pool.remaining_amount)

        logger.info(f"奖金池按需生成：剩余金额={bonus_pool.remaining_amount}，本次生成金额={task_amount}")

        # 使用虚拟任务生成逻辑（按需生成）
        try:
            result = self.virtual_order_service.generate_virtual_tasks_with_service_allocation(
                student_id=None,  # 奖金池任务不指定学生
                student_name="奖金池任务",
                subsidy_amount=task_amount,
                on_demand=True  # 按需生成1-2个任务
            )

            if not result['success']:
                raise Exception(f"奖金池任务生成失败: {result['message']}")

            # 更新生成的任务属性为奖金池任务
            generated_tasks = []
            now = datetime.now()

            for task_info in result['tasks']:
                # 获取已创建的任务对象
                task = self.db.query(Tasks).filter(Tasks.id == task_info['id']).first()
                if task:
                    # 更新任务属性为奖金池任务
                    task.source = '奖金池'
                    task.target_student_id = None  # 奖金池任务不指定特定学生
                    task.end_date = now + timedelta(hours=3)  # 3小时后过期
                    task.delivery_date = now + timedelta(hours=3)
                    task.is_bonus_pool = True  # 标记为奖金池任务
                    task.bonus_pool_date = pool_date
                    task.updated_at = now

                    generated_tasks.append(task)

        except Exception as e:
            logger.error(f"使用虚拟客服分配策略生成奖金池任务失败: {e}")
            # 回退到简单生成方式
            generated_tasks = []
            now = datetime.now()

            # 直接生成一个任务
            task_content = self.virtual_order_service.generate_random_task_content()

            task = Tasks(
                summary=task_content['summary'],
                requirement=task_content['requirement'],
                reference_images='',
                source='奖金池',
                order_number=self.virtual_order_service.generate_order_number(),
                commission=task_amount,
                commission_unit='人民币',
                end_date=now + timedelta(hours=3),  # 3小时后过期
                delivery_date=now + timedelta(hours=3),
                status='0',  # 待接取
                task_style='其他',
                task_type='其他',
                created_at=now,
                updated_at=now,
                orders_number=1,
                order_received_number=0,
                founder='奖金池系统',
                founder_id=0,
                payment_status='1',
                task_level='D',
                is_virtual=True,
                is_bonus_pool=True,  # 标记为奖金池任务
                bonus_pool_date=pool_date,
                target_student_id=None,  # 不限定特定学生
                is_renew='0',
                virtual_service_id=None,
                virtual_service_name=None
            )

            self.db.add(task)
            generated_tasks.append(task)

        # 奖金池任务生成时不扣减金额，等任务完成时再按实际收益扣减
        # 这里只更新时间戳
        bonus_pool.updated_at = datetime.now()

        self.db.commit()

        generated_amount = sum(task.commission for task in generated_tasks)
        return {
            'success': True,
            'message': f'成功生成 {len(generated_tasks)} 个奖金池任务',
            'generated_tasks': len(generated_tasks),
            'total_amount': float(generated_amount),
            'remaining_amount': float(bonus_pool.remaining_amount)
        }

    def process_expired_bonus_tasks(self) -> Dict[str, Any]:
        """
        处理过期的奖金池任务（按需重新生成）
        """
        now = datetime.now()
        today = date.today()

        # 查找今天过期的奖金池任务
        expired_tasks = self.db.query(Tasks).filter(
            Tasks.is_virtual == True,
            Tasks.is_bonus_pool == True,
            Tasks.bonus_pool_date == today,
            Tasks.status == '0',  # 未接取
            Tasks.end_date <= now  # 已过期
        ).all()

        if not expired_tasks:
            return {
                'processed_tasks': 0,
                'regenerated_tasks': 0
            }

        expired_count = len(expired_tasks)
        logger.info(f"发现 {expired_count} 个过期的奖金池任务，准备删除并重新生成")

        # 删除过期任务
        for task in expired_tasks:
            # 先清理图片引用，避免外键约束错误
            try:
                from shared.models.resource_images import ResourceImages
                self.db.query(ResourceImages).filter(
                    ResourceImages.used_in_task_id == task.id
                ).update({
                    'used_in_task_id': None,
                    'updated_at': datetime.now()
                })
                self.db.flush()
            except Exception as img_error:
                logger.warning(f"清理奖金池任务 {task.id} 的图片引用失败: {str(img_error)}")

            self.db.delete(task)

        self.db.commit()

        # 重新生成对应数量的奖金池任务（严格1:1替换）
        regenerated_count = 0
        for i in range(expired_count):
            try:
                result = self.generate_single_bonus_pool_task(today)
                if result['success'] and result['generated_tasks'] > 0:
                    regenerated_count += result['generated_tasks']
                    logger.info(f"过期替换：第 {i+1}/{expired_count} 生成了 {result['generated_tasks']} 个奖金池任务")
                else:
                    logger.warning(f"过期替换：第 {i+1}/{expired_count} 生成失败: {result['message']}")
                    break  # 如果生成失败（比如奖金池用完），停止生成
            except Exception as e:
                logger.error(f"过期替换：第 {i+1}/{expired_count} 生成异常: {str(e)}")
                break

        return {
            'processed_tasks': expired_count,
            'regenerated_tasks': regenerated_count
        }

    def process_completed_bonus_tasks(self) -> Dict[str, Any]:
        """
        处理已完成的奖金池任务（按学生实际收益扣减奖金池）
        """
        today = date.today()

        # 查找今天已完成但未标记为已回收的奖金池任务
        completed_tasks = self.db.query(Tasks).filter(
            Tasks.is_virtual == True,
            Tasks.is_bonus_pool == True,
            Tasks.bonus_pool_date == today,
            Tasks.status == '4',  # 已完成状态
            Tasks.value_recycled == False  # 未标记为已回收
        ).all()

        if not completed_tasks:
            return {
                'processed_tasks': 0,
                'consumed_amount': 0,
                'regenerated_tasks': 0
            }

        completed_count = len(completed_tasks)
        total_consumed_amount = Decimal('0')

        logger.info(f"发现 {completed_count} 个已完成的奖金池任务，准备处理价值回收")

        # 获取奖金池
        bonus_pool = self.db.query(BonusPool).filter(
            BonusPool.pool_date == today
        ).first()

        if not bonus_pool:
            logger.warning("未找到今天的奖金池")
            return {
                'processed_tasks': 0,
                'consumed_amount': 0,
                'regenerated_tasks': 0
            }

        # 处理每个完成的任务
        for task in completed_tasks:
            # 获取实际完成任务的学生ID（奖金池任务的target_student_id为NULL，需要使用accepted_by）
            if task.accepted_by:
                try:
                    actual_student_id = int(task.accepted_by)  # accepted_by是字符串，需要转换为整数
                except (ValueError, TypeError):
                    logger.error(f"奖金池任务 {task.id} 的accepted_by字段无效: {task.accepted_by}")
                    actual_student_id = task.target_student_id
            else:
                actual_student_id = task.target_student_id

            # 获取学生返佣比例
            rebate_rate = self.virtual_order_service.get_student_rebate_rate(actual_student_id)

            # 计算学生实际收益和价值回收
            student_income = task.commission * rebate_rate  # 学生实际收益
            recycled_value = task.commission - student_income  # 价值回收

            # 奖金池只消耗学生实际收益部分
            bonus_pool.remaining_amount -= student_income
            total_consumed_amount += student_income

            # 标记任务为已回收
            task.value_recycled = True
            task.recycled_at = datetime.now()

            logger.info(f"奖金池任务 {task.id} 价值回收: 任务面值={task.commission}, 学生收益={student_income}, 价值回收={recycled_value}, 奖金池消耗={student_income}")

        # 确保奖金池剩余金额不为负数
        if bonus_pool.remaining_amount < 0:
            bonus_pool.remaining_amount = Decimal('0')

        bonus_pool.updated_at = datetime.now()
        self.db.commit()

        # 为每个完成的任务重新生成1个新任务（严格1:1补充）
        regenerated_count = 0
        for i in range(completed_count):
            try:
                result = self.generate_single_bonus_pool_task(today)
                if result['success'] and result['generated_tasks'] > 0:
                    regenerated_count += result['generated_tasks']
                    logger.info(f"完成补充：第 {i+1}/{completed_count} 生成了 {result['generated_tasks']} 个奖金池任务")
                else:
                    logger.warning(f"完成补充：第 {i+1}/{completed_count} 生成失败: {result['message']}")
                    break  # 如果生成失败（比如奖金池用完），停止生成
            except Exception as e:
                logger.error(f"完成补充：第 {i+1}/{completed_count} 生成异常: {str(e)}")
                break

        return {
            'processed_tasks': completed_count,
            'consumed_amount': float(total_consumed_amount),
            'remaining_amount': float(bonus_pool.remaining_amount),
            'regenerated_tasks': regenerated_count
        }

    def process_single_completed_bonus_task(self, task_id: int) -> Dict[str, Any]:
        """
        处理单个完成的奖金池任务（实时调用）

        Args:
            task_id: 任务ID

        Returns:
            Dict: 处理结果
        """
        task = self.db.query(Tasks).filter(Tasks.id == task_id).first()

        if not task or not task.is_bonus_pool or task.value_recycled:
            return {
                'success': False,
                'message': '任务不存在或不是奖金池任务或已处理'
            }

        # 获取奖金池
        bonus_pool = self.db.query(BonusPool).filter(
            BonusPool.pool_date == task.bonus_pool_date
        ).first()

        if not bonus_pool:
            return {
                'success': False,
                'message': '奖金池不存在'
            }

        # 获取实际完成任务的学生ID（奖金池任务的target_student_id为NULL，需要使用accepted_by）
        if task.accepted_by:
            try:
                actual_student_id = int(task.accepted_by)  # accepted_by是字符串，需要转换为整数
            except (ValueError, TypeError):
                logger.error(f"奖金池任务 {task.id} 的accepted_by字段无效: {task.accepted_by}")
                actual_student_id = task.target_student_id
        else:
            actual_student_id = task.target_student_id

        # 获取学生返佣比例
        rebate_rate = self.virtual_order_service.get_student_rebate_rate(actual_student_id)

        # 计算学生实际收益和价值回收
        student_income = task.commission * rebate_rate  # 学生实际收益
        recycled_value = task.commission - student_income  # 价值回收

        # 奖金池只消耗学生实际收益部分
        old_remaining = bonus_pool.remaining_amount
        bonus_pool.remaining_amount -= student_income

        # 确保奖金池剩余金额不为负数
        if bonus_pool.remaining_amount < 0:
            bonus_pool.remaining_amount = Decimal('0')

        # 标记任务为已回收
        task.value_recycled = True
        task.recycled_at = datetime.now()
        bonus_pool.updated_at = datetime.now()

        self.db.commit()

        logger.info(f"奖金池任务 {task_id} 完成处理: 任务面值={task.commission}, 学生收益={student_income}, 价值回收={recycled_value}")
        logger.info(f"奖金池状态: {old_remaining} → {bonus_pool.remaining_amount}")

        # 尝试生成新的奖金池任务（严格1:1替换）
        regenerated_tasks = 0
        try:
            result = self.generate_single_bonus_pool_task(task.bonus_pool_date)
            if result['success']:
                regenerated_tasks = result['generated_tasks']
                logger.info(f"完成任务后重新生成了 {regenerated_tasks} 个奖金池任务")
        except Exception as e:
            logger.error(f"重新生成奖金池任务失败: {str(e)}")

        return {
            'success': True,
            'task_face_value': float(task.commission),
            'student_income': float(student_income),
            'recycled_value': float(recycled_value),
            'consumed_amount': float(student_income),
            'remaining_amount': float(bonus_pool.remaining_amount),
            'regenerated_tasks': regenerated_tasks
        }

    def get_bonus_pool_status(self, pool_date: date = None) -> Dict[str, Any]:
        """
        获取奖金池状态

        Args:
            pool_date: 奖金池日期，默认为今天

        Returns:
            Dict: 奖金池状态信息
        """
        if pool_date is None:
            pool_date = date.today()

        bonus_pool = self.db.query(BonusPool).filter(
            BonusPool.pool_date == pool_date
        ).first()

        if not bonus_pool:
            return {
                'exists': False,
                'date': pool_date.isoformat()
            }

        # 统计任务情况
        tasks_stats = self.db.query(
            func.count(Tasks.id).label('total_tasks'),
            func.sum(func.case([(Tasks.status == '0', 1)], else_=0)).label('pending_tasks'),
            func.sum(func.case([(Tasks.status == '1', 1)], else_=0)).label('accepted_tasks'),
            func.sum(func.case([(Tasks.status.in_(['3', '4']), 1)], else_=0)).label('completed_tasks')
        ).filter(
            Tasks.is_bonus_pool == True,
            Tasks.bonus_pool_date == pool_date
        ).first()

        # 获取昨天达标学生数
        yesterday = pool_date - timedelta(days=1)
        qualified_students = self.db.query(StudentDailyAchievement).filter(
            StudentDailyAchievement.achievement_date == yesterday,
            StudentDailyAchievement.is_achieved == True
        ).count()

        return {
            'exists': True,
            'date': pool_date.isoformat(),
            'carry_forward_amount': float(bonus_pool.carry_forward_amount),
            'new_expired_amount': float(bonus_pool.new_expired_amount),
            'total_amount': float(bonus_pool.total_amount),
            'generated_amount': float(bonus_pool.generated_amount),
            'completed_amount': float(bonus_pool.completed_amount),
            'remaining_amount': float(bonus_pool.remaining_amount),
            'qualified_students': qualified_students,
            'tasks': {
                'total': tasks_stats.total_tasks or 0,
                'pending': tasks_stats.pending_tasks or 0,
                'accepted': tasks_stats.accepted_tasks or 0,
                'completed': tasks_stats.completed_tasks or 0
            }
        }

    def get_daily_subsidy_stats(self, start_date: date = None, end_date: date = None, days: int = 7) -> Dict[str, Any]:
        """
        获取每日补贴统计数据

        Args:
            start_date: 开始日期，默认为7天前
            end_date: 结束日期，默认为今天
            days: 查询天数，当start_date和end_date都为None时使用，默认7天

        Returns:
            Dict: 每日补贴统计数据
        """
        try:
            # 确定查询日期范围
            if end_date is None:
                end_date = date.today()

            if start_date is None:
                start_date = end_date - timedelta(days=days-1)

            # 确保日期范围合理
            if start_date > end_date:
                start_date, end_date = end_date, start_date

            daily_stats = []
            current_date = start_date

            while current_date <= end_date:
                # 获取当日奖金池数据
                bonus_pool = self.db.query(BonusPool).filter(
                    BonusPool.pool_date == current_date
                ).first()

                # 统计当日生成的任务数（使用created_at）
                generated_stats = self.db.query(
                    func.count(Tasks.id).label('total_generated')
                ).filter(
                    Tasks.is_virtual == True,
                    func.date(Tasks.created_at) == current_date
                ).first()

                # 统计当日完成的任务数和金额（使用updated_at）
                completed_stats = self.db.query(
                    func.count(case((Tasks.status == '4', 1))).label('total_completed'),
                    func.sum(case((Tasks.status == '4', Tasks.commission), else_=0)).label('completed_amount')
                ).filter(
                    Tasks.is_virtual == True,
                    Tasks.status == '4',
                    func.date(Tasks.updated_at) == current_date
                ).first()

                # 合并统计结果
                task_stats = type('TaskStats', (), {
                    'total_generated': generated_stats.total_generated or 0,
                    'total_completed': completed_stats.total_completed or 0,
                    'completed_amount': completed_stats.completed_amount or 0
                })()

                # 统计当日学员补贴总金额（每个学员的固定补贴金额总和）
                from shared.models.virtual_order_pool import VirtualOrderPool
                subsidy_stats = self.db.query(
                    func.count(VirtualOrderPool.id).label('total_students'),
                    func.sum(VirtualOrderPool.total_subsidy).label('total_subsidy_amount')
                ).filter(
                    VirtualOrderPool.is_deleted == False,
                    func.date(VirtualOrderPool.created_at) <= current_date  # 在当日或之前创建的补贴池
                ).first()

                # 统计当日学生达标情况
                achievement_stats = self.db.query(
                    func.count(StudentDailyAchievement.id).label('total_students'),
                    func.count(case((StudentDailyAchievement.is_achieved == True, 1))).label('achieved_students'),
                    func.sum(StudentDailyAchievement.completed_amount).label('total_completed_amount')
                ).filter(
                    StudentDailyAchievement.achievement_date == current_date
                ).first()

                # 计算统计数据
                total_generated = task_stats.total_generated or 0
                total_completed = task_stats.total_completed or 0
                actual_earned_amount = float(task_stats.completed_amount or 0)

                # 计算当日补贴总金额（所有学员的固定补贴金额总和）
                total_subsidy_amount = float(subsidy_stats.total_subsidy_amount or 0)
                active_students_count = subsidy_stats.total_students or 0

                # 计算完成率
                completion_rate = 0.0
                if total_generated > 0:
                    completion_rate = round((total_completed / total_generated) * 100, 2)

                # 奖金池相关数据
                bonus_pool_data = {
                    'total_amount': 0.0,
                    'remaining_amount': 0.0,
                    'generated_amount': 0.0,
                    'completed_amount': 0.0
                }

                if bonus_pool:
                    bonus_pool_data = {
                        'total_amount': float(bonus_pool.total_amount),
                        'remaining_amount': float(bonus_pool.remaining_amount),
                        'generated_amount': float(bonus_pool.generated_amount),
                        'completed_amount': float(bonus_pool.completed_amount)
                    }

                daily_stat = {
                    'date': current_date.isoformat(),
                    'subsidy_total_amount': total_subsidy_amount,  # 每天补贴总金额（所有学员固定补贴总和）
                    'remaining_amount': bonus_pool_data['remaining_amount'],  # 剩余金额（奖金池）
                    'actual_earned_amount': actual_earned_amount,  # 实际获得金额
                    'completion_rate': completion_rate,  # 每天完成率
                    'tasks_generated': total_generated,  # 每天生成任务数
                    'tasks_completed': total_completed,  # 完成数
                    'active_students_count': active_students_count,  # 当日有补贴的学员数量
                    'bonus_pool': bonus_pool_data,  # 奖金池详细数据
                    'achievement_stats': {
                        'total_students': achievement_stats.total_students or 0,
                        'achieved_students': achievement_stats.achieved_students or 0,
                        'total_completed_amount': float(achievement_stats.total_completed_amount or 0)
                    }
                }

                daily_stats.append(daily_stat)
                current_date += timedelta(days=1)

            # 将日期倒序排列，最新的日期在前
            daily_stats.reverse()

            # 计算汇总统计
            total_subsidy = sum(stat['subsidy_total_amount'] for stat in daily_stats)
            total_earned = sum(stat['actual_earned_amount'] for stat in daily_stats)
            total_generated = sum(stat['tasks_generated'] for stat in daily_stats)
            total_completed = sum(stat['tasks_completed'] for stat in daily_stats)

            overall_completion_rate = 0.0
            if total_generated > 0:
                overall_completion_rate = round((total_completed / total_generated) * 100, 2)

            return {
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': len(daily_stats)
                },
                'daily_stats': daily_stats,
                'summary': {
                    'total_subsidy_amount': total_subsidy,
                    'total_earned_amount': total_earned,
                    'total_tasks_generated': total_generated,
                    'total_tasks_completed': total_completed,
                    'overall_completion_rate': overall_completion_rate
                }
            }

        except Exception as e:
            logger.error(f"获取每日补贴统计失败: {e}")
            raise BusinessException(
                code=500,
                message=f"获取每日补贴统计失败: {str(e)}",
                data=None
            )

    def export_daily_subsidy_stats(self, start_date: date = None, end_date: date = None, days: int = 7) -> bytes:
        """
        导出每日补贴统计数据为Excel

        Args:
            start_date: 开始日期，默认为7天前
            end_date: 结束日期，默认为今天
            days: 查询天数，当start_date和end_date都为None时使用，默认7天

        Returns:
            bytes: Excel文件内容
        """
        try:
            import pandas as pd
            import io

            # 获取统计数据
            stats_data = self.get_daily_subsidy_stats(start_date, end_date, days)

            # 准备Excel数据 - 完全参考studentIncome/export的方式
            data = []
            for daily_stat in stats_data['daily_stats']:
                data.append({
                    '日期': daily_stat['date'],
                    '补贴总金额': float(daily_stat['subsidy_total_amount']),
                    '剩余金额': float(daily_stat['remaining_amount']),
                    '实际获得金额': float(daily_stat['actual_earned_amount']),
                    '完成率(%)': daily_stat['completion_rate'],
                    '生成任务数': daily_stat['tasks_generated'],
                    '完成任务数': daily_stat['tasks_completed'],
                    '补贴学员数': daily_stat.get('active_students_count', 0),
                    '奖金池总金额': float(daily_stat['bonus_pool']['total_amount']),
                    '奖金池已生成金额': float(daily_stat['bonus_pool']['generated_amount']),
                    '奖金池已完成金额': float(daily_stat['bonus_pool']['completed_amount']),
                    '达标学生数': daily_stat['achievement_stats']['achieved_students'],
                    '总学生数': daily_stat['achievement_stats']['total_students'],
                    '导出时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

            # 如果没有数据，创建一个示例行
            if not data:
                data.append({
                    '日期': date.today().isoformat(),
                    '补贴总金额': 0.0,
                    '剩余金额': 0.0,
                    '实际获得金额': 0.0,
                    '完成率(%)': 0.0,
                    '生成任务数': 0,
                    '完成任务数': 0,
                    '补贴学员数': 0,
                    '奖金池总金额': 0.0,
                    '奖金池已生成金额': 0.0,
                    '奖金池已完成金额': 0.0,
                    '达标学生数': 0,
                    '总学生数': 0,
                    '导出时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

            # 创建DataFrame
            df = pd.DataFrame(data)

            # 创建Excel文件 - 完全按照studentIncome/export的方式
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # 写入每日统计数据
                df.to_excel(writer, sheet_name='每日补贴统计', index=False)

                # 获取工作表对象进行格式化
                worksheet = writer.sheets['每日补贴统计']

                # 设置列宽
                column_widths = {
                    'A': 12,  # 日期
                    'B': 15,  # 补贴总金额
                    'C': 12,  # 剩余金额
                    'D': 15,  # 实际获得金额
                    'E': 12,  # 完成率
                    'F': 12,  # 生成任务数
                    'G': 12,  # 完成任务数
                    'H': 12,  # 补贴学员数
                    'I': 15,  # 奖金池总金额
                    'J': 18,  # 奖金池已生成金额
                    'K': 18,  # 奖金池已完成金额
                    'L': 12,  # 达标学生数
                    'M': 12,  # 总学生数
                    'N': 20,  # 导出时间
                }

                for col, width in column_widths.items():
                    worksheet.column_dimensions[col].width = width

            output.seek(0)
            return output.getvalue()

        except Exception as e:
            logger.error(f"导出每日补贴统计失败: {e}")
            raise BusinessException(
                code=500,
                message=f"导出每日补贴统计失败: {str(e)}",
                data=None
            )
