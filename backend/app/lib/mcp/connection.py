"""MCP连接管理器，负责创建和维护与MCP服务器的连接。"""

import asyncio
# AsyncExitStack is no longer used here
from typing import Any, Dict, Optional, Tuple, AsyncContextManager

from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters, get_default_environment, stdio_client

from .config import ConfigProvider
from .utils.logger import Logger


class ConnectionManager:
    """
    管理与MCP服务器的连接，支持stdio和sse传输方式。
    
    负责:
    - 创建连接到服务器的传输层
    - 管理连接的生命周期
    - 提供连接状态监控
    """
    
    def __init__(self, config_provider: ConfigProvider, logger: Optional[Logger] = None):
        """
        初始化连接管理器。
        
        Args:
            config_provider: 配置提供器
            logger: 日志记录器
        """
        self.config_provider = config_provider
        self.logger = logger or Logger("connection_manager")
        # No longer managing contexts with an exit stack here
        self._active_connections: Dict[str, bool] = {} # Simple bookkeeping

    # __aenter__ and __aexit__ removed as this class no longer acts as a context manager itself

    async def create_connection(self, server_name: str) -> AsyncContextManager[Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]]:
        """
        获取用于创建到指定服务器连接的异步上下文管理器。

        Args:
            server_name: 服务器名称

        Returns:
            一个异步上下文管理器 (例如 stdio_client 或 sse_client 实例)
            
        Raises:
            ValueError: 如果服务器配置无效
            ConnectionError: 如果连接失败
        """
        config = self.config_provider.get_server_config(server_name)
        if not config:
            raise ValueError(f"未找到服务器'{server_name}'的配置")
        
        transport = config.get("transport", "stdio")
        
        try:
            if transport == "stdio":
                # Return the context manager itself, don't enter it
                return self._get_stdio_context(server_name, config)
            elif transport == "sse":
                # Return the context manager itself, don't enter it
                return self._get_sse_context(server_name, config)
            else:
                raise ValueError(f"不支持的传输类型: {transport}")
        except Exception as e:
            self.logger.error(f"连接到服务器'{server_name}'失败: {e}")
            raise ConnectionError(f"连接到服务器'{server_name}'失败: {e}") from e
    
    def _get_stdio_context(
        self, server_name: str, config: Dict[str, Any]
    ) -> AsyncContextManager[Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]]:
        """获取stdio连接的异步上下文管理器。"""
        if "command" not in config:
            raise ValueError(f"服务器'{server_name}'的stdio配置缺少'command'字段")
        
        # 准备环境变量
        env = {**get_default_environment()}
        if "env" in config and isinstance(config["env"], dict):
            env.update(config["env"])
        
        # 创建服务器参数
        params = StdioServerParameters(
            command=config["command"],
            args=config.get("args", []),
            env=env
        )
        
        # 创建和管理连接
        self.logger.info(f"准备stdio传输上下文: 服务器'{server_name}'")

        # 返回上下文管理器实例
        # 注意：stdio_client 需要返回一个 AsyncContextManager
        return stdio_client(params)

    def _get_sse_context(
        self, server_name: str, config: Dict[str, Any]
    ) -> AsyncContextManager[Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]]:
        """获取SSE连接的异步上下文管理器。"""
        if "url" not in config:
            raise ValueError(f"服务器'{server_name}'的sse配置缺少'url'字段")
        
        url = config["url"]
        headers = config.get("headers", {})
        timeout = config.get("sse_timeout")
        self.logger.info(f"准备SSE传输上下文: 服务器'{server_name}': {url}")

        # 返回上下文管理器实例
        # 注意：sse_client 需要返回一个 AsyncContextManager
        return sse_client(url, headers, sse_read_timeout=timeout)
    
    def _get_stderr_handler(self, server_name: str):
        """创建标准错误处理函数，将输出重定向到日志。"""
        def log_stderr(line: str):
            if line.strip():
                self.logger.debug(f"[{server_name}] stderr: {line.rstrip()}")
        return log_stderr
    
    def is_connected(self, server_name: str) -> bool:
        """检查是否已连接到指定服务器。"""
        return self._active_connections.get(server_name, False)
    
    async def close_connection(self, server_name: str) -> None:
        """标记指定服务器的连接为待关闭状态（实际关闭由会话管理器处理）。"""
        if server_name in self._active_connections:
            self.logger.info(f"标记服务器'{server_name}'连接为待关闭")
            # Actual closing is handled by the context manager's exit in SessionManager
            del self._active_connections[server_name] # Or mark inactive

    async def close_all(self) -> None:
        """标记所有连接为待关闭状态（实际关闭由会话管理器处理）。"""
        self.logger.info("标记所有连接为待关闭 (由会话管理器处理)")
        # Actual closing is handled by the context manager's exit in SessionManager
        self._active_connections.clear()
        # No exit_stack.aclose() needed here anymore
