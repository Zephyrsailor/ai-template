"""
用户LLM配置服务 - 数据库版本
"""
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.service import BaseService
from ..core.logging import get_logger
from ..core.errors import (
    NotFoundException, ServiceException, ConflictException, 
    ValidationException
)
from ..domain.models.user_llm_config import (
    UserLLMConfigModel, UserLLMConfigCreate, UserLLMConfigUpdate, 
    UserLLMConfigResponse, LLMProvider, UserLLMConfig
)
from ..repositories.user_llm_config import UserLLMConfigRepository
from ..core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()



class UserLLMConfigService(BaseService[UserLLMConfigModel, UserLLMConfigRepository]):
    """用户LLM配置服务 - 数据库版本"""
    
    def __init__(self, session: AsyncSession):
        """初始化用户LLM配置服务"""
        repository = UserLLMConfigRepository(session)
        super().__init__(repository)
        
        self.session = session
        logger.info("用户LLM配置服务初始化（数据库模式）")
    
    def get_entity_name(self) -> str:
        """获取实体名称"""
        return "用户LLM配置"
    
    # === 配置管理 ===
    
    async def create_config(self, user_id: str, config_data: UserLLMConfigCreate) -> UserLLMConfigResponse:
        """创建用户LLM配置"""
        # 检查配置名称是否已存在
        existing_config = await self.repository.find_by_user_and_name(user_id, config_data.config_name)
        if existing_config:
            raise ConflictException(f"配置名称 '{config_data.config_name}' 已存在")
        
        # 如果设置为默认配置，先清除其他默认配置
        if config_data.is_default:
            await self.repository.clear_default_configs(user_id)
        
        # 创建配置数据
        config_dict = config_data.model_dump()
        config_dict.update({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "created_at": datetime.now()
        })
        
        # 保存到数据库
        config = await self.repository.create(config_dict)
        
        logger.info(f"创建用户LLM配置成功: {config.config_name} (用户: {user_id})")
        return config.to_response_model()
    
    async def get_config(self, config_id: str, user_id: str) -> UserLLMConfigResponse:
        """获取用户LLM配置详情"""
        config = await self.repository.get_user_config(config_id, user_id)
        if not config:
            raise NotFoundException(f"LLM配置 {config_id} 不存在")
        
        return config.to_response_model()
    
    async def list_configs(self, user_id: str) -> List[UserLLMConfigResponse]:
        """获取用户所有LLM配置"""
        configs = await self.repository.find_by_user_id(user_id)
        return [config.to_response_model() for config in configs]
    
    async def update_config(self, config_id: str, user_id: str, update_data: UserLLMConfigUpdate) -> UserLLMConfigResponse:
        """更新用户LLM配置"""
        # 检查配置是否存在且属于用户
        config = await self.repository.get_user_config(config_id, user_id)
        if not config:
            raise NotFoundException(f"LLM配置 {config_id} 不存在")
        
        # 检查配置名称冲突
        if update_data.config_name and update_data.config_name != config.config_name:
            existing = await self.repository.find_by_user_and_name(user_id, update_data.config_name)
            if existing and existing.id != config_id:
                raise ConflictException(f"配置名称 '{update_data.config_name}' 已存在")
        
        # 如果设置为默认配置，先清除其他默认配置
        if update_data.is_default:
            await self.repository.clear_default_configs(user_id)
        
        # 准备更新数据
        update_dict = {k: v for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None}
        update_dict["updated_at"] = datetime.now()
        
        # 更新数据库
        updated_config = await self.repository.update(config_id, update_dict)
        if not updated_config:
            raise ServiceException("更新配置失败")
        
        logger.info(f"更新用户LLM配置成功: {config_id}")
        return updated_config.to_response_model()
    
    async def delete_config(self, config_id: str, user_id: str) -> bool:
        """删除用户LLM配置"""
        # 检查配置是否存在且属于用户
        if not await self.repository.check_user_ownership(config_id, user_id):
            raise NotFoundException(f"LLM配置 {config_id} 不存在")
        
        # 删除数据库记录
        success = await self.repository.delete(config_id)
        if success:
            logger.info(f"删除用户LLM配置成功: {config_id}")
        
        return success
    
    # === 默认配置管理 ===
    
    async def get_default_config(self, user_id: str) -> Optional[UserLLMConfigResponse]:
        """获取用户默认LLM配置"""
        config = await self.repository.find_default_config(user_id)
        if not config:
            # 如果没有默认配置，返回第一个配置
            configs = await self.repository.find_by_user_id(user_id)
            if configs:
                config = configs[0]
            else:
                # 如果没有任何配置，创建默认配置
                return await self._create_default_config(user_id)
        
        return config.to_response_model()
    
    async def set_default_config(self, config_id: str, user_id: str) -> bool:
        """设置默认配置"""
        # 检查配置是否存在且属于用户
        if not await self.repository.check_user_ownership(config_id, user_id):
            raise NotFoundException(f"LLM配置 {config_id} 不存在")
        
        return await self.repository.set_default_config(config_id, user_id)
    
    # === 查询方法 ===
    
    async def find_by_provider(self, user_id: str, provider: str) -> List[UserLLMConfigResponse]:
        """根据提供商查找配置"""
        configs = await self.repository.find_by_provider(user_id, provider)
        return [config.to_response_model() for config in configs]
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户配置统计信息"""
        return await self.repository.get_user_stats(user_id)
    
    # === 兼容性方法（向后兼容旧版本API） ===
    
    def get_user_config(self, user_id: str) -> Dict[str, Any]:
        """获取用户LLM配置（向后兼容方法）"""
        # 这个方法需要同步调用，暂时返回默认配置
        # 在实际使用中应该使用异步方法
        logger.warning("使用了同步兼容方法 get_user_config，建议使用异步方法")
        return self._get_default_config_dict()
    
    def get_user_configs(self, user_id: str) -> List[UserLLMConfig]:
        """获取用户所有LLM配置（向后兼容方法）"""
        # 这个方法需要同步调用，暂时返回默认配置
        logger.warning("使用了同步兼容方法 get_user_configs，建议使用异步方法")
        return [self._get_default_user_config()]
    
    def get_user_default_config(self, user_id: str) -> Optional[UserLLMConfig]:
        """获取用户默认LLM配置（向后兼容方法）"""
        logger.warning("使用了同步兼容方法 get_user_default_config，建议使用异步方法")
        return self._get_default_user_config()
    
    def save_user_config(self, config: UserLLMConfig) -> bool:
        """保存用户LLM配置（向后兼容方法）"""
        logger.warning("使用了同步兼容方法 save_user_config，建议使用异步方法")
        return True
    
    def delete_user_config(self, user_id: str, config_name: str) -> bool:
        """删除用户配置（向后兼容方法）"""
        logger.warning("使用了同步兼容方法 delete_user_config，建议使用异步方法")
        return True
    
    # === 工具方法 ===
    
    def list_available_providers(self) -> List[str]:
        """获取可用的LLM提供商列表"""
        return [provider.value for provider in LLMProvider]
    
    def list_available_models(self, provider: str) -> List[str]:
        """获取指定提供商的可用模型列表"""
        models_map = {
            "openai": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o"],
            "anthropic": ["claude-3-haiku", "claude-3-sonnet", "claude-3-opus"],
            "azure": ["gpt-35-turbo", "gpt-4", "gpt-4-32k"],
            "ollama": ["llama2", "llama2:13b", "codellama", "mistral"],
            "deepseek": ["deepseek-chat", "deepseek-coder"],
            "gemini": ["gemini-pro", "gemini-pro-vision"]
        }
        return models_map.get(provider, [])
    
    # === 私有方法 ===
    
    async def _create_default_config(self, user_id: str) -> UserLLMConfigResponse:
        """创建默认配置"""

        default_config = UserLLMConfigCreate(
            provider=LLMProvider.DEEPSEEK,
            model_name="deepseek-chat",
            temperature=0.7,
            max_tokens=4096,
            context_length=32768,
            system_prompt="你是一个有用的AI助手。",
            config_name="默认配置",
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            is_default=True
        )
        
        return await self.create_config(user_id, default_config)
    
    def _get_default_user_config(self) -> UserLLMConfig:
        """获取默认用户配置对象（兼容性）"""
        # 尝试使用系统配置的API密钥    
        #     
        # 根据系统默认Provider选择配置
        if settings.LLM_PROVIDER == "ollama":
            return UserLLMConfig(
                id="default_config",
                user_id="unknown",
                provider=LLMProvider.OLLAMA,
                model_name=settings.LLM_MODEL_NAME,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0.7,
                max_tokens=4096,
                context_length=32768,
                system_prompt="你是一个有用的AI助手。",
                config_name="默认配置",
                is_default=True,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
        elif settings.LLM_PROVIDER == "deepseek":
            return UserLLMConfig(
                id="default_config",
                user_id="unknown",
                provider=LLMProvider.DEEPSEEK,
                model_name=settings.LLM_MODEL_NAME,
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                temperature=0.7,
                max_tokens=4096,
                context_length=32768,
                system_prompt="你是一个有用的AI助手。",
                config_name="默认配置",
                is_default=True,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
        else:
            # 默认使用OpenAI配置
            return UserLLMConfig(
                id="default_config",
                user_id="unknown",
                provider=LLMProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                temperature=0.7,
                max_tokens=4096,
                context_length=32768,
                system_prompt="你是一个有用的AI助手。",
                config_name="默认配置",
                is_default=True,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
    
    def _get_default_config_dict(self) -> Dict[str, Any]:
        """获取默认配置字典（兼容性）"""
        return self._get_default_user_config().to_dict() 