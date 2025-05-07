"""
MCP客户端管理模块 - 实现与多个MCP服务器的交互

这个模块提供了一个统一的接口来管理与多个MCP服务器的连接、发现并使用它们的工具、提示和资源。
"""

from .hub import MCPHub
from .config import ConfigProvider

__all__ = ['MCPHub', 'ConfigProvider'] 