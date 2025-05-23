import React, { useState, useRef, useEffect } from 'react';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import Header from './Header';
import Sidebar from './Sidebar';
import MessageBubble from './MessageBubble';
import ThinkingBubble from './ThinkingBubble';
import ToolCallDisplay from './ToolCallDisplay'; // Import ToolCallDisplay
import { CgSpinner } from 'react-icons/cg';
import { FiUser } from 'react-icons/fi';
import { RiRobot2Line } from 'react-icons/ri';
// 导入API函数
import { fetchConversations, createConversation, deleteConversation, getConversationDetails } from '../api';

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
  type: 'content' // Add type for welcome message
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
    // 只在新消息到来时自动滚动，用户手动滚动时不干扰
    if (messagesEndRef.current && messages.length > 0) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg && lastMsg.role === 'assistant') {
        messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    }
  }, [messages]);

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
      type: 'content', // Add type for user message
      // 保存使用的知识库和服务器IDs，方便展示
      knowledgeBaseIds: knowledgeBaseIds.length > 0 ? knowledgeBaseIds : [],
      mcpServerIds: mcpServerIds.length > 0 ? mcpServerIds : [],
      useWebSearch: useWebSearch
    };

    // 更新对话中的消息
    updateConversation(activeConversationId, userMessage);

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

    let currentMessageId = null;
    let currentMessageType = null;

    try {
      // API端点
      const API_URL = 'http://localhost:8000/api/chat/stream';
      const currentConversation = conversations.find(c => c.id === activeConversationId);
      const conversationId = currentConversation?.serverId;
      
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
                // 更新当前会话的serverId
                const newConversationId = chunkData.data;
                console.log('服务器创建了新会话，ID:', newConversationId);
                
                // 更新会话ID
                setConversations(prev =>
                  prev.map(conv => {
                    if (conv.id === activeConversationId) {
                      return { ...conv, serverId: newConversationId };
                    }
                    return conv;
                  })
                );
                
                // 保存更新后的会话
                saveConversationAfterCreation(activeConversationId, newConversationId);
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
              // 判断是否需要新建消息块
              if (type !== currentMessageType) {
                // 新建消息块
                currentMessageId = `${type}-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
                currentMessageType = type;
                if (type === 'thinking' || type === 'reasoning') {
                  updateConversation(activeConversationId, {
                    id: currentMessageId,
                    role: 'assistant',
                    thinking: chunkData.data || "",
                    createdAt: new Date().toISOString(),
                    type: 'thinking',
                    isCompleted: false
                  });
                  setThinking(chunkData.data || "");
                  setIsThinking(true);
                } else if (type === 'tool_call') {
                  console.log("tool_call", chunkData.data)
                  let tools = JSON.parse(chunkData.data)  
                  tools.forEach(tool => {
                    updateConversation(activeConversationId, {
                      id: tool.id,
                      role: 'assistant',
                      toolCallId: tool.id,
                      name: tool.name || tool.tool_name,
                      arguments: tool.arguments || {},
                      createdAt: new Date().toISOString(),
                      type: 'tool_call'
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
                  updateConversation(activeConversationId, {
                    id: currentMessageId,
                    role: 'assistant',
                    content: chunkData.data || "",
                    createdAt: new Date().toISOString(),
                    type: 'content',
                    knowledgeBaseIds: userMessage.knowledgeBaseIds,
                    mcpServerIds: userMessage.mcpServerIds,
                    useWebSearch: userMessage.useWebSearch
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
              title: conv.title || "New Conversation",
              messages: convMessages.length > 0
                ? convMessages.flatMap(msg => {
                    const thinkingArr = [];
                    const contentArr = [];
                    const toolArr = [];
                    // 推理
                    if (msg.thinking) {
                      thinkingArr.push({
                        id: `thinking-${msg.id || Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
                        role: 'assistant',
                        thinking: msg.thinking,
                        createdAt: msg.timestamp || new Date().toISOString(),
                        type: 'thinking',
                        isCompleted: true
                      });
                    }
                    // 内容
                    if (msg.content) {
                      contentArr.push({
                        id: msg.id || `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
                        role: msg.role,
                        content: msg.content,
                        createdAt: msg.timestamp || new Date().toISOString(),
                        type: 'content',
                        knowledgeBaseIds: msg.metadata?.knowledge_base_ids || [],
                        mcpServerIds: msg.metadata?.mcp_server_ids || [],
                        useWebSearch: !!msg.metadata?.web_search,
                        isError: msg.isError
                      });
                    }
                    // 工具
                    if (Array.isArray(msg.tool_calls)) {
                      msg.tool_calls.forEach(toolCall => {
                        toolArr.push({
                          id: `tool-${toolCall.id || Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
                          role: 'assistant',
                          name: toolCall.name || toolCall.tool_name,
                          arguments: toolCall.arguments || {},
                          result: toolCall.result,
                          error: toolCall.error,
                          timestamp: toolCall.timestamp || new Date().toISOString(),
                          type: toolCall.result !== undefined || toolCall.error !== undefined ? 'tool_result' : 'tool_call'
                        });
                      });
                    }
                    // 合并顺序：推理 > 内容 > 工具
                    return [...thinkingArr, ...contentArr, ...toolArr];
                  })
                : [WELCOME_MESSAGE],
              isNew: false
            };
          });

          console.log("Processed conversation data:", serverConversations);

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

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-50 fixed top-0 left-0">
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

              const formattedMessages = res.data.messages.flatMap(msg => { // Use flatMap here too
                 const formattedEntries = [];

                 if (msg.thinking) {
                   formattedEntries.push({
                     id: `thinking-${msg.id || Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
                     role: 'assistant',
                     thinking: msg.thinking,
                     createdAt: msg.timestamp || new Date().toISOString(),
                     type: 'thinking',
                     isCompleted: true
                   });
                 }

                 if (Array.isArray(msg.tool_calls)) {
                   msg.tool_calls.forEach(toolCall => {
                     formattedEntries.push({
                       id: `tool-${toolCall.id || Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
                       role: 'assistant',
                       name: toolCall.name || toolCall.tool_name,
                       arguments: toolCall.arguments || {},
                       result: toolCall.result,
                       error: toolCall.error,
                       timestamp: toolCall.timestamp || new Date().toISOString(),
                       type: toolCall.result !== undefined || toolCall.error !== undefined ? 'tool_result' : 'tool_call'
                     });
                   });
                 }

                 formattedEntries.push({
                   id: msg.id || `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
                   role: msg.role,
                   content: msg.content,
                   createdAt: msg.timestamp || new Date().toISOString(),
                   type: 'content',
                   knowledgeBaseIds: msg.metadata?.knowledge_base_ids || [],
                   mcpServerIds: msg.metadata?.mcp_server_ids || [],
                   useWebSearch: !!msg.metadata?.web_search,
                   isError: msg.isError
                 });

                 return formattedEntries;
              });

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
                const isUser = message.role === 'user';
                const isAssistant = message.role === 'assistant';

                return (
                  <React.Fragment key={message.id}>
                    {/* 用户消息 */}
                    {isUser && (
                       <div
                         className="flex items-start gap-3 justify-end"
                       >
                         <div className="max-w-[85%] order-1">
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
                    )}

                    {/* 助手消息条目 */}
                    {isAssistant && message.type === 'thinking' && (
                       <div className="flex items-start gap-3">
                         <div className="w-9 h-9 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
                           <RiRobot2Line size={20} className="text-purple-700" />
                         </div>
                         <div className="max-w-[85%]">
                           <ThinkingBubble
                             thinking={message.thinking}
                             isThinking={!message.isCompleted} // 如果未完成，则显示为正在思考
                             isCompleted={message.isCompleted}
                             autoCollapse={true}
                             isHistorical={message.isCompleted} // 如果已完成，则标记为历史
                             preserveContent={false}
                           />
                         </div>
                       </div>
                    )}

                    {isAssistant && (message.type === 'tool_call' || message.type === 'tool_result') && (
                       <div className="flex items-start gap-3">
                         <div className="w-9 h-9 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
                           <RiRobot2Line size={20} className="text-purple-700" />
                         </div>
                         <div className="max-w-[85%]">
                           <ToolCallDisplay
                             data={message} // Pass the message object which contains tool call/result data
                             isUser={false}
                           />
                         </div>
                       </div>
                    )}

                    {isAssistant && message.type === 'content' && (
                       <div className="flex items-start gap-3">
                         <div className="w-9 h-9 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
                           <RiRobot2Line size={20} className="text-purple-700" />
                         </div>
                         <div className="max-w-[85%]">
                           <MessageBubble
                             content={message.content}
                             isUser={false}
                             knowledgeBaseIds={message.knowledgeBaseIds}
                             mcpServerIds={message.mcpServerIds}
                             isError={message.isError}
                             useWebSearch={message.useWebSearch}
                           />
                           <div className="text-xs text-gray-400 mt-1 px-1 self-start">
                             {new Date(message.createdAt).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                           </div>
                         </div>
                       </div>
                    )}
                  </React.Fragment>
                );
              })}

              {/* Active thinking bubble (for the very last, ongoing thinking) */}
              {/* {isThinking && !completedThinking && (
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
              )} */}

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
