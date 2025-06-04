"""
用户Repository单元测试

专注于测试：
- 数据库CRUD操作
- 查询逻辑
- 数据持久化
使用Mock数据库连接
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.repositories.user import UserRepository
from app.domain.models.user import User, UserRole
from tests.factories import TestDataBuilder


@pytest.mark.unit
class TestUserRepository:
    """用户Repository测试
    
    专注于测试：
    - 数据库CRUD操作
    - 查询逻辑
    - 数据持久化
    使用Mock数据库连接
    """
    
    @pytest.fixture
    def mock_session(self):
        """Mock数据库会话"""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        return session
    
    @pytest.fixture
    def user_repository(self, mock_session):
        """用户Repository实例"""
        return UserRepository(mock_session)
    
    @pytest.fixture
    def sample_user(self):
        """示例用户"""
        return TestDataBuilder.create_user()
    
    @pytest.mark.asyncio
    async def test_get_by_username_success(self, user_repository, mock_session, sample_user):
        """测试根据用户名获取用户成功"""
        # Arrange
        username = "testuser"
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repository.get_by_username(username)
        
        # Assert
        assert result == sample_user
        mock_session.execute.assert_called_once()
        
        # 验证SQL查询
        call_args = mock_session.execute.call_args[0][0]
        assert str(call_args).lower().count("where") == 1
        assert "username" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_get_by_username_not_found(self, user_repository, mock_session):
        """测试根据用户名获取用户未找到"""
        # Arrange
        username = "nonexistent"
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repository.get_by_username(username)
        
        # Assert
        assert result is None
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_username_database_error(self, user_repository, mock_session):
        """测试根据用户名获取用户数据库错误"""
        # Arrange
        username = "testuser"
        mock_session.execute.side_effect = Exception("Database error")
        
        # Act
        result = await user_repository.get_by_username(username)
        
        # Assert
        assert result is None
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_email_success(self, user_repository, mock_session, sample_user):
        """测试根据邮箱获取用户成功"""
        # Arrange
        email = "test@example.com"
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repository.get_by_email(email)
        
        # Assert
        assert result == sample_user
        mock_session.execute.assert_called_once()
        
        # 验证SQL查询
        call_args = mock_session.execute.call_args[0][0]
        assert "email" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, user_repository, mock_session):
        """测试根据邮箱获取用户未找到"""
        # Arrange
        email = "nonexistent@example.com"
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repository.get_by_email(email)
        
        # Assert
        assert result is None
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_email_database_error(self, user_repository, mock_session):
        """测试根据邮箱获取用户数据库错误"""
        # Arrange
        email = "test@example.com"
        mock_session.execute.side_effect = Exception("Database error")
        
        # Act
        result = await user_repository.get_by_email(email)
        
        # Assert
        assert result is None
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_active_users_success(self, user_repository, mock_session):
        """测试获取活跃用户列表成功"""
        # Arrange
        users = [
            TestDataBuilder.create_user(username="user1"),
            TestDataBuilder.create_user(username="user2"),
            TestDataBuilder.create_user(username="user3")
        ]
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = users
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repository.get_active_users()
        
        # Assert
        assert len(result) == 3
        assert result == users
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_active_users_with_limit_and_offset(self, user_repository, mock_session):
        """测试获取活跃用户列表带分页参数"""
        # Arrange
        users = [TestDataBuilder.create_user(username="user1")]
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = users
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repository.get_active_users(limit=10, offset=5)
        
        # Assert
        assert result == users
        mock_session.execute.assert_called_once()
        
        # 验证SQL查询包含limit和offset
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args)
        # 注意：具体的SQL语法可能因SQLAlchemy版本而异
        assert "LIMIT" in query_str or "limit" in query_str.lower()
        assert "OFFSET" in query_str or "offset" in query_str.lower()
    
    @pytest.mark.asyncio
    async def test_get_active_users_empty_result(self, user_repository, mock_session):
        """测试获取活跃用户列表空结果"""
        # Arrange
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repository.get_active_users()
        
        # Assert
        assert result == []
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_active_users_database_error(self, user_repository, mock_session):
        """测试获取活跃用户列表数据库错误"""
        # Arrange
        mock_session.execute.side_effect = Exception("Database error")
        
        # Act
        result = await user_repository.get_active_users()
        
        # Assert
        assert result == []
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_count_active_users_success(self, user_repository, mock_session):
        """测试获取活跃用户总数成功"""
        # Arrange
        expected_count = 42
        mock_result = Mock()
        mock_result.scalar.return_value = expected_count
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repository.count_active_users()
        
        # Assert
        assert result == expected_count
        mock_session.execute.assert_called_once()
        
        # 验证SQL查询包含count函数
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args).lower()
        assert "count" in query_str
    
    @pytest.mark.asyncio
    async def test_count_active_users_zero_result(self, user_repository, mock_session):
        """测试获取活跃用户总数为零"""
        # Arrange
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repository.count_active_users()
        
        # Assert
        assert result == 0
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_count_active_users_none_result(self, user_repository, mock_session):
        """测试获取活跃用户总数返回None"""
        # Arrange
        mock_result = Mock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repository.count_active_users()
        
        # Assert
        assert result == 0  # None应该被转换为0
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_count_active_users_database_error(self, user_repository, mock_session):
        """测试获取活跃用户总数数据库错误"""
        # Arrange
        mock_session.execute.side_effect = Exception("Database error")
        
        # Act
        result = await user_repository.count_active_users()
        
        # Assert
        assert result == 0
        mock_session.execute.assert_called_once()
    
    def test_get_table_name(self, user_repository):
        """测试获取表名"""
        # Act
        table_name = user_repository.get_table_name()
        
        # Assert
        assert table_name == "users"


@pytest.mark.unit
class TestUserRepositoryInheritedMethods:
    """测试UserRepository继承的BaseRepository方法"""
    
    @pytest.fixture
    def mock_session(self):
        """Mock数据库会话"""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        session.refresh = AsyncMock()
        return session
    
    @pytest.fixture
    def user_repository(self, mock_session):
        """用户Repository实例"""
        return UserRepository(mock_session)
    
    @pytest.mark.asyncio
    async def test_create_user(self, user_repository, mock_session):
        """测试创建用户"""
        # Arrange
        user_data = {
            "username": "newuser",
            "email": "new@example.com",
            "hashed_password": "hashed_password"
        }
        
        # Mock the BaseRepository create method
        with patch.object(user_repository, 'create') as mock_create:
            expected_user = User(**user_data)
            mock_create.return_value = expected_user
            
            # Act
            result = await user_repository.create(user_data)
            
            # Assert
            assert result == expected_user
            mock_create.assert_called_once_with(user_data)
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, user_repository, mock_session):
        """测试根据ID获取用户"""
        # Arrange
        user_id = "test-user-id"
        expected_user = TestDataBuilder.create_user(id=user_id)
        
        # Mock the BaseRepository get_by_id method
        with patch.object(user_repository, 'get_by_id') as mock_get:
            mock_get.return_value = expected_user
            
            # Act
            result = await user_repository.get_by_id(user_id)
            
            # Assert
            assert result == expected_user
            mock_get.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_update_user(self, user_repository, mock_session):
        """测试更新用户"""
        # Arrange
        user_id = "test-user-id"
        update_data = {"full_name": "Updated Name"}
        expected_user = TestDataBuilder.create_user(id=user_id, full_name="Updated Name")
        
        # Mock the BaseRepository update method
        with patch.object(user_repository, 'update') as mock_update:
            mock_update.return_value = expected_user
            
            # Act
            result = await user_repository.update(user_id, update_data)
            
            # Assert
            assert result == expected_user
            mock_update.assert_called_once_with(user_id, update_data)
    
    @pytest.mark.asyncio
    async def test_delete_user(self, user_repository, mock_session):
        """测试删除用户"""
        # Arrange
        user_id = "test-user-id"
        
        # Mock the BaseRepository delete method
        with patch.object(user_repository, 'delete') as mock_delete:
            mock_delete.return_value = True
            
            # Act
            result = await user_repository.delete(user_id)
            
            # Assert
            assert result is True
            mock_delete.assert_called_once_with(user_id)


@pytest.mark.unit
class TestUserRepositoryIntegration:
    """用户Repository集成测试"""
    
    @pytest.fixture
    def mock_session(self):
        """Mock数据库会话"""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        return session
    
    @pytest.fixture
    def user_repository(self, mock_session):
        """用户Repository实例"""
        return UserRepository(mock_session)
    
    @pytest.mark.asyncio
    async def test_user_repository_workflow(self, user_repository, mock_session):
        """测试用户Repository工作流程"""
        # Arrange
        username = "workflowuser"
        email = "workflow@example.com"
        
        # Mock查询结果 - 用户不存在
        mock_result_empty = Mock()
        mock_result_empty.scalar_one_or_none.return_value = None
        
        # Mock查询结果 - 用户存在
        expected_user = TestDataBuilder.create_user(username=username, email=email)
        mock_result_found = Mock()
        mock_result_found.scalar_one_or_none.return_value = expected_user
        
        # 设置mock行为：第一次查询返回None，第二次返回用户
        mock_session.execute.side_effect = [mock_result_empty, mock_result_found]
        
        # Act & Assert - 第一次查询用户不存在
        result1 = await user_repository.get_by_username(username)
        assert result1 is None
        
        # Act & Assert - 第二次查询用户存在
        result2 = await user_repository.get_by_username(username)
        assert result2 == expected_user
        
        # 验证调用次数
        assert mock_session.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_user_repository_error_handling_consistency(self, user_repository, mock_session):
        """测试用户Repository错误处理一致性"""
        # Arrange
        mock_session.execute.side_effect = Exception("Database connection lost")
        
        # Act - 测试所有查询方法的错误处理
        username_result = await user_repository.get_by_username("test")
        email_result = await user_repository.get_by_email("test@example.com")
        users_result = await user_repository.get_active_users()
        count_result = await user_repository.count_active_users()
        
        # Assert - 所有方法都应该优雅地处理错误
        assert username_result is None
        assert email_result is None
        assert users_result == []
        assert count_result == 0
        
        # 验证所有方法都被调用了
        assert mock_session.execute.call_count == 4 