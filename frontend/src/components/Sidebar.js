import React from 'react';
import styled from 'styled-components';

const SidebarContainer = styled.div`
  width: 70px;
  height: 100vh;
  background: linear-gradient(to bottom, #4a6cf7, #5e3fd7);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0;
  color: white;
  box-shadow: 2px 0 5px rgba(0, 0, 0, 0.1);

  @media (max-width: 768px) {
    width: 60px;
  }
`;

const Logo = styled.div`
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background-color: white;
  color: #4a6cf7;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 30px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
  
  svg {
    font-size: 24px;
  }
`;

const AssistantsList = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  gap: 8px;
  flex: 1;
  overflow-y: auto;
  padding: 5px 0;
`;

const AssistantButton = styled.button.attrs(props => ({
  className: props.className,
  type: 'button'
}))`
  width: 46px;
  height: 46px;
  border-radius: 10px;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: ${({ $isActive }) => $isActive ? 'rgba(255, 255, 255, 0.2)' : 'transparent'};
  color: white;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  
  &:hover {
    background-color: rgba(255, 255, 255, 0.15);
  }
  
  &::after {
    content: '';
    position: absolute;
    left: 0;
    width: 3px;
    height: ${({ $isActive }) => $isActive ? '20px' : '0'};
    background-color: white;
    border-radius: 0 2px 2px 0;
    transition: height 0.2s;
  }
`;

const StatusDot = styled.span`
  position: absolute;
  width: 8px;
  height: 8px;
  background-color: #4ade80;
  border-radius: 50%;
  top: 6px;
  right: 6px;
  border: 1px solid rgba(255, 255, 255, 0.8);
`;

const Sidebar = ({ assistants, activeAssistant, setActiveAssistant }) => {
  return (
    <SidebarContainer>
      <Logo>
        <span>AI</span>
      </Logo>
      
      <AssistantsList>
        {assistants.map(assistant => (
          <AssistantButton
            key={assistant.id}
            $isActive={activeAssistant.id === assistant.id}
            onClick={() => setActiveAssistant(assistant)}
            title={assistant.name}
          >
            {assistant.icon}
            {assistant.id === 'ai-chat' && <StatusDot />}
          </AssistantButton>
        ))}
      </AssistantsList>
    </SidebarContainer>
  );
};

export default Sidebar; 