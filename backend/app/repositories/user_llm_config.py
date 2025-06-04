"""
用户LLM配置Repository - 数据访问层
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update, delete
from datetime import datetime

from ..core.repository import BaseRepository
from ..domain.models.user_llm_config import UserLLMConfigModel
from ..core.logging import get_logger

logger = get_logger(__name__)


class UserLLMConfigRepository(BaseRepository[UserLLMConfigModel]):
    """用户LLM配置Repository - 数据库操作"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(UserLLMConfigModel, session)
        logger.info("用户LLM配置Repository初始化")
    
    # === 基础查询方法 ===
    
    async def find_by_user_id(self, user_id: str) -> List[UserLLMConfigModel]:
        """根据用户ID查找所有配置"""
        try:
            stmt = select(UserLLMConfigModel).where(UserLLMConfigModel.user_id == user_id)
            stmt = stmt.order_by(UserLLMConfigModel.is_default.desc(), UserLLMConfigModel.created_at.desc())
            
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"查找用户LLM配置失败: {str(e)}")
            return []
    
    async def find_by_user_and_name(self, user_id: str, config_name: str) -> Optional[UserLLMConfigModel]:
        """根据用户ID和配置名称查找配置"""
        try:
            stmt = select(UserLLMConfigModel).where(
                and_(
                    UserLLMConfigModel.user_id == user_id,
                    UserLLMConfigModel.config_name == config_name
                )
            )
            
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"查找用户配置失败: {str(e)}")
            return None
    
    async def find_default_config(self, user_id: str) -> Optional[UserLLMConfigModel]:
        """查找用户的默认配置"""
        try:
            stmt = select(UserLLMConfigModel).where(
                and_(
                    UserLLMConfigModel.user_id == user_id,
                    UserLLMConfigModel.is_default == True
                )
            )
            
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"查找用户默认配置失败: {str(e)}")
            return None
    
    async def find_by_provider(self, user_id: str, provider: str) -> List[UserLLMConfigModel]:
        """根据提供商查找配置"""
        try:
            stmt = select(UserLLMConfigModel).where(
                and_(
                    UserLLMConfigModel.user_id == user_id,
                    UserLLMConfigModel.provider == provider
                )
            )
            
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"根据提供商查找配置失败: {str(e)}")
            return []
    
    # === 用户权限相关方法 ===
    
    async def check_user_ownership(self, config_id: str, user_id: str) -> bool:
        """检查用户是否拥有指定配置"""
        try:
            stmt = select(UserLLMConfigModel).where(
                and_(
                    UserLLMConfigModel.id == config_id,
                    UserLLMConfigModel.user_id == user_id
                )
            )
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"检查用户配置所有权失败: {str(e)}")
            return False
    
    async def get_user_config(self, config_id: str, user_id: str) -> Optional[UserLLMConfigModel]:
        """获取用户的特定配置"""
        try:
            stmt = select(UserLLMConfigModel).where(
                and_(
                    UserLLMConfigModel.id == config_id,
                    UserLLMConfigModel.user_id == user_id
                )
            )
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取用户配置失败: {str(e)}")
            return None
    
    # === 默认配置管理 ===
    
    async def set_default_config(self, config_id: str, user_id: str) -> bool:
        """设置默认配置（会取消其他配置的默认状态）"""
        try:
            # 先取消所有默认配置
            await self.clear_default_configs(user_id)
            
            # 设置新的默认配置
            stmt = update(UserLLMConfigModel).where(
                and_(
                    UserLLMConfigModel.id == config_id,
                    UserLLMConfigModel.user_id == user_id
                )
            ).values(
                is_default=True,
                updated_at=datetime.now()
            )
            
            result = await self._session.execute(stmt)
            await self._session.commit()
            
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"设置默认配置失败: {str(e)}")
            await self._session.rollback()
            return False
    
    async def clear_default_configs(self, user_id: str) -> int:
        """清除用户所有默认配置"""
        try:
            stmt = update(UserLLMConfigModel).where(
                and_(
                    UserLLMConfigModel.user_id == user_id,
                    UserLLMConfigModel.is_default == True
                )
            ).values(
                is_default=False,
                updated_at=datetime.now()
            )
            
            result = await self._session.execute(stmt)
            await self._session.commit()
            
            return result.rowcount
        except Exception as e:
            logger.error(f"清除默认配置失败: {str(e)}")
            await self._session.rollback()
            return 0
    
    # === 批量操作方法 ===
    
    async def delete_user_configs(self, config_ids: List[str], user_id: str) -> int:
        """批量删除用户配置"""
        try:
            stmt = delete(UserLLMConfigModel).where(
                and_(
                    UserLLMConfigModel.id.in_(config_ids),
                    UserLLMConfigModel.user_id == user_id
                )
            )
            result = await self._session.execute(stmt)
            await self._session.commit()
            
            return result.rowcount
        except Exception as e:
            logger.error(f"批量删除用户配置失败: {str(e)}")
            await self._session.rollback()
            return 0
    
    async def delete_all_user_configs(self, user_id: str) -> int:
        """删除用户所有配置"""
        try:
            stmt = delete(UserLLMConfigModel).where(UserLLMConfigModel.user_id == user_id)
            result = await self._session.execute(stmt)
            await self._session.commit()
            
            return result.rowcount
        except Exception as e:
            logger.error(f"删除用户所有配置失败: {str(e)}")
            await self._session.rollback()
            return 0
    
    # === 统计方法 ===
    
    async def count_user_configs(self, user_id: str) -> int:
        """统计用户配置数量"""
        try:
            stmt = select(UserLLMConfigModel).where(UserLLMConfigModel.user_id == user_id)
            result = await self._session.execute(stmt)
            return len(list(result.scalars().all()))
        except Exception as e:
            logger.error(f"统计用户配置数量失败: {str(e)}")
            return 0
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户配置统计信息"""
        try:
            configs = await self.find_by_user_id(user_id)
            
            stats = {
                "total": len(configs),
                "has_default": any(config.is_default for config in configs),
                "providers": list(set(config.provider for config in configs)),
                "provider_counts": {}
            }
            
            # 按提供商统计
            for config in configs:
                provider = config.provider
                stats["provider_counts"][provider] = stats["provider_counts"].get(provider, 0) + 1
            
            return stats
        except Exception as e:
            logger.error(f"获取用户配置统计失败: {str(e)}")
            return {}
    
    def get_table_name(self) -> str:
        """获取表名"""
        return "user_llm_configs" 