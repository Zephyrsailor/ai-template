import React, { useState, useRef, useEffect } from 'react';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import Header from './Header';
import Sidebar from './Sidebar';
import MessageBubble from './MessageBubble';
import ThinkingBubble from './ThinkingBubble';
import ToolCallDisplay from './ToolCallDisplay'; // Import ToolCallDisplay
// import AssistantMessage from './AssistantMessage'; // 暂时移除，恢复简单显示
import { CgSpinner } from 'react-icons/cg';
import { FiUser } from 'react-icons/fi';
import { RiRobot2Line } from 'react-icons/ri';
import axios from 'axios';
// 导入API函数
import { fetchConversations, createConversation, deleteConversation, getConversationDetails, fetchDefaultLLMConfig } from '../api';

// 过滤标准消息对象，确保 role 和 content 的有效性
const filterValidMessages = arr => (arr || []).filter(m =>
  m &&
  typeof m === 'object' &&
  ('role' in m) && (m.role === 'user' || m.role === 'assistant') &&
  ('content' in m) && typeof m.content === 'string'
);

const WELCOME_MESSAGE = {
  id: 'welcome',
  content: '你好！我是AI助手，有什么我可以帮助你的？',
  role: 'assistant',
  createdAt: new Date().toISOString(),
  type: 'content', // Add type for welcome message
  messageId: 'welcome' // Add messageId for welcome message
};

const ChatInterface = ({
  messages = [],
  onMessagesChange,
  assistantName = 'AI Assistant',
  useSystemMessage = false,
  systemMessage = '',
  autoFocusInput = false,
  onOpenSettings,
  isThinking: externalIsThinking,
  selectedModel: externalSelectedModel,
  onModelChange: externalOnModelChange
}) => {
  const [conversations, setConversations] = useState([
    { id: 'default', title: '', messages: [WELCOME_MESSAGE], isNew: true }
  ]);
  const [isThinking, setIsThinking] = useState(externalIsThinking || false);
  const [thinking, setThinking] = useState('');
  const [completedThinking, setCompletedThinking] = useState(null); // 存储已完成的思考内容
  const [activeConversationId, setActiveConversationId] = useState('default');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false); // 是否正在流式响应
  const [currentReader, setCurrentReader] = useState(null); // 当前的流式读取器
  const [abortController, setAbortController] = useState(null); // 用于取消请求的控制器
  const [selectedModel, setSelectedModel] = useState(externalSelectedModel || null); // 选中的模型
  const messagesEndRef = useRef(null);

  // Get active conversation
  const activeConversation = conversations.find(c => c.id === activeConversationId) || conversations[0];
  messages = activeConversation?.messages || [];

  // 将消息分组，将连续的助手消息（thinking、tool_call、content）组合在一起
  // 移除复杂的消息分组逻辑，直接使用消息数组

  // Scroll to bottom when messages change - 优化为更频繁的滚动
  useEffect(() => {
    if (messagesEndRef.current) {
      // 在流式响应期间更频繁地滚动
      if (isStreaming || isThinking) {
        messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
      } else if (messages.length > 0) {
        // 非流式状态下的正常滚动
        const lastMsg = messages[messages.length - 1];
        if (lastMsg && lastMsg.role === 'assistant') {
          messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
      }
    }
  }, [messages, isStreaming, isThinking, thinking]);

  // 使用外部传入的isThinking状态更新内部状态
  useEffect(() => {
    if (typeof externalIsThinking !== 'undefined') {
      setIsThinking(externalIsThinking);
    }
  }, [externalIsThinking]);

  // 同步外部传入的selectedModel状态
  useEffect(() => {
    if (externalSelectedModel !== undefined) {
      setSelectedModel(externalSelectedModel);
    }
  }, [externalSelectedModel]);

  // 初始化默认模型
  useEffect(() => {
    const initializeDefaultModel = async () => {
      if (!selectedModel) {
        try {
          const token = localStorage.getItem('authToken');
          if (token) {
            // 尝试获取用户的默认配置
            const defaultConfig = await fetchDefaultLLMConfig();

            if (defaultConfig && defaultConfig.model_name) {
              console.log('ChatInterface - 设置用户默认模型:', defaultConfig.model_name);
              setSelectedModel(defaultConfig.model_name);
              // 同时调用外部的onModelChange
              if (externalOnModelChange) {
                externalOnModelChange(defaultConfig.model_name);
              }
              return;
            }
          }
          
          // 如果没有用户默认配置，不设置任何默认值
          // 让EnhancedLLMSelector组件来处理默认模型选择
          console.log('ChatInterface - 没有找到用户默认配置，等待LLMSelector自动选择');
        } catch (error) {
          console.error('初始化默认模型失败:', error);
          // 出错时也不设置默认值，让LLMSelector处理
        }
      }
    };

    initializeDefaultModel();
  }, [selectedModel, externalOnModelChange]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // 停止聊天生成
  const handleStopGeneration = async () => {
    try {
      console.log('开始停止聊天生成...');
      
      // 1. 立即取消网络请求（如果还在进行中）
      if (abortController) {
        console.log('取消网络请求...');
        abortController.abort();
        setAbortController(null);
      }

      // 2. 停止流式读取（如果已经开始）
      if (currentReader) {
        console.log('取消流式读取...');
        await currentReader.cancel();
        setCurrentReader(null);
      }

      // 3. 调用后端停止API，让后端处理状态保存
      const currentConversation = conversations.find(c => c.id === activeConversationId);
      const conversationId = currentConversation?.serverId;
      
      if (conversationId) {
        // 调用后端停止API（异步进行，不等待结果）
        axios.post(`/api/chat/stop?conversation_id=${conversationId}`)
          .then(() => {
            console.log('后端停止API调用成功');
          })
          .catch(error => {
            console.warn('后端停止API调用失败:', error);
          });
      }

      // 4. 立即重置流式状态，但保留已显示的消息
      setIsStreaming(false);
      setIsLoading(false);
      setIsThinking(false);
      setThinking('');
      
      // 5. 如果有未完成的thinking，标记为已完成
      setConversations(prev =>
        prev.map(conv => {
          if (conv.id === activeConversationId) {
            const updatedMessages = conv.messages.map(msg => {
              if (msg.type === 'thinking' && !msg.isCompleted) {
                return { ...msg, isCompleted: true };
              }
              return msg;
            });
            return { ...conv, messages: updatedMessages };
          }
          return conv;
        })
      );
      
      console.log('聊天生成已停止');
    } catch (error) {
      console.error('停止聊天失败:', error);
      // 即使出错也要重置状态
      setIsStreaming(false);
      setIsLoading(false);
      setIsThinking(false);
      setThinking('');
      setAbortController(null);
      setCurrentReader(null);
    }
  };

  const handleSendMessage = async (messageText, options = {}) => {
    // 解构选项获取知识库和MCP服务器ID以及网页搜索选项
    const { knowledgeBaseIds = [], mcpServerIds = [], useWebSearch = false, modelId = null } = options;

    if (!messageText.trim()) return;

    // 调试信息：确认模型ID
    const finalModelId = modelId || selectedModel;
    console.log('ChatInterface - handleSendMessage:');
    console.log('  options.modelId:', modelId);
    console.log('  selectedModel:', selectedModel);
    console.log('  finalModelId:', finalModelId);

    // 重置思考相关状态
    setCompletedThinking(null);

    // 构建用户消息对象
    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: messageText,
      createdAt: new Date().toISOString(),
      type: 'content', // Add type for user message
      // 保存使用的知识库和服务器IDs，方便展示
      knowledgeBaseIds: knowledgeBaseIds.length > 0 ? knowledgeBaseIds : [],
      mcpServerIds: mcpServerIds.length > 0 ? mcpServerIds : [],
      useWebSearch: useWebSearch,
      messageId: `user-${Date.now()}` // 用户消息独立的messageId
    };
    
    // 为这一轮AI回答生成统一的messageId
    const streamMessageId = `stream-${Date.now()}`;

    // 更新对话中的消息
    updateConversation(activeConversationId, userMessage);
    
    // 立即显示一个"正在思考"的助手消息框，提升用户体验
    const loadingMessageId = `loading-${Date.now()}`;
    updateConversation(activeConversationId, {
      id: loadingMessageId,
      role: 'assistant',
      content: '',
      createdAt: new Date().toISOString(),
      type: 'loading', // 特殊类型，表示正在加载
      isLoading: true,
      messageId: streamMessageId // 使用统一的messageId
    });

    // 获取历史记录(不包括当前用户消息)
    let history = messages.filter(msg => msg.role === 'user' || msg.role === 'assistant')
      .map(msg => ({ role: msg.role, content: msg.content }));

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

      // 确保第一条消息是用户消息，如果是助手消息则删除
      // DeepSeek模型要求第一条必须是用户消息
      if (history.length > 0 && history[0].role === 'assistant') {
        history.shift();
      }
    }

    setIsLoading(true);
    setIsStreaming(true); // 开始流式响应
    setThinking(''); // 清空思考内容
    setIsThinking(false); // 先不设置思考状态，等收到thinking数据再设置

    let currentMessageId = null;
    let currentMessageType = null;
    let hasReceivedResponse = false; // 跟踪是否收到任何响应
    let receivedOrderCounter = 0; // 接收顺序计数器
    
    // 立即滚动到底部，准备显示新内容
    setTimeout(() => scrollToBottom(), 100);

    // 创建AbortController用于取消请求
    const controller = new AbortController();
    setAbortController(controller);

    try {
      // API端点
      const currentConversation = conversations.find(c => c.id === activeConversationId);
      const conversationId = currentConversation?.serverId;
      
      const response = await fetch('http://localhost:8000/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('authToken') || ''}`,
        },
        signal: controller.signal, // 添加取消信号
        body: JSON.stringify({
          message: messageText,
          history: history,
          knowledge_base_ids: knowledgeBaseIds,
          mcp_server_ids: mcpServerIds,
          use_tools: mcpServerIds.length > 0,
          use_web_search: useWebSearch,
          model_id: finalModelId, // 使用确定的模型ID
          conversation_id: conversationId,
          conversation_title:
            currentConversation?.title ||
            (messageText.length > 20 ? messageText.substring(0, 20) + '...' : messageText)
        }),
      });
      if (!response.ok) {
        throw new Error(`API错误: ${response.status}`);
      }

      // 处理流式响应
      const reader = response.body.getReader();
      setCurrentReader(reader); // 保存reader引用以便停止
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunkText = decoder.decode(value);
        try {
          const lines = chunkText.split('\n').filter(line => line.trim());
          for (const line of lines) {
            try {
              const chunkData = JSON.parse(line);
              const type = chunkData.type;
              
              // 处理会话创建事件
              if (type === 'conversation_created') {
                // 更新当前会话的serverId和id
                const newConversationId = chunkData.data;
                console.log('服务器创建了新会话，ID:', newConversationId);
                
                // 更新会话ID和serverId
                setConversations(prev =>
                  prev.map(conv => {
                    if (conv.id === activeConversationId) {
                      return { 
                        ...conv, 
                        id: newConversationId,  // 更新本地ID
                        serverId: newConversationId  // 更新服务器ID
                      };
                    }
                    return conv;
                  })
                );
                
                // 更新当前活跃会话ID
                setActiveConversationId(newConversationId);
                
                // 保存更新后的会话
                saveConversationAfterCreation(newConversationId, newConversationId);
                continue;
              }
              
              // 如果 type 从 thinking 切换到其他，立即将前一个 thinking 设为 isCompleted
              if ((currentMessageType === 'thinking' || currentMessageType === 'reasoning') && type !== currentMessageType) {
                if (currentMessageId) {
                  setConversations(prev =>
                    prev.map(conv => {
                      if (conv.id === activeConversationId) {
                        const updatedMessages = conv.messages.map(msg => {
                          if (msg.id === currentMessageId && msg.type === 'thinking') {
                            return { ...msg, isCompleted: true };
                          }
                          return msg;
                        });
                        return { ...conv, messages: updatedMessages };
                      }
                      return conv;
                    })
                  );
                }
              }
              // 处理错误事件
              if (type === 'error') {
                const errorMessage = {
                  id: `error-${Date.now()}`,
                  role: 'assistant',
                  content: `发生错误: ${chunkData.data.error || '未知错误'}`,
                  isError: true,
                  createdAt: new Date().toISOString(),
                  type: 'content'
                };
                updateConversation(activeConversationId, errorMessage);
                continue;
              }

              // 标记已收到响应
              if (!hasReceivedResponse) {
                hasReceivedResponse = true;
                setIsLoading(false); // 收到第一个响应后立即取消loading状态
                
                // 移除loading消息
                setConversations(prev =>
                  prev.map(conv => {
                    if (conv.id === activeConversationId) {
                      const updatedMessages = conv.messages.filter(msg => msg.type !== 'loading');
                      return { ...conv, messages: updatedMessages };
                    }
                    return conv;
                  })
                );
              }

              // 判断是否需要新建消息块
              if (type !== currentMessageType) {
                // 新建消息块
                currentMessageId = `${type}-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
                currentMessageType = type;
                
                if (type === 'thinking' || type === 'reasoning') {
                  receivedOrderCounter++; // 增加接收顺序
                  updateConversation(activeConversationId, {
                    id: currentMessageId,
                    role: 'assistant',
                    thinking: chunkData.data || "",
                    createdAt: new Date().toISOString(),
                    type: 'thinking',
                    isCompleted: false,
                    messageId: streamMessageId // 使用统一的messageId
                  });
                  setThinking(chunkData.data || "");
                  setIsThinking(true);
                } else if (type === 'tool_call') {
                  console.log("tool_call", chunkData.data)
                  let tools = JSON.parse(chunkData.data)  
                  tools.forEach((tool, index) => {
                    receivedOrderCounter++; // 每个工具调用都增加接收顺序
                    updateConversation(activeConversationId, {
                      id: tool.id,
                      role: 'assistant',
                      toolCallId: tool.id,
                      name: tool.name || tool.tool_name,
                      arguments: tool.arguments || {},
                      createdAt: new Date().toISOString(),
                      type: 'tool_call',
                      messageId: streamMessageId // 使用统一的messageId
                    });
                  });
                } else if (type === 'tool_result') {
                  console.log("tool_result", chunkData.data)
                  console.log("typeof", typeof chunkData.data)
                  let toolResult = chunkData.data
                  // 只更新，不新增
                  setConversations(prev =>
                    prev.map(conv => {
                      if (conv.id === activeConversationId) {
                        const updatedMessages = conv.messages.map(msg => {
                          if (msg.id === toolResult.id && msg.type === 'tool_call') {
                            return { ...msg, result: toolResult.result, error: toolResult.error };
                          }
                          return msg;
                        });
                        return { ...conv, messages: updatedMessages };
                      }
                      return conv;
                    })
                  );
                } else if (type === 'content') {
                  receivedOrderCounter++; // 增加接收顺序
                  updateConversation(activeConversationId, {
                    id: currentMessageId,
                    role: 'assistant',
                    content: chunkData.data || "",
                    createdAt: new Date().toISOString(),
                    type: 'content',
                    knowledgeBaseIds: userMessage.knowledgeBaseIds,
                    mcpServerIds: userMessage.mcpServerIds,
                    useWebSearch: userMessage.useWebSearch,
                    messageId: streamMessageId // 使用统一的messageId
                  });
                } else if (type === 'reference') {
                  receivedOrderCounter++; // 增加接收顺序
                  updateConversation(activeConversationId, {
                    id: `reference-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
                    role: 'assistant',
                    content: chunkData.data || "",
                    createdAt: new Date().toISOString(),
                    type: 'reference',
                    messageId: streamMessageId // 使用统一的messageId
                  });
                }
              } else {
                // 合并到当前消息块
                if (type === 'thinking' || type === 'reasoning') {
                  updateConversationThinking(activeConversationId, currentMessageId, chunkData.data || "", true);
                  setThinking(prev => prev + (chunkData.data || ""));
                } else if (type === 'content') {
                  updateConversationContent(activeConversationId, currentMessageId, chunkData.data || "", true);
                } else if (type === 'tool_call') {
                  // 工具调用一般不会流式追加，但保留接口
                } else if (type === 'tool_result') {
                  // 工具结果一般不会流式追加，但保留接口
                   // 只更新，不新增
                   let toolResult = chunkData.data
                   setConversations(prev =>
                    prev.map(conv => {
                      if (conv.id === activeConversationId) {
                        const updatedMessages = conv.messages.map(msg => {
                          if (msg.id === toolResult.id && msg.type === 'tool_call') {
                            return { ...msg, result: toolResult.result, error: toolResult.error };
                          }
                          return msg;
                        });
                        return { ...conv, messages: updatedMessages };
                      }
                      return conv;
                    })
                  );
                }
              }
            } catch (e) {
              console.warn("Error processing data chunk:", e.message);
            }
          }
        } catch (e) {
          console.warn("Error processing chunk:", e.message);
        }
      }

      setIsThinking(false);
      // 流式结束后，强制将最后一个thinking设为isCompleted
      if ((currentMessageType === 'thinking' || currentMessageType === 'reasoning') && currentMessageId) {
        setConversations(prev =>
          prev.map(conv => {
            if (conv.id === activeConversationId) {
              const updatedMessages = conv.messages.map(msg => {
                if (msg.id === currentMessageId && msg.type === 'thinking') {
                  return { ...msg, isCompleted: true };
                }
                return msg;
              });
              return { ...conv, messages: updatedMessages };
            }
            return conv;
          })
        );
        setCompletedThinking(thinking);
      }

    } catch (error) {
      console.error('Error:', error);
      setIsThinking(false);

      // 移除loading消息
      setConversations(prev =>
        prev.map(conv => {
          if (conv.id === activeConversationId) {
            const updatedMessages = conv.messages.filter(msg => msg.type !== 'loading');
            return { ...conv, messages: updatedMessages };
          }
          return conv;
        })
      );

      // 如果是用户主动取消的请求，不显示错误消息
      if (error.name === 'AbortError') {
        console.log('请求被用户取消');
        return;
      }

      if (currentMessageType === 'thinking' && currentMessageId) {
         setConversations(prev =>
           prev.map(conv => {
             if (conv.id === activeConversationId) {
               const updatedMessages = conv.messages.map(msg => {
                 if (msg.id === currentMessageId && msg.type === 'thinking') {
                   return { ...msg, isCompleted: true };
                 }
                 return msg;
               });
               return { ...conv, messages: updatedMessages };
             }
             return conv;
           })
         );
         setCompletedThinking(thinking);
      }

      // Create error message as a new content entry
      const errorMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: `发生错误: ${error.message}`,
        isError: true,
        createdAt: new Date().toISOString(),
        type: 'content' // Error messages are content
      };

      updateConversation(activeConversationId, errorMessage);
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
      setCurrentReader(null);
      setAbortController(null);
      setIsThinking(false);
      
      // 流式响应结束后同步对话历史，确保前端状态与后端一致
      const currentConv = conversations.find(c => c.id === activeConversationId);
      if (currentConv?.serverId) {
        // 延迟一下再同步，确保后端已经完全保存
        setTimeout(() => {
          syncConversationHistory(activeConversationId);
        }, 1000);
      }
    }
  };

  const updateConversation = (conversationId, message) => {
    setConversations(prev =>
      prev.map(conv => {
        if (conv.id === conversationId) {
          const updatedMessages = [...conv.messages, message];
          // For the first user message, set the conversation title based on the message content and remove the isNew flag
          if (conv.isNew && message.role === 'user' && message.type === 'content') {
            const newTitle = message.content.length > 30 ?
              message.content.substring(0, 30) + '...' :
              message.content;

            return {
              ...conv,
              messages: updatedMessages,
              title: newTitle,
              isNew: false
            };
          }
          return { ...conv, messages: updatedMessages };
        }
        return conv;
      })
    );
  };

  // 更新指定思考消息的内容
  const updateConversationThinking = (conversationId, messageId, newThinking, append = true) => {
    setConversations(prev =>
      prev.map(conv => {
        if (conv.id === conversationId) {
          const updatedMessages = conv.messages.map(msg => {
            if (msg.id === messageId && msg.type === 'thinking') {
              return { ...msg, thinking: append ? msg.thinking + newThinking : newThinking };
            }
            return msg;
          });
          return { ...conv, messages: updatedMessages };
        }
        return conv;
      })
    );
  };

  const updateConversationContent = (conversationId, messageId, newContent, append = true) => {
    setConversations(prev =>
      prev.map(conv => {
        if (conv.id === conversationId) {
          const updatedMessages = conv.messages.map(msg => {
            if (msg.id === messageId && msg.type === 'content') {
              return { ...msg, content: append ? msg.content + newContent : newContent };
            }
            return msg;
          });
          return { ...conv, messages: updatedMessages };
        }
        return conv;
      })
    );
  };

  const handleNewChat = () => {
    const unusedChat = conversations.find(
      conv => conv.isNew && conv.messages.length === 1 && conv.messages[0].role === 'assistant'
    );

    if (unusedChat) {
      setActiveConversationId(unusedChat.id);
    } else {
      const newId = `conv-${Date.now()}`;
      setConversations(prev => [
        {
          id: newId,
          title: '',
          messages: [WELCOME_MESSAGE],
          isNew: true
        },
        ...prev
      ]);
      setActiveConversationId(newId);
    }
  };

  const saveCurrentConversation = async (conversationId) => {
    try {
      const currentConv = conversations.find(c => c.id === conversationId);
      if (!currentConv) return;

      const firstUserMessage = currentConv.messages.find(msg => msg.role === 'user' && msg.type === 'content');
      const titleFromMessage = firstUserMessage ?
        (firstUserMessage.content.length > 30 ?
          firstUserMessage.content.substring(0, 30) + '...' :
          firstUserMessage.content) :
        null;

      if (!currentConv.serverId) {
        const response = await createConversation({
          title: titleFromMessage || currentConv.title || "New Conversation",
          metadata: {
            clientId: currentConv.id,
            isNew: false
          }
        });

        if (response.data && response.data.id) {
          setConversations(prev =>
            prev.map(conv => {
              if (conv.id === conversationId) {
                return { ...conv, serverId: response.data.id };
              }
              return conv;
            })
          );

          console.log('Conversation saved to server, ID:', response.data.id);
        }
      } else {
        console.log('Conversation already exists on server, ID:', currentConv.serverId);
      }
    } catch (error) {
      console.error('Failed to save conversation:', error);
    }
  };

  // 在会话创建事件处理后保存会话
  const saveConversationAfterCreation = (conversationId, serverId) => {
    try {
      console.log(`保存会话 ${conversationId} 到服务器，服务器ID: ${serverId}`);
      
      // 确保会话ID已同步到状态
      setConversations(prev =>
        prev.map(conv => {
          if (conv.id === conversationId) {
            if (conv.serverId !== serverId) {
              return { ...conv, serverId };
            }
          }
          return conv;
        })
      );
      
      // 延迟同步对话历史，直接传入serverId避免状态更新时序问题
      setTimeout(() => {
        syncConversationHistory(conversationId, serverId);
      }, 1500);
    } catch (error) {
      console.error('Failed to update conversation after creation:', error);
    }
  };

  useEffect(() => {
    const loadConversations = async () => {
      try {
        const response = await fetchConversations();
        console.log("Load conversation response:", response);

        if (response.success && Array.isArray(response.data)) {

          const serverConversations = response.data.map(conv => {
            const convMessages = Array.isArray(conv.messages) ? conv.messages : [];

            return {
              id: `${conv.id}`,
              serverId: conv.id,
              title: conv.title || "新会话",
              messages: convMessages.length > 0
                ? convMessages.flatMap((msg, msgIndex) => {
                    const formattedEntries = [];
                    const baseTimestamp = msg.timestamp || new Date().toISOString();
                    
                    // 简化分组逻辑：每个后端Message使用其ID作为分组依据
                    const messageGroupId = `backend-msg-${msg.id || msgIndex}`;
                    
                    // 1. 添加思考消息（如果存在）
                    if (msg.thinking) {
                      formattedEntries.push({
                        id: `thinking-${msg.id || Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
                        role: 'assistant',
                        thinking: msg.thinking,
                        createdAt: baseTimestamp,
                        type: 'thinking',
                        isCompleted: true,
                        isHistorical: true,
                        messageId: messageGroupId
                      });
                    }
                    
                    // 2. 添加内容消息（如果存在）
                    if (msg.content) {
                      formattedEntries.push({
                        id: `content-${msg.id || Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
                        role: msg.role,
                        content: msg.content,
                        createdAt: baseTimestamp,
                        type: 'content',
                        knowledgeBaseIds: msg.metadata?.knowledge_base_ids || [],
                        mcpServerIds: msg.metadata?.mcp_server_ids || [],
                        useWebSearch: !!msg.metadata?.web_search,
                        isError: msg.isError,
                        isHistorical: true,
                        messageId: messageGroupId
                      });
                    }
                    
                    // 3. 添加工具调用（如果存在）
                    if (Array.isArray(msg.tool_calls)) {
                      msg.tool_calls.forEach((toolCall, index) => {
                        formattedEntries.push({
                          id: toolCall.id || `tool-${msg.id}-${index}-${Math.random().toString(36).substring(2, 9)}`,
                          role: 'assistant',
                          name: toolCall.name || toolCall.tool_name,
                          arguments: toolCall.arguments || {},
                          result: toolCall.result,
                          error: toolCall.error,
                          createdAt: baseTimestamp,
                          type: 'tool_call',
                          isHistorical: true,
                          messageId: messageGroupId
                        });
                      });
                    }
                    
                    return formattedEntries;
                  })
                : [WELCOME_MESSAGE],
              isNew: false
            };
          });

          console.log("Processed conversation data:", serverConversations);
          
          // 调试：打印第一个会话的消息结构
          if (serverConversations.length > 0) {
            console.log("第一个会话的消息结构:", serverConversations[0].messages.map(m => ({
              id: m.id,
              messageId: m.messageId,
              role: m.role,
              type: m.type
            })));
          }

          setConversations(prev => {
            const newLocalConvs = prev.filter(c => c.isNew);
            return [...newLocalConvs, ...serverConversations];
          });

          if (serverConversations.length > 0 && (!activeConversationId || !conversations.some(c => c.id === activeConversationId))) {
            setActiveConversationId(serverConversations[0].id);
          }
        } else {
          console.warn("Failed to load conversations or format is incorrect:", response.message);
        }
      } catch (error) {
        console.error('Failed to load conversation history:', error);
      }
    };

    if (localStorage.getItem('authToken')) {
      loadConversations();
    }
  }, []);

  const handleDeleteConversation = async (conversationId) => {
    const conversation = conversations.find(c => c.id === conversationId);
    if (!conversation) return;

    if (conversation.serverId) {
      try {
        await deleteConversation(conversation.serverId);
        console.log('Deleted conversation from server:', conversation.serverId);
      } catch (error) {
        console.error('Failed to delete conversation from server:', error);
      }
    }

    setConversations(prev => prev.filter(c => c.id !== conversationId));

    if (conversationId === activeConversationId) {
      const remaining = conversations.filter(c => c.id !== conversationId);
      if (remaining.length > 0) {
        setActiveConversationId(remaining[0].id);
      } else {
        handleNewChat();
      }
    }
  };

  // 重新设计消息显示 - 按时间顺序自然显示
  const renderMessage = (message, index, filteredMessages = messages) => {
    if (message.role === 'user') {
      // 用户消息直接渲染
      return (
        <div key={message.messageId || message.id} className="flex items-start gap-3 justify-end mb-6">
          <div className="max-w-2xl order-1">
            <MessageBubble
              content={message.content}
              isUser={true}
              knowledgeBaseIds={message.knowledgeBaseIds}
              mcpServerIds={message.mcpServerIds}
              isError={message.isError}
              useWebSearch={message.useWebSearch}
            />
            <div className="text-xs text-gray-400 mt-1 px-1">
              {new Date(message.createdAt).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
            </div>
          </div>
          <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 order-2">
            <FiUser size={18} className="text-gray-700" />
          </div>
        </div>
      );
    } else if (message.role === 'assistant') {
      // Assistant消息：按messageId分组显示，但保持接收顺序
      const currentGroup = [];
      let startIndex = index;
      
      // 向前查找，找到同一个messageId的开始 - 使用filteredMessages
      while (startIndex > 0 && 
             filteredMessages[startIndex - 1]?.role === 'assistant' && 
             filteredMessages[startIndex - 1]?.messageId === message.messageId) {
        startIndex--;
      }
      
      // 收集同一个messageId的所有消息 - 使用filteredMessages
      let endIndex = startIndex;
      while (endIndex < filteredMessages.length && 
             filteredMessages[endIndex]?.role === 'assistant' && 
             filteredMessages[endIndex]?.messageId === message.messageId) {
        currentGroup.push(filteredMessages[endIndex]);
        endIndex++;
      }
      
      // 只在第一个消息时渲染整个组
      if (index === startIndex) {
        // 按接收时间顺序显示，保持自然的流式响应顺序
        return (
          <div key={`group-${message.messageId || message.id}`} className="flex items-start gap-3 mb-6">
            <div className="w-9 h-9 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
              <RiRobot2Line size={18} className="text-purple-700" />
            </div>
            <div className="max-w-4xl bg-gray-50 rounded-2xl p-4 border border-gray-200">
              {/* 按接收顺序显示同一Message的所有组件 */}
              {currentGroup.map((msg, idx) => (
                <div key={msg.id} className={idx > 0 ? "mt-3" : ""}>
                  {msg.type === 'thinking' && (
                    <ThinkingBubble
                      thinking={msg.thinking}
                      isThinking={!msg.isCompleted}
                      isHistorical={msg.isHistorical}
                      isCompleted={msg.isCompleted}
                      autoCollapse={true}
                      preserveContent={true}
                    />
                  )}
                  {msg.type === 'tool_call' && (
                    <ToolCallDisplay 
                      data={{
                        tool_name: msg.name,
                        arguments: msg.arguments,
                        result: msg.result,
                        error: msg.error
                      }} 
                      isUser={false} 
                      compact={false}
                    />
                  )}
                  {msg.type === 'content' && (
                    <MessageBubble
                      content={msg.content}
                      isUser={false}
                      knowledgeBaseIds={msg.knowledgeBaseIds}
                      mcpServerIds={msg.mcpServerIds}
                      isError={msg.isError}
                      useWebSearch={msg.useWebSearch}
                      compact={true}
                    />
                  )}
                  {msg.type === 'loading' && (
                    <div className="flex items-center gap-2 text-gray-500 text-sm">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                      </div>
                      <span>正在思考...</span>
                    </div>
                  )}
                </div>
              ))}
              
              {/* 时间戳 */}
              <div className="text-xs text-gray-400 mt-3 pt-2 border-t border-gray-200">
                {new Date(currentGroup[currentGroup.length - 1]?.createdAt).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
              </div>
            </div>
          </div>
        );
      }
      
      // 其他消息返回null，因为已经在组中渲染了
      return null;
    }
    return null;
  };

  // 格式化后端消息为前端格式的通用函数 - 按时间顺序自然追加
  const formatBackendMessages = (backendMessages) => {
    const formattedMessages = [];
    
    backendMessages.forEach((msg, msgIndex) => {
      const baseTimestamp = msg.timestamp || new Date().toISOString();
      
      if (msg.role === 'user') {
        // 用户消息直接添加，每个用户消息使用独立的messageId
        formattedMessages.push({
          id: `content-${msg.id || Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
          role: msg.role,
          content: msg.content,
          createdAt: baseTimestamp,
          type: 'content',
          knowledgeBaseIds: msg.metadata?.knowledge_base_ids || [],
          mcpServerIds: msg.metadata?.mcp_server_ids || [],
          useWebSearch: !!msg.metadata?.web_search,
          isError: msg.isError,
          isHistorical: true,
          messageId: `user-msg-${msg.id || msgIndex}-${Date.now()}`
        });
      } else if (msg.role === 'assistant') {
        // Assistant消息：每个助手消息使用独立的messageGroupId，确保不同轮次不会混合
        const messageGroupId = `backend-msg-${msg.id || msgIndex}-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
        
        // 根据后端数据的实际结构，按顺序添加组件
        // 1. 如果有thinking，先添加thinking
        if (msg.thinking) {
          formattedMessages.push({
            id: `thinking-${msg.id || Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
            role: 'assistant',
            thinking: msg.thinking,
            createdAt: baseTimestamp,
            type: 'thinking',
            isCompleted: true,
            isHistorical: true,
            messageId: messageGroupId
          });
        }
        
        // 2. 如果有tool_calls，在content之前添加tool_calls
        if (Array.isArray(msg.tool_calls)) {
          msg.tool_calls.forEach((toolCall, index) => {
            formattedMessages.push({
              id: toolCall.id || `tool-${msg.id}-${index}-${Math.random().toString(36).substring(2, 9)}`,
              role: 'assistant',
              name: toolCall.name || toolCall.tool_name,
              arguments: toolCall.arguments || {},
              result: toolCall.result,
              error: toolCall.error,
              createdAt: baseTimestamp,
              type: 'tool_call',
              isHistorical: true,
              messageId: messageGroupId
            });
          });
        }
        
        // 3. 如果有content，最后添加content
        if (msg.content) {
          formattedMessages.push({
            id: `content-${msg.id || Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
            role: msg.role,
            content: msg.content,
            createdAt: baseTimestamp,
            type: 'content',
            knowledgeBaseIds: msg.metadata?.knowledge_base_ids || [],
            mcpServerIds: msg.metadata?.mcp_server_ids || [],
            useWebSearch: !!msg.metadata?.web_search,
            isError: msg.isError,
            isHistorical: true,
            messageId: messageGroupId
          });
        }
      }
    });
    
    return formattedMessages;
  };

  // 重新同步对话历史，确保前端状态与后端一致
  const syncConversationHistory = async (conversationId, forceServerId = null) => {
    try {
      const currentConv = conversations.find(c => c.id === conversationId);
      const serverId = forceServerId || currentConv?.serverId;
      
      if (!serverId) {
        console.log('会话还没有服务器ID，跳过同步');
        return;
      }

      console.log('开始同步对话历史，服务器ID:', serverId);
      const response = await getConversationDetails(serverId);
      
      if (response.success && response.data) {
        console.log('获取到最新的对话数据:', response.data);
        
        // 使用统一的消息格式化函数
        const formattedMessages = formatBackendMessages(response.data.messages);

        // 更新对话状态
        setConversations(prev =>
          prev.map(conv => {
            if (conv.id === conversationId) {
              return {
                ...conv,
                messages: formattedMessages,
                title: response.data.title || conv.title
              };
            }
            return conv;
          })
        );

        console.log('对话历史同步完成');
      }
    } catch (error) {
      console.error('同步对话历史失败:', error);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gradient-to-br from-gray-50 to-white fixed top-0 left-0">
      {/* Sidebar */}
      <Sidebar
        conversations={conversations.filter(conv =>
          !conv.isNew || conv.id === activeConversationId
        ).map(conv => ({
          ...conv,
          title: conv.title || (conv.id === activeConversationId ? 'New Conversation' : '')
        }))}
        activeChatId={activeConversationId}
        onSelectChat={id => {
          getConversationDetails(id).then(res => {
            if (res.success) {
              console.log("Fetched conversation details:", res.data);

              // 使用统一的消息格式化函数
              const formattedMessages = formatBackendMessages(res.data.messages);

              setConversations(prev =>
                prev.map(c => c.id === id ? { ...c, messages: formattedMessages } : c)
              );

              setActiveConversationId(id);

              setIsThinking(false);
              setThinking('');
              setCompletedThinking(null);

              // 如果最后一个思考消息存在，显示它为已完成
              const lastThinkingMsg = formattedMessages
                .filter(msg => msg.role === 'assistant' && msg.type === 'thinking')
                .pop();

              if (lastThinkingMsg?.thinking) {
                setCompletedThinking(lastThinkingMsg.thinking);
              }

              setTimeout(() => {
                scrollToBottom();
              }, 100);
            }
          }).catch(error => {
            console.error("Failed to fetch conversation details:", error);
          });
        }}
        onNewChat={() => {
          handleNewChat();
          setCompletedThinking(null);
        }}
        onDeleteChat={handleDeleteConversation}
      />

      {/* Main content */}
      <div className="flex flex-col flex-1 overflow-hidden bg-white border-l border-gray-200 shadow-sm" style={{height: '100vh'}}>
        {/* Header */}
        <div className="bg-white border-b border-gray-200 shadow-sm">
          <Header
            isThinking={isThinking}
            onOpenSettings={onOpenSettings}
            selectedModel={selectedModel}
            onModelChange={(model) => {
              console.log('ChatInterface - onModelChange called with:', model);
              setSelectedModel(model);
              // 如果有外部传入的onModelChange，也要调用它
              if (externalOnModelChange) {
                externalOnModelChange(model);
              }
              console.log('ChatInterface - selectedModel state updated to:', model);
            }}
          />
        </div>

        {/* Chat area - 现代化设计 */}
        <div className="flex-1 bg-gradient-to-b from-gray-50/30 to-white relative overflow-y-auto" style={{height: 'calc(100vh - 60px - 140px)'}}>
          <div className="max-w-5xl mx-auto h-full py-6 px-6">
            {/* Messages */}
            <div className="space-y-8 pb-32 pt-4">
              {/* 空状态时显示欢迎信息 - 只在没有任何用户消息时显示 */}
              {messages.filter(msg => msg.role === 'user').length === 0 && (
                <div className="text-center py-16">
                  <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                    <div className="text-white text-2xl">🤖</div>
                  </div>
                  <h3 className="text-xl font-semibold text-gray-800 mb-2">Hello! 我是您的AI助手</h3>
                  <p className="text-gray-600 max-w-md mx-auto">
                    我可以帮助您回答问题、解决问题，或者只是聊天。请随时向我提问！
                  </p>
                  <div className="mt-8 flex flex-wrap justify-center gap-3">
                    <button 
                      onClick={() => handleSendMessage("请解释一下人工智能的基本概念")}
                      className="bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm text-gray-600 hover:border-blue-300 hover:text-blue-600 transition-colors cursor-pointer"
                    >
                      💡 解释概念
                    </button>
                    <button 
                      onClick={() => handleSendMessage("帮我搜索最新的科技新闻")}
                      className="bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm text-gray-600 hover:border-blue-300 hover:text-blue-600 transition-colors cursor-pointer"
                    >
                      🔍 搜索信息
                    </button>
                    <button 
                      onClick={() => handleSendMessage("我遇到了一个编程问题，请帮我解决")}
                      className="bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm text-gray-600 hover:border-blue-300 hover:text-blue-600 transition-colors cursor-pointer"
                    >
                      🛠️ 解决问题
                    </button>
                    <button 
                      onClick={() => handleSendMessage("你好，我们聊聊天吧")}
                      className="bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm text-gray-600 hover:border-blue-300 hover:text-blue-600 transition-colors cursor-pointer"
                    >
                      💬 随意聊天
                    </button>
                  </div>
                </div>
              )}

              {/* 实际的消息列表 - 只显示非欢迎消息 */}
              {messages
                .filter(msg => msg.id !== 'welcome') // 过滤掉欢迎消息
                .map((message, index, filteredMessages) => {
                  // 为每个消息添加更好的样式
                  return (
                    <div 
                      key={message.id || index} 
                      className={`${
                        message.role === 'user' 
                          ? 'flex justify-end' 
                          : 'flex justify-start'
                      } animate-fadeIn`}
                    >
                      {renderMessage(message, index, filteredMessages)}
                    </div>
                  );
                })}

              {/* Scroll anchor */}
              <div ref={messagesEndRef} />
            </div>
          </div>
        </div>

        {/* Input area - 美化输入区域 */}
        <div className="bg-white border-t border-gray-200 shadow-lg" style={{height: '140px', flexShrink: 0}}>
          <ChatInput
            onSendMessage={handleSendMessage}
            isDisabled={isThinking || isLoading}
            isLoading={isThinking || isLoading}
            isStreaming={isStreaming}
            onStopGeneration={handleStopGeneration}
            selectedModel={selectedModel}
          />
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
