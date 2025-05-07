import React from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';
import styled from 'styled-components';

const MarkdownContainer = styled.div`
  & > * {
    margin-bottom: 8px;
  }
  
  & > *:last-child {
    margin-bottom: 0;
  }

  h1, h2, h3, h4, h5, h6 {
    font-weight: 600;
    line-height: 1.25;
    margin-top: 16px;
    margin-bottom: 8px;
  }
  
  h1 {
    font-size: 1.5em;
  }
  
  h2 {
    font-size: 1.3em;
  }
  
  h3 {
    font-size: 1.1em;
  }
  
  h4, h5, h6 {
    font-size: 1em;
  }
  
  p {
    margin-top: 0;
    margin-bottom: 8px;
  }
  
  ul, ol {
    padding-left: 20px;
    margin-top: 0;
    margin-bottom: 8px;
  }
  
  li {
    margin-bottom: 4px;
  }
  
  a {
    color: #4a6cf7;
    text-decoration: none;
    
    &:hover {
      text-decoration: underline;
    }
  }
  
  code {
    font-family: monospace;
    background-color: rgba(0, 0, 0, 0.05);
    padding: 2px 4px;
    border-radius: 3px;
  }
  
  pre {
    background-color: rgba(0, 0, 0, 0.05);
    padding: 12px;
    border-radius: 5px;
    overflow-x: auto;
    font-family: monospace;
    
    code {
      background-color: transparent;
      padding: 0;
    }
  }
  
  blockquote {
    border-left: 3px solid #ddd;
    padding-left: 12px;
    margin-left: 0;
    color: #555;
  }
  
  table {
    border-collapse: collapse;
    width: 100%;
    margin-bottom: 16px;
  }
  
  th, td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
  }
  
  th {
    background-color: #f0f2f5;
  }
  
  img {
    max-width: 100%;
    border-radius: 5px;
  }
`;

// 为聊天消息定制的样式
const MessageMarkdownContainer = styled(MarkdownContainer)`
  color: ${(props) => (props.isUser ? 'white' : 'inherit')};

  a {
    color: ${(props) => (props.isUser ? '#fff' : '#4a6cf7')};
  }
  
  code {
    background-color: ${(props) => (props.isUser ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.05)')};
  }
  
  pre {
    background-color: ${(props) => (props.isUser ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)')};
  }
  
  blockquote {
    border-left-color: ${(props) => (props.isUser ? 'rgba(255, 255, 255, 0.5)' : '#ddd')};
  }
`;

// 为思考内容定制的样式
const ThinkingMarkdownContainer = styled(MarkdownContainer)`
  font-style: italic;
  color: #555;
  
  pre {
    background-color: rgba(0, 0, 0, 0.03);
  }
`;

const MarkdownRenderer = ({ 
  content, 
  variant = 'default', 
  isUser = false,
  codeBlockRenderer = null // 自定义代码块渲染器
}) => {
  const Container = variant === 'message' 
    ? MessageMarkdownContainer 
    : variant === 'thinking' 
      ? ThinkingMarkdownContainer 
      : MarkdownContainer;

  // 处理自定义代码块渲染
  const components = {};
  
  if (codeBlockRenderer) {
    components.code = ({ className, children, ...props }) => {
      // 获取代码块语言
      const match = /language-(\w+)/.exec(className || '');
      const lang = match ? match[1] : '';
      
      // 使用自定义渲染器
      const customRendered = codeBlockRenderer(lang, String(children), props.node?.position?.start?.line);
      if (customRendered) {
        return customRendered;
      }
      
      // 默认渲染
      return (
        <pre className={className}>
          <code {...props}>{children}</code>
        </pre>
      );
    };
  }

  return (
    <Container isUser={isUser}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize, rehypeHighlight]}
        components={Object.keys(components).length > 0 ? components : undefined}
      >
        {content}
      </ReactMarkdown>
    </Container>
  );
};

export default MarkdownRenderer; 