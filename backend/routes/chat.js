/**
 * 聊天API路由
 */

const express = require('express');
const router = express.Router();
const { Readable } = require('stream');
const axios = require('axios');

// Deepseek API配置
const DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions';  // 替换为实际的API URL
const DEEPSEEK_API_KEY = process.env.DEEPSEEK_API_KEY || 'your_api_key_here';

/**
 * 处理聊天历史，确保符合deepseek-reasoner的要求
 * 消息必须按照user-assistant交替排列
 */
function processMessageHistory(history, currentMessage) {
  // 如果没有历史，直接返回当前用户消息
  if (history.length === 0) {
    return [{ role: 'user', content: currentMessage }];
  }
  
  const validHistory = [];
  let lastRole = null;
  
  // 处理历史消息
  for (const msg of history) {
    // 只接受user和assistant角色的消息
    if (msg.role !== 'user' && msg.role !== 'assistant') {
      continue;
    }
    
    // 如果与上一消息同类型，跳过或合并
    if (msg.role === lastRole) {
      // 选择合并内容而非跳过
      const lastIndex = validHistory.length - 1;
      if (lastIndex >= 0) {
        validHistory[lastIndex].content += "\n\n" + msg.content;
      }
    } else {
      validHistory.push({
        role: msg.role,
        content: msg.content
      });
      lastRole = msg.role;
    }
  }
  
  // 确保历史以assistant消息结尾，这样才能添加新的user消息
  if (validHistory.length > 0 && validHistory[validHistory.length - 1].role === 'user') {
    // 如果历史以user消息结尾，添加一个空的assistant回复
    validHistory.push({
      role: 'assistant',
      content: '我明白了，请继续。'
    });
  }
  
  // 添加当前用户消息
  validHistory.push({ role: 'user', content: currentMessage });
  
  // 如果总消息超过10条，只保留最近的对话
  if (validHistory.length > 10) {
    // 确保保留偶数条消息，维持user-assistant对话格式
    const startIndex = validHistory.length % 2 === 0 ? 
                       validHistory.length - 10 : 
                       validHistory.length - 9;
    return validHistory.slice(startIndex);
  }
  
  return validHistory;
}

/**
 * POST /api/chat
 * 处理常规聊天请求
 */
router.post('/', (req, res) => {
  const { message } = req.body;
  
  // 简单回复示例
  res.json({
    response: `您发送的消息是: ${message}`,
    timestamp: new Date().toISOString()
  });
});

/**
 * POST /api/chat/stream
 * 处理流式聊天请求
 */
router.post('/stream', async (req, res) => {
  const { message, history = [] } = req.body;
  
  if (!message) {
    return res.status(400).json({
      status: 'error',
      message: '消息不能为空'
    });
  }
  
  // 设置响应头，支持流式传输
  res.setHeader('Content-Type', 'application/octet-stream');
  res.setHeader('Transfer-Encoding', 'chunked');
  
  // 处理消息历史，确保符合deepseek-reasoner的要求
  const formattedMessages = processMessageHistory(history, message);
  
  // 创建可读流
  const stream = new Readable({
    read() {}
  });
  
  // 将流连接到响应
  stream.pipe(res);
  
  // 开始思考流程
  stream.push(JSON.stringify({
    type: 'thinking',
    data: '正在分析您的问题...\n'
  }) + '\n');
  
  try {
    // 调用Deepseek API
    const deepseekResponse = await axios.post(
      DEEPSEEK_API_URL,
      {
        model: 'deepseek-reasoner',
        messages: formattedMessages,
        temperature: 0.7,
        max_tokens: 2000,
        stream: false // 我们在这里处理自己的流逻辑
      },
      {
        headers: {
          'Authorization': `Bearer ${DEEPSEEK_API_KEY}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    // 收到模型回复
    if (deepseekResponse.data && deepseekResponse.data.choices && deepseekResponse.data.choices.length > 0) {
      const assistantResponse = deepseekResponse.data.choices[0].message.content;
      
      // 发送思考内容（可以是模型的中间推理步骤，这里简化处理）
      stream.push(JSON.stringify({
        type: 'thinking',
        data: '分析完成，准备回复...\n'
      }) + '\n');
      
      // 短暂延迟后发送最终回复
      setTimeout(() => {
        stream.push(JSON.stringify({
          type: 'content',
          data: assistantResponse
        }) + '\n');
        
        // 结束流
        stream.push(null);
      }, 500);
    } else {
      throw new Error('API返回数据格式错误');
    }
  } catch (error) {
    console.error('API错误:', error);
    
    // 发送错误信息
    let errorMessage = '处理请求时发生错误';
    
    if (error.response && error.response.data && error.response.data.error) {
      errorMessage = `API错误: ${error.response.data.error.message || error.response.data.error}`;
      console.error('详细错误:', JSON.stringify(error.response.data));
    } else if (error.message) {
      errorMessage = `错误: ${error.message}`;
    }
    
    stream.push(JSON.stringify({
      type: 'thinking',
      data: `发生错误: ${errorMessage}\n`
    }) + '\n');
    
    stream.push(JSON.stringify({
      type: 'content',
      data: `很抱歉，我无法处理您的请求。${errorMessage}`
    }) + '\n');
    
    // 结束流
    stream.push(null);
  }
});

/**
 * 使用模拟回复的简化版本（用于测试）
 */
router.post('/mock', (req, res) => {
  const { message } = req.body;
  
  // 设置响应头，支持流式传输
  res.setHeader('Content-Type', 'application/octet-stream');
  res.setHeader('Transfer-Encoding', 'chunked');
  
  // 创建可读流
  const stream = new Readable({
    read() {}
  });
  
  // 将流连接到响应
  stream.pipe(res);
  
  // 模拟思考过程
  setTimeout(() => {
    stream.push(JSON.stringify({
      type: 'thinking',
      data: '正在思考您的问题...\n'
    }) + '\n');
    
    setTimeout(() => {
      stream.push(JSON.stringify({
        type: 'thinking',
        data: '分析中...\n'
      }) + '\n');
      
      setTimeout(() => {
        stream.push(JSON.stringify({
          type: 'content',
          data: `这是对"${message}"的模拟回复。实际应用中，这里会返回AI生成的内容。`
        }) + '\n');
        
        // 结束流
        stream.push(null);
      }, 1000);
    }, 800);
  }, 500);
});

module.exports = router; 