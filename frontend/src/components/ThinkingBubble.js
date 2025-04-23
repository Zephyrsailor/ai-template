import React, { useState, useEffect, useRef } from 'react';
import styled from 'styled-components';
import { FaRobot, FaChevronDown, FaChevronUp, FaSpinner } from 'react-icons/fa';
import MarkdownRenderer from './MarkdownRenderer';

const ThinkingWrapper = styled.div.attrs(props => ({
  className: props.className
}))`
  width: 100%;
  opacity: ${({ $isThinking }) => ($isThinking ? 0.98 : 1)};
  margin-bottom: 8px;
`;

const ThinkingContainer = styled.div.attrs(props => ({
  className: props.className
}))`
  background-color: ${({ $isHistorical }) => $isHistorical ? '#f1f3f5' : '#f5f5f5'};
  border: 1px solid ${({ $isHistorical }) => $isHistorical ? '#d1d9e6' : '#c8d3e6'};
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
`;

const ThinkingHeader = styled.div.attrs(props => ({
  className: props.className
}))`
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background-color: ${({ $isHistorical }) => $isHistorical ? '#e9ecef' : '#edf2f7'};
  border-bottom: ${({ $collapsed }) => $collapsed ? 'none' : '1px solid #d1d9e6'};
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s ease;
  
  &:hover {
    background-color: ${({ $isHistorical }) => 
      $isHistorical ? '#dee2e6' : '#e2e8f0'};
  }
`;

const HeaderIcon = styled.div`
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background-color: #6c757d;
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-right: 10px;
  flex-shrink: 0;
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
  font-size: 14px;
  font-weight: 600;
  color: #4a5568;
  flex-grow: 1;
  display: flex;
  align-items: center;
`;

const ToggleButton = styled.div.attrs(props => ({
  className: props.className
}))`
  color: #4a6cf7;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background-color: rgba(74, 108, 247, 0.1);
  flex-shrink: 0;
  transition: all 0.2s;
  
  &:hover {
    background-color: rgba(74, 108, 247, 0.2);
    transform: scale(1.05);
  }
`;

const ToggleText = styled.span.attrs(props => ({
  className: props.className
}))`
  font-size: 13px;
  font-weight: 500;
  color: #4a6cf7;
  margin-right: 8px;
`;

const ThinkingContentWrapper = styled.div.attrs(props => ({
  className: props.className
}))`
  max-height: ${({ $collapsed }) => $collapsed ? '0' : '700px'};
  overflow: hidden;
  transition: max-height 0.5s ease-out;
`;

const ThinkingContent = styled.div`
  padding: 16px;
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

const ThinkingBubble = ({ content, isThinking = true, isHistorical = false }) => {
  const [collapsed, setCollapsed] = useState(isHistorical);
  const contentRef = useRef(null);
  
  useEffect(() => {
    if (isThinking && content && content.length > 0) {
      setCollapsed(false);
    }
    
    if (!isThinking && isHistorical) {
      setCollapsed(true);
    }
  }, [isThinking, isHistorical, content]);
  
  const toggleCollapse = () => {
    setCollapsed(!collapsed);
  };
  
  const headerText = isHistorical ? "思考（历史）" : "思考过程";

  const displayContent = content || "";
  const hasContent = displayContent.trim().length > 0;
  
  return (
    <ThinkingWrapper $isThinking={isThinking}>
      <ThinkingContainer $isHistorical={isHistorical}>
        <ThinkingHeader 
          onClick={toggleCollapse} 
          $collapsed={collapsed}
          $isHistorical={isHistorical}
          $isThinking={isThinking}
        >
          <HeaderIcon>
            <FaRobot size={16} />
          </HeaderIcon>
          <HeaderTitle>
            {headerText}
            {isThinking && (
              <SpinnerIcon>
                <FaSpinner size={14} />
              </SpinnerIcon>
            )}
          </HeaderTitle>
          <ToggleText>
            {collapsed ? "展开" : "收起"} 
          </ToggleText>
          <ToggleButton>
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