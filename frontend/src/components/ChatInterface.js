import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import Header from './Header';

const ChatContainer = styled.div`
  display: flex;
  flex-direction: column;
  flex: 1;
  height: calc(100vh - 60px);
  overflow: hidden;
`;

// 本地存储键名
const STORAGE_KEY = 'ai_chat_history';

const ChatInterface = ({ assistantName = 'AI聊天助手' }) => {
  // 从本地存储加载历史消息
  const loadHistoryFromStorage = () => {
    try {
      const savedHistory = localStorage.getItem(STORAGE_KEY);
      if (savedHistory) {
        return JSON.parse(savedHistory);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
    return [];
  };

  const [messages, setMessages] = useState(loadHistoryFromStorage);
  const [thinking, setThinking] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef(null);
  const messagesEndRef = useRef(null);
  
  // 在思考状态改变时，确保自动滚动到底部
  useEffect(() => {
    if (isThinking) {
      scrollToBottom();
    }
  }, [isThinking, thinking]);
  
  // 当消息更新时保存到本地存储
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
      // 触发自定义事件，通知历史记录组件更新
      window.dispatchEvent(new Event('chatHistoryUpdated'));
    } catch (error) {
      console.error('Error saving chat history:', error);
    }
  }, [messages]);
  
  // 自动滚动到底部，但允许用户中断
  const scrollToBottom = () => {
    if (autoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, thinking, autoScroll]);

  // 当用户手动滚动时，检测并控制自动滚动行为
  useEffect(() => {
    const container = scrollRef.current;
    
    if (!container) return;
    
    const handleScroll = () => {
      // 计算是否接近底部 (100px 的容差)
      const isNearBottom = 
        container.scrollHeight - container.scrollTop - container.clientHeight < 100;
      
      // 只有当用户滚动到接近底部时，才启用自动滚动
      setAutoScroll(isNearBottom);
    };
    
    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  // 清除历史记录功能
  const clearHistory = () => {
    try {
      localStorage.removeItem(STORAGE_KEY);
      setMessages([]);
      setThinking('');
      setIsThinking(false);
      // 触发自定义事件，通知历史记录组件更新
      window.dispatchEvent(new Event('chatHistoryUpdated'));
      // 重新启用自动滚动
      setAutoScroll(true);
    } catch (error) {
      console.error('Error clearing chat history:', error);
    }
  };

  const handleSendMessage = async (messageText, knowledgeBaseIds = [], mcpServerIds = []) => {
    if (!messageText.trim()) return;
    
    // 添加用户消息，包含知识库和MCP服务器信息
    const userMessage = { 
      role: 'user', 
      content: messageText, 
      timestamp: new Date().toISOString(),
      // 保存使用的知识库和服务器IDs，方便展示
      knowledgeBaseIds: knowledgeBaseIds.length > 0 ? knowledgeBaseIds : [],
      mcpServerIds: mcpServerIds.length > 0 ? mcpServerIds : []
    };
    setMessages(prev => [...prev, userMessage]);
    
    // 获取历史记录(不包括当前用户消息)
    let history = messages.filter(msg => msg.role === 'user' || msg.role === 'assistant');
    
    // 确保消息历史的格式符合要求：user和assistant交替出现
    if (history.length > 0) {
      const validHistory = [];
      let lastRole = null;
      
      for (const msg of history) {
        if (msg.role === lastRole) {
          // 如果连续出现相同角色的消息，合并它们
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
      
      history = validHistory;
    }
    
    setIsLoading(true);
    setThinking(''); // 清空思考内容
    setIsThinking(true); // 开始思考
    
    let toolCallsCollected = []; // 收集工具调用
    
    try {
      // API端点 (根据需要更新)
      const API_URL = 'http://localhost:8000/api/chat/stream';
      
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: messageText,
          history: history,
          knowledge_base_ids: knowledgeBaseIds, // 添加知识库IDs参数
          mcp_server_ids: mcpServerIds, // 添加MCP服务器IDs参数
          use_tools: mcpServerIds.length > 0 // 如果有MCP服务器，则启用工具
        }),
      });
      
      if (!response.ok) {
        throw new Error(`API错误: ${response.status}`);
      }
      
      // 处理流式响应
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      let assistantResponseText = '';
      let collectingThinking = true; // 标记是否处于思考阶段
      let thinkingContent = ''; // 保存完整的思考内容
      let lastChunkTime = Date.now(); // 记录最后收到数据的时间
      let hasReceivedContent = false; // 标记是否已收到实际内容（非思考）
      
      const updateMessage = () => {
        setMessages(prev => {
          const lastMessage = prev[prev.length - 1];
          if (lastMessage && lastMessage.role === 'assistant') {
            // 更新现有回复
            const newMessages = [...prev];
            newMessages[newMessages.length - 1] = { 
              role: 'assistant', 
              content: assistantResponseText,
              thinking: thinkingContent, // 保存关联的思考内容
              timestamp: new Date().toISOString(),
              // 保存使用的知识库和服务器IDs
              knowledgeBaseIds: userMessage.knowledgeBaseIds,
              mcpServerIds: userMessage.mcpServerIds,
              // 保存工具调用
              toolCalls: toolCallsCollected
            };
            return newMessages;
          } else {
            // 创建新回复
            return [...prev, { 
              role: 'assistant', 
              content: assistantResponseText,
              thinking: thinkingContent, // 保存关联的思考内容
              timestamp: new Date().toISOString(),
              // 保存使用的知识库和服务器IDs
              knowledgeBaseIds: userMessage.knowledgeBaseIds,
              mcpServerIds: userMessage.mcpServerIds,
              // 保存工具调用
              toolCalls: toolCallsCollected
            }];
          }
        });
      };
      
      // 心跳检查，确保长时间无数据时仍然显示思考状态
      const heartbeatInterval = setInterval(() => {
        const now = Date.now();
        // 如果超过3秒没有收到新数据，且仍在思考状态
        if (now - lastChunkTime > 3000 && isThinking && !hasReceivedContent) {
          // 确保思考状态保持显示
          setThinking(thinkingContent || ' '); // 使用空格确保有内容
        }
      }, 3000);
      
      while (true) {
        const { value, done } = await reader.read();
        
        if (done) break;
        
        lastChunkTime = Date.now(); // 更新最后收到数据的时间
        const chunkText = decoder.decode(value);
        
        try {
          // 尝试解析JSON
          const lines = chunkText.split('\n').filter(line => line.trim());
         
          for (const line of lines) {
            try {
              console.log(line);
              const chunkData = JSON.parse(line);
              
              if (chunkData.type === 'reasoning' || chunkData.type === 'thinking') {
                // 收集思考内容
                thinkingContent += chunkData.data;
                setThinking(thinkingContent);
                setIsThinking(true); // 确保思考标志始终为true
                collectingThinking = true;
              } else if (chunkData.type === 'content' || chunkData.type === 'reference') {
                // 当收到第一个内容块时
                hasReceivedContent = true;
                if (collectingThinking) {
                  collectingThinking = false; // 思考阶段结束
                  setIsThinking(false); // 思考结束
                }
                
                // 直接添加内容到响应文本
                assistantResponseText += chunkData.data;
                updateMessage();
              } else if (chunkData.type === 'tool_call') {
                // 处理工具调用
                const toolCallData = chunkData.data;
                
                // 收集工具调用数据
                const toolEventData = {
                  name: toolCallData.name,
                  arguments: toolCallData.arguments,
                  timestamp: new Date().toISOString()
                };
                
                // 如果包含结果，也添加进来
                if (toolCallData.result) {
                  toolEventData.result = toolCallData.result;
                }
                
                // 如果有错误信息，添加错误
                if (toolCallData.error) {
                  toolEventData.error = toolCallData.error;
                }
                
                // 添加到工具调用集合
                toolCallsCollected.push(toolEventData);
                
                // 将工具调用以JSON格式添加到内容流中，以便在界面上显示
                assistantResponseText += `\`\`\`json\n${JSON.stringify(toolCallData, null, 2)}\n\`\`\`\n\n`;
                
                // 更新消息
                updateMessage();
              } else if (chunkData.type === 'tool_result') {
                // 工具结果处理
                let resultData;
                
                if (typeof chunkData.data === 'string') {
                  try {
                    resultData = JSON.parse(chunkData.data);
                  } catch (e) {
                    resultData = chunkData.data;
                  }
                } else {
                  resultData = chunkData.data;
                }
                
                // 更新最后一个工具调用的结果
                if (toolCallsCollected.length > 0) {
                  const lastToolCall = toolCallsCollected[toolCallsCollected.length - 1];
                  
                  if (!lastToolCall.result) {
                    lastToolCall.result = resultData;
                    
                    if (resultData && resultData.isError) {
                      lastToolCall.error = resultData.message || '未知错误';
                    }
                    
                    // 输出工具结果
                    assistantResponseText += `\`\`\`json\n${JSON.stringify(resultData, null, 2)}\n\`\`\`\n\n`;
                    updateMessage();
                  }
                }
              } else {
                // 处理其他类型内容
                assistantResponseText += chunkData.data;
                updateMessage();
              }
            } catch (parseError) {
              console.warn("无法解析JSON行:", line);
            }
          }
        } catch (e) {
          // 非JSON或解析错误，处理为普通内容
          console.warn("处理数据时出错:", e.message);
          
          // 如果还在思考阶段，标记思考结束
          if (collectingThinking) {
            collectingThinking = false;
            setIsThinking(false);
          }
          
          // 添加到响应文本
          assistantResponseText += chunkText;
          updateMessage();
        }
      }
      
      // 流处理完成，确保思考状态已关闭
      setIsThinking(false);
      clearInterval(heartbeatInterval); // 清理心跳检查
      
    } catch (error) {
      console.error('错误:', error);
      setIsThinking(false);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `发生错误: ${error.message}`, 
        isError: true,
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ChatContainer>
      <Header title={assistantName} />
      <ChatMessages 
        messages={messages} 
        thinking={thinking}
        isThinking={isThinking}
        scrollRef={scrollRef}
        messagesEndRef={messagesEndRef}
      />
      <ChatInput 
        onSendMessage={handleSendMessage} 
        disabled={isLoading}
        onClearHistory={clearHistory}
        hasMessages={messages.length > 0}
      />
    </ChatContainer>
  );
};

export default ChatInterface; 