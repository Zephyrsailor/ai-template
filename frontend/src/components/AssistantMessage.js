import React, { useState } from 'react';
import styled from 'styled-components';
import { RiRobot2Line } from 'react-icons/ri';
import { FiChevronDown, FiChevronUp } from 'react-icons/fi';
import { HiCog } from 'react-icons/hi';
import MessageBubble from './MessageBubble';
import ToolCallDisplay from './ToolCallDisplay';

const MessageContainer = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 24px;
`;

const Avatar = styled.div`
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: #f3e8ff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
`;

const MessageContent = styled.div`
  flex: 1;
  background-color: #f8fafc;
  border-radius: 16px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  min-width: 0;
`;

const ThinkingSection = styled.div`
  margin-bottom: 12px;
  padding: 12px;
  background-color: #fef7ff;
  border-radius: 8px;
  border-left: 3px solid #a855f7;
`;

const ThinkingHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  margin-bottom: ${props => props.isExpanded ? '8px' : '0'};
`;

const ThinkingTitle = styled.div`
  font-size: 14px;
  font-weight: 500;
  color: #7c3aed;
  display: flex;
  align-items: center;
  gap: 6px;
`;

const ThinkingContent = styled.div`
  font-size: 13px;
  color: #6b7280;
  line-height: 1.5;
  white-space: pre-wrap;
  max-height: ${props => props.isExpanded ? 'none' : '60px'};
  overflow: hidden;
  position: relative;
  
  ${props => !props.isExpanded && `
    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 20px;
      background: linear-gradient(transparent, #fef7ff);
    }
  `}
`;

const ToolSection = styled.div`
  margin-bottom: 12px;
`;

const ToolItem = styled.div`
  margin-bottom: 8px;
  padding: 8px 12px;
  background-color: #f1f5f9;
  border-radius: 6px;
  border-left: 3px solid #3b82f6;
`;

const ContentSection = styled.div`
  /* 主要内容区域 */
`;

const Timestamp = styled.div`
  font-size: 12px;
  color: #9ca3af;
  margin-top: 8px;
  padding-left: 4px;
`;

const AssistantMessage = ({ 
  messageGroup, 
  isThinking = false,
  currentThinking = '',
  isCompleted = false
}) => {
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(false);
  
  // 从消息组中提取不同类型的内容
  const thinkingMessage = messageGroup.find(msg => msg.type === 'thinking');
  const toolMessages = messageGroup.filter(msg => msg.type === 'tool_call' || msg.type === 'tool_result');
  const contentMessage = messageGroup.find(msg => msg.type === 'content');
  
  // 获取时间戳（使用最新的消息时间）
  const timestamp = contentMessage?.createdAt || messageGroup[messageGroup.length - 1]?.createdAt;
  
  // 如果正在思考，使用当前思考内容
  const displayThinking = isThinking ? currentThinking : thinkingMessage?.thinking;
  
  // 判断是否真正完成（有内容且不在思考中）
  const isReallyCompleted = isCompleted || (!isThinking && contentMessage?.content);
  
  return (
    <MessageContainer>
      <Avatar>
        <RiRobot2Line size={20} className="text-purple-700" />
      </Avatar>
      
      <MessageContent>
        {/* 推理部分 */}
        {displayThinking && (
          <ThinkingSection>
            <ThinkingHeader 
              isExpanded={isThinkingExpanded}
              onClick={() => setIsThinkingExpanded(!isThinkingExpanded)}
            >
              <ThinkingTitle>
                <HiCog className="animate-spin" style={{ animationDuration: isThinking ? '2s' : '0s' }} />
                {isThinking ? '正在思考...' : '推理过程'}
              </ThinkingTitle>
              {displayThinking.length > 100 && (
                isThinkingExpanded ? <FiChevronUp /> : <FiChevronDown />
              )}
            </ThinkingHeader>
            
            {(isThinkingExpanded || displayThinking.length <= 100 || isThinking) && (
              <ThinkingContent isExpanded={isThinkingExpanded}>
                {displayThinking}
              </ThinkingContent>
            )}
          </ThinkingSection>
        )}
        
        {/* 主要内容部分 - 移到工具调用之前 */}
        {contentMessage && (
          <ContentSection>
            <MessageBubble
              content={contentMessage.content}
              isUser={false}
              knowledgeBaseIds={contentMessage.knowledgeBaseIds}
              mcpServerIds={contentMessage.mcpServerIds}
              isError={contentMessage.isError}
              useWebSearch={contentMessage.useWebSearch}
              compact={true}
            />
          </ContentSection>
        )}
        
        {/* 工具调用部分 - 移到内容之后 */}
        {toolMessages.length > 0 && (
          <ToolSection>
            {toolMessages.map((toolMsg, index) => (
              <ToolItem key={toolMsg.id || index}>
                <ToolCallDisplay data={toolMsg} isUser={false} compact={true} />
              </ToolItem>
            ))}
          </ToolSection>
        )}
        
        {/* 时间戳 */}
        {timestamp && (
          <Timestamp>
            {new Date(timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
          </Timestamp>
        )}
      </MessageContent>
    </MessageContainer>
  );
};

export default AssistantMessage; 