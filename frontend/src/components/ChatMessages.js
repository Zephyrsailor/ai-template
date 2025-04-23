import React from 'react';
import styled from 'styled-components';
import { FaUser, FaRobot } from 'react-icons/fa';
import ThinkingBubble from './ThinkingBubble';
import MessageBubble from './MessageBubble';
import MarkdownRenderer from './MarkdownRenderer';

const MessagesContainer = styled.div`
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
  background-color: #f9fafc;
  position: relative;
  -webkit-overflow-scrolling: touch; /* 增强iOS滚动体验 */
  overscroll-behavior: contain; /* 防止滚动事件穿透 */
  
  /* 确保滚动条宽度足够便于触摸 */
  &::-webkit-scrollbar {
    width: 10px;
    height: 10px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 10px;
    border: 2px solid #f9fafc;
  }
  
  &::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 0, 0, 0.3);
  }
  
  @media (max-width: 768px) {
    padding: 15px;
  }
`;

const MessageWrapper = styled.div.attrs(props => ({
  className: props.className
}))`
  display: flex;
  flex-direction: ${({ $isUser }) => $isUser ? 'row-reverse' : 'row'};
  align-items: flex-start;
  gap: 12px;
  max-width: 80%;
  align-self: ${({ $isUser }) => $isUser ? 'flex-end' : 'flex-start'};
`;

const MessageGroup = styled.div.attrs(props => ({
  className: props.className
}))`
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 80%;
  align-self: ${({ $isUser }) => $isUser ? 'flex-end' : 'flex-start'};
`;

const Avatar = styled.div.attrs(props => ({
  className: props.className
}))`
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: ${({ $isUser }) => $isUser ? '#4a6cf7' : '#6c757d'};
  color: white;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
`;

const TimeStamp = styled.div.attrs(props => ({
  className: props.className
}))`
  font-size: 12px;
  color: #9e9e9e;
  margin-top: 5px;
  text-align: ${({ $isUser }) => $isUser ? 'right' : 'left'};
`;

const WelcomeMessage = styled.div`
  align-self: center;
  text-align: center;
  color: #757575;
  font-size: 14px;
  padding: 12px 20px;
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
  width: auto;
  max-width: 80%;
  margin: 0 auto 20px;
`;

const ThinkingAlignedWrapper = styled.div`
  padding-left: 50px;
  width: 100%;
  max-width: calc(100% - 50px);
`;

const formatTime = (timestamp) => {
  if (!timestamp) return '';
  try {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    return '';
  }
};

// 改进滚动指示器
const ScrollIndicator = styled.div`
  position: fixed;
  bottom: 80px;
  right: 20px;
  width: 45px;
  height: 45px;
  border-radius: 50%;
  background-color: rgba(74, 108, 247, 0.9);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  z-index: 100;
  transition: all 0.2s;
  opacity: ${({ $visible }) => $visible ? 1 : 0};
  transform: ${({ $visible }) => $visible ? 'scale(1)' : 'scale(0.8)'};
  pointer-events: ${({ $visible }) => $visible ? 'all' : 'none'};
  touch-action: manipulation; /* 优化触摸体验 */
  
  &:hover {
    background-color: rgba(74, 108, 247, 1);
    transform: scale(1.1);
  }
  
  @media (max-width: 768px) {
    bottom: 70px;
    right: 15px;
  }
`;

const ArrowDown = styled.div`
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 8px solid white;
`;

const ChatMessages = ({ 
  messages, 
  thinking, 
  isThinking = true, 
  messagesEndRef, 
  scrollRef,
  autoScroll,
  setAutoScroll
}) => {
  const hasMessages = messages.length > 0;
  
  // 重新排列消息，确保思考内容与AI回复视觉上作为一组
  const renderMessages = () => {
    // 如果没有消息，只显示欢迎信息
    if (!hasMessages) {
      return (
        <WelcomeMessage>
          👋 你好！我是AI助手，有什么可以帮到你的吗？
        </WelcomeMessage>
      );
    }
    
    // 创建消息元素数组
    const messageElements = [];
    
    for (let i = 0; i < messages.length; i++) {
      const currentMessage = messages[i];
      const nextMessage = i < messages.length - 1 ? messages[i + 1] : null;
      
      if (currentMessage.role === 'user') {
        // 用户消息单独显示
        messageElements.push(
          <MessageWrapper 
            key={`msg-${i}`} 
            $isUser={true}
          >
            <Avatar $isUser={true}>
              <FaUser />
            </Avatar>
            <div>
              <MessageBubble 
                content={currentMessage.content}
                isUser={true}
                isError={false}
              />
              <TimeStamp $isUser={true}>
                {formatTime(currentMessage.timestamp)}
              </TimeStamp>
            </div>
          </MessageWrapper>
        );
      } else {
        // 助手消息，如果有思考内容则作为一组显示
        const hasThinking = currentMessage.thinking && currentMessage.thinking.trim();
        
        const assistantMessageGroup = (
          <MessageGroup key={`msg-group-${i}`}>
            {hasThinking && (
              <ThinkingAlignedWrapper>
                <ThinkingBubble
                  content={currentMessage.thinking}
                  isThinking={false}
                  isHistorical={true}
                />
              </ThinkingAlignedWrapper>
            )}
            
            <MessageWrapper $isUser={false}>
              <Avatar $isUser={false}>
                <FaRobot />
              </Avatar>
              <div>
                <MessageBubble 
                  content={currentMessage.content}
                  isUser={false}
                  isError={currentMessage.isError}
                />
                <TimeStamp $isUser={false}>
                  {formatTime(currentMessage.timestamp)}
                </TimeStamp>
              </div>
            </MessageWrapper>
          </MessageGroup>
        );
        
        messageElements.push(assistantMessageGroup);
      }
    }
    
    // 处理当前活动的思考内容（用户最后一条消息之后的思考）
    const lastMessage = messages[messages.length - 1];
    if (lastMessage && lastMessage.role === 'user' && thinking) {
      messageElements.push(
        <MessageGroup key="current-thinking-group">
          <ThinkingAlignedWrapper>
            <ThinkingBubble
              content={thinking} 
              isThinking={isThinking} 
              isHistorical={false}
            />
          </ThinkingAlignedWrapper>
        </MessageGroup>
      );
    }
    
    return messageElements;
  };

  // 处理点击滚动指示器事件
  const handleScrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    setAutoScroll(true);
  };

  return (
    <MessagesContainer ref={scrollRef}>
      {renderMessages()}
      
      {/* 用于自动滚动到底部 */}
      <div ref={messagesEndRef} />
      
      {/* 滚动指示器，只在消息较多且用户不在底部时显示 */}
      {messages.length > 3 && (
        <ScrollIndicator 
          $visible={!autoScroll} 
          onClick={handleScrollToBottom}
        >
          <ArrowDown />
        </ScrollIndicator>
      )}
    </MessagesContainer>
  );
};

export default ChatMessages; 