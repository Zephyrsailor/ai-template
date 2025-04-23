# AI聊天应用 - React前端

这是使用React实现的AI聊天应用前端，提供了更美观友好的用户界面。

## 功能特点

- 现代化UI界面，使用React和styled-components构建
- 实时显示AI思考过程
- 自适应布局，支持移动端和桌面端
- 消息气泡设计，区分用户和AI助手
- 支持展开/收起思考内容
- 优化的输入体验，支持Enter发送和Shift+Enter换行

## 安装和运行

1. 安装依赖：

```bash
cd frontend
npm install
```

2. 启动开发服务器：

```bash
npm start
```

应用将在 [http://localhost:3000](http://localhost:3000) 启动。

## 与后端连接

确保后端服务器正在运行（默认在端口8000上）：

```bash
cd ../backend
python -m uvicorn app.main:app --reload --port 8000
```

## 构建生产版本

```bash
npm run build
```

构建后的文件将在 `build` 目录中。

## 自定义

- 修改`src/components`中的组件以定制UI
- 在`ChatInterface.js`中更改API端点URL以连接到不同的后端服务器
- 调整样式和主题颜色以匹配您的品牌 