import React, { useState } from 'react';
import styled from 'styled-components';
import { FaTools, FaChevronDown, FaChevronUp, FaCopy, FaSearch, FaExternalLinkAlt } from 'react-icons/fa';

// 工具调用容器
const ToolCallContainer = styled.div`
  margin: 0;
  border-radius: 8px;
  overflow: hidden;
  background: ${props => props.isUser ? 'rgba(255, 255, 255, 0.15)' : 'rgba(74, 108, 247, 0.05)'};
  border: 1px solid ${props => props.isUser ? 'rgba(255, 255, 255, 0.2)' : 'rgba(74, 108, 247, 0.2)'};
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  width: 100%;
  min-height: 80px;
  display: block;
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
  width: 100%;
  
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
    flex-shrink: 0;
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
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
`;

// 工具调用内容
const ToolCallContent = styled.div`
  padding: ${props => props.expanded ? '15px' : '0'};
  max-height: ${props => props.expanded ? '500px' : '0'};
  overflow: hidden;
  transition: all 0.3s ease-in-out;
  opacity: ${props => props.expanded ? '1' : '0'};
  width: 100%;
`;

// 工具调用结果容器
const ResultContainer = styled.div`
  display: grid;
  grid-template-columns: auto 1fr;
  grid-gap: 10px;
  width: 100%;
  overflow-x: auto;
`;

// 工具调用标签
const Label = styled.div`
  font-size: 13px;
  font-weight: 500;
  color: ${props => props.isUser ? 'rgba(255, 255, 255, 0.9)' : '#666'};
  padding: 6px 0;
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
  white-space: pre-wrap;
  word-break: break-word;
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
  display: inline-flex;
  align-items: center;
`;

// 格式化结果内容，提取有用信息
const formatResultContent = (result) => {
  if (!result) return "无结果";
  
  // 检查是否是搜索结果
  if (Array.isArray(result)) {
    return "搜索完成";
  }
  
  // 检查内容字段
  if (result.content) {
    if (Array.isArray(result.content)) {
      // 将内容项合并成文本
      const texts = result.content
        .filter(item => item.type === 'text')
        .map(item => item.text);
      
      if (texts.length > 0) {
        return texts.join("\n");
      }
    } else if (typeof result.content === 'string') {
      return result.content;
    }
  }
  
  // 检查其他常见字段
  if (result.message) return result.message;
  if (result.data) return typeof result.data === 'string' ? result.data : JSON.stringify(result.data);
  
  // 无法识别的格式，返回JSON字符串
  return JSON.stringify(result);
};

// 获取工具类型图标
const getToolIcon = (toolName) => {
  if (toolName && toolName.includes('search')) {
    return <FaSearch size={14} />;
  }
  return <FaTools size={14} />;
};

// 获取查询预览
const getQueryPreview = (args) => {
  if (!args) return null;
  
  // 处理常见参数
  if (args.query) {
    return `"${args.query.length > 25 ? args.query.substring(0, 25) + '...' : args.query}"`;
  }
  
  if (args.search_term) {
    return `"${args.search_term.length > 25 ? args.search_term.substring(0, 25) + '...' : args.search_term}"`;
  }
  
  if (args.text || args.question) {
    const text = args.text || args.question;
    return `"${text.length > 25 ? text.substring(0, 25) + '...' : text}"`;
  }
  
  // 没有找到可预览的参数
  return null;
};

// 在最外层容器加样式
const ToolCallWrapper = styled.div`
  width: 100%;
  max-width: 600px;
  min-height: 80px;
  box-sizing: border-box;
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: stretch;
  background: none;
`;

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
  // if (typeof data === 'string') {
  //   try {
  //     toolData = JSON.parse(data);
  //     console.log('工具数据(字符串解析后):', toolData); // 调试日志
  //   } catch (e) {
  //     console.warn('无法解析工具数据:', e, '原始数据:', data);
  //   }
  // } else {
  //   console.log('工具数据(对象):', toolData); // 调试日志
  // }
  
  // 提取工具信息
  const toolName = toolData?.tool_name || toolData?.name || '未知工具';
  const args = toolData?.arguments || {};
  const result = toolData?.result || toolData?.return || {};
  const error = toolData?.error;
  const hasError = Boolean(error);
  const hasResult = Boolean(result && Object.keys(result).length > 0);
  
  // console.log('工具名称:', toolName); // 调试日志
  // console.log('参数:', args); // 调试日志
  // console.log('结果:', result); // 调试日志
  // console.log('错误:', error); // 调试日志
  
  // 格式化JSON为字符串
  const formatJSON = (obj) => {
    try {
      if (obj === null || typeof obj === 'undefined') return "{}";
      return JSON.stringify(obj, null, 2);
    } catch (e) {
      console.error('JSON格式化错误:', e, '对象:', obj); // 调试错误
      return String(obj || "{}");
    }
  };
  
  // 提取结果中可能的文本内容
  let resultContent = error;
  if (!error) {
    if (hasResult) {
      resultContent = formatResultContent(result);
    } else if (typeof data.result === 'string' && data.result) {
      resultContent = data.result;
    } else if (typeof data.result === 'object' && data.result !== null) {
      resultContent = formatResultContent(data.result);
    } else if (data.return) {
      resultContent = formatResultContent(data.return);
    }
  }
  
  // 复制到剪贴板
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
      .then(() => console.log('复制成功'))
      .catch(err => console.error('复制失败:', err));
  };
  
  // 获取简化的显示名称
  const getDisplayName = () => {
    // 处理工具名称展示
    if (!toolName) return '未知工具';
    
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
    <ToolCallWrapper>
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
              {hasResult && !hasError && <ResultStatus isUser={isUser} isError={false}>成功</ResultStatus>}
              {!hasResult && !hasError && <ResultStatus isUser={isUser} isError={false}>处理中</ResultStatus>}
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
              {hasError ? error : (resultContent || formatJSON(result) || '无结果')}
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
    </ToolCallWrapper>
  );
};

export default ToolCallDisplay; 