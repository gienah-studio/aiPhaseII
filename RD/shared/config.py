import os
from dotenv import load_dotenv
from typing import Optional

from pydantic import BaseSettings, Field

# 加载.env文件
load_dotenv()

class Settings(BaseSettings):
    # 应用基础配置
    APP_NAME: str = "Organization Management System"
    API_V1_STR: str = "/api/v1"
    
    # 基础URL配置，用于生成资源的完整URL
    BASE_URL: str = Field(env="BASE_URL", default="http://localhost:9005")
    
    # 安全配置
    SECRET_KEY: str = Field(env="JWT_SECRET_KEY", default="your-secret-key-keep-it-secret")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES", default=30)
    ALGORITHM: str = "HS256"  # JWT加密算法
    
    # 数据库配置
    MYSQL_HOST: str
    MYSQL_PORT: int = 3306
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DATABASE: str
    
    # SQLAlchemy配置
    SQLALCHEMY_DATABASE_URL: Optional[str] = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 如果没有显式设置数据库URL，则根据其他配置生成
        if not self.SQLALCHEMY_DATABASE_URL:
            self.SQLALCHEMY_DATABASE_URL = (
                f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@"
                f"{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
                "?charset=utf8mb4"
            )
    
    # Redis配置
    REDIS_HOST: str = Field(default="redis")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_PASSWORD: str = Field(default="")
    

    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
