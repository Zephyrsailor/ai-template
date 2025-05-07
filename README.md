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
│   ├── public/              # 静态资源
│   └── src/                 # 源代码
│       ├── components/      # 组件
│       └── styles/          # 样式
└── backend/                 # Python后端应用
    ├── app/                 # 应用代码
    │   ├── main.py          # FastAPI 入口
    │   ├── config.py        # 配置项
    │   ├── routes           # 路由
    │   └── providers/       # LLM服务提供者
    └── requirements.txt     # Python依赖
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
- **app/routes/**: API路由定义
- **app/providers/**: LLM服务提供者实现
- **app/knowledge/**: 知识库管理服务模块

## 快速开始

### 前置条件

- Python >= 3.11
- Node.js >= 18.0.0
- npm 或 yarn

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/yourusername/ai-template.git
cd ai-template
```

2. 安装前端依赖
```bash
cd frontend
npm install
```

3. 安装后端依赖
```bash
cd ../backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. 配置环境变量
```bash
# 在backend目录创建.env文件
cp .env.example .env  # 然后编辑.env文件
```

添加以下内容到.env文件：
```
API秘钥
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_URL=https://api.deepseek.com/
```

5. 启动开发服务器

前端：
```bash
cd frontend
npm start
```

后端：
```bash
cd backend
uvicorn app.main:app --reload
```

6. 访问应用
浏览器打开 [http://localhost:3000](http://localhost:3000)

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

## 系统架构图

### 服务端架构图

```mermaid
graph TD
    ClientApps[Client Applications] -->|Connects via| TransportLayer[Transport Layer]

    subgraph TransportOptions [Transport Layer]
        direction TB
        subgraph Mechanisms [Transport Mechanisms]
            direction LR
            TM_WS[WebSocket]
            TM_STDIO[STDIO]
            TM_HTTP_SSE[HTTP/SSE]
        end
        
        subgraph Endpoints [Server Endpoints]
            EP_WS[websocket_server]
            EP_STDIO[stdio_server]
            EP_SSE[SseServerTransport]
        end

        TM_WS --> EP_WS
        TM_STDIO --> EP_STDIO
        TM_HTTP_SSE --> EP_SSE
    end
    TransportLayer --> Mechanisms


    ServerSession[ServerSession]
    EP_WS --> ServerSession
    EP_STDIO --> ServerSession
    EP_SSE --> ServerSession

    LowLevelServer[Server (low-level)]
    ServerSession -->|Communicates with| LowLevelServer

    subgraph ServerInternalLogic [Server Internal Logic and Components]
        RequestHandlers[Request Handlers]
        NotificationHandlers[Notification Handlers]
        ToolManager[ToolManager]
        ResourceManager[ResourceManager]
        PromptManager[PromptManager]
        FastMCP[FastMCP]
        RequestContext[RequestContext]

        LowLevelServer -->|Dispatches to| RequestHandlers
        LowLevelServer -->|Dispatches to| NotificationHandlers
        
        LowLevelServer -->|Delegates to| ToolManager
        LowLevelServer -->|Delegates to| ResourceManager
        LowLevelServer -->|Delegates to| PromptManager

        FastMCP -->|Manages| ToolManager
        FastMCP -->|Manages| ResourceManager
        FastMCP -->|Manages| PromptManager
        
        LowLevelServer -.->|Creates/Uses for Handlers| RequestContext
        ResourceManager -->|Uses| RequestContext
    end
```

### 请求处理流程图

```mermaid
sequenceDiagram
    participant Client
    participant ServerSession
    participant Server
    participant RequestHandler

    Client->>ServerSession: Send request
    ServerSession->>Server: Process message
    Server-->>Server: Identify handler
    Server-->>Server: Create request context
    Server->>RequestHandler: Call handler with request params
    RequestHandler-->>Server: Return result
    Server->>ServerSession: Send response
    ServerSession->>Client: Return response
```

## 版本历史

- **v1.1.0** - 添加知识库管理功能，支持文档上传与语义检索
- **v1.0.0** - 初始版本，包含基本聊天功能和思考状态

## 代码架构

### 前端结构
```mermaid
graph TD
    Frontend["frontend/"]
    Frontend --> Public["public/ (静态资源)"]
    Frontend --> Src["src/ (源代码)"]
    Frontend --> PackageJson["package.json (依赖配置)"]

    Src --> Components["components/ (组件)"]
    Src --> AppJs["App.js (应用入口)"]
    Src --> IndexJs["index.js (渲染入口)"]
    Src --> ThemeJs["theme.js (主题配置)"]

    Components --> ChatInterface["ChatInterface.js (聊天界面)"]
    Components --> ChatMessages["ChatMessages.js (消息历史)"]
    Components --> ThinkingBubble["ThinkingBubble.js (思考气泡)"]
    Components --> MessageBubble["MessageBubble.js (消息气泡)"]
    Components --> MarkdownRenderer["MarkdownRenderer.js (Markdown渲染)"]
    Components --> KnowledgeManager["KnowledgeManager.js (知识库管理)"]
    Components --> Sidebar["Sidebar.js (侧边栏)"]
```

### 后端整体架构
```mermaid
graph TD
    subgraph Client [Client Application]
        HTTPRequest[HTTP Request]
    end

    subgraph BackendApp [Backend FastAPI Application]
        direction LR
        FastAPI_App["FastAPI App (main.py)"]

        subgraph CoreComponents [Core FastAPI & App Components]
            direction TB
            Middleware["Middleware (CORS, Error Handling)"]
            DepInjection["Dependency Injection"]
            AppConfig["App Configuration (core/config.py)"]
        end
        
        APIRouter_Main["Main API Router (api/__init__.py)"]

        FastAPI_App --> Middleware
        FastAPI_App --> DepInjection
        FastAPI_App --> AppConfig
        FastAPI_App --> APIRouter_Main
        
        subgraph ModuleRouters [API Module Routers (api/routes/)]
            direction TB
            ChatRouter["Chat Router (chat.py)"]
            KnowledgeRouter["Knowledge Router (knowledge.py)"]
            MCPRouter["MCP Router (mcp.py)"]
        end
        APIRouter_Main --> ModuleRouters

        subgraph Services [Application Services (services/)]
            direction TB
            ChatService_S["ChatService (chat.py)"]
            KnowledgeService_S["KnowledgeService (knowledge.py)"]
            MCPService_S["MCPService (mcp.py)"]
        end
        
        ChatRouter --> ChatService_S
        KnowledgeRouter --> KnowledgeService_S
        MCPRouter --> MCPService_S

        subgraph Libraries [Libraries & Data (lib/, data/)]
            direction TB
            LLMProviders["LLM Providers (lib/providers/)"]
            KnowledgeLib["Knowledge Lib (lib/knowledge/)"]
            MCPLib["MCP Lib (lib/mcp/)"]
            KnowledgeDataStore["Knowledge Data (data/knowledge/)"]
        end

        ChatService_S --> LLMProviders
        KnowledgeService_S --> KnowledgeLib
        KnowledgeService_S --> KnowledgeDataStore
        MCPService_S --> MCPLib
        
        AppConfig --> Services
        AppConfig --> Libraries
    end
    
    HTTPRequest --> FastAPI_App
```

### 后端文件结构
```mermaid
graph TD
    Backend["backend/"]
    Backend --> App["app/ (应用代码)"]
    Backend --> Requirements["requirements.txt (依赖配置)"]

    App --> Routes["routes/ (API路由)"]
    App --> Providers["providers/ (服务提供者)"]
    App --> Knowledge["knowledge/ (知识库模块)"]
    App --> Data["data/ (数据存储)"]
    App --> ConfigPy["config.py (应用配置)"]
    App --> MainPy["main.py (应用入口)"]

    Routes --> ChatPy["chat.py (聊天API)"]
    Routes --> HealthPy["health.py (健康检查API)"]
    Routes --> KnowledgeApiPy["knowledge.py (知识库API)"]

    Providers --> BasePy["base.py (基类)"]
    Providers --> OpenaiPy["openai.py (OpenAI实现)"]

    Knowledge --> KnowledgeServicePy["service.py (知识库服务)"]
    Knowledge --> ChunkingPy["chunking.py (文档分块)"]
    Knowledge --> KnowledgeConfigPy["config.py (知识库配置)"]
    
    Data --> KnowledgeData["knowledge/ (知识库数据)"]
```

### 知识库架构
```mermaid
graph TD
    KnowledgeService["知识库服务 (KnowledgeService)"]

    subgraph Initialization["初始化"]
        direction LR
        InitDir["目录设置 (创建知识库存储路径)"]
        InitLoad["知识库加载 (加载已有知识库)"]
    end
    KnowledgeService --> Initialization

    subgraph KBManagement["知识库管理"]
        direction LR
        CreateKB["创建知识库 (create_knowledge_base)"]
        DeleteKB["删除知识库 (delete_knowledge_base)"]
        ListKBs["获取知识库列表 (list_knowledge_bases)"]
        GetKBDetail["获取知识库详情 (get_knowledge_base)"]
    end
    KnowledgeService --> KBManagement

    subgraph DocManagement["文档管理"]
        direction LR
        UploadDoc["上传文档 (upload_file, upload_folder)"]
        DeleteDoc["删除文档 (delete_file, delete_files)"]
        ListDocs["获取文档列表 (list_files)"]
        ProcessDoc["文档处理 (_process_document)"]
    end
    KnowledgeService --> DocManagement

    subgraph VectorSearch["向量检索"]
        direction LR
        QueryText["文本查询 (query)"]
        VectorStore["向量存储 (_create_or_get_index)"]
        DocChunking["文档分块 (StructureAwareChunker)"]
    end
    KnowledgeService --> VectorSearch
```

### mcp架构
```mermaid
graph TD
    MCP["/mcp"]
    MCP --> InitPy["__init__.py (主入口点，导出公共 API)"]
    MCP --> HostPy["host.py (MCP主机类，对外提供统一接口)"]
    MCP --> ConfigPy["config.py (配置提供器)"]
    MCP --> ConnectionPy["connection.py (连接管理器)"]
    MCP --> SessionPy["session.py (会话管理器)"]
    MCP --> Managers["managers/"]
    MCP --> Models["models/"]
    MCP --> Utils["utils/"]

    Managers --> MgrInitPy["__init__.py (导出所有管理器)"]
    Managers --> MgrBasePy["base.py (基础管理器类)"]
    Managers --> ToolPy["tool.py (工具管理器)"]
    Managers --> PromptPy["prompt.py (提示管理器)"]
    Managers --> ResourcePy["resource.py (资源管理器)"]

    Models --> ModInitPy["__init__.py (导出所有数据模型)"]
    Models --> NamespacedPy["namespaced.py (命名空间对象模型)"]
    Models --> ModCachePy["cache.py (缓存模型)"]

    Utils --> UtilInitPy["__init__.py (导出所有工具函数)"]
    Utils --> LoggerPy["logger.py (日志工具)"]
    Utils --> UtilCachePy["cache.py (缓存工具)"]
```
