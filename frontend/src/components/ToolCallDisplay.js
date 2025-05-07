import React, { useState } from 'react';
import styled from 'styled-components';
import { FaTools, FaChevronDown, FaChevronUp, FaCopy, FaSearch, FaExternalLinkAlt } from 'react-icons/fa';

// 工具调用容器
const ToolCallContainer = styled.div`
  margin: 10px 0;
  border-radius: 8px;
  overflow: hidden;
  background: ${props => props.isUser ? 'rgba(255, 255, 255, 0.15)' : 'rgba(74, 108, 247, 0.05)'};
  border: 1px solid ${props => props.isUser ? 'rgba(255, 255, 255, 0.2)' : 'rgba(74, 108, 247, 0.2)'};
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
`;

// 工具调用标题
const ToolCallHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: ${props => props.isUser ? 'rgba(255, 255, 255, 0.2)' : 'rgba(74, 108, 247, 0.1)'};
  color: ${props => props.isUser ? 'white' : '#333'};
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s;
  
  &:hover {
    background: ${props => props.isUser ? 'rgba(255, 255, 255, 0.25)' : 'rgba(74, 108, 247, 0.15)'};
  }
`;

// 工具名称
const ToolName = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  
  svg {
    color: ${props => props.isUser ? 'white' : '#4a6cf7'};
  }
`;

// 工具调用简短预览信息
const ToolPreview = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: ${props => props.isUser ? 'rgba(255, 255, 255, 0.9)' : '#666'};
  margin-top: 4px;
  font-style: italic;
`;

// 工具调用内容
const ToolCallContent = styled.div`
  padding: ${props => props.expanded ? '15px' : '0'};
  max-height: ${props => props.expanded ? '500px' : '0'};
  overflow: hidden;
  transition: all 0.3s ease-in-out;
`;

// 工具调用结果容器
const ResultContainer = styled.div`
  display: grid;
  grid-template-columns: auto 1fr;
  grid-gap: 10px;
`;

// 工具调用标签
const Label = styled.div`
  font-size: 13px;
  font-weight: 500;
  color: ${props => props.isUser ? 'rgba(255, 255, 255, 0.9)' : '#666'};
`;

// 工具调用值
const Value = styled.div`
  font-family: monospace;
  background: ${props => props.isUser ? 'rgba(0, 0, 0, 0.2)' : 'rgba(0, 0, 0, 0.05)'};
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 13px;
  color: ${props => props.isUser ? 'rgba(255, 255, 255, 0.9)' : '#333'};
  overflow-x: auto;
  position: relative;
  max-height: 300px;
  overflow-y: auto;
`;

// 工具结果状态显示
const ResultStatus = styled.span`
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  background-color: ${props => 
    props.isError ? (props.isUser ? 'rgba(255, 100, 100, 0.3)' : 'rgba(255, 100, 100, 0.1)') : 
    (props.isUser ? 'rgba(100, 255, 100, 0.3)' : 'rgba(100, 255, 100, 0.1)')};
  color: ${props => 
    props.isError ? (props.isUser ? 'white' : '#d32f2f') : 
    (props.isUser ? 'white' : '#2e7d32')};
  margin-left: 8px;
`;

// 获取工具类型图标
const getToolIcon = (toolName) => {
  if (toolName.includes('search')) {
    return <FaSearch />;
  }
  return <FaTools />;
};

// 获取查询预览
const getQueryPreview = (args) => {
  if (args && args.query) {
    return `"${args.query.length > 25 ? args.query.substring(0, 25) + '...' : args.query}"`;
  }
  return null;
};

/**
 * 工具调用显示组件
 * @param {Object} props 组件属性
 * @param {Object} props.data 工具调用数据
 * @param {boolean} props.isUser 是否为用户消息
 */
const ToolCallDisplay = ({ data, isUser }) => {
  // 状态和数据处理
  const [expanded, setExpanded] = useState(false);
  
  // 如果数据是字符串，尝试解析
  let toolData = data;
  if (typeof data === 'string') {
    try {
      toolData = JSON.parse(data);
    } catch (e) {
      console.warn('无法解析工具数据:', e);
    }
  }
  
  // 提取工具信息
  const toolName = toolData.name || toolData.tool_name || '未知工具';
  const args = toolData.arguments || {};
  const result = toolData.result || toolData.return || {};
  const error = toolData.error;
  const hasError = Boolean(error);
  
  // 格式化JSON为字符串
  const formatJSON = (obj) => {
    try {
      return JSON.stringify(obj, null, 2);
    } catch (e) {
      return String(obj);
    }
  };
  
  // 复制到剪贴板
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
      .then(() => console.log('复制成功'))
      .catch(err => console.error('复制失败:', err));
  };
  
  // 获取简化的显示名称
  const getDisplayName = () => {
    if (toolName.includes('/')) {
      const parts = toolName.split('/');
      return parts[parts.length - 1];
    }
    if (toolName.includes(':')) {
      const [serverId, name] = toolName.split(':', 2);
      return `${name} (${serverId})`;
    }
    return toolName;
  };
  
  // 获取简短预览
  const queryPreview = getQueryPreview(args);
  
  return (
    <ToolCallContainer isUser={isUser}>
      <ToolCallHeader 
        isUser={isUser} 
        onClick={() => setExpanded(!expanded)}
      >
        <div>
          <ToolName isUser={isUser}>
            {getToolIcon(toolName)}
            {getDisplayName()}
            {hasError && <ResultStatus isUser={isUser} isError={true}>失败</ResultStatus>}
            {!hasError && <ResultStatus isUser={isUser} isError={false}>成功</ResultStatus>}
          </ToolName>
          {queryPreview && (
            <ToolPreview isUser={isUser}>
              {queryPreview}
            </ToolPreview>
          )}
        </div>
        {expanded ? <FaChevronUp /> : <FaChevronDown />}
      </ToolCallHeader>
      
      <ToolCallContent expanded={expanded}>
        <ResultContainer>
          <Label isUser={isUser}>参数:</Label>
          <Value isUser={isUser}>
            {formatJSON(args)}
            <FaCopy 
              size={12} 
              style={{
                position: 'absolute',
                top: 6,
                right: 6,
                cursor: 'pointer',
                opacity: 0.7
              }}
              onClick={(e) => {
                e.stopPropagation();
                copyToClipboard(formatJSON(args));
              }}
            />
          </Value>
          
          <Label isUser={isUser}>{hasError ? '错误:' : '结果:'}</Label>
          <Value isUser={isUser}>
            {hasError ? error : formatJSON(result)}
            <FaCopy 
              size={12} 
              style={{
                position: 'absolute',
                top: 6,
                right: 6,
                cursor: 'pointer',
                opacity: 0.7
              }}
              onClick={(e) => {
                e.stopPropagation();
                copyToClipboard(hasError ? error : formatJSON(result));
              }}
            />
          </Value>
        </ResultContainer>
      </ToolCallContent>
    </ToolCallContainer>
  );
};

export default ToolCallDisplay; 