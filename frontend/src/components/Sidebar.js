import React, { useState } from 'react';
import { HiPlus, HiOutlineChatAlt, HiOutlineTrash } from 'react-icons/hi';
import ConfirmDialog from './ConfirmDialog';

const Sidebar = ({ 
  conversations = [], 
  activeChatId, 
  onSelectChat, 
  onNewChat,
  onDeleteChat
}) => {
  // 将会话分为新会话和历史会话两组
  const newConversations = conversations.filter(chat => chat.isNew);
  const historyConversations = conversations.filter(chat => !chat.isNew);
  
  // 检查是否有实际的历史会话
  const hasRealConversations = historyConversations.length > 0;
  
  return (
    <aside className="w-60 h-full flex flex-col bg-white border-r border-gray-100 shadow-sm">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex justify-between items-center">
        <h2 className="text-lg font-medium">会话</h2>
        <button
          onClick={onNewChat}
          className="flex items-center justify-center w-8 h-8 rounded-full bg-purple-100 text-purple-600 hover:bg-purple-200 transition-colors"
        >
          <HiPlus className="w-5 h-5" />
        </button>
      </div>
      
      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto py-2">
        {/* 新会话 - 放在顶部 */}
        {newConversations.length > 0 && (
          <>
            <div className="px-2 mb-1 text-xs font-medium text-gray-500 uppercase tracking-wider">新会话</div>
            <div className="space-y-1 mb-4">
              {newConversations.map(chat => (
                <ConversationItem 
                  key={chat.id}
                  chat={chat}
                  isActive={activeChatId === chat.id}
                  onSelect={onSelectChat}
                  onDelete={onDeleteChat}
                />
              ))}
            </div>
          </>
        )}
        
        {/* 历史会话 - 放在底部 */}
        {hasRealConversations && (
          <>
            <div className="px-2 mb-1 text-xs font-medium text-gray-500 uppercase tracking-wider">历史会话</div>
            <div className="space-y-1">
              {historyConversations.map(chat => (
                <ConversationItem 
                  key={chat.id} 
                  chat={chat} 
                  isActive={activeChatId === chat.id}
                  onSelect={onSelectChat}
                  onDelete={onDeleteChat}
                />
              ))}
            </div>
          </>
        )}
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

// 提取出单个会话项组件便于重用
const ConversationItem = ({ chat, isActive, onSelect, onDelete }) => {
  // 添加状态控制确认对话框
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  // 判断是否为新会话：没有serverId或者isNew为true
  const isNewConversation = chat.isNew || !chat.serverId;

  return (
    <>
      <div 
        className={`
          flex items-center justify-between py-2 px-3 rounded-lg cursor-pointer hover:bg-gray-100
          ${isActive ? 'bg-purple-50 hover:bg-purple-50 border border-purple-200' : ''}
        `}
        onClick={() => onSelect(chat.id)}
      >
        <div className="flex items-center space-x-3 flex-1 min-w-0">
          <HiOutlineChatAlt
            className={`h-5 w-5 ${isActive ? 'text-purple-500' : 'text-gray-400'}`}
          />
          <span className="text-sm text-gray-700 truncate flex-1">
            {chat.title || '新会话'}
          </span>
        </div>
        
        {/* 删除按钮 - 只有非新会话才显示 */}
        {onDelete && !isNewConversation && (
          <button 
            className="p-1 rounded-full text-gray-400 hover:bg-gray-200 hover:text-red-500"
            onClick={(e) => {
              e.stopPropagation(); // 防止触发选择会话
              setShowConfirmDialog(true);
            }}
          >
            <HiOutlineTrash className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* 使用自定义确认对话框 - 只有非新会话才需要 */}
      {!isNewConversation && (
        <ConfirmDialog
          isOpen={showConfirmDialog}
          onClose={() => setShowConfirmDialog(false)}
          onConfirm={() => {
            onDelete(chat.id);
            setShowConfirmDialog(false);
          }}
          title="确认删除"
          message={`确定要删除会话 "${chat.title || '新会话'}" 吗？`}
          confirmText="删除"
          cancelText="取消"
          type="danger"
        />
      )}
    </>
  );
};

export default Sidebar; 