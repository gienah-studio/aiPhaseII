from typing import TypeVar, Generic, Optional, Any, List
from pydantic.generics import GenericModel

DataT = TypeVar("DataT")

class ResponseSchema(GenericModel, Generic[DataT]):
    code: int = 200
    data: Optional[DataT] = None
    message: str = "请求成功"

    class Config:
        json_encoders = {
            # 可以在这里添加自定义的JSON编码器
        }

class PageResponseSchema(GenericModel, Generic[DataT]):
    """分页响应模型"""
    code: int = 200
    message: str = "请求成功"
    data: Optional[dict] = None
    total: Optional[int] = None
    page: Optional[int] = None
    limit: Optional[int] = None

    class Config:
        json_encoders = {
            # 可以在这里添加自定义的JSON编码器
        }

# 为了保持兼容性，添加Response类
Response = ResponseSchema 