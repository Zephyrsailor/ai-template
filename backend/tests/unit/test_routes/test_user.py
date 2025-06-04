"""
用户路由单元测试

专注于测试：
- HTTP请求/响应
- 状态码
- 数据序列化
- 认证授权
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.domain.models.user import User, UserRole
from app.domain.schemas.user import UserCreate, UserResponse, UserUpdate
from app.core.errors import ValidationException, NotFoundException, AuthenticationException
from tests.factories import TestDataBuilder


@pytest.mark.unit
class TestUserRoutes:
    """用户路由测试
    
    专注于测试：
    - HTTP请求/响应
    - 状态码
    - 数据序列化
    - 认证授权
    """
    
    @pytest.fixture
    def client(self):
        """测试客户端"""
        return TestClient(app)
    
    @pytest.fixture
    def admin_user(self):
        """管理员用户"""
        return TestDataBuilder.create_user(role=UserRole.ADMIN.value)
    
    @pytest.fixture
    def regular_user(self):
        """普通用户"""
        return TestDataBuilder.create_user(role=UserRole.USER.value)
    
    @pytest.fixture
    def mock_user_service(self):
        """Mock用户服务"""
        return Mock()
    
    def test_create_user_success(self, client):
        """测试创建用户API成功"""
        # Arrange
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User"
        }
        expected_user = TestDataBuilder.create_user(
            id="user-123",
            username="testuser",
            email="test@example.com",
            full_name="Test User"
        )
        
        with patch('app.api.routes.user.user_service') as mock_service:
            mock_service.create_user = AsyncMock(return_value=expected_user)
            
            # Act
            response = client.post("/api/users/", json=user_data)
            
            # Assert
            assert response.status_code == status.HTTP_201_CREATED
            response_data = response.json()
            assert response_data["username"] == "testuser"
            assert response_data["email"] == "test@example.com"
            assert response_data["full_name"] == "Test User"
            assert "password" not in response_data
            assert "hashed_password" not in response_data
    
    def test_create_user_validation_error(self, client):
        """测试创建用户验证错误"""
        # Arrange
        user_data = {
            "username": "testuser",
            "email": "invalid-email",  # 无效邮箱
            "password": "short"        # 密码太短
        }
        
        # Act
        response = client.post("/api/users/", json=user_data)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_data = response.json()
        assert "detail" in response_data
        # 验证错误信息包含字段验证错误
        errors = response_data["detail"]
        assert any("email" in str(error) for error in errors)
        assert any("password" in str(error) for error in errors)
    
    def test_create_user_username_exists(self, client):
        """测试创建用户用户名已存在"""
        # Arrange
        user_data = {
            "username": "existinguser",
            "email": "test@example.com",
            "password": "password123"
        }
        
        with patch('app.api.routes.user.user_service') as mock_service:
            mock_service.create_user = AsyncMock(
                side_effect=ValidationException("用户名已存在")
            )
            
            # Act
            response = client.post("/api/users/", json=user_data)
            
            # Assert
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            response_data = response.json()
            assert response_data["detail"] == "用户名已存在"
    
    def test_get_user_success(self, client, admin_user, mock_user_service):
        """测试获取用户API成功"""
        # Arrange
        user_id = "user-123"
        expected_user = TestDataBuilder.create_user(
            id=user_id,
            username="testuser",
            email="test@example.com"
        )
        
        mock_user_service.get_user_by_id = AsyncMock(return_value=expected_user)
        
        with patch('app.api.routes.user.get_current_admin', return_value=admin_user), \
             patch('app.api.routes.user.get_user_service', return_value=mock_user_service):
            
            # Act
            response = client.get(f"/api/users/{user_id}")
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["id"] == user_id
            assert response_data["username"] == "testuser"
            assert response_data["email"] == "test@example.com"
    
    def test_get_user_not_found(self, client, admin_user, mock_user_service):
        """测试获取不存在的用户"""
        # Arrange
        user_id = "nonexistent-id"
        
        mock_user_service.get_user_by_id = AsyncMock(return_value=None)
        
        with patch('app.api.routes.user.get_current_admin', return_value=admin_user), \
             patch('app.api.routes.user.get_user_service', return_value=mock_user_service):
            
            # Act
            response = client.get(f"/api/users/{user_id}")
            
            # Assert
            assert response.status_code == status.HTTP_404_NOT_FOUND
            response_data = response.json()
            assert response_data["detail"] == "用户不存在"
    
    def test_update_user_success(self, client, admin_user, mock_user_service):
        """测试更新用户API成功"""
        # Arrange
        user_id = "user-123"
        update_data = {
            "email": "updated@example.com",
            "full_name": "Updated User"
        }
        updated_user = TestDataBuilder.create_user(
            id=user_id,
            email="updated@example.com",
            full_name="Updated User"
        )
        
        mock_user_service.get_user_by_id = AsyncMock(return_value=updated_user)
        mock_user_service.update_user = AsyncMock(return_value=updated_user)
        
        with patch('app.api.routes.user.get_current_admin', return_value=admin_user), \
             patch('app.api.routes.user.get_user_service', return_value=mock_user_service):
            
            # Act
            response = client.put(f"/api/users/{user_id}", json=update_data)
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["email"] == "updated@example.com"
            assert response_data["full_name"] == "Updated User"
    
    def test_update_user_unauthorized(self, client):
        """测试更新用户未授权"""
        # Arrange
        user_id = "user-123"
        update_data = {"email": "updated@example.com"}
        
        # Act (不提供认证信息)
        response = client.put(f"/api/users/{user_id}", json=update_data)
        
        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_update_user_forbidden(self, client, regular_user, mock_user_service):
        """测试更新用户权限不足"""
        # Arrange
        user_id = "user-123"
        current_user_id = "other-user-456"
        update_data = {"email": "updated@example.com"}
        
        with patch('app.api.routes.user.get_current_admin') as mock_get_admin:
            # 当前用户不是要更新的用户，且不是管理员
            mock_get_admin.return_value = TestDataBuilder.create_user(
                id=current_user_id,
                role=UserRole.USER.value
            )
            
            # Act
            response = client.put(f"/api/users/{user_id}", json=update_data)
            
            # Assert
            assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_delete_user_success(self, client, admin_user, mock_user_service):
        """测试删除用户API成功"""
        # Arrange
        user_id = "user-123"
        
        mock_user_service.delete_user = AsyncMock(return_value=True)
        
        with patch('app.api.routes.user.get_current_admin', return_value=admin_user), \
             patch('app.api.routes.user.get_user_service', return_value=mock_user_service):
            
            # Act
            response = client.delete(f"/api/users/{user_id}")
            
            # Assert
            assert response.status_code == status.HTTP_204_NO_CONTENT
    
    def test_delete_user_not_found(self, client, admin_user, mock_user_service):
        """测试删除不存在的用户"""
        # Arrange
        user_id = "nonexistent-id"
        
        mock_user_service.delete_user = AsyncMock(
            side_effect=NotFoundException("用户不存在")
        )
        
        with patch('app.api.routes.user.get_current_admin', return_value=admin_user), \
             patch('app.api.routes.user.get_user_service', return_value=mock_user_service):
            
            # Act
            response = client.delete(f"/api/users/{user_id}")
            
            # Assert
            assert response.status_code == status.HTTP_404_NOT_FOUND
            response_data = response.json()
            assert response_data["detail"] == "用户不存在"
    
    def test_list_users_success(self, client, admin_user, mock_user_service):
        """测试获取用户列表API成功"""
        # Arrange
        expected_users = TestDataBuilder.create_users(count=3)
        
        mock_user_service.list_users = AsyncMock(return_value=expected_users)
        
        with patch('app.api.routes.user.get_current_admin', return_value=admin_user), \
             patch('app.api.routes.user.get_user_service', return_value=mock_user_service):
            
            # Act
            response = client.get("/api/users/")
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert len(response_data) == 3
            assert all("password" not in user for user in response_data)
            assert all("hashed_password" not in user for user in response_data)
    
    def test_list_users_with_pagination(self, client):
        """测试获取用户列表带分页"""
        # Arrange
        expected_users = TestDataBuilder.create_users(count=2)
        
        with patch('app.api.routes.user.user_service') as mock_service, \
             patch('app.api.deps.get_current_user') as mock_get_user:
            
            mock_service.list_users = AsyncMock(return_value=expected_users)
            mock_get_user.return_value = TestDataBuilder.create_user(
                role=UserRole.ADMIN.value
            )
            
            # Act
            response = client.get("/api/users/?limit=10&offset=20")
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert len(response_data) == 2
            # 验证服务被正确调用
            mock_service.list_users.assert_called_once_with(limit=10, offset=20)
    
    def test_change_password_success(self, client):
        """测试修改密码API成功"""
        # Arrange
        user_id = "user-123"
        password_data = {
            "old_password": "oldpass123",
            "new_password": "newpass123"
        }
        
        with patch('app.api.routes.user.user_service') as mock_service, \
             patch('app.api.deps.get_current_user') as mock_get_user:
            
            mock_service.change_password = AsyncMock(return_value=True)
            mock_get_user.return_value = TestDataBuilder.create_user(id=user_id)
            
            # Act
            response = client.post(f"/api/users/{user_id}/change-password", json=password_data)
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["message"] == "密码修改成功"
    
    def test_change_password_wrong_old_password(self, client):
        """测试修改密码旧密码错误"""
        # Arrange
        user_id = "user-123"
        password_data = {
            "old_password": "wrongpass",
            "new_password": "newpass123"
        }
        
        with patch('app.api.routes.user.user_service') as mock_service, \
             patch('app.api.deps.get_current_user') as mock_get_user:
            
            mock_service.change_password = AsyncMock(
                side_effect=AuthenticationException("旧密码错误")
            )
            mock_get_user.return_value = TestDataBuilder.create_user(id=user_id)
            
            # Act
            response = client.post(f"/api/users/{user_id}/change-password", json=password_data)
            
            # Assert
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            response_data = response.json()
            assert response_data["detail"] == "旧密码错误"
    
    def test_get_current_user_profile(self, client):
        """测试获取当前用户资料"""
        # Arrange
        current_user = TestDataBuilder.create_user(
            id="current-user-id",
            username="currentuser",
            email="current@example.com"
        )
        
        with patch('app.api.deps.get_current_user') as mock_get_user:
            mock_get_user.return_value = current_user
            
            # Act
            response = client.get("/api/users/me")
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["id"] == "current-user-id"
            assert response_data["username"] == "currentuser"
            assert response_data["email"] == "current@example.com"
            assert "password" not in response_data
    
    def test_api_requires_authentication(self, client):
        """测试API需要认证"""
        # Arrange & Act
        protected_endpoints = [
            ("GET", "/api/users/me"),
            ("PUT", "/api/users/user-123"),
            ("DELETE", "/api/users/user-123"),
            ("POST", "/api/users/user-123/change-password"),
        ]
        
        for method, endpoint in protected_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "PUT":
                response = client.put(endpoint, json={})
            elif method == "DELETE":
                response = client.delete(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            
            # Assert
            assert response.status_code == status.HTTP_401_UNAUTHORIZED, f"Endpoint {method} {endpoint} should require authentication"
    
    @pytest.mark.parametrize("invalid_data", [
        {"username": "", "email": "test@example.com", "password": "password123"},  # 空用户名
        {"username": "test", "email": "", "password": "password123"},              # 空邮箱
        {"username": "test", "email": "test@example.com", "password": ""},         # 空密码
        {"email": "test@example.com", "password": "password123"},                  # 缺少用户名
        {"username": "test", "password": "password123"},                           # 缺少邮箱
        {"username": "test", "email": "test@example.com"},                         # 缺少密码
    ])
    def test_create_user_invalid_data(self, client, invalid_data):
        """参数化测试创建用户无效数据"""
        # Act
        response = client.post("/api/users/", json=invalid_data)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_data = response.json()
        assert "detail" in response_data
    
    def test_response_excludes_sensitive_fields(self, client):
        """测试响应排除敏感字段"""
        # Arrange
        user = TestDataBuilder.create_user(
            hashed_password="sensitive_hash"
        )
        
        with patch('app.api.routes.user.user_service') as mock_service:
            mock_service.get_user_by_id = AsyncMock(return_value=user)
            
            # Act
            response = client.get(f"/api/users/{user.id}")
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            
            # 验证敏感字段不在响应中
            sensitive_fields = ["password", "hashed_password"]
            for field in sensitive_fields:
                assert field not in response_data, f"Sensitive field '{field}' should not be in response"


@pytest.mark.unit
class TestUserRoutesAuthentication:
    """用户Routes认证测试"""
    
    @pytest.fixture
    def client(self):
        """测试客户端"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user_service(self):
        """Mock用户服务"""
        return Mock()
    
    def test_all_endpoints_require_admin_authentication(self, client, mock_user_service):
        """测试所有端点都需要管理员认证"""
        # Arrange
        endpoints = [
            ("GET", "/api/users/"),
            ("GET", "/api/users/test-id"),
            ("PUT", "/api/users/test-id"),
            ("DELETE", "/api/users/test-id")
        ]
        
        with patch('app.api.routes.user.get_user_service', return_value=mock_user_service):
            for method, url in endpoints:
                with patch('app.api.routes.user.get_current_admin') as mock_get_admin:
                    mock_get_admin.side_effect = Exception("Authentication required")
                    
                    # Act
                    if method == "GET":
                        response = client.get(url)
                    elif method == "PUT":
                        response = client.put(url, json={"email": "test@example.com"})
                    elif method == "DELETE":
                        response = client.delete(url)
                    
                    # Assert
                    assert response.status_code in [
                        status.HTTP_401_UNAUTHORIZED, 
                        status.HTTP_403_FORBIDDEN,
                        status.HTTP_500_INTERNAL_SERVER_ERROR  # 如果异常未被正确处理
                    ], f"Endpoint {method} {url} should require authentication"


@pytest.mark.unit
class TestUserRoutesIntegration:
    """用户Routes集成测试"""
    
    @pytest.fixture
    def client(self):
        """测试客户端"""
        return TestClient(app)
    
    @pytest.fixture
    def admin_user(self):
        """管理员用户"""
        return TestDataBuilder.create_user(role=UserRole.ADMIN.value)
    
    @pytest.fixture
    def mock_user_service(self):
        """Mock用户服务"""
        return Mock()
    
    def test_user_management_workflow(self, client, admin_user, mock_user_service):
        """测试用户管理完整工作流程"""
        # Arrange
        user_id = "workflow-user-id"
        original_user = TestDataBuilder.create_user(
            id=user_id,
            username="workflowuser",
            email="workflow@example.com"
        )
        updated_user = TestDataBuilder.create_user(
            id=user_id,
            username="workflowuser",
            email="updated@example.com"
        )
        
        # Mock服务行为
        mock_user_service.list_users.return_value = [original_user]
        mock_user_service.get_user_by_id.return_value = original_user
        mock_user_service.update_user.return_value = updated_user
        mock_user_service.delete_user.return_value = True
        
        with patch('app.api.routes.user.get_current_admin', return_value=admin_user), \
             patch('app.api.routes.user.get_user_service', return_value=mock_user_service):
            
            # Act & Assert - 1. 获取用户列表
            list_response = client.get("/api/users/")
            assert list_response.status_code == status.HTTP_200_OK
            list_data = list_response.json()
            assert len(list_data["data"]) == 1
            assert list_data["data"][0]["username"] == "workflowuser"
            
            # Act & Assert - 2. 获取用户详情
            detail_response = client.get(f"/api/users/{user_id}")
            assert detail_response.status_code == status.HTTP_200_OK
            detail_data = detail_response.json()
            assert detail_data["data"]["email"] == "workflow@example.com"
            
            # Act & Assert - 3. 更新用户
            update_data = {"email": "updated@example.com"}
            update_response = client.put(f"/api/users/{user_id}", json=update_data)
            assert update_response.status_code == status.HTTP_200_OK
            update_result = update_response.json()
            assert update_result["data"]["email"] == "updated@example.com"
            
            # Act & Assert - 4. 删除用户
            delete_response = client.delete(f"/api/users/{user_id}")
            assert delete_response.status_code == status.HTTP_200_OK
            delete_result = delete_response.json()
            assert delete_result["success"] is True
            
            # 验证服务调用
            mock_user_service.list_users.assert_called_once()
            assert mock_user_service.get_user_by_id.call_count == 2  # 详情 + 更新前检查
            mock_user_service.update_user.assert_called_once()
            mock_user_service.delete_user.assert_called_once_with(user_id)
    
    def test_error_handling_consistency(self, client, admin_user, mock_user_service):
        """测试错误处理一致性"""
        # Arrange
        user_id = "error-test-id"
        
        # 模拟各种错误情况
        error_scenarios = [
            ("get_user_by_id", None),  # 用户不存在
            ("update_user", Exception("Service error")),  # 服务异常
            ("delete_user", False),  # 删除失败
        ]
        
        with patch('app.api.routes.user.get_current_admin', return_value=admin_user), \
             patch('app.api.routes.user.get_user_service', return_value=mock_user_service):
            
            for method_name, error_value in error_scenarios:
                # 重置mock
                mock_user_service.reset_mock()
                
                if isinstance(error_value, Exception):
                    getattr(mock_user_service, method_name).side_effect = error_value
                else:
                    getattr(mock_user_service, method_name).return_value = error_value
                
                # 测试各个端点的错误处理
                responses = [
                    client.get(f"/api/users/{user_id}"),
                    client.put(f"/api/users/{user_id}", json={"email": "test@example.com"}),
                    client.delete(f"/api/users/{user_id}")
                ]
                
                for response in responses:
                    # 所有错误都应该被API包装，返回200状态码但包含错误信息
                    assert response.status_code == status.HTTP_200_OK
                    response_data = response.json()
                    assert response_data["success"] is False
                    assert response_data["code"] in [404, 500]  # 错误码应该在响应体中 