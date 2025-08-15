"""
基础模型类，提供通用的数据模型功能
包含驼峰命名转换和基础配置
"""

from pydantic import BaseModel
from typing import Any
import re


def to_camel(snake_str: str) -> str:
    """
    将 snake_case 转换为 camelCase
    
    Args:
        snake_str: snake_case 格式的字符串
        
    Returns:
        camelCase 格式的字符串
        
    Examples:
        >>> to_camel("user_name")
        "userName"
        >>> to_camel("category_id")
        "categoryId"
        >>> to_camel("file_upload_info")
        "fileUploadInfo"
    """
    if not snake_str:
        return snake_str
    
    # 分割字符串并转换
    components = snake_str.split('_')
    if len(components) == 1:
        return components[0]
    
    # 第一个组件保持小写，其余组件首字母大写
    return components[0] + ''.join(word.capitalize() for word in components[1:])


class CamelCaseModel(BaseModel):
    """
    支持驼峰命名的基础模型类
    
    特性:
    1. 自动将 snake_case 字段名转换为 camelCase 作为别名
    2. 支持通过原字段名和别名两种方式赋值
    3. 向后兼容，不破坏现有接口
    """
    
    class Config:
        # 启用别名生成器
        alias_generator = to_camel
        # 允许通过字段名赋值（向后兼容）
        allow_population_by_field_name = True
        # 启用额外字段验证
        extra = 'forbid'


class BaseResponseModel(BaseModel):
    """
    基础响应模型
    不使用驼峰转换，保持现有API格式
    """
    
    class Config:
        # 与ORM模型兼容
        orm_mode = True
        # 允许额外字段
        extra = 'allow'


class BaseRequestModel(CamelCaseModel):
    """
    基础请求模型
    使用驼峰转换，提升前端开发体验
    """
    pass


# 兼容性别名，保持现有代码正常工作
SnakeCaseModel = BaseModel