import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import ChatInterface from './components/ChatInterface';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import KnowledgeManager from './components/KnowledgeManager';
import { RiRobot2Fill, RiSettings4Line, RiHistoryLine, RiUserLine, RiBookLine } from 'react-icons/ri';
import GlobalStyles from './styles/GlobalStyles';

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
const assistants = [
  { id: 'ai-chat', name: 'AI聊天助手', icon: <RiRobot2Fill size={24} /> },
  { id: 'knowledge', name: '知识库管理', icon: <RiBookLine size={24} /> },
  { id: 'history', name: '历史记录', icon: <RiHistoryLine size={24} /> },
  { id: 'profile', name: '个人设置', icon: <RiUserLine size={24} /> },
  { id: 'settings', name: '系统设置', icon: <RiSettings4Line size={24} /> }
];

function App() {
  const [activeAssistant, setActiveAssistant] = useState(assistants[0]);
  const [chatHistory, setChatHistory] = useState([]);
  
  // 加载历史记录
  useEffect(() => {
    try {
      const savedHistory = localStorage.getItem(STORAGE_KEY);
      if (savedHistory) {
        setChatHistory(JSON.parse(savedHistory));
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  }, []);
  
  // 监听本地存储变化，实时更新历史记录
  useEffect(() => {
    const handleStorageChange = () => {
      try {
        const savedHistory = localStorage.getItem(STORAGE_KEY);
        if (savedHistory) {
          setChatHistory(JSON.parse(savedHistory));
        } else {
          setChatHistory([]);
        }
      } catch (error) {
        console.error('Error loading chat history:', error);
      }
    };
    
    // 添加自定义事件监听器
    window.addEventListener('chatHistoryUpdated', handleStorageChange);
    
    // 添加storage事件监听器（跨标签页支持）
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
  
  // 渲染历史记录列表
  const renderHistory = () => {
    if (chatHistory.length === 0) {
      return (
        <EmptyHistory>
          <RiHistoryLine />
          <div>暂无聊天历史记录</div>
        </EmptyHistory>
      );
    }

    // 对话分组
    const conversations = [];
    let currentConversation = [];
    
    for (const message of chatHistory) {
      if (message.role === 'user' && currentConversation.length > 0) {
        conversations.push([...currentConversation]);
        currentConversation = [message];
      } else {
        currentConversation.push(message);
      }
    }
    
    if (currentConversation.length > 0) {
      conversations.push(currentConversation);
    }
    
    return conversations.map((conversation, index) => {
      const firstUserMessage = conversation.find(msg => msg.role === 'user');
      const timestamp = firstUserMessage?.timestamp;
      
      return (
        <HistoryItem 
          key={index} 
          onClick={() => {
            // 找到AI聊天助手对象，并设置为当前活动助手
            const aiChatAssistant = assistants.find(a => a.id === 'ai-chat');
            if (aiChatAssistant) {
              setActiveAssistant(aiChatAssistant);
            }
            // 这里可以添加加载特定对话的逻辑
          }}
        >
          <HistoryTitle>
            {firstUserMessage?.content.substring(0, 40) || "对话记录"}
            {firstUserMessage?.content.length > 40 ? '...' : ''}
          </HistoryTitle>
          <HistoryPreview>
            {conversation.length} 条消息
          </HistoryPreview>
          <HistoryDate>
            {timestamp ? new Date(timestamp).toLocaleString() : '未知时间'}
          </HistoryDate>
        </HistoryItem>
      );
    });
  };

  return (
    <>
      <GlobalStyles />
      <AppContainer>
        <Sidebar 
          assistants={assistants}
          activeAssistant={activeAssistant}
          setActiveAssistant={setActiveAssistant}
        />
        <MainContent>
          {activeAssistant.id === 'ai-chat' ? (
            <ChatInterface assistantName={activeAssistant.name} />
          ) : activeAssistant.id === 'history' ? (
            <HistoryListContainer>
              {renderHistory()}
            </HistoryListContainer>
          ) : activeAssistant.id === 'knowledge' ? (
            <KnowledgeManager />
          ) : (
            <div style={{ padding: '20px', textAlign: 'center' }}>
              {activeAssistant.id === 'profile' ? '个人设置' : '系统设置'} 功能待开发...
            </div>
          )}
        </MainContent>
      </AppContainer>
    </>
  );
}

export default App; 