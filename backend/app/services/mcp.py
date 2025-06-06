"""
MCP服务 - 提供MCP服务器管理和协议交互功能

职责分离：
1. MCPService: 管理服务器配置（CRUD）+ 协调 Hub 操作
2. MCPHub: 实际的 MCP 协议通信（list_tools, call_tool, health check 等）
"""
import uuid
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.service import BaseService
from ..core.logging import get_logger
from ..core.errors import (
    NotFoundException, ServiceException, AuthorizationException, 
    ConflictException, ValidationException
)
from ..domain.models.user import User
from ..domain.models.mcp import (
    MCPServer, MCPServerCreate, MCPServerUpdate, MCPServerResponse,
    MCPServerStatus, MCPTool, MCPResource, MCPPrompt, MCPToolCall, 
    MCPToolResult, MCPConnectionTest, MCPTransportType, MCPCapability
)
from ..domain.schemas.tools import Tool, ToolParameter
from ..repositories.mcp import MCPRepository
from ..lib.mcp import MCPHub, ConfigProvider
from ..core.database import get_session

logger = get_logger(__name__)


class MCPService(BaseService[MCPServer, MCPRepository]):
    """
    MCP服务 - 管理服务器配置并协调 Hub 操作
    
    职责：
    1. 服务器配置的 CRUD 操作
    2. 用户 Hub 的生命周期管理
    3. 协调 Hub 进行实际的 MCP 协议操作
    """
    
    def __init__(self, session: AsyncSession):
        """初始化MCP服务"""
        repository = MCPRepository(session)
        super().__init__(repository)
        
        self.session = session
        # 🔥 使用全局连接池，不再自己管理Hub
        from ..lib.mcp.connection_pool import get_connection_pool
        self.connection_pool = get_connection_pool()
        
        logger.info("MCP服务初始化 - 使用全局连接池")
    
    def get_entity_name(self) -> str:
        """获取实体名称"""
        return "MCP服务器"
    
    # ==========================================
    # Hub 管理 - 通过连接池
    # ==========================================
    
    async def _get_user_hub(self, user_id: str) -> Optional[MCPHub]:
        """获取用户的 MCP Hub，通过连接池"""
        # 获取用户的服务器配置
        servers = await self.repository.find_by_user_id(user_id, active_only=True)
        
        # 通过连接池获取或创建Hub
        if servers:
            return await self.connection_pool.get_or_create_user_hub(user_id, servers)
        else:
            return await self.connection_pool.get_user_hub(user_id)
    
    def get_hub_status(self, user_id: str) -> str:
        """获取 Hub 连接状态"""
        return self.connection_pool.get_connection_status(user_id)
    
    def is_hub_ready(self, user_id: str) -> bool:
        """检查 Hub 是否已准备就绪"""
        return self.connection_pool.is_connected(user_id)
    
    async def _refresh_user_hub(self, user_id: str) -> None:
        """刷新用户的 MCP Hub（重新加载配置）"""
        servers = await self.repository.find_by_user_id(user_id, active_only=True)
        if servers:
            await self.connection_pool.update_user_hub_servers(user_id, servers)
        else:
            await self.connection_pool.remove_user_hub(user_id)
    
    async def _update_hub_server(self, user_id: str, server: MCPServer, operation: str) -> None:
        """更新Hub中的服务器配置 - 使用单服务器操作避免影响其他服务器
        
        Args:
            user_id: 用户ID
            server: 服务器配置
            operation: 操作类型 ('add', 'update', 'remove')
        """
        try:
            # 🔧 修复：确保Hub存在，如果不存在则创建
            hub = await self.connection_pool.get_user_hub_wait(user_id, timeout=5.0)
            if not hub:
                # 🔥 修复：第一次创建服务器时，主动创建Hub
                logger.info(f"Hub未初始化，为用户 {user_id} 创建新Hub以应用操作 ({operation}): {server.name}")
                servers = await self.repository.find_by_user_id(user_id, active_only=True)
                hub = await self.connection_pool.create_user_hub(user_id, servers)
                if not hub:
                    logger.error(f"创建Hub失败，无法应用操作 ({operation}): {server.name}")
                return
            
            # 🔧 使用Hub的单服务器操作方法，避免影响其他服务器
            if operation == 'add':
                # 🔥 修复：直接添加服务器配置到ConfigProvider，不调用reload()
                server_config = {
                    "name": server.name,
                    "transport": server.transport,
                    "command": server.command,
                    "args": self._normalize_args(server.args),  # 🔥 修复：标准化args格式
                    "env": server.env or {},
                    "url": server.url,
                    "active": server.active
                }
                hub.config_provider.add_or_update_server(server_config)
                success = await hub.add_server(server.name)
                logger.info(f"{'成功' if success else '失败'}添加服务器到Hub: {server.name}")
                
            elif operation == 'update':
                # 🔥 修复：直接更新服务器配置到ConfigProvider
                server_config = {
                    "name": server.name,
                    "transport": server.transport,
                    "command": server.command,
                    "args": self._normalize_args(server.args),  # 🔥 修复：标准化args格式
                    "env": server.env or {},
                    "url": server.url,
                    "active": server.active
                }
                hub.config_provider.add_or_update_server(server_config)
                success = await hub.update_server(server.name)
                logger.info(f"{'成功' if success else '失败'}更新Hub中的服务器: {server.name}")
                
            elif operation == 'remove':
                # 先从Hub移除服务器，再从ConfigProvider移除配置
                success = await hub.remove_server(server.name)
                hub.config_provider.remove_server_config(server.name)
                logger.info(f"{'成功' if success else '失败'}从Hub移除服务器: {server.name}")
                
        except Exception as e:
            logger.error(f"更新Hub服务器配置失败 ({operation}): {str(e)}")
            # 只有在严重错误时才断开连接
            if "timeout" in str(e).lower() or "connection" in str(e).lower():
                logger.warning(f"由于连接问题，将重置用户 {user_id} 的Hub")
                await self.connection_pool.disconnect_user(user_id)
    
    async def cleanup_user_connections(self, user_id: str) -> None:
        """清理用户的所有连接"""
        await self.connection_pool.disconnect_user(user_id)
    

    
    # ==========================================
    # 服务器配置管理 - CRUD 操作
    # ==========================================
    
    async def create_server(self, user_id: str, server_data: MCPServerCreate) -> MCPServerResponse:
        """创建MCP服务器配置"""
        # 检查名称是否已存在
        existing_server = await self.repository.find_by_name(server_data.name, user_id)
        if existing_server:
            raise ConflictException(f"服务器名称 '{server_data.name}' 已存在")
        
        # 验证配置
        self._validate_server_config(server_data)
        
        # 创建服务器数据
        server_dict = server_data.model_dump()
        server_dict.update({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "status": "inactive",
            "capabilities": [],
            "created_at": datetime.now()
        })
        
        # 保存到数据库
        server = await self.repository.create(server_dict)
        
        # 重新加载Hub配置（包含新服务器）
        await self._update_hub_server(user_id, server, 'add')
        
        # 如果设置为自动启动，尝试连接
        # if server_data.auto_start:
            # asyncio.create_task(self._auto_connect_server(server.id, user_id))
        
        logger.info(f"创建MCP服务器成功: {server.name} (用户: {user_id})")
        return MCPServerResponse.model_validate(server.to_dict())
    
    async def update_server(self, server_id: str, user_id: str, update_data: MCPServerUpdate) -> MCPServerResponse:
        """更新MCP服务器配置"""
        # 检查服务器是否存在且属于用户
        server = await self.repository.get_user_server(server_id, user_id)
        if not server:
            raise NotFoundException(f"MCP服务器 {server_id} 不存在")
        
        # 检查名称冲突
        if update_data.name and update_data.name != server.name:
            existing = await self.repository.find_by_name(update_data.name, user_id)
            if existing and existing.id != server_id:
                raise ConflictException(f"服务器名称 '{update_data.name}' 已存在")
        
        # 准备更新数据
        update_dict = {k: v for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None}
        update_dict["updated_at"] = datetime.now()
        
        # 更新数据库
        updated_server = await self.repository.update(server_id, update_dict)
        if not updated_server:
            raise ServiceException("更新服务器失败")
        
        # 重新加载Hub配置（包含更新的服务器）
        await self._update_hub_server(user_id, updated_server, 'update')
        
        logger.info(f"更新MCP服务器成功: {server_id}")
        return MCPServerResponse.model_validate(updated_server.to_dict())
    
    async def delete_server(self, server_id: str, user_id: str) -> bool:
        """删除MCP服务器配置"""
        # 检查服务器是否存在且属于用户
        server = await self.repository.get_user_server(server_id, user_id)
        if not server:
            raise NotFoundException(f"MCP服务器 {server_id} 不存在")
        
        # 先从Hub中移除（在删除数据库记录之前）
        await self._update_hub_server(user_id, server, 'remove')
        
        # 删除数据库记录
        success = await self.repository.delete(server_id)
        if success:
            logger.info(f"删除MCP服务器成功: {server_id}")
        else:
            # 如果数据库删除失败，需要重新加载Hub以恢复状态
            logger.error(f"数据库删除失败，重新加载Hub以恢复状态: {server_id}")
            await self._refresh_user_hub(user_id)
        
        return success
    
    async def get_server(self, server_id: str, user_id: str) -> MCPServerResponse:
        """获取MCP服务器详情"""
        server = await self.repository.get_user_server(server_id, user_id)
        if not server:
            raise NotFoundException(f"MCP服务器 {server_id} 不存在")
        
        return MCPServerResponse.model_validate(server.to_dict())
    
    async def list_servers(self, user_id: str, active_only: bool = False) -> List[MCPServerResponse]:
        """获取用户的MCP服务器列表"""
        servers = await self.repository.find_by_user_id(user_id, active_only)
        return [MCPServerResponse.model_validate(server.to_dict()) for server in servers]
    
    # ==========================================
    # 服务器状态和健康检查 - 通过 Hub 实现
    # ==========================================
    
    async def get_server_statuses(self, user_id: str) -> List[MCPServerStatus]:
        """获取用户所有MCP服务器状态"""
        try:
            # 获取用户所有服务器
            servers = await self.repository.find_by_user_id(user_id)
            if not servers:
                return []
            
            # 获取用户Hub
            hub = await self._get_user_hub(user_id)
            if not hub:
                # 🔥 改进：Hub未初始化时不显示错误信息
                return [
                    MCPServerStatus(
                        server_id=server.id,
                        name=server.name,
                        status="inactive",
                        connected=False,
                        healthy=False,
                        error_message=None,  # 不显示"Hub未初始化"
                        capabilities=[]
                    ) for server in servers
                ]
            
            # 🚀 并行获取所有服务器的状态
            async def get_single_server_status(server: MCPServer) -> MCPServerStatus:
                """获取单个服务器状态的辅助函数"""
                try:
                    return await self._get_server_status_via_hub(server, hub)
                except Exception as e:
                        # 单个服务器状态获取失败不影响其他服务器
                        logger.error(f"获取服务器 {server.name} 状态失败: {e}")
                        return MCPServerStatus(
                            server_id=server.id,
                            name=server.name,
                            status="error",
                            connected=False,
                            healthy=False,
                            error_message=str(e),
                            capabilities=[]
                        )
            
            # 并行执行所有状态检查
            statuses = await asyncio.gather(
                *[get_single_server_status(server) for server in servers],
                return_exceptions=False  # 异常已在内部处理
            )
            
            return statuses
        except Exception as e:
            logger.error(f"获取用户服务器状态失败: {e}")
            return []

    async def get_server_status(self, server_id: str, user_id: str) -> MCPServerStatus:
        """获取单个服务器的状态"""
        try:
            # 获取服务器信息
            server = await self.repository.get_user_server(server_id, user_id)
            if not server:
                raise NotFoundException(f"MCP服务器 {server_id} 不存在")
            
            # 获取用户Hub
            hub = await self._get_user_hub(user_id)
            if not hub:
                # 🔥 改进：Hub未初始化时不显示错误信息
                return MCPServerStatus(
                    server_id=server.id,
                    name=server.name,
                    status="inactive",
                    connected=False,
                    healthy=False,
                    error_message=None,  # 不显示"Hub未初始化"，避免困惑用户
                    capabilities=[]
                )
            
            # 获取服务器状态
            return await self._get_server_status_via_hub(server, hub)
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"获取服务器 {server_id} 状态失败: {e}")
            # 返回错误状态而不是抛出异常
            return MCPServerStatus(
                server_id=server.id,
                name="未知",
                status="error",
                connected=False,
                healthy=False,
                error_message=str(e),
                capabilities=[]
            )
    
    async def get_connected_server_statuses(self, user_id: str) -> List[MCPServerStatus]:
        """获取用户已初始化且连接的服务器状态（用于聊天场景）"""
        # 检查Hub是否已初始化
        if not self.is_hub_ready(user_id):
            logger.info(f"用户 {user_id} 的 MCP Hub 未就绪，返回空状态列表")
            return []
        
        try:
            hub = await self._get_user_hub(user_id)
            if not hub:
                return []
            
            # 只获取活跃的服务器
            servers = await self.repository.find_by_user_id(user_id, active_only=True)
            
            # 🚀 并行获取所有服务器状态
            async def get_server_status_if_connected(server: MCPServer) -> Optional[MCPServerStatus]:
                """获取服务器状态，只返回已连接的"""
                try:
                    status = await self._get_server_status_via_hub(server, hub)
                    # 只返回已连接且健康的服务器
                    if status.connected and status.healthy:
                            return status
                    return None
                except Exception as e:
                    logger.error(f"检查服务器 {server.name} 连接状态失败: {e}")
                    return None
            
            # 并行检查所有服务器
            status_results = await asyncio.gather(
                *[get_server_status_if_connected(server) for server in servers],
                return_exceptions=False
            )
            
            # 过滤掉None值
            connected_statuses = [status for status in status_results if status is not None]
            
            logger.info(f"用户 {user_id} 有 {len(connected_statuses)} 个已连接的MCP服务器")
            return connected_statuses
            
        except Exception as e:
            logger.error(f"获取已连接服务器状态失败: {str(e)}")
            return []
    
    async def _get_server_status_via_hub(self, server: MCPServer, hub: MCPHub) -> MCPServerStatus:
        """通过Hub获取服务器实时状态"""
        try:
            # 检查服务器是否在Hub中连接
            is_connected = await self._check_server_health_via_hub(server.name, hub)
            
            # 🚀 并行获取服务器能力
            capabilities = []
            if is_connected:
                try:
                    # 并行检查所有能力
                    async def check_tools_capability():
                        try:
                            tools_result = await hub.list_tools()
                            if tools_result and tools_result.tools:
                                server_tools = [tool for tool in tools_result.tools 
                                              if tool.name.startswith(f"{server.name}/")]
                                if server_tools:
                                    return MCPCapability.TOOLS
                        except:
                            pass
                        return None
                    
                    async def check_resources_capability():
                        try:
                            resources_result = await hub.list_resources()
                            if resources_result:
                                return MCPCapability.RESOURCES
                        except:
                            pass
                        return None
                    
                    async def check_prompts_capability():
                        try:
                            prompts_result = await hub.list_prompts()
                            if prompts_result:
                                return MCPCapability.PROMPTS
                        except:
                            pass
                        return None
                    
                    # 并行执行能力检查
                    capability_results = await asyncio.gather(
                        check_tools_capability(),
                        check_resources_capability(),
                        check_prompts_capability(),
                        return_exceptions=False
                    )
                    
                    # 过滤掉None值
                    capabilities = [cap for cap in capability_results if cap is not None]
                except:
                    pass
            
            # 🔥 修复：改进状态逻辑，提供更好的用户体验
            if is_connected:
                actual_status = "active"
                error_message = None
            else:
                # 区分不同的未连接状态
                if server.last_error:
                    # 有错误记录，说明之前尝试过连接
                    actual_status = "error"
                    error_message = server.last_error
                else:
                    # 没有错误记录，可能是刚创建或未尝试连接
                    actual_status = "inactive"
                    error_message = None  # 🔥 不显示错误信息，避免误导用户
            
            # 获取等待者数量
            waiting_count = hub.get_server_waiting_count(server.name)
            
            return MCPServerStatus(
                server_id=server.id,
                name=server.name,
                status=actual_status,
                connected=is_connected,
                healthy=server.active and is_connected,
                last_ping=datetime.now() if is_connected else None,
                error_message=error_message,
                capabilities=capabilities,
                waiting_count=waiting_count
            )
        except Exception as e:
            logger.error(f"获取服务器 {server.name} 状态失败: {e}")
            
            # 🔥 改进：区分Hub未初始化和真正的错误
            if "Hub未初始化" in str(e) or "timeout" in str(e).lower():
                # Hub相关问题，不是服务器配置问题
                return MCPServerStatus(
                    server_id=server.id,
                    name=server.name,
                    status="inactive",
                    connected=False,
                    healthy=False,
                    error_message=None,  # 不显示技术错误信息
                    capabilities=[],
                    waiting_count=0
                )
            else:
                # 真正的配置或连接错误
                return MCPServerStatus(
                    server_id=server.id,
                    name=server.name,
                    status="error",
                    connected=False,
                    healthy=False,
                    error_message=str(e),
                    capabilities=[],
                    waiting_count=0
                )
    
    async def _check_server_health_via_hub(self, server_name: str, hub: MCPHub) -> bool:
        """通过 Hub 检查特定服务器的健康状态"""
        try:
            # 🔥 核心修复：检查特定服务器的连接状态，而不是整个Hub
            # 使用Hub的get_server_status方法检查特定服务器
            server_status = await hub.get_server_status(server_name)
            
            # 检查服务器是否在Hub中配置且已连接
            is_connected = server_status.get("connected", False)
            
            if not is_connected:
                return False
            
            # 🔥 进一步验证：尝试获取该服务器的工具来确认连接可用
            result = await hub.list_tools([server_name])  # 只检查指定服务器的工具
            
            # 检查是否返回了工具数据（即使是空列表也说明连接正常）
            return hasattr(result, 'tools')
            
        except Exception as e:
            # 任何异常都说明该服务器不健康
            self.logger.debug(f"服务器 {server_name} 健康检查失败: {e}")
            return False
    
    # ==========================================
    # 连接管理 - 通过 Hub 实现
    # ==========================================
    
    async def connect_server(self, server_id: str, user_id: str) -> MCPConnectionTest:
        """连接到MCP服务器 - 单服务器隔离版本"""
        server = await self.repository.get_user_server(server_id, user_id)
        if not server:
            raise NotFoundException(f"MCP服务器 {server_id} 不存在")
        
        if not server.active:
            raise ValidationException("服务器未启用")
        
        return await self._connect_single_server_isolated(server, user_id)
    
    async def _connect_single_server_isolated(self, server: MCPServer, user_id: str) -> MCPConnectionTest:
        """连接单个服务器 - 完全隔离版本，绝不影响其他服务器"""
        start_time = datetime.now()
        
        try:
            # 🔥 关键修复：获取用户的所有活跃服务器来创建Hub，确保完整配置
            logger.info(f"为用户 {user_id} 创建包含所有活跃服务器的Hub")
            all_active_servers = await self.repository.find_by_user_id(user_id, active_only=True)
            hub = await self.connection_pool.get_or_create_user_hub(user_id, all_active_servers)
            
            if not hub:
                raise ServiceException("Hub初始化失败或超时")
            
            # 🔥 使用Hub的单服务器连接方法，只影响指定服务器
            logger.info(f"连接单个服务器: {server.name}（不影响其他服务器）")
            success = await hub.connect_single_server(server.name)
            
            if not success:
                raise ServiceException(f"服务器 {server.name} 连接失败")
            
            # 测试连接能力
            capabilities = []
            server_tools = []
            
            # 测试工具能力
            try:
                tools_result = await hub.list_tools()
                if hasattr(tools_result, 'tools') and tools_result.tools:
                    server_tools = [tool for tool in tools_result.tools 
                                  if tool.name.startswith(f"{server.name}/")]
                if server_tools:
                    capabilities.append(MCPCapability.TOOLS)
            except Exception as e:
                logger.warning(f"测试服务器 {server.name} 工具能力失败: {e}")
            
            # 测试资源能力
            try:
                resources_result = await hub.list_resources(server.name)
                if resources_result:
                    capabilities.append(MCPCapability.RESOURCES)
            except Exception as e:
                logger.warning(f"测试服务器 {server.name} 资源能力失败: {e}")
            
            # 测试提示能力
            try:
                prompts_result = await hub.list_prompts(server.name)
                if prompts_result:
                    capabilities.append(MCPCapability.PROMPTS)
            except Exception as e:
                logger.warning(f"测试服务器 {server.name} 提示能力失败: {e}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # ✅ 不更新数据库状态 - 状态从Hub实时获取
            logger.info(f"单服务器连接成功: {server.name} (耗时: {execution_time:.2f}s)")
            
            return MCPConnectionTest(
                success=True,
                message=f"连接成功，发现 {len(server_tools)} 个工具",
                latency_ms=int(execution_time * 1000),
                capabilities=capabilities
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"连接失败: {str(e)}"
            
            # ✅ 不更新数据库状态 - 错误信息从Hub实时获取
            logger.error(f"单服务器连接失败: {server.name} - {error_msg}")
            
            return MCPConnectionTest(
                success=False,
                message=error_msg,
                latency_ms=int(execution_time * 1000),
                capabilities=[]
            )
    
    async def _test_single_server_connection(self, server: MCPServer, user_id: str) -> MCPConnectionTest:
        """测试单个服务器连接 - 重新设计版本"""
        start_time = datetime.now()
        
        try:
            # 1. 获取或创建用户Hub（包含所有活跃服务器配置）
            all_active_servers = await self.repository.find_by_user_id(user_id, active_only=True)
            hub = await self.connection_pool.get_or_create_user_hub(user_id, all_active_servers)
            
            if not hub:
                raise ServiceException("Hub初始化失败或超时")
            
            # 2. 连接指定的单个服务器
            success = await hub.connect_single_server(server.name)
            if not success:
                raise ServiceException(f"服务器 {server.name} 连接失败")
            
            # 3. 测试连接能力
            capabilities = []
            server_tools = []
            
            # 测试工具能力
            try:
                tools_result = await hub.list_tools()
                if hasattr(tools_result, 'tools') and tools_result.tools:
                    server_tools = [tool for tool in tools_result.tools 
                                if tool.name.startswith(f"{server.name}/")]
                if server_tools:
                    capabilities.append(MCPCapability.TOOLS)
            except Exception as e:
                logger.warning(f"测试服务器 {server.name} 工具能力失败: {e}")
            
            # 测试资源能力
            try:
                resources_result = await hub.list_resources(server.name)
                if resources_result:
                    capabilities.append(MCPCapability.RESOURCES)
            except Exception as e:
                logger.warning(f"测试服务器 {server.name} 资源能力失败: {e}")
            
            # 测试提示能力
            try:
                prompts_result = await hub.list_prompts(server.name)
                if prompts_result:
                    capabilities.append(MCPCapability.PROMPTS)
            except Exception as e:
                logger.warning(f"测试服务器 {server.name} 提示能力失败: {e}")
            
            # 计算延迟
            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return MCPConnectionTest(
                success=True,
                message=f"连接成功，发现 {len(server_tools)} 个工具",
                latency_ms=latency,
                capabilities=capabilities
            )
            
        except Exception as e:
            error_msg = f"连接失败: {str(e)}"
            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return MCPConnectionTest(
                success=False,
                message=error_msg,
                latency_ms=latency,
                capabilities=[]
            )

    async def disconnect_server(self, server_id: str, user_id: str) -> bool:
        """断开MCP服务器连接 - 完全隔离版本，绝不影响其他服务器"""
        server = await self.repository.get_user_server(server_id, user_id)
        if not server:
            raise NotFoundException(f"MCP服务器 {server_id} 不存在")
        
        try:
            # 🔥 核心修复：只获取现有Hub，绝不重建
            hub = await self.connection_pool.get_user_hub_no_create(user_id)
            if not hub:
                logger.warning(f"用户 {user_id} 的Hub不存在，可能服务器已经断开")
                # ✅ 不更新数据库状态 - 状态从Hub实时获取
                return True
            
            # 🔥 使用Hub的单服务器断开方法，只影响指定服务器
            logger.info(f"断开单个服务器: {server.name}（不影响其他服务器）")
            success = await hub.disconnect_single_server(server.name)
            
            if success:
                # ✅ 不更新数据库状态 - 状态从Hub实时获取
                logger.info(f"单服务器断开连接成功: {server.name}")
            else:
                logger.error(f"单服务器断开连接失败: {server.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"断开服务器连接异常: {str(e)}")
            return False
    
    async def refresh_server_connection(self, server_id: str, user_id: str) -> MCPServerStatus:
        """刷新服务器连接 - 单服务器隔离版本"""
        server = await self.repository.get_user_server(server_id, user_id)
        if not server:
            raise NotFoundException(f"MCP服务器 {server_id} 不存在")
        
        try:
            # 🔥 核心修复：只获取现有Hub，绝不重建整个Hub
            hub = await self.connection_pool.get_user_hub_no_create(user_id)
            if not hub:
                # 🔥 如果没有Hub，使用所有活跃服务器创建完整Hub
                logger.info(f"为用户 {user_id} 创建包含所有活跃服务器的Hub")
                all_active_servers = await self.repository.find_by_user_id(user_id, active_only=True)
                hub = await self.connection_pool.get_or_create_user_hub(user_id, all_active_servers)
            else:
                # 🔥 确保该服务器在Hub中（如果不存在则添加）
                server_status = await hub.get_server_status(server.name)
                if not server_status.get("active", False):
                    logger.info(f"将服务器 {server.name} 添加到现有Hub（用于刷新）")
                    await hub.add_server(server.name)
                
            if not hub:
                raise ServiceException("Hub初始化失败或超时")
            
            # 🔧 使用单服务器重连：先断开再连接
            # await hub.disconnect_single_server(server.name)
            # await asyncio.sleep(0.5)  # 短暂等待确保断开完成
            
            # 重新加载配置（获取最新配置）
            # hub.config_provider.reload()
            
            # 重新连接
            success = await hub.connect_single_server(server.name)
            
            if success:
                logger.info(f"单服务器重连成功: {server.name}")
                # ✅ 不更新数据库状态 - 状态从Hub实时获取
            else:
                logger.error(f"单服务器重连失败: {server.name}")
                # ✅ 不更新数据库状态 - 错误信息从Hub实时获取
            
            # 返回服务器状态
            return await self._get_server_status_via_hub(server, hub)
            
        except Exception as e:
            logger.error(f"刷新服务器连接失败: {str(e)}")
            # 更新数据库状态
            await self.repository.update(server.id, {
                "status": "error",
                "last_error": f"刷新失败: {str(e)}"
            })
            # 返回错误状态而不是抛出异常
            return MCPServerStatus(
                server_id=server.id,
                name=server.name,
                status="error",
                connected=False,
                healthy=False,
                error_message=f"刷新失败: {str(e)}",
                capabilities=[]
            )
    
    async def _auto_connect_server(self, server_id: str, user_id: str) -> None:
        """自动连接服务器（后台任务）"""
        try:
            # 🔥 修复：使用异步迭代器正确处理异步生成器
            async for independent_session in get_session():
                independent_repository = MCPRepository(independent_session)
                server = await independent_repository.get_by_id(server_id)
                if server and server.active and server.auto_start:
                    await self._test_single_server_connection(server, user_id)
                break  # 只获取一次会话
        except Exception as e:
            logger.error(f"自动连接服务器 {server_id} 失败: {str(e)}")
    
    # ==========================================
    # 工具管理 - 通过 Hub 实现
    # ==========================================

    async def get_user_tools(self, user_id: str, server_ids: List[str] = None) -> List[Tool]:
        """获取用户可用的工具列表"""
        if server_ids:
            # 获取指定服务器的工具
            tools = []
            for server_id in server_ids:
                server_tools = await self.list_tools(user_id, server_id)
                tools.extend(server_tools)
            return tools
        else:
            # 获取所有工具
            return await self.get_all_user_tools(user_id)
    
    async def list_tools(self, user_id: str, server_id: Optional[str] = None) -> List[Tool]:
        """获取可用工具列表"""
        if server_id:
            # 获取特定服务器的工具
            server = await self.repository.get_user_server(server_id, user_id)
            if not server:
                raise NotFoundException(f"MCP服务器 {server_id} 不存在")
            return await self._get_server_tools_via_hub(server, user_id)
        else:
            # 获取所有活跃服务器的工具
            return await self.get_all_user_tools(user_id)
    
    async def get_all_user_tools(self, user_id: str) -> List[Tool]:
        """获取用户所有可用工具"""
        try:
            # 获取用户Hub
            hub = await self._get_user_hub(user_id)
            if not hub:
                logger.warning(f"用户 {user_id} 的Hub未初始化")
                return []
            
            # 获取所有活跃服务器
            servers = await self.repository.get_user_servers(user_id, active_only=True)
            if not servers:
                logger.info(f"用户 {user_id} 没有活跃的MCP服务器")
                return []
            
            all_tools = []
            for server in servers:
                try:
                    server_tools = await self._get_server_tools_with_timeout(server, hub)
                    all_tools.extend(server_tools)
                except Exception as e:
                    logger.warning(f"获取服务器 {server.name} 工具失败: {e}")
                    continue
            
            logger.info(f"用户 {user_id} 总共获取到 {len(all_tools)} 个工具")
            return all_tools
            
        except Exception as e:
            logger.error(f"获取用户 {user_id} 所有工具失败: {e}")
            return []
    
    async def _get_server_tools_with_timeout(self, server: MCPServer, hub: MCPHub, timeout: float = 5.0) -> List[Tool]:
        """获取服务器工具（带超时）"""
        try:
            return await asyncio.wait_for(
                self._get_server_tools_via_hub_internal(server, hub),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"获取服务器 '{server.name}' 工具超时 ({timeout}s)")
            return []
        except Exception as e:
            logger.error(f"获取服务器 '{server.name}' 工具失败: {e}")
            return []
    
    async def _get_server_tools_via_hub(self, server: MCPServer, user_id: str) -> List[Tool]:
        """通过Hub获取服务器工具"""
        try:
            hub = await self._get_user_hub(user_id)
            if not hub:
                logger.warning(f"用户 {user_id} 的Hub未初始化")
                return []
            
            return await self._get_server_tools_via_hub_internal(server, hub)
            
        except Exception as e:
            logger.error(f"通过Hub获取服务器 '{server.name}' 工具失败: {e}")
            return []
    
    async def _get_server_tools_via_hub_internal(self, server: MCPServer, hub: MCPHub) -> List[Tool]:
        """内部方法：通过Hub获取服务器工具"""
        try:
            # 获取服务器工具列表
            tools_data = await hub.list_tools()
            if not tools_data or not tools_data.tools:
                return []
            
            tools = []
            for tool_info in tools_data.tools:
                original_tool_name = tool_info.name
                tool_description = tool_info.description
                input_schema = tool_info.inputSchema

                # 检查工具是否属于当前服务器
                tool_server_name = None
                if "/" in original_tool_name:
                    tool_server_name = original_tool_name.split("/")[0]
                elif ":" in original_tool_name:
                    tool_server_name = original_tool_name.split(":")[0]
                elif "__" in original_tool_name:
                    tool_server_name = original_tool_name.split("__")[0]
                else:
                    # 没有前缀，假设属于当前服务器
                    tool_server_name = server.name
                
                if tool_server_name != server.name:
                    continue

                # 生成符合OpenAI要求的工具名称
                # 先提取纯工具名（去掉服务器前缀）
                if "/" in original_tool_name:
                    pure_tool_name = original_tool_name.split("/", 1)[1]
                elif ":" in original_tool_name:
                    pure_tool_name = original_tool_name.split(":", 1)[1]
                elif "__" in original_tool_name:
                    pure_tool_name = original_tool_name.split("__", 1)[1]
                else:
                    pure_tool_name = original_tool_name
                
                # 清理名称中的特殊字符
                clean_tool_name = self._clean_tool_name(pure_tool_name)
                clean_server_name = self._clean_tool_name(server.name)
                
                # 直接拼接服务器名和工具名，不使用分隔符避免歧义
                openai_tool_name = f"{clean_server_name}_{clean_tool_name}"
                
                # 转换为标准Tool格式
                tool_parameters = []
                if input_schema and "properties" in input_schema:
                    properties = input_schema["properties"]
                    required_fields = input_schema.get("required", [])
                    
                    for param_name, param_def in properties.items():
                        tool_parameter = ToolParameter(
                            name=param_name,
                            description=param_def.get("description", ""),
                            type=param_def.get("type", "string"),
                            required=param_name in required_fields,
                            enum=param_def.get("enum"),
                            default=param_def.get("default")
                        )
                        tool_parameters.append(tool_parameter)
                
                tool = Tool(
                    id=original_tool_name,  # ID保持原始名称用于调用
                    name=openai_tool_name,  # name使用OpenAI兼容格式
                    description=tool_description,
                    parameters=tool_parameters
                )
                tools.append(tool)
            
            logger.debug(f"服务器 '{server.name}' 提供 {len(tools)} 个工具")
            return tools
            
        except Exception as e:
            logger.error(f"解析服务器 '{server.name}' 工具数据失败: {e}")
            return []
    
    def _clean_tool_name(self, tool_name: str) -> str:
        """清理工具名称，只保留字母数字下划线连字符"""
        import re
        # 替换不符合要求的字符为下划线
        cleaned = re.sub(r'[^a-zA-Z0-9_-]', '_', tool_name)
        # 移除连续的下划线
        cleaned = re.sub(r'_+', '_', cleaned)
        # 移除开头和结尾的下划线
        cleaned = cleaned.strip('_')
        # 确保不为空
        return cleaned if cleaned else "tool"
    
    def _tool_belongs_to_server(self, tool_name: str, server_name: str) -> bool:
        """检查工具是否属于指定服务器"""
        if "/" in tool_name:
            # 格式: "server_name/tool_name"
            parts = tool_name.split("/", 1)
            return len(parts) == 2 and parts[0] == server_name
        else:
            # 没有命名空间的工具，可能属于任何服务器
            return True
    
    def _parse_tool_name(self, full_name: str, server_name: str) -> tuple[str, Optional[str]]:
        """解析工具名称，返回 (tool_name, namespace)"""
        if "/" in full_name:
            parts = full_name.split("/", 1)
            if len(parts) == 2:
                return parts[1], parts[0]
        return full_name, None
    
    def _categorize_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """根据工具名称和参数推断分类"""
        name_lower = tool_name.lower()
        
        # 文件系统相关
        if any(keyword in name_lower for keyword in ['file', 'read', 'write', 'directory', 'folder', 'path']):
            return '文件系统'
        
        # 网络请求相关
        elif any(keyword in name_lower for keyword in ['web', 'http', 'fetch', 'request', 'url', 'api']):
            return '网络请求'
        
        # 记忆管理相关
        elif any(keyword in name_lower for keyword in ['memory', 'remember', 'store', 'save', 'recall']):
            return '记忆管理'
        
        # 搜索相关
        elif any(keyword in name_lower for keyword in ['search', 'query', 'find', 'lookup']):
            return '搜索工具'
        
        # 图像处理相关
        elif any(keyword in name_lower for keyword in ['image', 'photo', 'picture', 'visual', 'img']):
            return '图像处理'
        
        # 文本处理相关
        elif any(keyword in name_lower for keyword in ['text', 'string', 'format', 'parse']):
            return '文本处理'
        
        # 数据库相关
        elif any(keyword in name_lower for keyword in ['database', 'db', 'sql', 'query']):
            return '数据库'
        
        # 系统工具
        elif any(keyword in name_lower for keyword in ['system', 'process', 'exec', 'run']):
            return '系统工具'
        
        else:
            return '其他工具'
    
    async def get_tools_by_category(self, user_id: str) -> Dict[str, List[Tool]]:
        """按分类获取工具"""
        try:
            all_tools = await self.get_all_user_tools(user_id)
            
            categories = {}
            for tool in all_tools:
                # 从工具名称推断分类
                category = self._categorize_tool(tool.name, tool.parameters)
                if category not in categories:
                    categories[category] = []
                categories[category].append(tool)
            
            return categories
            
        except Exception as e:
            logger.error(f"按分类获取用户 {user_id} 工具失败: {e}")
            return {}
    
    async def search_tools(self, user_id: str, query: str, limit: int = 20) -> List[Tool]:
        """搜索工具"""
        try:
            all_tools = await self.get_all_user_tools(user_id)
            
            # 简单的文本匹配搜索
            query_lower = query.lower()
            matched_tools = []
            
            for tool in all_tools:
                if (query_lower in tool.name.lower() or 
                    query_lower in tool.description.lower()):
                    matched_tools.append(tool)
                    
                    if len(matched_tools) >= limit:
                        break
            
            return matched_tools
            
        except Exception as e:
            logger.error(f"搜索用户 {user_id} 工具失败: {e}")
            return []
    
    # ==========================================
    # 资源和提示管理 - 通过 Hub 实现
    # ==========================================
    
    async def list_resources(self, user_id: str, server_id: Optional[str] = None) -> List[MCPResource]:
        """获取可用资源列表"""
        if server_id:
            server = await self.repository.get_user_server(server_id, user_id)
            if not server:
                raise NotFoundException(f"MCP服务器 {server_id} 不存在")
            return await self._get_server_resources_via_hub(server, user_id)
        else:
            servers = await self.repository.find_active_servers(user_id)
            resources = []
            for server in servers:
                server_resources = await self._get_server_resources_via_hub(server, user_id)
                resources.extend(server_resources)
            return resources
    
    async def list_prompts(self, user_id: str, server_id: Optional[str] = None) -> List[MCPPrompt]:
        """获取可用提示模板列表"""
        if server_id:
            server = await self.repository.get_user_server(server_id, user_id)
            if not server:
                raise NotFoundException(f"MCP服务器 {server_id} 不存在")
            return await self._get_server_prompts_via_hub(server, user_id)
        else:
            servers = await self.repository.find_active_servers(user_id)
            prompts = []
            for server in servers:
                server_prompts = await self._get_server_prompts_via_hub(server, user_id)
                prompts.extend(server_prompts)
            return prompts
    
    async def _get_server_resources_via_hub(self, server: MCPServer, user_id: str) -> List[MCPResource]:
        """通过 Hub 获取服务器资源列表"""
        try:
            hub = await self._get_user_hub(user_id)
            resources_result = await hub.list_resources()
            
            # 转换为 MCPResource 格式
            server_resources = []
            if resources_result:
                for server_name, resources in resources_result.items():
                    if server_name == server.name:
                        for resource in resources:
                            mcp_resource = MCPResource(
                                uri=resource.uri,
                                name=resource.name or resource.uri,
                                description=resource.description or "",
                                server_id=server.id,
                                server_name=server.name,
                                mime_type=getattr(resource, 'mimeType', None)
                            )
                            server_resources.append(mcp_resource)
            
            return server_resources
        except Exception as e:
            logger.error(f"获取服务器 {server.name} 资源列表失败: {str(e)}")
            return []
    
    async def _get_server_prompts_via_hub(self, server: MCPServer, user_id: str) -> List[MCPPrompt]:
        """通过 Hub 获取服务器提示模板列表"""
        try:
            hub = await self._get_user_hub(user_id)
            prompts_result = await hub.list_prompts(server.name)
            
            # 转换为 MCPPrompt 格式
            server_prompts = []
            if prompts_result and server.name in prompts_result:
                for prompt in prompts_result[server.name]:
                    mcp_prompt = MCPPrompt(
                        name=prompt.name,
                        description=prompt.description or "",
                        server_id=server.id,
                        server_name=server.name,
                        arguments=getattr(prompt, 'arguments', [])
                    )
                    server_prompts.append(mcp_prompt)
            
            return server_prompts
        except Exception as e:
            logger.error(f"获取服务器 {server.name} 提示模板列表失败: {str(e)}")
            return []
    
    # ==========================================
    # 工具调用 - 通过 Hub 实现
    # ==========================================
    
    async def call_tool(self, user_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用MCP工具 - 非阻塞模式
        
        Args:
            user_id: 用户ID
            tool_name: 工具名称（可能是OpenAI格式或原始格式）
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        try:
            # 非阻塞检查 Hub 状态
            hub = await self._get_user_hub(user_id)
            if not hub:
                status = self.get_hub_status(user_id)
                error_msg = f"MCP Hub 未就绪 (状态: {status})，无法调用工具"
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "content": []
                }
            
            # 🔥 简化工具名称解析：如果是server_toolname格式，提取toolname
            actual_tool_name = tool_name
            if '_' in tool_name and not tool_name.startswith('temp_'):
                # 假设格式是 server_toolname，提取 toolname 部分
                parts = tool_name.split('_', 1)
                if len(parts) == 2:
                    actual_tool_name = parts[1]
                    logger.info(f"工具名称转换: {tool_name} -> {actual_tool_name}")
            
            # 添加超时控制
            result = await asyncio.wait_for(
                hub.call_tool(actual_tool_name, arguments),
                timeout=30.0  # 30秒超时
            )
            
            logger.info(f"用户 {user_id} 成功调用工具 '{actual_tool_name}'")
            
            # 转换结果格式
            if hasattr(result, 'content') and result.content:
                return {
                    "success": True,
                    "content": [
                        {
                            "type": item.type,
                            "text": getattr(item, 'text', str(item))
                        }
                        for item in result.content
                    ]
                }
            else:
                return {
                    "success": True,
                    "content": [{"type": "text", "text": "工具执行完成，无返回内容"}]
                }
                
        except asyncio.TimeoutError:
            error_msg = f"工具 '{tool_name}' 执行超时"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "content": []
            }
        except Exception as e:
            error_msg = f"调用工具 '{tool_name}' 失败: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "content": []
            }
    
    async def _resolve_tool_name(self, user_id: str, tool_name: str) -> Optional[str]:
        """解析工具名称，从OpenAI格式还原到原始格式"""
        try:
            # 获取所有工具
            tools = await self.get_all_user_tools(user_id)
            
            # 先尝试直接匹配（原始名称）
            for tool in tools:
                if tool.id == tool_name:
                    return tool.id
            
            # 再尝试匹配OpenAI格式的名称
            for tool in tools:
                if tool.name == tool_name:
                    return tool.id
            
            return None
            
        except Exception as e:
            logger.error(f"解析工具名称失败: {str(e)}")
            return None
    
    # ==========================================
    # 批量操作和统计
    # ==========================================
    
    async def batch_activate_servers(self, server_ids: List[str], user_id: str) -> Dict[str, Any]:
        """批量激活服务器 - 单服务器隔离版本"""
        count = await self.repository.activate_servers(server_ids, user_id)
        
        # 🔧 修复：不刷新整个Hub，而是逐个添加激活的服务器
        try:
            hub = await self.connection_pool.get_user_hub_wait(user_id, timeout=5.0)
            if hub:
                # 重新加载配置以获取激活的服务器
                hub.config_provider.reload()
        
                # 逐个添加激活的服务器
            for server_id in server_ids:
                    server = await self.repository.get_user_server(server_id, user_id)
                    if server and server.active:
                        try:
                            await hub.add_server(server.name)
                            logger.info(f"批量激活：添加服务器到Hub: {server.name}")
                        except Exception as e:
                            logger.error(f"批量激活：添加服务器失败: {server.name} - {e}")
        except Exception as e:
            logger.error(f"批量激活服务器时更新Hub失败: {str(e)}")
        
        # 尝试连接激活的服务器
        # for server_id in server_ids:
            # asyncio.create_task(self._auto_connect_server(server_id, user_id))
        
        return {"activated_count": count, "total_requested": len(server_ids)}
    
    async def batch_deactivate_servers(self, server_ids: List[str], user_id: str) -> Dict[str, Any]:
        """批量停用服务器 - 单服务器隔离版本"""
        # 🔧 修复：先从Hub移除服务器，再停用数据库记录
        try:
            hub = await self.connection_pool.get_user_hub_wait(user_id, timeout=5.0)
            if hub:
                # 逐个从Hub移除服务器
                for server_id in server_ids:
                    server = await self.repository.get_user_server(server_id, user_id)
                    if server:
                        try:
                            await hub.remove_server(server.name)
                            logger.info(f"批量停用：从Hub移除服务器: {server.name}")
                        except Exception as e:
                            logger.error(f"批量停用：移除服务器失败: {server.name} - {e}")
        except Exception as e:
            logger.error(f"批量停用服务器时更新Hub失败: {str(e)}")
        
        count = await self.repository.deactivate_servers(server_ids, user_id)
        
        return {"deactivated_count": count, "total_requested": len(server_ids)}
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户MCP统计信息"""
        try:
            # 获取基础统计
            stats = await self.repository.get_server_stats(user_id)
            
            # 添加工具统计
            tools = await self.get_all_user_tools(user_id)
            tools_by_category = await self.get_tools_by_category(user_id)
            
            stats.update({
                "total_tools": len(tools),
                "tools_by_category": {
                    category: len(tools) for category, tools in tools_by_category.items()
                },
                "hub_status": self.connection_pool.get_connection_status(user_id)
            })
            
            return stats
        except Exception as e:
            logger.error(f"获取用户统计信息失败: {str(e)}")
            return {"error": str(e)}
    
    # ==========================================
    # 辅助方法
    # ==========================================
    
    def _normalize_args(self, args: Any) -> List[str]:
        """标准化args参数，确保返回列表格式"""
        import json
        
        if args is None:
            return []
        
        if isinstance(args, list):
            return [str(arg) for arg in args]
        
        if isinstance(args, str):
            # 尝试解析JSON字符串
            try:
                parsed = json.loads(args)
                if isinstance(parsed, list):
                    return [str(arg) for arg in parsed]
                else:
                    # 如果不是列表，按空格分割
                    return args.split()
            except json.JSONDecodeError:
                # 如果不是JSON，按空格分割
                return args.split()
        
        return []
    
    def _validate_server_config(self, server_data: MCPServerCreate) -> None:
        """验证服务器配置"""
        if server_data.transport == MCPTransportType.STDIO:
            if not server_data.command:
                raise ValidationException("STDIO传输类型需要指定启动命令")
        elif server_data.transport in [MCPTransportType.HTTP, MCPTransportType.SSE]:
            if not server_data.url:
                raise ValidationException(f"{server_data.transport.value}传输类型需要指定URL")
    
    async def test_server_connection(self, server_id: str, user_id: str) -> MCPConnectionTest:
        """测试MCP服务器连接"""
        server = await self.repository.get_user_server(server_id, user_id)
        if not server:
            raise NotFoundException(f"MCP服务器 {server_id} 不存在")
        
        return await self._test_single_server_connection(server, user_id)
    
    async def get_hub_initialization_status(self, user_id: str) -> Dict[str, Any]:
        """获取Hub初始化状态详情"""
        status = self.connection_pool.get_connection_status(user_id)
        is_connected = self.connection_pool.is_connected(user_id)
        
        # 获取用户的服务器数量
        servers = await self.repository.find_by_user_id(user_id, active_only=True)
        
        return {
            "user_id": user_id,
            "status": status,
            "is_connected": is_connected,
            "server_count": len(servers),
            "timestamp": datetime.now().isoformat(),
            "details": {
                "not_started": "Hub还未开始初始化",
                "connecting": "Hub正在连接中",
                "connected": "Hub已成功连接",
                "failed": "Hub连接失败",
                "disconnected": "Hub已断开连接"
            }.get(status, "未知状态")
        }
    
    async def force_hub_initialization(self, user_id: str) -> Dict[str, Any]:
        """强制重新初始化Hub"""
        try:
            # 断开现有连接
            await self.connection_pool.disconnect_user(user_id)
            
            # 获取服务器配置并触发新连接
            servers = await self.repository.find_by_user_id(user_id, active_only=True)
            hub = await self.connection_pool.get_user_hub(user_id, servers)
            
            status = self.connection_pool.get_connection_status(user_id)
            
            return {
                "success": True,
                "user_id": user_id,
                "status": status,
                "message": f"Hub初始化已触发，当前状态: {status}",
                "server_count": len(servers)
            }
        except Exception as e:
            logger.error(f"强制初始化用户 {user_id} 的Hub失败: {str(e)}")
            return {
                "success": False,
                "user_id": user_id,
                "error": str(e),
                "message": "强制初始化失败"
            }
    
    async def cleanup_failed_hubs(self) -> Dict[str, int]:
        """清理失败的Hub连接 - 通过连接池的清理机制"""
        try:
            # 触发连接池的清理
            await self.connection_pool.cleanup_inactive_connections()
        
            return {
                    "success": True,
                    "message": "已触发连接池清理",
                    "cleaned_count": 0  # 连接池内部管理，无法获取具体数量
                }
        except Exception as e:
            logger.error(f"清理失败的Hub连接出错: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "cleaned_count": 0
            }
