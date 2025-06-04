import React, { useState, useEffect, useRef, useCallback } from 'react';
import styled from 'styled-components';
import { FaSearch, FaServer, FaSync } from 'react-icons/fa';
import { fetchMCPServers } from '../api';

// 添加旋转动画的CSS
const GlobalStyle = styled.div`
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;

// 样式定义
const ServerContainer = styled.div`
  position: relative;
`;

const ServerButton = styled.button`
  background: none;
  border: none;
  font-size: 16px;
  color: ${props => props.active ? '#4a6cf7' : '#666'};
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

const BadgeCount = styled.span`
  background-color: #4a6cf7;
  color: white;
  border-radius: 50%;
  min-width: 14px;
  height: 14px;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: absolute;
  top: -2px;
  right: -2px;
  padding: 0 2px;
`;

const Dropdown = styled.div`
  position: absolute;
  bottom: calc(100% + 5px);
  left: 0;
  width: 280px;
  max-height: 350px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  overflow: hidden;
  display: flex;
  flex-direction: column;
`;

const DropdownHeader = styled.div`
  padding: 10px 12px;
  border-bottom: 1px solid #eee;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const SearchBox = styled.div`
  padding: 8px 12px;
  border-bottom: 1px solid #eee;
  position: relative;
`;

const SearchInput = styled.input`
  width: 100%;
  padding: 8px 12px 8px 32px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  
  &:focus {
    border-color: #4a6cf7;
  }
`;

const SearchIcon = styled.div`
  position: absolute;
  left: 22px;
  top: 50%;
  transform: translateY(-50%);
  color: #888;
`;

const ServerList = styled.div`
  overflow-y: auto;
  max-height: 250px;
  
  &::-webkit-scrollbar {
    width: 5px;
  }
  
  &::-webkit-scrollbar-thumb {
    background-color: #ddd;
    border-radius: 5px;
  }
`;

const ServerItem = styled.label`
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #f5f5f5;
  
  &:hover {
    background-color: #f9f9f9;
  }
`;

const CheckboxInput = styled.input`
  margin-right: 10px;
  cursor: pointer;
  width: 16px;
  height: 16px;
`;

const ServerInfo = styled.div`
  display: flex;
  flex-direction: column;
  flex: 1;
`;

const ServerName = styled.div`
  display: flex;
  align-items: center;
`;

const StatusIndicator = styled.div`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-left: 8px;
  background-color: ${props => props.active ? '#4CAF50' : '#ccc'};
`;

const ServerDescription = styled.div`
  font-size: 12px;
  color: #888;
  margin-top: 2px;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
`;

const EmptyState = styled.div`
  padding: 20px;
  text-align: center;
  color: #888;
`;

const LoadingState = styled.div`
  padding: 20px;
  text-align: center;
  color: #888;
`;

const SelectAllLabel = styled.label`
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #eee;
  background-color: #f5f5f5;
  font-weight: 500;
  
  &:hover {
    background-color: #f0f0f0;
  }
`;

const MCPServerSelector = ({ selectedServers = [], onChange }) => {
  // 完全使用内部状态，不依赖props更新
  const [isOpen, setIsOpen] = useState(false);
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selected, setSelected] = useState(selectedServers || []);
  const dropdownRef = useRef(null);
  
  // 只在初始化时同步一次props，然后独立管理状态
  useEffect(() => {
    setSelected(selectedServers || []);
  }, []); // 仅在挂载时执行一次
  
  // 防止state和props的循环依赖
  const emitChange = useCallback((newSelected) => {
    // 避免不必要的props更新
    if (JSON.stringify(newSelected) !== JSON.stringify(selectedServers)) {
      if (typeof onChange === 'function') {
        onChange(newSelected);
      }
    }
  }, [onChange, selectedServers]);
  
  // 加载MCP服务器
  const loadMCPServers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchMCPServers(true);
      if (data?.code === 200 && Array.isArray(data.data)) {
        setServers(data.data);
      } else {
        console.error('MCP servers data is not in expected format:', data);
        setServers([]);
      }
    } catch (error) {
      console.error('Failed to load MCP servers:', error);
      setServers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMCPServers();
  }, [loadMCPServers]);

  // 监听设置页面关闭事件，自动刷新MCP服务器列表
  useEffect(() => {
    const handleSettingsClosed = (event) => {
      console.log('设置页面已关闭，自动刷新MCP服务器列表', event.detail);
      loadMCPServers();
    };

    // 添加事件监听器
    window.addEventListener('settingsClosed', handleSettingsClosed);

    // 清理函数
    return () => {
      window.removeEventListener('settingsClosed', handleSettingsClosed);
    };
  }, [loadMCPServers]);

  // 手动刷新服务器列表
  const handleRefresh = useCallback(() => {
    loadMCPServers();
  }, [loadMCPServers]);
  
  // 关闭下拉时点击外部
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);
  
  // 根据搜索查询过滤服务器
  const filteredServers = Array.isArray(servers) 
    ? servers.filter(server => 
        server.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (server.description && server.description.toLowerCase().includes(searchQuery.toLowerCase())))
    : [];
  
  // 处理勾选变化 - 改进版
  const handleCheckboxChange = (serverId, isChecked) => {
    console.log('Checkbox changed:', serverId, isChecked);
    
    let newSelected;
    if (isChecked) {
      // 仅当不存在时才添加
      if (!selected.includes(serverId)) {
        newSelected = [...selected, serverId];
      } else {
        newSelected = [...selected]; // 不变
      }
    } else {
      newSelected = selected.filter(id => id !== serverId);
    }
    
    console.log('New selected state:', newSelected);
    
    // 更新本地状态
    setSelected(newSelected);
    // 通知父组件
    emitChange(newSelected);
  };
  
  // 处理全选/取消全选 - 改进版
  const handleSelectAll = (isChecked) => {
    console.log('Select all changed:', isChecked);
    
    let newSelected;
    if (isChecked) {
      // 合并现有选择和可见选择
      const visibleServerIds = filteredServers.map(server => server.id);
      newSelected = [...new Set([...selected, ...visibleServerIds])];
    } else {
      // 仅移除可见项
      const visibleServerIds = new Set(filteredServers.map(server => server.id));
      newSelected = selected.filter(id => !visibleServerIds.has(id));
    }
    
    console.log('New selected state after select all:', newSelected);
    
    // 更新本地状态
    setSelected(newSelected);
    // 通知父组件
    emitChange(newSelected);
  };
  
  // 判断当前可见项是否全选
  const isAllSelected = 
    filteredServers.length > 0 && 
    filteredServers.every(server => selected.includes(server.id));
  
  // 为避免冲突，使用唯一ID前缀
  const checkboxIdPrefix = "mcp-server-";
  
  return (
    <GlobalStyle>
      <ServerContainer ref={dropdownRef}>
        <ServerButton 
          onClick={() => setIsOpen(!isOpen)}
          active={isOpen || selected.length > 0}
          title="选择MCP服务器"
        >
          <FaServer />
          {selected.length > 0 && <BadgeCount>{selected.length}</BadgeCount>}
        </ServerButton>
        
        {isOpen && (
          <Dropdown>
            <DropdownHeader>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                <div>
                  MCP服务器
                  <small style={{ fontSize: '10px', color: '#888', marginLeft: '8px' }}>
                    已选: {selected.length}
                  </small>
                </div>
                <button
                  onClick={handleRefresh}
                  disabled={loading}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#666',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    padding: '4px',
                    borderRadius: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    fontSize: '12px'
                  }}
                  title="刷新服务器列表"
                >
                  <FaSync style={{ 
                    marginRight: '4px', 
                    animation: loading ? 'spin 1s linear infinite' : 'none' 
                  }} />
                  刷新
                </button>
              </div>
            </DropdownHeader>
            
            <SearchBox>
              <SearchIcon>
                <FaSearch size={14} />
              </SearchIcon>
              <SearchInput
                placeholder="搜索服务器"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </SearchBox>
            
            {loading ? (
              <LoadingState>加载中...</LoadingState>
            ) : (
              <>
                {filteredServers.length > 0 ? (
                  <ServerList>
                    <SelectAllLabel>
                      <CheckboxInput 
                        id={`${checkboxIdPrefix}select-all`}
                        type="checkbox"
                        checked={isAllSelected}
                        onChange={(e) => handleSelectAll(e.target.checked)}
                      />
                      <span>全选</span>
                    </SelectAllLabel>
                    
                    {filteredServers.map(server => (
                      <ServerItem key={server.id}>
                        <CheckboxInput 
                          id={`${checkboxIdPrefix}${server.id}`}
                          type="checkbox"
                          checked={selected.includes(server.id)}
                          onChange={(e) => handleCheckboxChange(server.id, e.target.checked)}
                        />
                        <ServerInfo>
                          <ServerName>
                            {server.name}
                            <StatusIndicator active={server.active} />
                          </ServerName>
                          {server.description && (
                            <ServerDescription>{server.description}</ServerDescription>
                          )}
                        </ServerInfo>
                      </ServerItem>
                    ))}
                  </ServerList>
                ) : (
                  <EmptyState>
                    {Array.isArray(servers) && servers.length === 0 
                      ? "没有可用的MCP服务器" 
                      : "无搜索结果"}
                  </EmptyState>
                )}
              </>
            )}
          </Dropdown>
        )}
      </ServerContainer>
    </GlobalStyle>
  );
};

export default MCPServerSelector; 