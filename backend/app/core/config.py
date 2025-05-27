"""
配置模块 - 提供应用配置和环境变量处理
"""
import os
from functools import lru_cache
from typing import Optional, Dict, Any
import logging

from pydantic_settings import BaseSettings

# 设置日志记录器
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """应用配置"""
    # 应用设置
    APP_NAME: str = "AI助手"
    APP_DESCRIPTION: str = "基于大语言模型的AI助手"
    
    # API密钥
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    AZURE_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    # LLM配置
    LLM_PROVIDER: str = "ollama"  # 可选值: "openai", "anthropic", "azure", "ollama", "local", "deepseek", "gemini"
    LLM_MODEL_NAME: str = "llama2"  # 默认模型名称
    
    # 嵌入模型配置
    EMBEDDING_PROVIDER: str = "ollama"  # 可选值: "openai", "huggingface", "ollama", "local", "deepseek", "gemini"
    EMBEDDING_MODEL_NAME: str = "nomic-embed-text"  # 默认嵌入模型
    
    # 第三方服务配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OPENAI_BASE_URL: Optional[str] = None
    DEEPSEEK_BASE_URL: Optional[str] = None
    GEMINI_BASE_URL: Optional[str] = None

    # JWT认证配置
    SECRET_KEY: str = "supersecretkey"  # 生产环境应使用安全的密钥并通过环境变量配置
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天

    # 用户数据存储目录
    USERS_DATA_DIR: str = "data/users"

    # 网络搜索配置
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_CSE_ID: Optional[str] = None

    class Config:
        """Pydantic配置"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 允许额外字段，避免验证错误

    def get_llm_params(self) -> Dict[str, Any]:
        """获取LLM模型的参数，基于当前配置"""
        provider = self.LLM_PROVIDER.lower()
        params = {"model": self.LLM_MODEL_NAME}
        
        if provider == "ollama":
            params["base_url"] = self.OLLAMA_BASE_URL
        elif provider == "openai" and self.OPENAI_BASE_URL:
            params["api_base"] = self.OPENAI_BASE_URL
        elif provider == "azure":
            params["api_key"] = self.AZURE_API_KEY
            # 对于Azure，使用engine而不是model
            params["engine"] = params.pop("model")
        elif provider == "deepseek":
            params["api_key"] = self.DEEPSEEK_API_KEY
            if self.DEEPSEEK_BASE_URL:
                params["api_base"] = self.DEEPSEEK_BASE_URL
        elif provider == "gemini":
            params["api_key"] = self.GEMINI_API_KEY
            if self.GEMINI_BASE_URL:
                params["api_base"] = self.GEMINI_BASE_URL
            
        return params
        
    def get_embedding_params(self) -> Dict[str, Any]:
        """获取嵌入模型的参数，基于当前配置"""
        provider = self.EMBEDDING_PROVIDER.lower()
        params = {"model_name": self.EMBEDDING_MODEL_NAME}
        
        if provider == "ollama":
            params["base_url"] = self.OLLAMA_BASE_URL
        elif provider == "openai":
            # OpenAI使用model而不是model_name
            params["model"] = params.pop("model_name")
            if self.OPENAI_BASE_URL:
                params["api_base"] = self.OPENAI_BASE_URL
        elif provider == "deepseek":
            # DeepSeek使用OpenAI兼容接口
            params["model"] = params.pop("model_name")
            params["api_key"] = self.DEEPSEEK_API_KEY
            if self.DEEPSEEK_BASE_URL:
                params["api_base"] = self.DEEPSEEK_BASE_URL
        elif provider == "gemini":
            # Gemini使用自己的接口
            params["model"] = params.pop("model_name")
            params["api_key"] = self.GEMINI_API_KEY
            if self.GEMINI_BASE_URL:
                params["api_base"] = self.GEMINI_BASE_URL
                
        return params

@lru_cache()
def get_settings():
    """获取应用配置单例"""
    settings = Settings()
    logger.info(f"加载配置: LLM提供商={settings.LLM_PROVIDER}, 嵌入模型提供商={settings.EMBEDDING_PROVIDER}")
    return settings

@lru_cache()
def get_embedding_model():
    """获取嵌入模型"""
    settings = get_settings()
    provider = settings.EMBEDDING_PROVIDER.lower()
    params = settings.get_embedding_params()
    
    try:
        logger.info(f"尝试初始化嵌入模型: 提供商={provider}, 模型={settings.EMBEDDING_MODEL_NAME}")
        logger.info(f"嵌入模型参数: {params}")
        
        if provider == "ollama":
            try:
                logger.info("正在加载Ollama嵌入模型...")
                from llama_index.embeddings.ollama import OllamaEmbedding
                return OllamaEmbedding(**params)
            except ImportError as e:
                logger.error(f"Ollama嵌入模型导入失败: {e}")
                logger.info("尝试fallback到本地嵌入模型...")
                from llama_index.core.embeddings import resolve_embed_model
                return resolve_embed_model("local")
            
        elif provider == "openai":
            from llama_index.embeddings.openai import OpenAIEmbedding
            return OpenAIEmbedding(**params)
            
        elif provider == "deepseek":
            # DeepSeek使用OpenAI兼容接口
            from llama_index.embeddings.openai import OpenAIEmbedding
            logger.info("使用DeepSeek嵌入模型")
            return OpenAIEmbedding(**params)
            
        elif provider == "gemini":
            # Gemini嵌入模型
            try:
                logger.info("正在加载Gemini嵌入模型...")
                from llama_index.embeddings.gemini import GeminiEmbedding
                return GeminiEmbedding(**params)
            except ImportError as e:
                logger.error(f"Gemini嵌入模型导入失败: {e}")
                logger.info("尝试fallback到本地嵌入模型...")
                from llama_index.core.embeddings import resolve_embed_model
                return resolve_embed_model("local")
            
        elif provider == "huggingface":
            try:
                logger.info("正在加载HuggingFace嵌入模型...")
                from llama_index.embeddings.huggingface import HuggingFaceEmbedding
                return HuggingFaceEmbedding(**params)
            except ImportError as e:
                logger.error(f"HuggingFace嵌入模型导入失败: {e}")
                logger.info("尝试fallback到本地嵌入模型...")
                from llama_index.core.embeddings import resolve_embed_model
                return resolve_embed_model("local")
            
        elif provider == "local":
            logger.info("使用本地嵌入模型")
            from llama_index.core.embeddings import resolve_embed_model
            return resolve_embed_model("local")
            
        else:
            logger.warning(f"未知的嵌入模型提供商: {provider}，回退到本地模型")
            from llama_index.core.embeddings import resolve_embed_model
            return resolve_embed_model("local")
            
    except Exception as e:
        logger.error(f"加载嵌入模型失败: {str(e)}，回退到本地模型")
        from llama_index.core.embeddings import resolve_embed_model
        return resolve_embed_model("local")

@lru_cache()
def get_llm_model():
    """获取LLM模型"""
    settings = get_settings()
    provider = settings.LLM_PROVIDER.lower()
    params = settings.get_llm_params()
    
    try:
        logger.info(f"初始化LLM模型: 提供商={provider}, 模型={settings.LLM_MODEL_NAME}")
        
        if provider == "ollama":
            from llama_index.llms.ollama import Ollama
            return Ollama(**params)
            
        elif provider == "openai":
            from llama_index.llms.openai import OpenAI
            return OpenAI(**params)
            
        elif provider == "anthropic":
            from llama_index.llms.anthropic import Anthropic
            return Anthropic(**params)
            
        elif provider == "azure":
            from llama_index.llms.azure_openai import AzureOpenAI
            return AzureOpenAI(**params)
            
        elif provider == "deepseek":
            # 处理DeepSeek API，使用OpenAI兼容接口
            from llama_index.llms.openai import OpenAI
            logger.info("使用DeepSeek LLM")
            return OpenAI(**params)
            
        elif provider == "gemini":
            # 处理Gemini API
            from llama_index.llms.gemini import Gemini
            logger.info("使用Gemini LLM")
            return Gemini(**params)
            
        elif provider == "local":
            from llama_index.llms import LlamaCPP
            return LlamaCPP(model_path=settings.LLM_MODEL_NAME)
            
        else:
            logger.warning(f"未知的LLM提供程序: {provider}，回退到Ollama")
            from llama_index.llms.ollama import Ollama
            return Ollama(model="llama2")
            
    except Exception as e:
        logger.error(f"加载LLM模型失败: {str(e)}")
        raise ValueError(f"无法加载LLM模型: {str(e)}")

@lru_cache()
def get_provider():
    """获取LLM提供商"""
    settings = get_settings()
    
    # 根据LLM_PROVIDER确定要使用的提供商
    provider_type = settings.LLM_PROVIDER.lower()
    
    if provider_type == "openai":
        from ..lib.providers.openai import OpenAIProvider
        api_key = settings.OPENAI_API_KEY
        base_url = settings.OPENAI_BASE_URL
        return OpenAIProvider(api_key=api_key, base_url=base_url)
    elif provider_type == "deepseek":
        from ..lib.providers.deepseek import DeepSeekProvider
        api_key = settings.DEEPSEEK_API_KEY
        base_url = settings.DEEPSEEK_BASE_URL
        return DeepSeekProvider(api_key=api_key, base_url=base_url)
    elif provider_type == "gemini":
        from ..lib.providers.gemini import GeminiProvider
        api_key = settings.GEMINI_API_KEY
        base_url = settings.GEMINI_BASE_URL
        return GeminiProvider(api_key=api_key, base_url=base_url)
    elif provider_type == "azure":
        from ..lib.providers.azure import AzureOpenAIProvider
        api_key = settings.AZURE_API_KEY
        base_url = getattr(settings, 'AZURE_BASE_URL', None)
        return AzureOpenAIProvider(api_key=api_key, base_url=base_url)
    elif provider_type == "ollama":
        from ..lib.providers.ollama import OllamaProvider
        return OllamaProvider(
            api_key="ollama-local", 
            base_url=settings.OLLAMA_BASE_URL
        )
    elif provider_type == "local":
        # 对于本地模型，仍然使用Ollama包装器
        from ..lib.providers.ollama import OllamaProvider
        return OllamaProvider(
            api_key="ollama-local", 
            base_url=settings.OLLAMA_BASE_URL
        )
    else:
        raise ValueError(f"不支持的LLM提供商类型: {provider_type}") 