# shared/middlewares/case_middleware.py

from typing import Any, Dict, List
import re
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
import json
from starlette.types import Message
from shared.exceptions import BusinessException
from fastapi.exceptions import RequestValidationError

def to_camel_case(snake_str: str) -> str:
    """将下划线格式转换为驼峰格式"""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def convert_dict_keys(obj: Any) -> Any:
    """递归转换字典的key为驼峰格式"""
    if isinstance(obj, dict):
        new_dict = {}
        for key, value in obj.items():
            new_key = to_camel_case(key)
            new_dict[new_key] = convert_dict_keys(value)
        return new_dict
    elif isinstance(obj, list):
        return [convert_dict_keys(item) for item in obj]
    return obj

class CamelCaseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            response = await call_next(request)

            if response.headers.get("content-type") == "application/json":
                response_body = [chunk async for chunk in response.body_iterator]
                response_body = b"".join(response_body)

                try:
                    data = json.loads(response_body)
                    converted_data = convert_dict_keys(data)
                    
                    # 创建新的响应头，移除 content-length 头
                    headers = dict(response.headers)
                    if "content-length" in headers:
                        del headers["content-length"]
                    
                    # 使用JSONResponse创建新的响应
                    return JSONResponse(
                        content=converted_data,
                        status_code=response.status_code,
                        headers=headers
                    )
                    
                except Exception as e:
                    # 如果处理失败，返回原始响应
                    return Response(
                        content=response_body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type
                    )

            return response
            
        except RequestValidationError as e:
            # 处理参数验证错误
            error_messages = []
            for error in e.errors():
                field = error.get("loc", [])[-1]  # 获取字段名
                msg = error.get("msg", "")  # 获取错误信息
                error_messages.append(f"{field}: {msg}")
            
            return JSONResponse(
                status_code=200,
                content=convert_dict_keys({
                    "code": 400,
                    "message": "参数错误: " + "; ".join(error_messages),
                    "data": None
                })
            )
        except BusinessException as e:
            # 处理业务异常
            return JSONResponse(
                status_code=200,
                content=convert_dict_keys({
                    "code": e.code,
                    "message": e.message,
                    "data": e.data
                })
            )
        except Exception as e:
            # 处理其他异常
            return Response(
                content=str(e),
                status_code=500
            )
