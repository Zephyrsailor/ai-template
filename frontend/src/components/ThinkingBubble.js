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
  
  ${({ $collapsed, $isThinking }) => $collapsed && $isThinking && `
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
  max-height: ${({ $collapsed }) => $collapsed ? '0' : '500px'};
  overflow: hidden;
  transition: max-height 0.4s ease-out;
  position: relative;
  
  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 30px;
    background: ${({ $hasScroll }) => $hasScroll ? 'linear-gradient(to top, rgba(241, 243, 245, 0.9), rgba(241, 243, 245, 0))' : 'transparent'};
    pointer-events: none;
    display: ${({ $collapsed, $hasScroll }) => (!$collapsed && $hasScroll) ? 'block' : 'none'};
  }
`;

const ThinkingContent = styled.div`
  padding: 16px 18px;
  color: #4a5568;
  font-size: 14px;
  line-height: 1.6;
  min-height: 60px;
  overflow-wrap: break-word;
  word-break: break-word;
  overflow-y: auto;
  max-height: 500px;
  
  &::-webkit-scrollbar {
    width: 5px;
  }
  
  &::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 5px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: #c0c0c0;
    border-radius: 5px;
  }
  
  &::-webkit-scrollbar-thumb:hover {
    background: #a0a0a0;
  }
  
  pre {
    white-space: pre-wrap;
    max-width: 100%;
    overflow-x: auto;
  }
  
  @media (max-width: 768px) {
    padding: 12px;
    font-size: 13px;
    max-height: 400px;
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

// 添加查看全文按钮样式
const ViewFullButton = styled.button`
  display: block;
  width: 100%;
  padding: 8px;
  text-align: center;
  color: #4a6cf7;
  background: #f8f9fa;
  border: none;
  border-top: 1px solid #e2e8f0;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background: #f0f4f8;
  }
`;

const ThinkingBubble = ({ content, isThinking = true, isHistorical = false }) => {
  // 默认状态逻辑：
  // - 历史思考默认折叠
  // - 当前思考（正在进行中）默认展开
  const [collapsed, setCollapsed] = useState(isHistorical);
  const [fullHeight, setFullHeight] = useState(false);
  const contentRef = useRef(null);
  const prevThinkingRef = useRef(isThinking);
  const contentUpdatedRef = useRef(false);
  const lastContentUpdateRef = useRef(Date.now());
  const [heartbeat, setHeartbeat] = useState(0);
  const [hasScroll, setHasScroll] = useState(false);
  
  // 检测内容是否需要滚动
  useEffect(() => {
    if (contentRef.current && !collapsed) {
      const contentElement = contentRef.current.querySelector('div');
      if (contentElement) {
        setHasScroll(contentElement.scrollHeight > contentElement.clientHeight);
      }
    } else {
      setHasScroll(false);
    }
  }, [content, collapsed, fullHeight]);

  // 思考过程中的心跳机制，确保长时间思考时也保持界面响应
  useEffect(() => {
    let heartbeatTimer;
    
    if (isThinking) {
      // 每2秒触发一次心跳，以保持UI响应
      heartbeatTimer = setInterval(() => {
        setHeartbeat(prev => prev + 1);
        
        // 如果内容超过10秒未更新，确保用户能看到（防止气泡过早折叠）
        const now = Date.now();
        if (now - lastContentUpdateRef.current > 10000) {
          setCollapsed(false);
        }
      }, 2000);
    }
    
    return () => {
      if (heartbeatTimer) clearInterval(heartbeatTimer);
    };
  }, [isThinking]);
  
  // 内容变化时，记录最后更新时间
  useEffect(() => {
    if (content) {
      lastContentUpdateRef.current = Date.now();
    }
  }, [content]);
  
  // 首次渲染或思考状态改变时的逻辑
  useEffect(() => {
    if (prevThinkingRef.current && !isThinking) {
      // 从思考状态变为完成状态时，标记内容已更新
      contentUpdatedRef.current = true;
      setFullHeight(false); // 重置全高显示状态
    }
    prevThinkingRef.current = isThinking;
  }, [isThinking]);
  
  // 内容更新时的处理逻辑
  useEffect(() => {
    // 如果内容为空，不做任何处理
    if (!content || content.trim().length === 0) return;
    
    // 如果是正在思考中，始终保持展开
    if (isThinking) {
      setCollapsed(false);
      
      // 自动滚动到底部，以便用户看到最新内容
      if (contentRef.current) {
        const contentElement = contentRef.current.querySelector('div');
        if (contentElement) {
          contentElement.scrollTop = contentElement.scrollHeight;
        }
      }
      return;
    }
    
    // 历史思考内容刚从空内容变为有内容时，也允许自动展开一次
    if (isHistorical && contentUpdatedRef.current) {
      setCollapsed(false);
      contentUpdatedRef.current = false;
    }
  }, [content, isThinking, isHistorical, heartbeat]);
  
  // 处理用户点击折叠/展开事件
  const handleToggleCollapse = (e) => {
    e.stopPropagation();
    setCollapsed(!collapsed);
    if (!collapsed) {
      setFullHeight(false); // 折叠时重置全高显示状态
    }
  };
  
  // 处理显示全部内容
  const handleViewFull = () => {
    setFullHeight(true);
  };
  
  const headerText = isHistorical ? "思考（历史）" : "思考过程";

  const displayContent = content || "";
  const hasContent = displayContent.trim().length > 0;
  
  // 计算内容字数
  const wordCount = displayContent ? displayContent.length : 0;
  const formattedCount = wordCount > 10000 
    ? `${Math.floor(wordCount/1000)}k+字符` 
    : wordCount > 1000 
      ? `${(wordCount/1000).toFixed(1)}k字符` 
      : `${wordCount}字符`;
  
  // 检测内容是否足够大，需要显示滚动提示
  const isLargeContent = wordCount > 3000;
  const isExtremelyLargeContent = wordCount > 8000;
  
  // 确定内容区域的样式
  const contentStyle = fullHeight ? { maxHeight: 'none' } : {};
  
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
              {!collapsed && isLargeContent && !fullHeight && " (可滚动)"}
            </WordCount>
          )}
          
          {hasContent && !isThinking && (
            <>
              <ToggleText>
                {collapsed ? "展开" : "收起"} 
              </ToggleText>
              <ToggleButton 
                onClick={handleToggleCollapse}
                $collapsed={collapsed}
              >
                {collapsed ? <FaChevronDown size={14} /> : <FaChevronUp size={14} />}
              </ToggleButton>
            </>
          )}
        </ThinkingHeader>
        
        <ThinkingContentWrapper 
          $collapsed={collapsed}
          $hasScroll={hasScroll && !fullHeight}
          ref={contentRef}
        >
          <ThinkingContent style={contentStyle}>
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
        
        {/* 对于特别长的内容，显示查看全文按钮 */}
        {!collapsed && hasScroll && isExtremelyLargeContent && !fullHeight && (
          <ViewFullButton onClick={handleViewFull}>
            查看全部内容
          </ViewFullButton>
        )}
      </ThinkingContainer>
    </ThinkingWrapper>
  );
};

export default ThinkingBubble; 