import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';
import { 
  FaSpinner, 
  FaTrash,
  FaGlobe
} from 'react-icons/fa';
import KnowledgeSelector from './KnowledgeSelector';
import { MdSend } from 'react-icons/md';
import MCPServerSelector from './MCPServerSelector';
const InputContainer = styled.div`
  display: flex;
  flex-direction: column;
  padding: 15px 20px;
  background-color: white;
  border-top: 1px solid #e6e6e6;
  position: relative;
`;

const ToolbarContainer = styled.div`
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 0 10px;
`;

const ToolsLeft = styled.div`
  display: flex;
  gap: 16px;
`;

const ToolsRight = styled.div`
  display: flex;
  gap: 16px;
`;

const ToolButton = styled.button`
  background: none;
  border: none;
  font-size: 18px;
  color: #666;
  cursor: pointer;
  display: flex;
  align-items: center;
  padding: 5px;
  border-radius: 8px;
  transition: all 0.2s;
  
  &:hover {
    color: #4a6cf7;
    background-color: #f0f2f5;
  }
  
  &.active {
    color: #4a6cf7;
    background-color: #f0f5ff;
  }
`;

const InputWrapper = styled.div`
  display: flex;
  position: relative;
  align-items: center;
  border: 1px solid #e6e6e6;
  border-radius: 8px;
  background-color: #f5f5f5;
`;

const TextareaWrapper = styled.div`
  flex: 1;
  position: relative;
  transition: all 0.2s;
`;

const StyledTextarea = styled.textarea`
  width: 100%;
  padding: 14px 60px 14px 20px;
  border: none;
  background-color: transparent;
  resize: none;
  font-family: inherit;
  font-size: 16px;
  outline: none;
  max-height: 120px;
  min-height: 46px;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: break-word;
  
  &::placeholder {
    color: #aaa;
  }
`;

const ToolbarInner = styled.div`
  display: flex;
  align-items: center;
  padding: 5px;
  gap: 4px;
  position: absolute;
  left: 5px;
  bottom: -40px;
`;

const InnerToolButton = styled.button`
  background: none;
  border: none;
  font-size: 16px;
  color: #666;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  padding: 0;
  transition: all 0.2s;
  
  &:hover {
    color: #4a6cf7;
    background-color: #efefef;
  }
`;

const SendButton = styled.button`
  position: absolute;
  right: 10px;
  bottom: 50%;
  transform: translateY(50%);
  background-color: ${props => props.disabled ? '#d1d5db' : '#4a6cf7'};
  color: white;
  border: none;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: ${props => props.disabled ? 'not-allowed' : 'pointer'};
  transition: background-color 0.2s;
  
  &:hover:not(:disabled) {
    background-color: #3a57d7;
  }
  
  .icon-spin {
    animation: spin 1s linear infinite;
  }
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const CharacterCount = styled.div`
  position: absolute;
  right: 60px;
  bottom: 12px;
  font-size: 12px;
  color: ${props => props.isNearLimit ? '#ff9800' : '#aaa'};
`;

const ChatInput = ({ onSendMessage, disabled, onClearHistory, hasMessages }) => {
  const [message, setMessage] = useState('');
  const [selectedKbs, setSelectedKbs] = useState([]);
  const [selectedServers, setSelectedServers] = useState([]);
  const textareaRef = useRef(null);
  const maxLength = 4000;
  
  // 自动调整文本框高度
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, [message]);
  
  const handleChange = (e) => {
    const value = e.target.value;
    if (value.length <= maxLength) {
      setMessage(value);
    }
  };
  
  const handleSend = () => {
    if (message.trim() && !disabled) {
      // 传递选中的知识库ID和MCP服务器ID
      onSendMessage(message, selectedKbs, selectedServers);
      setMessage('');
    }
  };
  
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  
  const isNearLimit = message.length > maxLength * 0.8;
  
  return (
    <InputContainer>
      <ToolbarContainer>
        <ToolsLeft>
        </ToolsLeft>
        
        <ToolsRight>
          {hasMessages && (
            <ToolButton 
              title="清空历史记录" 
              onClick={onClearHistory}
              style={{ color: '#d32f2f' }}
            >
              <FaTrash />
            </ToolButton>
          )}
        </ToolsRight>
      </ToolbarContainer>
      
      <InputWrapper>
        <TextareaWrapper>
          <StyledTextarea
            ref={textareaRef}
            value={message}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="在这里输入消息..."
            disabled={disabled}
            rows={1}
          />
          {message.length > 0 && (
            <CharacterCount isNearLimit={isNearLimit}>
              {message.length}/{maxLength}
            </CharacterCount>
          )}
        </TextareaWrapper>
        
        <SendButton 
          onClick={handleSend} 
          disabled={!message.trim() || disabled}
        >
          {disabled ? (
            <FaSpinner className="icon-spin" />
          ) : (
            <MdSend />
          )}
        </SendButton>
      </InputWrapper>
      
      <ToolbarInner>
        <KnowledgeSelector 
          selectedKbs={selectedKbs}
          onChange={setSelectedKbs}
        />
        <InnerToolButton title="互联网搜索">
          <FaGlobe />
        </InnerToolButton>
        <MCPServerSelector 
          selectedServers={selectedServers}
          onChange={setSelectedServers}
        />
      </ToolbarInner>
    </InputContainer>
  );
};

export default ChatInput; 