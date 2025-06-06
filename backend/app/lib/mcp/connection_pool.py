"""
MCP连接池 - 管理用户的Hub实例
"""
import asyncio
from typing import Dict, Optional, List
from datetime import datetime
from app.core.logging import get_logger
from app.domain.models.mcp import MCPServer
from .hub import MCPHub

logger = get_logger(__name__)

class MCPConnectionPool:
    """简化的MCP连接池 - 单例模式
    
    🎯 核心职责：
    1. 管理用户的Hub实例（一用户一Hub）
    2. 简单的创建/获取/删除逻辑
    3. 用户隔离
    
    ❌ 不负责：
    - 复杂的状态管理
    - 异步创建管理
    - 配置热更新
    """
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        self._user_hubs: Dict[str, MCPHub] = {}
        self._last_access: Dict[str, datetime] = {}
        self._instance_lock = asyncio.Lock()
        self._initialized = True
        
        logger.info("MCPConnectionPool初始化完成")

    async def get_user_hub(self, user_id: str) -> Optional[MCPHub]:
        """
        获取用户的Hub实例
        
        Args:
            user_id: 用户ID
            
        Returns:
            Hub实例或None
        """
        async with self._instance_lock:
            self._last_access[user_id] = datetime.now()
            return self._user_hubs.get(user_id)

    async def create_user_hub(self, user_id: str, servers: List[MCPServer]) -> MCPHub:
        """
        为用户创建新的Hub实例
        
        Args:
            user_id: 用户ID
            servers: 服务器配置列表
            
        Returns:
            创建的Hub实例
        """
        async with self._instance_lock:
            # 如果已存在，先关闭旧的
            if user_id in self._user_hubs:
                await self._close_hub(user_id)
            
            # 创建新Hub
            config_dict = self._build_hub_config(servers, user_id)
            hub = MCPHub(config_dict=config_dict)
            
            # 存储并返回
            self._user_hubs[user_id] = hub
            self._last_access[user_id] = datetime.now()
            
            logger.info(f"为用户 {user_id} 创建新Hub，包含 {len(servers)} 个服务器")
            return hub

    async def get_or_create_user_hub(self, user_id: str, servers: List[MCPServer]) -> MCPHub:
        """
        获取或创建用户的Hub实例
        
        Args:
            user_id: 用户ID
            servers: 服务器配置列表（用于创建）
            
        Returns:
            Hub实例
        """
        # 先尝试获取
        hub = await self.get_user_hub(user_id)
        if hub:
            return hub
        
        # 不存在则创建
        return await self.create_user_hub(user_id, servers)

    async def update_user_hub_servers(self, user_id: str, servers: List[MCPServer]) -> MCPHub:
        """
        更新用户Hub的服务器配置
        
        Args:
            user_id: 用户ID
            servers: 新的服务器配置列表
            
        Returns:
            更新后的Hub实例
        """
        # 直接重新创建Hub（简单可靠）
        return await self.create_user_hub(user_id, servers)

    async def remove_user_hub(self, user_id: str) -> bool:
        """
        移除用户的Hub实例
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功移除
        """
        async with self._instance_lock:
            if user_id in self._user_hubs:
                await self._close_hub(user_id)
                return True
            return False

    async def _close_hub(self, user_id: str):
        """关闭并清理用户的Hub"""
        if user_id in self._user_hubs:
            hub = self._user_hubs[user_id]
            try:
                await hub.shutdown()  # Hub的正确关闭方法是shutdown
            except Exception as e:
                logger.error(f"关闭用户 {user_id} 的Hub时出错: {e}")
            
            del self._user_hubs[user_id]
            self._last_access.pop(user_id, None)
            logger.info(f"已关闭用户 {user_id} 的Hub")

    def get_connection_status(self, user_id: str) -> str:
        """获取连接状态（简化版）"""
        if user_id in self._user_hubs:
            return "connected"
        return "disconnected"

    def is_connected(self, user_id: str) -> bool:
        """检查是否已连接"""
        return user_id in self._user_hubs

    async def disconnect_user(self, user_id: str) -> bool:
        """断开用户连接"""
        return await self.remove_user_hub(user_id)

    async def cleanup_inactive_connections(self):
        """清理不活跃的连接"""
        cutoff_time = datetime.now()
        # 简化：暂时不实现自动清理，避免复杂性
        pass

    # === 兼容性方法（保持现有API） ===
    
    async def get_user_hub_wait(self, user_id: str, servers: Optional[List[MCPServer]] = None, timeout: float = 10.0) -> Optional[MCPHub]:
        """兼容方法：获取Hub并等待（实际上直接创建）"""
        if not servers:
            return await self.get_user_hub(user_id)
        return await self.get_or_create_user_hub(user_id, servers)

    async def get_user_hub_no_create(self, user_id: str) -> Optional[MCPHub]:
        """兼容方法：仅获取，不创建"""
        return await self.get_user_hub(user_id)

    def _build_hub_config(self, servers: List[MCPServer], user_id: str) -> Dict:
        """构建Hub配置"""
        mcp_servers = {}
        
        for server in servers:
            if not server.active:
                continue
                
            server_config = {
                "name": server.name,
                "description": server.description or "",
                "transport": server.transport,
                "timeout": server.timeout or 30,
                "active": True,
                "user_id": user_id
            }
            
            if server.transport == "stdio":
                if not server.command:
                    logger.warning(f"服务器 {server.name} 缺少command配置")
                    continue
                
                server_config.update({
                    "command": server.command,
                    "args": self._parse_args(server.args),
                    "env": self._parse_env(server.env)
                })
            
            elif server.transport in ["http", "sse"]:
                if not server.url:
                    logger.warning(f"服务器 {server.name} 缺少URL配置")
                    continue
                server_config["url"] = server.url
            
            mcp_servers[server.name] = server_config
        
        return {"mcp_servers": mcp_servers}
    
    def _parse_args(self, args) -> List[str]:
        """解析参数"""
        if isinstance(args, list):
            return [str(arg) for arg in args]
        elif isinstance(args, str):
            try:
                import json
                parsed = json.loads(args)
                return [str(arg) for arg in parsed] if isinstance(parsed, list) else []
            except:
                return []
        return []
    
    def _parse_env(self, env) -> Dict[str, str]:
        """解析环境变量"""
        if isinstance(env, dict):
            return {str(k): str(v) for k, v in env.items()}
        elif isinstance(env, str):
            try:
                import json
                parsed = json.loads(env)
                return {str(k): str(v) for k, v in parsed.items()} if isinstance(parsed, dict) else {}
            except:
                return {}
        return {}

# 全局连接池实例
connection_pool = MCPConnectionPool()

def get_connection_pool() -> MCPConnectionPool:
    """获取全局连接池实例"""
    return connection_pool 