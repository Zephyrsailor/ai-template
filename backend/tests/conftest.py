"""
pytest配置文件 - 全局fixtures和测试配置
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_session
from app.domain.models.user import User, UserRole
from tests.factories import TestDataBuilder

# 测试数据库配置
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """创建异步数据库会话"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()
        await session.close()

@pytest.fixture
def mock_db_session() -> Mock:
    """Mock数据库会话"""
    session = Mock(spec=AsyncSession)
    session.add = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    return session

@pytest.fixture
def client() -> TestClient:
    """测试客户端"""
    return TestClient(app)

@pytest.fixture
def sample_user() -> User:
    """示例用户数据"""
    return TestDataBuilder.create_user()

@pytest.fixture
def sample_user_dict() -> dict:
    """示例用户字典数据"""
    return {
        "id": "test-user-id",
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "hashed_password": "hashed_password_123",
        "role": UserRole.USER.value
    }

@pytest.fixture
def admin_user() -> User:
    """管理员用户"""
    return TestDataBuilder.create_user(role=UserRole.ADMIN.value)

@pytest.fixture
def authenticated_user() -> User:
    """已认证用户"""
    return TestDataBuilder.create_user()

@pytest.fixture
def inactive_user() -> User:
    """非活跃用户"""
    return TestDataBuilder.create_user()

@pytest.fixture
def mock_logger():
    """Mock日志记录器"""
    return Mock()

# 测试数据清理
@pytest.fixture(scope="function")
def clean_database():
    """确保每个测试都有干净的数据库状态"""
    # 测试前清理
    yield
    # 测试后清理
    pass

# 异步测试标记
pytest_plugins = ["pytest_asyncio"] 