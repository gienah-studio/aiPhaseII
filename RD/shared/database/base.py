from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# 创建声明性基类
Base = declarative_base()

# 如果需要的话，这里可以添加数据库引擎配置
# engine = create_engine('your_database_url')
# SessionLocal = sessionmaker(bind=engine)

# 导出Base类
__all__ = ['Base']
