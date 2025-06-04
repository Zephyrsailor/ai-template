"""
安全配置
"""
from typing import List
from pydantic import BaseModel, Field

class SecurityConfig(BaseModel):
    """安全配置"""
    
    # JWT配置
    jwt_secret_key: str = Field(default="your-secret-key-change-in-production", description="JWT密钥")
    jwt_algorithm: str = Field(default="HS256", description="JWT算法")
    jwt_access_token_expire_minutes: int = Field(default=30, description="访问令牌过期时间（分钟）")
    jwt_refresh_token_expire_days: int = Field(default=7, description="刷新令牌过期时间（天）")
    
    # API Key配置
    api_key_header: str = Field(default="X-API-Key", description="API Key请求头")
    api_key_length: int = Field(default=32, description="API Key长度")
    
    # CORS配置
    cors_origins: List[str] = Field(default=["*"], description="允许的CORS源")
    cors_methods: List[str] = Field(default=["*"], description="允许的CORS方法")
    cors_headers: List[str] = Field(default=["*"], description="允许的CORS头")
    cors_credentials: bool = Field(default=True, description="是否允许CORS凭证")
    
    # 密码配置
    password_min_length: int = Field(default=8, description="密码最小长度")
    password_require_uppercase: bool = Field(default=True, description="密码是否需要大写字母")
    password_require_lowercase: bool = Field(default=True, description="密码是否需要小写字母")
    password_require_numbers: bool = Field(default=True, description="密码是否需要数字")
    password_require_special: bool = Field(default=True, description="密码是否需要特殊字符")
    
    # 速率限制配置
    rate_limit_enabled: bool = Field(default=True, description="是否启用速率限制")
    rate_limit_requests: int = Field(default=100, description="速率限制请求数")
    rate_limit_window: int = Field(default=60, description="速率限制时间窗口（秒）")
    
    # 会话配置
    session_timeout: int = Field(default=3600, description="会话超时时间（秒）")
    max_login_attempts: int = Field(default=5, description="最大登录尝试次数")
    lockout_duration: int = Field(default=300, description="锁定持续时间（秒）")
    
    class Config:
        """Pydantic配置"""
        env_prefix = "SECURITY_" 