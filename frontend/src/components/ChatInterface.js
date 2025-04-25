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

  const handleSendMessage = async (messageText, knowledgeBaseIds = []) => {
    if (!messageText.trim()) return;
    
    // 添加用户消息，包含知识库信息
    const userMessage = { 
      role: 'user', 
      content: messageText, 
      timestamp: new Date().toISOString(),
      // 保存使用的知识库IDs，方便展示
      knowledgeBaseIds: knowledgeBaseIds.length > 0 ? knowledgeBaseIds : undefined
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
          knowledge_base_ids: knowledgeBaseIds // 添加知识库IDs参数
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
      
      const updateMessage = (isNewMessage) => {
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
              // 保存使用的知识库IDs
              knowledgeBaseIds: userMessage.knowledgeBaseIds
            };
            return newMessages;
          } else {
            // 创建新回复
            return [...prev, { 
              role: 'assistant', 
              content: assistantResponseText,
              thinking: thinkingContent, // 保存关联的思考内容
              timestamp: new Date().toISOString(),
              // 保存使用的知识库IDs
              knowledgeBaseIds: userMessage.knowledgeBaseIds
            }];
          }
        });
      };
      
      while (true) {
        const { value, done } = await reader.read();
        
        if (done) break;
        
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
              } else if (chunkData.type === 'content') {
                // 当收到第一个内容块时
                if (collectingThinking) {
                  collectingThinking = false; // 思考阶段结束
                  setIsThinking(false); // 思考结束
                }
                
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
          
          assistantResponseText += chunkText;
          updateMessage();
        }
      }
      
      // 流处理完成，确保思考状态已关闭
      setIsThinking(false);
      
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