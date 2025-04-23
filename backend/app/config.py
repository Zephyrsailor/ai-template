import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv
from typing import Optional

from .providers.openai import OpenAIProvider

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    # Provider configuration
    PROVIDER_TYPE: str = os.getenv("PROVIDER_TYPE", "openai")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL", None)
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    
    # Model defaults
    DEFAULT_MODEL: str = "gpt-4o-mini"  # Default model, can be overridden
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    """Cached settings to avoid reloading .env file for each request"""
    return Settings()


@lru_cache()
def get_provider():
    """Create and cache the LLM provider"""
    settings = get_settings()
    
    if settings.PROVIDER_TYPE == "openai":
        api_key = settings.OPENAI_API_KEY
        base_url = settings.OPENAI_BASE_URL
        settings.DEFAULT_MODEL = "gpt-4o-mini"
    elif settings.PROVIDER_TYPE == "deepseek":
        api_key = settings.DEEPSEEK_API_KEY
        base_url = settings.DEEPSEEK_BASE_URL
        settings.DEFAULT_MODEL = "deepseek-reasoner"
    else:
        raise ValueError(f"Unsupported PROVIDER_TYPE: {settings.PROVIDER_TYPE}")

    if not api_key:
        raise ValueError(f"API Key not found for provider: {settings.PROVIDER_TYPE}")
        
    # Currently only OpenAI provider is implemented
    # In a real app, you would instantiate different provider classes based on settings.PROVIDER_TYPE
    return OpenAIProvider(api_key=api_key, base_url=base_url) 