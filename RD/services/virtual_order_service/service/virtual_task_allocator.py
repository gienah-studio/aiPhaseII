"""
虚拟任务分配器
实现基于虚拟客服的智能任务分配策略
"""

import redis
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from dataclasses import dataclass
import threading
from concurrent.futures import ThreadPoolExecutor

from shared.models.virtual_customer_service import VirtualCustomerService
from shared.models.tasks import Tasks
from shared.models.userinfo import UserInfo
from shared.exceptions import BusinessException

logger = logging.getLogger(__name__)

@dataclass
class VirtualServiceAllocation:
    """虚拟客服分配信息"""
    service_id: int
    service_name: str
    user_id: int
    current_task_count: int
    allocated_amount: Decimal
    priority: int  # 优先级，数字越小优先级越高
    is_new: bool  # 是否为新增的虚拟客服

@dataclass
class AllocationResult:
    """分配结果"""
    success: bool
    allocated_tasks: List[Dict[str, Any]]
    total_amount: Decimal
    error_message: Optional[str] = None

class VirtualTaskAllocator:
    """虚拟任务分配器"""
    
    def __init__(self, db: Session, redis_client: Optional[redis.Redis] = None):
        self.db = db
        self.redis_client = redis_client
        self.cache_ttl = 1800  # 缓存30分钟
        self.lock = threading.RLock()  # 可重入锁，确保线程安全
        
        # 分配策略配置
        self.config = {
            # 移除虚拟客服最大任务数限制，虚拟客服可以接受无限任务
            'min_task_amount': Decimal('5'),  # 最小任务金额
            'max_task_amount': Decimal('25'),  # 最大任务金额
            'new_service_priority_boost': 100,  # 新增客服优先级提升
            'allocation_batch_size': 20,  # 批量分配大小
        }
    
    def get_active_virtual_services(self, use_cache: bool = True) -> List[VirtualServiceAllocation]:
        """
        获取所有激活状态的虚拟客服，支持缓存
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            List[VirtualServiceAllocation]: 虚拟客服分配信息列表
        """
        cache_key = "virtual_services:active"
        
        # 尝试从缓存获取
        if use_cache and self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    services_data = json.loads(cached_data)
                    return [VirtualServiceAllocation(**data) for data in services_data]
            except Exception as e:
                logger.warning(f"从缓存获取虚拟客服失败: {e}")
        
        # 从数据库查询
        with self.lock:
            services = self.db.query(VirtualCustomerService).filter(
                VirtualCustomerService.status == 'active',
                VirtualCustomerService.is_deleted == False
            ).all()
            
            allocations = []
            for service in services:
                # 统计当前任务数量（未完成的虚拟任务）
                current_task_count = self.db.query(Tasks).filter(
                    and_(
                        Tasks.founder_id == service.user_id,
                        Tasks.is_virtual == True,
                        Tasks.status.in_(['0', '1', '2'])  # 未接单、已接单、进行中
                    )
                ).count()
                
                # 判断是否为新增客服（24小时内创建的）
                is_new = (datetime.now() - service.created_at).total_seconds() < 86400
                
                # 计算优先级（任务数越少优先级越高）
                priority = current_task_count
                if is_new:
                    priority -= self.config['new_service_priority_boost']  # 新增客服优先级提升
                
                allocation = VirtualServiceAllocation(
                    service_id=service.id,
                    service_name=service.name,
                    user_id=service.user_id,
                    current_task_count=current_task_count,
                    allocated_amount=Decimal('0'),
                    priority=priority,
                    is_new=is_new
                )
                allocations.append(allocation)
            
            # 按优先级排序（优先级数字越小越优先）
            allocations.sort(key=lambda x: x.priority)
        
        # 缓存结果
        if self.redis_client:
            try:
                cache_data = [
                    {
                        'service_id': alloc.service_id,
                        'service_name': alloc.service_name,
                        'user_id': alloc.user_id,
                        'current_task_count': alloc.current_task_count,
                        'allocated_amount': float(alloc.allocated_amount),
                        'priority': alloc.priority,
                        'is_new': alloc.is_new
                    }
                    for alloc in allocations
                ]
                self.redis_client.setex(
                    cache_key, 
                    self.cache_ttl, 
                    json.dumps(cache_data)
                )
            except Exception as e:
                logger.warning(f"缓存虚拟客服数据失败: {e}")
        
        return allocations
    
    def calculate_relative_average_allocation(self, 
                                           total_amount: Decimal, 
                                           services: List[VirtualServiceAllocation]) -> Dict[int, Decimal]:
        """
        计算相对平均分配策略
        
        Args:
            total_amount: 总金额
            services: 虚拟客服列表
            
        Returns:
            Dict[int, Decimal]: 每个虚拟客服分配的金额 {user_id: amount}
        """
        if not services:
            return {}
        
        # 虚拟客服没有最大任务数限制，所有激活的客服都可用
        available_services = services

        if not available_services:
            raise BusinessException(
                code=400,
                message="没有可用的虚拟客服",
                data=None
            )
        
        allocation = {}
        remaining_amount = total_amount
        
        # 计算权重：任务数越少权重越高，新增客服有额外权重
        total_weight = Decimal('0')
        for service in available_services:
            # 基础权重：使用反比例计算，任务数越少权重越高
            # 使用 100 作为基数，避免权重为0或负数
            base_weight = max(1, 100 - service.current_task_count)

            # 新增客服权重加成
            if service.is_new:
                weight = base_weight * Decimal('2')  # 新增客服权重翻倍
            else:
                weight = base_weight

            total_weight += weight
            allocation[service.user_id] = weight
        
        # 按权重分配金额
        final_allocation = {}
        for user_id, weight in allocation.items():
            if total_weight > 0:
                allocated_amount = (weight / total_weight) * total_amount
                # 确保分配金额至少为最小任务金额
                if allocated_amount >= self.config['min_task_amount']:
                    final_allocation[user_id] = allocated_amount
                    remaining_amount -= allocated_amount
        
        # 处理剩余金额：分配给权重最高的客服
        if remaining_amount > 0 and final_allocation:
            # 找到权重最高的客服
            max_weight_user = max(allocation.keys(), key=lambda x: allocation[x])
            if max_weight_user in final_allocation:
                final_allocation[max_weight_user] += remaining_amount
        
        return final_allocation
    
    def allocate_tasks_to_services(self,
                                 total_amount: Decimal,
                                 student_id: int,
                                 student_name: str,
                                 on_demand: bool = False) -> AllocationResult:
        """
        为虚拟客服分配任务（修复版：先计算标准任务金额，再分配给客服）

        Args:
            total_amount: 总任务金额
            student_id: 学生ID
            student_name: 学生姓名
            on_demand: 是否按需生成（True=生成1-2个任务，False=全部生成）

        Returns:
            AllocationResult: 分配结果
        """
        try:
            with self.lock:
                # 获取活跃的虚拟客服
                services = self.get_active_virtual_services()

                if not services:
                    return AllocationResult(
                        success=False,
                        allocated_tasks=[],
                        total_amount=Decimal('0'),
                        error_message="没有可用的虚拟客服"
                    )

                # 根据模式计算任务金额列表
                from .virtual_order_service import VirtualOrderService
                service = VirtualOrderService(self.db)

                if on_demand:
                    # 按需生成：只生成1-2个任务
                    task_amounts = service.calculate_on_demand_task_amounts(total_amount)
                else:
                    # 传统模式：生成所有任务
                    task_amounts = service.calculate_task_amounts(total_amount)

                if not task_amounts:
                    return AllocationResult(
                        success=False,
                        allocated_tasks=[],
                        total_amount=Decimal('0'),
                        error_message="无法计算任务金额分配"
                    )

                # 虚拟客服没有最大任务数限制，所有激活的客服都可用
                available_services = services

                if not available_services:
                    return AllocationResult(
                        success=False,
                        allocated_tasks=[],
                        total_amount=Decimal('0'),
                        error_message="没有可用的虚拟客服"
                    )

                # 按优先级排序（任务数少的优先，新客服优先）
                available_services.sort(key=lambda x: x.priority)

                # 将任务轮流分配给虚拟客服
                allocated_tasks = []
                service_index = 0

                for amount in task_amounts:
                    # 选择当前客服
                    selected_service = available_services[service_index % len(available_services)]

                    # 为该客服创建单个任务（如果图片不足则停止）
                    task = service.create_virtual_task(student_id, student_name, amount)

                    if task is None:
                        logger.warning(f"图片资源不足，停止为学生 {student_name} 分配虚拟任务")
                        break

                    # 设置创建者为虚拟客服
                    task.founder_id = selected_service.user_id
                    task.founder = selected_service.service_name

                    # 保存到数据库
                    self.db.add(task)

                    allocated_tasks.append({
                        'id': task.id,
                        'amount': float(amount),
                        'founder_id': selected_service.user_id,
                        'founder': selected_service.service_name,
                        'student_id': student_id,
                        'summary': task.summary,
                        'order_number': task.order_number
                    })

                    # 轮转到下一个客服
                    service_index += 1

                # 清除相关缓存
                self._clear_cache()

                return AllocationResult(
                    success=True,
                    allocated_tasks=allocated_tasks,
                    total_amount=total_amount
                )

        except Exception as e:
            logger.error(f"分配任务失败: {e}")
            return AllocationResult(
                success=False,
                allocated_tasks=[],
                total_amount=Decimal('0'),
                error_message=str(e)
            )
    

    
    def handle_service_deletion(self, deleted_service_id: int) -> Dict[str, Any]:
        """
        处理虚拟客服删除后的任务重新分配
        
        Args:
            deleted_service_id: 被删除的虚拟客服ID
            
        Returns:
            Dict: 重新分配结果
        """
        try:
            with self.lock:
                # 获取被删除虚拟客服的信息
                deleted_service = self.db.query(VirtualCustomerService).filter(
                    VirtualCustomerService.id == deleted_service_id
                ).first()
                
                if not deleted_service:
                    return {
                        'success': False,
                        'message': '未找到指定的虚拟客服'
                    }
                
                # 查找该客服的未完成任务
                pending_tasks = self.db.query(Tasks).filter(
                    and_(
                        Tasks.founder_id == deleted_service.user_id,
                        Tasks.is_virtual == True,
                        Tasks.status.in_(['0', '1', '2'])  # 未接单、已接单、进行中
                    )
                ).all()
                
                if not pending_tasks:
                    return {
                        'success': True,
                        'message': '该虚拟客服没有待处理的任务',
                        'redistributed_tasks': 0
                    }
                
                # 按学生分组任务
                student_tasks = {}
                for task in pending_tasks:
                    student_id = task.target_student_id
                    if student_id not in student_tasks:
                        student_tasks[student_id] = []
                    student_tasks[student_id].append(task)
                
                redistributed_count = 0
                
                # 为每个学生重新分配任务
                for student_id, tasks in student_tasks.items():
                    # 删除原任务
                    total_amount = sum(task.commission for task in tasks)
                    
                    for task in tasks:
                        self.db.delete(task)
                    
                    # 获取学生名称
                    student = self.db.query(UserInfo).filter(
                        UserInfo.roleId == student_id
                    ).first()
                    
                    student_name = student.name if student else f"学生{student_id}"
                    
                    # 重新分配任务
                    result = self.allocate_tasks_to_services(
                        total_amount, student_id, student_name
                    )
                    
                    if result.success:
                        redistributed_count += len(result.allocated_tasks)
                
                # 清除缓存
                self._clear_cache()
                
                return {
                    'success': True,
                    'message': f'成功重新分配 {len(pending_tasks)} 个任务',
                    'redistributed_tasks': redistributed_count,
                    'affected_students': len(student_tasks)
                }
                
        except Exception as e:
            logger.error(f"处理虚拟客服删除失败: {e}")
            self.db.rollback()
            return {
                'success': False,
                'message': f'重新分配任务失败: {str(e)}'
            }
    
    def get_allocation_statistics(self) -> Dict[str, Any]:
        """
        获取分配统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            # 获取虚拟客服列表
            services = self.get_active_virtual_services(use_cache=False)
            
            stats = {
                'total_services': len(services),
                'new_services': sum(1 for s in services if s.is_new),
                'service_details': []
            }
            
            for service in services:
                # 计算该客服的任务总金额
                total_amount = self.db.query(func.sum(Tasks.commission)).filter(
                    and_(
                        Tasks.founder_id == service.user_id,
                        Tasks.is_virtual == True,
                        Tasks.status.in_(['0', '1', '2'])
                    )
                ).scalar() or Decimal('0')
                
                stats['service_details'].append({
                    'service_id': service.service_id,
                    'service_name': service.service_name,
                    'user_id': service.user_id,
                    'current_task_count': service.current_task_count,
                    'total_amount': float(total_amount),
                    'priority': service.priority,
                    'is_new': service.is_new
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"获取分配统计失败: {e}")
            raise BusinessException(
                code=500,
                message=f"获取分配统计失败: {str(e)}",
                data=None
            )
    
    def _clear_cache(self):
        """清除相关缓存"""
        if self.redis_client:
            try:
                # 清除虚拟客服缓存
                self.redis_client.delete("virtual_services:active")
                logger.info("已清除虚拟客服缓存")
            except Exception as e:
                logger.warning(f"清除缓存失败: {e}")
    
    def batch_allocate_tasks(self, 
                           allocation_requests: List[Dict[str, Any]]) -> List[AllocationResult]:
        """
        批量分配任务
        
        Args:
            allocation_requests: 分配请求列表
                [{'total_amount': Decimal, 'student_id': int, 'student_name': str}, ...]
                
        Returns:
            List[AllocationResult]: 分配结果列表
        """
        results = []
        
        # 使用线程池进行并发处理
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            
            for request in allocation_requests:
                # 检查是否为按需生成
                on_demand = request.get('on_demand', False)

                future = executor.submit(
                    self.allocate_tasks_to_services,
                    request['total_amount'],
                    request['student_id'],
                    request['student_name'],
                    on_demand
                )
                futures.append(future)
            
            # 收集结果
            for future in futures:
                try:
                    result = future.result(timeout=30)  # 30秒超时
                    results.append(result)
                except Exception as e:
                    logger.error(f"批量分配任务失败: {e}")
                    results.append(AllocationResult(
                        success=False,
                        allocated_tasks=[],
                        total_amount=Decimal('0'),
                        error_message=str(e)
                    ))
        
        return results