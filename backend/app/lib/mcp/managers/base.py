"""MCP管理器基类，提供所有管理器的共享功能"""

import asyncio
from typing import Any, Dict, List, Optional, TypeVar

from ..session import SessionManager
from ..utils.cache import Cache
from ..utils.logger import Logger

# 泛型类型变量
T = TypeVar('T')


class BaseManager:
    """
    MCP管理器基类，提供所有管理器共享的基本功能。
    
    这个类定义了初始化、缓存和日志记录等通用功能。
    """
    
    def __init__(
        self,
        session_manager: SessionManager,
        cache: Optional[Cache] = None,
        logger: Optional[Logger] = None,
        name: str = "base_manager"
    ):
        """
        初始化基础管理器。
        
        Args:
            session_manager: 会话管理器
            cache: 缓存对象
            logger: 日志记录器
            name: 管理器名称
        """
        self.session_manager = session_manager
        self.cache = cache
        self.logger = logger or Logger(name)
        self.name = name
        self.initialized = False
        
    async def get_session(self, server_name: str):
        """
        获取指定服务器的会话。
        
        Args:
            server_name: 服务器名称
            
        Returns:
            服务器会话
        """
        return await self.session_manager.get_session(server_name)
        
    async def execute_with_retry(
        self,
        server_name: str,
        operation: str,
        method_name: str,
        method_args: Optional[Dict[str, Any]] = None,
        max_retries: int = 1
    ) -> Any:
        """
        使用重试机制执行操作。
        
        Args:
            server_name: 服务器名称
            operation: 操作名称（用于日志）
            method_name: 要调用的方法名
            method_args: 方法参数
            max_retries: 最大重试次数
            
        Returns:
            操作结果
        """
        return await self.session_manager.execute_with_retry(
            server_name, operation, method_name, method_args, max_retries
        )
        
    def get_capabilities(self, server_name: str) -> Any:
        """
        获取服务器的能力。
        
        Args:
            server_name: 服务器名称
            
        Returns:
            服务器能力对象
        """
        return self.session_manager.get_capabilities(server_name)
        
    def get_server_names_with_capability(self, capability_name: str) -> List[str]:
        """
        获取具有指定能力的所有服务器名称。
        
        Args:
            capability_name: 能力名称
            
        Returns:
            服务器名称列表
        """
        return self.session_manager.get_server_names_with_capability(capability_name)
        
    async def _parse_namespaced_identifier(self, identifier: str, sep: str = "/") -> tuple[Optional[str], Optional[str]]:
        """
        解析带命名空间的标识符。
        
        Args:
            identifier: 标识符，格式为'server/name'或'name'
            sep: 分隔符
            
        Returns:
            元组(server_name, local_name)
        """
        # 检查是否是命名空间形式
        if sep in identifier:
            server_name, local_name = identifier.split(sep, 1)
            return server_name, local_name
        
        # 简单名称，将返回(None, identifier)
        return None, identifier 