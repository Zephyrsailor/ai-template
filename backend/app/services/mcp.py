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

from ..lib.mcp import MCPHub # 假设 MCPHub 在这里
from ..core.errors import NotFoundException, ServiceException
from ..domain.schemas.tools import Tool, ToolParameter
from pydantic import BaseModel
from mcp.types import CallToolResult, TextContent # 确保从 mcp.types 导入
from ..domain.models.user import User

# 假设 settings 和 get_..._api, User 等已定义
# from ..core.config import settings
# from ..dependencies import get_chat_service_api, get_knowledge_service_api, get_mcp_service_api, get_optional_current_user, get_conversation_service
# from ..domain.models import User
# from ..services import ChatService, KnowledgeService, ConversationService

# 定义 name 变量，通常是模块名
name = __name__ # 或者根据你的项目结构设置
logger = logging.getLogger(name)


class MCPService:
    """MCP服务，提供工具、提示和资源管理功能"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化MCP服务

        Args:
            config_path: MCP配置文件路径 (现在直接使用 servers.json)
        """
        self._initialized = False
        self._tools_cache = {}
        self.hub: Optional[MCPHub] = None # 初始化为 None

        # MCP服务器配置目录
        self.base_dir = os.path.join(os.getcwd(), "app", "data", "mcp")
        self.meta_dir = os.path.join(self.base_dir, "meta")
        self.config_dir = os.path.join(self.base_dir, "config")

        # 用户上下文目录
        self.user_contexts_dir = os.path.join(self.base_dir, "user_contexts")

        # 确保目录存在
        os.makedirs(self.meta_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.user_contexts_dir, exist_ok=True)

        # 服务器列表文件路径
        self.servers_file = os.path.join(self.meta_dir, "servers.json")

        # 将 servers.json 作为 MCPHub 的配置路径
        self.config_path = self.servers_file

        # 初始化服务器列表文件（如果不存在）
        if not os.path.exists(self.servers_file):
            self._save_servers([])

        logger.info("MCP服务已创建 (尚未初始化)")

    async def initialize(self) -> None:
        """初始化MCP服务，创建并初始化MCPHub实例"""
        if self._initialized:
            logger.warning("MCP服务已初始化，跳过重复初始化")
            return

        try:
            logger.info(f"正在初始化MCP服务，配置文件: {self.config_path}")
            # 创建 MCPHub 实例
            self.hub = MCPHub(config_path=self.config_path)

            # 初始化 MCPHub (连接服务器、发现功能等)
            # 添加错误处理，允许一些服务器初始化失败
            try:
                await self.hub.initialize() # MCPHub 自己的 initialize
            except Exception as e:
                # 检查是否是stdio相关的取消作用域错误
                # 这些通常在关闭时发生，初始化时可能表示更严重的问题，但我们暂时按原逻辑处理
                if "cancel scope" in str(e).lower():
                    logger.warning(f"MCP Hub 初始化期间出现非致命错误 (stdio cancel scope): {str(e)}")
                else:
                    # 其他类型的错误则记录并可能继续（取决于 hub.initialize 的设计）
                    logger.error(f"MCP Hub 初始化时发生错误: {str(e)}", exc_info=True)
                    # 根据需要决定是否抛出异常
                    # raise ServiceException(f"MCP Hub 初始化失败: {str(e)}") from e

            self._initialized = True
            logger.info("MCP服务初始化成功")
        except Exception as e:
            logger.error(f"MCP服务初始化失败: {str(e)}", exc_info=True)
            self.hub = None # 初始化失败，重置 hub
            raise ServiceException(f"MCP服务初始化失败: {str(e)}") from e

    async def _ensure_initialized(self) -> None:
        """确保MCP服务已初始化"""
        if not self._initialized or not self.hub:
            # 在某些场景下，可能希望自动初始化，但这通常应在应用启动时完成
            logger.warning("MCP服务尚未初始化或初始化失败。尝试重新初始化...")
            await self.initialize()
            if not self._initialized or not self.hub:
                 raise ServiceException("MCP服务未能成功初始化")


    async def get_tools(self, selected_servers: Optional[List[Dict[str, Any]]] = None) -> List[Tool]:
        """
        获取可用工具列表

        Args:
            selected_servers: mcp servers

        Returns:
            工具列表
        """
        await self._ensure_initialized()
        assert self.hub is not None # _ensure_initialized 应该保证这一点

        try:
            # # 缓存键
            # cache_key = "tools_all"

            # # 检查缓存 (简单实现，可能需要更复杂的缓存策略)
            # if cache_key in self._tools_cache:
            #      # logger.debug(f"命中工具缓存: {cache_key}")
            #      return self._tools_cache[cache_key]

            # 从 Hub 获取工具列表
            # 注意：MCPHub 的 list_tools 返回的是一个包含 .tools 属性的对象
            result = await self.hub.list_tools()
            mcp_tools = result.tools # 这是原始 MCP 工具列表

            # 转换为应用内部的 Tool 模型
            converted_tools = []
            for tool in mcp_tools:
                parameters = []
                # 检查 inputSchema 是否存在且为字典
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
                            enum=param_info.get("enum") # pydantic 会处理 None
                        ))

                # 获取服务器名称，如果存在
                server_name = tool.name.split("/")[0]
                # 创建唯一的工具ID
                tool_id = f"{server_name}/{tool.name}" if server_name else tool.name

                tool_model = Tool(
                    id=tool_id,
                    name=tool.name,
                    description=tool.description,
                    server=server_name,
                    category=getattr(tool, "category", "general"),
                    parameters=parameters
                )

                for server in selected_servers:
                    if server.get("name") == server_name:
                        converted_tools.append(tool_model)

            # 更新缓存
            # self._tools_cache[cache_key] = converted_tools
            # logger.debug(f"已缓存工具: {cache_key}, 数量: {len(converted_tools)}")

            return converted_tools

        except Exception as e:
            logger.error(f"获取工具列表失败: {str(e)}", exc_info=True)
            raise ServiceException(f"获取工具列表失败: {str(e)}") from e

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """
        调用工具 (简化版，主要委托给 _safe_call_tool)

        Args:
            tool_name: 工具名称 (可能是 server/tool 格式)
            arguments: 工具参数

        Returns:
            工具调用结果 (CallToolResult 对象)

        Raises:
            NotFoundException: 如果工具不存在 (由 mcp-py 内部处理)
            ServiceException: 如果调用失败
        """
        await self._ensure_initialized()
        logger.info(f"准备调用工具: {tool_name}")
        # 直接调用 _safe_call_tool，它会使用 self.hub
        result = await self._safe_call_tool(tool_name, arguments)

        # _safe_call_tool 已经处理了基本错误并返回 CallToolResult
        # 这里可以根据需要添加额外的检查或日志记录
        if getattr(result, 'isError', False):
             logger.warning(f"工具调用返回错误: {tool_name} - {result.content}")
             # 不再抛出异常，让调用者处理 CallToolResult 中的错误状态
             # error_msg = next((content.text for content in result.content if getattr(content, 'type', None) == 'text'), "未知错误")
             # raise ServiceException(f"工具调用失败: {error_msg}")

        return result


    async def call_tool_on_server(self, server_id: str, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """
        在特定服务器上调用工具

        Args:
            server_id: 服务器ID
            tool_name: 工具名称 (不含服务器前缀)
            arguments: 工具参数

        Returns:
            工具调用结果 (CallToolResult 对象)

        Raises:
            NotFoundException: 如果服务器不存在
            ServiceException: 如果调用失败
        """
        await self._ensure_initialized()

        # 检查服务器是否存在 (通过配置)
        server = self.get_server(server_id)
        if not server:
            raise NotFoundException(f"MCP服务器 {server_id} 不存在或未配置")

        logger.info(f"准备在服务器 {server_id} 上调用工具: {tool_name}")

        # 构造完整的工具名称
        qualified_tool_name = f"{server_id}/{tool_name}"

        # 调用通用的 call_tool 方法
        return await self.call_tool(qualified_tool_name, arguments)


    async def get_prompts(self, server_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取提示模板列表

        Args:
            server_name: 可选的服务器名称过滤器

        Returns:
            提示模板列表 (格式由 MCPHub 定义)
        """
        await self._ensure_initialized()
        assert self.hub is not None
        try:
            logger.info(f"获取提示模板，服务器: {server_name or '所有'}")
            # MCPHub 的 list_prompts 返回值格式可能需要确认
            result = await self.hub.list_prompts(server_name)
            return result # 直接返回 Hub 的结果
        except Exception as e:
            logger.error(f"获取提示模板失败: {str(e)}", exc_info=True)
            raise ServiceException(f"获取提示模板失败: {str(e)}") from e

    async def get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, str]] = None) -> str:
        """
        获取并应用提示模板

        Args:
            prompt_name: 提示模板名称 (可以是 server/prompt 格式)
            arguments: 提示模板参数

        Returns:
            应用参数后的提示文本

        Raises:
            NotFoundException: 如果提示模板不存在 (由 mcp-py 处理)
            ServiceException: 如果获取失败
        """
        await self._ensure_initialized()
        assert self.hub is not None
        try:
            logger.info(f"获取提示模板: {prompt_name}")
            result = await self.hub.get_prompt(prompt_name, arguments)
            # 假设 GetPromptResult 有 content 属性
            return result.content
        except Exception as e:
            # TODO: 区分 NotFound 和其他错误
            logger.error(f"获取提示模板 {prompt_name} 失败: {str(e)}", exc_info=True)
            raise ServiceException(f"获取提示模板失败: {str(e)}") from e

    async def get_resources(self, server_name: Optional[str] = None) -> Dict[str, List[str]]:
        """
        获取资源列表

        Args:
            server_name: 可选的服务器名称过滤器

        Returns:
            资源列表 (格式由 MCPHub 定义)
        """
        await self._ensure_initialized()
        assert self.hub is not None
        try:
            logger.info(f"获取资源列表，服务器: {server_name or '所有'}")
            result = await self.hub.list_resources(server_name)
            return result # 直接返回 Hub 的结果
        except Exception as e:
            logger.error(f"获取资源列表失败: {str(e)}", exc_info=True)
            raise ServiceException(f"获取资源列表失败: {str(e)}") from e

    async def get_resource(self, resource_uri: str) -> Union[str, bytes, Dict[str, Any]]:
        """
        获取资源内容

        Args:
            resource_uri: 资源URI (可以是 server/uri 格式)

        Returns:
            资源内容 (格式由 MCPHub 定义)

        Raises:
            NotFoundException: 如果资源不存在 (由 mcp-py 处理)
            ServiceException: 如果获取失败
        """
        await self._ensure_initialized()
        assert self.hub is not None
        try:
            logger.info(f"获取资源: {resource_uri}")
            result = await self.hub.get_resource(resource_uri)
            # 假设 ReadResourceResult 有 content 属性
            return result.content
        except Exception as e:
            # TODO: 区分 NotFound 和其他错误
            logger.error(f"获取资源 {resource_uri} 失败: {str(e)}", exc_info=True)
            raise ServiceException(f"获取资源失败: {str(e)}") from e

    async def shutdown(self) -> None:
        """关闭MCP服务，关闭MCP Hub连接"""
        if self.hub and self._initialized:
            try:
                logger.info("正在关闭MCP服务 (调用 MCP Hub shutdown)")
                await self.hub.shutdown() # 调用 MCPHub 的关闭方法
                logger.info("MCP Hub 已关闭")
            except RuntimeError as e:
                # 尝试捕获并记录特定的运行时错误，例如在不同任务中退出 cancel scope
                if "cancel scope" in str(e).lower():
                    logger.warning(f"MCP Hub 关闭期间发生已知的运行时错误 (可能与 anyio/stdio 有关): {str(e)}")
                else:
                    logger.error(f"关闭 MCP Hub 时发生意外的运行时错误: {str(e)}", exc_info=True)
                    # 选择不重新抛出以允许其他关闭操作继续
            except Exception as e:
                logger.error(f"关闭 MCP Hub 时发生错误: {str(e)}", exc_info=True)
                # 不抛出异常，以免影响其他关闭操作
            finally:
                self._initialized = False
                self.hub = None
                logger.info("MCP服务状态已重置为未初始化")
        elif not self._initialized:
             logger.info("MCP服务未初始化或已关闭，无需执行关闭操作")
        else:
             logger.warning("MCP服务处于未初始化状态，但 Hub 实例存在？进行清理。")
             self._initialized = False
             self.hub = None


    async def process_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        处理多个工具调用 (顺序执行)

        Args:
            tool_calls: 工具调用列表，每个字典包含 'name' 和 'arguments'

        Returns:
            工具调用结果列表，每个字典包含 'tool_name', 'arguments', 'result' (CallToolResult) 或 'error'
        """
        await self._ensure_initialized()

        results = []
        for call in tool_calls:
            tool_name = call.get("name") # 假设格式是 { "name": "...", "arguments": {...} }
            arguments = call.get("arguments", {})

            if not tool_name:
                logger.warning(f"跳过无效的工具调用请求: {call}")
                results.append({
                    "tool_name": "未知工具",
                    "error": "工具名称缺失"
                })
                continue

            try:
                # 调用 _safe_call_tool 来执行单个调用
                result = await self._safe_call_tool(tool_name, arguments)
                results.append({
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "result": result # result 是 CallToolResult 对象
                })
            except Exception as e:
                # _safe_call_tool 应该捕获大部分错误并返回 CallToolResult(isError=True)
                # 但以防万一有其他类型的异常逃逸
                logger.error(f"处理工具调用 {tool_name} 时发生意外错误: {str(e)}", exc_info=True)
                results.append({
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "error": f"意外错误: {str(e)}"
                })

        return results

    async def _safe_call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """
        安全地调用工具，使用应用的单例 MCPHub，处理异常并返回 CallToolResult。

        Args:
            tool_name: 工具名称 (可以是 server/tool 格式)
            arguments: 工具参数

        Returns:
            工具调用结果 (CallToolResult 对象)，即使发生错误也会返回此类型并标记 isError=True
        """
        # 不再创建临时 Hub！ 确保主 Hub 已初始化
        await self._ensure_initialized()
        assert self.hub is not None

        try:
            # 移除用户上下文注入逻辑，因为 hub.call_tool 不直接支持
            # 上下文管理需要通过 session 变量或其他方式实现，目前超出此函数范围
            # user_context = arguments.pop("_user_context", None) # 移除这行

            logger.info(f"通过主 Hub 调用工具: {tool_name}")
            # 使用应用的单例 Hub 调用工具
            result: CallToolResult = await self.hub.call_tool(tool_name, arguments)

            # 移除从临时 Hub 获取更新后上下文的逻辑
            # if user_context is not None:
            #     # ... (移除获取 session variable 的代码) ...
            #     result.user_context = new_context # 移除这行

            # 检查 mcp-py 返回的结果是否已经是错误
            if getattr(result, 'isError', False):
                 logger.warning(f"工具 {tool_name} 调用返回错误状态: {result.content}")

            return result

        except Exception as e:
            # 捕获调用 self.hub.call_tool 时可能发生的任何异常
            error_message = f"调用工具 {tool_name} 时发生 MCP 服务层错误: {str(e)}"
            logger.error(error_message, exc_info=True)

            # 创建一个表示错误的 CallToolResult 对象
            return CallToolResult(
                isError=True,
                content=[TextContent(text=error_message, type="text")]
            )

    # --- 服务器管理方法 (基本保持不变，注意日志和错误处理) ---

    def get_all_servers(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """获取所有MCP服务器"""
        servers = self._load_servers()
        if active_only:
            # 确保 active 键存在，不存在时默认为 True
            return [s for s in servers if s.get("active", True)]
        return servers

    def get_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        """获取单个MCP服务器配置"""
        servers = self._load_servers()
        for server in servers:
            if server.get("id") == server_id: # 使用 .get() 避免 KeyError
                return server
        return None

    def add_server(self, server_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加新的MCP服务器配置"""
        if "name" not in server_data:
             raise ValueError("服务器名称 'name' 是必需的")

        servers = self._load_servers()

        # 检查URL是否已存在 (仅当URL非空时检查)
        new_url = server_data.get("url")
        if new_url:
            for server in servers:
                if server.get("url") == new_url:
                    raise ValueError(f"具有相同URL '{new_url}' 的服务器已存在 (ID: {server.get('id')})")

        # 确保 args 是列表
        if "args" in server_data and not isinstance(server_data["args"], list):
            if isinstance(server_data["args"], str):
                server_data["args"] = server_data["args"].split()
            else:
                logger.warning(f"服务器 {server_data['name']} 的 'args' 类型无效，将设置为空列表。")
                server_data["args"] = []
        elif "args" not in server_data:
             server_data["args"] = [] # 确保存在

        # 确保 env 是字典
        if "env" in server_data and not isinstance(server_data["env"], dict):
            if isinstance(server_data["env"], str):
                try:
                    # 尝试更健壮地解析字符串格式的环境变量
                    env_dict = {}
                    for line in server_data["env"].strip().split("\n"):
                        line = line.strip()
                        if line and "=" in line:
                             key, value = line.split("=", 1)
                             env_dict[key.strip()] = value.strip()
                    server_data["env"] = env_dict
                except Exception as e:
                    logger.warning(f"解析服务器 {server_data['name']} 的 'env' 字符串失败: {e}. 将设置为空字典。")
                    server_data["env"] = {}
            else:
                logger.warning(f"服务器 {server_data['name']} 的 'env' 类型无效，将设置为空字典。")
                server_data["env"] = {}
        elif "env" not in server_data:
             server_data["env"] = {} # 确保存在

        now = datetime.now().isoformat()
        new_server = {
            "id": server_data.get("id") or str(uuid.uuid4()),
            "name": server_data["name"],
            "url": server_data.get("url"), # 可以是 None 或 ""
            "command": server_data.get("command", "npx"), # 默认为 npx
            "args": server_data.get("args"), # 已经处理过
            "env": server_data.get("env"),   # 已经处理过
            "transport": server_data.get("transport", "stdio"), # 添加 transport 字段
            "description": server_data.get("description", ""),
            "active": server_data.get("active", True),
            "created_at": now,
            "updated_at": now
        }

        servers.append(new_server)
        self._save_servers(servers)
        logger.info(f"已添加MCP服务器: {new_server['name']} (ID: {new_server['id']})")

        # 清理缓存
        self._tools_cache = {}
        self._initialized = False
        self.initialize()

        return new_server

    def update_server(self, server_id: str, server_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新MCP服务器配置"""
        servers = self._load_servers()
        server_found = False
        updated_server = None

        # 参数和环境的类型处理逻辑（与 add_server 类似）
        if "args" in server_data and not isinstance(server_data["args"], list):
            if isinstance(server_data["args"], str): server_data["args"] = server_data["args"].split()
            else: server_data["args"] = [] # 忽略无效类型或设为默认
        if "env" in server_data and not isinstance(server_data["env"], dict):
            if isinstance(server_data["env"], str):
                env_dict = {}
                for line in server_data["env"].strip().split("\n"):
                    if line and "=" in line:
                        key, value = line.split("=", 1)
                        env_dict[key.strip()] = value.strip()
                server_data["env"] = env_dict
            else: server_data["env"] = {} # 忽略无效类型或设为默认

        for i, server in enumerate(servers):
            if server.get("id") == server_id:
                # 更新字段，只更新 server_data 中存在的键
                original_name = server.get("name", "未知")
                for key, value in server_data.items():
                     # 不允许更新 id, created_at
                     if key not in ["id", "created_at"]:
                         servers[i][key] = value
                servers[i]["updated_at"] = datetime.now().isoformat()

                self._save_servers(servers)
                updated_server = servers[i]
                server_found = True
                logger.info(f"已更新MCP服务器: {updated_server.get('name', original_name)} (ID: {server_id})")
                break

        if not server_found:
            logger.warning(f"尝试更新服务器失败，未找到ID: {server_id}")
            return None
        
        # 清理缓存
        self._tools_cache = {}

        self._initialized = False
        self.initialize()

        return updated_server


    def delete_server(self, server_id: str) -> bool:
        """删除MCP服务器配置"""
        servers = self._load_servers()
        original_length = len(servers)
        servers = [s for s in servers if s.get("id") != server_id]

        if len(servers) < original_length:
            self._save_servers(servers)
            logger.info(f"已删除MCP服务器，ID: {server_id}")
             # 清理缓存
            self._tools_cache = {}
            self._initialized = False
            self.initialize()
            return True
        else:
            logger.warning(f"尝试删除服务器失败，未找到ID: {server_id}")
            
            return False

    def _load_servers(self) -> List[Dict[str, Any]]:
        """加载服务器列表 (改进错误处理和日志)"""
        if not os.path.exists(self.servers_file):
            logger.warning(f"服务器配置文件不存在: {self.servers_file}，返回空列表。")
            return []

        try:
            with open(self.servers_file, "r", encoding="utf-8") as f:
                raw_content = f.read()
                if not raw_content.strip():
                     logger.warning(f"服务器配置文件为空: {self.servers_file}")
                     return []

                # logger.debug(f"加载服务器配置原始内容: {raw_content[:500]}...") # 截断长内容
                data = json.loads(raw_content)

            # logger.debug(f"JSON解析结果类型: {type(data)}")

            # 健壮地获取服务器列表
            if isinstance(data, dict):
                servers = data.get("servers")
                if servers is None:
                    # 尝试查找其他可能的键名 (忽略大小写)
                    for key in data.keys():
                        if key.lower() == "servers":
                            servers = data[key]
                            logger.warning(f"找到了大小写不同的服务器键: '{key}'")
                            break
            elif isinstance(data, list):
                 # 如果顶层直接是列表，也接受
                 servers = data
                 logger.warning(f"服务器配置文件顶层是列表，而非预期的字典结构 {{'servers': [...]}}")
            else:
                 logger.error(f"服务器配置文件格式无效，预期为字典或列表，实际为: {type(data)}")
                 return []

            if not isinstance(servers, list):
                logger.error(f"配置文件中 'servers' 键的值不是列表，实际为: {type(servers)}")
                return []

            # logger.info(f"成功加载 {len(servers)} 个服务器配置")
            return servers

        except json.JSONDecodeError as e:
            logger.error(f"加载MCP服务器列表失败：JSON解析错误 - {e}", exc_info=True)
            logger.error(f"错误发生在文件: {self.servers_file}")
            return []
        except Exception as e:
            logger.error(f"加载MCP服务器列表时发生未知错误: {e}", exc_info=True)
            return []

    def _save_servers(self, servers: List[Dict[str, Any]]) -> None:
        """保存服务器列表 (改进错误处理)"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.servers_file), exist_ok=True)
            with open(self.servers_file, "w", encoding="utf-8") as f:
                # 保存为 {"servers": [...]} 结构
                json.dump({"servers": servers}, f, ensure_ascii=False, indent=2)
            # logger.debug(f"已保存 {len(servers)} 个服务器配置到 {self.servers_file}")
        except IOError as e:
            logger.error(f"保存MCP服务器列表到文件时发生IO错误: {e}", exc_info=True)
        except TypeError as e:
             logger.error(f"保存MCP服务器列表时发生类型错误 (数据可能无法序列化为JSON): {e}", exc_info=True)
        except Exception as e:
            logger.error(f"保存MCP服务器列表时发生未知错误: {e}", exc_info=True)


    # --- 用户上下文管理 (基本保持不变) ---

    def _get_user_context_path(self, user_id: str) -> str:
        """获取用户上下文文件路径"""
        # 确保 user_id 是有效的文件名部分 (例如，移除路径分隔符)
        safe_user_id = "".join(c for c in str(user_id) if c.isalnum() or c in ('-', '_')).rstrip()
        if not safe_user_id:
            raise ValueError("无效的用户ID，无法生成上下文路径")
        return os.path.join(self.user_contexts_dir, f"context_{safe_user_id}.json")

    def save_user_context(self, user_id: str, context_data: Dict[str, Any]) -> bool:
        """保存用户MCP上下文"""
        try:
            context_path = self._get_user_context_path(user_id)
            os.makedirs(os.path.dirname(context_path), exist_ok=True)
            with open(context_path, "w", encoding="utf-8") as f:
                json.dump(context_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"已保存用户 {user_id} 的MCP上下文")
            return True
        except (IOError, TypeError, ValueError) as e:
            logger.error(f"保存用户 {user_id} MCP上下文失败: {e}", exc_info=True)
            return False
        except Exception as e:
             logger.error(f"保存用户 {user_id} MCP上下文时发生未知错误: {e}", exc_info=True)
             return False

    def load_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """加载用户MCP上下文"""
        try:
            context_path = self._get_user_context_path(user_id)
            if not os.path.exists(context_path):
                # logger.debug(f"用户 {user_id} 的MCP上下文文件不存在: {context_path}")
                return None

            with open(context_path, "r", encoding="utf-8") as f:
                context = json.load(f)
            # logger.debug(f"已加载用户 {user_id} 的MCP上下文")
            return context
        except (IOError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"加载用户 {user_id} MCP上下文失败: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"加载用户 {user_id} MCP上下文时发生未知错误: {e}", exc_info=True)
            return None


    def delete_user_context(self, user_id: str) -> bool:
        """删除用户MCP上下文"""
        try:
            context_path = self._get_user_context_path(user_id)
            if not os.path.exists(context_path):
                logger.debug(f"尝试删除用户 {user_id} 上下文，但文件已不存在: {context_path}")
                return True # 认为删除成功

            os.remove(context_path)
            logger.info(f"已删除用户 {user_id} 的MCP上下文文件: {context_path}")
            return True
        except (IOError, ValueError, OSError) as e:
            logger.error(f"删除用户 {user_id} MCP上下文失败: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"删除用户 {user_id} MCP上下文时发生未知错误: {e}", exc_info=True)
            return False

    async def call_tool_for_user(self, user_id: str, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """
        为特定用户调用工具，尝试加载上下文，但目前无法保证上下文更新和保存。

        Args:
            user_id: 用户ID
            tool_name: 工具名称 (可以是 server/tool 格式)
            arguments: 工具参数

        Returns:
            工具调用结果 (CallToolResult)

        Raises:
            ServiceException: 如果调用失败
        """
        await self._ensure_initialized()

        logger.info(f"准备为用户 {user_id} 调用工具: {tool_name}")

        # 1. 加载用户上下文 (如果存在)
        user_context = self.load_user_context(user_id)
        if user_context:
            logger.debug(f"为用户 {user_id} 加载了上下文: {list(user_context.keys())}")
            # !! 重要: 当前版本的 mcp-py Hub.call_tool 不支持直接传递上下文。
            #    上下文需要由工具自身通过某种机制（如 session 变量）来管理。
            #    这里的 user_context 目前仅用于日志记录或未来可能的扩展。
            #    我们不能像之前的 _safe_call_tool 那样将它注入 arguments.
            # arguments["_user_context"] = user_context # 不要这样做！
            pass
        else:
            logger.debug(f"用户 {user_id} 没有找到可加载的MCP上下文")

        # 2. 调用工具 (通过 _safe_call_tool 使用主 Hub)
        # 注意：移除了将 user_context 注入 arguments 的步骤
        result = await self._safe_call_tool(tool_name, arguments)

        # 3. 处理结果
        if getattr(result, 'isError', False):
            logger.warning(f"为用户 {user_id} 调用工具 {tool_name} 返回错误: {result.content}")
            # 不抛出异常，返回包含错误的 CallToolResult
        else:
            logger.info(f"为用户 {user_id} 调用工具 {tool_name} 成功")

        # 4. 保存上下文 (已移除)
        # !! 重要: 由于无法从 CallToolResult 获取更新后的上下文，
        #    并且 hub.call_tool 不返回它，我们无法在这里可靠地保存更新。
        #    上下文的持久化需要 mcp-py 或工具本身支持。
        # if hasattr(result, "user_context") and result.user_context:
        #     logger.warning("call_tool_for_user: result 包含 user_context，但这部分逻辑已禁用。")
        #     # self.save_user_context(user_id, result.user_context)

        # 5. 返回结果
        return result


# --- Pydantic 模型 (保持不变) ---
class MCPServerCreate(BaseModel):
    """MCP服务器创建模型"""
    name: str
    url: Optional[str] = None
    command: str = "npx"
    # 确保类型正确，FastAPI 会自动处理 JSON 到 list/dict 的转换
    args: List[str] = []
    env: Dict[str, str] = {}
    transport: str = "stdio" # 添加 transport 字段
    description: Optional[str] = ""
    active: bool = True