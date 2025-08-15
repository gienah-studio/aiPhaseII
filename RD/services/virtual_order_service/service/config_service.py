from sqlalchemy.orm import Session
from shared.models.system_config import SystemConfig
from typing import Union
import json
import logging

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
            else:
                return config.config_value
                
        except Exception as e:
            logger.error(f"获取配置失败: key={key}, error={str(e)}")
            return default_value
    
    def set_config(self, key: str, value: Union[str, int, float, dict], 
                   config_type: str = 'string', description: str = None) -> bool:
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            config_type: 配置类型 (string, number, json)
            description: 配置描述
            
        Returns:
            是否设置成功
        """
        try:
            # 查找现有配置
            config = self.db.query(SystemConfig).filter(
                SystemConfig.config_key == key
            ).first()
            
            # 转换值为字符串
            if config_type == 'json':
                config_value = json.dumps(value, ensure_ascii=False)
            else:
                config_value = str(value)
            
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
    
    def init_auto_confirm_config(self):
        """初始化自动确认配置"""
        try:
            # 设置默认配置
            self.set_config(
                'auto_confirm_enabled', 
                True, 
                'string', 
                '是否启用虚拟任务自动确认功能'
            )
            
            self.set_config(
                'auto_confirm_interval_hours', 
                1.0, 
                'number', 
                '自动确认时间间隔（小时）'
            )
            
            self.set_config(
                'auto_confirm_max_batch_size', 
                100, 
                'number', 
                '单次自动确认最大处理数量'
            )
            
            logger.info("自动确认配置初始化完成")
            
        except Exception as e:
            logger.error(f"初始化自动确认配置失败: {str(e)}")
