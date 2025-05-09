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
    
    async def initialize(self, server_names: Optional[List[str]] = None) -> 'MCPHub':
        """
        初始化MCP集线器及其所有组件
        
        Args:
            server_names: 要连接的服务器名称列表，默认为所有配置的服务器
        
        Returns:
            MCPHub实例，便于链式调用
        """
        if self._initialized:
            return self
            
        if server_names is None:
            server_names = self.config_provider.get_all_server_names()
            
        if not server_names:
            self.logger.warning("未找到任何服务器配置")
            return self
            
        self.logger.info(f"初始化MCP集线器，连接到服务器: {', '.join(server_names)}")
        
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