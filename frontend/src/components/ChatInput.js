import React, { useState, useRef, useEffect } from 'react';
import { IoSend, IoStop } from 'react-icons/io5';
import { IoMdAttach } from 'react-icons/io';
import { HiMicrophone } from 'react-icons/hi';
import { FaGlobe } from 'react-icons/fa';
import KnowledgeSelector from './KnowledgeSelector';
import MCPServerSelector from './MCPServerSelector';
import styled from 'styled-components';

// 创建工具栏容器
const ToolbarInner = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
`;

// 创建工具按钮
const InnerToolButton = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  background: ${props => props.active ? 'rgba(99, 102, 241, 0.1)' : 'none'};
  color: ${props => props.active ? '#4a6cf7' : '#666'};
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background-color: rgba(99, 102, 241, 0.1);
    color: #4a6cf7;
  }
`;

const ChatInput = ({ 
  onSendMessage, 
  isDisabled = false,
  placeholder = '输入您的问题...',
  isLoading = false,
  isStreaming = false,
  onStopGeneration
}) => {
  const [message, setMessage] = useState('');
  const [selectedKbs, setSelectedKbs] = useState([]);
  const [selectedServers, setSelectedServers] = useState([]);
  const [useWebSearch, setUseWebSearch] = useState(false);
  const textareaRef = useRef(null);
  
  useEffect(() => {
    // Auto-resize textarea
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const newHeight = Math.min(textarea.scrollHeight, 150);
      textarea.style.height = `${newHeight}px`;
    }
  }, [message]);
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !isDisabled && !isLoading) {
      // 传递选中的知识库和MCP服务器IDs
      onSendMessage(message, {
        knowledgeBaseIds: selectedKbs,
        mcpServerIds: selectedServers,
        useWebSearch: useWebSearch
      });
      setMessage('');
    }
  };
  
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };
  
  // 动态生成placeholder
  const getPlaceholder = () => {
    const hasKbs = selectedKbs.length > 0;
    const hasServers = selectedServers.length > 0;
    const hasWeb = useWebSearch;
    
    if (hasKbs && hasServers && hasWeb) {
      return "使用知识库、工具和网络搜索提问...";
    } else if (hasKbs && hasServers) {
      return "使用知识库和工具提问...";
    } else if (hasKbs && hasWeb) {
      return "使用知识库和网络搜索提问...";
    } else if (hasServers && hasWeb) {
      return "使用工具和网络搜索提问...";
    } else if (hasKbs) {
      return "在知识库中搜索相关信息...";
    } else if (hasServers) {
      return "使用工具解决问题...";
    } else if (hasWeb) {
      return "使用网络搜索提问...";
    }
    return placeholder;
  };
  
  // 检查是否有任何增强功能被启用
  const hasAnyFeatureEnabled = selectedKbs.length > 0 || selectedServers.length > 0 || useWebSearch;
  
  return (
    <div className="w-full border-t border-gray-100 bg-white shadow-sm">
      <div className="max-w-3xl mx-auto px-4">
        {/* 顶部工具栏 */}
        <ToolbarInner>
          <KnowledgeSelector 
            selectedKbs={selectedKbs}
            onChange={setSelectedKbs}
          />
          <InnerToolButton 
            title="互联网搜索"
            active={useWebSearch}
            onClick={() => setUseWebSearch(!useWebSearch)}
          >
            <FaGlobe size={14} />
          </InnerToolButton>
          <MCPServerSelector 
            selectedServers={selectedServers}
            onChange={setSelectedServers}
          />
        </ToolbarInner>
        
        {/* 输入区域 */}
        <form onSubmit={handleSubmit} className="mb-2">
          <div className="flex flex-col rounded-xl border border-gray-200 bg-white overflow-hidden transition-all duration-200 focus-within:border-gray-300 focus-within:shadow-sm">
            {/* 主要输入框 */}
            <div className="w-full">
              <textarea
                ref={textareaRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={getPlaceholder()}
                disabled={isDisabled}
                className="w-full py-3 px-4 resize-none outline-none text-gray-700 placeholder-gray-400 min-h-[44px] max-h-[150px]"
                rows={1}
              />
            </div>
            
            {/* 底部按钮栏 */}
            <div className="border-t border-gray-100 bg-gray-50 px-3 py-2 flex items-center justify-between">
              <div className="flex items-center">
                <button 
                  type="button"
                  className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 transition-colors"
                  title="添加附件"
                >
                  <IoMdAttach size={20} />
                </button>
                
                <button
                  type="button"
                  className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 transition-colors"
                  title="语音输入"
                >
                  <HiMicrophone size={20} />
                </button>
              </div>
              
              <div className="flex items-center">
                <span className="text-xs text-gray-400 mr-3">Enter 发送, Shift+Enter 换行</span>
                
                {/* 停止按钮 - 在加载或流式响应时显示 */}
                {(isLoading || isStreaming) && onStopGeneration && (
                  <button
                    type="button"
                    onClick={onStopGeneration}
                    className="p-2.5 rounded-lg transition-all duration-200 text-white bg-red-600 hover:bg-red-700 mr-2"
                    title="停止生成"
                  >
                    <IoStop size={18} />
                  </button>
                )}
                
                {/* 发送按钮 */}
                <button
                  type="submit"
                  className={`p-2.5 rounded-lg transition-all duration-200 ${
                    message.trim() && !isDisabled && !isLoading && !isStreaming
                      ? 'text-white bg-gray-700 hover:bg-gray-800' 
                      : 'text-gray-400 bg-gray-100 cursor-not-allowed'
                  }`}
                  disabled={!message.trim() || isDisabled || isLoading || isStreaming}
                  title={(isLoading || isStreaming) ? "正在生成中..." : "发送消息"}
                >
                  <IoSend size={18} />
                </button>
              </div>
            </div>
          </div>
        </form>
        
        {/* 状态指示区 */}
        {hasAnyFeatureEnabled && (
          <div className="text-xs text-gray-500 flex items-center flex-wrap gap-3 mb-3">
            {selectedKbs.length > 0 && 
              <span className="inline-flex items-center bg-purple-50 text-purple-700 py-1 px-2 rounded-full">
                <span>知识库 ({selectedKbs.length})</span>
              </span>
            }
            {useWebSearch && 
              <span className="inline-flex items-center bg-blue-50 text-blue-700 py-1 px-2 rounded-full">
                <span>网络搜索</span>
              </span>
            }
            {selectedServers.length > 0 && 
              <span className="inline-flex items-center bg-indigo-50 text-indigo-700 py-1 px-2 rounded-full">
                <span>工具 ({selectedServers.length})</span>
              </span>
            }
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatInput;
