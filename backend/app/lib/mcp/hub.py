"""MCP集线器，作为MCP模块的主要入口点。

这个模块提供了一个统一的接口来管理与多个MCP服务器的连接、
发现并使用它们的工具、提示和资源。
"""

import asyncio
from typing import Any, Dict, List, Optional, Union

from mcp.types import CallToolResult, GetPromptResult, ReadResourceResult

from .config import ConfigProvider
from .connection import ConnectionManager
from .managers import PromptManager, ResourceManager, ToolManager
from .session import SessionManager
from .utils.cache import Cache
from .utils.logger import Logger


class MCPHub:
    """
    MCP集线器 - 与MCP服务器交互的统一接口
    
    这个类是MCP模块的主要入口点，提供了一个统一的接口来管理
    与多个MCP服务器的连接、发现并使用它们的工具、提示和资源。
    """
    
    def __init__(
        self, 
        config_path: Optional[str] = None, 
        config_dict: Optional[Dict[str, Any]] = None,
        logger: Optional[Logger] = None,
        enable_cache: bool = True
    ):
        """
        初始化MCP集线器
        
        Args:
            config_path: JSON配置文件路径
            config_dict: 直接提供的配置字典
            logger: 自定义日志记录器
            enable_cache: 是否启用缓存
        """
        self.logger = logger or Logger("mcp_hub")
        
        # 初始化配置提供器
        self.config_provider = ConfigProvider(config_path, config_dict)
        
        # 初始化缓存
        self.cache = Cache() if enable_cache else None
        
        # 初始化连接和会话管理器
        self.connection_manager = ConnectionManager(self.config_provider, self.logger)
        self.session_manager = SessionManager(self.config_provider, self.connection_manager, self.logger)
        
        # 初始化功能管理器
        self.tool_manager = ToolManager(self.session_manager, self.cache, self.logger)
        self.prompt_manager = PromptManager(self.session_manager, self.cache, self.logger)
        self.resource_manager = ResourceManager(self.session_manager, self.cache, self.logger)
        
        self._initialized = False
    
    async def __aenter__(self):
        # 进入异步上下文时自动初始化
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()
    
    async def initialize(self, server_names: Optional[List[str]] = None, user_id: Optional[str] = None) -> 'MCPHub':
        """
        初始化MCP集线器及其所有组件
        
        Args:
            server_names: 要连接的服务器名称列表，默认为所有配置的服务器
            user_id: 用户ID，用于过滤只属于该用户的服务器
        
        Returns:
            MCPHub实例，便于链式调用
        """
        if self._initialized:
            return self
            
        if server_names is None:
            # 获取用户特定的服务器名称
            if user_id:
                server_names = self.config_provider.get_user_server_names(user_id)
            else:
                server_names = self.config_provider.get_all_server_names()
            
        if not server_names:
            self.logger.warning(f"未找到任何服务器配置 (用户: {user_id or '全局'})")
            return self
            
        self.logger.info(f"初始化MCP集线器，连接到服务器: {', '.join(server_names)} (用户: {user_id or '全局'})")
        
        # 并行发现功能
        discovery_tasks = [
            self.tool_manager.discover_tools(server_names),
            self.prompt_manager.discover_prompts(server_names),
            self.resource_manager.discover_resources(server_names)
        ]
        
        await asyncio.gather(*discovery_tasks, return_exceptions=True)
        
        self._initialized = True
        self.logger.info("MCP集线器初始化完成")
        
        return self
    
    async def shutdown(self) -> None:
        """关闭所有连接和资源"""
        self.logger.info("关闭MCP集线器")
        await self.session_manager.close_all()
        self._initialized = False
    
    # 工具相关方法
    async def list_tools(self):
        """
        列出所有可用工具
        
        Returns:
            包含所有可用工具的ListToolsResult对象
        """
        return await self.tool_manager.list_tools()
    
    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> CallToolResult:
        """
        调用指定的工具
        
        Args:
            tool_name: 工具名称，可以是命名空间形式(server/tool)或简单名称
            arguments: 工具参数
            
        Returns:
            工具调用结果
        """
        return await self.tool_manager.call_tool(tool_name, arguments)
    
    # 提示相关方法
    async def list_prompts(self, server_name: Optional[str] = None):
        """
        列出可用的提示模板
        
        Args:
            server_name: 可选的服务器名称过滤器
            
        Returns:
            服务器名称到提示列表的映射
        """
        return await self.prompt_manager.list_prompts(server_name)
    
    async def get_prompt(
        self, 
        prompt_name: str, 
        arguments: Optional[Dict[str, str]] = None
    ) -> GetPromptResult:
        """
        获取并应用提示模板
        
        Args:
            prompt_name: 提示名称，可以是命名空间形式(server/prompt)或简单名称
            arguments: 提示参数
            
        Returns:
            应用参数后的提示结果
        """
        return await self.prompt_manager.get_prompt(prompt_name, arguments)
    
    # 资源相关方法
    async def list_resources(self, server_name: Optional[str] = None):
        """
        列出可用资源
        
        Args:
            server_name: 可选的服务器名称过滤器
            
        Returns:
            服务器名称到资源URI列表的映射
        """
        return await self.resource_manager.list_resources(server_name)
    
    async def get_resource(self, resource_uri: str) -> ReadResourceResult:
        """
        获取资源内容
        
        Args:
            resource_uri: 资源URI，可以是命名空间形式(server/uri)或完整URI
            
        Returns:
            资源内容
        """
        return await self.resource_manager.get_resource(resource_uri)

    async def reload_servers(self, server_names: Optional[List[str]] = None, user_id: Optional[str] = None) -> None:
        """
        增量重新加载服务器配置和功能发现（用于增删改 server 后热更新）
        Args:
            server_names: 指定要刷新的服务器名列表，默认全部
            user_id: 用户ID，用于只重载该用户的服务器
        """
        self.logger.info(f"增量重新加载MCP服务器配置 (用户: {user_id or '全局'})")
        
        # 重新加载配置
        self.config_provider.reload()
        
        # 获取当前应该存在的服务器列表
        if server_names is None:
            if user_id:
                current_server_names = self.config_provider.get_user_server_names(user_id)
            else:
                current_server_names = self.config_provider.get_all_server_names()
        else:
            current_server_names = server_names
        
        # 获取当前已连接的服务器列表
        existing_server_names = list(self.session_manager.sessions.keys())
        
        # 计算需要添加、移除和更新的服务器
        servers_to_add = set(current_server_names) - set(existing_server_names)
        servers_to_remove = set(existing_server_names) - set(current_server_names)
        servers_to_update = set(current_server_names) & set(existing_server_names)
        
        self.logger.info(f"增量更新: 添加{len(servers_to_add)}个, 移除{len(servers_to_remove)}个, 更新{len(servers_to_update)}个服务器")
        
        # 移除不再需要的服务器
        for server_name in servers_to_remove:
            await self._remove_server(server_name)
        
        # 添加新服务器
        for server_name in servers_to_add:
            await self._add_server(server_name)
        
        # 更新现有服务器（重新发现工具）
        for server_name in servers_to_update:
            await self._update_server(server_name)
        
        self.logger.info("增量重新加载完成")
    
    async def _remove_server(self, server_name: str) -> None:
        """移除单个服务器及其工具"""
        self.logger.info(f"移除服务器: {server_name}")
        
        # 关闭会话
        await self.session_manager.close_session(server_name)
        
        # 从工具管理器中移除该服务器的工具
        if hasattr(self.tool_manager, 'tools_by_server') and server_name in self.tool_manager.tools_by_server:
            # 移除该服务器的所有工具
            server_tools = self.tool_manager.tools_by_server[server_name]
            for tool in server_tools:
                # 构建命名空间工具名
                namespaced_name = f"{server_name}/{tool.name}"
                if namespaced_name in self.tool_manager.tools_by_name:
                    del self.tool_manager.tools_by_name[namespaced_name]
            
            # 移除服务器工具缓存
            del self.tool_manager.tools_by_server[server_name]
        
        # 同样处理提示和资源管理器
        if hasattr(self.prompt_manager, 'prompts_by_server') and server_name in self.prompt_manager.prompts_by_server:
            del self.prompt_manager.prompts_by_server[server_name]
        
        if hasattr(self.resource_manager, 'resources_by_server') and server_name in self.resource_manager.resources_by_server:
            del self.resource_manager.resources_by_server[server_name]
    
    async def _add_server(self, server_name: str) -> None:
        """添加单个服务器并发现其工具"""
        self.logger.info(f"添加服务器: {server_name}")
        
        try:
            # 发现该服务器的工具、提示和资源
            await asyncio.gather(
                self.tool_manager.discover_tools([server_name]),
                self.prompt_manager.discover_prompts([server_name]),
                self.resource_manager.discover_resources([server_name]),
                return_exceptions=True
            )
        except Exception as e:
            self.logger.error(f"添加服务器 {server_name} 失败: {e}")
    
    async def _update_server(self, server_name: str) -> None:
        """更新单个服务器（重新发现工具）"""
        self.logger.info(f"更新服务器: {server_name}")
        
        try:
            # 先移除现有的工具缓存
            if hasattr(self.tool_manager, 'tools_by_server') and server_name in self.tool_manager.tools_by_server:
                # 移除该服务器的所有工具
                server_tools = self.tool_manager.tools_by_server[server_name]
                for tool in server_tools:
                    namespaced_name = f"{server_name}/{tool.name}"
                    if namespaced_name in self.tool_manager.tools_by_name:
                        del self.tool_manager.tools_by_name[namespaced_name]
            
            # 重新发现工具
            await asyncio.gather(
                self.tool_manager.discover_tools([server_name]),
                self.prompt_manager.discover_prompts([server_name]),
                self.resource_manager.discover_resources([server_name]),
                return_exceptions=True
            )
        except Exception as e:
            self.logger.error(f"更新服务器 {server_name} 失败: {e}")

    async def get_server_status(self, server_name: str) -> Dict[str, Any]:
        """
        获取单个服务器的健康/激活/连接状态
        Returns: {"name":..., "active":..., "connected":..., "healthy":...}
        """
        config = self.config_provider.get_server_config(server_name)
        if not config:
            return {"name": server_name, "active": False, "connected": False, "healthy": False}
        active = config.get("active", True)
        # 连接状态
        connected = self.connection_manager.is_connected(server_name)
        # 健康检查（可扩展为实际ping）
        healthy = connected # 简化：已连接即健康
        return {"name": server_name, "active": active, "connected": connected, "healthy": healthy}

    async def list_server_statuses(self, server_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        获取服务器的健康/激活/连接状态
        
        Args:
            server_names: 要查询状态的服务器名称列表，如果为None则查询所有服务器
            
        Returns:
            List[{"name":..., "active":..., "connected":..., "healthy":...}]
        """
        # 如果没有指定服务器名称，则获取所有配置的服务器
        if server_names is None:
            server_names = self.config_provider.get_all_server_names()
            
        return [await self.get_server_status(name) for name in server_names] 