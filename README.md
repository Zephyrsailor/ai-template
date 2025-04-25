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

## 版本历史

- **v1.1.0** - 添加知识库管理功能，支持文档上传与语义检索
- **v1.0.0** - 初始版本，包含基本聊天功能和思考状态

## 代码架构

### 前端结构
```
frontend/
├── public/          # 静态资源
├── src/             # 源代码
│   ├── components/  # 组件
│   │   ├── ChatInterface.js     # 聊天界面
│   │   ├── ChatMessages.js      # 消息历史
│   │   ├── ThinkingBubble.js    # 思考气泡
│   │   ├── MessageBubble.js     # 消息气泡
│   │   ├── MarkdownRenderer.js  # Markdown渲染
│   │   ├── KnowledgeManager.js  # 知识库管理
│   │   └── Sidebar.js           # 侧边栏
│   ├── App.js       # 应用入口
│   ├── index.js     # 渲染入口
│   └── theme.js     # 主题配置
└── package.json     # 依赖配置
```

### 后端结构
```
backend/
├── app/                 # 应用代码
│   ├── routes/          # API路由
│   │   ├── chat.py      # 聊天API
│   │   ├── health.py    # 健康检查API
│   │   └── knowledge.py # 知识库API
│   ├── providers/       # 服务提供者
│   │   ├── base.py      # 基类
│   │   └── openai.py    # OpenAI实现
│   ├── knowledge/       # 知识库模块
│   │   ├── service.py   # 知识库服务
│   │   ├── chunking.py  # 文档分块
│   │   └── config.py    # 知识库配置
│   ├── data/            # 数据存储
│   │   └── knowledge/   # 知识库数据
│   ├── config.py        # 应用配置
│   └── main.py          # 应用入口
└── requirements.txt     # 依赖配置
```

### 知识库架构
```
知识库服务（KnowledgeService）
├── 初始化
│   ├── 目录设置           # 创建知识库存储路径
│   └── 知识库加载         # 加载已有知识库
├── 知识库管理
│   ├── 创建知识库         # create_knowledge_base
│   ├── 删除知识库         # delete_knowledge_base
│   ├── 获取知识库列表     # list_knowledge_bases
│   └── 获取知识库详情     # get_knowledge_base
├── 文档管理
│   ├── 上传文档           # upload_file, upload_folder
│   ├── 删除文档           # delete_file, delete_files
│   ├── 获取文档列表       # list_files
│   └── 文档处理           # _process_document
└── 向量检索
    ├── 文本查询           # query
    ├── 向量存储           # _create_or_get_index
    └── 文档分块           # StructureAwareChunker
```