"""
用户服务 - 提供用户管理、认证等功能
"""
import os
import json
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from ..core.config import get_settings
from ..core.security import get_password_hash, verify_password, create_access_token
from ..domain.models.user import User, UserRole

settings = get_settings()

class UserService:
    """用户服务"""
    
    def __init__(self):
        """初始化用户服务"""
        self.users_dir = os.path.join(os.getcwd(), settings.USERS_DATA_DIR)
        os.makedirs(self.users_dir, exist_ok=True)
        
        # 确保有一个管理员账户
        self._ensure_admin_exists()
        
    def _ensure_admin_exists(self):
        """确保至少有一个管理员账户"""
        admin_exists = False
        
        # 检查是否已有管理员账户
        for filename in os.listdir(self.users_dir):
            if filename.endswith('.json'):
                with open(os.path.join(self.users_dir, filename), 'r') as f:
                    user_data = json.load(f)
                    if user_data.get('role') == UserRole.ADMIN:
                        admin_exists = True
                        break
        
        # 如果没有管理员账户，创建一个默认账户
        if not admin_exists:
            admin_user = {
                "id": str(uuid.uuid4()),
                "username": "admin",
                "email": "admin@example.com",
                "hashed_password": get_password_hash("admin123"),
                "full_name": "系统管理员",
                "role": UserRole.ADMIN,
                "created_at": datetime.now().isoformat(),
                "updated_at": None,
                "last_login": None
            }
            
            with open(os.path.join(self.users_dir, f"{admin_user['id']}.json"), 'w') as f:
                json.dump(admin_user, f, ensure_ascii=False, indent=2)
            
            print(f"已创建默认管理员账户: 用户名=admin, 密码=admin123")
    
    def _get_user_path(self, user_id: str) -> str:
        """获取用户文件路径"""
        return os.path.join(self.users_dir, f"{user_id}.json")
    
    def _save_user(self, user: User):
        """保存用户到文件"""
        user_dict = user.to_dict()
        # 转换datetime为ISO格式字符串
        if isinstance(user_dict['created_at'], datetime):
            user_dict['created_at'] = user_dict['created_at'].isoformat()
        if user_dict.get('updated_at') and isinstance(user_dict['updated_at'], datetime):
            user_dict['updated_at'] = user_dict['updated_at'].isoformat()
        if user_dict.get('last_login') and isinstance(user_dict['last_login'], datetime):
            user_dict['last_login'] = user_dict['last_login'].isoformat()
            
        with open(self._get_user_path(user.id), 'w', encoding='utf-8') as f:
            json.dump(user_dict, f, ensure_ascii=False, indent=2)
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """通过ID获取用户"""
        user_path = self._get_user_path(user_id)
        if os.path.exists(user_path):
            with open(user_path, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
                return User.from_dict(user_data)
        return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        for filename in os.listdir(self.users_dir):
            if filename.endswith('.json'):
                with open(os.path.join(self.users_dir, filename), 'r', encoding='utf-8') as f:
                    user_data = json.load(f)
                    if user_data.get('username') == username:
                        return User.from_dict(user_data)
        return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """通过邮箱获取用户"""
        for filename in os.listdir(self.users_dir):
            if filename.endswith('.json'):
                with open(os.path.join(self.users_dir, filename), 'r', encoding='utf-8') as f:
                    user_data = json.load(f)
                    if user_data.get('email') == email:
                        return User.from_dict(user_data)
        return None
    
    def list_users(self) -> List[User]:
        """获取所有用户"""
        users = []
        for filename in os.listdir(self.users_dir):
            if filename.endswith('.json'):
                with open(os.path.join(self.users_dir, filename), 'r', encoding='utf-8') as f:
                    user_data = json.load(f)
                    users.append(User.from_dict(user_data))
        return users
    
    def create_user(self, username: str, email: str, password: str, full_name: Optional[str] = None, role: UserRole = UserRole.USER) -> User:
        """创建新用户"""
        # 检查用户名是否已存在
        if self.get_user_by_username(username):
            raise ValueError(f"用户名 '{username}' 已存在")
        
        # 检查邮箱是否已存在
        if self.get_user_by_email(email):
            raise ValueError(f"邮箱 '{email}' 已被注册")
        
        # 创建新用户
        new_user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=role,
            created_at=datetime.now()
        )
        
        # 保存用户
        self._save_user(new_user)
        
        return new_user
    
    def update_user(self, user_id: str, email: Optional[str] = None, full_name: Optional[str] = None, role: Optional[UserRole] = None) -> Optional[User]:
        """更新用户信息"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        # 更新字段
        if email is not None:
            # 检查邮箱是否已被其他用户使用
            existing_user = self.get_user_by_email(email)
            if existing_user and existing_user.id != user_id:
                raise ValueError(f"邮箱 '{email}' 已被其他用户注册")
            user.email = email
            
        if full_name is not None:
            user.full_name = full_name
            
        if role is not None:
            user.role = role
        
        # 更新时间
        user.updated_at = datetime.now()
        
        # 保存用户
        self._save_user(user)
        
        return user
    
    def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """修改密码"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        # 验证当前密码
        if not verify_password(current_password, user.hashed_password):
            return False
        
        # 更新密码
        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.now()
        
        # 保存用户
        self._save_user(user)
        
        return True
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """验证用户"""
        user = self.get_user_by_username(username)
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        # 更新最后登录时间
        user.last_login = datetime.now()
        self._save_user(user)
        
        return user
    
    def create_access_token_for_user(self, user: User, expires_delta: Optional[timedelta] = None) -> str:
        """为用户创建访问令牌"""
        return create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            expires_delta=expires_delta
        ) 