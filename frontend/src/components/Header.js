import React from 'react';
import styled from 'styled-components';
import { RiRobot2Fill } from 'react-icons/ri';

const HeaderContainer = styled.header`
  display: flex;
  align-items: center;
  padding: 16px 24px;
  background: #ffffff;
  color: #333;
  border-bottom: 1px solid #eaeaea;
`;

const Logo = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 1.2rem;
  font-weight: 600;
  color: #4a6cf7;
`;

const HeaderRight = styled.div`
  margin-left: auto;
  display: flex;
  align-items: center;
`;

const StatusIndicator = styled.span.attrs(props => ({
  className: props.className
}))`
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: ${props => props.$online ? '#4ade80' : '#d1d5db'};
  margin-right: 6px;
  ${props => props.$thinking && `
    animation: pulse 1.5s infinite;
    background-color: #f59e0b;
  `}
  
  @keyframes pulse {
    0% { opacity: 0.6; }
    50% { opacity: 1; }
    100% { opacity: 0.6; }
  }
`;

const StatusText = styled.span`
  font-size: 0.875rem;
  color: #666;
`;

function Header({ assistantName = 'AI聊天助手', isThinking = false }) {
  return (
    <HeaderContainer>
      <Logo>
        <RiRobot2Fill size={20} />
        <span>{assistantName}</span>
      </Logo>
      <HeaderRight>
        <StatusIndicator $online={true} $thinking={isThinking} />
        <StatusText>{isThinking ? "正在思考..." : "在线"}</StatusText>
      </HeaderRight>
    </HeaderContainer>
  );
}

export default Header; 