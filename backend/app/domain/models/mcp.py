"""
MCP (Model Context Protocol) 相关数据模型
"""
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, JSON, Integer
from sqlalchemy.orm import relationship
import json

from ...core.database import BaseModel as SQLAlchemyBaseModel


class MCPTransportType(Enum):
    """MCP传输类型"""
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


class MCPServerStatus(Enum):
    """MCP服务器状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    CONNECTING = "connecting"


class MCPCapability(Enum):
    """MCP能力类型"""
    RESOURCES = "resources"
    TOOLS = "tools"
    PROMPTS = "prompts"
    SAMPLING = "sampling"


# === Pydantic模型 (用于API) ===

class MCPServerBase(BaseModel):
    """MCP服务器基础模型"""
    name: str = Field(..., description="服务器名称", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="服务器描述", max_length=1000)
    transport: MCPTransportType = Field(MCPTransportType.STDIO, description="传输类型")
    
    # 连接配置
    command: Optional[str] = Field(None, description="启动命令 (stdio)")
    args: Optional[List[str]] = Field(default_factory=list, description="命令参数")
    env: Optional[Dict[str, str]] = Field(default_factory=dict, description="环境变量")
    url: Optional[str] = Field(None, description="服务器URL (http/sse)")
    
    # 状态和配置
    active: bool = Field(True, description="是否启用")
    auto_start: bool = Field(True, description="是否自动启动")
    timeout: int = Field(30, description="连接超时时间(秒)", ge=1, le=300)
    
    class Config:
        use_enum_values = True


class MCPServerCreateRequest(MCPServerBase):
    """前端创建MCP服务器请求模型（不包含user_id）"""
    pass


class MCPServerCreate(MCPServerBase):
    """内部创建MCP服务器模型（包含user_id）"""
    user_id: str = Field(..., description="所属用户ID")


class MCPServerUpdate(BaseModel):
    """更新MCP服务器请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    transport: Optional[MCPTransportType] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    url: Optional[str] = None
    active: Optional[bool] = None
    auto_start: Optional[bool] = None
    timeout: Optional[int] = Field(None, ge=1, le=300)
    
    class Config:
        use_enum_values = True


class MCPServerResponse(MCPServerBase):
    """MCP服务器响应模型"""
    id: str = Field(..., description="服务器ID")
    user_id: str = Field(..., description="所属用户ID")
    status: MCPServerStatus = Field(..., description="服务器状态")
    capabilities: List[MCPCapability] = Field(default_factory=list, description="服务器能力")
    last_error: Optional[str] = Field(None, description="最后错误信息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    last_connected_at: Optional[datetime] = Field(None, description="最后连接时间")
    
    class Config:
        use_enum_values = True
        from_attributes = True


class MCPServerStatus(BaseModel):
    """MCP服务器状态模型"""
    server_id: str = Field(..., description="服务器ID")
    name: str = Field(..., description="服务器名称")
    status: str = Field(..., description="当前状态")
    connected: bool = Field(..., description="是否已连接")
    healthy: bool = Field(..., description="是否健康")
    last_ping: Optional[datetime] = Field(None, description="最后ping时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    capabilities: List[str] = Field(default_factory=list, description="可用能力")
    
    class Config:
        use_enum_values = True


class MCPTool(BaseModel):
    """MCP工具模型"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    server_id: Optional[str] = Field(None, description="所属服务器ID")
    server_name: str = Field(..., description="所属服务器名称")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="输入参数schema")
    # 新增字段
    namespace: Optional[str] = Field(None, description="工具命名空间")
    full_name: str = Field(..., description="完整工具名称（包含命名空间）")
    category: Optional[str] = Field(None, description="工具分类")
    version: Optional[str] = Field(None, description="工具版本")
    is_available: bool = Field(True, description="工具是否可用")
    last_used: Optional[datetime] = Field(None, description="最后使用时间")
    usage_count: int = Field(0, description="使用次数")
    
    @property
    def parameters(self) -> Dict[str, Any]:
        """兼容性属性：将input_schema转换为parameters格式"""
        if not self.input_schema:
            return {}
        
        # 如果input_schema已经是parameters格式，直接返回
        if "properties" in self.input_schema:
            return self.input_schema.get("properties", {})
        
        # 否则直接返回input_schema
        return self.input_schema
    
    def to_standard_tool(self) -> "Tool":
        """转换为标准Tool模型"""
        from ..schemas.tools import Tool, ToolParameter
        
        # 转换parameters
        tool_parameters = {}
        if self.input_schema and "properties" in self.input_schema:
            properties = self.input_schema["properties"]
            required_fields = self.input_schema.get("required", [])
            
            for param_name, param_def in properties.items():
                tool_parameters[param_name] = ToolParameter(
                    type=param_def.get("type", "string"),
                    description=param_def.get("description", ""),
                    required=param_name in required_fields,
                    enum=param_def.get("enum"),
                    default=param_def.get("default")
                )
        
        return Tool(
            name=self.name,
            description=self.description,
            parameters=tool_parameters
        )
    
    @classmethod
    def from_standard_tool(cls, tool: "Tool", server_name: str, server_id: Optional[str] = None) -> "MCPTool":
        """从标准Tool模型创建MCPTool"""
        # 转换parameters为input_schema格式
        input_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param_name, param in tool.parameters.items():
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
                
            input_schema["properties"][param_name] = prop
            
            if param.required:
                input_schema["required"].append(param_name)
        
        return cls(
            name=tool.name,
            description=tool.description,
            server_id=server_id,
            server_name=server_name,
            input_schema=input_schema,
            full_name=f"{server_name}/{tool.name}",
            is_available=True,
            usage_count=0
        )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class MCPResource(BaseModel):
    """MCP资源模型"""
    uri: str = Field(..., description="资源URI")
    name: str = Field(..., description="资源名称")
    description: Optional[str] = Field(None, description="资源描述")
    mime_type: Optional[str] = Field(None, description="MIME类型")
    server_id: str = Field(..., description="所属服务器ID")
    server_name: str = Field(..., description="所属服务器名称")


class MCPPrompt(BaseModel):
    """MCP提示模板模型"""
    name: str = Field(..., description="提示名称")
    description: Optional[str] = Field(None, description="提示描述")
    arguments: List[Dict[str, Any]] = Field(default_factory=list, description="参数定义")
    server_id: str = Field(..., description="所属服务器ID")
    server_name: str = Field(..., description="所属服务器名称")


class MCPToolCall(BaseModel):
    """MCP工具调用请求模型"""
    tool_name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


class MCPToolResult(BaseModel):
    """MCP工具调用结果模型"""
    success: bool = Field(..., description="是否成功")
    content: List[Dict[str, Any]] = Field(..., description="结果内容")
    error: Optional[str] = Field(None, description="错误信息")


class MCPConnectionTest(BaseModel):
    """MCP连接测试结果模型"""
    success: bool = Field(..., description="测试是否成功")
    message: str = Field(..., description="测试结果消息")
    latency_ms: Optional[int] = Field(None, description="延迟(毫秒)")
    capabilities: List[MCPCapability] = Field(default_factory=list, description="检测到的能力")


# === SQLAlchemy模型 (用于数据库) ===

class MCPServer(SQLAlchemyBaseModel):
    """MCP服务器数据库模型"""
    __tablename__ = "mcp_servers"
    
    # 基本信息
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    user_id = Column(String(36), nullable=False, index=True)  # 所属用户
    
    # 连接配置
    transport = Column(String(20), nullable=False, default="stdio")
    command = Column(Text)  # stdio命令
    args = Column(JSON)  # 命令参数
    env = Column(JSON)  # 环境变量
    url = Column(String(500))  # HTTP/SSE URL
    
    # 状态和配置
    active = Column(Boolean, default=True)
    auto_start = Column(Boolean, default=True)
    timeout = Column(Integer, default=30)
    status = Column(String(20), default="inactive")
    
    # 能力和状态
    capabilities = Column(JSON, default=list)  # 服务器能力列表
    last_error = Column(Text)
    last_connected_at = Column(DateTime)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        # 安全解析JSON字段
        def safe_parse_json(value, default):
            if value is None:
                return default
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return default
            return value
        
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "transport": self.transport,
            "command": self.command,
            "args": safe_parse_json(self.args, []),
            "env": safe_parse_json(self.env, {}),
            "url": self.url,
            "active": self.active,
            "auto_start": self.auto_start,
            "timeout": self.timeout,
            "status": self.status,
            "capabilities": safe_parse_json(self.capabilities, []),
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_connected_at": self.last_connected_at.isoformat() if self.last_connected_at else None,
        }
    
    def __repr__(self):
        return f"<MCPServer(id={self.id}, name={self.name}, user_id={self.user_id})>" 