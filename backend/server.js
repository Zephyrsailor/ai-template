const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const path = require('path');

// 导入路由
const chatRouter = require('./routes/chat');

const app = express();
const PORT = process.env.PORT || 8001;

// 中间件
app.use(cors());
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, '../frontend/build')));

// API路由
app.use('/api/chat', chatRouter);

// 所有其他请求返回React应用
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/build', 'index.html'));
});

// 启动服务器
app.listen(PORT, () => {
  console.log(`服务器运行在 http://localhost:${PORT}`);
  console.log(`聊天API: http://localhost:${PORT}/api/chat/stream`);
}); 