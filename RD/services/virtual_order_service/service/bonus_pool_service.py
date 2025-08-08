from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from shared.models.bonus_pool import BonusPool
from shared.models.student_daily_achievement import StudentDailyAchievement
from shared.models.system_config import SystemConfig
from shared.models.tasks import Tasks
from shared.models.userinfo import UserInfo
from shared.exceptions import BusinessException
from .virtual_order_service import VirtualOrderService

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
        
        # 计算当日完成的虚拟任务金额
        # 只统计已完成的虚拟任务
        completed_amount = self.db.query(func.sum(Tasks.commission)).filter(
            Tasks.target_student_id == student_id,
            Tasks.is_virtual == True,
            Tasks.payment_status.in_(['3', '4']),  # 可结算或已结算
            func.date(Tasks.created_at) == target_date
        ).scalar() or Decimal('0')
        
        # 获取每日目标
        daily_target = self.get_daily_target()
        
        # 判断是否达标
        is_achieved = completed_amount >= daily_target
        
        return {
            'student_id': student_id,
            'student_name': student.name,
            'achievement_date': target_date,
            'daily_target': daily_target,
            'completed_amount': completed_amount,
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
                    # 更新现有记录
                    achievement.completed_amount = achievement_data['completed_amount']
                    achievement.is_achieved = achievement_data['is_achieved']
                else:
                    # 创建新记录
                    achievement = StudentDailyAchievement(
                        student_id=student.roleId,
                        student_name=achievement_data['student_name'],
                        achievement_date=target_date,
                        daily_target=achievement_data['daily_target'],
                        completed_amount=achievement_data['completed_amount'],
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
        
        # 收集昨天的过期任务
        yesterday = pool_date - timedelta(days=1)
        expired_data = self.collect_expired_virtual_tasks(yesterday)
        
        # 查找或创建今日奖金池
        bonus_pool = self.db.query(BonusPool).filter(
            BonusPool.pool_date == pool_date
        ).first()
        
        if bonus_pool:
            # 更新现有奖金池
            bonus_pool.new_expired_amount += Decimal(str(expired_data['expired_normal_amount']))
            bonus_pool.carry_forward_amount += Decimal(str(expired_data['expired_bonus_amount']))
            bonus_pool.total_amount = bonus_pool.new_expired_amount + bonus_pool.carry_forward_amount
            bonus_pool.remaining_amount = bonus_pool.total_amount - bonus_pool.generated_amount
        else:
            # 创建新的奖金池
            bonus_pool = BonusPool(
                pool_date=pool_date,
                carry_forward_amount=Decimal(str(expired_data['expired_bonus_amount'])),
                new_expired_amount=Decimal(str(expired_data['expired_normal_amount'])),
                total_amount=Decimal(str(expired_data['total_expired_amount'])),
                generated_amount=Decimal('0'),
                completed_amount=Decimal('0'),
                remaining_amount=Decimal(str(expired_data['total_expired_amount']))
            )
            self.db.add(bonus_pool)
        
        self.db.commit()
        return bonus_pool
    
    def generate_bonus_pool_tasks(self, pool_date: date = None) -> Dict[str, Any]:
        """
        生成奖金池任务
        
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
        ).count()
        
        if qualified_students == 0:
            return {
                'success': False,
                'message': '没有达标学生，无法生成奖金池任务',
                'generated_tasks': 0
            }
        
        # 使用虚拟任务生成逻辑计算任务分配
        task_amounts = self.virtual_order_service.calculate_task_amounts(bonus_pool.remaining_amount)
        
        # 生成任务
        generated_tasks = []
        now = datetime.now()
        
        for amount in task_amounts:
            # 生成随机任务内容
            task_content = self.virtual_order_service.generate_random_task_content()
            
            task = Tasks(
                summary=task_content['summary'],
                requirement=task_content['requirement'],
                reference_images='',
                source='奖金池',
                order_number=self.virtual_order_service.generate_order_number(),
                commission=amount,
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
                payment_status='0',
                task_level='D',
                is_virtual=True,
                is_bonus_pool=True,  # 标记为奖金池任务
                bonus_pool_date=pool_date,
                target_student_id=None,  # 不限定特定学生
                is_renew='0'
            )
            
            self.db.add(task)
            generated_tasks.append(task)
        
        # 更新奖金池状态
        bonus_pool.generated_amount += bonus_pool.remaining_amount
        bonus_pool.remaining_amount = Decimal('0')
        
        self.db.commit()
        
        return {
            'success': True,
            'message': '奖金池任务生成成功',
            'pool_date': pool_date.isoformat(),
            'generated_tasks': len(generated_tasks),
            'total_amount': float(sum(task.commission for task in generated_tasks)),
            'qualified_students': qualified_students
        }
    
    def process_expired_bonus_tasks(self) -> Dict[str, Any]:
        """
        处理过期的奖金池任务（每3小时执行）
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
                'recycled_amount': 0
            }
        
        # 计算回收金额
        recycled_amount = sum(task.commission for task in expired_tasks)
        
        # 标记任务为过期
        for task in expired_tasks:
            task.status = '5'  # 终止/过期
            task.message = '奖金池任务过期，金额重新生成'
        
        # 更新奖金池
        bonus_pool = self.db.query(BonusPool).filter(
            BonusPool.pool_date == today
        ).first()
        
        if bonus_pool:
            bonus_pool.generated_amount -= recycled_amount
            bonus_pool.remaining_amount += recycled_amount
        
        self.db.commit()
        
        # 重新生成任务
        self.generate_bonus_pool_tasks(today)
        
        return {
            'processed_tasks': len(expired_tasks),
            'recycled_amount': float(recycled_amount)
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