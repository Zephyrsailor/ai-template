"""
系统常量和枚举定义
"""
from enum import Enum, auto

class ModelProvider(str, Enum):
    """模型提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    OLLAMA = "ollama"
    LOCAL = "local"
    DEEPSEEK = "deepseek"

class EmbeddingProvider(str, Enum):
    """嵌入模型提供商枚举"""
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    LOCAL = "local"
    DEEPSEEK = "deepseek"

class MessageRole(str, Enum):
    """消息角色枚举"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

class EventType(str, Enum):
    """事件类型枚举"""
    THINKING = "thinking"
    CONTENT = "content"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    REFERENCE = "reference"
    FINAL_CONTENT = "final_content"
    CONVERSATION_CREATED = "conversation_created"
class KnowledgeBaseStatus(str, Enum):
    """知识库状态枚举"""
    CREATING = "creating"
    READY = "ready"
    UPDATING = "updating"
    ERROR = "error"

class DocumentStatus(str, Enum):
    """文档状态枚举"""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"

class FileType(str, Enum):
    """支持的文件类型枚举"""
    PDF = "pdf"
    TXT = "txt"
    DOCX = "docx"
    MD = "md"
    CSV = "csv"
    HTML = "html"
    JSON = "json"

class ToolFormat(Enum):
    """工具调用格式"""
    OPENAI = "openai"      # OpenAI 的 function calling
    CLAUDE = "claude"      # Claude 的 JSON 工具调用
    TEXT = "text"          # 纯文本形式（不支持工具调用的模型）

# 系统常量
MAX_DOCUMENT_SIZE_MB = 20
MAX_DOCUMENTS_PER_KB = 100
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_TOP_K = 5
MAX_RETRY_ATTEMPTS = 3
DEFAULT_SIMILARITY_THRESHOLD = 0.7 