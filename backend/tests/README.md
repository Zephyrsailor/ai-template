# 测试文档

本项目采用标准的Python测试规范，使用pytest作为测试框架。

## 目录结构

```
tests/
├── __init__.py                 # 测试包初始化
├── conftest.py                 # pytest配置和全局fixtures
├── factories.py                # 测试数据工厂
├── README.md                   # 测试文档
├── unit/                       # 单元测试
│   ├── __init__.py
│   ├── test_models/           # 模型层测试
│   │   ├── __init__.py
│   │   └── test_user.py
│   ├── test_schemas/          # Schema层测试
│   │   ├── __init__.py
│   │   └── test_user.py
│   ├── test_repositories/     # Repository层测试
│   │   ├── __init__.py
│   │   └── test_user.py
│   ├── test_services/         # Service层测试
│   │   ├── __init__.py
│   │   └── test_user.py
│   └── test_routes/           # 路由层测试
│       ├── __init__.py
│       └── test_user.py
└── integration/               # 集成测试
    ├── __init__.py
    └── test_user_flow.py
```

## 测试分层

### 1. 单元测试 (Unit Tests)

#### Model层测试
- 测试数据模型的字段验证
- 测试模型方法逻辑
- 测试数据转换功能
- 不涉及数据库操作

#### Schema层测试
- 测试Pydantic模型的序列化/反序列化
- 测试字段验证规则
- 测试数据转换逻辑

#### Repository层测试
- 测试数据库CRUD操作
- 测试查询逻辑
- 使用Mock数据库连接

#### Service层测试
- 测试业务逻辑
- 测试服务间协调
- 测试错误处理
- 测试事务管理

#### Routes层测试
- 测试HTTP请求/响应
- 测试状态码
- 测试数据序列化
- 测试认证授权

### 2. 集成测试 (Integration Tests)

- 测试完整的业务流程
- 测试多个组件间的协作
- 测试端到端的用户操作流程

## 运行测试

### 基本命令

```bash
# 运行所有测试
python run_tests.py

# 运行单元测试
python run_tests.py --unit

# 运行集成测试
python run_tests.py --integration

# 生成覆盖率报告
python run_tests.py --coverage

# 并行运行测试
python run_tests.py --parallel

# 详细输出
python run_tests.py --verbose
```

### 高级选项

```bash
# 运行特定文件的测试
python run_tests.py --file tests/unit/test_models/test_user.py

# 按模式过滤测试
python run_tests.py --pattern "test_create"

# 只运行失败的测试
python run_tests.py --last-failed

# 遇到第一个失败就停止
python run_tests.py --fail-fast

# 生成HTML报告
python run_tests.py --html

# 调试模式
python run_tests.py --debug
```

### 直接使用pytest

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest -m unit

# 运行集成测试
pytest -m integration

# 生成覆盖率报告
pytest --cov=app --cov-report=html

# 并行运行
pytest -n auto

# 详细输出
pytest -v
```

## 测试标记

项目使用以下pytest标记：

- `@pytest.mark.unit`: 单元测试
- `@pytest.mark.integration`: 集成测试
- `@pytest.mark.e2e`: 端到端测试
- `@pytest.mark.slow`: 耗时测试
- `@pytest.mark.database`: 需要数据库的测试
- `@pytest.mark.external`: 需要外部服务的测试

## 测试数据

### Factories

使用`factory-boy`创建测试数据：

```python
from tests.factories import UserFactory, TestDataBuilder

# 使用Factory创建用户
user = UserFactory.build()

# 使用TestDataBuilder创建用户
user = TestDataBuilder.create_user(username="testuser")

# 批量创建用户
users = TestDataBuilder.create_users(count=5)
```

### Fixtures

在`conftest.py`中定义了全局fixtures：

- `client`: FastAPI测试客户端
- `mock_db_session`: Mock数据库会话
- `sample_user`: 示例用户数据
- `admin_user`: 管理员用户
- `authenticated_user`: 已认证用户

## 测试最佳实践

### 1. AAA模式

```python
def test_user_creation():
    # Arrange - 准备测试数据
    user_data = {"username": "testuser", "email": "test@example.com"}
    
    # Act - 执行被测试的操作
    user = create_user(user_data)
    
    # Assert - 验证结果
    assert user.username == "testuser"
    assert user.email == "test@example.com"
```

### 2. 描述性测试名称

```python
def test_should_create_user_when_valid_data_provided():
    """测试提供有效数据时应该创建用户"""
    pass

def test_should_raise_error_when_username_already_exists():
    """测试用户名已存在时应该抛出错误"""
    pass
```

### 3. 参数化测试

```python
@pytest.mark.parametrize("username,email,expected_valid", [
    ("validuser", "valid@example.com", True),
    ("", "valid@example.com", False),
    ("validuser", "invalid-email", False),
])
def test_user_validation(username, email, expected_valid):
    """参数化测试用户验证逻辑"""
    pass
```

### 4. Mock使用

```python
@pytest.mark.asyncio
async def test_user_service_with_mock():
    """使用Mock测试用户服务"""
    # 创建Mock对象
    mock_repository = Mock(spec=UserRepository)
    mock_repository.get_by_id.return_value = User(id=1, username="test")
    
    # 使用Mock
    user_service = UserService(mock_repository)
    result = await user_service.get_user(1)
    
    # 验证Mock调用
    mock_repository.get_by_id.assert_called_once_with(1)
    assert result.username == "test"
```

## 覆盖率要求

- 目标覆盖率：80%以上
- 关键业务逻辑：90%以上
- 新增代码：100%覆盖

## 持续集成

测试在以下情况下自动运行：

1. 代码提交时
2. Pull Request时
3. 合并到主分支时

## 故障排除

### 常见问题

1. **导入错误**: 确保PYTHONPATH正确设置
2. **异步测试失败**: 确保使用`@pytest.mark.asyncio`装饰器
3. **Mock不生效**: 检查Mock的路径是否正确
4. **数据库连接错误**: 确保使用Mock数据库会话

### 调试技巧

```bash
# 进入调试器
pytest --pdb

# 显示本地变量
pytest -l

# 显示最慢的测试
pytest --durations=10

# 只运行失败的测试
pytest --lf
``` 