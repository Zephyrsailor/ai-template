"""
MCP服务 - 提供用户隔离的MCP工具、提示和资源管理功能
"""
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import asyncio

from ..lib.mcp import MCPHub
from ..core.errors import NotFoundException, ServiceException
from ..domain.schemas.tools import Tool, ToolParameter
from pydantic import BaseModel
from mcp.types import CallToolResult, TextContent

logger = logging.getLogger(__name__)


class MCPService:
    """用户隔离的MCP服务"""

    def __init__(self):
        """初始化MCP服务"""
        self._user_hubs: Dict[str, MCPHub] = {}  # user_id -> MCPHub
        
        # MCP用户数据目录
        self.base_dir = os.path.join(os.getcwd(), "app", "data", "mcp", "users")
        os.makedirs(self.base_dir, exist_ok=True)
        
        logger.info("用户隔离MCP服务已创建")

    def _get_user_dir(self, user_id: str) -> str:
        """获取用户专用目录"""
        user_dir = os.path.join(self.base_dir, f"user_{user_id}")
        os.makedirs(user_dir, exist_ok=True)
        return user_dir

    def _get_user_servers_file(self, user_id: str) -> str:
        """获取用户的服务器配置文件路径"""
        return os.path.join(self._get_user_dir(user_id), "servers.json")

    def _get_user_context_file(self, user_id: str) -> str:
        """获取用户的上下文文件路径"""
        return os.path.join(self._get_user_dir(user_id), "context.json")

    async def _get_user_hub(self, user_id: str) -> MCPHub:
        """获取或创建用户的MCPHub"""
        if user_id not in self._user_hubs:
            logger.info(f"为用户 {user_id} 创建MCPHub")
            
            servers = self._load_user_servers(user_id)
            user_config = {"servers": servers}
            
            self._user_hubs[user_id] = MCPHub(config_dict=user_config)
            
            # 初始化连接
            if servers:
                server_names = [s.get('name') for s in servers if s.get('name') and s.get('active', True)]
                if server_names:
                    await self._user_hubs[user_id].initialize(server_names=server_names)
                    logger.info(f"用户 {user_id} 的MCPHub已初始化，连接服务器: {server_names}")
                    
        return self._user_hubs[user_id]

    async def _invalidate_user_hub(self, user_id: str) -> None:
        """清理用户的Hub（配置变更后调用）"""
        if user_id in self._user_hubs:
            logger.info(f"清理用户 {user_id} 的MCPHub")
            await self._user_hubs[user_id].shutdown()
            del self._user_hubs[user_id]

    async def _ensure_servers_initialized(self, user_id: str, selected_servers: List[Dict[str, Any]]) -> None:
        """确保选中的服务器在Hub中已初始化"""
        try:
            # 获取选中服务器的名称
            selected_server_names = {s.get('name') for s in selected_servers if s.get('name')}
            
            # 检查当前Hub是否包含了所有选中的服务器
            if user_id in self._user_hubs:
                hub = self._user_hubs[user_id]
                
                # 尝试获取当前Hub的服务器状态
                try:
                    current_statuses = await hub.list_server_statuses(list(selected_server_names))
                    current_server_names = {status.get('name') for status in current_statuses if status.get('connected')}
                    
                    # 如果所有选中的服务器都已连接，则无需重新初始化
                    if selected_server_names.issubset(current_server_names):
                        logger.debug(f"用户 {user_id} 的选中服务器已初始化: {selected_server_names}")
                        return
                except Exception as e:
                    logger.warning(f"检查服务器状态失败: {e}")
            
            # 需要重新初始化Hub以包含选中的服务器
            logger.info(f"重新初始化用户 {user_id} 的Hub以包含服务器: {selected_server_names}")
            await self._invalidate_user_hub(user_id)
            
            # 创建新的Hub并初始化选中的服务器
            servers = self._load_user_servers(user_id)
            user_config = {"servers": servers}
            
            self._user_hubs[user_id] = MCPHub(config_dict=user_config)
            
            # 初始化连接，只连接选中的活跃服务器
            active_selected_names = [s.get('name') for s in selected_servers if s.get('name') and s.get('active', True)]
            if active_selected_names:
                await self._user_hubs[user_id].initialize(server_names=active_selected_names)
                logger.info(f"用户 {user_id} 的MCPHub已重新初始化，连接服务器: {active_selected_names}")
                
        except Exception as e:
            logger.error(f"确保服务器初始化失败: {e}")
            # 如果出错，清理Hub让后续重新创建
            await self._invalidate_user_hub(user_id)

    def _load_user_servers(self, user_id: str) -> List[Dict[str, Any]]:
        """加载用户的服务器配置"""
        servers_file = self._get_user_servers_file(user_id)
        
        if not os.path.exists(servers_file):
            # 初始化空配置
            self._save_user_servers(user_id, [])
            return []
            
        try:
            with open(servers_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("servers", [])
        except Exception as e:
            logger.error(f"加载用户 {user_id} 服务器配置失败: {e}")
            return []

    def _save_user_servers(self, user_id: str, servers: List[Dict[str, Any]]) -> None:
        """保存用户的服务器配置"""
        servers_file = self._get_user_servers_file(user_id)
        
        try:
            with open(servers_file, "w", encoding="utf-8") as f:
                json.dump({"servers": servers}, f, ensure_ascii=False, indent=2)
            logger.debug(f"用户 {user_id} 的服务器配置已保存")
        except Exception as e:
            logger.error(f"保存用户 {user_id} 服务器配置失败: {e}")
            raise ServiceException(f"保存配置失败: {e}")

    # === 服务器管理 ===
    
    def get_user_servers(self, user_id: str, active_only: bool = False) -> List[Dict[str, Any]]:
        """获取用户的MCP服务器列表"""
        servers = self._load_user_servers(user_id)
        if active_only:
            return [s for s in servers if s.get("active", True)]
        return servers

    def get_user_server(self, user_id: str, server_id: str) -> Optional[Dict[str, Any]]:
        """获取用户的单个MCP服务器"""
        servers = self._load_user_servers(user_id)
        for server in servers:
            if server.get("id") == server_id:
                return server
        return None

    async def add_user_server(self, user_id: str, server_data: Dict[str, Any]) -> Dict[str, Any]:
        """为用户添加MCP服务器"""
        if "name" not in server_data:
            raise ValueError("服务器名称 'name' 是必需的")

        servers = self._load_user_servers(user_id)
        
        # 检查名称冲突
        for server in servers:
            if server.get("name") == server_data["name"]:
                raise ValueError(f"服务器名称 '{server_data['name']}' 已存在")

        # 创建新服务器配置
        now = datetime.now().isoformat()
        new_server = {
            "id": server_data.get("id") or str(uuid.uuid4()),
            "name": server_data["name"],
            "command": server_data.get("command", "npx"),
            "args": server_data.get("args", []),
            "env": server_data.get("env", {}),
            "transport": server_data.get("transport", "stdio"),
            "description": server_data.get("description", ""),
            "active": server_data.get("active", True),
            "created_at": now,
            "updated_at": now
        }

        servers.append(new_server)
        self._save_user_servers(user_id, servers)
        
        # 同步清理并重建Hub，确保立即生效
        await self._invalidate_user_hub(user_id)
        
        logger.info(f"用户 {user_id} 添加了MCP服务器: {new_server['name']}")
        return new_server

    async def update_user_server(self, user_id: str, server_id: str, server_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新用户的MCP服务器"""
        servers = self._load_user_servers(user_id)
        
        for i, server in enumerate(servers):
            if server.get("id") == server_id:
                # 更新字段
                for key, value in server_data.items():
                    if key not in ["id", "created_at"]:
                        servers[i][key] = value
                servers[i]["updated_at"] = datetime.now().isoformat()
                
                self._save_user_servers(user_id, servers)
                
                # 同步清理并重建Hub，确保立即生效
                await self._invalidate_user_hub(user_id)
                
                logger.info(f"用户 {user_id} 更新了MCP服务器: {server_id}")
                return servers[i]
                
        return None

    async def delete_user_server(self, user_id: str, server_id: str) -> bool:
        """删除用户的MCP服务器"""
        servers = self._load_user_servers(user_id)
        original_count = len(servers)
        
        servers = [s for s in servers if s.get("id") != server_id]
        
        if len(servers) < original_count:
            self._save_user_servers(user_id, servers)
            
            # 同步清理并重建Hub，确保立即生效
            await self._invalidate_user_hub(user_id)
            
            logger.info(f"用户 {user_id} 删除了MCP服务器: {server_id}")
            return True
            
        return False

    # === 服务器状态 ===
    
    async def get_user_server_statuses(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户MCP服务器的状态"""
        try:
            hub = await self._get_user_hub(user_id)
            servers = self.get_user_servers(user_id, active_only=True)
            server_names = [s.get('name') for s in servers if s.get('name')]
            
            if not server_names:
                return []
                
            statuses = await hub.list_server_statuses(server_names=server_names)
            return statuses
        except Exception as e:
            logger.error(f"获取用户 {user_id} 服务器状态失败: {e}")
            return []

    # === 工具管理 ===
    
    async def get_user_tools(self, user_id: str) -> List[Tool]:
        """获取用户可用的工具列表"""
        try:
            hub = await self._get_user_hub(user_id)
            servers = self.get_user_servers(user_id, active_only=True)
            
            # 获取工具列表
            result = await hub.list_tools()
            mcp_tools = result.tools
            
            # 转换为应用内部的Tool模型
            converted_tools = []
            server_names = {s.get('name') for s in servers}
            
            for tool in mcp_tools:
                server_name = tool.name.split("/")[0] if "/" in tool.name else tool.name.split(":")[0]
                
                # 只返回用户服务器的工具
                if server_name in server_names:
                    parameters = []
                    input_schema = getattr(tool, 'inputSchema', None)
                    if isinstance(input_schema, dict):
                        props = input_schema.get("properties", {})
                        required = input_schema.get("required", [])
                        
                        for param_name, param_info in props.items():
                            parameters.append(ToolParameter(
                                name=param_name,
                                description=param_info.get("description", ""),
                                type=param_info.get("type", "string"),
                                required=param_name in required,
                                enum=param_info.get("enum")
                            ))
                    
                    tool_model = Tool(
                        id=f"{server_name}/{tool.name}",
                        name=tool.name,
                        description=tool.description,
                        server=server_name,
                        category=getattr(tool, "category", "general"),
                        parameters=parameters
                    )
                    converted_tools.append(tool_model)
            
            return converted_tools
            
        except Exception as e:
            logger.error(f"获取用户 {user_id} 工具列表失败: {e}")
            raise ServiceException(f"获取工具列表失败: {e}")

    async def get_tools_for_servers(self, user_id: str, server_ids: List[str]) -> List[Tool]:
        """获取指定服务器的工具列表"""
        try:
            # 获取指定的服务器信息
            selected_servers = []
            for server_id in server_ids:
                server = self.get_user_server(user_id, server_id)
                if server and server.get('active', True):
                    selected_servers.append(server)
            
            if not selected_servers:
                logger.warning(f"用户 {user_id} 没有可用的服务器")
                return []
            
            # 确保Hub包含选中的服务器（强制重新初始化）
            await self._ensure_servers_initialized(user_id, selected_servers)
            
            hub = await self._get_user_hub(user_id)
            
            # 获取工具列表
            result = await hub.list_tools()
            mcp_tools = result.tools
            
            # 转换为应用内部的Tool模型，只返回选中服务器的工具
            converted_tools = []
            selected_server_names = {s.get('name') for s in selected_servers}
            
            for tool in mcp_tools:
                server_name = tool.name.split("/")[0] if "/" in tool.name else tool.name.split(":")[0]
                
                # 只返回选中服务器的工具
                if server_name in selected_server_names:
                    parameters = []
                    input_schema = getattr(tool, 'inputSchema', None)
                    if isinstance(input_schema, dict):
                        props = input_schema.get("properties", {})
                        required = input_schema.get("required", [])
                        
                        for param_name, param_info in props.items():
                            parameters.append(ToolParameter(
                                name=param_name,
                                description=param_info.get("description", ""),
                                type=param_info.get("type", "string"),
                                required=param_name in required,
                                enum=param_info.get("enum")
                            ))
                    
                    tool_model = Tool(
                        id=f"{server_name}/{tool.name}",
                        name=tool.name,
                        description=tool.description,
                        server=server_name,
                        category=getattr(tool, "category", "general"),
                        parameters=parameters
                    )
                    converted_tools.append(tool_model)
            
            logger.info(f"用户 {user_id} 获取到 {len(converted_tools)} 个工具，来自服务器: {selected_server_names}")
            return converted_tools
            
        except Exception as e:
            logger.error(f"获取用户 {user_id} 指定服务器工具列表失败: {e}")
            raise ServiceException(f"获取指定服务器工具列表失败: {e}")

    async def call_tool_for_user(self, user_id: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """为用户调用工具（封装MCPHub操作）"""
        try:
            hub = await self._get_user_hub(user_id)
            
            # 加载用户上下文
            context = self._load_user_context(user_id)
            if context:
                logger.debug(f"为用户 {user_id} 加载了上下文")
            
            # 调用工具
            result = await hub.call_tool(tool_name, arguments)
            
            logger.info(f"用户 {user_id} 调用工具 {tool_name} 成功")
            return result
            
        except Exception as e:
            error_message = f"调用工具 {tool_name} 失败: {str(e)}"
            logger.error(f"用户 {user_id} {error_message}")
            # 直接抛出异常，让调用者处理
            raise e

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """通用工具调用方法（用于匿名用户或非用户隔离场景）"""
        # 这个方法可以根据需要实现，暂时抛出异常提示需要用户隔离
        raise ServiceException("工具调用需要用户隔离，请使用 call_tool_for_user 方法")

    async def call_user_tool(self, user_id: str, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """调用用户的工具（保持向后兼容）"""
        try:
            result = await self.call_tool_for_user(user_id, tool_name, arguments)
            return result
        except Exception as e:
            return CallToolResult(
                isError=True,
                content=[TextContent(text=str(e), type="text")]
            )

    # === 用户上下文管理 ===
    
    def _load_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """加载用户上下文"""
        context_file = self._get_user_context_file(user_id)
        
        if not os.path.exists(context_file):
            return None
            
        try:
            with open(context_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载用户 {user_id} 上下文失败: {e}")
            return None

    def save_user_context(self, user_id: str, context: Dict[str, Any]) -> bool:
        """保存用户上下文"""
        context_file = self._get_user_context_file(user_id)
        
        try:
            with open(context_file, "w", encoding="utf-8") as f:
                json.dump(context, f, ensure_ascii=False, indent=2)
            logger.debug(f"用户 {user_id} 上下文已保存")
            return True
        except Exception as e:
            logger.error(f"保存用户 {user_id} 上下文失败: {e}")
            return False

    def delete_user_context(self, user_id: str) -> bool:
        """删除用户上下文"""
        context_file = self._get_user_context_file(user_id)
        
        try:
            if os.path.exists(context_file):
                os.remove(context_file)
                logger.info(f"用户 {user_id} 上下文已删除")
            return True
        except Exception as e:
            logger.error(f"删除用户 {user_id} 上下文失败: {e}")
            return False

    # === 服务关闭 ===
    
    async def shutdown(self) -> None:
        """关闭所有用户的Hub连接"""
        logger.info("关闭所有用户的MCP连接")
        
        for user_id, hub in list(self._user_hubs.items()):
            try:
                await hub.shutdown()
                logger.info(f"用户 {user_id} 的MCP连接已关闭")
            except Exception as e:
                logger.error(f"关闭用户 {user_id} MCP连接失败: {e}")
                
        self._user_hubs.clear()
        logger.info("MCP服务已关闭")


# === Pydantic 模型 ===

class MCPServerCreate(BaseModel):
    """MCP服务器创建模型"""
    name: str
    command: str = "npx"
    args: List[str] = []
    env: Dict[str, str] = {}
    transport: str = "stdio"
    description: Optional[str] = ""
    active: bool = True