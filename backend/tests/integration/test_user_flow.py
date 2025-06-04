"""
用户流程集成测试

测试完整的用户操作流程：
- 用户注册
- 用户登录
- 用户信息更新
- 密码修改
- 用户删除
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from tests.factories import TestDataBuilder


class TestUserIntegrationFlow:
    """用户集成测试流程
    
    测试完整的用户操作流程，包括：
    - 用户注册流程
    - 用户认证流程
    - 用户管理流程
    - 错误处理流程
    """
    
    @pytest.fixture
    def client(self):
        """测试客户端"""
        return TestClient(app)
    
    @pytest.mark.integration
    def test_complete_user_lifecycle(self, client):
        """测试完整的用户生命周期"""
        # 1. 用户注册
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User"
        }
        
        created_user = TestDataBuilder.create_user(
            id="user-123",
            username="testuser",
            email="test@example.com",
            full_name="Test User"
        )
        
        with patch('app.api.routes.user.user_service') as mock_user_service, \
             patch('app.api.routes.auth.auth_service') as mock_auth_service:
            
            # Mock用户创建
            mock_user_service.create_user = AsyncMock(return_value=created_user)
            
            # Act: 创建用户
            response = client.post("/api/users/", json=user_data)
            
            # Assert: 用户创建成功
            assert response.status_code == status.HTTP_201_CREATED
            response_data = response.json()
            assert response_data["username"] == "testuser"
            assert response_data["email"] == "test@example.com"
            user_id = response_data["id"]
            
            # 2. 用户登录
            login_data = {
                "username": "testuser",
                "password": "password123"
            }
            
            # Mock认证服务
            mock_auth_service.authenticate_user = AsyncMock(return_value=created_user)
            mock_auth_service.create_access_token = AsyncMock(return_value="jwt_token_123")
            
            # Act: 用户登录
            response = client.post("/api/auth/login", json=login_data)
            
            # Assert: 登录成功
            assert response.status_code == status.HTTP_200_OK
            token_data = response.json()
            assert "access_token" in token_data
            assert token_data["token_type"] == "bearer"
            access_token = token_data["access_token"]
            
            # 3. 获取用户信息（需要认证）
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Mock当前用户获取
            with patch('app.api.deps.get_current_user') as mock_get_current_user:
                mock_get_current_user.return_value = created_user
                mock_user_service.get_user_by_id = AsyncMock(return_value=created_user)
                
                # Act: 获取当前用户信息
                response = client.get("/api/users/me", headers=headers)
                
                # Assert: 获取成功
                assert response.status_code == status.HTTP_200_OK
                user_info = response.json()
                assert user_info["username"] == "testuser"
                assert user_info["email"] == "test@example.com"
                
                # 4. 更新用户信息
                update_data = {
                    "email": "updated@example.com",
                    "full_name": "Updated User"
                }
                
                updated_user = TestDataBuilder.create_user(
                    id=user_id,
                    username="testuser",
                    email="updated@example.com",
                    full_name="Updated User"
                )
                
                mock_user_service.update_user = AsyncMock(return_value=updated_user)
                
                # Act: 更新用户信息
                response = client.put(f"/api/users/{user_id}", json=update_data, headers=headers)
                
                # Assert: 更新成功
                assert response.status_code == status.HTTP_200_OK
                updated_info = response.json()
                assert updated_info["email"] == "updated@example.com"
                assert updated_info["full_name"] == "Updated User"
                
                # 5. 修改密码
                password_data = {
                    "old_password": "password123",
                    "new_password": "newpassword123"
                }
                
                mock_user_service.change_password = AsyncMock(return_value=True)
                
                # Act: 修改密码
                response = client.post(f"/api/users/{user_id}/change-password", 
                                     json=password_data, headers=headers)
                
                # Assert: 密码修改成功
                assert response.status_code == status.HTTP_200_OK
                password_response = response.json()
                assert password_response["message"] == "密码修改成功"
    
    @pytest.mark.integration
    def test_user_registration_and_duplicate_handling(self, client):
        """测试用户注册和重复处理"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        
        created_user = TestDataBuilder.create_user(
            username="testuser",
            email="test@example.com"
        )
        
        with patch('app.api.routes.user.user_service') as mock_service:
            # 第一次注册成功
            mock_service.create_user = AsyncMock(return_value=created_user)
            
            response = client.post("/api/users/", json=user_data)
            assert response.status_code == status.HTTP_201_CREATED
            
            # 第二次注册相同用户名失败
            from app.core.errors import ValidationException
            mock_service.create_user = AsyncMock(
                side_effect=ValidationException("用户名已存在")
            )
            
            response = client.post("/api/users/", json=user_data)
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json()["detail"] == "用户名已存在"
    
    @pytest.mark.integration
    def test_authentication_flow_with_errors(self, client):
        """测试认证流程及错误处理"""
        # 1. 尝试用不存在的用户登录
        login_data = {
            "username": "nonexistent",
            "password": "password123"
        }
        
        with patch('app.api.routes.auth.auth_service') as mock_auth_service:
            mock_auth_service.authenticate_user = AsyncMock(return_value=None)
            
            response = client.post("/api/auth/login", json=login_data)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            
            # 2. 尝试用错误密码登录
            login_data["username"] = "testuser"
            mock_auth_service.authenticate_user = AsyncMock(return_value=None)
            
            response = client.post("/api/auth/login", json=login_data)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            
            # 3. 尝试访问需要认证的端点但不提供token
            response = client.get("/api/users/me")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            
            # 4. 尝试使用无效token
            headers = {"Authorization": "Bearer invalid_token"}
            response = client.get("/api/users/me", headers=headers)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.integration
    def test_user_permissions_and_access_control(self, client):
        """测试用户权限和访问控制"""
        # 创建普通用户和管理员用户
        regular_user = TestDataBuilder.create_user(
            id="regular-user-id",
            username="regularuser",
            role="user"
        )
        
        admin_user = TestDataBuilder.create_user(
            id="admin-user-id",
            username="adminuser",
            role="admin"
        )
        
        other_user = TestDataBuilder.create_user(
            id="other-user-id",
            username="otheruser",
            role="user"
        )
        
        with patch('app.api.routes.user.user_service') as mock_user_service:
            # 1. 普通用户尝试访问其他用户信息（应该被拒绝）
            with patch('app.api.deps.get_current_user') as mock_get_current_user:
                mock_get_current_user.return_value = regular_user
                
                response = client.get(f"/api/users/{other_user.id}")
                # 根据实际权限控制逻辑调整状态码
                assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
                
                # 2. 普通用户尝试更新其他用户信息（应该被拒绝）
                update_data = {"full_name": "Hacked Name"}
                response = client.put(f"/api/users/{other_user.id}", json=update_data)
                assert response.status_code == status.HTTP_403_FORBIDDEN
                
                # 3. 普通用户可以更新自己的信息
                mock_user_service.update_user = AsyncMock(return_value=regular_user)
                response = client.put(f"/api/users/{regular_user.id}", json=update_data)
                assert response.status_code == status.HTTP_200_OK
            
            # 4. 管理员可以访问和管理所有用户
            with patch('app.api.deps.get_current_user') as mock_get_current_user:
                mock_get_current_user.return_value = admin_user
                
                # 管理员获取用户列表
                mock_user_service.list_users = AsyncMock(return_value=[regular_user, other_user])
                response = client.get("/api/users/")
                assert response.status_code == status.HTTP_200_OK
                
                # 管理员删除用户
                mock_user_service.delete_user = AsyncMock(return_value=True)
                response = client.delete(f"/api/users/{other_user.id}")
                assert response.status_code == status.HTTP_204_NO_CONTENT
    
    @pytest.mark.integration
    def test_data_validation_across_layers(self, client):
        """测试跨层数据验证"""
        # 测试各种无效数据在不同层的处理
        
        # 1. Schema层验证（Pydantic）
        invalid_data_sets = [
            {
                "data": {"username": "", "email": "test@example.com", "password": "password123"},
                "expected_error": "username"
            },
            {
                "data": {"username": "test", "email": "invalid-email", "password": "password123"},
                "expected_error": "email"
            },
            {
                "data": {"username": "test", "email": "test@example.com", "password": "short"},
                "expected_error": "password"
            }
        ]
        
        for test_case in invalid_data_sets:
            response = client.post("/api/users/", json=test_case["data"])
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            error_detail = response.json()["detail"]
            assert any(test_case["expected_error"] in str(error) for error in error_detail)
        
        # 2. 业务逻辑层验证
        valid_schema_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        
        with patch('app.api.routes.user.user_service') as mock_service:
            # 模拟业务逻辑错误
            from app.core.errors import ValidationException
            mock_service.create_user = AsyncMock(
                side_effect=ValidationException("用户名已存在")
            )
            
            response = client.post("/api/users/", json=valid_schema_data)
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json()["detail"] == "用户名已存在"
    
    @pytest.mark.integration
    def test_error_handling_consistency(self, client):
        """测试错误处理的一致性"""
        # 测试不同类型错误的统一处理
        
        with patch('app.api.routes.user.user_service') as mock_service:
            # 1. 验证错误
            from app.core.errors import ValidationException
            mock_service.create_user = AsyncMock(
                side_effect=ValidationException("验证失败")
            )
            
            response = client.post("/api/users/", json={
                "username": "test", "email": "test@example.com", "password": "password123"
            })
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "detail" in response.json()
            
            # 2. 未找到错误
            from app.core.errors import NotFoundException
            mock_service.get_user_by_id = AsyncMock(
                side_effect=NotFoundException("用户不存在")
            )
            
            response = client.get("/api/users/nonexistent-id")
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json()["detail"] == "用户不存在"
            
            # 3. 认证错误
            from app.core.errors import AuthenticationException
            mock_service.change_password = AsyncMock(
                side_effect=AuthenticationException("认证失败")
            )
            
            with patch('app.api.deps.get_current_user') as mock_get_user:
                mock_get_user.return_value = TestDataBuilder.create_user()
                
                response = client.post("/api/users/user-id/change-password", json={
                    "old_password": "wrong", "new_password": "newpass123"
                })
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
                assert response.json()["detail"] == "认证失败" 