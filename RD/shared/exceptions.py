from fastapi import Request
from fastapi.responses import JSONResponse
from typing import Any, Optional

class BusinessException(Exception):
    """业务异常类"""
    def __init__(
        self,
        code: int,
        message: str,
        data: Any = None
    ):
        self.code = code
        self.message = message
        self.data = data

async def business_exception_handler(request: Request, exc: BusinessException):
    """业务异常处理器"""
    return JSONResponse(
        status_code=200,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": exc.data
        }
    )

class ErrorCode:
    """错误码枚举"""
    SUCCESS = 200
    PARAM_ERROR = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    SERVER_ERROR = 500

    # 用户相关错误码 1000-1999
    USER_NOT_FOUND = 1000
    USER_ALREADY_EXISTS = 1001
    USER_DISABLED = 1002
    INVALID_PASSWORD = 1003
    
    # 验证码相关错误码 2000-2999
    INVALID_CODE = 2000
    CODE_EXPIRED = 2001
    CODE_SEND_FAILED = 2002
    CODE_SEND_TOO_FREQUENT = 2003
    
    # 企业相关错误码 3000-3999
    ENTERPRISE_NOT_FOUND = 3000
    ENTERPRISE_ALREADY_EXISTS = 3001

    # 文件相关错误码 4000-4999
    INVALID_FILE_TYPE = 4000
    FILE_TOO_LARGE = 4001
    FILE_UPLOAD_FAILED = 4002

class ErrorMessage:
    """错误信息"""
    @staticmethod
    def get_message(code: int) -> str:
        """获取错误信息"""
        messages = {
            ErrorCode.SUCCESS: "成功",
            ErrorCode.PARAM_ERROR: "参数错误",
            ErrorCode.UNAUTHORIZED: "未授权",
            ErrorCode.FORBIDDEN: "禁止访问",
            ErrorCode.NOT_FOUND: "资源不存在",
            ErrorCode.SERVER_ERROR: "服务器错误",
            
            ErrorCode.USER_NOT_FOUND: "用户不存在",
            ErrorCode.USER_ALREADY_EXISTS: "用户已存在",
            ErrorCode.USER_DISABLED: "用户已被禁用",
            ErrorCode.INVALID_PASSWORD: "密码错误",
            
            ErrorCode.INVALID_CODE: "验证码错误",
            ErrorCode.CODE_EXPIRED: "验证码已过期",
            ErrorCode.CODE_SEND_FAILED: "验证码发送失败",
            ErrorCode.CODE_SEND_TOO_FREQUENT: "验证码发送过于频繁",
            
            ErrorCode.ENTERPRISE_NOT_FOUND: "企业不存在",
            ErrorCode.ENTERPRISE_ALREADY_EXISTS: "企业已存在",

            # 文件相关错误信息
            ErrorCode.INVALID_FILE_TYPE: "不支持的文件类型",
            ErrorCode.FILE_TOO_LARGE: "文件大小超出限制",
            ErrorCode.FILE_UPLOAD_FAILED: "文件上传失败",
        }
        return messages.get(code, "未知错误") 