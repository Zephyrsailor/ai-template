import React, { createContext, useContext, useState, useCallback } from 'react';

// 创建MCP上下文
const MCPContext = createContext();

// MCP提供者组件
export function MCPProvider({ children }) {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // 触发MCP刷新的函数
  const triggerMCPRefresh = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
  }, []);

  const value = {
    refreshTrigger,
    triggerMCPRefresh
  };

  return (
    <MCPContext.Provider value={value}>
      {children}
    </MCPContext.Provider>
  );
}

// 使用MCP上下文的Hook
export function useMCP() {
  const context = useContext(MCPContext);
  if (!context) {
    throw new Error('useMCP must be used within a MCPProvider');
  }
  return context;
} 