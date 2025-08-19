from sqlalchemy.orm import Session
from shared.models.system_config import SystemConfig
from typing import Union
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ConfigService:
    """系统配置服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_config(self, key: str, default_value: Union[str, int, float, dict] = None) -> Union[str, int, float, dict, None]:
        """
        获取配置值
        
        Args:
            key: 配置键
            default_value: 默认值
            
        Returns:
            配置值，如果不存在则返回默认值
        """
        try:
            config = self.db.query(SystemConfig).filter(
                SystemConfig.config_key == key
            ).first()
            
            if not config:
                return default_value
            
            # 根据配置类型返回相应的值
            if config.config_type == 'number':
                return float(config.config_value)
            elif config.config_type == 'json':
                return json.loads(config.config_value)
            elif config.config_type == 'boolean':
                return config.config_value.lower() in ('true', '1', 'yes', 'on')
            else:
                # 对于字符串类型，如果值看起来像布尔值，则转换为布尔值
                if config.config_value.lower() in ('true', 'false'):
                    return config.config_value.lower() == 'true'
                return config.config_value
                
        except Exception as e:
            logger.error(f"获取配置失败: key={key}, error={str(e)}")
            return default_value
    
    def set_config(self, key: str, value: Union[str, int, float, dict],
                   config_type: str = 'string', description: str = None, init_only: bool = False) -> bool:
        """
        设置配置值

        Args:
            key: 配置键
            value: 配置值
            config_type: 配置类型 (string, number, json, boolean)
            description: 配置描述
            init_only: 是否仅在配置不存在时才设置（用于初始化，避免覆盖用户配置）

        Returns:
            是否设置成功
        """
        try:
            # 查找现有配置
            config = self.db.query(SystemConfig).filter(
                SystemConfig.config_key == key
            ).first()

            # 如果是初始化模式且配置已存在，则跳过
            if init_only and config:
                logger.info(f"配置 {key} 已存在，跳过初始化")
                return True

            # 转换值为字符串
            if config_type == 'json':
                config_value = json.dumps(value, ensure_ascii=False)
            elif config_type == 'boolean':
                config_value = str(bool(value)).lower()
            else:
                config_value = str(value)
            
            # 检查是否是虚拟任务生成配置的变更（从false到true）
            old_value = None
            if config and key == 'virtual_task_generation_enabled':
                old_value = config.config_value.lower() in ('true', '1', 'yes', 'on')

            if config:
                # 更新现有配置
                config.config_value = config_value
                config.config_type = config_type
                if description:
                    config.description = description
            else:
                # 创建新配置
                config = SystemConfig(
                    config_key=key,
                    config_value=config_value,
                    config_type=config_type,
                    description=description or f"配置项: {key}"
                )
                self.db.add(config)

            self.db.commit()

            # 如果虚拟任务生成配置从false变为true，触发补贴池任务生成
            if (key == 'virtual_task_generation_enabled' and
                config_type == 'boolean' and
                old_value is False and
                str(value).lower() == 'true'):
                logger.info("检测到虚拟任务生成配置从禁用变为启用，开始处理未生成任务的补贴池...")
                self._process_ungenerated_subsidy_pools()

            return True
            
        except Exception as e:
            logger.error(f"设置配置失败: key={key}, value={value}, error={str(e)}")
            self.db.rollback()
            return False
    
    def get_auto_confirm_config(self) -> dict:
        """
        获取自动确认相关配置

        Returns:
            自动确认配置字典
        """
        return {
            'enabled': self.get_config('auto_confirm_enabled', True),
            'interval_hours': self.get_config('auto_confirm_interval_hours', 1.0),
            'max_batch_size': self.get_config('auto_confirm_max_batch_size', 100)
        }

    def get_virtual_task_generation_config(self) -> dict:
        """
        获取虚拟任务生成相关配置

        Returns:
            虚拟任务生成配置字典
        """
        return {
            'enabled': self.get_config('virtual_task_generation_enabled', True),
            'daily_bonus_enabled': self.get_config('virtual_task_daily_bonus_enabled', True),
            'expired_task_regeneration_enabled': self.get_config('virtual_task_expired_regeneration_enabled', True),
            'value_recycling_enabled': self.get_config('virtual_task_value_recycling_enabled', True),
            'bonus_pool_task_enabled': self.get_config('virtual_task_bonus_pool_enabled', True)
        }
    
    def init_auto_confirm_config(self):
        """初始化自动确认配置（仅在配置不存在时设置默认值）"""
        try:
            # 设置默认配置（仅在不存在时）
            self.set_config(
                'auto_confirm_enabled',
                True,
                'string',
                '是否启用虚拟任务自动确认功能',
                init_only=True
            )

            self.set_config(
                'auto_confirm_interval_hours',
                1.0,
                'number',
                '自动确认时间间隔（小时）',
                init_only=True
            )

            self.set_config(
                'auto_confirm_max_batch_size',
                100,
                'number',
                '单次自动确认最大处理数量',
                init_only=True
            )

            logger.info("自动确认配置初始化完成")

        except Exception as e:
            logger.error(f"初始化自动确认配置失败: {str(e)}")

    def init_virtual_task_generation_config(self):
        """初始化虚拟任务生成配置（仅在配置不存在时设置默认值）"""
        try:
            # 设置默认配置（仅在不存在时）
            self.set_config(
                'virtual_task_generation_enabled',
                True,
                'boolean',
                '是否启用虚拟任务生成功能（总开关）',
                init_only=True
            )

            self.set_config(
                'virtual_task_daily_bonus_enabled',
                True,
                'boolean',
                '是否启用每日奖金池任务生成',
                init_only=True
            )

            self.set_config(
                'virtual_task_expired_regeneration_enabled',
                True,
                'boolean',
                '是否启用过期任务重新生成',
                init_only=True
            )

            self.set_config(
                'virtual_task_value_recycling_enabled',
                True,
                'boolean',
                '是否启用价值回收任务生成',
                init_only=True
            )

            self.set_config(
                'virtual_task_bonus_pool_enabled',
                True,
                'boolean',
                '是否启用奖金池任务生成',
                init_only=True
            )

            logger.info("虚拟任务生成配置初始化完成")

        except Exception as e:
            logger.error(f"初始化虚拟任务生成配置失败: {str(e)}")

    def _process_ungenerated_subsidy_pools(self):
        """
        处理未生成任务的补贴池
        仅处理有剩余补贴但从未生成过任何虚拟任务的补贴池
        """
        try:
            from shared.models.virtual_order_pool import VirtualOrderPool
            from shared.models.tasks import Tasks
            from sqlalchemy import and_, exists

            # 查找有剩余补贴但从未生成过任何虚拟任务的补贴池
            ungenerated_pools = self.db.query(VirtualOrderPool).filter(
                and_(
                    VirtualOrderPool.is_deleted == False,
                    VirtualOrderPool.remaining_amount > 0,
                    # 关键条件：该学生从未生成过任何虚拟任务
                    ~exists().where(
                        and_(
                            Tasks.is_virtual == True,
                            Tasks.target_student_id == VirtualOrderPool.student_id
                        )
                    )
                )
            ).all()

            if not ungenerated_pools:
                logger.info("没有发现需要处理的未生成任务的补贴池")
                return

            logger.info(f"发现 {len(ungenerated_pools)} 个需要生成任务的补贴池")

            # 导入虚拟订单服务
            from .virtual_order_service import VirtualOrderService
            service = VirtualOrderService(self.db)

            processed_count = 0
            total_generated_tasks = 0

            for pool in ungenerated_pools:
                try:
                    logger.info(f"为学生 {pool.student_name}(ID:{pool.student_id}) 生成任务，剩余补贴: {pool.remaining_amount}")

                    # 使用虚拟客服分配策略按需生成任务（1-2个任务）
                    result = service.generate_virtual_tasks_with_service_allocation(
                        pool.student_id, pool.student_name, pool.remaining_amount, on_demand=True
                    )

                    if result['success']:
                        task_count = len(result['tasks'])
                        total_generated_tasks += task_count
                        processed_count += 1

                        # 更新补贴池剩余金额（按需生成模式）
                        generated_amount = result['total_amount']
                        pool.remaining_amount -= generated_amount
                        pool.updated_at = datetime.now()

                        logger.info(f"成功为学生 {pool.student_name} 生成了 {task_count} 个任务，总金额: {result['total_amount']}，剩余补贴: {pool.remaining_amount}")
                    else:
                        logger.error(f"为学生 {pool.student_name} 生成任务失败: {result['message']}")

                except Exception as e:
                    logger.error(f"处理学生 {pool.student_name} 的补贴池时出错: {str(e)}")
                    continue

            # 提交所有更改
            self.db.commit()

            logger.info(f"补贴池任务生成完成: 处理了 {processed_count} 个补贴池，共生成 {total_generated_tasks} 个任务")

        except Exception as e:
            logger.error(f"处理未生成任务的补贴池失败: {str(e)}")
            self.db.rollback()
