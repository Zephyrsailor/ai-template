"""
用户LLM配置模型
"""
from datetime import datetime
from typing import Dict, Optional, Any
from enum import Enum

class LLMProvider(str, Enum):
    """LLM提供商枚举"""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    AZURE = "azure"
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"

class UserLLMConfig:
    """用户LLM配置模型"""
    def __init__(
        self,
        user_id: str,
        provider: LLMProvider,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        is_default: bool = False,
        config_name: str = "默认配置",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.user_id = user_id
        self.provider = provider
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.is_default = is_default
        self.config_name = config_name
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "provider": self.provider.value,
            "model_name": self.model_name,
            "api_key": self.api_key,  # 注意：实际存储时应加密
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "is_default": self.is_default,
            "config_name": self.config_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserLLMConfig":
        """从字典创建配置"""
        if "provider" in data and not isinstance(data["provider"], LLMProvider):
            data["provider"] = LLMProvider(data["provider"])
            
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            
        if "updated_at" in data and isinstance(data["updated_at"], str) and data["updated_at"]:
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            
        return cls(**data)
    
    def get_provider_params(self) -> Dict[str, Any]:
        """获取Provider初始化参数"""
        params = {
            "api_key": self.api_key or "default",
            "base_url": self.base_url
        }
        
        # 移除None值
        return {k: v for k, v in params.items() if v is not None} 