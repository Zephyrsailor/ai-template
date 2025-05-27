import logging
from typing import List, Optional
from .openai import OpenAIProvider

# 初始化logger
logger = logging.getLogger(__name__)

class AzureOpenAIProvider(OpenAIProvider):
    """
    Azure OpenAI API 提供者
    基于OpenAI兼容接口，但有自己的模型列表和配置
    """
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, api_version: str = "2024-02-01"):
        # Azure OpenAI需要特殊的base_url格式
        if base_url and not base_url.endswith('/'):
            base_url = base_url + '/'
        
        super().__init__(api_key=api_key, base_url=base_url)
        self.api_version = api_version
        logger.info(f"Azure OpenAI provider initialized with base_url: {self.base_url}")
    
    async def list_models(self) -> List[str]:
        """
        获取Azure OpenAI可用的模型列表
        注意：Azure OpenAI的模型列表通常是部署特定的，这里返回常见的模型
        """
        try:
            # 尝试从API获取模型列表
            try:
                models_response = await self.client.models.list()
                models = []
                
                # 过滤出聊天模型
                chat_model_prefixes = ['gpt-', 'text-davinci']
                
                for model in models_response.data:
                    model_id = model.id
                    if any(model_id.startswith(prefix) for prefix in chat_model_prefixes):
                        models.append(model_id)
                
                if models:
                    models.sort()
                    return models
            except Exception as api_error:
                logger.warning(f"无法从Azure API获取模型列表: {str(api_error)}")
            
            # 如果API调用失败，返回Azure OpenAI的常见模型
            models = [
                "gpt-4",
                "gpt-4-32k", 
                "gpt-4-turbo",
                "gpt-4o",
                "gpt-35-turbo",
                "gpt-35-turbo-16k"
            ]
            
            return models
            
        except Exception as e:
            logger.error(f"获取Azure OpenAI模型列表失败: {str(e)}")
            # 返回默认模型列表作为后备
            return ["gpt-4", "gpt-35-turbo"]

    async def check_model_availability(self, model_id: str) -> bool:
        """
        检查模型是否在Azure OpenAI中可用
        """
        try:
            available_models = await self.list_models()
            return model_id in available_models
        except Exception as e:
            logger.error(f"检查Azure OpenAI模型可用性失败: {str(e)}")
            return False 