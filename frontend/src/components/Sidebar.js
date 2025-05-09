import React from 'react';
import { AiOutlinePlus } from 'react-icons/ai';
import { BiMessageRoundedDetail } from 'react-icons/bi';

const Sidebar = ({ conversations = [], activeChatId, onSelectChat, onNewChat }) => {
  // 过滤出有实际内容的会话（非空标题或有多条消息）
  const hasRealConversations = conversations.some(chat => 
    (chat.title && chat.title.trim() !== '') || 
    (chat.messages && chat.messages.length > 1)
  );
  
  return (
    <aside className="w-60 h-full flex flex-col bg-white border-r border-gray-100 shadow-sm">
      {/* New chat button */}
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors duration-200"
        >
          <AiOutlinePlus size={16} />
          <span>新建会话</span>
        </button>
      </div>
      
      {/* Conversation list - 只在有实际对话时显示 */}
      <div className="flex-1 overflow-y-auto py-2">
        {hasRealConversations && (
          <div className="px-2 mb-1 text-xs font-medium text-gray-500 uppercase tracking-wider">历史会话</div>
        )}
        
        <ul className="space-y-0.5 px-1.5">
          {conversations.length > 0 ? (
            conversations.map((chat) => (
              <li key={chat.id}>
                <button
                  onClick={() => onSelectChat(chat.id)}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors duration-200 flex items-center gap-2 ${
                    activeChatId === chat.id
                      ? 'bg-gray-100 text-gray-900 font-medium'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <BiMessageRoundedDetail 
                    size={16} 
                    className={activeChatId === chat.id ? 'text-gray-700' : 'text-gray-400'} 
                  />
                  <span className="truncate">
                    {/* 如果是当前会话且没有标题，显示为"新会话" */}
                    {(chat.title && chat.title.trim()) || (activeChatId === chat.id ? '新会话' : '未命名会话')}
                  </span>
                </button>
              </li>
            ))
          ) : (
            <li className="px-3 py-2 text-sm text-gray-500 italic">暂无历史会话</li>
          )}
        </ul>
      </div>
      
      {/* Footer */}
      <div className="p-3 border-t border-gray-100">
        <div className="text-xs text-gray-500 text-center">
          AI 助手 © 2025
        </div>
      </div>
    </aside>
  );
};

export default Sidebar; 