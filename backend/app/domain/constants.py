"""
系统常量和枚举定义
"""
from enum import Enum, auto
from typing import List

class ModelProvider(str, Enum):
    """模型提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    OLLAMA = "ollama"
    LOCAL = "local"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"

class EmbeddingProvider(str, Enum):
    """嵌入模型提供商枚举"""
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    LOCAL = "local"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"

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

class ModelCapability(Enum):
    """模型能力枚举"""
    FUNCTION_CALLING = "function_calling"    # 支持原生Function Calling
    TEXT_ONLY = "text_only"                 # 仅支持文本模式

# 模型Function Calling能力映射表
MODEL_FC_SUPPORT = {
    # OpenAI 模型 - 明确支持FC
    "gpt-4o": True,
    "gpt-4o-mini": True,
    "gpt-4-turbo": True,
    "gpt-4": True,
    "gpt-3.5-turbo": True,
    "o1-preview": False,  # O1系列不支持工具调用
    "o1-mini": False,
    
    # DeepSeek 模型 - 支持OpenAI兼容的FC
    "deepseek-chat": True,
    "deepseek-coder": True,
    "deepseek-reasoner": False,  # 推理模型不支持工具调用
    "deepseek-r1": False,
    "deepseek-r1-lite-preview": False,
    
    # Anthropic 模型 - 支持tool_use
    "claude-3-5-sonnet-20241022": True,
    "claude-3-5-sonnet-20240620": True,
    "claude-3-5-haiku-20241022": True,
    "claude-3-opus-20240229": True,
    
    # Google Gemini 模型 - 支持FC
    "gemini-2.0-flash-exp": True,
    "gemini-1.5-pro": True,
    "gemini-1.5-flash": True,
    "gemini-1.5-flash-8b": True,
    
    # Azure OpenAI 模型（与OpenAI相同）
    "gpt-4": True,
    "gpt-4-32k": True,
    "gpt-35-turbo": True,
    "gpt-35-turbo-16k": True,
    
    # Ollama 模型 - 保守策略，只有明确知道支持的
    "llama3.1:70b": True,
    "qwen2.5:32b": True,
    "qwen2.5:14b": True,
    # 其他Ollama模型默认为False，使用文本模式
}

def supports_function_calling(model_name: str) -> bool:
    """检查模型是否支持Function Calling"""
    return MODEL_FC_SUPPORT.get(model_name, False)

def get_model_capability(model_name: str) -> ModelCapability:
    """获取模型能力"""
    if supports_function_calling(model_name):
        return ModelCapability.FUNCTION_CALLING
    else:
        return ModelCapability.TEXT_ONLY

# 注意：数值常量已移动到 app/core/constants.py 中统一管理
# 请从 app.core.constants 导入相关常量：
# - KnowledgeConstants: 知识库相关常量
# - ChatConstants: 聊天相关常量
# - APIConstants: API相关常量
# 等等... 