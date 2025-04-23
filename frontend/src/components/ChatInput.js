import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';
import { 
  FaPaperPlane, 
  FaSpinner, 
  FaImage, 
  FaFileAlt, 
  FaMicrophone, 
  FaEllipsisH,
  FaTrash
} from 'react-icons/fa';

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
`;

const InputWrapper = styled.div`
  display: flex;
  position: relative;
`;

const TextareaWrapper = styled.div`
  flex: 1;
  position: relative;
  border-radius: 24px;
  background-color: #f0f2f5;
  transition: all 0.2s;
  
  &:focus-within {
    box-shadow: 0 0 0 2px rgba(74, 108, 247, 0.2);
  }
`;

const StyledTextarea = styled.textarea`
  width: 100%;
  padding: 14px 60px 14px 20px;
  border: none;
  border-radius: 24px;
  resize: none;
  font-family: inherit;
  font-size: 16px;
  background-color: transparent;
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
  const textareaRef = useRef(null);
  const MAX_CHARS = 4000;
  
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
    if (value.length <= MAX_CHARS) {
      setMessage(value);
    }
  };
  
  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message);
      setMessage('');
    }
  };
  
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  
  const isNearLimit = message.length > MAX_CHARS * 0.8;
  
  return (
    <InputContainer>
      <ToolbarContainer>
        <ToolsLeft>
          <ToolButton title="上传图片">
            <FaImage />
          </ToolButton>
          <ToolButton title="上传文件">
            <FaFileAlt />
          </ToolButton>
          <ToolButton title="语音输入">
            <FaMicrophone />
          </ToolButton>
          <ToolButton title="更多功能">
            <FaEllipsisH />
          </ToolButton>
        </ToolsLeft>
        
        <ToolsRight>
          {hasMessages && (
            <ToolButton 
              title="清除历史记录" 
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
            placeholder="输入消息..."
            disabled={disabled}
            rows={1}
          />
          {message.length > 0 && (
            <CharacterCount isNearLimit={isNearLimit}>
              {message.length}/{MAX_CHARS}
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
            <FaPaperPlane />
          )}
        </SendButton>
      </InputWrapper>
    </InputContainer>
  );
};

export default ChatInput; 