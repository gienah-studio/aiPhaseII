from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
import logging
import re

from shared.utils.jwt import decode_jwt_token
from shared.exceptions import BusinessException

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件
    
    处理请求的JWT token认证
    """
    
    def __init__(self, app):
        super().__init__(app)
        # 不需要认证的路径白名单
        self.white_list = [
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/captcha",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/auth/sendVerificationCode",
            "/api/auth/phoneLogin",
            "/api/auth/resetPassword",
            "/api/auth/profile",
            "/api/grainPrice/pdf",  # 驼峰版本
            "/api/grainPrice/grainPrice/pdf",  # 嵌套路由版本
            "/static/pdf",  # 静态文件目录
            "/app/static/pdf",  # Docker容器内的静态文件目录
            "/favicon.ico"
        ]
        # 添加正则表达式模式匹配PDF文件
        self.white_patterns = [
            re.compile(r"^/api/grainPrice/pdf/.*\.pdf$"),
            re.compile(r"^/api/grainPrice/grainPrice/pdf/.*\.pdf$"),
            # 富文本PDF文件模式匹配
            re.compile(r"^/api/grainPrice/grainPrice/pdf/grain_price_richtext_.*\.pdf$"),
            # 静态PDF文件模式匹配
            re.compile(r"^/static/pdf/.*\.pdf$"),
            # Docker容器内的静态PDF文件模式匹配
            re.compile(r"^/app/static/pdf/.*\.pdf$")
        ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """处理请求
        
        Args:
            request: 请求对象
            call_next: 下一个处理函数
            
        Returns:
            Response: 响应对象
        """
        # 检查是否在白名单中或匹配白名单模式
        path = request.url.path
        print(f"[Auth] 当前请求路径: {path}")
        
        is_in_whitelist = any(path.startswith(white_path) for white_path in self.white_list)
        is_match_pattern = any(pattern.match(path) for pattern in self.white_patterns)
        print(f"[Auth] 是否在白名单中: {is_in_whitelist}")
        print(f"[Auth] 是否匹配白名单模式: {is_match_pattern}")
        
        if is_in_whitelist or is_match_pattern:
            print(f"[Auth] 路径在白名单中，允许访问: {path}")
            return await call_next(request)
            
        try:
            # 从请求头获取token
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                print(f"[Auth] 未提供认证凭据: {path}")
                return JSONResponse(
                    status_code=200,
                    content={
                        "code": 401,
                        "message": "未提供认证凭据",
                        "data": None
                    }
                )

            token = auth_header.split(" ")[1]

            # 解析token
            token_data = decode_jwt_token(token)

            # 将用户信息保存到request.state
            request.state.user = {
                "user_id": token_data.user_id,
                "account": token_data.account,
                "user_type": token_data.user_type,
                "organization_id": token_data.organization_id,
                "enterprise_id": token_data.enterprise_id
            }

            logger.debug(f"用户信息: {request.state.user}")

            return await call_next(request)

        except BusinessException as e:
            # 业务异常直接返回JSON响应
            print(f"[Auth] BusinessException: {e.message}")
            return JSONResponse(
                status_code=200,
                content={
                    "code": e.code,
                    "message": e.message,
                    "data": e.data
                }
            )
        except Exception as e:
            # 其他异常转换为认证失败
            logger.error(f"认证失败: {str(e)}")
            return JSONResponse(
                status_code=200,
                content={
                    "code": 401,
                    "message": "认证失败",
                    "data": None
                }
            )