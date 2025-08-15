"""
Redis缓存客户端配置
"""

import redis
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis客户端管理器"""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._connected = False
    
    def get_client(self) -> Optional[redis.Redis]:
        """获取Redis客户端实例"""
        if self._client is None or not self._connected:
            self._connect()
        return self._client if self._connected else None
    
    def _connect(self):
        """连接Redis"""
        try:
            # 从环境变量获取Redis配置
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
            redis_password = os.getenv('REDIS_PASSWORD', None)
            redis_db = int(os.getenv('REDIS_DB', '0'))
            
            # 创建Redis连接
            self._client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db,
                decode_responses=True,  # 自动解码响应
                socket_timeout=5,  # 5秒超时
                socket_connect_timeout=5,  # 5秒连接超时
                retry_on_timeout=True,
                health_check_interval=30  # 30秒健康检查
            )
            
            # 测试连接
            self._client.ping()
            self._connected = True
            logger.info(f"Redis连接成功: {redis_host}:{redis_port}")
            
        except Exception as e:
            logger.warning(f"Redis连接失败: {e}")
            self._client = None
            self._connected = False
    
    def is_connected(self) -> bool:
        """检查Redis是否连接"""
        if not self._connected or self._client is None:
            return False
        
        try:
            self._client.ping()
            return True
        except:
            self._connected = False
            return False
    
    def close(self):
        """关闭Redis连接"""
        if self._client:
            try:
                self._client.close()
                logger.info("Redis连接已关闭")
            except:
                pass
            finally:
                self._client = None
                self._connected = False

# 全局Redis客户端实例
_redis_manager = RedisClient()

def get_redis_client() -> Optional[redis.Redis]:
    """获取Redis客户端实例（全局单例）"""
    return _redis_manager.get_client()

def close_redis_connection():
    """关闭Redis连接"""
    _redis_manager.close()