"""
Provider配置
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class ProviderConfig(BaseModel):
    """单个Provider配置"""
    name: str = Field(..., description="Provider名称")
    display_name: str = Field(..., description="显示名称")
    enabled: bool = Field(default=True, description="是否启用")
    models: List[str] = Field(default_factory=list, description="支持的模型列表")
    default_model: Optional[str] = Field(default=None, description="默认模型")
    requires_api_key: bool = Field(default=True, description="是否需要API密钥")
    base_url: Optional[str] = Field(default=None, description="基础URL")
    timeout: int = Field(default=30, description="请求超时时间")
    max_retries: int = Field(default=3, description="最大重试次数")
    
class ProvidersConfig(BaseModel):
    """Provider配置"""
    
    # OpenAI配置
    openai: ProviderConfig = Field(
        default=ProviderConfig(
            name="openai",
            display_name="OpenAI",
            models=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            default_model="gpt-3.5-turbo",
            base_url="https://api.openai.com/v1"
        ),
        description="OpenAI配置"
    )
    
    # DeepSeek配置
    deepseek: ProviderConfig = Field(
        default=ProviderConfig(
            name="deepseek",
            display_name="DeepSeek",
            models=["deepseek-chat", "deepseek-coder"],
            default_model="deepseek-chat",
            base_url="https://api.deepseek.com/v1"
        ),
        description="DeepSeek配置"
    )
    
    # Gemini配置
    gemini: ProviderConfig = Field(
        default=ProviderConfig(
            name="gemini",
            display_name="Google Gemini",
            models=["gemini-pro", "gemini-pro-vision"],
            default_model="gemini-pro",
            base_url="https://generativelanguage.googleapis.com/v1"
        ),
        description="Gemini配置"
    )
    
    # Azure OpenAI配置
    azure: ProviderConfig = Field(
        default=ProviderConfig(
            name="azure",
            display_name="Azure OpenAI",
            models=["gpt-35-turbo", "gpt-4"],
            default_model="gpt-35-turbo",
            requires_api_key=True
        ),
        description="Azure OpenAI配置"
    )
    
    # Ollama配置
    ollama: ProviderConfig = Field(
        default=ProviderConfig(
            name="ollama",
            display_name="Ollama",
            models=["llama2", "codellama", "mistral"],
            default_model="llama2",
            requires_api_key=False,
            base_url="http://localhost:11434"
        ),
        description="Ollama配置"
    )
    
    # 默认Provider
    default_provider: str = Field(default="openai", description="默认Provider")
    
    # 全局配置
    global_timeout: int = Field(default=30, description="全局超时时间")
    global_max_retries: int = Field(default=3, description="全局最大重试次数")
    
    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """获取指定Provider配置"""
        return getattr(self, provider_name, None)
    
    def get_enabled_providers(self) -> List[ProviderConfig]:
        """获取启用的Provider列表"""
        providers = []
        for field_name in self.__fields__:
            if field_name.startswith(('openai', 'deepseek', 'gemini', 'azure', 'ollama')):
                provider = getattr(self, field_name)
                if isinstance(provider, ProviderConfig) and provider.enabled:
                    providers.append(provider)
        return providers
    
    def get_all_models(self) -> Dict[str, List[str]]:
        """获取所有Provider的模型列表"""
        models = {}
        for provider in self.get_enabled_providers():
            models[provider.name] = provider.models
        return models
    
    class Config:
        """Pydantic配置"""
        env_prefix = "PROVIDER_" 