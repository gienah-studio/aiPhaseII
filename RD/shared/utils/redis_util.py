from redis.asyncio import Redis, ConnectionPool
from shared.config import settings
from shared.exceptions import BusinessException
import time
import uuid
import asyncio

# 创建Redis连接池
redis_pool = ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
    socket_timeout=5.0,
    socket_connect_timeout=5.0,
    retry_on_timeout=True,
    encoding='utf8',
    max_connections=10  # 限制最大连接数
)

class RedisUtil:
    # 统一的键前缀
    TEST_KEY_PREFIX = "_test_write_"  # 测试键前缀
    TOKEN_BLACKLIST_PREFIX = "token_blacklist:"  # token黑名单前缀
    
    @staticmethod
    async def get_redis() -> Redis:
        """获取Redis客户端实例"""
        return Redis(connection_pool=redis_pool)
    
    @staticmethod
    async def test_connection() -> bool:
        """测试Redis连接"""
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                redis = await RedisUtil.get_redis()
                return await redis.ping()
            except Exception as e:
                print(f"Redis连接测试失败 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(1)  # 等待1秒后重试
            
        return False
            
    @staticmethod
    async def test_write() -> bool:
        """测试Redis写入权限"""
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                redis = await RedisUtil.get_redis()
                # 使用UUID生成唯一的测试键
                test_key = f"{RedisUtil.TEST_KEY_PREFIX}{uuid.uuid4().hex}"
                # 尝试写入测试键
                await redis.setex(test_key, 1, "1")
                # 验证写入是否成功
                value = await redis.get(test_key)
                # 立即删除测试键
                await redis.delete(test_key)
                # 只有当写入和读取都成功时才返回True
                if value == "1":
                    return True
                print(f"Redis写入测试失败: 写入验证未通过")
            except Exception as e:
                print(f"Redis写入测试失败 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
            
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(1)  # 等待1秒后重试
        
        return False
    









    @staticmethod
    async def add_token_to_blacklist(token: str, expire_seconds: int = 3600) -> bool:
        """将token加入黑名单
        
        Args:
            token: JWT令牌
            expire_seconds: 过期时间（秒）
            
        Returns:
            bool: 操作是否成功
        """
        if not await RedisUtil.test_connection():
            return False
            
        try:
            redis = await RedisUtil.get_redis()
            key = f"{RedisUtil.TOKEN_BLACKLIST_PREFIX}{token}"
            return await redis.setex(key, expire_seconds, "1")
        except Exception as e:
            print(f"将token加入黑名单失败: {str(e)}")
            return False

    @staticmethod
    async def is_token_blacklisted(token: str) -> bool:
        """检查token是否在黑名单中
        
        Args:
            token: JWT令牌
            
        Returns:
            bool: 如果token在黑名单中返回True，否则返回False
        """
        if not await RedisUtil.test_connection():
            return False
            
        try:
            redis = await RedisUtil.get_redis()
            key = f"{RedisUtil.TOKEN_BLACKLIST_PREFIX}{token}"
            return bool(await redis.get(key))
        except Exception as e:
            print(f"检查token黑名单失败: {str(e)}")
            return False