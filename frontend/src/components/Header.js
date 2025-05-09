import React, { useState } from 'react';
import { HiQuestionMarkCircle, HiCog } from 'react-icons/hi';
import { IoChevronDown } from 'react-icons/io5';
import { RiRobot2Fill } from 'react-icons/ri';
import { FaCog, FaQuestionCircle, FaRegQuestionCircle, FaRegLightbulb } from 'react-icons/fa';
import { IoSettingsOutline, IoSettingsSharp, IoHelpCircleOutline, IoHelpCircle } from 'react-icons/io5';
import styled from 'styled-components';

// Common styled components that can be reused across the application
export const TooltipContainer = styled.div`
  position: relative;
  display: inline-flex;
`;

export const Tooltip = styled.div`
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  background-color: #1F2937;
  color: white;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.2s, visibility 0.2s;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  
  &:before {
    content: '';
    position: absolute;
    bottom: 100%;
    right: 10px;
    border-width: 6px;
    border-style: solid;
    border-color: transparent transparent #1F2937 transparent;
  }
  
  ${TooltipContainer}:hover & {
    opacity: 1;
    visibility: visible;
  }
`;

export const HeaderIcon = styled.button`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: none;
  border: none;
  color: #6B7280;
  font-size: 18px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
  &:hover {
    background: #f3f4f6;
    color: #2563eb;
  }
`;

// Component-specific styled components
const ModelSelector = styled.div`
  position: relative;
  display: flex;
  align-items: center;
  margin-right: 12px;
`;

const ModelButton = styled.button`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background-color: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background-color: #e2e8f0;
  }
  
  svg {
    color: #64748b;
  }
`;

const ModelDropdown = styled.div`
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 8px;
  background-color: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  width: 200px;
  z-index: 100;
  overflow: hidden;
  display: ${({ isOpen }) => isOpen ? 'block' : 'none'};
`;

const ModelOption = styled.div`
  padding: 10px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
  
  &:hover {
    background-color: #f1f5f9;
  }
  
  ${({ isSelected }) => isSelected && `
    background-color: #eff6ff;
    color: #2563eb;
    font-weight: 500;
  `}
`;

const Header = ({ 
  assistantName = 'AI 助手', 
  isThinking = false, 
  userName = 'Zephyr',
  onOpenSettings,
  selectedModel,
  onModelChange,
  availableModels = []
}) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  
  const handleDropdownToggle = () => {
    setIsDropdownOpen(!isDropdownOpen);
  };
  
  const handleModelSelect = (model) => {
    onModelChange(model);
    setIsDropdownOpen(false);
  };
  
  const handleHelpClick = () => {
    // 未来可以实现打开帮助对话框
    alert('帮助功能正在开发中...');
  };
  
  return (
    <header className="flex items-center justify-between py-3 px-4 bg-white border-b border-gray-100 shadow-sm z-10">
      {/* 左侧部分 - 空白或者可以放置其他元素 */}
      <div className="flex items-center">
        {/* 移除了AI助手标题和模型选择器 */}
      </div>
      
      {/* 中间部分 - 状态指示器 */}
      <div className="flex-grow flex justify-center">
        <span className={`inline-flex items-center text-xs ${isThinking ? 'text-purple-600' : 'text-green-600'}`}>
          <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${
            isThinking 
              ? 'bg-purple-500 animate-pulse' 
              : 'bg-green-500'
          }`}></span>
          {isThinking ? '思考中' : '在线'}
        </span>
      </div>
      
      {/* 右侧部分 - 用户控制按钮 */}
      <div className="flex items-center gap-3">
        <TooltipContainer>
          <HeaderIcon onClick={handleHelpClick}>
            <IoHelpCircleOutline size={22} />
          </HeaderIcon>
          <Tooltip>
            <p style={{ margin: '0 0 4px 0', fontWeight: 'bold' }}>帮助提示</p>
            <p style={{ margin: '0 0 4px 0' }}>• 使用"/"可快速使用系统提示词</p>
            <p style={{ margin: '0 0 4px 0' }}>• 右侧知识库可上传文档供AI参考</p>
            <p style={{ margin: '0' }}>• 点击此图标查看更多帮助信息</p>
          </Tooltip>
        </TooltipContainer>
        <HeaderIcon onClick={onOpenSettings}>
          <IoSettingsOutline size={22} />
        </HeaderIcon>
      </div>
    </header>
  );
};

export default Header; 