"""MCP会话管理器，管理MCP客户端会话的生命周期。"""

import asyncio
from datetime import timedelta, datetime
from typing import Any, Dict, List, Optional, TypeVar
from contextlib import AsyncExitStack

from anyio import Lock
from mcp import ClientSession
from mcp.types import ServerCapabilities

from .config import ConfigProvider
from .connection import ConnectionManager
from .utils.logger import Logger


# 返回类型泛型
T = TypeVar('T')


class ServerSession:
    """表示单个服务器会话，包含状态和会话对象。"""
    
    def __init__(self, server_name: str, session: ClientSession, capabilities: ServerCapabilities):
        """
        初始化服务器会话。
        
        Args:
            server_name: 服务器名称
            session: MCP客户端会话
            capabilities: 服务器能力
        """
        self.server_name = server_name
        self.session = session
        self.capabilities = capabilities
        self.healthy = True
        self.last_error: Optional[Exception] = None
        self.consecutive_failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.total_failures = 0
    
    def mark_unhealthy(self, error: Exception) -> None:
        """标记会话为不健康状态。"""
        self.healthy = False
        self.last_error = error
        self.consecutive_failures += 1
        self.total_failures += 1
        self.last_failure_time = datetime.now()
    
    def mark_healthy(self) -> None:
        """标记会话为健康状态。"""
        self.healthy = True
        self.consecutive_failures = 0
        self.last_error = None
    
    def should_retry(self, max_consecutive_failures: int = 5) -> bool:
        """检查是否应该重试连接"""
        if self.consecutive_failures >= max_consecutive_failures:
            return False
        
        # 如果最近失败，等待一段时间再重试
        if self.last_failure_time:
            cooldown_period = timedelta(minutes=min(5, self.consecutive_failures))
            if datetime.now() - self.last_failure_time < cooldown_period:
                return False
        
        return True


class SessionManager:
    """
    管理MCP客户端会话的生命周期，包括创建、初始化和健康监控。
    
    负责:
    - 创建和初始化客户端会话
    - 会话健康监控
    - 会话恢复和重连
    """
    
    def __init__(
        self, 
        config_provider: ConfigProvider, 
        connection_manager: ConnectionManager,
        logger: Optional[Logger] = None
    ):
        """
        初始化会话管理器。
        
        Args:
            config_provider: 配置提供器
            connection_manager: 连接管理器
            logger: 日志记录器
        """
        self.config_provider = config_provider
        self.connection_manager = connection_manager
        self.logger = logger or Logger("session_manager")
        
        self.sessions: Dict[str, ServerSession] = {}
        self.session_lock = Lock()
        self.initialized = False
        self.exit_stack = AsyncExitStack()      
    
    async def __aenter__(self):
        """异步上下文管理器入口。"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出，关闭所有会话。"""
        await self.close_all()
    
    async def get_session(self, server_name: str) -> ClientSession:
        """
        获取指定服务器的会话，如果不存在或不健康则创建新的。
        
        Args:
            server_name: 服务器名称
            
        Returns:
            客户端会话
            
        Raises:
            ValueError: 如果服务器配置无效
            ConnectionError: 如果连接失败或达到最大失败次数
        """
        async with self.session_lock:
            # 检查是否已有健康的会话
            if server_name in self.sessions:
                session_info = self.sessions[server_name]
                if session_info.healthy:
                    return session_info.session
                
                # 会话不健康，检查是否应该重试
                if not session_info.should_retry():
                    self.logger.warning(
                        f"服务器'{server_name}'连续失败{session_info.consecutive_failures}次，"
                        f"等待冷却期结束后再重试"
                    )
                    raise ConnectionError(
                        f"服务器'{server_name}'暂时不可用，"
                        f"连续失败{session_info.consecutive_failures}次"
                    )
                
                # 清理不健康的会话
                self.logger.info(f"清理服务器'{server_name}'的不健康会话，准备重新连接")
                try:
                    await self.close_session(server_name)
                except Exception as e:
                    self.logger.warning(f"清理会话时出错: {e}")
            
            # 创建新会话
            return await self._create_and_initialize_session(server_name)
    
    async def _create_and_initialize_session(self, server_name: str) -> ClientSession:
        """创建并初始化会话。"""
        config = self.config_provider.get_server_config(server_name)
        if not config:
            raise ValueError(f"未找到服务器'{server_name}'的配置")
        
        self.logger.info(f"正在创建服务器'{server_name}'的会话")
        try:
            # 1. 获取连接的异步上下文管理器
            connection_cm = await self.connection_manager.create_connection(server_name)

            # 2. 使用 SessionManager 的 exit_stack 进入连接上下文
            read_stream, write_stream = await self.exit_stack.enter_async_context(connection_cm)
            self.logger.info(f"服务器'{server_name}'的连接上下文已进入")

            # Yield control to the event loop to allow stdio_client's internal tasks to progress.
            # A small delay can help ensure the subprocess is fully ready.
            await asyncio.sleep(0.1)

            # 3. 计算超时
            timeout = None
            if "read_timeout_seconds" in config:
                timeout = timedelta(seconds=config["read_timeout_seconds"])

            # 4. 创建 ClientSession 实例并将其作为异步上下文添加到 exit_stack
            #    This assumes ClientSession is an async context manager.
            self.logger.info(f"准备进入服务器'{server_name}'的 ClientSession 上下文")
            client_session_context = ClientSession(read_stream, write_stream, read_timeout_seconds=timeout)
            session = await self.exit_stack.enter_async_context(client_session_context)
            self.logger.info(f"服务器'{server_name}'的 ClientSession 上下文已进入")

            # The sleep previously here did not resolve the hang, removing it.
            
            # 5. 初始化会话实例 (returned by __aenter__ of ClientSession)
            self.logger.info(f"正在初始化服务器'{server_name}'的 ClientSession 实例 (调用 .initialize())")
            init_result = await session.initialize()
            
            # 保存会话和能力
            server_session = ServerSession(
                server_name=server_name,
                session=session,
                capabilities=init_result.capabilities
            )
            
            self.sessions[server_name] = server_session
            
            self.logger.info(f"服务器'{server_name}'的会话已成功初始化")
            
            return session
            
        except Exception as e:
            self.logger.error(f"创建服务器'{server_name}'的会话失败: {e}")
            
            # 如果存在旧会话，标记为不健康
            if server_name in self.sessions:
                self.sessions[server_name].mark_unhealthy(e)
                
            raise ConnectionError(f"无法创建服务器'{server_name}'的会话: {e}") from e
    
    async def execute_with_retry(
        self, 
        server_name: str, 
        operation: str,
        method_name: str,
        method_args: Optional[Dict[str, Any]] = None,
        max_retries: int = 3  # 增加默认重试次数
    ) -> Any:
        """
        在指定服务器上执行操作，支持智能重试。
        
        Args:
            server_name: 服务器名称
            operation: 操作名称（用于日志）
            method_name: 要调用的方法名
            method_args: 方法参数
            max_retries: 最大重试次数（默认3次）
            
        Returns:
            操作结果
            
        Raises:
            Exception: 如果所有重试都失败
        """
        method_args = method_args or {}
        retries = 0
        last_error = None
        
        # 检查是否有现有的不健康会话，且不应重试
        if server_name in self.sessions:
            session_info = self.sessions[server_name]
            if not session_info.healthy and not session_info.should_retry():
                self.logger.warning(
                    f"服务器'{server_name}'连续失败次数过多({session_info.consecutive_failures})，"
                    f"跳过重试直到冷却期结束"
                )
                raise ConnectionError(f"服务器'{server_name}'暂时不可用，已达到最大连续失败次数")
        
        while retries <= max_retries:
            try:
                # 获取会话（可能是新的，如果前一个失败）
                session = await self.get_session(server_name)
                
                # 执行操作
                method = getattr(session, method_name)
                result = await method(**method_args)
                
                # 成功后标记会话为健康
                if server_name in self.sessions:
                    self.sessions[server_name].mark_healthy()
                
                # 如果这是重试后的成功，记录恢复日志
                if retries > 0:
                    self.logger.info(f"服务器'{server_name}'在第{retries+1}次尝试后成功恢复")
                
                return result
                
            except Exception as e:
                retries += 1
                last_error = e
                
                self.logger.warning(
                    f"在服务器'{server_name}'上执行操作'{operation}'失败 "
                    f"(尝试 {retries}/{max_retries+1}): {e}"
                )
                
                # 标记会话为不健康
                if server_name in self.sessions:
                    self.sessions[server_name].mark_unhealthy(e)
                
                # 最后一次尝试失败，抛出异常
                if retries > max_retries:
                    break
                
                # 指数退避重试间隔，最大30秒
                delay = min(30.0, 2.0 ** retries + 0.5 * retries)
                self.logger.info(f"等待{delay:.1f}秒后重试...")
                await asyncio.sleep(delay)
        
        # 所有重试都失败
        self.logger.error(
            f"服务器'{server_name}'上的操作'{operation}'在{max_retries+1}次尝试后仍然失败"
        )
        raise last_error or Exception(f"在服务器'{server_name}'上执行操作'{operation}'失败")
    
    def get_capabilities(self, server_name: str) -> Optional[ServerCapabilities]:
        """获取服务器的能力。"""
        if server_name in self.sessions and self.sessions[server_name].healthy:
            return self.sessions[server_name].capabilities
        return None
    
    def get_server_names_with_capability(self, capability_name: str) -> List[str]:
        """获取具有指定能力的所有服务器名称。"""
        result = []
        
        for name, session_info in self.sessions.items():
            if not session_info.healthy:
                continue
                
            capabilities = session_info.capabilities
            if not capabilities:
                continue
                
            if getattr(capabilities, capability_name, False):
                result.append(name)
                
        return result
    
    async def close_session(self, server_name: str) -> None:
        """关闭指定服务器的会话。"""
        # 连接管理器会负责底层连接的关闭
        await self.connection_manager.close_connection(server_name)
        
        # 从会话映射中移除
        if server_name in self.sessions:
            del self.sessions[server_name]
            
    async def close_all(self) -> None:
        """关闭所有会话和管理的上下文。"""
        self.logger.info("正在关闭所有会话和管理的上下文")

        try:
            # 关闭由 SessionManager 的 exit_stack 管理的所有上下文 (现在包括连接和会话)
            # 这将按 LIFO 顺序退出，确保先关闭依赖的资源（如会话使用的流），
            # 然后关闭被依赖的资源（如连接上下文 stdio_client）
            await self.exit_stack.aclose()
            self.logger.info("已关闭所有由 SessionManager AsyncExitStack 管理的上下文 (连接和会话)")

            # 清理会话映射
            self.sessions.clear()

            # ConnectionManager.close_all() 不再需要显式调用，因为连接生命周期由 exit_stack 管理

            self.logger.info("所有会话和连接已成功关闭")
        except Exception as e:
            self.logger.error(f"关闭会话或连接时出错: {e}")
            # 重新抛出异常以便上层了解错误
            raise
