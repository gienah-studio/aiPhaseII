import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from shared.models.tasks import Tasks
from shared.models.studenttask import StudentTask
from shared.models.userinfo import UserInfo
from shared.models.agents import Agents
from shared.models.virtual_order_pool import VirtualOrderPool
from .virtual_order_service import VirtualOrderService

logger = logging.getLogger(__name__)

class BonusPoolAutoConfirmManager:
    """奖金池任务自动确认管理器"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_student_rebate_rate(self, student_id: int) -> Decimal:
        """
        获取学生的返佣比例（复制自VirtualOrderService）
        
        Args:
            student_id: 学生ID（roleId）
            
        Returns:
            Decimal: 返佣比例（如0.6表示60%）
        """
        # 查询学生信息
        student = self.db.query(UserInfo).filter(
            UserInfo.roleId == student_id
        ).first()
        
        if not student or not student.agentId:
            return Decimal('0.6')  # 默认返佣比例60%
        
        # 查询代理信息
        agent = self.db.query(Agents).filter(
            Agents.id == student.agentId
        ).first()
        
        if not agent or not agent.agent_rebate:
            return Decimal('0.6')  # 默认返佣比例60%
        
        # 处理返佣比例字符串
        rebate_str = agent.agent_rebate.replace('%', '') if '%' in agent.agent_rebate else agent.agent_rebate
        try:
            rebate_value = float(rebate_str)
            # 如果值大于1，说明是百分比形式（如60），需要除以100
            if rebate_value > 1:
                return Decimal(str(rebate_value / 100))
            else:
                return Decimal(str(rebate_value))
        except:
            return Decimal('0.6')  # 解析失败时使用默认值
    
    async def check_bonus_pool_auto_confirm_tasks(self, interval_hours: int = 1, max_batch_size: int = 50) -> Dict[str, Any]:
        """
        检查并自动确认提交超过指定时间的奖金池任务
        
        Args:
            interval_hours: 自动确认间隔时间（小时）
            max_batch_size: 最大批次大小
            
        Returns:
            Dict: 自动确认结果
        """
        try:
            logger.info(f"开始执行奖金池任务自动确认检查（间隔{interval_hours}小时）...")
            
            # 计算截止时间点
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=interval_hours)
            
            logger.info(f"奖金池自动确认配置: 间隔={interval_hours}小时, 最大批次={max_batch_size}")
            logger.info(f"时间信息: 当前时间={current_time}, 截止时间={cutoff_time}")
            
            # 查找需要自动确认的奖金池任务提交记录
            pending_submissions = self.db.query(StudentTask).join(
                Tasks, StudentTask.task_id == Tasks.id
            ).filter(
                and_(
                    # 使用creation_time字段，转换为datetime进行比较
                    func.STR_TO_DATE(StudentTask.creation_time, '%Y-%m-%d %H:%i:%s') <= cutoff_time,
                    StudentTask.content.isnot(None),  # 确实有提交内容
                    Tasks.is_virtual == True,  # 是虚拟任务
                    Tasks.is_bonus_pool == True,  # 是奖金池任务
                    Tasks.status.notin_(['4', '5'])  # 排除已完成(4)和终止(5)状态
                    # 删除 target_student_id.isnot(None) 条件，因为奖金池任务的target_student_id永远是None
                )
            ).limit(max_batch_size).all()
            
            if not pending_submissions:
                logger.info("没有发现需要自动确认的奖金池任务")
                return {
                    'success': True,
                    'confirmed_count': 0,
                    'failed_count': 0,
                    'message': '没有需要自动确认的奖金池任务'
                }
            
            logger.info(f"发现 {len(pending_submissions)} 个需要自动确认的奖金池任务")
            
            # 处理自动确认
            confirmed_count = 0
            failed_count = 0
            failed_details = []
            
            for submission in pending_submissions:
                try:
                    # 调用奖金池任务完成方法
                    result = await self.complete_bonus_pool_task(submission.task_id)
                    
                    if result['success']:
                        confirmed_count += 1
                        logger.info(f"奖金池任务自动确认成功: task_id={submission.task_id}, "
                                   f"student_id={result.get('student_id')}, "
                                   f"commission={result.get('task_commission')}, "
                                   f"remaining_value={result.get('remaining_task_value')}")
                    else:
                        failed_count += 1
                        failed_details.append(f"任务{submission.task_id}: {result.get('message', '未知错误')}")
                        logger.error(f"奖金池任务自动确认失败: task_id={submission.task_id}, "
                                    f"error={result.get('message')}")
                
                except Exception as e:
                    failed_count += 1
                    error_msg = str(e)
                    failed_details.append(f"任务{submission.task_id}: {error_msg}")
                    logger.error(f"奖金池任务自动确认异常: task_id={submission.task_id}, error={error_msg}")
                    continue
            
            logger.info(f"奖金池任务自动确认完成，成功确认 {confirmed_count} 个任务，失败 {failed_count} 个任务")
            
            return {
                'success': True,
                'confirmed_count': confirmed_count,
                'failed_count': failed_count,
                'failed_details': failed_details if failed_details else None,
                'message': f'成功确认 {confirmed_count} 个奖金池任务，失败 {failed_count} 个任务'
            }
            
        except Exception as e:
            logger.error(f"检查奖金池任务自动确认失败: {str(e)}")
            return {
                'success': False,
                'confirmed_count': 0,
                'failed_count': 0,
                'message': f'奖金池任务自动确认检查失败: {str(e)}'
            }
    
    async def complete_bonus_pool_task(self, task_id: int) -> Dict[str, Any]:
        """
        完成奖金池任务（参考普通虚拟任务逻辑但适配奖金池业务）
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict: 完成结果
        """
        try:
            # 1. 查找奖金池任务（参考虚拟任务的查找逻辑）
            task = self.db.query(Tasks).filter(
                and_(
                    Tasks.id == task_id,
                    Tasks.is_virtual == True,
                    Tasks.is_bonus_pool == True
                )
            ).first()
            
            if not task:
                return {
                    'success': False,
                    'message': f"未找到ID为{task_id}的奖金池任务"
                }
            
            # 2. 检查任务状态（完全相同的状态检查逻辑）
            if task.status in ['4', '5']:
                return {
                    'success': False,
                    'message': f"奖金池任务状态为{task.status}，无法重复完成"
                }
            
            # 3. 更新任务状态为已完成（完全相同）
            task.status = '4'
            task.payment_status = '4'
            task.value_recycled = True  # 奖金池任务立即标记为已回收，避免定时任务重复处理
            task.updated_at = datetime.now()
            
            # 4. 获取实际完成任务的学生ID和返佣比例
            if task.accepted_by:
                try:
                    actual_student_id = int(task.accepted_by)  # accepted_by是字符串，需要转换
                except (ValueError, TypeError):
                    logger.error(f"奖金池任务 {task.id} 的accepted_by字段无效: {task.accepted_by}")
                    return {
                        'success': False,
                        'message': f"无法获取任务接取者信息: {task.accepted_by}"
                    }
            else:
                return {
                    'success': False,
                    'message': "奖金池任务未被接取，无法确认完成"
                }
            
            rebate_rate = self.get_student_rebate_rate(actual_student_id)
            
            # 5. 计算剩余任务价值（完全相同的计算公式）
            student_actual_income = task.commission * rebate_rate  # 学生实际收入
            remaining_task_value = task.commission - student_actual_income  # 剩余价值
            
            logger.info(f"奖金池任务完成分析: 任务面值={task.commission}, 返佣比例={rebate_rate}, "
                       f"学生收入={student_actual_income}, 剩余价值={remaining_task_value}")
            
            # 6. 更新学生补贴池的奖金池相关字段
            pool = self.db.query(VirtualOrderPool).filter(
                VirtualOrderPool.student_id == actual_student_id,  # 使用实际的学生ID
                VirtualOrderPool.is_deleted == False
            ).first()
            
            if pool:
                # 更新奖金池任务完成金额和实际获得补贴
                pool.bonus_pool_completed_amount += task.commission
                pool.bonus_pool_consumed_subsidy += student_actual_income
                pool.updated_at = datetime.now()
                logger.info(f"更新学生 {actual_student_id} 奖金池统计: "
                           f"完成金额={pool.bonus_pool_completed_amount}, "
                           f"获得补贴={pool.bonus_pool_consumed_subsidy}")
            else:
                logger.warning(f"未找到学生 {actual_student_id} 的补贴池记录，无法更新奖金池统计")
            
            generated_tasks_info = []
            
            # 7. 判断任务是否为跨天完成（完全相同的判断逻辑）
            task_date = task.created_at.date()
            today = datetime.now().date()
            
            if task_date < today:
                # 跨天完成的任务：只确认完成，不重新生成任务
                logger.info(f"奖金池跨天任务完成: task_id={task.id}, 创建日期={task_date}, 当前日期={today}, 只确认完成不生成新任务")
            elif remaining_task_value > Decimal('0'):
                # 当天任务且有剩余价值：回收到奖金池并生成新的奖金池任务
                try:
                    from .bonus_pool_service import BonusPoolService
                    bonus_service = BonusPoolService(self.db)
                    
                    # 获取今日奖金池
                    today_pool = bonus_service.get_today_bonus_pool()
                    if today_pool:
                        # 将剩余价值加回奖金池
                        today_pool.remaining_amount += remaining_task_value
                        today_pool.updated_at = datetime.now()
                        logger.info(f"剩余价值 {remaining_task_value} 已加回奖金池，奖金池剩余: {today_pool.remaining_amount}")
                        
                        # 基于剩余价值生成新的奖金池任务（1:1替换）
                        if today_pool.remaining_amount > Decimal('0'):
                            generate_result = bonus_service.generate_bonus_pool_tasks(task_count=1)
                            if generate_result.get('success'):
                                generated_tasks_info.append({
                                    'type': 'bonus_pool_regeneration',
                                    'amount': float(remaining_task_value),
                                    'message': '基于剩余价值生成新奖金池任务'
                                })
                                logger.info(f"基于剩余价值重新生成奖金池任务: {generate_result}")
                            else:
                                logger.warning(f"生成新奖金池任务失败: {generate_result.get('message')}")
                    else:
                        logger.warning("未找到今日奖金池，无法回收剩余价值")
                
                except Exception as e:
                    logger.error(f"处理奖金池任务剩余价值失败: {str(e)}")
            
            # 提交事务
            self.db.commit()
            
            return {
                'success': True,
                'task_id': task_id,
                'student_id': actual_student_id,  # 使用实际的学生ID
                'task_commission': float(task.commission),
                'student_actual_income': float(student_actual_income),
                'remaining_task_value': float(remaining_task_value),
                'generated_tasks': generated_tasks_info,
                'completed_at': task.updated_at
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"完成奖金池任务失败: task_id={task_id}, error={str(e)}")
            return {
                'success': False,
                'message': f"完成奖金池任务失败: {str(e)}"
            }
    
    
    async def get_bonus_pool_auto_confirm_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        获取奖金池自动确认统计信息
        
        Args:
            days: 统计天数
            
        Returns:
            Dict: 统计信息
        """
        try:
            from datetime import date, timedelta
            
            start_date = date.today() - timedelta(days=days)
            end_date = date.today()
            
            # 统计指定天数内奖金池任务的确认情况
            bonus_pool_tasks = self.db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual == True,
                    Tasks.is_bonus_pool == True,
                    func.date(Tasks.created_at) >= start_date,
                    func.date(Tasks.created_at) <= end_date
                )
            ).all()
            
            total_tasks = len(bonus_pool_tasks)
            completed_tasks = len([task for task in bonus_pool_tasks if task.status == '4'])
            pending_tasks = len([task for task in bonus_pool_tasks if task.status in ['1', '2']])
            expired_tasks = len([task for task in bonus_pool_tasks if task.status == '5'])
            
            return {
                'period': f'{start_date} 到 {end_date}',
                'total_bonus_pool_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'pending_tasks': pending_tasks,
                'expired_tasks': expired_tasks,
                'completion_rate': round((completed_tasks / total_tasks * 100), 2) if total_tasks > 0 else 0,
                'auto_confirm_enabled': True
            }
            
        except Exception as e:
            logger.error(f"获取奖金池自动确认统计失败: {str(e)}")
            return {
                'period': f'最近{days}天',
                'total_bonus_pool_tasks': 0,
                'completed_tasks': 0,
                'pending_tasks': 0,
                'expired_tasks': 0,
                'completion_rate': 0,
                'error': str(e)
            }