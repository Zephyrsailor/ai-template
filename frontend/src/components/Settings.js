import React, { useState } from 'react';
import styled from 'styled-components';
import { IoClose } from 'react-icons/io5';
import { FiSettings, FiUser, FiInfo, FiBook, FiBell } from 'react-icons/fi';
import { FaDatabase, FaTools, FaLock, FaQuestionCircle, FaTag, FaKeyboard, FaUser } from 'react-icons/fa';
import KnowledgeManager from './KnowledgeManager';
import MCPManager from './MCPManager';

// 模态框容器 - 更新样式更像ChatGPT的设计
const ModalOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
`;

const ModalContainer = styled.div`
  width: 90%;
  height: 85%;
  max-width: 800px;
  max-height: 700px;
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
`;

const ModalHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
`;

const HeaderTitle = styled.h2`
  font-size: 20px;
  font-weight: 600;
  color: #202123;
  margin: 0;
`;

const CloseButton = styled.button`
  background: none;
  border: none;
  color: #6e6e80;
  font-size: 24px;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  
  &:hover {
    color: #202123;
  }
`;

const ModalBody = styled.div`
  display: flex;
  flex: 1;
  overflow: hidden;
`;

// 左侧导航样式 - 更新为更像ChatGPT的设计
const Sidebar = styled.nav`
  width: 200px;
  background-color: #f9f9fa;
  overflow-y: auto;
`;

const NavList = styled.ul`
  list-style: none;
  padding: 12px 0;
  margin: 0;
`;

const NavItem = styled.li`
  padding: 10px 12px;
  display: flex;
  align-items: center;
  color: ${props => props.active ? '#202123' : '#6e6e80'};
  background-color: ${props => props.active ? '#ececf1' : 'transparent'};
  cursor: pointer;
  font-weight: ${props => props.active ? '600' : 'normal'};
  font-size: 14px;
  
  &:hover {
    background-color: ${props => props.active ? '#ececf1' : '#f0f0f0'};
  }
  
  svg {
    margin-right: 12px;
    font-size: 18px;
  }
`;

// 右侧内容区域样式 - 更新为更像ChatGPT的设计
const ContentArea = styled.div`
  flex: 1;
  padding: 20px 24px;
  overflow-y: auto;
`;

const ContentSection = styled.div`
  display: ${props => props.active ? 'block' : 'none'};
`;

// 设置项样式 - 更接近ChatGPT
const SettingGroup = styled.div`
  margin-bottom: 28px;
  padding-bottom: 24px;
  border-bottom: 1px solid #f0f0f0;
  
  &:last-child {
    border-bottom: none;
  }
`;

const GroupTitle = styled.h3`
  font-size: 14px;
  font-weight: 600;
  color: #202123;
  margin-bottom: 16px;
`;

const SettingItem = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  
  &:last-child {
    margin-bottom: 0;
  }
`;

const SettingLabel = styled.div`
  flex: 1;
  
  h4 {
    margin: 0 0 4px 0;
    font-size: 16px;
    font-weight: 500;
    color: #202123;
  }
  
  p {
    margin: 0;
    font-size: 13px;
    color: #6e6e80;
  }
`;

const SettingControl = styled.div`
  margin-left: 16px;
`;

// 切换开关组件 - 更新为更像ChatGPT的设计
const Toggle = styled.div`
  position: relative;
  width: 36px;
  height: 20px;
  border-radius: 12px;
  background-color: ${props => props.checked ? '#10a37f' : '#ccc'};
  cursor: pointer;
  transition: background-color 0.2s;
  
  &:after {
    content: '';
    position: absolute;
    top: 2px;
    left: ${props => props.checked ? '16px' : '2px'};
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background-color: white;
    transition: left 0.2s;
  }
`;

// 按钮组件
const Button = styled.button`
  padding: 8px 14px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
  
  ${props => props.primary && `
    background-color: #10a37f;
    color: white;
    border: none;
    
    &:hover {
      background-color: #0c8c6d;
    }
  `}
  
  ${props => props.secondary && `
    background-color: white;
    color: #10a37f;
    border: 1px solid #10a37f;
    
    &:hover {
      background-color: #f0fdf9;
    }
  `}
  
  ${props => props.danger && `
    background-color: #f04438;
    color: white;
    border: none;
    
    &:hover {
      background-color: #d32f2f;
    }
  `}
`;

// 设置菜单项数据 - 更新为ChatGPT的设置项
const menuItems = [
  { id: 'general', label: '通用设置', icon: <FiSettings /> },
  { id: 'notifications', label: '通知', icon: <FiBell /> },
  { id: 'personalization', label: '个性化', icon: <FaUser /> },
  { id: 'knowledge-bases', label: '知识库管理', icon: <FaDatabase /> },
  { id: 'mcps-tools', label: 'MCPS工具', icon: <FaTools /> },
  { id: 'keyboard', label: '快捷键', icon: <FaKeyboard /> },
  { id: 'security', label: '安全设置', icon: <FaLock /> },
  { id: 'help', label: '帮助与FAQ', icon: <FaQuestionCircle /> },
  { id: 'release-notes', label: '版本说明', icon: <FaTag /> }
];

const Settings = ({ isOpen, onClose }) => {
  const [activeSection, setActiveSection] = useState('general');
  const [theme, setTheme] = useState('system');
  const [language, setLanguage] = useState('zh-CN');
  const [showThinking, setShowThinking] = useState(true);
  const [showSuggestions, setShowSuggestions] = useState(true);
  
  if (!isOpen) return null;
  
  // 处理点击事件，确保适当的函数调用
  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };
  
  return (
    <ModalOverlay onClick={handleOverlayClick}>
      <ModalContainer>
        <ModalHeader>
          <HeaderTitle>设置</HeaderTitle>
          <CloseButton onClick={onClose}>
            <IoClose />
          </CloseButton>
        </ModalHeader>
        
        <ModalBody>
          {/* 左侧导航 */}
          <Sidebar>
            <NavList>
              {menuItems.map(item => (
                <NavItem 
                  key={item.id} 
                  active={activeSection === item.id}
                  onClick={() => setActiveSection(item.id)}
                >
                  {item.icon}
                  {item.label}
                </NavItem>
              ))}
            </NavList>
          </Sidebar>
          
          {/* 右侧内容区域 */}
          <ContentArea>
            {/* 通用设置 */}
            <ContentSection active={activeSection === 'general'}>
              <SettingGroup>
                <GroupTitle>显示设置</GroupTitle>
                
                <SettingItem>
                  <SettingLabel>
                    <h4>主题</h4>
                    <p>选择应用的外观主题</p>
                  </SettingLabel>
                  <SettingControl>
                    <select 
                      value={theme} 
                      onChange={(e) => setTheme(e.target.value)}
                      style={{ 
                        padding: '8px 12px', 
                        borderRadius: '4px', 
                        border: '1px solid #d1d5db',
                        fontSize: '14px',
                        color: '#1f2937',
                        minWidth: '120px'
                      }}
                    >
                      <option value="light">亮色</option>
                      <option value="dark">暗色</option>
                      <option value="system">跟随系统</option>
                    </select>
                  </SettingControl>
                </SettingItem>
                
                <SettingItem>
                  <SettingLabel>
                    <h4>语言</h4>
                    <p>选择应用界面语言</p>
                  </SettingLabel>
                  <SettingControl>
                    <select 
                      value={language} 
                      onChange={(e) => setLanguage(e.target.value)}
                      style={{ 
                        padding: '8px 12px', 
                        borderRadius: '4px', 
                        border: '1px solid #d1d5db',
                        fontSize: '14px',
                        color: '#1f2937',
                        minWidth: '120px'
                      }}
                    >
                      <option value="zh-CN">中文</option>
                      <option value="en-US">English</option>
                      <option value="auto">自动检测</option>
                    </select>
                  </SettingControl>
                </SettingItem>
              </SettingGroup>
              
              <SettingGroup>
                <GroupTitle>聊天体验</GroupTitle>
                
                <SettingItem>
                  <SettingLabel>
                    <h4>显示思考过程</h4>
                    <p>AI回答问题时，显示思考过程</p>
                  </SettingLabel>
                  <SettingControl>
                    <Toggle 
                      checked={showThinking} 
                      onClick={() => setShowThinking(!showThinking)} 
                    />
                  </SettingControl>
                </SettingItem>
                
                <SettingItem>
                  <SettingLabel>
                    <h4>显示对话建议</h4>
                    <p>在聊天中显示后续对话建议</p>
                  </SettingLabel>
                  <SettingControl>
                    <Toggle 
                      checked={showSuggestions} 
                      onClick={() => setShowSuggestions(!showSuggestions)} 
                    />
                  </SettingControl>
                </SettingItem>
              </SettingGroup>
              
              <SettingGroup>
                <GroupTitle>对话管理</GroupTitle>
                
                <SettingItem>
                  <SettingLabel>
                    <h4>归档所有聊天</h4>
                    <p>将所有聊天记录移至归档</p>
                  </SettingLabel>
                  <SettingControl>
                    <Button secondary>归档全部</Button>
                  </SettingControl>
                </SettingItem>
                
                <SettingItem>
                  <SettingLabel>
                    <h4>删除所有聊天</h4>
                    <p>永久删除所有聊天记录</p>
                  </SettingLabel>
                  <SettingControl>
                    <Button danger>删除全部</Button>
                  </SettingControl>
                </SettingItem>
              </SettingGroup>
            </ContentSection>
            
            {/* 通知 */}
            <ContentSection active={activeSection === 'notifications'}>
              <h3>通知设置</h3>
              <p>该功能正在开发中</p>
            </ContentSection>
            
            {/* 个性化 */}
            <ContentSection active={activeSection === 'personalization'}>
              <h3>个性化设置</h3>
              <p>该功能正在开发中</p>
            </ContentSection>
            
            {/* 知识库管理 */}
            <ContentSection active={activeSection === 'knowledge-bases'}>
              <KnowledgeManager isInSettings={true} />
            </ContentSection>
            
            {/* MCPS工具 */}
            <ContentSection active={activeSection === 'mcps-tools'}>
              <MCPManager isInSettings={true} />
            </ContentSection>
            
            {/* 快捷键 */}
            <ContentSection active={activeSection === 'keyboard'}>
              <h3>键盘快捷键</h3>
              <p>该功能正在开发中</p>
            </ContentSection>
            
            {/* 安全设置 */}
            <ContentSection active={activeSection === 'security'}>
              <h3>安全设置</h3>
              <p>该功能正在开发中</p>
            </ContentSection>
            
            {/* 帮助与FAQ */}
            <ContentSection active={activeSection === 'help'}>
              <h3>帮助与FAQ</h3>
              <p>该功能正在开发中</p>
            </ContentSection>
            
            {/* 版本说明 */}
            <ContentSection active={activeSection === 'release-notes'}>
              <h3>版本说明</h3>
              <p>版本号：1.0.0</p>
              <p>更新日期：2025年5月8日</p>
              <p>主要更新：</p>
              <ul>
                <li>初始版本发布</li>
                <li>支持知识库管理</li>
                <li>支持MCPS工具接入</li>
                <li>流式思考和回答</li>
              </ul>
            </ContentSection>
          </ContentArea>
        </ModalBody>
      </ModalContainer>
    </ModalOverlay>
  );
};

export default Settings; 