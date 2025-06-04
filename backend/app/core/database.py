"""
数据库连接模块 - 使用 SQLAlchemy ORM
"""
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Generic, Type, AsyncGenerator
import uuid
from datetime import datetime
from .logging import get_logger
from enum import Enum

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, String, DateTime, func, select, update, delete, text
from sqlalchemy.dialects.postgresql import UUID

from .config import get_settings

logger = get_logger(__name__)

# 类型变量
T = TypeVar('T')

# SQLAlchemy Base
Base = declarative_base()

class BaseModel(Base):
    """数据库模型基类"""
    __abstract__ = True
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class DatabaseManager:
    """数据库管理器 - 使用 SQLAlchemy"""
    
    def __init__(self):
        self.settings = get_settings()
        database_url = self.settings.get_database_url()
        logger.info(f"使用数据库: {self.settings.DATABASE_TYPE} - {database_url.split('@')[0]}@***")
        
        # 构建连接参数
        connect_args = {}
        if self.settings.DATABASE_TYPE.lower() == "mysql":
            # 🔥 MySQL特定配置 - 解决连接丢失问题
            connect_args = {
                "charset": "utf8mb4",
                "autocommit": False,
                "connect_timeout": 30,  # 连接超时30秒
                # 🔥 关键：设置MySQL会话参数，防止连接超时
                "init_command": (
                    "SET SESSION wait_timeout = 3600, "  # 1小时超时
                    "interactive_timeout = 3600, "       # 1小时交互超时
                    f"innodb_lock_wait_timeout = {self.settings.DB_LOCK_TIMEOUT}, "
                    "sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'"
                )
            }
        
        # 🔥 改进连接池配置 - 防止连接丢失
        self.engine = create_async_engine(
            database_url,
            echo=self.settings.DATABASE_ECHO,
            pool_size=max(5, self.settings.DB_POOL_SIZE),  # 最少5个连接
            max_overflow=max(10, self.settings.DB_MAX_OVERFLOW),  # 最少10个溢出连接
            pool_timeout=30,  # 30秒获取连接超时
            pool_pre_ping=True,  # 🔥 连接前检查连接是否有效
            pool_recycle=1800,   # 🔥 30分钟回收连接，防止长时间连接超时
            connect_args=connect_args,
            # 🔥 添加连接重试机制
            execution_options={
                "isolation_level": "READ_COMMITTED",
                "autocommit": False
            }
        )
        self.async_session = async_sessionmaker(
            self.engine, 
            class_=AsyncSession, 
            expire_on_commit=False,
            autoflush=True,  # 自动刷新
            autocommit=False,  # 手动控制事务
        )
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话 - 带重试机制"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                async with self.async_session() as session:
                    try:
                        # 🔥 添加连接健康检查
                        await session.execute(text("SELECT 1"))
                        yield session
                        # 在正常情况下提交事务
                        await session.commit()
                        return  # 成功，退出重试循环
                    except Exception as e:
                        await session.rollback()
                        raise
                    finally:
                        # 确保会话被正确关闭
                        await session.close()
                        
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                
                # 🔥 检查是否是连接相关错误
                if any(keyword in error_msg.lower() for keyword in [
                    'lost connection', 'connection', 'timeout', 'broken pipe', 
                    'server has gone away', 'connection reset'
                ]):
                    if retry_count < max_retries:
                        logger.warning(f"数据库连接错误，第{retry_count}次重试: {error_msg}")
                        # 🔥 重新创建引擎，清理连接池
                        await self._recreate_engine()
                        continue
                    else:
                        logger.error(f"数据库连接失败，已重试{max_retries}次: {error_msg}")
                        raise
                else:
                    # 非连接错误，直接抛出
                    raise
    
    async def _recreate_engine(self):
        """重新创建数据库引擎 - 用于连接恢复"""
        try:
            # 关闭现有引擎
            await self.engine.dispose()
            logger.info("重新创建数据库引擎...")
            
            # 重新初始化
            self.__init__()
            logger.info("数据库引擎重新创建成功")
        except Exception as e:
            logger.error(f"重新创建数据库引擎失败: {e}")
            raise
    
    async def create_tables(self):
        """创建数据库表"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_tables(self):
        """删除所有表（仅用于测试）"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

# 全局数据库管理器实例
db_manager = DatabaseManager()

# 全局get_session函数，用于FastAPI依赖注入
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（全局函数）"""
    async for session in db_manager.get_session():
        yield session

# 为了向后兼容，保留原有的Database类接口
class Database:
    """向后兼容的数据库接口"""
    
    def __init__(self):
        self.settings = get_settings()
        self.manager = db_manager
        
    async def create_tables(self):
        """创建数据库表"""
        await self.manager.create_tables()
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话"""
        async for session in self.manager.get_session():
            yield session

class Repository(Generic[T]):
    """通用仓库基类 - 使用 SQLAlchemy"""
    
    def __init__(self, model_class: Type[T], session: AsyncSession):
        self.model_class = model_class
        self.session = session
    
    async def create(self, **kwargs) -> T:
        """创建实体"""
        if 'id' not in kwargs or not kwargs['id']:
            kwargs['id'] = str(uuid.uuid4())
            
        if 'created_at' not in kwargs:
            kwargs['created_at'] = datetime.now()
            
        # 处理复杂类型
        for key, value in kwargs.items():
            if isinstance(value, (dict, list)):
                kwargs[key] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, Enum):
                kwargs[key] = value.value
                
        instance = self.model_class(**kwargs)
        self.session.add(instance)
        await self.session.flush()  # 使用flush而不是commit
        await self.session.refresh(instance)
        return instance
    
    async def update(self, entity_id: str, **kwargs) -> Optional[T]:
        """更新实体"""
        kwargs['updated_at'] = datetime.now()
        
        # 处理复杂类型
        for key, value in kwargs.items():
            if isinstance(value, (dict, list)):
                kwargs[key] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, Enum):
                kwargs[key] = value.value
                
        stmt = update(self.model_class).where(
            self.model_class.id == entity_id
        ).values(**kwargs)
        
        await self.session.execute(stmt)
        await self.session.flush()  # 使用flush而不是commit
        
        return await self.get_by_id(entity_id)
    
    async def delete(self, entity_id: str) -> bool:
        """删除实体"""
        stmt = delete(self.model_class).where(self.model_class.id == entity_id)
        result = await self.session.execute(stmt)
        await self.session.flush()  # 使用flush而不是commit
        return result.rowcount > 0
    
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """通过ID获取实体"""
        stmt = select(self.model_class).where(self.model_class.id == entity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[T]:
        """获取所有实体"""
        stmt = select(self.model_class)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def find_by(self, **kwargs) -> List[T]:
        """根据条件查找实体"""
        stmt = select(self.model_class)
        for key, value in kwargs.items():
            if hasattr(self.model_class, key):
                stmt = stmt.where(getattr(self.model_class, key) == value)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def find_one_by(self, **kwargs) -> Optional[T]:
        """根据条件查找单个实体"""
        results = await self.find_by(**kwargs)
        return results[0] if results else None 