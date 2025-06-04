"""
应用常量配置 - 统一管理所有魔法数字和硬编码值
"""
from typing import Dict, Any

class APIConstants:
    """API相关常量"""
    # HTTP状态码
    HTTP_OK = 200
    HTTP_BAD_REQUEST = 400
    HTTP_UNAUTHORIZED = 401
    HTTP_FORBIDDEN = 403
    HTTP_NOT_FOUND = 404
    HTTP_TOO_MANY_REQUESTS = 429
    HTTP_INTERNAL_ERROR = 500
    
    # 分页默认值
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100
    MIN_PAGE_SIZE = 1
    DEFAULT_PAGE = 1
    
    # 请求限制
    DEFAULT_RATE_LIMIT_CALLS = 100
    DEFAULT_RATE_LIMIT_PERIOD = 60  # 秒
    
    # CORS配置
    CORS_MAX_AGE = 86400  # 24小时

class ChatConstants:
    """聊天相关常量"""
    # ReAct循环限制
    MAX_REACT_ITERATIONS = 20
    
    # 内容预览长度
    MAX_CONTENT_PREVIEW = 500
    MESSAGE_PREVIEW_LENGTH = 50
    
    # 知识库查询
    KNOWLEDGE_TOP_K = 10
    
    # 网络搜索
    WEB_SEARCH_TIMEOUT = 30
    
    # 内容清理
    CONTENT_SANITIZE_PATTERNS = [
        r'sk-[a-zA-Z0-9]{48}',  # OpenAI API key pattern
        r'Bearer [a-zA-Z0-9\-_]+',  # Bearer token pattern
        r'api[_-]?key["\s]*[:=]["\s]*[a-zA-Z0-9\-_]+',  # Generic API key pattern
    ]

class ConversationConstants:
    """会话相关常量"""
    # 内容预览长度
    CONTENT_PREVIEW_LENGTH = 100
    THINKING_PREVIEW_LENGTH = 100
    TITLE_PREVIEW_LENGTH = 20
    
    # 会话标题生成
    TITLE_SUFFIX = "..."

class KnowledgeConstants:
    """知识库相关常量"""
    # 文档处理
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_CHUNK_OVERLAP = 200
    DEFAULT_TOP_K = 5
    DEFAULT_SIMILARITY_THRESHOLD = 0.7
    
    # 文件限制
    MAX_DOCUMENT_SIZE_MB = 20
    MAX_DOCUMENTS_PER_KB = 100
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
    
    # 重试配置
    MAX_RETRY_ATTEMPTS = 3

class SearchConstants:
    """搜索相关常量"""
    # 网页搜索
    MAX_CHARS_PER_PAGE = 2000
    HTTP_TIMEOUT = 10  # 秒

class DatabaseConstants:
    """数据库相关常量"""
    # 连接池配置
    DEFAULT_POOL_SIZE = 10
    DEFAULT_MAX_OVERFLOW = 20
    
    # 字段长度限制
    USERNAME_MAX_LENGTH = 100
    EMAIL_MAX_LENGTH = 255
    PASSWORD_HASH_MAX_LENGTH = 255
    FULL_NAME_MAX_LENGTH = 255
    ROLE_MAX_LENGTH = 50
    
    # 知识库字段长度
    KB_NAME_MAX_LENGTH = 255
    KB_DESCRIPTION_MAX_LENGTH = 1000
    KB_EMBEDDING_MODEL_MAX_LENGTH = 100
    KB_STATUS_MAX_LENGTH = 50
    KB_TYPE_MAX_LENGTH = 50
    
    # 文件字段长度
    FILE_NAME_MAX_LENGTH = 255
    FILE_PATH_MAX_LENGTH = 500
    FILE_TYPE_MAX_LENGTH = 50
    
    # 会话字段长度
    CONVERSATION_TITLE_MAX_LENGTH = 255
    CONVERSATION_MODEL_MAX_LENGTH = 100
    MESSAGE_ROLE_MAX_LENGTH = 50
    
    # MCP服务器字段长度
    MCP_SERVER_NAME_MAX_LENGTH = 255
    MCP_SERVER_URL_MAX_LENGTH = 500
    MCP_SERVER_API_KEY_MAX_LENGTH = 255
    MCP_SERVER_STATUS_MAX_LENGTH = 10

class LoggingConstants:
    """日志相关常量"""
    # 日志文件配置
    MAX_LOG_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # 日志格式
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

class SecurityConstants:
    """安全相关常量"""
    # JWT配置
    DEFAULT_ALGORITHM = "HS256"
    DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天
    
    # 密码验证
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    
    # API密钥模式
    OPENAI_API_KEY_PATTERN = r'sk-[a-zA-Z0-9]{48}'
    BEARER_TOKEN_PATTERN = r'Bearer [a-zA-Z0-9\-_]+'

class LLMConstants:
    """LLM相关常量"""
    # 默认参数
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_CONTEXT_LENGTH = 32768
    
    # 模型配置
    DEFAULT_CONFIG_NAME = "默认配置"

class ValidationConstants:
    """验证相关常量"""
    # 字符串长度验证
    MIN_STRING_LENGTH = 1
    MAX_STRING_LENGTH = 1000
    
    # 数值验证
    MIN_POSITIVE_INT = 1
    MAX_REASONABLE_INT = 1000000

class ServerConstants:
    """服务器相关常量"""
    # 默认端口
    DEFAULT_PORT = 8000
    
    # 环境配置
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"

# 配置映射字典，便于动态访问
CONFIG_MAPPING: Dict[str, Any] = {
    "api": APIConstants,
    "chat": ChatConstants,
    "conversation": ConversationConstants,
    "knowledge": KnowledgeConstants,
    "search": SearchConstants,
    "database": DatabaseConstants,
    "logging": LoggingConstants,
    "security": SecurityConstants,
    "llm": LLMConstants,
    "validation": ValidationConstants,
    "server": ServerConstants,
}

def get_constant(category: str, name: str, default: Any = None) -> Any:
    """
    动态获取常量值
    
    Args:
        category: 常量类别
        name: 常量名称
        default: 默认值
        
    Returns:
        常量值
    """
    try:
        constant_class = CONFIG_MAPPING.get(category)
        if constant_class:
            return getattr(constant_class, name, default)
        return default
    except Exception:
        return default 