import React from 'react';
import styled from 'styled-components';
import MarkdownRenderer from './MarkdownRenderer';
import { FaBook } from 'react-icons/fa';

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

// 知识库引用标签，简化设计
const KnowledgeLabel = styled.div`
  display: inline-flex;
  align-items: center;
  background-color: ${props => props.isUser ? 'rgba(255, 255, 255, 0.2)' : 'rgba(74, 108, 247, 0.1)'};
  color: ${props => props.isUser ? 'white' : '#4a6cf7'};
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  margin-bottom: 8px;
  
  svg {
    margin-right: 4px;
  }
`;

// 引用显示
const ReferencesContainer = styled.div`
  margin-top: 15px;
  padding-top: 10px;
  border-top: 1px solid ${props => props.isUser ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)'};
  font-size: 12px;
  color: ${props => props.isUser ? 'rgba(255, 255, 255, 0.8)' : '#666'};
`;

const ReferencesTitle = styled.div`
  font-weight: 500;
  margin-bottom: 5px;
`;

const ReferenceItem = styled.div`
  margin-bottom: 3px;
`;

const MessageBubble = ({ content, isUser, isError, variant = "message", knowledgeBaseIds }) => {
  // 提取知识库引用
  const hasReferences = content && content.includes('参考来源:');
  let mainContent = content;
  let references = null;
  
  if (hasReferences) {
    const parts = content.split('参考来源:');
    mainContent = parts[0];
    if (parts.length > 1) {
      references = parts[1];
    }
  }
  
  return (
    <Bubble $isUser={isUser} $isError={isError}>
      {/* 知识库标签，只在助手回复中显示 */}
      {!isUser && knowledgeBaseIds && knowledgeBaseIds.length > 0 && (
        <KnowledgeLabel isUser={isUser}>
          <FaBook size={12} />
          知识库引用
        </KnowledgeLabel>
      )}
      
      {isUser ? (
        <UserContent>
          <MarkdownRenderer
            content={mainContent}
            variant={variant}
            isUser={isUser}
          />
        </UserContent>
      ) : (
        <MarkdownRenderer
          content={mainContent}
          variant={variant}
          isUser={isUser}
        />
      )}
      
      {/* 显示引用 */}
      {hasReferences && references && (
        <ReferencesContainer isUser={isUser}>
          <ReferencesTitle>参考来源:</ReferencesTitle>
          {references.split('\n').filter(line => line.trim()).map((line, i) => (
            <ReferenceItem key={i}>{line}</ReferenceItem>
          ))}
        </ReferencesContainer>
      )}
    </Bubble>
  );
};

export default MessageBubble; 