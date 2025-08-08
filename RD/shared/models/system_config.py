from sqlalchemy import Column, String, Integer, DateTime, Text
from shared.database.session import Base
from datetime import datetime

class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    config_key = Column(String(100), nullable=False, unique=True, comment="配置键")
    config_value = Column(Text, nullable=False, comment="配置值")
    config_type = Column(String(20), nullable=False, default='string', comment="配置类型：string, number, json")
    description = Column(String(500), nullable=True, comment="配置说明")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")

    def __repr__(self):
        return f"<SystemConfig(key={self.config_key}, value={self.config_value})>"
    
    def get_value(self):
        """根据类型返回配置值"""
        if self.config_type == 'number':
            return float(self.config_value)
        elif self.config_type == 'json':
            import json
            return json.loads(self.config_value)
        else:
            return self.config_value