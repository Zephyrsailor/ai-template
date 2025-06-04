import React, { useState, useEffect } from 'react';
import { HiOutlineUserCircle, HiOutlineSparkles } from 'react-icons/hi';
import { HiOutlineCpuChip } from 'react-icons/hi2';
import ThinkingBubble from './ThinkingBubble';
import MessageBubble from './MessageBubble';
import MarkdownRenderer from './MarkdownRenderer';
import { RiRobot2Line } from 'react-icons/ri';
import ToolCallDisplay from './ToolCallDisplay';

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

  // 预处理：合并 tool_result 到 tool_call
  const preprocessMessages = (messages) => {
    const toolCallMap = {};
    const toolResultMap = {};
    const mergedMessages = [];

    // 先收集所有 tool_call
    messages.forEach(msg => {
      if (msg.type === 'tool_call' && msg.id) {
        toolCallMap[msg.id] = { ...msg };
      }
      if (msg.type === 'tool_result' && msg.toolCallId) {
        toolResultMap[msg.toolCallId] = msg;
      }
    });

    // 合并 tool_result 到 tool_call
    Object.keys(toolCallMap).forEach(id => {
      if (toolResultMap[id]) {
        toolCallMap[id] = {
          ...toolCallMap[id],
          result: toolResultMap[id].result,
          error: toolResultMap[id].error
        };
      }
    });

    // 构建最终渲染用的消息列表
    messages.forEach(msg => {
      if (msg.type === 'tool_call' && msg.id) {
        mergedMessages.push(toolCallMap[msg.id]);
      } else if (msg.type !== 'tool_result') {
        mergedMessages.push(msg);
      }
    });
    return mergedMessages;
  };

  const renderMessages = () => {
    if (!messages || messages.length === 0) {
      // 只有在确实有thinking内容时才显示ThinkingBubble
      if (thinking && thinking.trim() !== '') {
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
    const processedMessages = preprocessMessages(safeMessages);
    if (processedMessages.length === 0) {
      // 只有在确实有thinking内容时才显示ThinkingBubble
      if (thinking && thinking.trim() !== '') {
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

    // 首先按照原始顺序和时间戳进行全局排序
    const globalSortedMessages = processedMessages.sort((a, b) => {
      // 优先按照 createdAt 排序
      const timeA = new Date(a.createdAt).getTime();
      const timeB = new Date(b.createdAt).getTime();
      
      if (timeA !== timeB) {
        return timeA - timeB;
      }
      
      // 如果时间相同，按照消息类型排序：user -> thinking -> tool_call -> content
      const typeOrder = { 'user': 0, 'thinking': 1, 'tool_call': 2, 'tool_result': 2, 'content': 3 };
      const orderA = typeOrder[a.type] || 999;
      const orderB = typeOrder[b.type] || 999;
      
      if (orderA !== orderB) {
        return orderA - orderB;
      }
      
      // 最后按照 id 排序确保稳定性
      return (a.id || '').localeCompare(b.id || '');
    });

    // 对消息进行分组，但保持全局排序
    const groupedMessages = {};
    const groupOrder = [];
    
    globalSortedMessages.forEach((message) => {
      const groupKey = message.groupId || message.id;
      if (!groupedMessages[groupKey]) {
        groupedMessages[groupKey] = [];
        groupOrder.push(groupKey);
      }
      groupedMessages[groupKey].push(message);
    });

    // 渲染消息组，按照 groupOrder 的顺序
    return groupOrder.map((groupId) => {
      const groupMessages = groupedMessages[groupId];
      
      // 组内消息保持已排序的顺序，不再重新排序
      return (
        <div key={groupId} className="message-group">
          {groupMessages.map((message, index) => {
            const isUser = message.role === 'user';
            const isAssistant = message.role === 'assistant';

            return (
              <React.Fragment key={`${message.id}-${index}`}>
                {isUser && (
                  <div className="flex w-full justify-end">
                    <div className="flex items-end gap-2 max-w-[80%] flex-row-reverse">
                      <div className="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center text-white flex-shrink-0 shadow-md">
                        <HiOutlineUserCircle size={22} />
                      </div>
                      <div className="rounded-2xl px-4 py-2 bg-blue-100 text-blue-900 break-words">
                        <MessageBubble
                          content={message.content}
                          isUser={true}
                        />
                        <div className="text-xs text-gray-400 mt-1 text-right">
                          {new Date(message.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {isAssistant && message.type === 'thinking' && (
                  <div className="flex items-start gap-3">
                    <div className="w-9 h-9 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
                      <RiRobot2Line size={20} className="text-purple-700" />
                    </div>
                    <div className="max-w-[85%]">
                      <ThinkingBubble
                        thinking={message.thinking}
                        isThinking={!message.isCompleted}
                        isCompleted={message.isCompleted}
                        autoCollapse={true}
                        isHistorical={message.isCompleted}
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
                        data={message}
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
                        {new Date(message.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      );
    });
  };

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto px-0 py-6 space-y-4 bg-transparent" style={{overflowY: 'auto', height: '100%', minHeight: 0}}>
      {renderMessages()}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessages; 