"""
测试数据工厂 - 用于生成测试数据
"""
import factory
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.domain.models.user import User, UserRole

class UserFactory(factory.Factory):
    """用户工厂"""
    
    class Meta:
        model = User
    
    id = factory.Sequence(lambda n: f"user-{n}")
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    full_name = factory.Faker("name")
    hashed_password = factory.LazyFunction(lambda: "hashed_password_123")
    role = UserRole.USER.value
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    last_login = None
    
    @factory.post_generation
    def set_password(obj, create, extracted, **kwargs):
        """设置密码"""
        if extracted:
            obj.hashed_password = f"hashed_{extracted}"

class TestDataBuilder:
    """测试数据构建器"""
    
    @staticmethod
    def create_user(
        id: str = "test-user-id",
        username: str = "testuser",
        email: str = "test@example.com",
        full_name: str = "Test User",
        hashed_password: str = "hashed_password_123",
        role: str = UserRole.USER.value,
        created_at: datetime = "default",
        updated_at: datetime = None,
        last_login: datetime = None,
        **kwargs
    ) -> User:
        """创建测试用户"""
        defaults = {
            "id": id,
            "username": username,
            "email": email,
            "full_name": full_name,
            "hashed_password": hashed_password,
            "role": role,
            "created_at": datetime.now(timezone.utc) if created_at == "default" else created_at,
            "updated_at": updated_at,
            "last_login": last_login
        }
        defaults.update(kwargs)
        
        # 移除只读属性
        defaults.pop('is_active', None)
        defaults.pop('is_admin', None)
        
        return User(**defaults)
    
    @staticmethod
    def create_user_dict(
        id: str = "test-user-id",
        username: str = "testuser",
        email: str = "test@example.com",
        full_name: str = "Test User",
        hashed_password: str = "hashed_password_123",
        role: str = UserRole.USER.value,
        created_at: datetime = "default",
        updated_at: datetime = None,
        last_login: datetime = None,
        **kwargs
    ) -> Dict[str, Any]:
        """创建测试用户字典数据"""
        defaults = {
            "id": id,
            "username": username,
            "email": email,
            "full_name": full_name,
            "hashed_password": hashed_password,
            "role": role,
            "created_at": datetime.now(timezone.utc) if created_at == "default" else created_at,
            "updated_at": updated_at,
            "last_login": last_login
        }
        defaults.update(kwargs)
        
        # 移除只读属性
        defaults.pop('is_active', None)
        defaults.pop('is_admin', None)
        
        return defaults
    
    @staticmethod
    def create_users(count: int = 5, **kwargs) -> List[User]:
        """批量创建测试用户"""
        users = []
        for i in range(count):
            user_kwargs = {
                "id": f"user-{i}",
                "username": f"user{i}",
                "email": f"user{i}@example.com",
                **kwargs
            }
            users.append(TestDataBuilder.create_user(**user_kwargs))
        return users
    
    @staticmethod
    def create_admin_user(**kwargs) -> User:
        """创建管理员用户"""
        defaults = {
            "username": "admin",
            "email": "admin@example.com",
            "role": UserRole.ADMIN.value
        }
        defaults.update(kwargs)
        return TestDataBuilder.create_user(**defaults)
    
    @staticmethod
    def create_inactive_user(**kwargs) -> User:
        """创建非活跃用户"""
        defaults = {
            "is_active": False
        }
        defaults.update(kwargs)
        return TestDataBuilder.create_user(**defaults) 