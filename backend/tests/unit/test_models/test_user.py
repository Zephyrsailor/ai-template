"""
用户模型单元测试

专注于测试：
- 模型字段验证
- 模型方法逻辑
- 数据转换
- 不涉及数据库操作
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock
from typing import Dict, Any

from app.domain.models.user import User, UserRole
from tests.factories import TestDataBuilder


@pytest.mark.unit
class TestUserModel:
    """用户模型测试类
    
    测试用户模型的：
    - 基本属性
    - 计算属性
    - 实例方法
    - 类方法
    """
    
    def test_user_creation(self):
        """测试用户模型创建"""
        # Arrange
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "hashed_password_123",
            "full_name": "Test User",
            "role": UserRole.USER.value
        }
        
        # Act
        user = User(**user_data)
        
        # Assert
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_password_123"
        assert user.full_name == "Test User"
        assert user.role == UserRole.USER.value
    
    def test_user_creation_with_minimal_data(self):
        """测试用户模型最小数据创建"""
        # Arrange
        minimal_data = {
            "username": "minimaluser",
            "email": "minimal@example.com",
            "hashed_password": "hashed_password"
        }
        
        # Act
        user = User(**minimal_data)
        
        # Assert
        assert user.username == "minimaluser"
        assert user.email == "minimal@example.com"
        assert user.hashed_password == "hashed_password"
        assert user.full_name is None
        assert user.role == UserRole.USER.value  # 默认值
        assert user.last_login is None
    
    def test_is_admin_property_for_admin_user(self):
        """测试管理员用户的is_admin属性"""
        # Arrange
        admin_user = User(
            username="admin",
            email="admin@example.com",
            hashed_password="password",
            role=UserRole.ADMIN.value
        )
        
        # Act & Assert
        assert admin_user.is_admin is True
    
    def test_is_admin_property_for_regular_user(self):
        """测试普通用户的is_admin属性"""
        # Arrange
        regular_user = User(
            username="user",
            email="user@example.com",
            hashed_password="password",
            role=UserRole.USER.value
        )
        
        # Act & Assert
        assert regular_user.is_admin is False
    
    def test_is_active_property(self):
        """测试is_active属性（当前总是返回True）"""
        # Arrange
        user = User(
            username="activeuser",
            email="active@example.com",
            hashed_password="password"
        )
        
        # Act & Assert
        assert user.is_active is True
    
    def test_to_dict_method(self):
        """测试to_dict方法"""
        # Arrange
        created_at = datetime(2024, 1, 1, 12, 0, 0)
        updated_at = datetime(2024, 1, 2, 12, 0, 0)
        last_login = datetime(2024, 1, 3, 12, 0, 0)
        
        user = User(
            id="test-id",
            username="testuser",
            email="test@example.com",
            hashed_password="password",
            full_name="Test User",
            role=UserRole.ADMIN.value,
            created_at=created_at,
            updated_at=updated_at,
            last_login=last_login
        )
        
        # Act
        user_dict = user.to_dict()
        
        # Assert
        expected_dict = {
            "id": "test-id",
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "role": UserRole.ADMIN.value,
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-02T12:00:00",
            "last_login": "2024-01-03T12:00:00",
            "is_admin": True,
            "is_active": True
        }
        assert user_dict == expected_dict
    
    def test_to_dict_method_with_none_dates(self):
        """测试to_dict方法处理None日期"""
        # Arrange
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="password"
        )
        
        # Act
        user_dict = user.to_dict()
        
        # Assert
        assert user_dict["created_at"] is None
        assert user_dict["updated_at"] is None
        assert user_dict["last_login"] is None
    
    def test_from_dict_method(self):
        """测试from_dict类方法"""
        # Arrange
        user_data = {
            "id": "test-id",
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "password",
            "full_name": "Test User",
            "role": UserRole.USER.value,
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-02T12:00:00",
            "last_login": "2024-01-03T12:00:00",
            "is_admin": False,  # 这个应该被过滤掉
            "is_active": True   # 这个应该被过滤掉
        }
        
        # Act
        user = User.from_dict(user_data)
        
        # Assert
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.role == UserRole.USER.value
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
        assert isinstance(user.last_login, datetime)
    
    def test_from_dict_method_with_invalid_dates(self):
        """测试from_dict方法处理无效日期"""
        # Arrange
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "password",
            "created_at": "invalid-date",
            "updated_at": None,
            "last_login": ""
        }
        
        # Act
        user = User.from_dict(user_data)
        
        # Assert
        assert user.username == "testuser"
        assert user.created_at is None
        assert user.updated_at is None
        assert user.last_login is None
    
    def test_repr_method(self):
        """测试__repr__方法"""
        # Arrange
        user = User(
            id="test-id",
            username="testuser",
            email="test@example.com",
            hashed_password="password"
        )
        
        # Act
        repr_str = repr(user)
        
        # Assert
        expected = "<User(id=test-id, username=testuser, email=test@example.com)>"
        assert repr_str == expected


@pytest.mark.unit
class TestUserRole:
    """用户角色枚举测试"""
    
    @pytest.mark.parametrize("role,expected_value", [
        (UserRole.ADMIN, "admin"),
        (UserRole.USER, "user"),
        (UserRole.GUEST, "guest"),
    ])
    def test_user_role_values(self, role: UserRole, expected_value: str):
        """测试用户角色枚举值"""
        assert role.value == expected_value
    
    def test_user_role_comparison(self):
        """测试用户角色比较"""
        assert UserRole.ADMIN == UserRole.ADMIN
        assert UserRole.ADMIN != UserRole.USER
        assert UserRole.USER != UserRole.GUEST
    
    def test_user_role_from_string(self):
        """测试从字符串创建用户角色"""
        assert UserRole("admin") == UserRole.ADMIN
        assert UserRole("user") == UserRole.USER
        assert UserRole("guest") == UserRole.GUEST
    
    def test_user_role_invalid_value(self):
        """测试无效的用户角色值"""
        with pytest.raises(ValueError):
            UserRole("invalid_role")


@pytest.mark.unit
class TestUserModelIntegration:
    """用户模型集成测试"""
    
    def test_user_lifecycle_methods(self):
        """测试用户生命周期方法"""
        # Arrange
        original_data = {
            "username": "lifecycle_user",
            "email": "lifecycle@example.com",
            "hashed_password": "password",
            "full_name": "Lifecycle User",
            "role": UserRole.ADMIN.value
        }
        
        # Act - 创建用户
        user = User(**original_data)
        
        # Act - 转换为字典
        user_dict = user.to_dict()
        
        # Act - 从字典重新创建
        recreated_user = User.from_dict(user_dict)
        
        # Assert - 验证数据一致性
        assert recreated_user.username == original_data["username"]
        assert recreated_user.email == original_data["email"]
        assert recreated_user.full_name == original_data["full_name"]
        assert recreated_user.role == original_data["role"]
        assert recreated_user.is_admin == user.is_admin
        assert recreated_user.is_active == user.is_active 