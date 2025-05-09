import React from 'react';
import styled from 'styled-components';
import MarkdownRenderer from './MarkdownRenderer';
import ToolCallDisplay from './ToolCallDisplay';
import { FaBook, FaTools, FaGlobe } from 'react-icons/fa';

const Bubble = styled.div.attrs(props => ({
  className: props.className
}))`
  padding: 14px 18px;
  border-radius: 18px;
  background-color: ${({ $isUser, $isError }) => 
    $isError ? '#ffecec' : $isUser ? '#f1f5f9' : 'white'};
  color: ${({ $isUser, $isError }) => 
    $isError ? '#d32f2f' : $isUser ? '#0f172a' : '#333'};
  box-shadow: ${({ $isUser }) => 
    $isUser ? '0 2px 4px rgba(0, 0, 0, 0.05)' : '0 2px 4px rgba(0, 0, 0, 0.05)'};
  border: ${({ $isUser, $isError }) => 
    $isError ? '1px solid #ffcdd2' : 
    $isUser ? '1px solid #e2e8f0' : '1px solid #f1f5f9'};
  position: relative;
  line-height: 1.5;
  transform: none !important; /* 防止任何变换 */
  
  &::before {
    content: '';
    position: absolute;
    ${({ $isUser }) => $isUser 
      ? 'right: -8px; border-left: 8px solid #e2e8f0;' 
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
  background-color: ${props => props.isUser ? 'rgba(226, 232, 240, 0.7)' : 'rgba(241, 245, 249, 0.7)'};
  color: ${props => props.isUser ? '#1e293b' : '#475569'};
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
  background-color: ${props => props.isUser ? 'rgba(226, 232, 240, 0.7)' : 'rgba(241, 245, 249, 0.7)'};
  color: ${props => props.isUser ? '#1e293b' : '#475569'};
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  margin-bottom: 8px;
  margin-right: 8px;
  
  svg {
    margin-right: 4px;
  }
`;

// 添加网页搜索标签
const WebSearchLabel = styled.div`
  display: inline-flex;
  align-items: center;
  background-color: ${props => props.isUser ? 'rgba(226, 232, 240, 0.7)' : 'rgba(241, 245, 249, 0.7)'};
  color: ${props => props.isUser ? '#1e293b' : '#475569'};
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
  border-top: 1px solid ${props => props.isUser ? 'rgba(15, 23, 42, 0.2)' : 'rgba(0, 0, 0, 0.1)'};
  font-size: 12px;
  color: ${props => props.isUser ? '#334155' : '#666'};
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
  useWebSearch = false,
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
      {/* 标签区域 */}
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
        
        {/* 网页搜索标签 */}
        {!isUser && useWebSearch && (
          <WebSearchLabel isUser={isUser}>
            <FaGlobe size={12} />
            网络搜索
          </WebSearchLabel>
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

// 更新用户消息样式
const UserBubble = styled.div`
  background-color: #f1f5f9;
  color: #0f172a;
  padding: 12px 16px;
  border-radius: 18px 18px 4px 18px;
  max-width: 100%;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  position: relative;
  transition: all 0.2s;
  border: 1px solid #e2e8f0;
  
  &:hover {
    background-color: #f8fafc;
  }
  
  .bubble-time {
    font-size: 11px;
    color: #64748b;
    text-align: right;
    margin-top: 4px;
    opacity: 0.8;
  }
`;

// 更新助手消息样式
const AssistantBubble = styled.div`
  background-color: #ffffff;
  color: #1f2937;
  padding: 12px 16px;
  border-radius: 18px 18px 18px 4px;
  max-width: 100%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #f1f5f9;
  position: relative;
  transition: all 0.2s;
  
  &:hover {
    box-shadow: 0 3px 6px rgba(0, 0, 0, 0.05);
  }
  
  pre {
    background-color: #f8fafc;
    border-radius: 6px;
    padding: 12px;
    overflow-x: auto;
    border: 1px solid #e2e8f0;
    margin: 10px 0;
  }
  
  code {
    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
    font-size: 0.9em;
  }
  
  p {
    margin-bottom: 0.75rem;
  }
  
  a {
    color: #64748b;
    text-decoration: none;
    
    &:hover {
      text-decoration: underline;
    }
  }
  
  ul, ol {
    padding-left: 1.5rem;
    margin-bottom: 1rem;
  }
  
  li {
    margin-bottom: 0.25rem;
  }
  
  .bubble-time {
    font-size: 11px;
    color: #94a3b8;
    text-align: right;
    margin-top: 4px;
    opacity: 0.8;
  }
`;

// 更新用户头像样式
const UserAvatar = styled.div`
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  margin-left: 10px;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
  
  svg {
    width: 20px;
    height: 20px;
  }
`;

// 更新助手头像样式
const AssistantAvatar = styled.div`
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: #7c3aed;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  margin-right: 10px;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
  
  svg {
    width: 20px;
    height: 20px;
  }
`;

// 更新内容容器，改善排版
const ContentContainer = styled.div`
  font-size: 15px;
  line-height: 1.6;
  word-break: break-word;
  overflow-wrap: break-word;
  
  h1, h2, h3, h4, h5, h6 {
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
    font-weight: 600;
    line-height: 1.3;
  }
  
  h1 {
    font-size: 1.5rem;
  }
  
  h2 {
    font-size: 1.3rem;
  }
  
  h3 {
    font-size: 1.2rem;
  }
  
  table {
    border-collapse: collapse;
    width: 100%;
    margin: 1rem 0;
    font-size: 0.9em;
  }
  
  th, td {
    border: 1px solid #e2e8f0;
    padding: 8px 12px;
    text-align: left;
  }
  
  th {
    background-color: #f8fafc;
    font-weight: 600;
  }
  
  tr:nth-child(even) {
    background-color: #f8fafc;
  }
`;

export default MessageBubble; 