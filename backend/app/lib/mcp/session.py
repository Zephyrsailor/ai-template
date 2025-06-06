"""MCP会话管理器，管理MCP客户端会话的生命周期。"""

import asyncio
from datetime import timedelta, datetime
from typing import Any, Dict, List, Optional, TypeVar

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
        # 保存连接上下文管理器的引用，用于清理
        self.connection_context = None
        self.session_context = None
    
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
    
    async def cleanup(self) -> None:
        """清理会话和连接资源"""
        try:
            # 先关闭会话上下文
            if self.session_context:
                try:
                    await asyncio.wait_for(
                        self.session_context.__aexit__(None, None, None),
                        timeout=2.0  # 2秒超时
                    )
                except asyncio.TimeoutError:
                    # 超时则强制清理
                    pass
                except Exception:
                    # 忽略其他清理错误
                    pass
                finally:
                    self.session_context = None
        except Exception:
            # 忽略清理时的错误，避免阻塞
            pass
        
        try:
            # 再关闭连接上下文
            if self.connection_context:
                try:
                    await asyncio.wait_for(
                        self.connection_context.__aexit__(None, None, None),
                        timeout=2.0  # 2秒超时
                    )
                except asyncio.TimeoutError:
                    # 超时则强制清理
                    pass
                except Exception:
                    # 忽略其他清理错误
                    pass
                finally:
                    self.connection_context = None
        except Exception:
            # 忽略清理时的错误，避免阻塞
            pass


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
            session = await self._create_and_initialize_session(server_name)
            return session
    
    def get_session_lock_waiting_count(self, server_name: str) -> int:
        """获取指定服务器session锁的等待者数量（简单实现）"""
        # 🔥 最小化修复：直接返回0，禁用等待计数
        return 0
    
    async def _create_and_initialize_session(self, server_name: str) -> ClientSession:
        """创建并初始化会话。"""
        config = self.config_provider.get_server_config(server_name)
        if not config:
            raise ValueError(f"未找到服务器'{server_name}'的配置")
        
        self.logger.info(f"正在创建服务器'{server_name}'的会话")
        
        connection_context = None
        session_context = None
        
        try:
            # 1. 获取连接的异步上下文管理器
            connection_context = await self.connection_manager.create_connection(server_name)
            read_stream, write_stream = await connection_context.__aenter__()
            self.logger.info(f"服务器'{server_name}'的连接已建立")

            # 让出控制权，确保子进程完全准备好
            await asyncio.sleep(0.1)

            # 2. 计算超时
            timeout = None
            if "read_timeout_seconds" in config:
                timeout = timedelta(seconds=config["read_timeout_seconds"])

            # 3. 创建 ClientSession 上下文
            self.logger.info(f"准备创建服务器'{server_name}'的 ClientSession")
            session_context = ClientSession(read_stream, write_stream, read_timeout_seconds=timeout)
            session = await session_context.__aenter__()
            self.logger.info(f"服务器'{server_name}'的 ClientSession 已创建")
            
            # 4. 初始化会话
            self.logger.info(f"正在初始化服务器'{server_name}'的会话")
            init_result = await session.initialize()
            
            # 5. 保存会话和能力
            server_session = ServerSession(
                server_name=server_name,
                session=session,
                capabilities=init_result.capabilities
            )
            # 保存上下文引用用于清理
            server_session.connection_context = connection_context
            server_session.session_context = session_context
            
            self.sessions[server_name] = server_session

            
            # 🔧 修复：通知ConnectionManager连接成功
            self.connection_manager._active_connections[server_name] = True
            
            self.logger.info(f"服务器'{server_name}'的会话已成功初始化")
            
            return session
            
        except Exception as e:
            self.logger.error(f"创建服务器'{server_name}'的会话失败: {e}")
            
            # 清理已创建的上下文
            try:
                if session_context:
                    await session_context.__aexit__(type(e), e, e.__traceback__)
            except Exception:
                pass
            
            try:
                if connection_context:
                    await connection_context.__aexit__(type(e), e, e.__traceback__)
            except Exception:
                pass
            
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
        if server_name in self.sessions:
            session_info = self.sessions[server_name]
            await session_info.cleanup()
            del self.sessions[server_name]
            
            # 🔧 修复：通知ConnectionManager连接已断开
            if server_name in self.connection_manager._active_connections:
                del self.connection_manager._active_connections[server_name]
            
            self.logger.info(f"已关闭服务器'{server_name}'的会话")
            
    async def close_all(self) -> None:
        """关闭所有会话和管理的上下文。"""
        self.logger.info("正在关闭所有会话")

        try:
            # 并行关闭所有会话以提高效率，但设置超时
            close_tasks = []
            for server_name, session_info in list(self.sessions.items()):
                close_tasks.append(session_info.cleanup())
            
            if close_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*close_tasks, return_exceptions=True),
                        timeout=5.0  # 5秒总超时
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("关闭会话超时，强制清理")
            
            # 清理会话映射
            self.sessions.clear()

            self.logger.info("所有会话已成功关闭")
        except Exception as e:
            self.logger.error(f"关闭会话时出错: {e}")
            # 强制清理会话映射
            self.sessions.clear()
            # 不重新抛出异常，避免影响程序退出
