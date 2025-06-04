"""
用户Repository - 用户数据访问层
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.repository import BaseRepository
from ..domain.models.user import User
from ..core.logging import get_logger

logger = get_logger(__name__)

class UserRepository(BaseRepository[User]):
    """用户Repository - 数据库操作"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)
        logger.info("用户Repository初始化")
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        try:
            stmt = select(User).where(User.username == username)
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"根据用户名获取用户失败: {str(e)}")
            return None
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        try:
            stmt = select(User).where(User.email == email)
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"根据邮箱获取用户失败: {str(e)}")
            return None
    
    async def get_active_users(self, limit: Optional[int] = None, offset: int = 0) -> List[User]:
        """获取活跃用户列表（所有用户都是活跃的）"""
        try:
            stmt = select(User)
            
            if offset > 0:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"获取活跃用户列表失败: {str(e)}")
            return []
    
    async def count_active_users(self) -> int:
        """获取活跃用户总数（所有用户都是活跃的）"""
        try:
            from sqlalchemy import func
            stmt = select(func.count(User.id))
            result = await self._session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"获取活跃用户总数失败: {str(e)}")
            return 0
    
    def get_table_name(self) -> str:
        """获取表名"""
        return "users" 