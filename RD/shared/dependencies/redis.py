from typing import AsyncGenerator
import aioredis
from shared.config import settings
from shared.exceptions import BusinessException
import asyncio

# Create Redis connection pool with external Redis server settings
redis_pool = aioredis.ConnectionPool(
    host=settings.REDIS_HOST,  # 使用环境变量中的主机地址
    port=settings.REDIS_PORT,  # 使用环境变量中的端口
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
    max_connections=5,
    socket_timeout=10.0,
    socket_connect_timeout=10.0
)

async def test_connection(client: aioredis.Redis, max_retries: int = 3) -> bool:
    """测试Redis连接
    
    Args:
        client: Redis客户端
        max_retries: 最大重试次数
        
    Returns:
        bool: 连接是否成功
    """
    for i in range(max_retries):
        try:
            await client.ping()
            print(f"Redis ping成功")
            return True
        except Exception as e:
            print(f"Redis连接测试失败 (尝试 {i+1}/{max_retries}): {str(e)}")
            print(f"连接信息: host={redis_pool.connection_kwargs['host']}, port={redis_pool.connection_kwargs['port']}")
            if i < max_retries - 1:
                await asyncio.sleep(2)
    return False

async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """获取Redis连接
    
    Yields:
        Redis: Redis客户端实例
    """
    client = None
    for attempt in range(3):
        try:
            if client:
                await client.close()
            
            client = aioredis.Redis(connection_pool=redis_pool)
            print(f"尝试连接Redis (尝试 {attempt + 1}/3)")
            print(f"连接配置: host={redis_pool.connection_kwargs['host']}, port={redis_pool.connection_kwargs['port']}")
            
            # 测试连接
            if await test_connection(client):
                print(f"Redis连接成功")
                yield client
                return
            
        except Exception as e:
            error_msg = f"Redis连接创建失败 (尝试 {attempt + 1}/3): {str(e)}"
            print(f"{error_msg}")
            if attempt < 2:
                await asyncio.sleep(2)
                continue
    
    # 如果所有重试都失败
    if client:
        await client.close()
    
    raise BusinessException(
        code=500,
        message="Redis服务暂时不可用，请检查Redis配置或稍后重试",
        data=None
    )