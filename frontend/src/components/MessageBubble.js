import React from 'react';
import styled from 'styled-components';
import MarkdownRenderer from './MarkdownRenderer';

const Bubble = styled.div.attrs(props => ({
  className: props.className
}))`
  padding: 14px 18px;
  border-radius: 18px;
  background-color: ${({ $isUser, $isError }) => 
    $isError ? '#ffecec' : $isUser ? '#4a6cf7' : 'white'};
  color: ${({ $isUser, $isError }) => 
    $isError ? '#d32f2f' : $isUser ? 'white' : '#333'};
  box-shadow: ${({ $isUser }) => 
    $isUser ? '0 2px 4px rgba(74, 108, 247, 0.2)' : '0 2px 4px rgba(0, 0, 0, 0.05)'};
  border: ${({ $isError }) => $isError ? '1px solid #ffcdd2' : 'none'};
  position: relative;
  line-height: 1.5;
  
  &::before {
    content: '';
    position: absolute;
    ${({ $isUser }) => $isUser 
      ? 'right: -8px; border-left: 8px solid #4a6cf7;' 
      : 'left: -8px; border-right: 8px solid white;'}
    border-top: 8px solid transparent;
    border-bottom: 8px solid transparent;
    top: 15px;
  }

  ${({ $isError }) => $isError && `
    &::before {
      border-left-color: #ffcdd2;
      border-right-color: #ffcdd2;
    }
  `}
`;

// 为用户消息创建特殊样式，确保短文本不会不必要换行
const UserContent = styled.div`
  display: inline-block;
  white-space: normal;
  word-break: break-word;
  max-width: 100%;
`;

const MessageBubble = ({ content, isUser, isError, variant = "message" }) => {
  return (
    <Bubble $isUser={isUser} $isError={isError}>
      {isUser ? (
        <UserContent>
          <MarkdownRenderer
            content={content}
            variant={variant}
            isUser={isUser}
          />
        </UserContent>
      ) : (
        <MarkdownRenderer
          content={content}
          variant={variant}
          isUser={isUser}
        />
      )}
    </Bubble>
  );
};

export default MessageBubble; 