"""
用户Schema单元测试

专注于测试：
- 数据序列化/反序列化
- 字段验证规则
- 数据转换逻辑
"""
import pytest
from pydantic import ValidationError

from app.domain.schemas.user import (
    UserBase, UserCreate, UserLogin, UserResponse, 
    UserUpdate, PasswordChange, Token, TokenData
)


@pytest.mark.unit
class TestUserBase:
    """用户基础Schema测试"""
    
    def test_user_base_valid_data(self):
        """测试UserBase有效数据"""
        # Arrange
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User"
        }
        
        # Act
        user_base = UserBase(**data)
        
        # Assert
        assert user_base.username == "testuser"
        assert user_base.email == "test@example.com"
        assert user_base.full_name == "Test User"
    
    def test_user_base_without_full_name(self):
        """测试UserBase不包含full_name"""
        # Arrange
        data = {
            "username": "testuser",
            "email": "test@example.com"
        }
        
        # Act
        user_base = UserBase(**data)
        
        # Assert
        assert user_base.username == "testuser"
        assert user_base.email == "test@example.com"
        assert user_base.full_name is None
    
    @pytest.mark.parametrize("invalid_email", [
        "invalid-email",
        "test@",
        "@example.com",
        "test.example.com",
        "",
        "test@.com",
        "test@com",
    ])
    def test_user_base_invalid_email(self, invalid_email):
        """参数化测试UserBase无效邮箱"""
        # Arrange
        data = {
            "username": "testuser",
            "email": invalid_email
        }
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserBase(**data)
        
        assert "email" in str(exc_info.value)
    
    @pytest.mark.parametrize("invalid_username", [
        "",
        None,
    ])
    def test_user_base_invalid_username(self, invalid_username):
        """参数化测试UserBase无效用户名"""
        # Arrange
        data = {
            "username": invalid_username,
            "email": "test@example.com"
        }
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserBase(**data)
        
        assert "username" in str(exc_info.value)


@pytest.mark.unit
class TestUserCreate:
    """用户创建Schema测试"""
    
    def test_user_create_valid_data(self):
        """测试UserCreate有效数据"""
        # Arrange
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepassword123",
            "full_name": "New User"
        }
        
        # Act
        user_create = UserCreate(**data)
        
        # Assert
        assert user_create.username == "newuser"
        assert user_create.email == "new@example.com"
        assert user_create.password == "securepassword123"
        assert user_create.full_name == "New User"
    
    def test_user_create_minimal_data(self):
        """测试UserCreate最小数据"""
        # Arrange
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepassword123"
        }
        
        # Act
        user_create = UserCreate(**data)
        
        # Assert
        assert user_create.username == "newuser"
        assert user_create.email == "new@example.com"
        assert user_create.password == "securepassword123"
        assert user_create.full_name is None
    
    @pytest.mark.parametrize("invalid_password", [
        "",
        "short",
        "1234567",  # 7个字符，少于最小长度8
        None,
    ])
    def test_user_create_invalid_password(self, invalid_password):
        """参数化测试UserCreate无效密码"""
        # Arrange
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": invalid_password
        }
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        
        error_str = str(exc_info.value)
        assert "password" in error_str


@pytest.mark.unit
class TestUserLogin:
    """用户登录Schema测试"""
    
    def test_user_login_valid_data(self):
        """测试UserLogin有效数据"""
        # Arrange
        data = {
            "username": "loginuser",
            "password": "loginpassword"
        }
        
        # Act
        user_login = UserLogin(**data)
        
        # Assert
        assert user_login.username == "loginuser"
        assert user_login.password == "loginpassword"
    
    @pytest.mark.parametrize("missing_field", ["username", "password"])
    def test_user_login_missing_required_field(self, missing_field):
        """参数化测试UserLogin缺少必需字段"""
        # Arrange
        data = {
            "username": "loginuser",
            "password": "loginpassword"
        }
        del data[missing_field]
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(**data)
        
        assert missing_field in str(exc_info.value)


@pytest.mark.unit
class TestUserResponse:
    """用户响应Schema测试"""
    
    def test_user_response_valid_data(self):
        """测试UserResponse有效数据"""
        # Arrange
        data = {
            "id": "user-123",
            "username": "responseuser",
            "email": "response@example.com",
            "full_name": "Response User",
            "is_active": True,
            "created_at": "2024-01-01T12:00:00"
        }
        
        # Act
        user_response = UserResponse(**data)
        
        # Assert
        assert user_response.id == "user-123"
        assert user_response.username == "responseuser"
        assert user_response.email == "response@example.com"
        assert user_response.full_name == "Response User"
        assert user_response.is_active is True
        assert user_response.created_at == "2024-01-01T12:00:00"
    
    def test_user_response_default_values(self):
        """测试UserResponse默认值"""
        # Arrange
        data = {
            "id": "user-123",
            "username": "responseuser",
            "email": "response@example.com"
        }
        
        # Act
        user_response = UserResponse(**data)
        
        # Assert
        assert user_response.is_active is True  # 默认值
        assert user_response.created_at is None  # 默认值
        assert user_response.full_name is None  # 默认值
    
    def test_user_response_excludes_password(self):
        """测试UserResponse不包含密码字段"""
        # Arrange
        data = {
            "id": "user-123",
            "username": "responseuser",
            "email": "response@example.com",
            "password": "should_not_appear",  # 这个字段应该被忽略
            "hashed_password": "should_not_appear"  # 这个字段应该被忽略
        }
        
        # Act
        user_response = UserResponse(**data)
        response_dict = user_response.model_dump()
        
        # Assert
        assert "password" not in response_dict
        assert "hashed_password" not in response_dict
        assert user_response.username == "responseuser"


@pytest.mark.unit
class TestUserUpdate:
    """用户更新Schema测试"""
    
    def test_user_update_all_fields(self):
        """测试UserUpdate所有字段"""
        # Arrange
        data = {
            "email": "updated@example.com",
            "full_name": "Updated User",
            "is_active": False
        }
        
        # Act
        user_update = UserUpdate(**data)
        
        # Assert
        assert user_update.email == "updated@example.com"
        assert user_update.full_name == "Updated User"
        assert user_update.is_active is False
    
    def test_user_update_partial_fields(self):
        """测试UserUpdate部分字段"""
        # Arrange
        data = {
            "email": "updated@example.com"
        }
        
        # Act
        user_update = UserUpdate(**data)
        
        # Assert
        assert user_update.email == "updated@example.com"
        assert user_update.full_name is None
        assert user_update.is_active is None
    
    def test_user_update_empty_data(self):
        """测试UserUpdate空数据"""
        # Arrange
        data = {}
        
        # Act
        user_update = UserUpdate(**data)
        
        # Assert
        assert user_update.email is None
        assert user_update.full_name is None
        assert user_update.is_active is None
    
    def test_user_update_invalid_email(self):
        """测试UserUpdate无效邮箱"""
        # Arrange
        data = {
            "email": "invalid-email"
        }
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(**data)
        
        assert "email" in str(exc_info.value)


@pytest.mark.unit
class TestPasswordChange:
    """密码修改Schema测试"""
    
    def test_password_change_valid_data(self):
        """测试PasswordChange有效数据"""
        # Arrange
        data = {
            "old_password": "oldpassword123",
            "new_password": "newpassword456"
        }
        
        # Act
        password_change = PasswordChange(**data)
        
        # Assert
        assert password_change.old_password == "oldpassword123"
        assert password_change.new_password == "newpassword456"
    
    @pytest.mark.parametrize("field_name,invalid_value", [
        ("old_password", ""),
        ("old_password", None),
        ("new_password", ""),
        ("new_password", None),
        ("new_password", "short"),  # 少于8个字符
    ])
    def test_password_change_invalid_data(self, field_name, invalid_value):
        """参数化测试PasswordChange无效数据"""
        # Arrange
        data = {
            "old_password": "oldpassword123",
            "new_password": "newpassword456"
        }
        data[field_name] = invalid_value
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            PasswordChange(**data)
        
        assert field_name in str(exc_info.value)


@pytest.mark.unit
class TestToken:
    """令牌Schema测试"""
    
    def test_token_valid_data(self):
        """测试Token有效数据"""
        # Arrange
        data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_in": 3600
        }
        
        # Act
        token = Token(**data)
        
        # Assert
        assert token.access_token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        assert token.token_type == "bearer"
        assert token.expires_in == 3600
    
    def test_token_default_values(self):
        """测试Token默认值"""
        # Arrange
        data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
        
        # Act
        token = Token(**data)
        
        # Assert
        assert token.access_token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        assert token.token_type == "bearer"  # 默认值
        assert token.expires_in is None  # 默认值
    
    def test_token_missing_access_token(self):
        """测试Token缺少access_token"""
        # Arrange
        data = {
            "token_type": "bearer"
        }
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Token(**data)
        
        assert "access_token" in str(exc_info.value)


@pytest.mark.unit
class TestTokenData:
    """令牌数据Schema测试"""
    
    def test_token_data_valid_data(self):
        """测试TokenData有效数据"""
        # Arrange
        data = {
            "username": "tokenuser",
            "user_id": "user-123"
        }
        
        # Act
        token_data = TokenData(**data)
        
        # Assert
        assert token_data.username == "tokenuser"
        assert token_data.user_id == "user-123"
    
    def test_token_data_partial_data(self):
        """测试TokenData部分数据"""
        # Arrange
        data = {
            "username": "tokenuser"
        }
        
        # Act
        token_data = TokenData(**data)
        
        # Assert
        assert token_data.username == "tokenuser"
        assert token_data.user_id is None
    
    def test_token_data_empty_data(self):
        """测试TokenData空数据"""
        # Arrange
        data = {}
        
        # Act
        token_data = TokenData(**data)
        
        # Assert
        assert token_data.username is None
        assert token_data.user_id is None


@pytest.mark.unit
class TestSchemaIntegration:
    """Schema集成测试"""
    
    def test_user_creation_to_response_flow(self):
        """测试用户创建到响应的完整流程"""
        # Arrange
        create_data = {
            "username": "flowuser",
            "email": "flow@example.com",
            "password": "flowpassword123",
            "full_name": "Flow User"
        }
        
        # Act - 创建用户Schema
        user_create = UserCreate(**create_data)
        
        # Act - 模拟创建用户后的响应数据
        response_data = {
            "id": "user-flow-123",
            "username": user_create.username,
            "email": user_create.email,
            "full_name": user_create.full_name,
            "is_active": True,
            "created_at": "2024-01-01T12:00:00"
        }
        
        # Act - 创建响应Schema
        user_response = UserResponse(**response_data)
        
        # Assert
        assert user_response.username == create_data["username"]
        assert user_response.email == create_data["email"]
        assert user_response.full_name == create_data["full_name"]
        assert "password" not in user_response.model_dump()
    
    def test_user_update_schema_flexibility(self):
        """测试用户更新Schema的灵活性"""
        # Arrange & Act - 只更新邮箱
        email_update = UserUpdate(email="newemail@example.com")
        
        # Arrange & Act - 只更新全名
        name_update = UserUpdate(full_name="New Full Name")
        
        # Arrange & Act - 只更新状态
        status_update = UserUpdate(is_active=False)
        
        # Assert
        assert email_update.email == "newemail@example.com"
        assert email_update.full_name is None
        assert email_update.is_active is None
        
        assert name_update.email is None
        assert name_update.full_name == "New Full Name"
        assert name_update.is_active is None
        
        assert status_update.email is None
        assert status_update.full_name is None
        assert status_update.is_active is False 