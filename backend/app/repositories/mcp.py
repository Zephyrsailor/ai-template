"""
MCP Repository - MCP服务器数据访问层
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update, delete
from datetime import datetime

from ..core.repository import BaseRepository
from ..domain.models.mcp import MCPServer
from ..core.logging import get_logger

logger = get_logger(__name__)


class MCPRepository(BaseRepository[MCPServer]):
    """MCP服务器Repository - 数据库操作"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(MCPServer, session)
        logger.info("MCP Repository初始化")
    
    # === 基础查询方法 ===
    
    async def find_by_name(self, name: str, user_id: Optional[str] = None) -> Optional[MCPServer]:
        """根据名称查找MCP服务器"""
        try:
            stmt = select(MCPServer).where(MCPServer.name == name)
            if user_id:
                stmt = stmt.where(MCPServer.user_id == user_id)
            
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"查找MCP服务器失败: {str(e)}")
            return None
    
    async def find_by_user_id(self, user_id: str, active_only: bool = False) -> List[MCPServer]:
        """根据用户ID查找MCP服务器列表"""
        try:
            stmt = select(MCPServer).where(MCPServer.user_id == user_id)
            if active_only:
                stmt = stmt.where(MCPServer.active == True)
            
            # 按创建时间排序
            stmt = stmt.order_by(MCPServer.created_at.desc())
            
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"查找用户MCP服务器失败: {str(e)}")
            return []
    
    async def find_active_servers(self, user_id: Optional[str] = None) -> List[MCPServer]:
        """查找活跃的MCP服务器"""
        try:
            stmt = select(MCPServer).where(MCPServer.active == True)
            if user_id:
                stmt = stmt.where(MCPServer.user_id == user_id)
            
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"查找活跃MCP服务器失败: {str(e)}")
            return []
    
    async def find_by_transport(self, transport: str, user_id: Optional[str] = None) -> List[MCPServer]:
        """根据传输类型查找MCP服务器"""
        try:
            stmt = select(MCPServer).where(MCPServer.transport == transport)
            if user_id:
                stmt = stmt.where(MCPServer.user_id == user_id)
            
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"根据传输类型查找MCP服务器失败: {str(e)}")
            return []
    
    async def find_by_status(self, status: str, user_id: Optional[str] = None) -> List[MCPServer]:
        """根据状态查找MCP服务器"""
        try:
            stmt = select(MCPServer).where(MCPServer.status == status)
            if user_id:
                stmt = stmt.where(MCPServer.user_id == user_id)
            
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"根据状态查找MCP服务器失败: {str(e)}")
            return []
    
    # === 用户权限相关方法 ===
    
    async def check_user_ownership(self, server_id: str, user_id: str) -> bool:
        """检查用户是否拥有指定服务器"""
        try:
            stmt = select(MCPServer).where(
                and_(
                    MCPServer.id == server_id,
                    MCPServer.user_id == user_id
                )
            )
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"检查用户服务器所有权失败: {str(e)}")
            return False
    
    async def get_user_server(self, server_id: str, user_id: str) -> Optional[MCPServer]:
        """获取用户的特定服务器"""
        try:
            stmt = select(MCPServer).where(
                and_(
                    MCPServer.id == server_id,
                    MCPServer.user_id == user_id
                )
            )
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取用户服务器失败: {str(e)}")
            return None
    
    async def get_user_servers(self, user_id: str, active_only: bool = False) -> List[MCPServer]:
        """获取用户的所有服务器 - 兼容方法"""
        return await self.find_by_user_id(user_id, active_only=active_only)
    
    # === 状态更新方法 ===
    
    async def update_server_status(self, server_id: str, status: str, error_message: Optional[str] = None) -> bool:
        """更新服务器状态 - 移除事务管理，由上层负责"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now()
            }
            
            if error_message is not None:
                update_data["last_error"] = error_message
            
            if status == "active":
                update_data["last_connected_at"] = datetime.now()
                update_data["last_error"] = None  # 清除错误信息
            
            # 只执行更新，不管理事务
            stmt = update(MCPServer).where(MCPServer.id == server_id).values(**update_data)
            result = await self._session.execute(stmt)
            
            success = result.rowcount > 0
            if success:
                logger.debug(f"更新服务器状态成功: {server_id} -> {status}")
            else:
                logger.warning(f"更新服务器状态失败，未找到服务器: {server_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"更新服务器状态失败: {str(e)}")
            raise  # 抛出异常，让上层处理事务
    
    async def update_server_capabilities(self, server_id: str, capabilities: List[str]) -> bool:
        """更新服务器能力 - 移除事务管理，由上层负责"""
        try:
            stmt = update(MCPServer).where(MCPServer.id == server_id).values(
                capabilities=capabilities,
                updated_at=datetime.now()
            )
            result = await self._session.execute(stmt)
            
            success = result.rowcount > 0
            if success:
                logger.debug(f"更新服务器能力成功: {server_id}")
            
            return success
        except Exception as e:
            logger.error(f"更新服务器能力失败: {str(e)}")
            raise  # 抛出异常，让上层处理事务
    
    async def update_last_connected(self, server_id: str) -> bool:
        """更新最后连接时间 - 移除事务管理，由上层负责"""
        try:
            stmt = update(MCPServer).where(MCPServer.id == server_id).values(
                last_connected_at=datetime.now(),
                updated_at=datetime.now()
            )
            result = await self._session.execute(stmt)
            
            success = result.rowcount > 0
            if success:
                logger.debug(f"更新最后连接时间成功: {server_id}")
            
            return success
        except Exception as e:
            logger.error(f"更新最后连接时间失败: {str(e)}")
            raise  # 抛出异常，让上层处理事务
    
    # === 批量操作方法 ===
    
    async def activate_servers(self, server_ids: List[str], user_id: str) -> int:
        """批量激活服务器"""
        try:
            stmt = update(MCPServer).where(
                and_(
                    MCPServer.id.in_(server_ids),
                    MCPServer.user_id == user_id
                )
            ).values(
                active=True,
                updated_at=datetime.now()
            )
            result = await self._session.execute(stmt)
            
            return result.rowcount
        except Exception as e:
            logger.error(f"批量激活服务器失败: {str(e)}")
            return 0
    
    async def deactivate_servers(self, server_ids: List[str], user_id: str) -> int:
        """批量停用服务器"""
        try:
            stmt = update(MCPServer).where(
                and_(
                    MCPServer.id.in_(server_ids),
                    MCPServer.user_id == user_id
                )
            ).values(
                active=False,
                updated_at=datetime.now()
            )
            result = await self._session.execute(stmt)
            
            return result.rowcount
        except Exception as e:
            logger.error(f"批量停用服务器失败: {str(e)}")
            return 0
    
    async def bulk_delete_user_servers(self, server_ids: List[str], user_id: str) -> int:
        """批量删除用户的服务器"""
        try:
            stmt = delete(MCPServer).where(
                and_(
                    MCPServer.id.in_(server_ids),
                    MCPServer.user_id == user_id
                )
            )
            result = await self._session.execute(stmt)
            
            return result.rowcount
        except Exception as e:
            logger.error(f"批量删除用户服务器失败: {str(e)}")
            return 0
    
    # === 统计方法 ===
    
    async def count_user_servers(self, user_id: str, active_only: bool = False) -> int:
        """统计用户服务器数量"""
        try:
            stmt = select(MCPServer).where(MCPServer.user_id == user_id)
            if active_only:
                stmt = stmt.where(MCPServer.active == True)
            
            result = await self._session.execute(stmt)
            return len(list(result.scalars().all()))
        except Exception as e:
            logger.error(f"统计用户服务器数量失败: {str(e)}")
            return 0
    
    async def get_server_stats(self, user_id: str) -> Dict[str, int]:
        """获取用户服务器统计信息"""
        try:
            servers = await self.find_by_user_id(user_id)
            
            stats = {
                "total": len(servers),
                "active": len([s for s in servers if s.active]),
                "inactive": len([s for s in servers if not s.active]),
                "connected": len([s for s in servers if s.status == "active"]),
                "error": len([s for s in servers if s.status == "error"]),
            }
            
            # 按传输类型统计
            transport_stats = {}
            for server in servers:
                transport = server.transport
                transport_stats[transport] = transport_stats.get(transport, 0) + 1
            
            stats["by_transport"] = transport_stats
            
            return stats
        except Exception as e:
            logger.error(f"获取服务器统计信息失败: {str(e)}")
            return {}
    
    def get_table_name(self) -> str:
        """获取表名"""
        return "mcp_servers" 