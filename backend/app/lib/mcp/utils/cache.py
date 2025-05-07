"""MCP模块的简单内存缓存实现"""

import time
from typing import Any, Dict, Optional, TypeVar, cast

# 泛型类型变量
T = TypeVar('T')


class CacheEntry:
    """
    表示缓存中的单个条目，包含值和过期时间。
    """
    
    def __init__(self, value: Any, ttl: Optional[float] = None):
        """
        初始化缓存条目
        
        Args:
            value: 缓存的值
            ttl: 生存时间（秒），None表示永不过期
        """
        self.value = value
        self.expiry = time.time() + ttl if ttl is not None else None
        
    def is_expired(self) -> bool:
        """
        检查缓存条目是否已过期
        
        Returns:
            如果已过期则为True，否则为False
        """
        if self.expiry is None:
            return False
        return time.time() > self.expiry


class Cache:
    """
    简单的内存缓存实现，支持过期时间。
    """
    
    def __init__(self, default_ttl: Optional[float] = 3600.0):
        """
        初始化缓存
        
        Args:
            default_ttl: 默认生存时间（秒），None表示永不过期
        """
        self._cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        
    async def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存项
        
        Args:
            key: 缓存键
            default: 如果键不存在或已过期，返回的默认值
            
        Returns:
            缓存值或默认值
        """
        entry = self._cache.get(key)
        
        if entry is None or entry.is_expired():
            # 如果已过期，删除条目
            if entry is not None:
                del self._cache[key]
            return default
            
        return entry.value
        
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        设置缓存项
        
        Args:
            key: 缓存键
            value: 要缓存的值
            ttl: 生存时间（秒），None使用默认值
        """
        if ttl is None:
            ttl = self.default_ttl
            
        self._cache[key] = CacheEntry(value, ttl)
        
    async def delete(self, key: str) -> bool:
        """
        删除缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            如果键存在且被删除则为True，否则为False
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
        
    async def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        
    async def get_typed(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        获取类型化的缓存项
        
        Args:
            key: 缓存键
            default: 默认值
            
        Returns:
            类型化的缓存值
        """
        value = await self.get(key, default)
        return cast(Optional[T], value) 