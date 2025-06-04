"""
用户服务
"""
import hashlib
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.models.user import User, UserRole
from ..domain.schemas.user import UserCreate, UserUpdate, PasswordChange
from ..repositories.user import UserRepository
from ..core.service import BaseService
from ..core.logging import get_logger
from ..core.security import create_access_token, verify_password, get_password_hash
from ..core.errors import ValidationException, NotFoundException, AuthenticationException

logger = get_logger(__name__)

class UserService(BaseService[User, UserRepository]):
    """用户服务"""
    
    def __init__(self, session: AsyncSession):
        repository = UserRepository(session)
        super().__init__(repository)
        logger.info("用户服务初始化")
    
    def get_entity_name(self) -> str:
        """获取实体名称"""
        return "用户"
    
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        return get_password_hash(password)
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """验证密码"""
        return verify_password(password, hashed_password)
    
    def create_access_token_for_user(self, user: User) -> str:
        """为用户创建访问令牌"""
        return create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role.value if hasattr(user.role, 'value') else user.role
        )
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码（公开方法）"""
        return self._verify_password(plain_password, hashed_password)
    
    async def update_password(self, user_id: str, new_password: str) -> bool:
        """更新用户密码"""
        try:
            hashed_password = self._hash_password(new_password)
            updated_user = await self.repository.update(user_id, {"hashed_password": hashed_password})
            return updated_user is not None
        except Exception as e:
            logger.error(f"更新密码失败: {str(e)}")
            return False
    
    async def create_user(self, user_data: UserCreate) -> User:
        """创建用户"""
        try:
            # 检查用户名是否已存在
            existing_user = await self.repository.get_by_username(user_data.username)
            if existing_user:
                raise ValidationException("用户名已存在")
            
            # 检查邮箱是否已存在
            existing_email = await self.repository.get_by_email(user_data.email)
            if existing_email:
                raise ValidationException("邮箱已存在")
            
            # 创建用户数据
            user_dict = {
                "username": user_data.username,
                "email": user_data.email,
                "full_name": user_data.full_name,
                "hashed_password": self._hash_password(user_data.password),
                "role": UserRole.USER.value,
            }
            
            # 创建用户
            user = await self.repository.create(user_dict)
            
            logger.info(f"用户创建成功: {user_data.username}")
            return user
            
        except Exception as e:
            logger.error(f"创建用户失败: {str(e)}")
            raise
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return await self.repository.get_by_username(username)
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return await self.repository.get_by_email(email)
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据用户ID获取用户"""
        return await self.repository.get_by_id(user_id)
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """用户认证"""
        try:
            logger.info(f"开始认证用户: {username}")
            user = await self.repository.get_by_username(username)
            if not user:
                logger.warning(f"用户不存在: {username}")
                return None
            
            logger.info(f"找到用户: {user.username}, ID: {user.id}")
            logger.info(f"数据库中的密码哈希: {user.hashed_password[:20]}...")
            logger.info(f"输入的密码: {password}")
            
            # 测试密码验证
            verification_result = self._verify_password(password, user.hashed_password)
            logger.info(f"密码验证结果: {verification_result}")
            
            if not verification_result:
                logger.warning(f"密码验证失败: {username}")
                return None
            
            if not user.is_active:
                logger.warning(f"用户账户已被禁用: {username}")
                raise AuthenticationException("用户账户已被禁用")
            
            # 更新最后登录时间
            await self.repository.update(user.id, {"last_login": datetime.now()})
            
            logger.info(f"用户认证成功: {username}")
            return user
            
        except Exception as e:
            logger.error(f"用户认证失败: {str(e)}")
            return None
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> User:
        """更新用户"""
        try:
            # 检查用户是否存在
            user = await self.repository.get_by_id(user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 准备更新数据
            update_dict = {}
            if user_data.email is not None:
                # 检查邮箱是否已被其他用户使用
                existing_email = await self.repository.get_by_email(user_data.email)
                if existing_email and existing_email.id != user_id:
                    raise ValidationException("邮箱已被其他用户使用")
                update_dict["email"] = user_data.email
            
            if user_data.full_name is not None:
                update_dict["full_name"] = user_data.full_name
            
            if user_data.is_active is not None:
                update_dict["is_active"] = user_data.is_active
            
            # 更新用户
            updated_user = await self.repository.update(user_id, update_dict)
            
            logger.info(f"用户更新成功: {user_id}")
            return updated_user
            
        except Exception as e:
            logger.error(f"更新用户失败: {str(e)}")
            raise
    
    async def change_password(self, user_id: str, password_data: PasswordChange) -> bool:
        """修改密码"""
        try:
            # 检查用户是否存在
            user = await self.repository.get_by_id(user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 验证旧密码
            if not self._verify_password(password_data.old_password, user.hashed_password):
                raise AuthenticationException("旧密码错误")
            
            # 更新密码
            await self.repository.update(user_id, {
                "hashed_password": self._hash_password(password_data.new_password)
            })
            
            logger.info(f"密码修改成功: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"修改密码失败: {str(e)}")
            raise
    
    async def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        try:
            # 检查用户是否存在
            user = await self.repository.get_by_id(user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 删除用户
            success = await self.repository.delete(user_id)
            
            if success:
                logger.info(f"用户删除成功: {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除用户失败: {str(e)}")
            raise
    
    async def list_users(self, limit: Optional[int] = None, offset: int = 0) -> List[User]:
        """获取用户列表"""
        return await self.repository.get_active_users(limit=limit, offset=offset)
    
    async def count_users(self) -> int:
        """获取用户总数"""
        return await self.repository.count_active_users()
    
    # 重写BaseService的权限检查方法
    async def _can_access(self, entity: User, user_id: str) -> bool:
        """检查是否可以访问用户信息"""
        # 用户只能访问自己的信息，管理员可以访问所有用户
        if entity.id == user_id:
            return True
        
        # 检查当前用户是否为管理员
        current_user = await self.repository.get_by_id(user_id)
        return current_user and current_user.is_admin
    
    async def _can_update(self, entity: User, user_id: str) -> bool:
        """检查是否可以更新用户信息"""
        return await self._can_access(entity, user_id)
    
    async def _can_delete(self, entity: User, user_id: str) -> bool:
        """检查是否可以删除用户"""
        # 只有管理员可以删除用户，且不能删除自己
        current_user = await self.repository.get_by_id(user_id)
        return (current_user and current_user.is_admin and 
                entity.id != user_id)
    
    async def _validate_create_data(self, data: dict) -> None:
        """验证创建数据"""
        if not data.get("username"):
            raise ValidationException("用户名不能为空")
        if not data.get("email"):
            raise ValidationException("邮箱不能为空")
        if not data.get("password"):
            raise ValidationException("密码不能为空") 