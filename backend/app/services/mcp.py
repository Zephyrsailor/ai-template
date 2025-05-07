"""
MCP服务 - 提供MCP工具、提示和资源管理功能
"""
import logging
import os
from typing import List, Dict, Any, Optional, Union
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
    """MCP服务，提供工具、提示和资源管理功能"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化MCP服务
        
        Args:
            config_path: MCP配置文件路径
        """
        self.config_path = config_path
        self.hub = None
        self._initialized = False
        self._tools_cache = {}

         # 新增：MCP服务器配置目录
        self.base_dir = os.path.join(os.getcwd(), "app", "data", "mcp")
        self.meta_dir = os.path.join(self.base_dir, "meta")
        self.config_dir = os.path.join(self.base_dir, "config")
        
        # 确保目录存在
        os.makedirs(self.meta_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 服务器列表文件路径
        self.servers_file = os.path.join(self.meta_dir, "servers.json")

        
        self.config_path = self.servers_file
        
        # 初始化服务器列表文件（如果不存在）
        if not os.path.exists(self.servers_file):
            self._save_servers([])
        
        logger.info("MCP服务已创建")
    
    async def initialize(self) -> None:
        """初始化MCP服务，连接到MCP服务器"""
        if self._initialized:
            return
            
        try:
            logger.info(f"正在初始化MCP服务，配置路径: {self.config_path or '默认'}")
            self.hub = MCPHub(config_path=self.config_path)
            
            # 添加错误处理，允许一些服务器初始化失败
            try:
                await self.hub.initialize()
            except Exception as e:
                # 检查是否是stdio相关的取消作用域错误
                if "cancel scope" in str(e):
                    logger.warning(f"MCP服务初始化期间出现非致命错误 (stdio cancel scope): {str(e)}")
                else:
                    # 其他类型的错误则重新抛出
                    raise
            
            self._initialized = True
            logger.info("MCP服务初始化成功")
        except Exception as e:
            logger.error(f"MCP服务初始化失败: {str(e)}")
            raise ServiceException(f"MCP服务初始化失败: {str(e)}")
    
    async def get_tools(self, category: Optional[str] = None) -> List[Tool]:
        """
        获取可用工具列表
        
        Args:
            category: 可选的工具类别过滤器
            
        Returns:
            工具列表
        """
        await self._ensure_initialized()
        
        try:
            # 缓存键
            cache_key = f"tools_{category or 'all'}"
            
            # 检查缓存
            if cache_key in self._tools_cache:
                return self._tools_cache[cache_key]
                
            # 获取工具列表
            result = await self.hub.list_tools()
            tools = result.tools
            
            # 转换为Tool模型
            converted_tools = []
            for tool in tools:
                # 提取参数
                parameters = []
                if hasattr(tool, 'inputSchema') and isinstance(tool.inputSchema, dict):
                    props = tool.inputSchema.get("properties", {})
                    required = tool.inputSchema.get("required", [])
                    
                    for param_name, param_info in props.items():
                        parameters.append(ToolParameter(
                            name=param_name,
                            description=param_info.get("description", ""),
                            type=param_info.get("type", "string"),
                            required=param_name in required,
                            enum=param_info.get("enum")
                        ))
                
                # 创建工具
                tool_model = Tool(
                    id=f"{getattr(tool, 'server', '')}/{tool.name}" if hasattr(tool, "server") else tool.name,
                    name=tool.name,
                    description=tool.description,
                    server=getattr(tool, "server", None),
                    category=getattr(tool, "category", "general"),
                    parameters=parameters
                )
                
                # 应用类别过滤
                if category is None or tool_model.category == category:
                    converted_tools.append(tool_model)
            
            # 更新缓存
            self._tools_cache[cache_key] = converted_tools
            
            return converted_tools
            
        except Exception as e:
            logger.error(f"获取工具列表失败: {str(e)}")
            raise ServiceException(f"获取工具列表失败: {str(e)}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        调用工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具调用结果
            
        Raises:
            NotFoundException: 如果工具不存在
            ServiceException: 如果调用失败
        """
        await self._ensure_initialized()
        
        try:
            logger.info(f"调用工具: {tool_name}")
            # 直接委托给 _safe_call_tool 方法，确保一致的错误处理和资源管理
            result = await self._safe_call_tool(tool_name, arguments)
            
            # 检查结果是否表示错误
            if getattr(result, 'isError', False):
                error_msg = next((content.text for content in result.content if getattr(content, 'type', None) == 'text'), 
                                "未知错误")
                raise ServiceException(error_msg)
            
            return result
        except Exception as e:
            if not isinstance(e, ServiceException):
                logger.error(f"调用工具 {tool_name} 失败: {str(e)}")
                raise ServiceException(f"调用工具失败: {str(e)}")
            raise
            
    async def call_tool_on_server(self, server_id: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        在特定服务器上调用工具
        
        Args:
            server_id: 服务器ID
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具调用结果
            
        Raises:
            NotFoundException: 如果服务器或工具不存在
            ServiceException: 如果调用失败
        """
        await self._ensure_initialized()
        
        try:
            # 获取服务器信息
            server = self.get_server(server_id)
            if not server:
                raise NotFoundException(f"MCP服务器 {server_id} 不存在")
                
            logger.info(f"在服务器 {server_id} 上调用工具: {tool_name}")
            
            # 调用工具，使用完整的工具名称（包含服务器ID）
            qualified_tool_name = f"{server_id}:{tool_name}"
            return await self.call_tool(qualified_tool_name, arguments)
        except Exception as e:
            if not isinstance(e, (NotFoundException, ServiceException)):
                logger.error(f"在服务器 {server_id} 上调用工具 {tool_name} 失败: {str(e)}")
                raise ServiceException(f"调用工具失败: {str(e)}")
            raise
    
    async def get_prompts(self, server_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取提示模板列表
        
        Args:
            server_name: 可选的服务器名称过滤器
            
        Returns:
            提示模板列表
        """
        await self._ensure_initialized()
        
        try:
            logger.info(f"获取提示模板，服务器: {server_name or '所有'}")
            result = await self.hub.list_prompts(server_name)
            return result
        except Exception as e:
            logger.error(f"获取提示模板失败: {str(e)}")
            raise ServiceException(f"获取提示模板失败: {str(e)}")
    
    async def get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, str]] = None) -> str:
        """
        获取并应用提示模板
        
        Args:
            prompt_name: 提示模板名称
            arguments: 提示模板参数
            
        Returns:
            应用参数后的提示文本
            
        Raises:
            NotFoundException: 如果提示模板不存在
            ServiceException: 如果获取失败
        """
        await self._ensure_initialized()
        
        try:
            logger.info(f"获取提示模板: {prompt_name}")
            result = await self.hub.get_prompt(prompt_name, arguments)
            return result.content
        except Exception as e:
            logger.error(f"获取提示模板 {prompt_name} 失败: {str(e)}")
            raise ServiceException(f"获取提示模板失败: {str(e)}")
    
    async def get_resources(self, server_name: Optional[str] = None) -> Dict[str, List[str]]:
        """
        获取资源列表
        
        Args:
            server_name: 可选的服务器名称过滤器
            
        Returns:
            资源列表
        """
        await self._ensure_initialized()
        
        try:
            logger.info(f"获取资源列表，服务器: {server_name or '所有'}")
            result = await self.hub.list_resources(server_name)
            return result
        except Exception as e:
            logger.error(f"获取资源列表失败: {str(e)}")
            raise ServiceException(f"获取资源列表失败: {str(e)}")
    
    async def get_resource(self, resource_uri: str) -> Union[str, bytes, Dict[str, Any]]:
        """
        获取资源内容
        
        Args:
            resource_uri: 资源URI
            
        Returns:
            资源内容
            
        Raises:
            NotFoundException: 如果资源不存在
            ServiceException: 如果获取失败
        """
        await self._ensure_initialized()
        
        try:
            logger.info(f"获取资源: {resource_uri}")
            result = await self.hub.get_resource(resource_uri)
            return result.content
        except Exception as e:
            logger.error(f"获取资源 {resource_uri} 失败: {str(e)}")
            raise ServiceException(f"获取资源失败: {str(e)}")
    
    async def _ensure_initialized(self) -> None:
        """确保MCP服务已初始化"""
        if not self._initialized:
            await self.initialize()
    
    async def shutdown(self) -> None:
        """关闭MCP服务"""
        if self.hub and self._initialized:
            try:
                logger.info("正在关闭MCP服务")
                try:
                    # 直接调用 shutdown，移除 asyncio.shield
                    await self.hub.shutdown()
                except RuntimeError as e:
                    # 忽略关闭时的 cancel scope 错误
                    if "cancel scope" in str(e):
                        logger.warning(f"忽略MCP服务关闭时的 cancel scope 错误: {str(e)}")
                    else:
                        raise
            
                self._initialized = False
                self.hub = None
                logger.info("MCP服务已关闭")
            except Exception as e:
                logger.error(f"关闭MCP服务失败: {str(e)}")
                # 不抛出异常，以免影响其他关闭操作
    
    async def process_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        处理多个工具调用
        
        Args:
            tool_calls: 工具调用列表
            
        Returns:
            工具调用结果列表
        """
        await self._ensure_initialized()
        
        results = []
        
        for call in tool_calls:
            try:
                # 提取工具名称和参数
                tool_name = call.get("name", call.get("function", {}).get("name"))
                arguments = call.get("arguments", call.get("function", {}).get("arguments", {}))
                
                if not tool_name:
                    continue
                
                # 直接调用 _safe_call_tool，避免使用 asyncio.create_task
                # 这样可以确保每个工具调用在同一个上下文中完成
                result = await self._safe_call_tool(tool_name, arguments)
                
                results.append({
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"处理工具调用失败: {str(e)}")
                results.append({
                    "tool_name": call.get("name", "未知工具"),
                    "error": str(e)
                })
        
        return results
        
    async def _safe_call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """
        安全地调用工具，处理所有异常
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具调用结果或错误信息
        """
        temp_hub = None
        try:
            # 为每次调用创建一个新的 MCPHub 实例，确保上下文隔离
            # 这样可以避免在不同任务间共享同一个上下文对象
            temp_hub = MCPHub(config_path=self.config_path)
            
            # 为stdio客户端相关任务设置异常处理器，避免"Task exception was never retrieved"警告
            loop = asyncio.get_running_loop()
            original_exception_handler = loop.get_exception_handler()
            
            def custom_exception_handler(loop, context):
                exception = context.get('exception')
                if isinstance(exception, RuntimeError) and "cancel scope" in str(exception):
                    # 静默处理cancel scope相关错误
                    logger.debug(f"忽略asyncio任务中的cancel scope错误: {str(exception)}")
                    return
                # 对于其他类型的错误，使用原始处理器
                if original_exception_handler is not None:
                    original_exception_handler(loop, context)
                else:
                    loop.default_exception_handler(context)
                
            # 设置自定义异常处理器
            loop.set_exception_handler(custom_exception_handler)
            
            try:
                await temp_hub.initialize()
                
                # 在新的隔离上下文中调用工具
                result = await temp_hub.call_tool(tool_name, arguments)
                return result
            finally:
                # 恢复原始异常处理器
                loop.set_exception_handler(original_exception_handler)
            
        except Exception as e:
            logger.error(f"调用工具 {tool_name} 失败: {str(e)}")
            error_msg = f"调用工具失败: {str(e)}"
            
            # 返回CallToolResult结构
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=error_msg)]
            )
        finally:
            # 确保资源被正确清理，即使发生异常
            if temp_hub:
                try:
                    # 直接调用 shutdown，移除 asyncio.shield
                    await temp_hub.shutdown()
                except RuntimeError as e:
                    # 忽略关闭时的 cancel scope 错误，因为此时工具调用已经完成
                    if "cancel scope" in str(e):
                        logger.warning(f"忽略工具关闭时的 cancel scope 错误: {str(e)}")
                    else:
                        logger.error(f"关闭临时Hub时出错: {str(e)}")
                except Exception as e:
                    logger.error(f"关闭临时Hub时出错: {str(e)}")
    
    # 新增：服务器管理方法
    def get_all_servers(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """获取所有MCP服务器"""
        servers = self._load_servers()
        if active_only:
            return [s for s in servers if s.get("active", True)]
        return servers
    
    def get_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        """获取单个MCP服务器"""
        servers = self._load_servers()
        for server in servers:
            if server["id"] == server_id:
                return server
        return None
    
    def add_server(self, server_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加新的MCP服务器"""
        servers = self._load_servers()
        
        # 检查URL是否已存在 (仅当URL存在时才检查)
        if "url" in server_data and server_data["url"]:
            for server in servers:
                if "url" in server and server["url"] == server_data["url"]:
                    raise ValueError(f"具有相同URL的服务器已存在: {server_data['url']}")
        
        # 确保args是数组形式
        if "args" in server_data and not isinstance(server_data["args"], list):
            if isinstance(server_data["args"], str):
                # 如果是字符串，将其分割为数组
                server_data["args"] = server_data["args"].split()
            else:
                # 如果不是字符串也不是数组，设置为空数组
                server_data["args"] = []
        
        # 确保env是字典形式
        if "env" in server_data and not isinstance(server_data["env"], dict):
            if isinstance(server_data["env"], str):
                # 如果是字符串，尝试解析为字典
                env_dict = {}
                for line in server_data["env"].strip().split("\n"):
                    if line and "=" in line:
                        key, value = line.split("=", 1)
                        env_dict[key.strip()] = value.strip()
                server_data["env"] = env_dict
            else:
                # 如果不是字符串也不是字典，设置为空字典
                server_data["env"] = {}
        
        # 创建新服务器
        now = datetime.now().isoformat()
        new_server = {
            "id": server_data.get("id") or str(uuid.uuid4()),
            "name": server_data["name"],
            "url": server_data.get("url", ""),  # URL可选
            "command": server_data.get("command", "npx"),
            "args": server_data.get("args", []),
            "env": server_data.get("env", {}),
            "description": server_data.get("description", ""),
            "active": server_data.get("active", True),
            "created_at": now,
            "updated_at": now
        }
        
        servers.append(new_server)
        self._save_servers(servers)
        return new_server
    
    def update_server(self, server_id: str, server_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新MCP服务器配置"""
        servers = self._load_servers()
        
        # 确保args是数组形式
        if "args" in server_data and not isinstance(server_data["args"], list):
            if isinstance(server_data["args"], str):
                # 如果是字符串，将其分割为数组
                server_data["args"] = server_data["args"].split()
            else:
                # 如果不是字符串也不是数组，设置为空数组
                server_data["args"] = []
                
        # 确保env是字典形式
        if "env" in server_data and not isinstance(server_data["env"], dict):
            if isinstance(server_data["env"], str):
                # 如果是字符串，尝试解析为字典
                env_dict = {}
                for line in server_data["env"].strip().split("\n"):
                    if line and "=" in line:
                        key, value = line.split("=", 1)
                        env_dict[key.strip()] = value.strip()
                server_data["env"] = env_dict
            else:
                # 如果不是字符串也不是字典，设置为空字典
                server_data["env"] = {}
                
        for i, server in enumerate(servers):
            if server["id"] == server_id:
                # 更新服务器
                servers[i].update({
                    "name": server_data.get("name", server["name"]),
                    "url": server_data.get("url", server.get("url", "")),
                    "command": server_data.get("command", server.get("command", "npx")),
                    "args": server_data.get("args", server.get("args", [])),
                    "env": server_data.get("env", server.get("env", {})),
                    "description": server_data.get("description", server.get("description", "")),
                    "active": server_data.get("active", server.get("active", True)),
                    "updated_at": datetime.now().isoformat()
                })
                
                self._save_servers(servers)
                return servers[i]
                
        return None
    
    def delete_server(self, server_id: str) -> bool:
        """删除MCP服务器"""
        servers = self._load_servers()
        
        for i, server in enumerate(servers):
            if server["id"] == server_id:
                del servers[i]
                self._save_servers(servers)
                return True
                
        return False
    
    def _load_servers(self) -> List[Dict[str, Any]]:
        """加载服务器列表"""
        if not os.path.exists(self.servers_file):
            logger.error(f"服务器配置文件不存在: {self.servers_file}")
            return []
            
        try:
            with open(self.servers_file, "r", encoding="utf-8") as f:
                # 打印原始文件内容
                f.seek(0)
                raw_content = f.read()
                logger.info(f"原始文件内容: {raw_content}")
                
                # 重置文件指针并解析JSON
                f.seek(0)
                data = json.load(f)
                
                # 检查解析后的数据结构
                logger.info(f"JSON解析结果: {data}")
                logger.info(f"数据类型: {type(data)}")
                logger.info(f"包含的键: {list(data.keys()) if isinstance(data, dict) else '非字典类型'}")
                
                # 尝试获取servers键
                servers = data.get("servers", [])
                logger.info(f"获取到的服务器数量: {len(servers)}")
                
                # 如果没有servers键，尝试其他可能的键名
                if not servers and isinstance(data, dict):
                    for key in data.keys():
                        if key.lower() == "servers":
                            logger.info(f"找到了不同大小写的键: {key}")
                            servers = data[key]
                            break
                
                return servers
        except Exception as e:
            logger.error(f"加载MCP服务器列表失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _save_servers(self, servers: List[Dict[str, Any]]) -> None:
        """保存服务器列表"""
        try:
            with open(self.servers_file, "w", encoding="utf-8") as f:
                json.dump({"servers": servers}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存MCP服务器列表失败: {str(e)}")

class MCPServerCreate(BaseModel):
    """MCP服务器创建模型"""
    name: str
    url: Optional[str] = None  # URL是可选的，支持stdio模式
    command: str = "npx"
    args: List[str] = []  # 参数列表，确保是数组格式
    env: Dict[str, str] = {}
    description: Optional[str] = ""
    active: bool = True
