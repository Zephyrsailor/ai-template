import React, { useState } from 'react';
import { HiQuestionMarkCircle, HiCog } from 'react-icons/hi';
import { IoChevronDown } from 'react-icons/io5';
import { RiRobot2Fill } from 'react-icons/ri';
import { FaCog, FaQuestionCircle, FaRegQuestionCircle, FaRegLightbulb, FaSignOutAlt, FaUser } from 'react-icons/fa';
import { IoSettingsOutline, IoSettingsSharp, IoHelpCircleOutline, IoHelpCircle } from 'react-icons/io5';
import styled from 'styled-components';
import { checkAuthStatus } from '../api/index';
import { logout } from '../api/auth';
import EnhancedLLMSelector from './EnhancedLLMSelector';

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

// 用户信息相关样式
const UserContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 24px;
  transition: background-color 0.2s;
  position: relative;
  
  &:hover {
    background-color: #f3f4f6;
  }
`;

const UserAvatar = styled.div`
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: #4B5563;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 16px;
`;

const UserName = styled.span`
  font-size: 14px;
  font-weight: 500;
  color: #1F2937;
`;

const UserMenu = styled.div`
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  width: 200px;
  z-index: 100;
  overflow: hidden;
  display: ${({ isOpen }) => isOpen ? 'block' : 'none'};
`;

const UserMenuItem = styled.div`
  padding: 10px 16px;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #4B5563;
  
  &:hover {
    background-color: #f3f4f6;
  }
  
  svg {
    font-size: 16px;
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
  onOpenSettings,
  selectedModel,
  onModelChange,
  availableModels = [],
  user = { username: 'User' },
  onLogout
}) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuRef = React.useRef(null);
  
  // 新增：点击外部关闭菜单
  React.useEffect(() => {
    if (!isUserMenuOpen) return;
    const handleClickOutside = (event) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setIsUserMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isUserMenuOpen]);

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
  
  // 点击显示认证状态
  const showAuthStatus = () => {
    const status = checkAuthStatus();
    console.log('当前认证状态:', status);
    alert(
      `认证状态:\n` +
      `Token存在: ${status.hasToken}\n` +
      `Token长度: ${status.tokenLength}\n` + 
      `请求头中有认证: ${status.hasAuthHeader}\n` +
      `认证头部: ${status.headerValue || '无'}`
    );
  };
  
  // 处理登出
  const handleLogout = () => {
    logout();
    if (onLogout) {
      onLogout();
    } else {
      // 如果没有传入登出回调，则直接刷新页面
      window.location.reload();
    }
    setIsUserMenuOpen(false); // 新增：点击后关闭菜单
  };
  
  // 获取用户头像显示文本
  const getAvatarText = () => {
    if (!user || !user.username) return '?';
    return user.username.charAt(0).toUpperCase();
  };
  
  // 新增：点击设置后关闭菜单
  const handleOpenSettings = () => {
    if (onOpenSettings) onOpenSettings();
    setIsUserMenuOpen(false);
  };

  return (
    <header className="flex items-center justify-between py-3 px-4 bg-white border-b border-gray-100 shadow-sm z-10 w-full">
      {/* 左侧部分 - LLM选择器 */}
      <div className="flex items-center">
        <EnhancedLLMSelector 
          selectedModel={selectedModel}
          onModelChange={onModelChange}
        />
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
      
      {/* 右侧部分 - 只保留用户信息，移除其他按钮 */}
      <div className="flex items-center gap-3">
        {/* 用户信息 - 始终显示，不再进行条件渲染 */}
        <div className="relative" ref={userMenuRef}>
          <UserContainer onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}>
            <UserAvatar>{getAvatarText()}</UserAvatar>
            <UserName>{user.username}</UserName>
          </UserContainer>
          {isUserMenuOpen && (
            <UserMenu isOpen={true}>
              <UserMenuItem onClick={handleOpenSettings}>
                <FaCog /> 设置
              </UserMenuItem>
              <UserMenuItem onClick={handleLogout}>
                <FaSignOutAlt /> 退出登录
              </UserMenuItem>
            </UserMenu>
          )}
        </div>
        
        {/* 调试按钮和设置按钮已移除 */}
      </div>
    </header>
  );
};

export default Header; 