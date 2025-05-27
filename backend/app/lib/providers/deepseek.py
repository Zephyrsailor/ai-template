import logging
from typing import List, Optional
from .openai import OpenAIProvider

# 初始化logger
logger = logging.getLogger(__name__)

class DeepSeekProvider(OpenAIProvider):
    """
    DeepSeek API 提供者
    基于OpenAI兼容接口，但有自己的模型列表
    """
    
    def __init__(self, api_key: str, base_url: Optional[str] = "https://api.deepseek.com"):
        super().__init__(api_key=api_key, base_url=base_url)
        logger.info(f"DeepSeek provider initialized with base_url: {self.base_url}")
    
    async def list_models(self) -> List[str]:
        """
        获取DeepSeek API可用的模型列表
        """
        try:
            # 尝试从API获取模型列表
            models_response = await self.client.models.list()
            models = []
            
            # 过滤出DeepSeek模型
            for model in models_response.data:
                model_id = model.id
                # 只包含DeepSeek相关的模型
                if 'deepseek' in model_id.lower():
                    models.append(model_id)
            
            # 如果API返回的模型列表为空，使用默认列表
            if not models:
                models = [
                    "deepseek-chat", 
                    "deepseek-coder", 
                    "deepseek-reasoner", 
                    "deepseek-r1", 
                    "deepseek-r1-lite-preview"
                ]
            
            # 按名称排序
            models.sort()
            return models
            
        except Exception as e:
            logger.error(f"获取DeepSeek模型列表失败: {str(e)}")
            # 返回默认模型列表作为后备
            return [
                "deepseek-chat", 
                "deepseek-coder", 
                "deepseek-reasoner", 
                "deepseek-r1", 
                "deepseek-r1-lite-preview"
            ]

    async def check_model_availability(self, model_id: str) -> bool:
        """
        检查模型是否在DeepSeek中可用
        """
        try:
            available_models = await self.list_models()
            return model_id in available_models
        except Exception as e:
            logger.error(f"检查DeepSeek模型可用性失败: {str(e)}")
            return False 