# shared/utils/pagination.py
from typing import Generic, List, TypeVar, Optional, Any, Dict
from pydantic import BaseModel, Field
from fastapi import Query
from math import ceil

T = TypeVar('T')

class PaginationParams:
    """
    分页参数类
    """
    def __init__(
        self,
        page: int = Query(1, ge=1, description="页码，从1开始"),
        page_size: int = Query(10, ge=1, le=100, description="每页条目数"),
    ):
        self.page = page
        self.page_size = page_size
        self.skip = (page - 1) * page_size

class PaginatedResponse(BaseModel, Generic[T]):
    """
    分页响应模型
    """
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int
    has_more: bool = Field(..., description="是否有更多数据")
    
    class Config:
        arbitrary_types_allowed = True

async def paginate(
    query_func, 
    count_func, 
    pagination: PaginationParams,
    **kwargs
) -> PaginatedResponse:
    """
    通用分页函数
    
    参数:
        query_func: 查询数据的异步函数
        count_func: 计算总数的异步函数
        pagination: 分页参数
        **kwargs: 传递给查询函数的额外参数
    """
    # 获取总数
    total = await count_func(**kwargs)
    
    # 计算总页数
    pages = ceil(total / pagination.page_size) if total > 0 else 0
    
    # 查询当前页数据
    items = await query_func(
        skip=pagination.skip,
        limit=pagination.page_size,
        **kwargs
    )
    
    # 构建分页响应
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
        has_more=pagination.page < pages
    )
