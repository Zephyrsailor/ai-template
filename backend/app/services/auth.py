"""
认证服务 - 提供用户认证、令牌管理等功能
"""
from datetime import datetime, timedelta
from typing import Optional

from ..core.config import get_settings
from ..core.security import get_password_hash, verify_password, create_access_token
from ..domain.models.user import User, UserRole
from ..core.errors import (
    ValidationException, AuthenticationException, ConflictException,
    UserNotFoundException, UserAlreadyExistsException
)
from ..core.logging import get_service_logger
from .user import UserService

logger = get_service_logger()
settings = get_settings()


class AuthService:
    """认证服务"""
    
    def __init__(self):
        """初始化认证服务"""
        self.user_service = UserService()
    
    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None
    ) -> User:
        """
        注册新用户
        
        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            full_name: 全名
            
        Returns:
            创建的用户对象
            
        Raises:
            UserAlreadyExistsException: 当用户名或邮箱已存在时
        """
        try:
            # 检查用户名是否已存在
            existing_user = self.user_service.get_user_by_username(username)
            if existing_user:
                raise UserAlreadyExistsException(username)
            
            # 检查邮箱是否已被注册
            existing_email = self.user_service.get_user_by_email(email)
            if existing_email:
                raise ConflictException(f"邮箱 '{email}' 已被注册")
            
            # 创建新用户
            user = self.user_service.create_user(
                username=username,
                email=email,
                password=password,
                full_name=full_name,
                role=UserRole.USER
            )
            
            logger.info(f"用户注册成功: {username}")
            return user
            
        except Exception as e:
            logger.error(f"用户注册失败: {str(e)}", exc_info=True)
            raise ValidationException(str(e))
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        验证用户凭据
        
        Args:
            username: 用户名或邮箱
            password: 密码
            
        Returns:
            验证成功的用户对象，失败返回None
        """
        try:
            # 尝试通过用户名查找
            user = self.user_service.get_user_by_username(username)
            
            # 如果用户名查找失败，尝试通过邮箱查找
            if not user:
                user = self.user_service.get_user_by_email(username)
            
            if not user:
                logger.warning(f"用户不存在: {username}")
                return None
            
            # 验证密码
            if not verify_password(password, user.hashed_password):
                logger.warning(f"密码错误: {username}")
                return None
            
            # 检查用户是否激活
            if not user.is_active:
                logger.warning(f"用户未激活: {username}")
                return None
            
            # 更新最后登录时间
            user.last_login = datetime.now()
            self.user_service._save_user(user)
            
            logger.info(f"用户认证成功: {username}")
            return user
            
        except Exception as e:
            logger.error(f"用户认证异常: {e}")
            return None
    
    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        创建访问令牌
        
        Args:
            data: 令牌数据
            expires_delta: 过期时间增量
            
        Returns:
            JWT访问令牌
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode = data.copy()
        to_encode.update({"exp": expire})
        
        return create_access_token(to_encode)
    
    def get_token_expire_minutes(self) -> int:
        """获取令牌过期时间（分钟）"""
        return settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        修改用户密码
        
        Args:
            user_id: 用户ID
            current_password: 当前密码
            new_password: 新密码
            
        Returns:
            是否修改成功
            
        Raises:
            UserNotFoundException: 用户不存在
            AuthenticationException: 当前密码错误
        """
        try:
            user = self.user_service.get_user_by_id(user_id)
            if not user:
                raise UserNotFoundException(user_id)
            
            # 验证当前密码
            if not verify_password(current_password, user.hashed_password):
                raise AuthenticationException("当前密码错误")
            
            # 修改密码
            success = self.user_service.change_password(
                user_id=user_id,
                current_password=current_password,
                new_password=new_password
            )
            
            if success:
                logger.info(f"用户密码修改成功: {user.username}")
            else:
                logger.warning(f"用户密码修改失败: {user.username}")
            
            return success
            
        except AuthenticationException:
            # 重新抛出认证异常
            raise
        except Exception as e:
            logger.error(f"密码修改失败: {str(e)}", exc_info=True)
            raise ValidationException("密码修改失败")
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        通过ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户对象或None
        """
        return self.user_service.get_user_by_id(user_id)
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        通过用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            用户对象或None
        """
        return self.user_service.get_user_by_username(username)
    
    async def update_user_profile(
        self,
        user_id: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None
    ) -> Optional[User]:
        """
        更新用户资料
        
        Args:
            user_id: 用户ID
            email: 新邮箱
            full_name: 新全名
            
        Returns:
            更新后的用户对象
            
        Raises:
            UserNotFoundException: 用户不存在
            ValidationException: 邮箱已被使用或用户资料更新失败
        """
        try:
            user = self.user_service.update_user(
                user_id=user_id,
                email=email,
                full_name=full_name
            )
            
            if user:
                logger.info(f"用户资料更新成功: {user.username}")
            
            return user
            
        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"用户资料更新失败: {str(e)}", exc_info=True)
            raise ValidationException(str(e))
        
        raise ValidationException("用户资料更新失败") 