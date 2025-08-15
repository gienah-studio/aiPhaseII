"""
虚拟客服管理服务
提供虚拟客服的完整生命周期管理功能
"""

import redis
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
import threading
import bcrypt

from shared.models.virtual_customer_service import VirtualCustomerService
from shared.models.original_user import OriginalUser
from shared.models.tasks import Tasks
from shared.exceptions import BusinessException
from .virtual_task_allocator import VirtualTaskAllocator

logger = logging.getLogger(__name__)

class VirtualCustomerServiceManager:
    """虚拟客服管理器"""
    
    def __init__(self, db: Session, redis_client: Optional[redis.Redis] = None):
        self.db = db
        self.redis_client = redis_client
        self.lock = threading.RLock()
        self.allocator = VirtualTaskAllocator(db, redis_client)
        
        # 缓存配置
        self.cache_ttl = 1800  # 30分钟
        
        # 管理配置
        self.config = {
            'default_password': '123456',
            'virtual_service_role': '6',  # 虚拟客服角色
            'max_services_per_batch': 100,  # 批量操作最大数量
        }
    
    def create_virtual_service(self, 
                             name: str, 
                             account: str, 
                             initial_password: Optional[str] = None) -> Dict[str, Any]:
        """
        创建虚拟客服
        
        Args:
            name: 客服姓名
            account: 客服账号
            initial_password: 初始密码
            
        Returns:
            Dict: 创建结果
        """
        try:
            with self.lock:
                # 检查账号是否已存在
                existing_user = self.db.query(OriginalUser).filter(
                    OriginalUser.username == account,
                    OriginalUser.isDeleted == False
                ).first()
                
                if existing_user:
                    raise BusinessException(
                        code=400,
                        message=f"账号 {account} 已存在",
                        data=None
                    )
                
                # 检查虚拟客服账号是否已存在
                existing_cs = self.db.query(VirtualCustomerService).filter(
                    VirtualCustomerService.account == account,
                    VirtualCustomerService.is_deleted == False
                ).first()
                
                if existing_cs:
                    raise BusinessException(
                        code=400,
                        message=f"虚拟客服账号 {account} 已存在",
                        data=None
                    )
                
                # 使用提供的密码或默认密码
                password = initial_password or self.config['default_password']
                
                # 对密码进行哈希处理
                salt = bcrypt.gensalt(rounds=10)
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
                
                # 创建用户账号
                user = OriginalUser(
                    username=account,
                    password=hashed_password,
                    role=self.config['virtual_service_role'],
                    lastLoginTime=None,
                    isDeleted=False
                )
                self.db.add(user)
                self.db.flush()  # 获取用户ID
                
                # 创建虚拟客服记录
                virtual_cs = VirtualCustomerService(
                    user_id=user.id,
                    name=name,
                    account=account,
                    initial_password=hashed_password,  # 存储加密密码
                    level=self.config['virtual_service_role'],
                    status='active',
                    is_deleted=False
                )
                self.db.add(virtual_cs)
                
                # 提交事务
                self.db.commit()
                
                # 清除缓存
                self._clear_cache()
                
                logger.info(f"成功创建虚拟客服: {name} ({account})")
                
                return {
                    'id': virtual_cs.id,
                    'user_id': user.id,
                    'name': name,
                    'account': account,
                    'level': self.config['virtual_service_role'],
                    'status': 'active',
                    'initial_password': password,  # 返回明文密码供前端显示
                    'created_at': virtual_cs.created_at.isoformat()
                }
                
        except BusinessException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建虚拟客服失败: {e}")
            raise BusinessException(
                code=500,
                message=f"创建虚拟客服失败: {str(e)}",
                data=None
            )
    
    def get_virtual_services(self, 
                           page: int = 1, 
                           size: int = 20, 
                           status: Optional[str] = None,
                           include_stats: bool = True) -> Dict[str, Any]:
        """
        获取虚拟客服列表
        
        Args:
            page: 页码
            size: 每页大小
            status: 状态过滤
            include_stats: 是否包含统计信息
            
        Returns:
            Dict: 虚拟客服列表和统计信息
        """
        try:
            # 构建查询
            query = self.db.query(VirtualCustomerService).filter(
                VirtualCustomerService.is_deleted == False
            )
            
            # 状态过滤
            if status:
                query = query.filter(VirtualCustomerService.status == status)
            
            # 总数统计
            total = query.count()
            
            # 分页查询
            offset = (page - 1) * size
            customer_services = query.order_by(
                VirtualCustomerService.created_at.desc()
            ).offset(offset).limit(size).all()
            
            # 转换为字典格式
            items = []
            for cs in customer_services:
                # 获取关联的用户信息
                user = self.db.query(OriginalUser).filter(
                    OriginalUser.id == cs.user_id,
                    OriginalUser.isDeleted == False
                ).first()
                
                item_data = {
                    'id': cs.id,
                    'user_id': cs.user_id,
                    'name': cs.name,
                    'account': cs.account,
                    'level': cs.level,
                    'status': cs.status,
                    'last_login_time': user.lastLoginTime.isoformat() if user and user.lastLoginTime else None,
                    'created_at': cs.created_at.isoformat(),
                    'updated_at': cs.updated_at.isoformat()
                }
                
                # 包含统计信息
                if include_stats:
                    # 统计任务数量
                    task_stats = self._get_service_task_stats(cs.user_id)
                    item_data.update(task_stats)
                
                items.append(item_data)
            
            result = {
                'items': items,
                'total': total,
                'page': page,
                'size': size
            }
            
            # 添加整体统计
            if include_stats:
                result['summary'] = self._get_services_summary()
            
            return result
            
        except Exception as e:
            logger.error(f"获取虚拟客服列表失败: {e}")
            raise BusinessException(
                code=500,
                message=f"获取虚拟客服列表失败: {str(e)}",
                data=None
            )
    
    def update_virtual_service(self, 
                             cs_id: int, 
                             update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新虚拟客服信息
        
        Args:
            cs_id: 虚拟客服ID
            update_data: 更新数据
            
        Returns:
            Dict: 更新结果
        """
        try:
            with self.lock:
                # 查找虚拟客服
                cs = self.db.query(VirtualCustomerService).filter(
                    VirtualCustomerService.id == cs_id,
                    VirtualCustomerService.is_deleted == False
                ).first()
                
                if not cs:
                    raise BusinessException(
                        code=404,
                        message="未找到该虚拟客服",
                        data=None
                    )
                
                # 更新允许的字段
                allowed_fields = ['name', 'status']
                updated_fields = []
                
                for field in allowed_fields:
                    if field in update_data and update_data[field] is not None:
                        old_value = getattr(cs, field)
                        new_value = update_data[field]
                        
                        if old_value != new_value:
                            setattr(cs, field, new_value)
                            updated_fields.append({
                                'field': field,
                                'old_value': old_value,
                                'new_value': new_value
                            })
                
                if updated_fields:
                    cs.updated_at = datetime.now()
                    self.db.commit()
                    
                    # 清除缓存
                    self._clear_cache()
                    
                    logger.info(f"虚拟客服 {cs.name} 更新完成: {updated_fields}")
                
                return {
                    'id': cs.id,
                    'name': cs.name,
                    'account': cs.account,
                    'status': cs.status,
                    'updated_fields': updated_fields,
                    'updated_at': cs.updated_at.isoformat()
                }
                
        except BusinessException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新虚拟客服失败: {e}")
            raise BusinessException(
                code=500,
                message=f"更新虚拟客服失败: {str(e)}",
                data=None
            )
    
    def delete_virtual_service(self, cs_id: int) -> Dict[str, Any]:
        """
        删除虚拟客服（软删除）并重新分配任务
        
        Args:
            cs_id: 虚拟客服ID
            
        Returns:
            Dict: 删除和重新分配结果
        """
        try:
            with self.lock:
                # 查找虚拟客服
                cs = self.db.query(VirtualCustomerService).filter(
                    VirtualCustomerService.id == cs_id,
                    VirtualCustomerService.is_deleted == False
                ).first()
                
                if not cs:
                    raise BusinessException(
                        code=404,
                        message="未找到该虚拟客服",
                        data=None
                    )
                
                # 记录删除前的信息
                service_info = {
                    'id': cs.id,
                    'name': cs.name,
                    'account': cs.account,
                    'user_id': cs.user_id
                }
                
                # 1. 处理任务重新分配
                reallocation_result = self.allocator.handle_service_deletion(cs_id)
                
                # 2. 软删除虚拟客服记录
                cs.is_deleted = True
                cs.status = 'deleted'
                cs.updated_at = datetime.now()
                
                # 3. 软删除关联的用户账号
                user = self.db.query(OriginalUser).filter(
                    OriginalUser.id == cs.user_id
                ).first()
                
                if user:
                    user.isDeleted = True
                
                # 提交事务
                self.db.commit()
                
                # 清除缓存
                self._clear_cache()
                
                logger.info(f"虚拟客服 {cs.name} 删除完成，任务重新分配结果: {reallocation_result}")
                
                return {
                    'service': service_info,
                    'deleted': True,
                    'reallocation': reallocation_result,
                    'deleted_at': datetime.now().isoformat()
                }
                
        except BusinessException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除虚拟客服失败: {e}")
            raise BusinessException(
                code=500,
                message=f"删除虚拟客服失败: {str(e)}",
                data=None
            )
    
    def batch_create_virtual_services(self, services_data: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        批量创建虚拟客服
        
        Args:
            services_data: 虚拟客服数据列表
                [{'name': str, 'account': str, 'password': str}, ...]
                
        Returns:
            Dict: 批量创建结果
        """
        try:
            if len(services_data) > self.config['max_services_per_batch']:
                raise BusinessException(
                    code=400,
                    message=f"批量创建数量不能超过{self.config['max_services_per_batch']}个",
                    data=None
                )
            
            created_services = []
            failed_services = []
            
            with self.lock:
                for data in services_data:
                    try:
                        result = self.create_virtual_service(
                            name=data['name'],
                            account=data['account'],
                            initial_password=data.get('password')
                        )
                        created_services.append(result)
                        
                    except Exception as e:
                        failed_services.append({
                            'name': data.get('name', ''),
                            'account': data.get('account', ''),
                            'error': str(e)
                        })
                        # 继续处理其他客服，不回滚已成功的
                        continue
            
            return {
                'total_requested': len(services_data),
                'created_count': len(created_services),
                'failed_count': len(failed_services),
                'created_services': created_services,
                'failed_services': failed_services if failed_services else None
            }
            
        except BusinessException:
            raise
        except Exception as e:
            logger.error(f"批量创建虚拟客服失败: {e}")
            raise BusinessException(
                code=500,
                message=f"批量创建虚拟客服失败: {str(e)}",
                data=None
            )
    
    def get_service_performance(self, cs_id: int, days: int = 30) -> Dict[str, Any]:
        """
        获取虚拟客服性能统计
        
        Args:
            cs_id: 虚拟客服ID
            days: 统计天数
            
        Returns:
            Dict: 性能统计数据
        """
        try:
            cs = self.db.query(VirtualCustomerService).filter(
                VirtualCustomerService.id == cs_id,
                VirtualCustomerService.is_deleted == False
            ).first()
            
            if not cs:
                raise BusinessException(
                    code=404,
                    message="未找到该虚拟客服",
                    data=None
                )
            
            # 计算时间范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 查询任务统计
            task_query = self.db.query(Tasks).filter(
                and_(
                    Tasks.founder_id == cs.user_id,
                    Tasks.is_virtual == True,
                    Tasks.created_at >= start_date,
                    Tasks.created_at <= end_date
                )
            )
            
            total_tasks = task_query.count()
            
            # 按状态统计
            status_stats = {}
            for status in ['0', '1', '2', '3', '4']:
                count = task_query.filter(Tasks.status == status).count()
                status_stats[status] = count
            
            # 计算总金额
            total_amount = self.db.query(func.sum(Tasks.commission)).filter(
                and_(
                    Tasks.founder_id == cs.user_id,
                    Tasks.is_virtual == True,
                    Tasks.created_at >= start_date,
                    Tasks.created_at <= end_date
                )
            ).scalar() or Decimal('0')
            
            # 计算完成率
            completed_tasks = status_stats.get('4', 0)
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            return {
                'service_id': cs.id,
                'service_name': cs.name,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'task_statistics': {
                    'total_tasks': total_tasks,
                    'total_amount': float(total_amount),
                    'status_breakdown': {
                        'pending': status_stats.get('0', 0),  # 未接单
                        'accepted': status_stats.get('1', 0),  # 已接单
                        'in_progress': status_stats.get('2', 0),  # 进行中
                        'submitted': status_stats.get('3', 0),  # 已提交
                        'completed': status_stats.get('4', 0)  # 已完成
                    },
                    'completion_rate': round(completion_rate, 2)
                },
                'daily_average': {
                    'tasks_per_day': round(total_tasks / days, 2),
                    'amount_per_day': round(float(total_amount) / days, 2)
                }
            }
            
        except BusinessException:
            raise
        except Exception as e:
            logger.error(f"获取虚拟客服性能统计失败: {e}")
            raise BusinessException(
                code=500,
                message=f"获取虚拟客服性能统计失败: {str(e)}",
                data=None
            )
    
    def _get_service_task_stats(self, user_id: int) -> Dict[str, Any]:
        """获取单个虚拟客服的任务统计"""
        try:
            # 查询任务统计
            total_tasks = self.db.query(Tasks).filter(
                and_(
                    Tasks.founder_id == user_id,
                    Tasks.is_virtual == True
                )
            ).count()
            
            pending_tasks = self.db.query(Tasks).filter(
                and_(
                    Tasks.founder_id == user_id,
                    Tasks.is_virtual == True,
                    Tasks.status.in_(['0', '1', '2'])
                )
            ).count()
            
            completed_tasks = self.db.query(Tasks).filter(
                and_(
                    Tasks.founder_id == user_id,
                    Tasks.is_virtual == True,
                    Tasks.status == '4'
                )
            ).count()
            
            # 计算总金额
            total_amount = self.db.query(func.sum(Tasks.commission)).filter(
                and_(
                    Tasks.founder_id == user_id,
                    Tasks.is_virtual == True
                )
            ).scalar() or Decimal('0')
            
            return {
                'task_stats': {
                    'total_tasks': total_tasks,
                    'pending_tasks': pending_tasks,
                    'completed_tasks': completed_tasks,
                    'total_amount': float(total_amount),
                    'completion_rate': round(
                        (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 2
                    )
                }
            }
            
        except Exception as e:
            logger.warning(f"获取任务统计失败: {e}")
            return {
                'task_stats': {
                    'total_tasks': 0,
                    'pending_tasks': 0,
                    'completed_tasks': 0,
                    'total_amount': 0.0,
                    'completion_rate': 0.0
                }
            }
    
    def _get_services_summary(self) -> Dict[str, Any]:
        """获取虚拟客服整体统计"""
        try:
            # 统计虚拟客服数量
            total_services = self.db.query(VirtualCustomerService).filter(
                VirtualCustomerService.is_deleted == False
            ).count()
            
            active_services = self.db.query(VirtualCustomerService).filter(
                and_(
                    VirtualCustomerService.is_deleted == False,
                    VirtualCustomerService.status == 'active'
                )
            ).count()
            
            # 统计新增客服（24小时内）
            recent_cutoff = datetime.now() - timedelta(hours=24)
            new_services = self.db.query(VirtualCustomerService).filter(
                and_(
                    VirtualCustomerService.is_deleted == False,
                    VirtualCustomerService.created_at >= recent_cutoff
                )
            ).count()
            
            return {
                'total_services': total_services,
                'active_services': active_services,
                'inactive_services': total_services - active_services,
                'new_services_24h': new_services
            }
            
        except Exception as e:
            logger.warning(f"获取虚拟客服统计失败: {e}")
            return {
                'total_services': 0,
                'active_services': 0,
                'inactive_services': 0,
                'new_services_24h': 0
            }
    
    def _clear_cache(self):
        """清除相关缓存"""
        if self.redis_client:
            try:
                # 清除虚拟客服相关缓存
                cache_keys = [
                    "virtual_services:*",
                    "allocation_stats:*"
                ]
                
                for pattern in cache_keys:
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        self.redis_client.delete(*keys)
                
                logger.info("已清除虚拟客服管理相关缓存")
                
            except Exception as e:
                logger.warning(f"清除缓存失败: {e}")