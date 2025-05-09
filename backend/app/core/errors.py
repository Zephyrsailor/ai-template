"""
错误处理模块 - 定义自定义异常和错误处理器
"""
from typing import Dict, Any, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class BaseAppException(Exception):
    """应用基础异常类"""
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(BaseAppException):
    """资源未找到异常"""
    def __init__(self, message: str = "资源未找到", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_404_NOT_FOUND, details)


class BadRequestException(BaseAppException):
    """请求参数错误异常"""
    def __init__(self, message: str = "请求参数错误", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)


class UnauthorizedException(BaseAppException):
    """未授权异常"""
    def __init__(self, message: str = "未授权操作", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, details)


class ForbiddenException(BaseAppException):
    """禁止访问异常"""
    def __init__(self, message: str = "禁止访问", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, details)


class ServiceException(BaseAppException):
    """服务层异常"""
    def __init__(self, message: str = "服务错误", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR, details)


# 错误处理器
async def app_exception_handler(request: Request, exc: BaseAppException):
    """自定义异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.message,
            "details": exc.details,
            "status_code": exc.status_code
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理器"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": "数据验证错误",
            "details": exc.errors(),
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY
        }
    )


# 注册错误处理器函数
def register_exception_handlers(app):
    """在FastAPI应用中注册所有错误处理器"""
    app.add_exception_handler(BaseAppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler) 