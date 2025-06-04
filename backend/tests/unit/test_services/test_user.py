"""
用户Service单元测试

专注于测试：
- 业务逻辑
- 服务间协调
- 错误处理
- 事务管理
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from app.services.user import UserService
from app.repositories.user import UserRepository
from app.domain.models.user import User, UserRole
from app.domain.schemas.user import UserCreate, UserUpdate, PasswordChange
from app.core.exceptions import (
    UserNotFoundError, UserAlreadyExistsError, 
    InvalidCredentialsError, ValidationError
)
from tests.factories import TestDataBuilder


@pytest.mark.unit
class TestUserService:
    """用户Service测试
    
    专注于测试：
    - 业务逻辑
    - 服务间协调
    - 错误处理
    - 事务管理
    """
    
    @pytest.fixture
    def mock_session(self):
        """Mock数据库会话"""
        return Mock()
    
    @pytest.fixture
    def user_service(self, mock_session):
        """用户Service实例"""
        return UserService(mock_session)
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service):
        """测试创建用户成功"""
        # Arrange
        user_data = UserCreate(
            username="newuser",
            email="new@example.com",
            password="password123",
            full_name="New User"
        )
        expected_user = TestDataBuilder.create_user(
            username="newuser",
            email="new@example.com",
            full_name="New User"
        )
        
        # Mock repository methods
        with patch.object(user_service.repository, 'get_by_username', new_callable=AsyncMock) as mock_get_username, \
             patch.object(user_service.repository, 'get_by_email', new_callable=AsyncMock) as mock_get_email, \
             patch.object(user_service.repository, 'create', new_callable=AsyncMock) as mock_create, \
             patch.object(user_service, '_hash_password') as mock_hash:
            
            mock_get_username.return_value = None  # 用户名不存在
            mock_get_email.return_value = None     # 邮箱不存在
            mock_create.return_value = expected_user
            mock_hash.return_value = "hashed_password_123"
            
            # Act
            result = await user_service.create_user(user_data)
            
            # Assert
            assert result == expected_user
            mock_get_username.assert_called_once_with("newuser")
            mock_get_email.assert_called_once_with("new@example.com")
            mock_create.assert_called_once()
            mock_hash.assert_called_once_with("password123")
    
    @pytest.mark.asyncio
    async def test_create_user_username_exists(self, user_service):
        """测试创建用户时用户名已存在"""
        # Arrange
        user_data = UserCreate(
            username="existinguser",
            email="new@example.com",
            password="password123"
        )
        existing_user = TestDataBuilder.create_user(username="existinguser")
        
        with patch.object(user_service.repository, 'get_by_username', new_callable=AsyncMock) as mock_get_username:
            mock_get_username.return_value = existing_user
            
            # Act & Assert
            with pytest.raises(ValidationError, match="用户名已存在"):
                await user_service.create_user(user_data)
            
            mock_get_username.assert_called_once_with("existinguser")
    
    @pytest.mark.asyncio
    async def test_create_user_email_exists(self, user_service):
        """测试创建用户时邮箱已存在"""
        # Arrange
        user_data = UserCreate(
            username="newuser",
            email="existing@example.com",
            password="password123"
        )
        existing_user = TestDataBuilder.create_user(email="existing@example.com")
        
        with patch.object(user_service.repository, 'get_by_username', new_callable=AsyncMock) as mock_get_username, \
             patch.object(user_service.repository, 'get_by_email', new_callable=AsyncMock) as mock_get_email:
            
            mock_get_username.return_value = None
            mock_get_email.return_value = existing_user
            
            # Act & Assert
            with pytest.raises(ValidationError, match="邮箱已存在"):
                await user_service.create_user(user_data)
            
            mock_get_username.assert_called_once_with("newuser")
            mock_get_email.assert_called_once_with("existing@example.com")
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, user_service):
        """测试用户认证成功"""
        # Arrange
        username = "testuser"
        password = "password123"
        user = TestDataBuilder.create_user(
            username=username,
            hashed_password="hashed_password_123"
        )
        
        with patch.object(user_service.repository, 'get_by_username', new_callable=AsyncMock) as mock_get_user, \
             patch.object(user_service, '_verify_password') as mock_verify, \
             patch.object(user_service.repository, 'update', new_callable=AsyncMock) as mock_update:
            
            mock_get_user.return_value = user
            mock_verify.return_value = True
            mock_update.return_value = user
            
            # Act
            result = await user_service.authenticate_user(username, password)
            
            # Assert
            assert result == user
            mock_get_user.assert_called_once_with(username)
            mock_verify.assert_called_once_with(password, "hashed_password_123")
            mock_update.assert_called_once()  # 更新最后登录时间
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, user_service):
        """测试用户认证用户不存在"""
        # Arrange
        username = "nonexistent"
        password = "password123"
        
        with patch.object(user_service.repository, 'get_by_username', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = None
            
            # Act
            result = await user_service.authenticate_user(username, password)
            
            # Assert
            assert result is None
            mock_get_user.assert_called_once_with(username)
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, user_service):
        """测试用户认证密码错误"""
        # Arrange
        username = "testuser"
        password = "wrongpassword"
        user = TestDataBuilder.create_user(
            username=username,
            hashed_password="hashed_password_123"
        )
        
        with patch.object(user_service.repository, 'get_by_username', new_callable=AsyncMock) as mock_get_user, \
             patch.object(user_service, '_verify_password') as mock_verify:
            
            mock_get_user.return_value = user
            mock_verify.return_value = False
            
            # Act
            result = await user_service.authenticate_user(username, password)
            
            # Assert
            assert result is None
            mock_get_user.assert_called_once_with(username)
            mock_verify.assert_called_once_with(password, "hashed_password_123")
    
    @pytest.mark.asyncio
    async def test_update_user_success(self, user_service):
        """测试更新用户成功"""
        # Arrange
        user_id = "test-user-id"
        user_data = UserUpdate(
            email="updated@example.com",
            full_name="Updated Name"
        )
        existing_user = TestDataBuilder.create_user(id=user_id)
        updated_user = TestDataBuilder.create_user(
            id=user_id,
            email="updated@example.com",
            full_name="Updated Name"
        )
        
        with patch.object(user_service.repository, 'get_by_id', new_callable=AsyncMock) as mock_get_by_id, \
             patch.object(user_service.repository, 'get_by_email', new_callable=AsyncMock) as mock_get_by_email, \
             patch.object(user_service.repository, 'update', new_callable=AsyncMock) as mock_update:
            
            mock_get_by_id.return_value = existing_user
            mock_get_by_email.return_value = None  # 邮箱未被其他用户使用
            mock_update.return_value = updated_user
            
            # Act
            result = await user_service.update_user(user_id, user_data)
            
            # Assert
            assert result == updated_user
            mock_get_by_id.assert_called_once_with(user_id)
            mock_get_by_email.assert_called_once_with("updated@example.com")
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_service):
        """测试更新用户用户不存在"""
        # Arrange
        user_id = "nonexistent-id"
        user_data = UserUpdate(email="updated@example.com")
        
        with patch.object(user_service.repository, 'get_by_id', new_callable=AsyncMock) as mock_get_by_id:
            mock_get_by_id.return_value = None
            
            # Act & Assert
            with pytest.raises(NotFoundException, match="用户不存在"):
                await user_service.update_user(user_id, user_data)
            
            mock_get_by_id.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_update_user_email_conflict(self, user_service):
        """测试更新用户邮箱冲突"""
        # Arrange
        user_id = "test-user-id"
        user_data = UserUpdate(email="existing@example.com")
        existing_user = TestDataBuilder.create_user(id=user_id)
        other_user = TestDataBuilder.create_user(
            id="other-user-id",
            email="existing@example.com"
        )
        
        with patch.object(user_service.repository, 'get_by_id', new_callable=AsyncMock) as mock_get_by_id, \
             patch.object(user_service.repository, 'get_by_email', new_callable=AsyncMock) as mock_get_by_email:
            
            mock_get_by_id.return_value = existing_user
            mock_get_by_email.return_value = other_user
            
            # Act & Assert
            with pytest.raises(ValidationError, match="邮箱已被其他用户使用"):
                await user_service.update_user(user_id, user_data)
            
            mock_get_by_id.assert_called_once_with(user_id)
            mock_get_by_email.assert_called_once_with("existing@example.com")
    
    @pytest.mark.asyncio
    async def test_change_password_success(self, user_service):
        """测试修改密码成功"""
        # Arrange
        user_id = "test-user-id"
        password_data = PasswordChange(
            old_password="oldpass123",
            new_password="newpass123"
        )
        user = TestDataBuilder.create_user(
            id=user_id,
            hashed_password="old_hashed_password"
        )
        
        with patch.object(user_service.repository, 'get_by_id', new_callable=AsyncMock) as mock_get_by_id, \
             patch.object(user_service, '_verify_password') as mock_verify, \
             patch.object(user_service, '_hash_password') as mock_hash, \
             patch.object(user_service.repository, 'update', new_callable=AsyncMock) as mock_update:
            
            mock_get_by_id.return_value = user
            mock_verify.return_value = True
            mock_hash.return_value = "new_hashed_password"
            mock_update.return_value = user
            
            # Act
            result = await user_service.change_password(user_id, password_data)
            
            # Assert
            assert result is True
            mock_get_by_id.assert_called_once_with(user_id)
            mock_verify.assert_called_once_with("oldpass123", "old_hashed_password")
            mock_hash.assert_called_once_with("newpass123")
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_change_password_user_not_found(self, user_service):
        """测试修改密码用户不存在"""
        # Arrange
        user_id = "nonexistent-id"
        password_data = PasswordChange(
            old_password="oldpass123",
            new_password="newpass123"
        )
        
        with patch.object(user_service.repository, 'get_by_id', new_callable=AsyncMock) as mock_get_by_id:
            mock_get_by_id.return_value = None
            
            # Act & Assert
            with pytest.raises(NotFoundException, match="用户不存在"):
                await user_service.change_password(user_id, password_data)
            
            mock_get_by_id.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_change_password_wrong_old_password(self, user_service):
        """测试修改密码旧密码错误"""
        # Arrange
        user_id = "test-user-id"
        password_data = PasswordChange(
            old_password="wrongpass",
            new_password="newpass123"
        )
        user = TestDataBuilder.create_user(
            id=user_id,
            hashed_password="old_hashed_password"
        )
        
        with patch.object(user_service.repository, 'get_by_id', new_callable=AsyncMock) as mock_get_by_id, \
             patch.object(user_service, '_verify_password') as mock_verify:
            
            mock_get_by_id.return_value = user
            mock_verify.return_value = False
            
            # Act & Assert
            with pytest.raises(InvalidCredentialsError, match="旧密码错误"):
                await user_service.change_password(user_id, password_data)
            
            mock_get_by_id.assert_called_once_with(user_id)
            mock_verify.assert_called_once_with("wrongpass", "old_hashed_password")
    
    @pytest.mark.asyncio
    async def test_get_user_by_username(self, user_service):
        """测试根据用户名获取用户"""
        # Arrange
        username = "testuser"
        expected_user = TestDataBuilder.create_user(username=username)
        
        with patch.object(user_service.repository, 'get_by_username', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = expected_user
            
            # Act
            result = await user_service.get_user_by_username(username)
            
            # Assert
            assert result == expected_user
            mock_get.assert_called_once_with(username)
    
    @pytest.mark.asyncio
    async def test_get_user_by_email(self, user_service):
        """测试根据邮箱获取用户"""
        # Arrange
        email = "test@example.com"
        expected_user = TestDataBuilder.create_user(email=email)
        
        with patch.object(user_service.repository, 'get_by_email', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = expected_user
            
            # Act
            result = await user_service.get_user_by_email(email)
            
            # Assert
            assert result == expected_user
            mock_get.assert_called_once_with(email)
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_service):
        """测试根据ID获取用户"""
        # Arrange
        user_id = "test-user-id"
        expected_user = TestDataBuilder.create_user(id=user_id)
        
        with patch.object(user_service.repository, 'get_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = expected_user
            
            # Act
            result = await user_service.get_user_by_id(user_id)
            
            # Assert
            assert result == expected_user
            mock_get.assert_called_once_with(user_id)
    
    def test_verify_password(self, user_service):
        """测试密码验证方法"""
        # Arrange
        plain_password = "password123"
        hashed_password = "hashed_password_123"
        
        with patch.object(user_service, '_verify_password') as mock_verify:
            mock_verify.return_value = True
            
            # Act
            result = user_service.verify_password(plain_password, hashed_password)
            
            # Assert
            assert result is True
            mock_verify.assert_called_once_with(plain_password, hashed_password)
    
    def test_create_access_token_for_user(self, user_service):
        """测试为用户创建访问令牌"""
        # Arrange
        user = TestDataBuilder.create_user(
            id="test-user-id",
            username="testuser",
            role=UserRole.USER.value
        )
        expected_token = "jwt_token_string"
        
        with patch('app.services.user.create_access_token') as mock_create_token:
            mock_create_token.return_value = expected_token
            
            # Act
            result = user_service.create_access_token_for_user(user)
            
            # Assert
            assert result == expected_token
            mock_create_token.assert_called_once_with(
                user_id=user.id,
                username=user.username,
                role=user.role
            )
    
    def test_get_entity_name(self, user_service):
        """测试获取实体名称"""
        # Act
        entity_name = user_service.get_entity_name()
        
        # Assert
        assert entity_name == "用户" 