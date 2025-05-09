"""命名空间对象模型。

这些模型用于表示带命名空间的MCP对象，例如工具、提示和资源。
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from mcp.types import Prompt, Resource, Tool


@dataclass
class NamespacedTool:
    """
    表示带命名空间的工具对象。
    
    命名空间工具是原始工具的包装，包含服务器来源信息。
    """
    
    tool: Tool
    """原始工具对象"""
    
    server_name: str
    """服务器名称"""
    
    @property
    def namespaced_name(self) -> str:
        """返回命名空间化的工具名称 (server/tool)。"""
        return f"{self.server_name}/{self.tool.name}"
    
    @property
    def name(self) -> str:
        """返回原始工具名称。"""
        return self.tool.name
    
    @property
    def description(self) -> str:
        """返回工具描述。"""
        return self.tool.description or ""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        """返回工具参数。"""
        return self.tool.parameters or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """将命名空间工具转换为字典。"""
        return {
            "name": self.namespaced_name,
            "original_name": self.name,
            "server_name": self.server_name,
            "description": self.description,
            "parameters": self.parameters
        }


@dataclass
class NamespacedPrompt:
    """
    表示带命名空间的提示对象。
    
    命名空间提示是原始提示的包装，包含服务器来源信息。
    """
    
    prompt: Prompt
    """原始提示对象"""
    
    server_name: str
    """服务器名称"""
    
    @property
    def namespaced_name(self) -> str:
        """返回命名空间化的提示名称 (server/prompt)。"""
        return f"{self.server_name}/{self.prompt.name}"
    
    @property
    def name(self) -> str:
        """返回原始提示名称。"""
        return self.prompt.name
    
    @property
    def description(self) -> str:
        """返回提示描述。"""
        return self.prompt.description or ""
    
    def to_dict(self) -> Dict[str, Any]:
        """将命名空间提示转换为字典。"""
        return {
            "name": self.namespaced_name,
            "original_name": self.name,
            "server_name": self.server_name,
            "description": self.description
        }


@dataclass
class NamespacedResource:
    """
    表示带命名空间的资源对象。
    
    命名空间资源是原始资源的包装，包含服务器来源信息。
    """
    
    resource: Optional[Resource] = None
    """原始资源对象"""
    
    server_name: str = ""
    """服务器名称"""
    
    uri: str = ""
    """资源URI"""
    
    @property
    def namespaced_uri(self) -> str:
        """返回命名空间化的资源URI (server/uri)。"""
        if "://" in self.uri:
            # 如果是完整的URI，不添加命名空间
            return self.uri
        return f"{self.server_name}/{self.uri}"
    
    def to_dict(self) -> Dict[str, Any]:
        """将命名空间资源转换为字典。"""
        return {
            "uri": self.namespaced_uri,
            "original_uri": self.uri,
            "server_name": self.server_name
        } 