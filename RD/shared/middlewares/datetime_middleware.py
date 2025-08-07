from datetime import datetime
import arrow
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
import json
import re
from shared.exceptions import BusinessException, ErrorCode

class DatetimeMiddleware(BaseHTTPMiddleware):
    # ISO 8601 日期时间格式的正则表达式模式
    ISO_DATETIME_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$')
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)

            if response.headers.get("content-type") == "application/json":
                try:
                    # 读取响应体
                    body = b""
                    async for chunk in response.body_iterator:
                        body += chunk

                    # 解析并处理数据
                    data = json.loads(body.decode())
                    self._format_datetime(data)
                    
                    # 转换回JSON并编码
                    modified_body = json.dumps(data, ensure_ascii=False).encode('utf-8')
                    
                    # 创建新的响应，包含更新后的Content-Length
                    headers = dict(response.headers)
                    headers['content-length'] = str(len(modified_body))
                    
                    return Response(
                        content=modified_body,
                        status_code=response.status_code,
                        headers=headers,
                        media_type="application/json"
                    )
                except Exception as e:
                    print(f"Error in datetime middleware: {str(e)}")
                    return response
            
            return response
            
        except BusinessException as e:
            # 处理业务异常
            data = {
                "code": e.code,
                "message": e.message,
                "data": e.data
            }
            self._format_datetime(data)
            return JSONResponse(
                status_code=200,
                content=data
            )
        except Exception as e:
            # 处理其他异常
            return JSONResponse(
                status_code=200,
                content={
                    "code": ErrorCode.SERVER_ERROR,
                    "message": str(e),
                    "data": None
                }
            )

    def _format_datetime(self, data):
        """递归格式化字典中的所有datetime值"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and self.ISO_DATETIME_PATTERN.match(value):
                    # 处理ISO格式的时间字符串
                    try:
                        # 将ISO格式直接转换为指定格式，不进行时区转换
                        dt = arrow.get(value)
                        data[key] = dt.format('YYYY-MM-DD HH:mm:ss')
                    except Exception as e:
                        print(f"Error formatting datetime {value}: {str(e)}")
                elif isinstance(value, (dict, list)):
                    self._format_datetime(value)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._format_datetime(item)

