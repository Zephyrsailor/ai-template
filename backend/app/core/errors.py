"""
错误处理模块 - 定义自定义异常和错误处理器
"""
from typing import Dict, Any, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .constants import APIConstants

class BaseAppException(Exception):
    """应用基础异常类"""
    def __init__(
        self, 
        message: str, 
        status_code: int = APIConstants.HTTP_INTERNAL_ERROR, 
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class BusinessException(BaseAppException):
    """业务逻辑异常"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, APIConstants.HTTP_BAD_REQUEST, details)

class ValidationException(BusinessException):
    """数据验证异常"""
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if field:
            details = details or {}
            details["field"] = field
        super().__init__(message, details)

class AuthenticationException(BaseAppException):
    """认证异常"""
    def __init__(self, message: str = "认证失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, APIConstants.HTTP_UNAUTHORIZED, details)

class AuthorizationException(BaseAppException):
    """授权异常"""
    def __init__(self, message: str = "权限不足", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, APIConstants.HTTP_FORBIDDEN, details)

class PermissionException(AuthorizationException):
    """权限异常（AuthorizationException的别名）"""
    pass

class NotFoundException(BaseAppException):
    """资源未找到异常"""
    def __init__(self, message: str = "资源不存在", resource_type: Optional[str] = None, resource_id: Optional[str] = None):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, APIConstants.HTTP_NOT_FOUND, details)

class ConflictException(BaseAppException):
    """资源冲突异常"""
    def __init__(self, message: str = "资源冲突", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 409, details)

class RateLimitException(BaseAppException):
    """请求频率限制异常"""
    def __init__(self, message: str = "请求过于频繁", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, APIConstants.HTTP_TOO_MANY_REQUESTS, details)

class ServiceException(BaseAppException):
    """服务异常"""
    def __init__(self, message: str = "服务异常", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, APIConstants.HTTP_INTERNAL_ERROR, details)

class ExternalServiceException(ServiceException):
    """外部服务异常"""
    def __init__(self, service_name: str, message: str = "外部服务异常", details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["service_name"] = service_name
        super().__init__(message, details)

class DatabaseException(ServiceException):
    """数据库异常"""
    def __init__(self, message: str = "数据库操作失败", operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if operation:
            details["operation"] = operation
        super().__init__(message, details)

class ConfigurationException(ServiceException):
    """配置异常"""
    def __init__(self, message: str = "配置错误", config_key: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, details)

# 业务特定异常

class KnowledgeBaseException(BusinessException):
    """知识库相关异常"""
    pass

class KnowledgeBaseNotFoundException(NotFoundException):
    """知识库未找到异常"""
    def __init__(self, kb_id: str):
        super().__init__(f"知识库 {kb_id} 不存在", "knowledge_base", kb_id)

class DocumentNotFoundException(NotFoundException):
    """文档未找到异常"""
    def __init__(self, doc_id: str):
        super().__init__(f"文档 {doc_id} 不存在", "document", doc_id)

class ConversationException(BusinessException):
    """会话相关异常"""
    pass

class ConversationNotFoundException(NotFoundException):
    """会话未找到异常"""
    def __init__(self, conversation_id: str):
        super().__init__(f"会话 {conversation_id} 不存在", "conversation", conversation_id)

class UserException(BusinessException):
    """用户相关异常"""
    pass

class UserNotFoundException(NotFoundException):
    """用户未找到异常"""
    def __init__(self, user_id: str):
        super().__init__(f"用户 {user_id} 不存在", "user", user_id)

class UserAlreadyExistsException(ConflictException):
    """用户已存在异常"""
    def __init__(self, username: str):
        super().__init__(f"用户名 {username} 已存在", {"username": username})

class MCPException(BusinessException):
    """MCP相关异常"""
    pass

class MCPServerNotFoundException(NotFoundException):
    """MCP服务器未找到异常"""
    def __init__(self, server_id: str):
        super().__init__(f"MCP服务器 {server_id} 不存在", "mcp_server", server_id)

class ToolCallException(ServiceException):
    """工具调用异常"""
    def __init__(self, tool_name: str, message: str = "工具调用失败", details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["tool_name"] = tool_name
        super().__init__(message, details)

class ChatException(ServiceException):
    """聊天相关异常"""
    pass

class FileException(BusinessException):
    """文件相关异常"""
    pass

class FileTooLargeException(ValidationException):
    """文件过大异常"""
    def __init__(self, file_size: int, max_size: int):
        super().__init__(
            f"文件大小 {file_size} 字节超过限制 {max_size} 字节",
            details={"file_size": file_size, "max_size": max_size}
        )

class UnsupportedFileTypeException(ValidationException):
    """不支持的文件类型异常"""
    def __init__(self, file_type: str, supported_types: list):
        super().__init__(
            f"不支持的文件类型 {file_type}，支持的类型: {', '.join(supported_types)}",
            details={"file_type": file_type, "supported_types": supported_types}
        )

# 异常处理器

async def base_exception_handler(request: Request, exc: BaseAppException):
    """基础异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "code": exc.status_code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": "2024-01-01T00:00:00Z",  # 实际应用中应使用当前时间
            "path": str(request.url.path)
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """验证异常处理器"""
    return JSONResponse(
        status_code=APIConstants.HTTP_BAD_REQUEST,
        content={
            "success": False,
            "code": APIConstants.HTTP_BAD_REQUEST,
            "message": "请求参数验证失败",
            "details": {"validation_errors": exc.errors()},
            "timestamp": "2024-01-01T00:00:00Z",
            "path": str(request.url.path)
        }
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "code": exc.status_code,
            "message": exc.detail,
            "timestamp": "2024-01-01T00:00:00Z",
            "path": str(request.url.path)
        }
    )

def register_exception_handlers(app):
    """注册异常处理器"""
    app.add_exception_handler(BaseAppException, base_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler) 