import React, { useState, useEffect, useRef } from 'react';
import styled from 'styled-components';
import { FaRobot, FaChevronDown, FaChevronUp, FaSpinner, FaBrain } from 'react-icons/fa';
import MarkdownRenderer from './MarkdownRenderer';

const ThinkingWrapper = styled.div.attrs(props => ({
  className: props.className
}))`
  width: 100%;
  opacity: ${({ $isThinking }) => ($isThinking ? 0.98 : 1)};
  margin-bottom: 12px;
  transition: all 0.3s ease;
`;

const ThinkingContainer = styled.div.attrs(props => ({
  className: props.className
}))`
  background-color: ${({ $isHistorical }) => $isHistorical ? '#f1f3f5' : '#f5f5f5'};
  border: 1px solid ${({ $isHistorical }) => $isHistorical ? '#d1d9e6' : '#c8d3e6'};
  border-radius: 16px;
  overflow: hidden;
  box-shadow: ${({ $collapsed }) => $collapsed 
    ? '0 2px 5px rgba(0, 0, 0, 0.05)' 
    : '0 3px 10px rgba(0, 0, 0, 0.08)'};
  transition: all 0.3s ease;
`;

const ThinkingHeader = styled.div.attrs(props => ({
  className: props.className
}))`
  display: flex;
  align-items: center;
  padding: ${({ $collapsed }) => $collapsed ? '10px 16px' : '14px 18px'};
  background-color: ${({ $isHistorical, $collapsed }) => 
    $collapsed 
      ? ($isHistorical ? '#e9ecef' : '#edf2f7') 
      : ($isHistorical ? '#e2e8f0' : '#e5e9f2')};
  border-bottom: ${({ $collapsed }) => $collapsed ? 'none' : '1px solid #d1d9e6'};
  cursor: pointer;
  user-select: none;
  transition: all 0.2s ease;
  
  &:hover {
    background-color: ${({ $isHistorical }) => 
      $isHistorical ? '#dee2e6' : '#e2e8f0'};
  }
`;

const HeaderIcon = styled.div`
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: ${({ $isThinking }) => $isThinking ? '#6366f1' : '#6c757d'};
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-right: 12px;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  
  ${({ $collapsed }) => $collapsed && `
    animation: pulse 2s infinite;
    
    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.4); }
      70% { box-shadow: 0 0 0 6px rgba(99, 102, 241, 0); }
      100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0); }
    }
  `}
`;

const SpinnerIcon = styled.div`
  margin-left: 8px;
  color: #6c757d;
  animation: spin 1.5s linear infinite;
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const HeaderTitle = styled.div`
  font-size: 15px;
  font-weight: 600;
  color: #4a5568;
  flex-grow: 1;
  display: flex;
  align-items: center;
`;

const ToggleButton = styled.button.attrs(props => ({
  className: props.className,
  type: 'button',
  'aria-label': props.$collapsed ? '展开思考内容' : '收起思考内容'
}))`
  color: #4a6cf7;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: rgba(74, 108, 247, 0.1);
  flex-shrink: 0;
  transition: all 0.2s;
  border: none;
  outline: none;
  
  &:hover {
    background-color: rgba(74, 108, 247, 0.2);
    transform: scale(1.05);
  }
  
  &:focus {
    box-shadow: 0 0 0 2px rgba(74, 108, 247, 0.3);
  }
`;

const ToggleText = styled.span.attrs(props => ({
  className: props.className
}))`
  font-size: 14px;
  font-weight: 500;
  color: #4a6cf7;
  margin-right: 8px;
`;

const CollapsedIndicator = styled.div`
  display: ${({ $collapsed }) => $collapsed ? 'flex' : 'none'};
  align-items: center;
  margin-right: 12px;
  color: #6366f1;
  gap: 4px;
  font-size: 13px;
  
  .dot {
    width: 4px;
    height: 4px;
    background-color: #6366f1;
    border-radius: 50%;
    margin: 0 1px;
  }
`;

const ThinkingContentWrapper = styled.div.attrs(props => ({
  className: props.className
}))`
  max-height: ${({ $collapsed }) => $collapsed ? '0' : '700px'};
  overflow: hidden;
  transition: max-height 0.3s ease-out;
`;

const ThinkingContent = styled.div`
  padding: 16px 18px;
  color: #4a5568;
  font-size: 14px;
  line-height: 1.6;
  min-height: 60px;
  overflow-wrap: break-word;
  word-break: break-word;
  
  pre {
    white-space: pre-wrap;
    max-width: 100%;
    overflow-x: auto;
  }
  
  @media (max-width: 768px) {
    padding: 12px;
    font-size: 13px;
  }
`;

const PlaceholderContent = styled.div`
  min-height: 60px;
  width: 100%;
  display: flex;
  align-items: center;
`;

const ThinkingDots = styled.div`
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 0;
`;

const ThinkingDot = styled.div`
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #aaaaaa;
  animation: blink 1.4s infinite;
  animation-delay: ${({ delay }) => delay}s;
  
  @keyframes blink {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
  }
`;

const WordCount = styled.div`
  font-size: 12px;
  color: #718096;
  margin-left: auto;
  padding-left: 12px;
  display: ${({ $collapsed }) => $collapsed ? 'block' : 'none'};
`;

const ThinkingBubble = ({ content, isThinking = true, isHistorical = false }) => {
  // 用户控制的折叠状态
  const [userCollapsed, setUserCollapsed] = useState(isHistorical);
  // 实际折叠状态 (考虑用户操作和自动展开)
  const [collapsed, setCollapsed] = useState(isHistorical);
  const contentRef = useRef(null);
  
  // 首次渲染时，如果是历史思考内容则默认折叠
  useEffect(() => {
    if (isHistorical) {
      setUserCollapsed(true);
      setCollapsed(true);
    }
  }, []);
  
  // 当内容更新时，仅在特定条件下更新折叠状态
  useEffect(() => {
    // 只有在没有用户干预的情况下才自动展开/折叠
    // 当开始思考或内容更新时，展开显示（但不覆盖用户操作）
    if (isThinking && content && content.length > 0 && collapsed) {
      // 仅当用户没有手动收起时才自动展开
      if (!userCollapsed) {
        setCollapsed(false);
      }
    }
    
    // 思考完成且是历史内容时才折叠（不覆盖用户已手动展开的）
    if (!isThinking && isHistorical && !collapsed) {
      // 仅当用户没有手动展开时才自动折叠
      if (userCollapsed) {
        setCollapsed(true);
      }
    }
  }, [isThinking, isHistorical, content, userCollapsed]);
  
  // 处理用户点击折叠/展开事件
  const handleToggleCollapse = (e) => {
    e.stopPropagation();
    // 记录用户选择
    setUserCollapsed(!userCollapsed);
    // 实际设置折叠状态
    setCollapsed(!collapsed);
  };
  
  const headerText = isHistorical ? "思考（历史）" : "思考过程";

  const displayContent = content || "";
  const hasContent = displayContent.trim().length > 0;
  
  // 计算内容字数
  const wordCount = displayContent ? displayContent.length : 0;
  const formattedCount = wordCount > 1000 
    ? `${Math.floor(wordCount/1000)}k+字符` 
    : `${wordCount}字符`;
  
  return (
    <ThinkingWrapper $isThinking={isThinking}>
      <ThinkingContainer $isHistorical={isHistorical} $collapsed={collapsed}>
        <ThinkingHeader 
          onClick={handleToggleCollapse}
          $collapsed={collapsed}
          $isHistorical={isHistorical}
          $isThinking={isThinking}
        >
          <HeaderIcon $isThinking={isThinking} $collapsed={collapsed}>
            {isThinking ? <FaBrain size={16} /> : <FaRobot size={16} />}
          </HeaderIcon>
          <HeaderTitle>
            {headerText}
            {isThinking && (
              <SpinnerIcon>
                <FaSpinner size={14} />
              </SpinnerIcon>
            )}
          </HeaderTitle>
          
          {collapsed && hasContent && (
            <CollapsedIndicator $collapsed={collapsed}>
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </CollapsedIndicator>
          )}
          
          {hasContent && (
            <WordCount $collapsed={collapsed}>
              {formattedCount}
            </WordCount>
          )}
          
          <ToggleText onClick={handleToggleCollapse}>
            {collapsed ? "展开" : "收起"} 
          </ToggleText>
          <ToggleButton 
            onClick={handleToggleCollapse}
            $collapsed={collapsed}
          >
            {collapsed ? <FaChevronDown size={14} /> : <FaChevronUp size={14} />}
          </ToggleButton>
        </ThinkingHeader>
        
        <ThinkingContentWrapper 
          $collapsed={collapsed}
          ref={contentRef}
        >
          <ThinkingContent>
            {hasContent ? (
              <MarkdownRenderer content={displayContent} variant="thinking" />
            ) : (
              <PlaceholderContent>
                {isThinking && (
                  <ThinkingDots>
                    <ThinkingDot delay={0} />
                    <ThinkingDot delay={0.2} />
                    <ThinkingDot delay={0.4} />
                  </ThinkingDots>
                )}
              </PlaceholderContent>
            )}
          </ThinkingContent>
        </ThinkingContentWrapper>
      </ThinkingContainer>
    </ThinkingWrapper>
  );
};

export default ThinkingBubble; 