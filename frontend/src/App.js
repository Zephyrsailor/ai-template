import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import ChatInterface from './components/ChatInterface';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import KnowledgeManager from './components/KnowledgeManager';
import MCPManager from './components/MCPManager';
import Settings from './components/Settings';
import { RiRobot2Fill, RiSettings4Line, RiHistoryLine, RiUserLine, RiBookLine, RiTerminalBoxLine } from 'react-icons/ri';
import GlobalStyles from './styles/GlobalStyles';
import ChatInput from './components/ChatInput';
import { Menu, MenuItem } from '@mui/material';
import { useRef } from 'react';
import Tooltip from '@mui/material/Tooltip';
import { PanelLeft } from 'lucide-react';
import { sendMessage, fetchConversations as fetchConversationsApi, deleteConversation, checkAuthStatus, diagnoseConnectionIssues } from './api/index';
import Auth from './components/Auth';
import { initAuthToken, getCurrentUser } from './api/auth';

// 全局认证检查和诊断
const token = localStorage.getItem('authToken');

// 确保axios的全局实例有Authorization头
if (token) {
  console.log('全局认证检查: 发现token，长度:', token.length);
  // 确保这里导入的axios是同一个实例
  import('./api/http').then(httpModule => {
    const axios = httpModule.default;
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    console.log('全局初始化: Authorization头已设置');
    
    // 添加全局诊断按钮到window对象，方便通过控制台调用
    window.diagnoseAPI = diagnoseConnectionIssues;
    console.log('全局诊断工具已添加到window.diagnoseAPI');
  });
} else {
  console.log('全局认证检查: 未找到token');
}

// 初始化token并输出状态
const tokenInitialized = initAuthToken();
console.log('Token初始化状态:', tokenInitialized);
console.log('认证状态:', checkAuthStatus());

const AppContainer = styled.div`
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
`;

const MainContent = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-primary);
`;

const HistoryListContainer = styled.div`
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background-color: #f9fafc;
`;

const HistoryItem = styled.div`
  padding: 15px;
  margin-bottom: 15px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background-color: #f0f2f5;
    transform: translateY(-2px);
  }
`;

const HistoryTitle = styled.div`
  font-weight: 500;
  margin-bottom: 5px;
  color: #333;
`;

const HistoryPreview = styled.div`
  font-size: 14px;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const HistoryDate = styled.div`
  font-size: 12px;
  color: #999;
  margin-top: 8px;
  text-align: right;
`;

const EmptyHistory = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
  text-align: center;
  
  svg {
    font-size: 48px;
    margin-bottom: 15px;
    opacity: 0.4;
  }
`;

// 本地存储键名
const STORAGE_KEY = 'ai_chat_history';

// 模拟一些助手选项
const assistants = [];

function App() {
  // 所有useState/useEffect都在这里，绝不放在条件分支或return后
  const [activeAssistant, setActiveAssistant] = useState(assistants[0]);
  const [chatSessions, setChatSessions] = useState(() => {
    const saved = localStorage.getItem('ai_chat_sessions');
    return saved ? JSON.parse(saved) : [{ id: 'default', title: '新会话', messages: [] }];
  });
  const [activeSessionId, setActiveSessionId] = useState(chatSessions[0]?.id || 'default');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [anchorEl, setAnchorEl] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    try {
      const savedHistory = localStorage.getItem(STORAGE_KEY);
      if (savedHistory) {
        setChatSessions(prev => [
          { id: 'default', title: '新会话', messages: JSON.parse(savedHistory) },
          ...prev.filter(s => s.id !== 'default')
        ]);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  }, []);

  useEffect(() => {
    const handleStorageChange = () => {
      try {
        const savedHistory = localStorage.getItem(STORAGE_KEY);
        if (savedHistory) {
          setChatSessions(prev => [
            { id: 'default', title: '新会话', messages: JSON.parse(savedHistory) },
            ...prev.filter(s => s.id !== 'default')
          ]);
        } else {
          setChatSessions(prev => [
            { id: 'default', title: '新会话', messages: [] },
            ...prev.filter(s => s.id !== 'default')
          ]);
        }
      } catch (error) {
        console.error('Error loading chat history:', error);
      }
    };
    window.addEventListener('chatHistoryUpdated', handleStorageChange);
    window.addEventListener('storage', (e) => {
      if (e.key === STORAGE_KEY) {
        handleStorageChange();
      }
    });
    return () => {
      window.removeEventListener('chatHistoryUpdated', handleStorageChange);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  useEffect(() => {
    const checkAuth = async () => {
      if (initAuthToken()) {
        const result = await getCurrentUser();
        if (result.success) {
          setUser(result.data);
          setIsAuthenticated(true);
        } else {
          setIsAuthenticated(false);
        }
      } else {
        setIsAuthenticated(false);
      }
    };
    checkAuth();
  }, []);

  // 加载会话列表
  useEffect(() => {
    const loadConversations = async () => {
      try {
        const conversations = await fetchConversationsApi();
        // 处理从API获取的会话
        if (Array.isArray(conversations) && conversations.length > 0) {
          setChatSessions(prev => {
            // 合并已有的会话与新获取的会话
            const newSessions = [...conversations];
            // 保留本地的default会话
            const defaultSession = prev.find(s => s.id === 'default');
            if (defaultSession) {
              newSessions.unshift(defaultSession);
            }
            return newSessions;
          });
        }
      } catch (error) {
        console.error('Failed to load conversations:', error);
      }
    };
    loadConversations();
  }, []);

  const handleAuthSuccess = (userData) => {
    setUser(userData);
    setIsAuthenticated(true);
  };

  // 未登录时只渲染登录页
  if (!isAuthenticated) {
    return <Auth onAuthSuccess={handleAuthSuccess} />;
  }
  
  // 新建会话
  const handleNewSession = () => {
    // 只允许一个未命名会话
    if (chatSessions.some(s => !s.title || s.title === '新会话')) return;
    const newSession = { id: Date.now().toString(), title: '新会话', messages: [] };
    setChatSessions(prev => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
  };

  // 切换会话
  const handleSelectSession = (id) => {
    setActiveSessionId(id);
  };

  // 更新会话内容（有内容时才写入历史）
  const handleUpdateSession = (id, messages) => {
    setChatSessions(prev => {
      return prev.map(s => {
        if (s.id === id) {
          // 有内容时才赋title，否则不显示在历史
          if (messages && messages.length > 0 && (!s.title || s.title === '新会话')) {
            return { ...s, title: messages[0].content.slice(0, 20) || '新会话', messages };
          }
          return { ...s, messages };
        }
        return s;
      });
    });
  };

  // 获取当前会话
  const currentSession = chatSessions.find(s => s.id === activeSessionId) || chatSessions[0];

  // 用户菜单逻辑
  const handleUserMenuOpen = (e) => setAnchorEl(e.currentTarget);
  const handleUserMenuClose = () => setAnchorEl(null);
  
  // 打开设置面板
  const handleOpenSettings = () => {
    setIsSettingsOpen(true);
    handleUserMenuClose(); // 关闭用户菜单
  };

  // 处理登出
  const handleLogout = () => {
    // 清除认证状态和用户信息
    setIsAuthenticated(false);
    setUser(null);
    // 清除本地存储的令牌
    localStorage.removeItem('authToken');
    // 刷新页面
    window.location.reload();
  };

  // 侧边栏开关
  const toggleSidebar = () => setSidebarOpen(v => !v);

  // 渲染历史记录列表
  const renderHistory = () => {
    if (chatSessions.length === 0) {
      return (
        <EmptyHistory>
          <RiHistoryLine />
          <div>暂无聊天历史记录</div>
        </EmptyHistory>
      );
    }

    // 显示每个会话记录，而不是分割会话
    return chatSessions.map((session, index) => {
      // 找到第一条用户消息用于标题
      const firstUserMessage = session.messages.find(msg => msg.role === 'user');
      const timestamp = firstUserMessage?.timestamp || session.messages[0]?.timestamp;
      
      return (
        <HistoryItem 
          key={session.id} 
          onClick={() => {
            // 设置当前会话
            setActiveSessionId(session.id);
            // 找到AI聊天助手对象，并设置为当前活动助手
            const aiChatAssistant = assistants.find(a => a.id === 'ai-chat');
            if (aiChatAssistant) {
              setActiveAssistant(aiChatAssistant);
            }
          }}
        >
          <HistoryTitle>
            {session.title || (firstUserMessage?.content.substring(0, 40) || "对话记录")}
            {firstUserMessage?.content && firstUserMessage.content.length > 40 ? '...' : ''}
          </HistoryTitle>
          <HistoryPreview>
            {session.messages.length} 条消息
          </HistoryPreview>
          <HistoryDate>
            {timestamp ? new Date(timestamp).toLocaleString() : '未知时间'}
          </HistoryDate>
        </HistoryItem>
      );
    });
  };

  return !isAuthenticated
    ? <Auth onAuthSuccess={handleAuthSuccess} />
    : (
      <>
        <GlobalStyles />
        <div className="flex h-screen w-screen bg-gray-50">
          {/* 左侧历史会话栏，可关闭 */}
          {sidebarOpen && (
            <Sidebar
              sidebarOpen={sidebarOpen}
              toggleSidebar={toggleSidebar}
              onNewSession={handleNewSession}
              chatSessions={chatSessions}
              activeSessionId={activeSessionId}
              onSelectSession={handleSelectSession}
            />
          )}
          {/* 展开侧边栏按钮 */}
          {!sidebarOpen && (
            <div className="flex flex-col h-full justify-start items-center pt-4 pl-2 pr-1 bg-transparent">
              <Tooltip title="Open sidebar" placement="right" arrow>
                <button className="w-9 h-9 flex items-center justify-center rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-600 transition shadow-none focus:outline-none" onClick={toggleSidebar}>
                  <PanelLeft size={22} />
                </button>
              </Tooltip>
            </div>
          )}
          {/* 主聊天区 */}
          <main className="flex-1 flex flex-col items-center justify-start relative overflow-y-auto bg-gray-50">
            {/* 使用Header组件替代原有用户菜单 */}
          <Header
              isThinking={false}
              onOpenSettings={handleOpenSettings}
              user={user}
              onLogout={handleLogout}
              selectedModel={selectedModel}
              onModelChange={setSelectedModel}
            />

            {/* 聊天窗口无历史时居中显示，输入框自动聚焦 */}
            <div className={`flex-1 w-full flex flex-col items-center justify-${currentSession.messages.length === 0 ? 'center' : 'end'}`}>
              <div className="w-full max-w-4xl flex-1 flex flex-col justify-end pt-2 pb-36">
                <ChatInterface
                  assistantName="ChatGPT"
                  messages={currentSession.messages}
                  onMessagesChange={msgs => handleUpdateSession(currentSession.id, msgs)}
                  autoFocusInput={currentSession.messages.length === 0}
                  onOpenSettings={handleOpenSettings}
                  isThinking={false}
                  selectedModel={selectedModel}
                  onModelChange={setSelectedModel}
                />
              </div>
            </div>
            <div className="fixed bottom-0 left-72 right-0 flex justify-center pb-8 z-30">
              <div className="w-full max-w-4xl"></div>
            </div>
          </main>
        </div>

        {/* 设置面板 */}
        <Settings
          isOpen={isSettingsOpen}
          onClose={() => setIsSettingsOpen(false)}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
        />
      </>
    );
}

export default App;
