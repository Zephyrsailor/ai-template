"""
异常模块 - 重新导出所有异常类以便于导入
"""

from .errors import (
    # 基础异常
    BaseAppException,
    BusinessException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    PermissionException,
    NotFoundException,
    ConflictException,
    RateLimitException,
    ServiceException,
    ExternalServiceException,
    DatabaseException,
    ConfigurationException,
    
    # 业务特定异常
    KnowledgeBaseException,
    KnowledgeBaseNotFoundException,
    DocumentNotFoundException,
    ConversationException,
    ConversationNotFoundException,
    UserException,
    UserNotFoundException,
    UserAlreadyExistsException,
    MCPException,
    MCPServerNotFoundException,
    ToolCallException,
    ChatException,
    FileException,
    FileTooLargeException,
    UnsupportedFileTypeException,
)

# 为了兼容性，创建一些别名
UserNotFoundError = UserNotFoundException
UserAlreadyExistsError = UserAlreadyExistsException
InvalidCredentialsError = AuthenticationException
ValidationError = ValidationException

__all__ = [
    # 基础异常
    "BaseAppException",
    "BusinessException", 
    "ValidationException",
    "AuthenticationException",
    "AuthorizationException",
    "PermissionException",
    "NotFoundException",
    "ConflictException",
    "RateLimitException",
    "ServiceException",
    "ExternalServiceException",
    "DatabaseException",
    "ConfigurationException",
    
    # 业务特定异常
    "KnowledgeBaseException",
    "KnowledgeBaseNotFoundException", 
    "DocumentNotFoundException",
    "ConversationException",
    "ConversationNotFoundException",
    "UserException",
    "UserNotFoundException",
    "UserAlreadyExistsException",
    "MCPException",
    "MCPServerNotFoundException",
    "ToolCallException",
    "ChatException",
    "FileException",
    "FileTooLargeException",
    "UnsupportedFileTypeException",
    
    # 别名
    "UserNotFoundError",
    "UserAlreadyExistsError", 
    "InvalidCredentialsError",
    "ValidationError",
] 