import React, { useState, useEffect, useRef } from 'react';
import styled from 'styled-components';
import { FaChevronDown, FaChevronUp } from 'react-icons/fa';
import { HiOutlineSparkles } from 'react-icons/hi';
import MarkdownRenderer from './MarkdownRenderer';

const ThinkingWrapper = styled.div.attrs(props => ({
  className: props.className
}))`
  width: 100%;
  opacity: ${({ $isThinking }) => ($isThinking ? 0.98 : 1)};
  margin-bottom: 12px;
  transition: all 0.3s ease;
  position: static;
`;

const ThinkingContainer = styled.div.attrs(props => ({
  className: props.className
}))`
  background-color: ${({ $isHistorical, $isCompleted }) => 
    $isCompleted ? '#f8fafc' : 
    $isHistorical ? '#f8fafc' : '#f8fafc'};
  border: 1px solid ${({ $isHistorical, $isCompleted }) => 
    $isCompleted ? '#e2e8f0' : 
    $isHistorical ? '#e2e8f0' : '#e2e8f0'};
  border-radius: 14px;
  overflow: hidden;
  box-shadow: ${({ $collapsed }) => $collapsed 
    ? '0 1px 3px rgba(0, 0, 0, 0.03)' 
    : '0 2px 5px rgba(0, 0, 0, 0.05)'};
  transition: all 0.3s ease;
  margin-left: 0;
  width: 100%;
  position: relative;
`;

const ThinkingHeader = styled.div.attrs(props => ({
  className: props.className
}))`
  display: flex;
  align-items: center;
  padding: ${({ $collapsed }) => $collapsed ? '12px 16px' : '14px 18px'};
  background-color: ${({ $isHistorical, $collapsed, $isCompleted }) => 
    $collapsed 
      ? ($isHistorical || $isCompleted ? '#f8fafc' : '#f1f5f9') 
      : ($isHistorical || $isCompleted ? '#f1f5f9' : '#f1f5f9')};
  border-bottom: ${({ $collapsed }) => $collapsed ? 'none' : '1px solid #e2e8f0'};
  cursor: pointer;
  user-select: none;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  
  &:hover {
    background-color: ${({ $isHistorical, $isCompleted }) => 
      $isHistorical || $isCompleted ? '#f1f5f9' : '#e2e8f0'};
  }
`;

const HeaderIcon = styled.div`
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: ${({ $isThinking, $isCompleted }) => 
    $isCompleted ? '#7c3aed' : 
    $isThinking ? '#7c3aed' : '#64748b'};
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-right: 12px;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  
  ${({ $collapsed, $isThinking }) => $collapsed && $isThinking && `
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    
    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(124, 58, 237, 0.5); }
      70% { box-shadow: 0 0 0 8px rgba(124, 58, 237, 0); }
      100% { box-shadow: 0 0 0 0 rgba(124, 58, 237, 0); }
    }
  `}
`;

const SpinnerIcon = styled.div`
  margin-left: 8px;
  color: #6c757d;
  display: flex;
  align-items: center;
  justify-content: center;
`;

// 更优雅的加载动画
const ThinkingProgress = styled.div`
  width: 16px;
  height: 16px;
  border-radius: 50%;
  position: relative;
  
  &:before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    border: 2px solid rgba(99, 102, 241, 0.15);
  }
  
  &:after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    border: 2px solid transparent;
    border-top-color: #6366f1;
    animation: spinner 1.2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  }
  
  @keyframes spinner {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const HeaderTitle = styled.div`
  font-size: 15px;
  font-weight: 600;
  color: #475569;
  flex-grow: 1;
  display: flex;
  align-items: center;
`;

const ToggleButton = styled.button.attrs(props => ({
  className: props.className,
  type: 'button',
  'aria-label': props.$collapsed ? '展开思考内容' : '收起思考内容'
}))`
  color: #7c3aed;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background-color: rgba(124, 58, 237, 0.1);
  flex-shrink: 0;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;
  outline: none;
  
  &:hover {
    background-color: rgba(124, 58, 237, 0.15);
    transform: scale(1.05);
  }
  
  &:focus {
    box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.2);
  }

  &:active {
    transform: scale(0.98);
  }
`;

const ToggleText = styled.span.attrs(props => ({
  className: props.className
}))`
  font-size: 14px;
  font-weight: 500;
  color: #7c3aed;
  margin-right: 8px;
`;

const CollapsedIndicator = styled.div`
  display: ${({ $collapsed }) => $collapsed ? 'flex' : 'none'};
  align-items: center;
  margin-right: 12px;
  color: #7c3aed;
  gap: 4px;
  font-size: 13px;
  
  .dot {
    width: 4px;
    height: 4px;
    background-color: #7c3aed;
    border-radius: 50%;
    margin: 0 1px;
  }
`;

const ThinkingContentWrapper = styled.div.attrs(props => ({
  className: props.className
}))`
  max-height: ${({ $collapsed }) => $collapsed ? '0' : '80vh'};
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
  color: #374151;
  font-size: 14px;
  line-height: 1.7;
  min-height: 60px;
  overflow-wrap: break-word;
  word-break: break-word;
  overflow-y: auto;
  max-height: ${props => props.$isHistorical ? '45vh' : '70vh'};
  
  &::-webkit-scrollbar {
    width: 5px;
  }
  
  &::-webkit-scrollbar-track {
    background: #f5f5f5;
    border-radius: 5px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 5px;
  }
  
  &::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
  }
  
  pre {
    white-space: pre-wrap;
    max-width: 100%;
    overflow-x: auto;
    background-color: #f8fafc;
    border-radius: 6px;
    padding: 12px;
    border: 1px solid #e2e8f0;
    margin: 12px 0;
  }
  
  code {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 13px;
    background-color: #f1f5f9;
    padding: 2px 4px;
    border-radius: 3px;
  }
  
  p {
    margin-bottom: 10px;
  }
  
  @media (max-width: 768px) {
    padding: 12px;
    font-size: 13px;
    max-height: ${props => props.$isHistorical ? '40vh' : '60vh'};
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

const ThinkingBubble = ({ 
  thinking, 
  isThinking = true, 
  isHistorical = false,
  isCompleted = false,
  autoCollapse = false,
  preserveContent = true
}) => {
  // 只在首次渲染时根据 isThinking/isCompleted/isHistorical 决定初始折叠状态，后续完全由用户控制
  const [collapsed, setCollapsed] = useState(
    autoCollapse || isHistorical || isCompleted
  );
  const [hasScroll, setHasScroll] = useState(false);
  const contentRef = useRef(null);

  // 检查内容是否需要滚动
  useEffect(() => {
    if (contentRef.current) {
      const hasOverflow = contentRef.current.scrollHeight > contentRef.current.clientHeight;
      setHasScroll(hasOverflow);
    }
  }, [thinking, collapsed]);

  // 用户可随时手动展开/收缩
  const handleToggleCollapse = (e) => {
    e.stopPropagation();
    setCollapsed(prev => !prev);
  };

  // 只要有内容或已完成/历史就显示
  if (!thinking && !isThinking && !isHistorical && !isCompleted && !preserveContent) {
    return null;
  }
  if ((isHistorical || isCompleted) && (!thinking || thinking.trim() === '') && !preserveContent) {
    return null;
  }

  // 标题逻辑优化
  const getHeaderTitle = () => {
    if (isHistorical) return '历史思考过程';
    if (isCompleted) return '思考已完成';
    if (isThinking) return '正在思考中...';
    return '思考过程';
  };

  // 判断是否显示动画
  const showThinkingAnim = isThinking && !isCompleted && !isHistorical;

  return (
    <ThinkingWrapper $isThinking={isThinking && !isCompleted && !isHistorical}>
      <ThinkingContainer 
        $collapsed={collapsed} 
        $isHistorical={isHistorical}
        $isCompleted={isCompleted}
      >
        <ThinkingHeader 
          onClick={handleToggleCollapse}
          $collapsed={collapsed}
          $isHistorical={isHistorical}
          $isCompleted={isCompleted}
        >
          <HeaderIcon 
            $isThinking={isThinking && !isCompleted && !isHistorical} 
            $collapsed={collapsed}
            $isCompleted={isCompleted}
          >
            <HiOutlineSparkles size={18} />
          </HeaderIcon>
          <HeaderTitle>
            {getHeaderTitle()}
            {(showThinkingAnim && !collapsed) && (
              <SpinnerIcon>
                <ThinkingProgress />
              </SpinnerIcon>
            )}
            {collapsed && (
              <CollapsedIndicator $collapsed={collapsed}>
                <span className="dot"></span>
                <span className="dot"></span>
                <span className="dot"></span>
              </CollapsedIndicator>
            )}
          </HeaderTitle>
          <ToggleButton 
            onClick={handleToggleCollapse}
            $collapsed={collapsed}
          >
            {collapsed ? <FaChevronDown size={14} /> : <FaChevronUp size={14} />}
          </ToggleButton>
        </ThinkingHeader>
        <ThinkingContentWrapper 
          $collapsed={collapsed} 
          $hasScroll={hasScroll}
        >
          <ThinkingContent ref={contentRef} $isHistorical={isHistorical}>
            {thinking ? (
              <MarkdownRenderer 
                content={thinking} 
                variant="thinking" 
              />
            ) : (
              <PlaceholderContent>
                {showThinkingAnim ? (
                  <ThinkingDots>
                    <ThinkingDot delay={0} />
                    <ThinkingDot delay={0.2} />
                    <ThinkingDot delay={0.4} />
                  </ThinkingDots>
                ) : (
                  <span>暂无思考内容</span>
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