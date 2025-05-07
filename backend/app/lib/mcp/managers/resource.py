"""MCP资源管理器，负责资源的发现和获取。"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from anyio import Lock
from mcp.types import ReadResourceResult

from ..models.namespaced import NamespacedResource
from ..session import SessionManager
from ..utils.cache import Cache
from ..utils.logger import Logger
from .base import BaseManager


class ResourceManager(BaseManager):
    """
    管理MCP资源的发现和获取。
    
    负责:
    - 从服务器发现资源
    - 获取资源内容
    - 维护资源索引
    """
    
    def __init__(
        self, 
        session_manager: SessionManager,
        cache: Optional[Cache] = None,
        logger: Optional[Logger] = None
    ):
        """
        初始化资源管理器。
        
        Args:
            session_manager: 会话管理器
            cache: 缓存
            logger: 日志记录器
        """
        super().__init__(session_manager, cache, logger, "resource_manager")
        
        # 资源索引
        self.resources_by_server: Dict[str, List[str]] = {}
        self.resources_by_uri: Dict[str, NamespacedResource] = {}
        self.discovery_lock = Lock()
    
    async def discover_resources(self, server_names: Optional[List[str]] = None) -> None:
        """
        从指定服务器发现资源。
        
        Args:
            server_names: 要发现资源的服务器名称列表，如果为None则使用所有已知服务器
        """
        if server_names is None:
            # 获取具有资源能力的服务器
            server_names = self.get_server_names_with_capability("resources")
            
        if not server_names:
            self.logger.warning("没有具有资源能力的服务器")
            return
            
        async with self.discovery_lock:
            # 并行发现所有服务器的资源
            discover_tasks = [self._discover_server_resources(name) for name in server_names]
            server_resources = await asyncio.gather(*discover_tasks, return_exceptions=True)
            
            # 处理结果
            for i, result in enumerate(server_resources):
                server_name = server_names[i]
                
                if isinstance(result, Exception):
                    self.logger.error(f"从服务器'{server_name}'发现资源失败: {result}")
                    continue
                    
                resources = result
                if not resources:
                    self.logger.info(f"服务器'{server_name}'没有可用的资源")
                    continue
                    
                # 更新索引
                self.resources_by_server[server_name] = resources
                
                # 添加到命名空间索引
                for resource_uri in resources:
                    namespaced_resource = NamespacedResource(server_name=server_name, uri=resource_uri)
                    self.resources_by_uri[namespaced_resource.namespaced_uri] = namespaced_resource
                    
                self.logger.info(f"从服务器'{server_name}'发现了{len(resources)}个资源")
                
            self.initialized = True
            
            # 更新缓存
            if self.cache:
                await self.cache.set("resources_by_server", self.resources_by_server)
                await self.cache.set("resources_by_uri", {k: v.to_dict() for k, v in self.resources_by_uri.items()})
    
    async def _discover_server_resources(self, server_name: str) -> List[str]:
        """从单个服务器发现资源。"""
        # 首先检查缓存
        if self.cache:
            cached_resources = await self.cache.get(f"server_resources_{server_name}")
            if cached_resources:
                self.logger.debug(f"使用缓存的资源列表: 服务器'{server_name}'")
                return cached_resources
                
        # 检查服务器是否支持资源
        capabilities = self.get_capabilities(server_name)
        if not capabilities or not capabilities.resources:
            self.logger.debug(f"服务器'{server_name}'不支持资源")
            return []
                
        # 从服务器获取资源
        try:
            # 使用会话管理器执行操作
            result = await self.execute_with_retry(
                server_name=server_name,
                operation="list_resources",
                method_name="list_resources"
            )
            
            resources = []
            # 处理不同的响应格式
            if hasattr(result, "resources") and isinstance(result.resources, list):
                resources = result.resources
            elif hasattr(result, "resources") and isinstance(result.resources, dict):
                # 有些服务器返回 {type: [uri, ...]} 格式
                for resource_list in result.resources.values():
                    resources.extend(resource_list)
            
            # 更新缓存
            if self.cache:
                await self.cache.set(f"server_resources_{server_name}", resources)
                
            return resources
            
        except Exception as e:
            self.logger.error(f"从服务器'{server_name}'列出资源失败: {e}")
            raise
    
    async def list_resources(self, server_name: Optional[str] = None) -> Dict[str, List[str]]:
        """
        列出可用的资源。
        
        Args:
            server_name: 可选的服务器名称过滤器
            
        Returns:
            服务器名称到资源URI列表的映射
        """
        # 确保资源已发现
        if not self.initialized:
            await self.discover_resources()
            
        result = {}
        
        if server_name:
            # 返回特定服务器的资源
            if server_name in self.resources_by_server:
                result[server_name] = self.resources_by_server[server_name]
        else:
            # 返回所有服务器的资源
            result = self.resources_by_server
            
        return result
    
    async def get_resource(self, resource_uri: str) -> ReadResourceResult:
        """
        获取资源内容。
        
        Args:
            resource_uri: 资源URI，可以是命名空间形式(server/uri)或完整URI
            
        Returns:
            资源内容
        """
        # 确保资源已发现
        if not self.initialized:
            await self.discover_resources()
            
        # 解析资源URI
        server_name, local_uri = await self._parse_resource_uri(resource_uri)
        
        if not server_name or not local_uri:
            error = f"资源'{resource_uri}'不存在或格式无效"
            self.logger.error(error)
            return ReadResourceResult(
                content=None,
                metadata={"error": error}
            )
            
        self.logger.info(f"获取资源: {local_uri} (服务器: {server_name})")
        
        try:
            # 使用会话管理器执行操作
            result = await self.execute_with_retry(
                server_name=server_name,
                operation=f"read_resource",
                method_name="read_resource",
                method_args={"uri": local_uri}
            )
            
            return result
            
        except Exception as e:
            error = f"获取资源'{resource_uri}'失败: {e}"
            self.logger.error(error)
            return ReadResourceResult(
                content=None,
                metadata={"error": error}
            )
    
    async def _parse_resource_uri(self, resource_uri: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析资源URI，支持命名空间形式和完整URI。
        
        Args:
            resource_uri: 资源URI，格式为'server/uri'、'uri'或完整URI
            
        Returns:
            (server_name, local_uri)元组
        """
        # 如果是完整URI（包含协议），直接处理
        if "://" in resource_uri:
            # 查找匹配的资源
            for uri, resource in self.resources_by_uri.items():
                if uri == resource_uri or resource.uri == resource_uri:
                    return resource.server_name, resource.uri
            return None, None
        
        # 首先检查完全命名空间的资源
        if resource_uri in self.resources_by_uri:
            namespaced_resource = self.resources_by_uri[resource_uri]
            return namespaced_resource.server_name, namespaced_resource.uri
            
        # 检查是否是命名空间形式
        server_name, local_uri = await self._parse_namespaced_identifier(resource_uri)
        if server_name:
            # 验证服务器存在
            if server_name not in self.resources_by_server:
                return None, None
                
            # 验证资源在该服务器上存在
            resources = self.resources_by_server.get(server_name, [])
            if local_uri in resources:
                return server_name, local_uri
                    
        # 如果是简单URI，查找第一个匹配的资源
        elif local_uri:
            for server_name, resources in self.resources_by_server.items():
                if local_uri in resources:
                    return server_name, local_uri
                        
        return None, None 