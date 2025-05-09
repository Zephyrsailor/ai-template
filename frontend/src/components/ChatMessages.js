import React, { useState, useEffect } from 'react';
import { HiOutlineUserCircle, HiOutlineSparkles } from 'react-icons/hi';
import { HiOutlineCpuChip } from 'react-icons/hi2';
import ThinkingBubble from './ThinkingBubble';
import MessageBubble from './MessageBubble';
import MarkdownRenderer from './MarkdownRenderer';

const ChatMessages = ({ 
  messages, 
  thinking, 
  isThinking = false, 
  messagesEndRef, 
  scrollRef,
  autoScroll,
  setAutoScroll
}) => {
  const hasMessages = messages.length > 0;
  const [lastUserMessageId, setLastUserMessageId] = useState(null);

  useEffect(() => {
    if (messages.length > 0) {
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === 'user' && messages[i].content.trim() !== '') {
          setLastUserMessageId(`user-${i}-${messages[i].timestamp}`);
          break;
        }
      }
    }
  }, [messages]);

  // 过滤有效消息
  const filterValidMessages = arr => (arr || []).filter(m =>
    m &&
    typeof m === 'object' &&
    ('role' in m) && (m.role === 'user' || m.role === 'assistant') &&
    ('content' in m) && typeof m.content === 'string'
  );

  const renderMessages = () => {
    if (!messages || messages.length === 0) {
      // 即使没有消息，如果在思考状态，也显示思考组件
      if (isThinking && thinking && thinking.trim() !== '') {
        return (
          <div key="thinking-bubble-empty" className="flex w-full justify-start">
            <div className="flex items-start max-w-[85%]">
              <ThinkingBubble thinking={thinking} isThinking={isThinking} />
            </div>
          </div>
        );
      }
      return null;
    }
    const safeMessages = filterValidMessages(messages);
    if (safeMessages.length === 0) {
      // 没有有效消息但有思考内容时显示思考组件
      if (isThinking && thinking && thinking.trim() !== '') {
        return (
          <div key="thinking-bubble-empty" className="flex w-full justify-start">
            <div className="flex items-start max-w-[85%]">
              <ThinkingBubble thinking={thinking} isThinking={isThinking} />
            </div>
          </div>
        );
      }
      return null;
    }

    // 查找最后一个用户消息的位置
    let lastUserMessageIndex = -1;
    let lastAssistantMessageIndex = -1;
    
    for (let i = safeMessages.length - 1; i >= 0; i--) {
      if (safeMessages[i].role === 'user' && lastUserMessageIndex === -1) {
        lastUserMessageIndex = i;
      }
      if (safeMessages[i].role === 'assistant' && lastAssistantMessageIndex === -1) {
        lastAssistantMessageIndex = i;
      }
      if (lastUserMessageIndex !== -1 && lastAssistantMessageIndex !== -1) {
        break;
      }
    }

    // 简化思考组件显示逻辑: 只要在思考状态且有思考内容就显示
    const shouldShowThinking = isThinking && thinking && thinking.trim() !== '';
    
    // 确定思考组件的位置 - 通常在最后一个助手消息之后，如果没有助手消息，则在最后一个用户消息之后
    const thinkingPosition = lastAssistantMessageIndex !== -1 ? lastAssistantMessageIndex + 1 : lastUserMessageIndex + 1;
    
    // 准备渲染消息元素
    const messageElements = [];

    // 渲染所有消息，并在适当位置插入思考组件
    safeMessages.forEach((currentMessage, i) => {
      if (!currentMessage || !currentMessage.role || !currentMessage.content) return;
      
      const isUser = currentMessage.role === 'user';
      
      // 仅显示内容不为空的助手消息
      if (!isUser && (!currentMessage.content || currentMessage.content.trim() === '')) {
        return;
      }

      // 渲染消息
      messageElements.push(
        <div key={`${currentMessage.role}-${i}-${currentMessage.timestamp || 'key'}`} className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}>
          <div className={`flex items-end gap-2 max-w-[80%] ${isUser ? 'flex-row-reverse' : ''}`}>
            <div className={`w-9 h-9 rounded-full flex items-center justify-center ${isUser ? 'bg-blue-600' : 'bg-indigo-500'} text-white flex-shrink-0 shadow-md`}>
              {isUser ? <HiOutlineUserCircle size={22} /> : <HiOutlineCpuChip size={20} />}
            </div>
            <div className={`rounded-2xl px-4 py-2 shadow-sm ${isUser ? 'bg-blue-100 text-blue-900' : 'bg-gray-100 text-gray-900'} break-words`}>
              <MarkdownRenderer content={currentMessage.content} />
              <div className="text-xs text-gray-400 mt-1 text-right">{currentMessage.timestamp ? new Date(currentMessage.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}</div>
            </div>
          </div>
        </div>
      );
      
      // 如果当前位置是思考组件应该显示的位置，并且需要显示思考组件
      if (i === thinkingPosition - 1 && shouldShowThinking) {
        messageElements.push(
          <div key="thinking-bubble" className="flex w-full justify-start">
            <div className="flex items-start max-w-[85%]">
              <ThinkingBubble thinking={thinking} isThinking={isThinking} />
            </div>
          </div>
        );
      }
    });

    return messageElements;
  };

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto px-0 py-6 space-y-4 bg-transparent">
      {renderMessages()}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessages; 