"""
数据库依赖模块
提供数据库会话的依赖注入
"""

from shared.database.session import get_db

__all__ = ["get_db"]