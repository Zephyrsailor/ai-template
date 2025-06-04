# AI聊天应用模板

一个功能完整的AI聊天应用模板，支持流式响应、思考状态展示和多轮对话记忆，可用于快速构建各类AI助手应用。

## 功能特点

- ✨ 现代化的UI界面，响应式设计
- 🔄 流式响应，实时显示AI回复
- 💭 思考状态展示，直观呈现AI思考过程
- 📝 多轮对话记忆功能
- 📚 知识库管理，支持文档上传与语义检索
- 🧩 模块化设计，易于扩展
- 🌐 可作为各类AI应用的起点

## 技术栈

### 前端
- React.js
- Styled Components
- React Icons
- Markdown渲染

### 后端
- Python
- FastAPI
- 异步流处理
- OpenAI/自定义LLM适配器

## 项目结构

```
ai-template/
├── frontend/                # 前端React应用
│   ├── public/              # 静态资源 (e.g., index.html)
│   ├── src/                 # React源代码
│   │   ├── api/             # API请求模块
│   │   ├── components/      # UI组件
│   │   ├── styles/          # 样式文件
│   │   ├── App.js           # 应用主组件
│   │   └── index.js         # 应用入口
│   ├── package.json         # 前端依赖与脚本
│   └── ...                  # 其他配置文件 (tailwind.config.js, postcss.config.js, etc.)
└── backend/                 # Python后端应用
    ├── app/                 # FastAPI应用代码
    │   ├── main.py          # FastAPI 应用入口
    │   ├── api/             # API层
    │   │   ├── __init__.py  # API模块导出
    │   │   └── routes/      # API路由
    │   │       ├── __init__.py      # 路由集成器
    │   │       ├── auth.py          # 认证路由
    │   │       ├── chat.py          # 聊天路由
    │   │       ├── conversations.py # 会话路由
    │   │       ├── health.py        # 健康检查路由
    │   │       ├── knowledge.py     # 知识库路由
    │   │       ├── mcp.py           # MCP工具路由
    │   │       └── users.py         # 用户路由
    │   ├── core/            # 核心组件
    │   │   ├── config.py    # 应用配置
    │   │   ├── security.py  # 安全认证
    │   │   ├── logging.py   # 日志管理
    │   │   ├── repository.py # Repository基类
    │   │   ├── service.py   # Service基类
    │   │   ├── database.py  # 数据库管理
    │   │   └── errors.py    # 异常处理
    │   ├── config/          # 配置模块
    │   │   ├── __init__.py  # 配置模块导出
    │   │   ├── database.py  # 数据库配置
    │   │   ├── security.py  # 安全配置
    │   │   ├── logging.py   # 日志配置
    │   │   ├── providers.py # Provider配置
    │   │   └── messages/    # 国际化消息
    │   ├── domain/          # 领域模型
    │   │   ├── models/      # 数据模型
    │   │   │   ├── user.py          # 用户模型
    │   │   │   ├── conversation.py  # 会话模型
    │   │   │   ├── events.py        # 事件模型
    │   │   │   └── user_llm_config.py # 用户LLM配置模型
    │   │   └── schemas/     # 数据Schema
    │   │       ├── user.py          # 用户Schema
    │   │       ├── chat.py          # 聊天Schema
    │   │       ├── conversation.py  # 会话Schema
    │   │       └── tools.py         # 工具Schema
    │   ├── repositories/    # 数据访问层
    │   │   ├── __init__.py          # Repository模块导出
    │   │   ├── knowledge_repository.py # 知识库Repository
    │   │   ├── user_repository.py   # 用户Repository
    │   │   ├── conversation_repository.py # 会话Repository
    │   │   └── mcp_repository.py    # MCP Repository
    │   ├── services/        # 业务服务层
    │   │   ├── chat.py      # 聊天服务
    │   │   ├── knowledge.py # 知识库服务
    │   │   ├── user.py      # 用户服务
    │   │   ├── user_llm_config.py # 用户LLM配置服务
    │   │   ├── search.py    # 搜索服务
    │   │   └── mcp.py       # MCP服务
    │   └── lib/             # 核心库
    │       ├── knowledge/   # 知识库功能
    │       ├── mcp/         # MCP工具集成
    │       └── providers/   # LLM Providers
    │           ├── base.py      # Provider基类
    │           ├── openai.py    # OpenAI Provider
    │           ├── deepseek.py  # DeepSeek Provider
    │           ├── gemini.py    # Gemini Provider
    │           ├── azure.py     # Azure OpenAI Provider
    │           └── ollama.py    # Ollama Provider
    ├── requirements.txt     # Python依赖
    ├── run.py               # 应用启动脚本
    ├── .env.example         # 环境变量示例
    └── ...                  # 其他文件 (e.g. architecture.md)
```

## 组件说明

### 前端主要组件

- **ChatInterface**: 聊天界面主组件，处理消息发送和接收
- **ChatMessages**: 显示消息历史
- **ThinkingBubble**: 思考气泡组件，显示AI思考过程
- **MessageBubble**: 消息气泡组件
- **MarkdownRenderer**: Markdown内容渲染器
- **KnowledgeManager**: 知识库管理组件，支持文档上传与管理
- **Sidebar**: 侧边栏导航

### 后端主要模块

- **app/main.py**: FastAPI应用入口
- **app/api/**: API层，包含路由 (`app/api/routes`) 和依赖 (`app/api/deps.py`)
- **app/core/**: 核心组件，如配置 (`app/core/config.py`)、数据库 (`app/core/database.py`) 和安全模块
- **app/services/**: 业务逻辑服务，如聊天服务 (`app/services/chat.py`) 和知识库服务 (`app/services/knowledge.py`)
- **app/lib/knowledge/**: 知识库功能的核心实现
- **app/lib/providers/**: LLM及其他外部服务提供者的适配层
- **app/domain/**: 应用的数据结构，包括数据模型 (`app/domain/models`) 和校验模式 (`app/domain/schemas`)
- **manage_db.py**: 数据库管理脚本，用于创建和重置数据库表

## 快速开始

### 前置条件

- Python >= 3.11
- Node.js >= 18.0.0
- npm 或 yarn
- PostgreSQL >= 12.0

### 安装步骤

#### 1. 克隆仓库
```bash
git clone https://github.com/yourusername/ai-template.git
cd ai-template
```

#### 2. 安装PostgreSQL (macOS)

使用Homebrew安装PostgreSQL：
```bash
# 安装PostgreSQL
brew install postgresql@14

# 启动PostgreSQL服务
brew services start postgresql@14

# 创建项目数据库
createdb ai_template
```

**macOS PostgreSQL配置说明：**
- 默认用户：当前系统用户名（无密码）
- 默认端口：5432
- 数据目录：`/opt/homebrew/var/postgresql@14/`
- 配置文件：`/opt/homebrew/var/postgresql@14/postgresql.conf`

#### 3. 安装前端依赖
```bash
cd frontend
npm install
```

#### 4. 安装后端依赖
```bash
cd ../backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 5. 配置环境变量
```bash
# 在backend目录创建.env文件
cp env.example .env
```

**macOS环境变量配置：**
```bash
# 数据库配置 (macOS默认配置)
DATABASE_URL=postgresql+asyncpg://$(whoami)@localhost:5432/ai_template

# 如果设置了密码，使用：
# DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/ai_template

# API密钥配置
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_URL=https://api.deepseek.com/

# LLM配置
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

#### 6. 初始化数据库

```bash
cd backend
./scripts/init_db.sh
```

#### 7. 启动开发服务器

**后端服务：**
```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端服务：**
```bash
cd frontend
npm start
```

#### 8. 访问应用
- 前端界面：[http://localhost:3000](http://localhost:3000)
- 后端API文档：[http://localhost:8000/docs](http://localhost:8000/docs)
- 健康检查：[http://localhost:8000/health](http://localhost:8000/health)

## 故障排除

### macOS常见问题

#### PostgreSQL连接问题
```bash
# 检查PostgreSQL服务状态
brew services list | grep postgresql

# 启动PostgreSQL服务
brew services start postgresql@14

# 检查数据库是否存在
psql -l | grep ai_template

# 创建数据库（如果不存在）
createdb ai_template
```

#### Python依赖问题
```bash
# 确保使用虚拟环境
cd backend
source venv/bin/activate

# 安装缺失的依赖
pip install python-json-logger

# 重新安装所有依赖
pip install -r requirements.txt
```

#### 端口占用问题
```bash
# 检查端口占用
lsof -i :8000
lsof -i :3000

# 杀死占用进程
kill -9 <PID>
```

## 数据库管理

### 数据库架构
项目采用混合存储架构：
- **PostgreSQL**: 存储元数据（用户、知识库、对话、消息等）
- **文件系统**: 存储原始文档和上传文件
- **ChromaDB**: 存储向量索引和语义检索数据

### 数据库操作

#### 一键切换数据库类型

项目支持PostgreSQL、MySQL、SQLite三种数据库，只需修改环境变量即可切换：

```bash
# 切换到PostgreSQL（默认）
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/ai_template

# 切换到MySQL
DATABASE_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=ai_template

# 切换到SQLite
DATABASE_TYPE=sqlite
SQLITE_PATH=data/ai_template.db
```

#### 数据库管理脚本

```bash
# 初始化数据库
./scripts/init_db.sh
```

### 生产环境部署
1. 确保PostgreSQL服务运行
2. 创建数据库：`createdb ai_template`
3. 配置环境变量中的`DATABASE_URL`
4. 应用启动时会自动创建表结构

### 开发环境快速重置
```bash
# 如果需要清空所有数据重新开始，重新运行初始化脚本
./scripts/init_db.sh
```

## 使用指南

### 基本对话
- 在输入框中输入消息并发送
- AI会开始思考，显示思考状态
- 回复会以流式方式显示

### 使用知识库
- 在知识库管理页面创建新的知识库
- 上传文档（支持PDF、TXT等格式）
- 使用知识库进行对话查询
- 对话中引用相关知识源

### 移动端使用
- 界面已适配移动设备
- 触摸滚动优化
- 响应式布局

## 扩展指南

### 添加新的LLM提供者
1. 在`backend/app/providers`目录下创建新提供者文件
2. 实现BaseProvider接口
3. 在配置中启用新提供者

### 自定义界面
- 修改`frontend/src/styles/GlobalStyles.js`调整全局样式
- 调整组件样式可编辑相应的样式定义

## 问题解决

### 常见问题

1. **API连接错误**
   - 检查API密钥配置
   - 确认网络连接正常

2. **样式显示问题**
   - 检查GlobalStyles是否正确导入
   - 确认样式变量定义

## 贡献指南

欢迎提交PR改进这个模板。请确保：
1. 代码风格一致
2. 添加适当的注释
3. 更新相关文档

## 许可证

MIT

---

## 版本历史

- **v1.1.0** - 添加知识库管理功能，支持文档上传与语义检索
- **v1.0.0** - 初始版本，包含基本聊天功能和思考状态