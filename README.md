# AI Template - 智能对话平台

🤖 **现代化的AI智能体平台**，集成多种AI能力，为用户提供强大的AI助手服务。

## 🎯 项目简介

AI Template 是一个**生产级的智能对话平台**，不仅仅是聊天机器人，而是真正的AI智能体：

### 🌟 核心特性
- 🤖 **多Provider LLM支持** - OpenAI、Claude、DeepSeek、Gemini、Ollama等
- 🔧 **MCP工具集成** - 通过Model Context Protocol集成外部工具和服务
- 📚 **RAG知识库** - 智能文档检索和知识问答
- 🌐 **网络搜索** - 实时获取最新信息
- 💬 **流式对话** - 实时响应，支持思考过程展示
- 👥 **多用户系统** - 完整的用户管理和权限控制
- 🔒 **企业级安全** - JWT认证、数据隔离、API密钥安全管理

### 🚀 技术亮点
- **ReAct智能体架构** - Reasoning + Acting的思考-行动循环
- **实时流式** - WebSocket + SSE双重流式支持

## 🛠️ 技术栈

### 前端
- **React 18** + TypeScript
- **Material-UI** - 现代化UI组件
- **Axios** + **EventSource** - HTTP + 流式通信
- **React Router** - 单页应用路由

### 后端
- **FastAPI** + **Uvicorn** - 高性能异步Web框架
- **SQLAlchemy** + **Alembic** - ORM和数据库迁移
- **MySQL 8.0** - 主数据库
- **Pydantic** - 数据验证和序列化
- **JWT** - 安全认证

## 📁 项目结构

```
ai-template/
├── frontend/                # 🎨 React前端应用
│   ├── src/
│   │   ├── components/      # UI组件
│   │   ├── api/             # API请求模块
│   │   └── App.js           # 应用主组件
│   └── package.json
└── backend/                 # ⚡ FastAPI后端应用
    ├── app/
    │   ├── main.py          # 应用入口
    │   ├── api/routes/      # API路由
    │   ├── services/        # 业务服务层
    │   ├── repositories/    # 数据访问层
    │   ├── domain/          # 领域模型
    │   └── lib/             # 核心库
    │       ├── providers/   # LLM Providers
    │       ├── mcp/         # MCP工具集成
    │       └── knowledge/   # 知识库功能
    ├── requirements.txt
    └── .env.example
```

> 📖 **详细架构说明**：查看 [docs/PROJECT_ARCHITECTURE.md](docs/PROJECT_ARCHITECTURE.md) 了解完整的系统架构设计

## 🚀 快速开始

### 📋 前置条件

- **Python** >= 3.11
- **Node.js** >= 18.0.0
- **MySQL** >= 8.0
- **npm** 或 yarn

### ⚡ 一键启动

#### 1. 克隆项目
```bash
git clone https://github.com/yourusername/ai-template.git
cd ai-template
```

#### 2. 准备MySQL数据库
```bash
# 确保MySQL服务运行 (可以使用Docker、Homebrew或其他方式)
# 例如使用Docker:
docker run -d --name mysql-ai -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mysql:8.0

# 或使用Homebrew (macOS):
brew install mysql
brew services start mysql
```

#### 3. 配置环境变量
```bash
cd backend
cp env.example .env
# 编辑.env文件，配置数据库和API密钥
```

#### 4. 安装依赖并启动
```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py

# 前端 (新终端)
cd frontend
npm install
npm start
```

#### 5. 访问应用
- 🌐 **前端界面**: http://localhost:3000
- 📡 **API文档**: http://localhost:8000/docs

### 🔧 环境变量配置

在 `backend/.env` 文件中配置：

```bash
# 复制示例配置文件
cp env.example .env

# 编辑配置文件，主要配置以下内容：

# 数据库配置
DATABASE_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=ai_template

# LLM配置 (选择一个Provider)
LLM_PROVIDER=deepseek  # 或 ollama
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 向量模型配置 (知识库会用到, 这里使用ollama pull bge-m3)
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL_NAME="bge-m3"

# 可选：网络搜索功能
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_google_custom_search_engine_id_here
```

### 🎯 功能演示

#### 💬 智能对话
- 支持多轮对话，具备上下文记忆
- 实时流式响应，展示AI思考过程
- 支持Markdown格式，代码高亮

#### 🔧 MCP工具集成
- 文件系统操作：读取、写入、搜索文件
- 网络搜索：获取实时信息
- 自定义工具：扩展AI能力

#### 📚 知识库RAG
- 上传文档，自动向量化
- 智能检索相关内容
- 基于知识库的问答

#### 👥 多用户管理
- 用户注册登录
- 独立的配置空间
- 数据隔离保护

## 🛠️ 开发指南

### 📝 添加新的LLM Provider
```bash
# 1. 创建Provider文件
backend/app/lib/providers/your_provider.py

# 2. 实现BaseProvider接口
# 3. 在配置中注册Provider
```

### 🔌 集成新的MCP服务器
```bash
# 1. 在MCP管理界面添加服务器
# 2. 配置连接参数
# 3. 测试工具调用
```

### 🎨 自定义界面
```bash
# 修改组件样式
frontend/src/components/

# 调整全局样式
frontend/src/styles/
```

## 📖 文档

- 📋 **[项目架构](docs/PROJECT_ARCHITECTURE.md)** - 完整的系统架构设计
- 🔧 **[MCP集成指南](backend/docs/MCP_COMPLETE_GUIDE.md)** - MCP服务集成详解
- 🚀 **部署指南** - 生产环境部署 (待完善)
- 🔒 **安全指南** - 安全最佳实践 (待完善)

## 🤝 贡献

欢迎提交Issue和Pull Request！

### 开发流程
1. Fork项目
2. 创建功能分支
3. 提交代码
4. 创建Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🌟 Star History

如果这个项目对你有帮助，请给个Star ⭐️

---

**AI Template** - 让AI智能体开发变得简单 🚀