"""
消息管理模块 - 统一管理所有用户可见的消息，支持国际化
"""
import json
import os
from typing import Dict, Any, Optional
from enum import Enum

from .logging import get_logger

logger = get_logger(__name__)

class Language(str, Enum):
    """支持的语言"""
    ZH_CN = "zh_CN"
    EN_US = "en_US"

class MessageManager:
    """消息管理器"""
    
    def __init__(self, default_language: Language = Language.ZH_CN):
        self.default_language = default_language
        self.messages: Dict[str, Dict[str, str]] = {}
        self._load_messages()
    
    def _load_messages(self):
        """加载消息文件"""
        messages_dir = os.path.join(os.path.dirname(__file__), "..", "config", "messages")
        
        for language in Language:
            message_file = os.path.join(messages_dir, f"{language.value}.json")
            try:
                if os.path.exists(message_file):
                    with open(message_file, 'r', encoding='utf-8') as f:
                        self.messages[language.value] = json.load(f)
                else:
                    logger.warning(f"消息文件不存在: {message_file}")
                    self.messages[language.value] = {}
            except Exception as e:
                logger.error(f"加载消息文件失败 {message_file}: {str(e)}")
                self.messages[language.value] = {}
    
    def get(self, key: str, language: Optional[Language] = None, **kwargs) -> str:
        """获取消息"""
        lang = language or self.default_language
        
        # 处理嵌套键（如 "common.success"）
        def get_nested_value(data: dict, key_path: str):
            keys = key_path.split('.')
            value = data
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return None
            return value
        
        # 尝试获取指定语言的消息
        message = get_nested_value(self.messages.get(lang.value, {}), key)
        
        # 如果没有找到，尝试默认语言
        if not message and lang != self.default_language:
            message = get_nested_value(self.messages.get(self.default_language.value, {}), key)
        
        # 如果还是没有找到，返回key本身
        if not message:
            logger.warning(f"消息键未找到: {key}")
            return key
        
        # 格式化消息
        try:
            return message.format(**kwargs)
        except Exception as e:
            logger.error(f"消息格式化失败 {key}: {str(e)}")
            return message

# 全局消息管理器实例
_message_manager = None

def get_message_manager() -> MessageManager:
    """获取全局消息管理器实例"""
    global _message_manager
    if _message_manager is None:
        _message_manager = MessageManager()
    return _message_manager

def get_message(key: str, language: Optional[Language] = None, **kwargs) -> str:
    """获取消息的便捷函数"""
    return get_message_manager().get(key, language, **kwargs)

# 常用消息键常量
class MessageKeys:
    """消息键常量"""
    
    # 通用消息
    SUCCESS = "common.success"
    ERROR = "common.error"
    NOT_FOUND = "common.not_found"
    UNAUTHORIZED = "common.unauthorized"
    FORBIDDEN = "common.forbidden"
    BAD_REQUEST = "common.bad_request"
    INTERNAL_ERROR = "common.internal_error"
    
    # 认证相关
    AUTH_LOGIN_SUCCESS = "auth.login_success"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_LOGOUT_SUCCESS = "auth.logout_success"
    AUTH_TOKEN_INVALID = "auth.token_invalid"
    AUTH_PASSWORD_INCORRECT = "auth.password_incorrect"
    
    # 用户相关
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_NOT_FOUND = "user.not_found"
    USER_ALREADY_EXISTS = "user.already_exists"
    
    # 知识库相关
    KB_CREATED = "knowledge.created"
    KB_UPDATED = "knowledge.updated"
    KB_DELETED = "knowledge.deleted"
    KB_NOT_FOUND = "knowledge.not_found"
    KB_QUERY_SUCCESS = "knowledge.query_success"
    KB_QUERY_FAILED = "knowledge.query_failed"
    KB_INDEX_REBUILD_SUCCESS = "knowledge.index_rebuild_success"
    KB_INDEX_REBUILD_FAILED = "knowledge.index_rebuild_failed"
    KB_FILE_UPLOADED = "knowledge.file_uploaded"
    KB_FILE_DELETED = "knowledge.file_deleted"
    KB_FILE_NOT_FOUND = "knowledge.file_not_found"
    
    # 会话相关
    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_UPDATED = "conversation.updated"
    CONVERSATION_DELETED = "conversation.deleted"
    CONVERSATION_NOT_FOUND = "conversation.not_found"
    
    # 聊天相关
    CHAT_SUCCESS = "chat.success"
    CHAT_FAILED = "chat.failed"
    CHAT_STOPPED = "chat.stopped"
    
    # MCP相关
    MCP_SERVER_CREATED = "mcp.server_created"
    MCP_SERVER_UPDATED = "mcp.server_updated"
    MCP_SERVER_DELETED = "mcp.server_deleted"
    MCP_SERVER_NOT_FOUND = "mcp.server_not_found"
    MCP_TOOL_CALL_SUCCESS = "mcp.tool_call_success"
    MCP_TOOL_CALL_FAILED = "mcp.tool_call_failed"
    
    # 文件相关
    FILE_UPLOAD_SUCCESS = "file.upload_success"
    FILE_UPLOAD_FAILED = "file.upload_failed"
    FILE_DELETE_SUCCESS = "file.delete_success"
    FILE_DELETE_FAILED = "file.delete_failed"
    FILE_NOT_FOUND = "file.not_found"
    FILE_TOO_LARGE = "file.too_large"
    FILE_TYPE_NOT_SUPPORTED = "file.type_not_supported"
    
    # 验证相关
    VALIDATION_REQUIRED = "validation.required"
    VALIDATION_INVALID_FORMAT = "validation.invalid_format"
    VALIDATION_TOO_LONG = "validation.too_long"
    VALIDATION_TOO_SHORT = "validation.too_short" 