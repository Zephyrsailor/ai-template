"""
用户LLM配置API路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...domain.models.user import User
from ...domain.models.user_llm_config import UserLLMConfig, LLMProvider
from ...services.user_llm_config import UserLLMConfigService
from ..deps import get_current_user

router = APIRouter(prefix="/api/user/llm-config", tags=["user-llm-config"])

class LLMConfigRequest(BaseModel):
    """LLM配置请求模型"""
    provider: LLMProvider
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1024
    is_default: bool = False
    config_name: str = "默认配置"

class LLMConfigResponse(BaseModel):
    """LLM配置响应模型"""
    provider: str
    model_name: str
    base_url: Optional[str] = None
    temperature: float
    max_tokens: int
    is_default: bool
    config_name: str
    created_at: str
    updated_at: Optional[str] = None

@router.get("/", response_model=List[LLMConfigResponse])
async def get_user_llm_configs(
    current_user: User = Depends(get_current_user)
):
    """获取用户所有LLM配置"""
    service = UserLLMConfigService()
    configs = service.get_user_configs(current_user.id)
    
    # 转换为响应模型（不包含API密钥）
    response_configs = []
    for config in configs:
        config_dict = config.to_dict()
        # 移除敏感信息
        config_dict.pop('api_key', None)
        config_dict.pop('user_id', None)
        response_configs.append(LLMConfigResponse(**config_dict))
    
    return response_configs

@router.get("/default", response_model=Optional[LLMConfigResponse])
async def get_user_default_llm_config(
    current_user: User = Depends(get_current_user)
):
    """获取用户默认LLM配置"""
    service = UserLLMConfigService()
    config = service.get_user_default_config(current_user.id)
    
    if not config:
        return None
    
    # 转换为响应模型（不包含API密钥）
    config_dict = config.to_dict()
    config_dict.pop('api_key', None)
    config_dict.pop('user_id', None)
    
    return LLMConfigResponse(**config_dict)

@router.post("/", response_model=dict)
async def create_user_llm_config(
    config_request: LLMConfigRequest,
    current_user: User = Depends(get_current_user)
):
    """创建或更新用户LLM配置"""
    service = UserLLMConfigService()
    
    # 创建配置对象
    config = UserLLMConfig(
        user_id=current_user.id,
        provider=config_request.provider,
        model_name=config_request.model_name,
        api_key=config_request.api_key,
        base_url=config_request.base_url,
        temperature=config_request.temperature,
        max_tokens=config_request.max_tokens,
        is_default=config_request.is_default,
        config_name=config_request.config_name
    )
    
    # 保存配置
    success = service.save_user_config(config)
    
    if not success:
        raise HTTPException(status_code=500, detail="保存配置失败")
    
    return {"success": True, "message": "配置保存成功"}

@router.delete("/{config_name}", response_model=dict)
async def delete_user_llm_config(
    config_name: str,
    current_user: User = Depends(get_current_user)
):
    """删除用户LLM配置"""
    service = UserLLMConfigService()
    
    success = service.delete_user_config(current_user.id, config_name)
    
    if not success:
        raise HTTPException(status_code=404, detail="配置不存在或删除失败")
    
    return {"success": True, "message": "配置删除成功"}

@router.get("/ollama/models", response_model=List[str])
async def get_ollama_models(
    base_url: Optional[str] = "http://localhost:11434",
    current_user: User = Depends(get_current_user)
):
    """获取 Ollama 实际可用的模型列表"""
    try:
        from ...lib.providers.ollama import OllamaProvider
        
        # 创建 Ollama 提供者实例
        ollama_provider = OllamaProvider(base_url=base_url)
        
        # 获取模型列表
        models = await ollama_provider.list_models()
        
        return models
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"获取 Ollama 模型列表失败: {str(e)}"
        )

@router.get("/models/available", response_model=List[dict])
async def get_available_models_for_user(
    current_user: User = Depends(get_current_user)
):
    """获取用户配置的提供商的所有可用模型（包括动态获取的）+ 默认模型列表，去重合并"""
    try:
        service = UserLLMConfigService()
        user_configs = service.get_user_configs(current_user.id)
        
        # 获取用户配置的所有提供商
        configured_providers = {}
        for config in user_configs:
            provider = config.provider.value
            if provider not in configured_providers:
                configured_providers[provider] = {
                    "base_url": config.base_url,
                    "api_key": config.api_key
                }
        
        # 获取所有可用提供商的信息
        all_providers_info = {
            "openai": {
                "label": "OpenAI",
                "is_dynamic": True  # 现在所有提供商都支持动态获取
            },
            "deepseek": {
                "label": "DeepSeek",
                "is_dynamic": True
            },
            "gemini": {
                "label": "Google Gemini",
                "is_dynamic": True
            },
            "anthropic": {
                "label": "Anthropic",
                "is_dynamic": True
            },
            "azure": {
                "label": "Azure OpenAI",
                "is_dynamic": True
            },
            "ollama": {
                "label": "Ollama",
                "is_dynamic": True
            }
        }
        
        result = []
        
        # 为每个提供商获取模型列表
        for provider_name, provider_info in all_providers_info.items():
            try:
                models = []
                provider_config = configured_providers.get(provider_name, {})
                
                # 动态获取模型列表（如果用户已配置该提供商）
                if provider_name in configured_providers:
                    try:
                        provider_instance = await _create_provider_instance(
                            provider_name, 
                            provider_config.get("api_key"),
                            provider_config.get("base_url")
                        )
                        if provider_instance:
                            dynamic_models = await provider_instance.list_models()
                            if dynamic_models:
                                models = dynamic_models
                    except Exception as e:
                        print(f"动态获取{provider_name}模型失败: {str(e)}")
                
                # 如果动态获取失败或用户未配置，使用默认模型列表
                if not models:
                    models = _get_default_models(provider_name)
                
                # 去重（保持顺序）
                unique_models = []
                seen = set()
                for model in models:
                    if model not in seen:
                        unique_models.append(model)
                        seen.add(model)
                
                if unique_models:
                    result.append({
                        "provider": provider_name,
                        "provider_label": provider_info["label"],
                        "models": unique_models,
                        "is_dynamic": provider_info["is_dynamic"] and provider_name in configured_providers,
                        "base_url": provider_config.get("base_url"),
                        "is_configured": provider_name in configured_providers
                    })
                    
            except Exception as e:
                # 如果某个提供商获取失败，记录错误但继续处理其他提供商
                print(f"获取 {provider_name} 模型列表失败: {str(e)}")
                # 即使失败也添加默认模型列表
                result.append({
                    "provider": provider_name,
                    "provider_label": provider_info["label"],
                    "models": _get_default_models(provider_name),
                    "is_dynamic": False,
                    "base_url": None,
                    "is_configured": provider_name in configured_providers,
                    "error": f"获取模型列表失败: {str(e)}"
                })
                continue
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"获取可用模型列表失败: {str(e)}"
        )

def _get_provider_label(provider_name: str) -> str:
    """获取提供商的显示名称"""
    labels = {
        "openai": "OpenAI",
        "deepseek": "DeepSeek", 
        "azure": "Azure OpenAI",
        "ollama": "Ollama",
        "anthropic": "Anthropic",
        "gemini": "Google Gemini"
    }
    return labels.get(provider_name, provider_name.title())

@router.get("/providers", response_model=List[dict])
async def get_available_providers():
    """获取可用的LLM提供商列表"""
    providers = [
        {
            "value": LLMProvider.OPENAI.value,
            "label": "OpenAI",
            "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            "requires_api_key": True,
            "supports_custom_models": False
        },
        {
            "value": LLMProvider.DEEPSEEK.value,
            "label": "DeepSeek",
            "models": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
            "requires_api_key": True,
            "default_base_url": "https://api.deepseek.com",
            "supports_custom_models": True
        },
        {
            "value": LLMProvider.AZURE.value,
            "label": "Azure OpenAI",
            "models": ["gpt-4", "gpt-35-turbo"],
            "requires_api_key": True,
            "supports_custom_models": True
        },
        {
            "value": LLMProvider.OLLAMA.value,
            "label": "Ollama",
            "models": ["llama2", "llama3", "qwen", "mistral","deepseek-r1:32b","qwen2.5:32b"],
            "requires_api_key": False,
            "default_base_url": "http://localhost:11434",
            "supports_custom_models": True,
            "supports_dynamic_models": True
        },
        {
            "value": LLMProvider.ANTHROPIC.value,
            "label": "Anthropic",
            "models": ["claude-3.7-sonnet", "claude-4-sonnet"],
            "requires_api_key": True,
            "supports_custom_models": False
        },
        {
            "value": LLMProvider.GEMINI.value,
            "label": "Google Gemini",
            "models": ["gemini-2.5-pro", "gemini-2.5-flash"],
            "requires_api_key": True,
            "default_base_url": None,
            "supports_custom_models": True
        }
    ]
    
    return providers 

async def _create_provider_instance(provider_name: str, api_key: str, base_url: str = None):
    """创建提供商实例"""
    try:
        if provider_name == "openai":
            from ...lib.providers.openai import OpenAIProvider
            return OpenAIProvider(api_key=api_key, base_url=base_url)
        elif provider_name == "deepseek":
            from ...lib.providers.deepseek import DeepSeekProvider
            return DeepSeekProvider(api_key=api_key, base_url=base_url)
        elif provider_name == "gemini":
            from ...lib.providers.gemini import GeminiProvider
            return GeminiProvider(api_key=api_key, base_url=base_url)
        elif provider_name == "anthropic":
            from ...lib.providers.anthropic import AnthropicProvider
            return AnthropicProvider(api_key=api_key, base_url=base_url)
        elif provider_name == "azure":
            from ...lib.providers.azure import AzureOpenAIProvider
            return AzureOpenAIProvider(api_key=api_key, base_url=base_url)
        elif provider_name == "ollama":
            from ...lib.providers.ollama import OllamaProvider
            return OllamaProvider(api_key="ollama-local", base_url=base_url or "http://localhost:11434")
        else:
            return None
    except Exception as e:
        print(f"创建{provider_name}提供商实例失败: {str(e)}")
        return None

def _get_default_models(provider_name: str) -> List[str]:
    """获取提供商的默认模型列表"""
    default_models = {
        "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "o1-preview", "o1-mini"],
        "deepseek": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner", "deepseek-r1", "deepseek-r1-lite-preview"],
        "gemini": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b"],
        "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20240620", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
        "azure": ["gpt-4", "gpt-4-32k", "gpt-4-turbo", "gpt-4o", "gpt-35-turbo", "gpt-35-turbo-16k"],
        "ollama": ["llama2", "llama3", "qwen", "mistral", "deepseek-r1:32b", "qwen2.5:32b"]
    }
    return default_models.get(provider_name, []) 