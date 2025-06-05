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
        self._user_hubs: Dict[str, MCPHub] = {}  # 用户ID -> MCPHub实例
        self._hub_initialization_status: Dict[str, str] = {}  # "initializing", "ready", "failed"
        self._hub_initialization_tasks: Dict[str, asyncio.Task] = {}  # 后台初始化任务
        self._initialization_timeout = 30  # 30秒超时
        
        logger.info("MCP服务初始化")
    
    def get_entity_name(self) -> str:
        """获取实体名称"""
        return "MCP服务器"
    
    # ==========================================
    # Hub 管理 - 核心基础设施
    # ==========================================
    
    async def _get_user_hub(self, user_id: str) -> Optional[MCPHub]:
        """获取用户的 MCP Hub，非阻塞模式"""
        # 检查初始化状态
        status = self._hub_initialization_status.get(user_id, "not_started")
        
        if status == "ready":
            return self._user_hubs.get(user_id)
        elif status == "failed":
            logger.warning(f"用户 {user_id} 的 MCP Hub 初始化失败，返回 None")
            return None
        elif status == "initializing":
            logger.info(f"用户 {user_id} 的 MCP Hub 正在初始化中，返回 None")
            return None
        else:
            # 🔥 关键修复：不等待初始化完成，立即返回None，启动后台初始化
            self._start_hub_initialization_background(user_id)
            return None
    
    def _start_hub_initialization_background(self, user_id: str) -> None:
        """启动后台初始化 Hub - 完全非阻塞"""
        if user_id in self._hub_initialization_tasks:
            # 已经在初始化中
            return
            
        self._hub_initialization_status[user_id] = "initializing"
        logger.info(f"开始后台初始化用户 {user_id} 的 MCP Hub")
        
        # 🔥 关键：创建后台任务，不等待结果
        task = asyncio.create_task(self._do_hub_initialization(user_id))
        self._hub_initialization_tasks[user_id] = task
    
    async def _do_hub_initialization(self, user_id: str) -> None:
        """执行实际的 Hub 初始化"""
        try:
            # 🔥 减少超时时间，快速失败
            hub = await asyncio.wait_for(
                self._create_user_hub(user_id),
                timeout=30
            )
            
            self._user_hubs[user_id] = hub
            self._hub_initialization_status[user_id] = "ready"
            logger.info(f"用户 {user_id} 的 MCP Hub 初始化成功")
            
        except asyncio.TimeoutError:
            logger.error(f"用户 {user_id} 的 MCP Hub 初始化超时(30秒)")
            self._hub_initialization_status[user_id] = "failed"
        except Exception as e:
            logger.error(f"用户 {user_id} 的 MCP Hub 初始化失败: {str(e)}")
            self._hub_initialization_status[user_id] = "failed"
        finally:
            # 清理任务
            if user_id in self._hub_initialization_tasks:
                del self._hub_initialization_tasks[user_id]
    
    async def _create_user_hub(self, user_id: str) -> MCPHub:
        """为用户创建 MCP Hub"""
        try:
            # 使用独立的数据库会话来避免会话状态冲突
            async for independent_session in get_session():
                # 创建独立的repository实例
                independent_repository = MCPRepository(independent_session)
                
                # 获取用户的活跃服务器配置
                servers = await independent_repository.find_by_user_id(user_id, active_only=True)
                
                # 🔥 限制服务器数量，避免过多服务器导致初始化超时
                if len(servers) > 5:
                    logger.warning(f"用户 {user_id} 有 {len(servers)} 个活跃服务器，只初始化前5个")
                    servers = servers[:5]
                
                # 构建 Hub 配置
                config_dict = self._build_hub_config(servers, user_id)
                
                # 创建并初始化 Hub
                hub = MCPHub(config_dict=config_dict, logger=logger)
                await hub.initialize(user_id=user_id)
                
                logger.info(f"为用户 {user_id} 创建 MCP Hub，包含 {len(servers)} 个服务器")
                return hub  # 返回创建的Hub实例
            
        except Exception as e:
            logger.error(f"创建用户 {user_id} 的 MCP Hub 失败: {str(e)}")
            # 创建空配置的 Hub 作为后备
            # 空配置字典，没有任何服务器
            hub = MCPHub(config_dict={}, logger=logger)
            return hub  # 返回后备Hub实例
    
    def get_hub_status(self, user_id: str) -> str:
        """获取 Hub 初始化状态"""
        return self._hub_initialization_status.get(user_id, "not_started")
    
    def is_hub_ready(self, user_id: str) -> bool:
        """检查 Hub 是否已准备就绪"""
        return self._hub_initialization_status.get(user_id) == "ready"
    
    async def _refresh_user_hub(self, user_id: str) -> None:
        """刷新用户的 MCP Hub（重新加载配置）"""
        if user_id in self._user_hubs:
            await self._user_hubs[user_id].shutdown()
            del self._user_hubs[user_id]
        
        # 重新创建Hub
        try:
            hub = await self._create_user_hub(user_id)
            self._user_hubs[user_id] = hub
            self._hub_initialization_status[user_id] = "ready"
        except Exception as e:
            logger.error(f"刷新用户 {user_id} 的 MCP Hub 失败: {str(e)}")
            self._hub_initialization_status[user_id] = "failed"
    
    async def _update_hub_server(self, user_id: str, server: MCPServer, operation: str) -> None:
        """更新Hub中的服务器配置 - 使用reload_servers方法
        
        Args:
            user_id: 用户ID
            server: 服务器配置
            operation: 操作类型 ('add', 'update', 'remove')
        """
        try:
            hub = await self._get_user_hub(user_id)
            if not hub:
                logger.warning(f"用户 {user_id} 的Hub未初始化，跳过更新")
                return
            
            # 使用reload_servers方法重新加载配置
            # 这会重新读取数据库中的最新配置
            await hub.reload_servers(user_id=user_id)
            logger.info(f"Hub服务器配置已重新加载 ({operation}): {server.name}")
                
        except Exception as e:
            logger.error(f"重新加载Hub服务器配置失败 ({operation}): {str(e)}")
            # 如果reload失败，回退到全量刷新
            logger.info(f"回退到全量刷新Hub: {user_id}")
            await self._refresh_user_hub(user_id)
    
    async def cleanup_user_connections(self, user_id: str) -> None:
        """清理用户的所有连接"""
        if user_id in self._user_hubs:
            await self._user_hubs[user_id].shutdown()
            del self._user_hubs[user_id]
            logger.info(f"清理用户 {user_id} 的 MCP 连接")
    
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
        if server_data.auto_start:
            asyncio.create_task(self._auto_connect_server(server.id, user_id))
        
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
        """获取用户所有服务器的状态"""
        try:
            # 确保使用新的查询获取服务器列表
            servers = await self.repository.find_by_user_id(user_id)
            statuses = []
            
            try:
                hub = await self._get_user_hub(user_id)
                
                for server in servers:
                    status = await self._get_server_status_via_hub(server, hub)
                    statuses.append(status)
            except Exception as e:
                logger.error(f"获取服务器状态失败: {str(e)}")
                # 返回基础状态信息
                for server in servers:
                    statuses.append(MCPServerStatus(
                        server_id=server.id,
                        name=server.name,
                        status=server.status or "unknown",
                        connected=False,
                        healthy=False,
                        error_message=f"无法获取状态: {str(e)}",
                        capabilities=[]
                    ))
            
            return statuses
        except Exception as e:
            logger.error(f"查找用户MCP服务器失败: {str(e)}")
            # 如果数据库查询失败，返回空列表
            return []
    
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
            connected_statuses = []
            
            for server in servers:
                status = await self._get_server_status_via_hub(server, hub)
                # 只返回已连接且健康的服务器
                if status.connected and status.healthy:
                    connected_statuses.append(status)
            
            logger.info(f"用户 {user_id} 有 {len(connected_statuses)} 个已连接的MCP服务器")
            return connected_statuses
            
        except Exception as e:
            logger.error(f"获取已连接服务器状态失败: {str(e)}")
            return []
    
    async def _get_server_status_via_hub(self, server: MCPServer, hub: MCPHub) -> MCPServerStatus:
        """通过 Hub 获取服务器状态 - 优化数据库更新"""
        try:
            # 检查服务器是否连接
            is_connected = await self._check_server_health_via_hub(server.name, hub)
            
            # 获取服务器能力
            capabilities = []
            if server.capabilities:
                if isinstance(server.capabilities, list):
                    capabilities = server.capabilities
                elif isinstance(server.capabilities, str):
                    try:
                        import json
                        capabilities = json.loads(server.capabilities)
                        if not isinstance(capabilities, list):
                            capabilities = []
                    except (json.JSONDecodeError, TypeError):
                        capabilities = []
            
            # 根据实际连接状态确定status
            if is_connected:
                actual_status = "active"
                error_message = None
            else:
                actual_status = "inactive"
                error_message = server.last_error or "无法连接到服务器"
            
            # 🔥 修复：只在状态真正改变时才更新数据库，且不使用独立事务
            if server.status != actual_status:
                logger.info(f"服务器 {server.name} 状态变化: {server.status} -> {actual_status}")
                try:
                    # 使用当前事务进行状态更新，避免独立事务导致的锁等待
                    await self.repository.update_server_status(server.id, actual_status, error_message)
                except Exception as e:
                    logger.error(f"更新服务器状态失败: {str(e)}")
                    # 继续执行，不影响状态返回
            
            return MCPServerStatus(
                server_id=server.id,
                name=server.name,
                status=actual_status,
                connected=is_connected,
                healthy=server.active and is_connected,
                last_ping=datetime.now() if is_connected else None,
                error_message=error_message,
                capabilities=capabilities
            )
        except Exception as e:
            # 🔥 修复：只在状态真正改变时才更新数据库
            if server.status != "error":
                logger.error(f"服务器 {server.name} 状态检查异常: {str(e)}")
                try:
                    # 使用当前事务进行错误状态更新
                    await self.repository.update_server_status(server.id, "error", str(e))
                except Exception as update_error:
                    logger.error(f"更新错误状态失败: {str(update_error)}")
            
            return MCPServerStatus(
                server_id=server.id,
                name=server.name,
                status="error",
                connected=False,
                healthy=False,
                error_message=str(e),
                capabilities=[]
            )
    
    async def _check_server_health_via_hub(self, server_name: str, hub: MCPHub) -> bool:
        """通过 Hub 检查服务器健康状态"""
        try:
            # 尝试列出工具来检查连接
            result = await hub.list_tools()
            # 如果能成功获取工具列表，说明连接正常
            return True
        except Exception:
            return False
    
    # ==========================================
    # 连接管理 - 通过 Hub 实现
    # ==========================================
    
    async def connect_server(self, server_id: str, user_id: str) -> MCPConnectionTest:
        """连接到MCP服务器"""
        server = await self.repository.get_user_server(server_id, user_id)
        if not server:
            raise NotFoundException(f"MCP服务器 {server_id} 不存在")
        
        if not server.active:
            raise ValidationException("服务器未启用")
        
        return await self._test_server_connection_via_hub(server, user_id)
    
    async def refresh_server_connection(self, server_id: str, user_id: str) -> MCPServerStatus:
        """刷新服务器连接 - 优化版本，避免长事务"""
        # 1. 快速查询服务器信息（短事务）
        server = await self.repository.get_user_server(server_id, user_id)
        if not server:
            raise NotFoundException(f"MCP服务器 {server_id} 不存在")
        
        # 2. 在事务外执行Hub刷新（避免长事务导致MySQL超时）
        try:
            # 刷新用户的 Hub（重新加载配置）- 这个操作可能很耗时
            await self._refresh_user_hub(user_id)
            
            # 3. 获取Hub实例
            hub = await self._get_user_hub(user_id)
            if not hub:
                raise ServiceException("Hub初始化失败")
            
            # 4. 返回服务器状态
            return await self._get_server_status_via_hub(server, hub)
            
        except Exception as e:
            logger.error(f"刷新服务器连接失败: {str(e)}")
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
    
    async def _test_server_connection_via_hub(self, server: MCPServer, user_id: str) -> MCPConnectionTest:
        """通过 Hub 测试服务器连接"""
        start_time = datetime.now()
        
        try:
            hub = await self._get_user_hub(user_id)
            
            # 尝试列出工具来测试连接
            tools_result = await hub.list_tools()
            
            # 检查是否有来自该服务器的工具
            server_tools = []
            if hasattr(tools_result, 'tools') and tools_result.tools:
                server_tools = [tool for tool in tools_result.tools 
                              if tool.name.startswith(f"{server.name}/")]
            
            # 确定服务器能力
            capabilities = []
            if server_tools:
                capabilities.append(MCPCapability.TOOLS)
            
            # 尝试其他能力检测
            try:
                resources_result = await hub.list_resources()
                if resources_result:
                    capabilities.append(MCPCapability.RESOURCES)
            except:
                pass
            
            try:
                prompts_result = await hub.list_prompts()
                if prompts_result:
                    capabilities.append(MCPCapability.PROMPTS)
            except:
                pass
            
            # 计算延迟
            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 更新服务器状态
            await self.repository.update_server_status(server.id, "active")
            await self.repository.update_server_capabilities(server.id, [cap.value for cap in capabilities])
            
            return MCPConnectionTest(
                success=True,
                message=f"连接成功，发现 {len(server_tools)} 个工具",
                latency_ms=latency,
                capabilities=capabilities
            )
            
        except Exception as e:
            error_msg = f"连接失败: {str(e)}"
            await self.repository.update_server_status(server.id, "error", error_msg)
            
            return MCPConnectionTest(
                success=False,
                message=error_msg,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
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
                    await self._test_server_connection_via_hub(server, user_id)
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
        """批量激活服务器"""
        count = await self.repository.activate_servers(server_ids, user_id)
        
        # 刷新用户的 Hub（重新加载配置）
        await self._refresh_user_hub(user_id)
        
        # 尝试连接激活的服务器
        for server_id in server_ids:
            asyncio.create_task(self._auto_connect_server(server_id, user_id))
        
        return {"activated_count": count, "total_requested": len(server_ids)}
    
    async def batch_deactivate_servers(self, server_ids: List[str], user_id: str) -> Dict[str, Any]:
        """批量停用服务器"""
        count = await self.repository.deactivate_servers(server_ids, user_id)
        
        # 刷新用户的 Hub（重新加载配置）
        await self._refresh_user_hub(user_id)
        
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
                "hub_status": "connected" if user_id in self._user_hubs else "disconnected"
            })
            
            return stats
        except Exception as e:
            logger.error(f"获取用户统计信息失败: {str(e)}")
            return {"error": str(e)}
    
    # ==========================================
    # 辅助方法
    # ==========================================
    
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
        
        return await self._test_server_connection_via_hub(server, user_id)
    
    async def disconnect_server(self, server_id: str, user_id: str) -> bool:
        """断开MCP服务器连接"""
        if not await self.repository.check_user_ownership(server_id, user_id):
            raise NotFoundException(f"MCP服务器 {server_id} 不存在")
        
        # 更新状态为非活跃
        await self.repository.update_server_status(server_id, "inactive")
        
        # 刷新用户的 Hub（这会重新连接其他活跃服务器）
        await self._refresh_user_hub(user_id)
        
        logger.info(f"断开MCP服务器连接: {server_id}")
        return True
    
    async def get_hub_initialization_status(self, user_id: str) -> Dict[str, Any]:
        """获取Hub初始化状态信息"""
        status = self.get_hub_status(user_id)
        
        result = {
            "user_id": user_id,
            "status": status,
            "is_ready": self.is_hub_ready(user_id),
            "timestamp": datetime.now().isoformat()
        }
        
        # 如果有正在进行的初始化任务，添加任务信息
        if user_id in self._hub_initialization_tasks:
            task = self._hub_initialization_tasks[user_id]
            result["task_info"] = {
                "done": task.done(),
                "cancelled": task.cancelled()
            }
        
        return result
    
    async def force_hub_initialization(self, user_id: str) -> Dict[str, Any]:
        """强制重新初始化Hub - 非阻塞版本"""
        # 取消现有的初始化任务
        if user_id in self._hub_initialization_tasks:
            task = self._hub_initialization_tasks[user_id]
            if not task.done():
                task.cancel()
            del self._hub_initialization_tasks[user_id]
        
        # 清理现有状态
        if user_id in self._user_hubs:
            await self._user_hubs[user_id].shutdown()
            del self._user_hubs[user_id]
        
        if user_id in self._hub_initialization_status:
            del self._hub_initialization_status[user_id]
        
        # 开始新的非阻塞初始化
        self._start_hub_initialization_background(user_id)
        
        return await self.get_hub_initialization_status(user_id)
    
    async def cleanup_failed_hubs(self) -> Dict[str, int]:
        """清理失败的Hub初始化状态"""
        cleaned_count = 0
        failed_count = 0
        
        for user_id, status in list(self._hub_initialization_status.items()):
            if status == "failed":
                # 清理失败的状态
                del self._hub_initialization_status[user_id]
                if user_id in self._user_hubs:
                    try:
                        await self._user_hubs[user_id].shutdown()
                        del self._user_hubs[user_id]
                    except Exception:
                        pass
                cleaned_count += 1
            elif status == "failed":
                failed_count += 1
        
        logger.info(f"清理了 {cleaned_count} 个失败的Hub状态")
        
        return {
            "cleaned": cleaned_count,
            "still_failed": failed_count,
            "total_hubs": len(self._hub_initialization_status)
        }
    
    def _build_hub_config(self, servers: List[MCPServer], user_id: str) -> Dict[str, Any]:
        """构建 Hub 配置字典"""
        # 使用简单字典格式: {"server1": {...}, "server2": {...}}
        # 这是 ConfigProvider 支持的第三种格式
        config_dict = {}
        
        for server in servers:
            server_config = {
                "name": server.name,
                "transport": server.transport,
                "user_id": user_id
            }
            
            # 根据传输类型添加配置
            if server.transport == "stdio":
                if server.command:
                    server_config["command"] = server.command
                server_config["args"] = self._parse_args(server.args)
                server_config["env"] = self._parse_env(server.env)
            elif server.transport in ["http", "sse"]:
                if server.url:
                    server_config["url"] = server.url
            
            # 添加其他配置
            if hasattr(server, 'timeout') and server.timeout:
                server_config["timeout"] = server.timeout
            
            # 直接使用服务器名称作为键，而不是嵌套在 "servers" 下
            config_dict[server.name] = server_config
        
        return config_dict
    
    def _parse_args(self, args: Any) -> List[str]:
        """解析参数列表"""
        if not args:
            return []
        if isinstance(args, list):
            return args
        if isinstance(args, str):
            try:
                import json
                parsed = json.loads(args)
                return parsed if isinstance(parsed, list) else [args]
            except:
                return [arg.strip() for arg in args.split('\n') if arg.strip()]
        return []
    
    def _parse_env(self, env: Any) -> Dict[str, str]:
        """解析环境变量"""
        if not env:
            return {}
        if isinstance(env, dict):
            return env
        if isinstance(env, str):
            try:
                import json
                parsed = json.loads(env)
                return parsed if isinstance(parsed, dict) else {}
            except:
                # 解析 KEY=VALUE 格式
                env_dict = {}
                for line in env.split('\n'):
                    line = line.strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_dict[key.strip()] = value.strip()
                return env_dict
        return {}
