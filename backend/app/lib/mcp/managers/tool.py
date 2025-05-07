"""MCP工具管理器，负责工具发现和执行。"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union

from anyio import Lock
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool

from ..models.namespaced import NamespacedTool
from ..session import SessionManager
from ..utils.cache import Cache
from ..utils.logger import Logger
from .base import BaseManager


class ToolManager(BaseManager):
    """
    管理MCP工具的发现和执行。
    
    负责:
    - 从服务器发现工具
    - 维护工具索引
    - 执行工具调用
    """
    
    def __init__(
        self, 
        session_manager: SessionManager,
        cache: Optional[Cache] = None,
        logger: Optional[Logger] = None
    ):
        """
        初始化工具管理器。
        
        Args:
            session_manager: 会话管理器
            cache: 缓存
            logger: 日志记录器
        """
        super().__init__(session_manager, cache, logger, "tool_manager")
        
        # 工具索引
        self.tools_by_server: Dict[str, List[Tool]] = {}
        self.tools_by_name: Dict[str, NamespacedTool] = {}
        self.discovery_lock = Lock()
    
    async def discover_tools(self, server_names: Optional[List[str]] = None) -> None:
        """
        从指定服务器发现工具。
        
        Args:
            server_names: 要发现工具的服务器名称列表，如果为None则使用所有已知服务器
        """
        if server_names is None:
            # 获取所有已知服务器名称
            server_names = list(self.session_manager.sessions.keys())
            
        if not server_names:
            self.logger.warning("没有可用的服务器来发现工具")
            return
            
        async with self.discovery_lock:
            # 并行发现所有服务器的工具
            discover_tasks = [self._discover_server_tools(name) for name in server_names]
            server_tools = await asyncio.gather(*discover_tasks, return_exceptions=True)
            
            # 处理结果
            for i, result in enumerate(server_tools):
                server_name = server_names[i]
                
                if isinstance(result, Exception):
                    self.logger.error(f"从服务器'{server_name}'发现工具失败: {result}")
                    continue
                    
                tools = result
                if not tools:
                    self.logger.info(f"服务器'{server_name}'没有可用的工具")
                    continue
                    
                # 更新索引
                self.tools_by_server[server_name] = tools
                
                # 添加到命名空间索引
                for tool in tools:
                    namespaced_tool = NamespacedTool(tool=tool, server_name=server_name)
                    self.tools_by_name[namespaced_tool.namespaced_name] = namespaced_tool
                    
                self.logger.info(f"从服务器'{server_name}'发现了{len(tools)}个工具")
                
            self.initialized = True
            
            # 更新缓存
            if self.cache:
                await self.cache.set("tools_by_server", self.tools_by_server)
                await self.cache.set("tools_by_name", {k: v.to_dict() for k, v in self.tools_by_name.items()})
    
    async def _discover_server_tools(self, server_name: str) -> List[Tool]:
        """从单个服务器发现工具。"""
        # 首先检查缓存
        if self.cache:
            cached_tools = await self.cache.get(f"server_tools_{server_name}")
            if cached_tools:
                self.logger.debug(f"使用缓存的工具列表: 服务器'{server_name}'")
                return cached_tools
                
        # 从服务器获取工具
        try:
            # 使用会话管理器执行操作
            result = await self.execute_with_retry(
                server_name=server_name,
                operation="list_tools",
                method_name="list_tools"
            )
            
            tools = result.tools if hasattr(result, "tools") else []
            
            # 更新缓存
            if self.cache:
                await self.cache.set(f"server_tools_{server_name}", tools)
                
            return tools
            
        except Exception as e:
            self.logger.error(f"从服务器'{server_name}'列出工具失败: {e}")
            raise
    
    async def list_tools(self) -> ListToolsResult:
        """
        列出所有可用的工具。
        
        Returns:
            带有命名空间工具列表的ListToolsResult
        """
        # 确保工具已发现
        if not self.initialized:
            await self.discover_tools()
            
        # 创建带有命名空间的工具列表
        namespaced_tools = []
        for namespaced_name, namespaced_tool in self.tools_by_name.items():
            # 创建原始工具的副本，但使用命名空间名称
            tool_copy = Tool(
                name=namespaced_name,
                description=f"[{namespaced_tool.server_name}] {namespaced_tool.description}",
                inputSchema=namespaced_tool.tool.inputSchema,
            )
            namespaced_tools.append(tool_copy)
            
        return ListToolsResult(tools=namespaced_tools)
    
    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> CallToolResult:
        """
        调用指定的工具。
        
        Args:
            tool_name: 工具名称，可以是命名空间形式(server/tool)或简单名称
            arguments: 工具参数
            
        Returns:
            工具调用结果
            
        Raises:
            ValueError: 如果找不到工具
        """
        # 确保工具已发现
        if not self.initialized:
            await self.discover_tools()
            
        # 解析工具名称
        server_name, local_tool_name = await self._parse_tool_name(tool_name)
        
        if not server_name or not local_tool_name:
            error = f"工具'{tool_name}'不存在或格式无效"
            self.logger.error(error)
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=error)]
            )
            
        self.logger.info(f"调用工具: {local_tool_name} (服务器: {server_name})")
        
        try:
            # 使用会话管理器执行操作
            result = await self.execute_with_retry(
                server_name=server_name,
                operation=f"call_tool_{local_tool_name}",
                method_name="call_tool",
                method_args={"name": local_tool_name, "arguments": arguments}
            )
            
            # 验证结果类型并确保返回CallToolResult
            if not isinstance(result, CallToolResult):
                self.logger.warning(f"工具'{tool_name}'返回了非预期类型: {type(result).__name__}")
                
                # 尝试将结果转换为CallToolResult
                try:
                    # 如果结果是字典类型
                    if isinstance(result, dict):
                        # 提取字典中可能存在的字段
                        is_error = result.get("isError", False)
                        content = result.get("content", [])
                        
                        # 确保content是列表并包含TextContent
                        if not isinstance(content, list):
                            if isinstance(content, str):
                                content = [TextContent(type="text", text=content)]
                            else:
                                content = [TextContent(type="text", text=str(content))]
                                
                        return CallToolResult(isError=is_error, content=content)
                    
                    # 如果结果是字符串或其他简单类型
                    else:
                        return CallToolResult(
                            isError=False,
                            content=[TextContent(type="text", text=str(result))]
                        )
                except Exception as e:
                    self.logger.error(f"转换工具结果失败: {e}")
                    return CallToolResult(
                        isError=True,
                        content=[TextContent(type="text", text=f"工具返回了无效结果: {str(result)[:200]}...")]
                    )
            
            return result
            
        except Exception as e:
            error = f"调用工具'{tool_name}'失败: {e}"
            self.logger.error(error)
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=error)]
            )
    
    async def _parse_tool_name(self, tool_name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析工具名称，支持命名空间形式和简单名称。
        
        Args:
            tool_name: 工具名称，格式为'server/tool'或'tool'
            
        Returns:
            (server_name, local_tool_name)元组
        """
        # 首先检查完全命名空间的工具
        if tool_name in self.tools_by_name:
            namespaced_tool = self.tools_by_name[tool_name]
            return namespaced_tool.server_name, namespaced_tool.name
            
        # 检查是否是命名空间形式
        server_name, local_name = await self._parse_namespaced_identifier(tool_name)
        if server_name:
            # 验证服务器存在
            if server_name not in self.tools_by_server:
                return None, None
                
            # 验证工具在该服务器上存在
            for tool in self.tools_by_server.get(server_name, []):
                if tool.name == local_name:
                    return server_name, local_name
                    
        # 如果是简单名称，查找第一个匹配的工具
        elif local_name:
            for server_name, tools in self.tools_by_server.items():
                for tool in tools:
                    if tool.name == local_name:
                        return server_name, local_name
                        
        return None, None 