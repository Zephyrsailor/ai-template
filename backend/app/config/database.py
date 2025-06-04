"""
数据库配置
"""
from typing import Optional
from pydantic import BaseModel, Field

class DatabaseConfig(BaseModel):
    """数据库配置"""
    
    # SQLite配置
    sqlite_url: str = Field(default="sqlite+aiosqlite:///./data/app.db", description="SQLite数据库URL")
    
    # PostgreSQL配置（可选）
    postgres_host: Optional[str] = Field(default=None, description="PostgreSQL主机")
    postgres_port: int = Field(default=5432, description="PostgreSQL端口")
    postgres_user: Optional[str] = Field(default=None, description="PostgreSQL用户名")
    postgres_password: Optional[str] = Field(default=None, description="PostgreSQL密码")
    postgres_database: Optional[str] = Field(default=None, description="PostgreSQL数据库名")
    
    # 连接池配置
    pool_size: int = Field(default=10, description="连接池大小")
    max_overflow: int = Field(default=20, description="最大溢出连接数")
    pool_timeout: int = Field(default=30, description="连接池超时时间")
    pool_recycle: int = Field(default=3600, description="连接回收时间")
    
    # 其他配置
    echo: bool = Field(default=False, description="是否打印SQL语句")
    echo_pool: bool = Field(default=False, description="是否打印连接池信息")
    
    @property
    def database_url(self) -> str:
        """获取数据库URL"""
        if all([self.postgres_host, self.postgres_user, self.postgres_password, self.postgres_database]):
            return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        return self.sqlite_url
    
    class Config:
        """Pydantic配置"""
        env_prefix = "DB_" 