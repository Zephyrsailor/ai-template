import React from 'react';
import styled from 'styled-components';
import MarkdownRenderer from './MarkdownRenderer';
import ToolCallDisplay from './ToolCallDisplay';
import { FaBook, FaTools } from 'react-icons/fa';

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

// 工具调用标签
const ToolLabel = styled.div`
  display: inline-flex;
  align-items: center;
  background-color: ${props => props.isUser ? 'rgba(255, 255, 255, 0.2)' : 'rgba(74, 108, 247, 0.1)'};
  color: ${props => props.isUser ? 'white' : '#4a6cf7'};
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  margin-bottom: 8px;
  margin-right: 8px;
  
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

// 处理工具调用渲染的组件
const MessageContent = ({ content, isUser, toolCalls = [] }) => {
  // 解析内容，保留普通文本，将JSON代码块替换为工具调用组件
  const parseContent = (content) => {
    if (!content) return null;
    
    // 匹配```json...```格式的代码块
    const codeBlockRegex = /```json\n([\s\S]*?)\n```/g;
    const parts = [];
    let lastIndex = 0;
    let match;
    
    while ((match = codeBlockRegex.exec(content)) !== null) {
      // 添加工具调用前的文本
      if (match.index > lastIndex) {
        parts.push(
          <MarkdownRenderer
            key={`text-${lastIndex}`}
            content={content.substring(lastIndex, match.index)}
            variant="message"
            isUser={isUser}
          />
        );
      }
      
      // 处理JSON代码块
      try {
        const jsonContent = match[1];
        const data = JSON.parse(jsonContent);
        
        // 检查是否是工具调用
        if (data.name || data.tool_name) {
          // 使用ToolCallDisplay组件
          parts.push(
            <ToolCallDisplay 
              key={`tool-${match.index}`} 
              data={data} 
              isUser={isUser} 
            />
          );
        } else {
          // 非工具调用JSON，正常显示
          parts.push(
            <MarkdownRenderer
              key={`code-${match.index}`}
              content={match[0]}
              variant="message"
              isUser={isUser}
            />
          );
        }
      } catch (e) {
        // 解析失败，正常显示
        parts.push(
          <MarkdownRenderer
            key={`code-${match.index}`}
            content={match[0]}
            variant="message"
            isUser={isUser}
          />
        );
      }
      
      lastIndex = match.index + match[0].length;
    }
    
    // 添加剩余文本
    if (lastIndex < content.length) {
      parts.push(
        <MarkdownRenderer
          key={`text-end`}
          content={content.substring(lastIndex)}
          variant="message"
          isUser={isUser}
        />
      );
    }
    
    return parts;
  };
  
  return isUser ? (
    <MarkdownRenderer
      content={content}
      variant="message"
      isUser={isUser}
    />
  ) : (
    <>{parseContent(content)}</>
  );
};

const MessageBubble = ({ 
  content, 
  isUser, 
  isError, 
  variant = "message", 
  knowledgeBaseIds,
  mcpServerIds,
  toolCalls = []
}) => {
  // 提取知识库引用
  const hasReferences = content && content.includes('参考来源:');
  let mainContent = content;
  let references = null;
  
  // 从内容中提取引用
  if (hasReferences) {
    const parts = content.split('参考来源:');
    mainContent = parts[0];
    if (parts.length > 1) {
      references = parts[1];
    }
  }
  
  return (
    <Bubble $isUser={isUser} $isError={isError}>
      {/* 知识库标签 */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
        {!isUser && knowledgeBaseIds && knowledgeBaseIds.length > 0 && (
          <KnowledgeLabel isUser={isUser}>
            <FaBook size={12} />
            知识库引用
          </KnowledgeLabel>
        )}
        
        {/* MCP服务器标签 */}
        {!isUser && mcpServerIds && mcpServerIds.length > 0 && (
          <ToolLabel isUser={isUser}>
            <FaTools size={12} />
            工具服务
          </ToolLabel>
        )}
      </div>
      
      {isUser ? (
        <UserContent>
          <MessageContent
            content={mainContent}
            isUser={isUser}
          />
        </UserContent>
      ) : (
        <>
          {/* 使用内容处理组件，保持原始顺序 */}
          <MessageContent
            content={mainContent}
            isUser={isUser}
            toolCalls={toolCalls}
          />
          
          {/* 显示引用 */}
          {hasReferences && references && (
            <ReferencesContainer isUser={isUser}>
              <ReferencesTitle>参考来源:</ReferencesTitle>
              <ReferenceItem>{references}</ReferenceItem>
            </ReferencesContainer>
          )}
        </>
      )}
    </Bubble>
  );
};

export default MessageBubble; 