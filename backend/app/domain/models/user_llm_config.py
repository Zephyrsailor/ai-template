"""
用户LLM配置模型
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Text, DateTime, Boolean, Float, Integer, JSON
from sqlalchemy.orm import relationship

from ...core.database import BaseModel as SQLAlchemyBaseModel

class LLMProvider(str, Enum):
    """LLM提供商枚举"""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    AZURE = "azure"
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"

# === Pydantic模型 (用于API) ===

class UserLLMConfigBase(BaseModel):
    """用户LLM配置基础模型"""
    provider: LLMProvider = Field(..., description="LLM提供商")
    model_name: str = Field(..., description="模型名称")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="基础URL")
    temperature: float = Field(default=0.7, description="温度参数", ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, description="单次生成最大token数", ge=1, le=32000)
    context_length: int = Field(default=32768, description="上下文窗口大小", ge=1024, le=1000000)
    system_prompt: Optional[str] = Field(default=None, description="系统提示")
    config_name: str = Field(default="默认配置", description="配置名称")
    is_default: bool = Field(default=False, description="是否为默认配置")
    
    class Config:
        use_enum_values = True

class UserLLMConfigCreate(UserLLMConfigBase):
    """创建用户LLM配置请求模型"""
    pass

class UserLLMConfigUpdate(BaseModel):
    """更新用户LLM配置请求模型"""
    provider: Optional[LLMProvider] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=32000)
    context_length: Optional[int] = Field(None, ge=1024, le=1000000)
    system_prompt: Optional[str] = None
    config_name: Optional[str] = None
    is_default: Optional[bool] = None
    
    class Config:
        use_enum_values = True

class UserLLMConfigResponse(BaseModel):
    """用户LLM配置响应模型"""
    id: str = Field(..., description="配置ID")
    user_id: str = Field(..., description="用户ID")
    provider: LLMProvider = Field(..., description="LLM提供商")
    model_name: str = Field(..., description="模型名称")
    api_key: Optional[str] = Field(default=None, description="API密钥（安全考虑，通常不返回）")
    base_url: Optional[str] = Field(default=None, description="基础URL")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=4096, description="单次生成最大token数")
    context_length: int = Field(default=32768, description="上下文窗口大小")
    system_prompt: Optional[str] = Field(default=None, description="系统提示")
    config_name: str = Field(default="默认配置", description="配置名称")
    is_default: bool = Field(default=False, description="是否为默认配置")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")
    
    class Config:
        use_enum_values = True

class UserLLMConfig(BaseModel):
    """用户LLM配置模型（兼容旧版本）"""
    id: str = Field(..., description="配置ID")
    user_id: str = Field(..., description="用户ID")
    provider: LLMProvider = Field(..., description="LLM提供商")
    model_name: str = Field(..., description="模型名称")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="基础URL")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=4096, description="单次生成最大token数")
    context_length: int = Field(default=32768, description="上下文窗口大小")
    system_prompt: Optional[str] = Field(default=None, description="系统提示")
    config_name: str = Field(default="默认配置", description="配置名称")
    is_default: bool = Field(default=False, description="是否为默认配置")
    created_at: str = Field(..., description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserLLMConfig":
        """从字典创建实例"""
        # 处理provider字段，如果是字符串则转换为枚举
        if isinstance(data.get("provider"), str):
            data["provider"] = LLMProvider(data["provider"])
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = self.model_dump()
        # 将枚举转换为字符串
        if isinstance(data.get("provider"), LLMProvider):
            data["provider"] = data["provider"].value
        return data
    
    def get_provider_params(self) -> Dict[str, Any]:
        """获取Provider参数"""
        params = {}
        
        # 返回Provider构造函数需要的参数
        if self.api_key:
            params["api_key"] = self.api_key
        
        if self.base_url:
            params["base_url"] = self.base_url
            
        return params
    
    class Config:
        """Pydantic配置"""
        from_attributes = True
        use_enum_values = True

# === SQLAlchemy模型 (用于数据库) ===

class UserLLMConfigModel(SQLAlchemyBaseModel):
    """用户LLM配置数据库模型"""
    __tablename__ = "user_llm_configs"
    
    # 基本信息
    user_id = Column(String(36), nullable=False, index=True)
    config_name = Column(String(255), nullable=False)
    
    # LLM配置
    provider = Column(String(50), nullable=False)
    model_name = Column(String(255), nullable=False)
    api_key = Column(Text)  # 加密存储
    base_url = Column(String(500))
    
    # 参数配置
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4096)
    context_length = Column(Integer, default=32768)
    system_prompt = Column(Text)
    
    # 状态
    is_default = Column(Boolean, default=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "config_name": self.config_name,
            "provider": self.provider,
            "model_name": self.model_name,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "context_length": self.context_length,
            "system_prompt": self.system_prompt,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def to_response_model(self) -> UserLLMConfigResponse:
        """转换为响应模型"""
        return UserLLMConfigResponse(
            id=self.id,
            user_id=self.user_id,
            config_name=self.config_name,
            api_key=self.api_key,
            provider=LLMProvider(self.provider),
            model_name=self.model_name,
            base_url=self.base_url,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            context_length=self.context_length,
            system_prompt=self.system_prompt,
            is_default=self.is_default,
            created_at=self.created_at,
            updated_at=self.updated_at
        )
    
    def __repr__(self):
        return f"<UserLLMConfig(id={self.id}, user_id={self.user_id}, config_name={self.config_name})>" 