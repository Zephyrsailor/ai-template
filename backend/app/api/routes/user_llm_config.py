"""
用户LLM配置API路由 - 数据库版本
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from ...domain.models.user import User
from ...domain.models.user_llm_config import (
    UserLLMConfigCreate, UserLLMConfigUpdate, UserLLMConfigResponse, LLMProvider
)
from ...domain.schemas.base import ApiResponse
from ...services.user_llm_config import UserLLMConfigService
from ...core.errors import NotFoundException, ConflictException, ValidationException
from ..deps import get_user_llm_config_service, api_response, get_current_user
from ...core.logging import get_logger

router = APIRouter(prefix="/api/user/llm-config", tags=["user-llm-config"])
logger = get_logger(__name__)

# === 响应模型定义 ===

class ConfigListResponse(ApiResponse[List[UserLLMConfigResponse]]):
    """配置列表响应"""
    pass

class ConfigDetailResponse(ApiResponse[UserLLMConfigResponse]):
    """配置详情响应"""
    pass

class ConfigStatsResponse(ApiResponse[dict]):
    """配置统计响应"""
    pass

class ProvidersResponse(ApiResponse[List[str]]):
    """提供商列表响应"""
    pass

class ModelsResponse(ApiResponse[List[str]]):
    """模型列表响应"""
    pass

class ProviderInfo(BaseModel):
    """提供商信息"""
    value: Optional[str] = Field(None, description="提供商值")
    label: Optional[str] = Field(None, description="提供商显示名称")
    provider: Optional[str] = Field(None, description="提供商名称（别名）")
    provider_label: Optional[str] = Field(None, description="提供商显示名称（别名）")
    models: List[str] = Field(default_factory=list, description="支持的模型列表")
    requires_api_key: bool = Field(default=True, description="是否需要API密钥")
    default_base_url: Optional[str] = Field(default=None, description="默认基础URL")
    supports_custom_models: bool = Field(default=False, description="是否支持自定义模型")
    supports_dynamic_models: bool = Field(default=False, description="是否支持动态模型加载")
    is_dynamic: bool = Field(default=False, description="是否动态加载")
    base_url: Optional[str] = Field(default=None, description="基础URL")
    is_configured: bool = Field(default=False, description="是否已配置")
    
    def __init__(self, **data):
        super().__init__(**data)
        # 自动设置别名字段
        if self.provider and not self.value:
            self.value = self.provider
        if self.provider_label and not self.label:
            self.label = self.provider_label
        if self.value and not self.provider:
            self.provider = self.value
        if self.label and not self.provider_label:
            self.provider_label = self.label

class ProvidersInfoResponse(ApiResponse[List[ProviderInfo]]):
    """提供商信息列表响应"""
    pass

class ProviderModels(BaseModel):
    """提供商模型信息"""
    provider: str = Field(..., description="提供商名称")
    provider_label: str = Field(..., description="提供商显示名称")
    models: List[str] = Field(default_factory=list, description="可用模型列表")
    has_user_config: bool = Field(default=False, description="用户是否有此提供商的配置")

class AvailableModelsResponse(ApiResponse[List[ProviderModels]]):
    """可用模型列表响应"""
    pass

# === 配置管理API ===

@router.post("/", response_model=ConfigDetailResponse, status_code=201)
async def create_llm_config(
    config_data: UserLLMConfigCreate,
    current_user: User = Depends(get_current_user),
    service: UserLLMConfigService = Depends(get_user_llm_config_service)
):
    """创建用户LLM配置"""
    try:
        config = await service.create_config(current_user.id, config_data)
        return api_response(data=config, message="LLM配置创建成功")
    except ConflictException as e:
        return api_response(code=409, message=str(e))
    except ValidationException as e:
        return api_response(code=400, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"创建LLM配置失败: {str(e)}")

@router.get("/", response_model=ConfigListResponse)
async def list_llm_configs(
    current_user: User = Depends(get_current_user),
    service: UserLLMConfigService = Depends(get_user_llm_config_service)
):
    """获取用户所有LLM配置"""
    try:
        configs = await service.list_configs(current_user.id)
        return api_response(data=configs)
    except Exception as e:
        return api_response(code=500, message=f"获取配置列表失败: {str(e)}")

@router.get("/default", response_model=ConfigDetailResponse)
async def get_default_llm_config(
    current_user: User = Depends(get_current_user),
    service: UserLLMConfigService = Depends(get_user_llm_config_service)
):
    """获取用户默认LLM配置"""
    try:
        config = await service.get_default_config(current_user.id)
        if not config:
            return api_response(code=404, message="未找到默认配置")
        return api_response(data=config)
    except Exception as e:
        return api_response(code=500, message=f"获取默认配置失败: {str(e)}")

@router.get("/providers")
async def get_llm_providers():
    """获取LLM提供商列表（前端兼容格式）- 不需要认证的基础信息"""

    # 临时返回前端期望的格式，包含value和label字段
    providers_info = [
        {
            "value": "openai",
            "label": "OpenAI",
            "models": [
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
                "gpt-4",
                "gpt-3.5-turbo",
                "o1-preview",
                "o1-mini"
            ],
            "requires_api_key": True,
            "supports_custom_models": True,
            "supports_dynamic_models": False,
            "default_base_url": None
        },
        {
            "value": "deepseek",
            "label": "DeepSeek",
            "models": [
                "deepseek-chat",
                "deepseek-coder",
                "deepseek-reasoner",
                "deepseek-r1",
                "deepseek-r1-lite-preview"
            ],
            "requires_api_key": True,
            "supports_custom_models": True,
            "supports_dynamic_models": False,
            "default_base_url": None
        },
        {
            "value": "gemini",
            "label": "Google Gemini",
            "models": [
                "gemini-2.0-flash-exp",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-1.5-flash-8b"
            ],
            "requires_api_key": True,
            "supports_custom_models": False,
            "supports_dynamic_models": False,
            "default_base_url": None
        },
        {
            "value": "anthropic",
            "label": "Anthropic",
            "models": [
                "claude-3-5-sonnet-20241022",
                "claude-3-5-sonnet-20240620",
                "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229"
            ],
            "requires_api_key": True,
            "supports_custom_models": False,
            "supports_dynamic_models": False,
            "default_base_url": None
        },
        {
            "value": "azure",
            "label": "Azure OpenAI",
            "models": [
                "gpt-4",
                "gpt-4-32k",
                "gpt-4-turbo",
                "gpt-4o",
                "gpt-35-turbo",
                "gpt-35-turbo-16k"
            ],
            "requires_api_key": True,
            "supports_custom_models": True,
            "supports_dynamic_models": False,
            "default_base_url": None
        },
        {
            "value": "ollama",
            "label": "Ollama",
            "models": [
                "llama3.2:latest", "llama3.2:3b", "llama3.2:1b",
                "llama3.1:latest", "llama3.1:8b", "llama3.1:70b",
                "qwen2.5:latest", "qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b",
                "deepseek-r1:1.5b", "deepseek-r1:7b", "deepseek-r1:8b", "deepseek-r1:14b", "deepseek-r1:32b",
                "mistral:latest", "mistral:7b",
                "phi3:latest", "phi3:mini", "phi3:medium",
                "codellama:latest", "codellama:7b", "codellama:13b",
                "gemma2:latest", "gemma2:2b", "gemma2:9b", "gemma2:27b"
            ],
            "requires_api_key": False,
            "supports_custom_models": True,
            "supports_dynamic_models": True,
            "default_base_url": "http://localhost:11434"
        }
    ]
    try:
        return {"success": True, "code": 200, "message": "success", "data": providers_info}
    except Exception as e:
        return {"success": False, "code": 500, "message": f"获取提供商列表失败: {str(e)}", "data": []}

@router.get("/{config_id}", response_model=ConfigDetailResponse)
async def get_llm_config(
    config_id: str = Path(..., description="配置ID"),
    current_user: User = Depends(get_current_user),
    service: UserLLMConfigService = Depends(get_user_llm_config_service)
):
    """获取用户LLM配置详情"""
    try:
        config = await service.get_config(config_id, current_user.id)
        return api_response(data=config)
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"获取配置详情失败: {str(e)}")

@router.put("/{config_id}", response_model=ConfigDetailResponse)
async def update_llm_config(
    config_id: str = Path(..., description="配置ID"),
    update_data: UserLLMConfigUpdate = Body(...),
    current_user: User = Depends(get_current_user),
    service: UserLLMConfigService = Depends(get_user_llm_config_service)
):
    """更新用户LLM配置"""
    try:
        config = await service.update_config(config_id, current_user.id, update_data)
        return api_response(data=config, message="LLM配置更新成功")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except ConflictException as e:
        return api_response(code=409, message=str(e))
    except ValidationException as e:
        return api_response(code=400, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"更新LLM配置失败: {str(e)}")

@router.delete("/{config_id}")
async def delete_llm_config(
    config_id: str = Path(..., description="配置ID"),
    current_user: User = Depends(get_current_user),
    service: UserLLMConfigService = Depends(get_user_llm_config_service)
):
    """删除用户LLM配置"""
    try:
        success = await service.delete_config(config_id, current_user.id)
        if success:
            return api_response(message="LLM配置删除成功")
        else:
            return api_response(code=500, message="删除LLM配置失败")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"删除LLM配置失败: {str(e)}")

# === 默认配置管理API ===

@router.post("/{config_id}/set-default")
async def set_default_config(
    config_id: str = Path(..., description="配置ID"),
    current_user: User = Depends(get_current_user),
    service: UserLLMConfigService = Depends(get_user_llm_config_service)
):
    """设置默认配置"""
    try:
        success = await service.set_default_config(config_id, current_user.id)
        if success:
            return api_response(message="默认配置设置成功")
        else:
            return api_response(code=500, message="设置默认配置失败")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"设置默认配置失败: {str(e)}")

# === 查询API ===

@router.get("/provider/{provider}", response_model=ConfigListResponse)
async def get_configs_by_provider(
    provider: str = Path(..., description="提供商名称"),
    current_user: User = Depends(get_current_user),
    service: UserLLMConfigService = Depends(get_user_llm_config_service)
):
    """根据提供商获取配置列表"""
    try:
        configs = await service.find_by_provider(current_user.id, provider)
        return api_response(data=configs)
    except Exception as e:
        return api_response(code=500, message=f"获取配置列表失败: {str(e)}")

@router.get("/stats/user", response_model=ConfigStatsResponse)
async def get_user_config_stats(
    current_user: User = Depends(get_current_user),
    service: UserLLMConfigService = Depends(get_user_llm_config_service)
):
    """获取用户配置统计信息"""
    try:
        stats = await service.get_user_stats(current_user.id)
        return api_response(data=stats)
    except Exception as e:
        return api_response(code=500, message=f"获取统计信息失败: {str(e)}")

# === 工具API ===

@router.get("/providers/available", response_model=ProvidersResponse)
async def get_available_providers(
    service: UserLLMConfigService = Depends(get_user_llm_config_service)
):
    """获取可用的LLM提供商列表"""
    try:
        providers = service.list_available_providers()
        return api_response(data=providers)
    except Exception as e:
        return api_response(code=500, message=f"获取提供商列表失败: {str(e)}")

# @router.get("/models/{provider}", response_model=ModelsResponse)
# async def get_available_models(
#     provider: str = Path(..., description="提供商名称"),
#     service: UserLLMConfigService = Depends(get_user_llm_config_service)
# ):
#     """获取指定提供商的可用模型列表"""
#     try:
#         models = service.list_available_models(provider)
#         return api_response(data=models)
#     except Exception as e:
#         return api_response(code=500, message=f"获取模型列表失败: {str(e)}")
    

@router.get("/models/available", response_model=AvailableModelsResponse)
async def get_available_models_for_user(
    current_user: User = Depends(get_current_user),
    service: UserLLMConfigService = Depends(get_user_llm_config_service)
):
    """获取用户配置的所有提供商的可用模型列表"""
    try:
        # 获取用户配置
        user_configs = await service.list_configs(current_user.id)
        user_providers = {}
        
        # 构建用户配置的提供商映射
        for config in user_configs:
            provider = config.provider
            if provider not in user_providers:
                user_providers[provider] = {
                    "base_url": config.base_url,
                    "config_name": config.config_name
                }
        
        # 定义所有提供商的信息
        all_providers_info = {
            "openai": {"label": "OpenAI"},
            "deepseek": {"label": "DeepSeek"},
            "anthropic": {"label": "Anthropic"},
            "gemini": {"label": "Google Gemini"},
            "azure": {"label": "Azure OpenAI"},
            "ollama": {"label": "Ollama"}
        }
        
        result = []
        
        # 只为用户已配置的提供商获取模型列表
        for provider_name in user_providers.keys():
            try:
                provider_info = all_providers_info.get(provider_name, {"label": provider_name.title()})
                
                # 使用默认模型列表
                models = _get_default_models(provider_name)
                
                # 如果是Ollama，尝试获取动态模型列表
                if provider_name == "ollama":
                    try:
                        base_url = user_providers[provider_name].get("base_url", "http://localhost:11434")
                        # TODO: 实现动态获取Ollama模型
                        # 暂时使用扩展的静态列表
                        models = [
                            "llama3.2:latest", "llama3.2:3b", "llama3.2:1b",
                            "llama3.1:latest", "llama3.1:8b", "llama3.1:70b",
                            "qwen2.5:latest", "qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b",
                            "deepseek-r1:1.5b", "deepseek-r1:7b", "deepseek-r1:8b", "deepseek-r1:14b", "deepseek-r1:32b",
                            "mistral:latest", "mistral:7b",
                            "phi3:latest", "phi3:mini", "phi3:medium",
                            "codellama:latest", "codellama:7b", "codellama:13b",
                            "gemma2:latest", "gemma2:2b", "gemma2:9b", "gemma2:27b"
                        ]
                    except Exception as e:
                        logger.warning(f"获取Ollama动态模型失败，使用默认列表: {str(e)}")
                
                if models:
                    result.append(ProviderModels(
                        provider=provider_name,
                        provider_label=provider_info["label"],
                        models=models,
                        has_user_config=True
                    ))
                    
            except Exception as e:
                # 如果某个提供商处理失败，记录错误但继续处理其他提供商
                logger.error(f"处理 {provider_name} 提供商失败: {str(e)}")
                # 添加默认模型列表作为后备
                default_models = _get_default_models(provider_name)
                if default_models:
                    result.append(ProviderModels(
                        provider=provider_name,
                        provider_label=all_providers_info.get(provider_name, {"label": provider_name.title()})["label"],
                        models=default_models,
                        has_user_config=True
                    ))
        
        return api_response(data=result)
        
    except Exception as e:
        logger.error(f"获取可用模型列表失败: {str(e)}")
        return api_response(code=500, message=f"获取可用模型列表失败: {str(e)}")

# === 兼容性API（保持向后兼容） ===

class LegacyConfigResponse(BaseModel):
    """旧版配置响应格式"""
    provider: str
    model_name: str
    base_url: Optional[str] = None
    temperature: float
    max_tokens: int
    is_default: bool
    config_name: str
    created_at: str
    updated_at: Optional[str] = None

@router.get("/legacy/list", response_model=List[LegacyConfigResponse])
async def get_user_llm_configs_legacy(
    current_user: User = Depends(get_current_user),
    service: UserLLMConfigService = Depends(get_user_llm_config_service)
):
    """获取用户所有LLM配置（兼容性API）"""
    try:
        configs = await service.list_configs(current_user.id)
        
        # 转换为旧版响应格式
        legacy_configs = []
        for config in configs:
            legacy_configs.append(LegacyConfigResponse(
                provider=config.provider.value,
                model_name=config.model_name,
                base_url=config.base_url,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                is_default=config.is_default,
                config_name=config.config_name,
                created_at=config.created_at.isoformat(),
                updated_at=config.updated_at.isoformat() if config.updated_at else None
            ))
        
        return legacy_configs
    except Exception as e:
        logger.error(f"获取用户LLM配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取配置列表失败")

@router.get("/legacy/default", response_model=Optional[LegacyConfigResponse])
async def get_user_default_llm_config_legacy(
    current_user: User = Depends(get_current_user),
    service: UserLLMConfigService = Depends(get_user_llm_config_service)
):
    """获取用户默认LLM配置（兼容性API）"""
    try:
        config = await service.get_default_config(current_user.id)
        
        if not config:
            return None
        
        # 转换为旧版响应格式
        return LegacyConfigResponse(
            provider=config.provider.value,
            model_name=config.model_name,
            base_url=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            is_default=config.is_default,
            config_name=config.config_name,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat() if config.updated_at else None
        )
    except Exception as e:
        logger.error(f"获取用户默认LLM配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取默认配置失败")

# === Ollama特殊API ===

@router.get("/ollama/models", response_model=List[str])
async def get_ollama_models(
    base_url: Optional[str] = Query("http://localhost:11434", description="Ollama服务器地址"),
    current_user: User = Depends(get_current_user)
):
    """获取Ollama可用模型列表"""
    try:
        # TODO: 实现动态获取Ollama模型列表
        # 这里暂时返回静态列表
        models = ["llama2", "llama2:13b", "codellama", "mistral", "neural-chat"]
        return models
    except Exception as e:
        logger.error(f"获取Ollama模型列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取Ollama模型列表失败")

@router.get("/models/available", response_model=AvailableModelsResponse)
async def get_available_models_for_user(
    current_user: User = Depends(get_current_user),
    service: UserLLMConfigService = Depends(get_user_llm_config_service)
):
    """获取用户配置的所有提供商的可用模型列表"""
    try:
        # 获取用户配置
        user_configs = await service.list_configs(current_user.id)
        user_providers = {}
        
        # 构建用户配置的提供商映射
        for config in user_configs:
            provider = config.provider
            if provider not in user_providers:
                user_providers[provider] = {
                    "base_url": config.base_url,
                    "config_name": config.config_name
                }
        
        # 定义所有提供商的信息
        all_providers_info = {
            "openai": {"label": "OpenAI"},
            "deepseek": {"label": "DeepSeek"},
            "anthropic": {"label": "Anthropic"},
            "gemini": {"label": "Google Gemini"},
            "azure": {"label": "Azure OpenAI"},
            "ollama": {"label": "Ollama"}
        }
        
        result = []
        
        # 只为用户已配置的提供商获取模型列表
        for provider_name in user_providers.keys():
            try:
                provider_info = all_providers_info.get(provider_name, {"label": provider_name.title()})
                
                # 使用默认模型列表
                models = _get_default_models(provider_name)
                
                # 如果是Ollama，尝试获取动态模型列表
                if provider_name == "ollama":
                    try:
                        base_url = user_providers[provider_name].get("base_url", "http://localhost:11434")
                        # TODO: 实现动态获取Ollama模型
                        # 暂时使用扩展的静态列表
                        models = [
                            "llama3.2:latest", "llama3.2:3b", "llama3.2:1b",
                            "llama3.1:latest", "llama3.1:8b", "llama3.1:70b",
                            "qwen2.5:latest", "qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b",
                            "deepseek-r1:1.5b", "deepseek-r1:7b", "deepseek-r1:8b", "deepseek-r1:14b", "deepseek-r1:32b",
                            "mistral:latest", "mistral:7b",
                            "phi3:latest", "phi3:mini", "phi3:medium",
                            "codellama:latest", "codellama:7b", "codellama:13b",
                            "gemma2:latest", "gemma2:2b", "gemma2:9b", "gemma2:27b"
                        ]
                    except Exception as e:
                        logger.warning(f"获取Ollama动态模型失败，使用默认列表: {str(e)}")
                
                if models:
                    result.append(ProviderModels(
                        provider=provider_name,
                        provider_label=provider_info["label"],
                        models=models,
                        has_user_config=True
                    ))
                    
            except Exception as e:
                # 如果某个提供商处理失败，记录错误但继续处理其他提供商
                logger.error(f"处理 {provider_name} 提供商失败: {str(e)}")
                # 添加默认模型列表作为后备
                default_models = _get_default_models(provider_name)
                if default_models:
                    result.append(ProviderModels(
                        provider=provider_name,
                        provider_label=all_providers_info.get(provider_name, {"label": provider_name.title()})["label"],
                        models=default_models,
                        has_user_config=True
                    ))
        
        return api_response(data=result)
        
    except Exception as e:
        logger.error(f"获取可用模型列表失败: {str(e)}")
        return api_response(code=500, message=f"获取可用模型列表失败: {str(e)}")

# === 辅助函数 ===

def _get_default_models(provider_name: str) -> List[str]:
    """获取提供商的默认模型列表"""
    default_models = {
        "openai": [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
            "o1-preview", "o1-mini"
        ],
        "deepseek": [
            "deepseek-chat", "deepseek-coder", "deepseek-reasoner",
            "deepseek-r1", "deepseek-r1-lite-preview"
        ],
        "anthropic": [
            "claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20240620",
            "claude-3-5-haiku-20241022", "claude-3-opus-20240229"
        ],
        "gemini": [
            "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b"
        ],
        "azure": [
            "gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-4-32k",
            "gpt-35-turbo", "gpt-35-turbo-16k"
        ],
        "ollama": [
            "llama3.2:latest", "llama3.2:3b", "llama3.2:1b",
            "llama3.1:latest", "llama3.1:8b", "llama3.1:70b",
            "qwen2.5:latest", "qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b",
            "deepseek-r1:1.5b", "deepseek-r1:7b", "deepseek-r1:8b", "deepseek-r1:14b", "deepseek-r1:32b",
            "mistral:latest", "mistral:7b",
            "phi3:latest", "phi3:mini", "phi3:medium",
            "codellama:latest", "codellama:7b", "codellama:13b",
            "gemma2:latest", "gemma2:2b", "gemma2:9b", "gemma2:27b"
        ]
    }
    return default_models.get(provider_name, [])

# 在文件末尾添加新的API端点
@router.get("/model-limits/{model_name}")
async def get_model_limits(
    model_name: str = Path(..., description="模型名称")
):
    """获取指定模型的推荐token参数"""
    try:
        # 使用BaseProvider的get_model_limits方法
        from ...lib.providers.base import BaseProvider
        provider = BaseProvider()
        limits = provider.get_model_limits(model_name)
        
        return api_response(
            data={
                "model_name": model_name,
                "context_length": limits["context_length"],
                "max_tokens": limits["max_tokens"],
                "description": f"模型 {model_name} 的推荐参数"
            },
            message="获取模型参数成功"
        )
    except Exception as e:
        logger.error(f"获取模型参数失败: {str(e)}")
        return api_response(code=500, message=f"获取模型参数失败: {str(e)}")