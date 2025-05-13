import React, { useState, useRef, useEffect } from 'react';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import Header from './Header';
import Sidebar from './Sidebar';
import MessageBubble from './MessageBubble';
import ThinkingBubble from './ThinkingBubble';
import { CgSpinner } from 'react-icons/cg';
import { FiUser } from 'react-icons/fi';
import { RiRobot2Line } from 'react-icons/ri';
// 导入API函数
import { fetchConversations, createConversation, deleteConversation } from '../api';

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
  createdAt: new Date().toISOString()
};

const ChatInterface = ({ 
  messages = [], 
  onMessagesChange,
  assistantName = 'AI Assistant',
  useSystemMessage = false,
  systemMessage = '',
  autoFocusInput = false,
  onOpenSettings,
  isThinking: externalIsThinking
}) => {
  const [conversations, setConversations] = useState([
    { id: 'default', title: '', messages: [WELCOME_MESSAGE], isNew: true }
  ]);
  const [isThinking, setIsThinking] = useState(externalIsThinking || false);
  const [thinking, setThinking] = useState('');
  const [completedThinking, setCompletedThinking] = useState(null); // 存储已完成的思考内容
  const [activeConversationId, setActiveConversationId] = useState('default');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  
  // Get active conversation
  const activeConversation = conversations.find(c => c.id === activeConversationId) || conversations[0];
  messages = activeConversation?.messages || [];
  
  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages, thinking, completedThinking]);
  
  // 使用外部传入的isThinking状态更新内部状态
  useEffect(() => {
    if (typeof externalIsThinking !== 'undefined') {
      setIsThinking(externalIsThinking);
    }
  }, [externalIsThinking]);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  const handleSendMessage = async (messageText, options = {}) => {
    // 解构选项获取知识库和MCP服务器ID以及网页搜索选项
    const { knowledgeBaseIds = [], mcpServerIds = [], useWebSearch = false } = options;

    if (!messageText.trim()) return;
    
    // 重置思考相关状态
    setCompletedThinking(null);
    
    // 构建用户消息对象
    const userMessage = { 
      id: `user-${Date.now()}`,
      role: 'user', 
      content: messageText, 
      createdAt: new Date().toISOString(),
      // 保存使用的知识库和服务器IDs，方便展示
      knowledgeBaseIds: knowledgeBaseIds.length > 0 ? knowledgeBaseIds : [],
      mcpServerIds: mcpServerIds.length > 0 ? mcpServerIds : [],
      useWebSearch: useWebSearch
    };
    
    // 更新对话中的消息
    updateConversation(activeConversationId, userMessage);
    
    // 尝试保存会话到数据库
    saveCurrentConversation(activeConversationId);
    
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
    setThinking(''); // 清空思考内容
    setIsThinking(true); // 开始思考
    
    let toolCallsCollected = []; // 收集工具调用
    
    try {
      // API端点
      const API_URL = 'http://localhost:8000/api/chat/stream';
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('authToken') || ''}`,
        },
        body: JSON.stringify({
          message: messageText,
          history: history,
          knowledge_base_ids: knowledgeBaseIds,
          mcp_server_ids: mcpServerIds,
          use_tools: mcpServerIds.length > 0,
          use_web_search: useWebSearch,
          // 如果会话已有服务器ID，则传递它
          conversation_id: conversations.find(c => c.id === activeConversationId)?.serverId,
          // 使用会话标题或从用户消息生成标题
          conversation_title: 
            conversations.find(c => c.id === activeConversationId)?.title || 
            (messageText.length > 20 ? messageText.substring(0, 20) + '...' : messageText)
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
      let hasReceivedContent = false; // 标记是否已收到实际内容（非思考）
      
      const updateMessage = () => {
        const assistantMessage = { 
          id: `assistant-${Date.now()}`,
          role: 'assistant', 
          content: assistantResponseText,
          thinking: thinkingContent, // 保存关联的思考内容
          createdAt: new Date().toISOString(),
          // 保存使用的知识库和服务器IDs
          knowledgeBaseIds: userMessage.knowledgeBaseIds,
          mcpServerIds: userMessage.mcpServerIds,
          // 保存工具调用
          toolCalls: toolCallsCollected
        };

        // 更新会话中的消息
        updateConversationWithAssistantMessage(activeConversationId, assistantMessage);
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
              const chunkData = JSON.parse(line);
              
              if (chunkData.type === 'reasoning' || chunkData.type === 'thinking') {
                // 收集思考内容
                thinkingContent += (chunkData.data || "");
                // 在控制台输出收到的思考内容
                console.log("收到思考内容", (thinkingContent || "").substring(0, 50) + "...");
                // 更新UI状态
                setThinking(thinkingContent);
                setIsThinking(true);
                collectingThinking = true;
              } else if (chunkData.type === 'conversation_id' && chunkData.data) {
                console.log("接收到会话ID:", chunkData.data);
                const convData = chunkData.data;
                // 更新本地会话数据
                setConversations(prev => 
                  prev.map(conv => {
                    if (conv.id === activeConversationId) {
                      // 更新会话ID
                      return { 
                        ...conv, 
                        serverId: convData.id,
                        isNew: convData.is_new
                      };
                    }
                    return conv;
                  })
                );
              } else if (chunkData.type === 'content' || chunkData.type === 'reference') {
                // 当收到第一个内容块时
                hasReceivedContent = true;
                if (collectingThinking) {
                  collectingThinking = false; // 思考阶段结束
                  setIsThinking(false); // 思考结束
                  setCompletedThinking(thinkingContent); // 保存已完成的思考内容
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
            setCompletedThinking(thinkingContent); // 保存已完成的思考内容
          }
          
          // 添加到响应文本
          assistantResponseText += chunkText;
          updateMessage();
        }
      }
      
      // 流处理完成，确保思考状态已关闭但内容保留
      setIsThinking(false);
      if (thinkingContent) {
        setCompletedThinking(thinkingContent);
      }
      
    } catch (error) {
      console.error('错误:', error);
      setIsThinking(false);
      
      // 如果有思考内容，保存为已完成
      if (thinking) {
        setCompletedThinking(thinking);
      }
      
      // 创建错误消息并更新会话
      const errorMessage = { 
        id: `assistant-${Date.now()}`,
        role: 'assistant', 
        content: `发生错误: ${error.message}`, 
        isError: true,
        createdAt: new Date().toISOString()
      };
      
      updateConversation(activeConversationId, errorMessage);
    } finally {
      setIsLoading(false);
    }
  };
  
  const updateConversation = (conversationId, message) => {
    setConversations(prev => 
      prev.map(conv => {
        if (conv.id === conversationId) {
          const updatedMessages = [...conv.messages, message];
          // 第一条用户消息时，根据消息内容设置会话标题并移除isNew标记
          if (conv.isNew && message.role === 'user') {
            // 使用用户消息的前30个字符作为标题，超出则添加省略号
            const newTitle = message.content.length > 30 ? 
              message.content.substring(0, 30) + '...' : 
              message.content;
              
            return { 
              ...conv, 
              messages: updatedMessages,
              title: newTitle, // 使用更长的标题摘要
              isNew: false // 已有用户消息，不再是新会话
            };
          }
          return { ...conv, messages: updatedMessages };
        }
        return conv;
      })
    );
  };
  
  // 特别为助手消息创建的更新函数，避免重复添加或更新现有消息
  const updateConversationWithAssistantMessage = (conversationId, assistantMessage) => {
    // 确保assistantMessage中包含thinking字段
    if (completedThinking && !assistantMessage.thinking) {
      assistantMessage.thinking = completedThinking;
    }
    
    setConversations(prev => 
      prev.map(conv => {
        if (conv.id === conversationId) {
          // 检查最后一条消息是否已经是助手的回复
          const lastMessage = conv.messages[conv.messages.length - 1];
          if (lastMessage && lastMessage.role === 'assistant' && !lastMessage.isError) {
            // 更新现有的助手消息而不是添加新消息
            const updatedMessages = [...conv.messages];
            // 保留思考内容
            if (assistantMessage.thinking && !updatedMessages[updatedMessages.length - 1].thinking) {
              updatedMessages[updatedMessages.length - 1].thinking = assistantMessage.thinking;
            }
            updatedMessages[updatedMessages.length - 1] = assistantMessage;
            return { ...conv, messages: updatedMessages };
          } else {
            // 添加新的助手消息
            return { ...conv, messages: [...conv.messages, assistantMessage] };
          }
        }
        return conv;
      })
    );
  };
  
  const handleNewChat = () => {
    // 检查是否已有未使用的空白会话
    const unusedChat = conversations.find(
      conv => conv.isNew && conv.messages.length === 1 && conv.messages[0].role === 'assistant'
    );
    
    if (unusedChat) {
      // 如果有未使用的空白会话，直接切换到它
      setActiveConversationId(unusedChat.id);
    } else {
      // 创建新的会话，但不显示标题，标记为isNew
      const newId = `conv-${Date.now()}`;
      setConversations(prev => [
        // 将新会话添加到顶部
        { 
          id: newId, 
          title: '', // 不设置标题，等用户发送消息后再设置
          messages: [WELCOME_MESSAGE],
          isNew: true // 标记为新会话
        },
        ...prev
      ]);
      setActiveConversationId(newId);
    }
  };
  
  // 新增保存会话到数据库的方法
  const saveCurrentConversation = async (conversationId) => {
    try {
      // 获取当前活动会话
      const currentConv = conversations.find(c => c.id === conversationId);
      if (!currentConv) return;
      
      // 获取用户消息，优先使用第一条用户消息作为标题
      const firstUserMessage = currentConv.messages.find(msg => msg.role === 'user');
      const titleFromMessage = firstUserMessage ? 
        (firstUserMessage.content.length > 30 ? 
          firstUserMessage.content.substring(0, 30) + '...' : 
          firstUserMessage.content) : 
        null;
      
      // 检查是否已有服务器端ID
      if (!currentConv.serverId) {
        // 创建新会话
        const response = await createConversation({
          // 优先使用从用户消息生成的标题，而不是使用"新会话"作为默认值
          title: titleFromMessage || currentConv.title || "新会话",
          // 可以添加其他元数据
          metadata: {
            clientId: currentConv.id,
            isNew: false
          }
        });
        
        if (response.data && response.data.id) {
          // 更新本地会话对象，保存服务器ID
          setConversations(prev => 
            prev.map(conv => {
              if (conv.id === conversationId) {
                return { ...conv, serverId: response.data.id };
              }
              return conv;
            })
          );
          
          console.log('会话已保存到服务器，ID:', response.data.id);
        }
      } else {
        // 已有服务器ID，后续可以实现更新操作
        console.log('会话已存在于服务器，ID:', currentConv.serverId);
      }
    } catch (error) {
      console.error('保存会话失败:', error);
    }
  };
  
  // 载入会话历史
  useEffect(() => {
    const loadConversations = async () => {
      try {
        const response = await fetchConversations();
        console.log("加载会话响应:", response);
        
        if (response.success && Array.isArray(response.data)) {
          // 将服务器会话转换为前端会话格式
          const serverConversations = response.data.map(conv => {
            // 确保消息是数组格式
            const convMessages = Array.isArray(conv.messages) ? conv.messages : [];
            
            return {
              id: `local-${conv.id}`, // 本地ID
              serverId: conv.id,      // 服务器ID
              title: conv.title || "新会话",
              messages: convMessages.length > 0 
                ? convMessages.map(msg => ({
                    id: msg.id || `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
                    role: msg.role,
                    content: msg.content,
                    createdAt: msg.timestamp || new Date().toISOString()
                  }))
                : [WELCOME_MESSAGE],
              isNew: false
            };
          });
          
          console.log("处理后的会话数据:", serverConversations);
          
          // 合并现有会话和服务器会话，确保新会话在顶部
          setConversations(prev => {
            // 仅保留新会话
            const newLocalConvs = prev.filter(c => c.isNew);
            // 新会话放在顶部
            return [...newLocalConvs, ...serverConversations];
          });
          
          // 如果有会话且没有活动会话，设置第一个为活动会话
          if (serverConversations.length > 0 && (!activeConversationId || !conversations.some(c => c.id === activeConversationId))) {
            setActiveConversationId(serverConversations[0].id);
          }
        } else {
          console.warn("加载会话失败或格式不正确:", response.message);
        }
      } catch (error) {
        console.error('加载会话历史失败:', error);
      }
    };
    
    // 只有用户已登录时才加载会话
    if (localStorage.getItem('authToken')) {
      loadConversations();
    }
  }, []);

  // 修改删除会话方法，同步删除服务器数据
  const handleDeleteConversation = async (conversationId) => {
    const conversation = conversations.find(c => c.id === conversationId);
    if (!conversation) return;
    
    // 如果有服务器ID，同步删除服务器数据
    if (conversation.serverId) {
      try {
        await deleteConversation(conversation.serverId);
        console.log('已从服务器删除会话:', conversation.serverId);
      } catch (error) {
        console.error('从服务器删除会话失败:', error);
      }
    }
    
    // 从本地状态中移除会话
    setConversations(prev => prev.filter(c => c.id !== conversationId));
    
    // 如果删除的是当前活动会话，切换到第一个会话或创建新会话
    if (conversationId === activeConversationId) {
      const remaining = conversations.filter(c => c.id !== conversationId);
      if (remaining.length > 0) {
        setActiveConversationId(remaining[0].id);
      } else {
        handleNewChat();
      }
    }
  };
  
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-50 fixed top-0 left-0">
      {/* Sidebar */}
      <Sidebar
        conversations={conversations.filter(conv => 
          // 只显示已有实际对话内容的会话（非isNew或当前活动的会话）
          !conv.isNew || conv.id === activeConversationId
        ).map(conv => ({
          ...conv,
          // 只在侧边栏显示时，为空标题的会话显示"新会话"
          title: conv.title || (conv.id === activeConversationId ? '新会话' : '')
        }))}
        activeChatId={activeConversationId}
        onSelectChat={id => {
          setActiveConversationId(id);
          // 查找选中会话的最后一条助手消息，恢复其思考内容
          const selectedConversation = conversations.find(conv => conv.id === id);
          if (selectedConversation && selectedConversation.messages) {
            // 找到最后一条助手消息
            const lastAssistantMsg = [...selectedConversation.messages]
              .reverse()
              .find(msg => msg.role === 'assistant');
              
            // 如果找到且有思考内容，则恢复
            if (lastAssistantMsg && lastAssistantMsg.thinking) {
              setCompletedThinking(lastAssistantMsg.thinking);
            } else {
              setCompletedThinking(null);
            }
          } else {
            setCompletedThinking(null);
          }
        }}
        onNewChat={() => {
          handleNewChat();
          setCompletedThinking(null); // 新会话时清除已完成的思考
        }}
        onDeleteChat={handleDeleteConversation}
      />
      
      {/* Main content */}
      <div className="flex flex-col flex-1 h-full overflow-hidden relative">
        {/* Header */}
        <Header 
          isThinking={isThinking} 
          onOpenSettings={onOpenSettings}
        />
        
        {/* Chat area */}
        <div className="flex-1 overflow-y-auto bg-white relative">
          <div className="max-w-3xl mx-auto h-full py-4 px-4">
            {/* Messages */}
            <div className="space-y-6 pb-20 static">
              {messages.map((message, index) => {
                // 判断是否显示思考内容 - 对于助手消息，检查是否有thinking字段
                // 为当前消息查找是否有关联的已完成思考内容
                const msgHasThinking = message.role === 'assistant' && message.thinking;
                const showCompletedThinking = 
                  !isThinking && 
                  (msgHasThinking || (index === messages.length - 1 && message.role === 'assistant' && completedThinking));
                
                // 确定要显示的思考内容 - 优先使用消息自带的thinking，其次是completedThinking
                const thinkingToShow = msgHasThinking ? message.thinking : completedThinking;
                
                return (
                  <React.Fragment key={message.id}>
                    {/* 如果是助手消息且有思考内容，显示思考气泡 */}
                    {showCompletedThinking && thinkingToShow && (
                      <div className="flex items-start gap-3">
                        <div className="w-9 h-9 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
                          <RiRobot2Line size={20} className="text-purple-700" />
                        </div>
                        <div className="max-w-[85%]">
                          <ThinkingBubble 
                            thinking={thinkingToShow} 
                            isThinking={false} 
                            isCompleted={true} 
                            autoCollapse={true} 
                            isHistorical={index < messages.length - 1} // 如果不是最后一条消息，则标记为历史记录
                            preserveContent={false} // 设置为false，让历史记录中的思考内容默认是折叠的
                          />
                        </div>
                      </div>
                    )}
                    
                    {/* 显示消息内容 */}
                    <div 
                      className={`flex items-start gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}
                    >
                      {message.role === 'assistant' && (
                        <div className="w-9 h-9 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
                          <RiRobot2Line size={20} className="text-purple-700" />
                        </div>
                      )}
                      
                      <div className={`max-w-[85%] ${message.role === 'user' ? 'order-1' : 'order-2'}`}>
                        <MessageBubble
                          content={message.content}
                          isUser={message.role === 'user'}
                          knowledgeBaseIds={message.knowledgeBaseIds}
                          mcpServerIds={message.mcpServerIds}
                          isError={message.isError}
                          toolCalls={message.toolCalls}
                          useWebSearch={message.useWebSearch}
                        />
                        <div className="text-xs text-gray-400 mt-1 px-1">
                          {new Date(message.createdAt).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </div>
                      </div>
                      
                      {message.role === 'user' && (
                        <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 order-2">
                          <FiUser size={18} className="text-gray-700" />
                        </div>
                      )}
                    </div>
                  </React.Fragment>
                );
              })}
              
              {/* 活动的思考气泡 */}
              {isThinking && (
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
                    <CgSpinner className="w-5 h-5 text-purple-700 animate-spin" />
                  </div>
                  <div className="max-w-[85%]">
                    <ThinkingBubble 
                      thinking={thinking} 
                      isThinking={true} 
                      autoCollapse={false} 
                      preserveContent={true} 
                    />
                  </div>
                </div>
              )}
              
              {/* Scroll anchor */}
              <div ref={messagesEndRef} />
            </div>
          </div>
        </div>
        
        {/* Input area */}
        <ChatInput 
          onSendMessage={handleSendMessage}
          isDisabled={isThinking || isLoading}
          isLoading={isThinking || isLoading}
        />
      </div>
    </div>
  );
};

export default ChatInterface;
