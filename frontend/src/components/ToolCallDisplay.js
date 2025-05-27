import React, { useState } from 'react';
import styled from 'styled-components';
import { FaTools, FaChevronDown, FaChevronUp, FaCopy, FaSearch, FaExternalLinkAlt } from 'react-icons/fa';

// 工具调用容器 - 参考Claude/ChatGPT的紧凑设计
const ToolCallContainer = styled.div`
  margin: 8px 0;
  border-radius: 8px;
  overflow: hidden;
  background: ${props => props.isUser ? 'rgba(255, 255, 255, 0.1)' : '#f8fafc'};
  border: 1px solid ${props => props.isUser ? 'rgba(255, 255, 255, 0.2)' : '#e2e8f0'};
  font-size: 13px;
  transition: all 0.2s ease;
  
  &:hover {
    border-color: ${props => props.isUser ? 'rgba(255, 255, 255, 0.3)' : '#cbd5e1'};
  }
`;

// 工具调用标题 - 更紧凑的设计
const ToolCallHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: ${props => props.isUser ? 'rgba(255, 255, 255, 0.15)' : '#f1f5f9'};
  color: ${props => props.isUser ? 'white' : '#475569'};
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s;
  border-bottom: ${props => props.expanded ? '1px solid #e2e8f0' : 'none'};
  
  &:hover {
    background: ${props => props.isUser ? 'rgba(255, 255, 255, 0.2)' : '#e2e8f0'};
  }
`;

// 工具名称 - 简化设计
const ToolName = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  font-size: 13px;
  
  svg {
    color: ${props => props.isUser ? 'white' : '#64748b'};
    flex-shrink: 0;
    font-size: 12px;
  }
`;

// 工具调用简短预览信息
const ToolPreview = styled.div`
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: ${props => props.isUser ? 'rgba(255, 255, 255, 0.8)' : '#64748b'};
  margin-left: 18px;
  font-style: italic;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 250px;
`;

// 工具调用内容 - 去掉多余padding
const ToolCallContent = styled.div`
  padding: ${props => props.expanded ? '12px' : '0'};
  max-height: ${props => props.expanded ? '300px' : '0'};
  overflow: hidden;
  transition: all 0.3s ease-in-out;
  opacity: ${props => props.expanded ? '1' : '0'};
  background: ${props => props.isUser ? 'rgba(0, 0, 0, 0.1)' : 'white'};
`;

// 工具调用结果容器 - 简化布局
const ResultContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

// 工具调用标签 - 更小的标签
const Label = styled.div`
  font-size: 11px;
  font-weight: 600;
  color: ${props => props.isUser ? 'rgba(255, 255, 255, 0.9)' : '#64748b'};
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
`;

// 工具调用值 - 紧凑设计
const Value = styled.div`
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
  background: ${props => props.isUser ? 'rgba(0, 0, 0, 0.2)' : '#f8fafc'};
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12px;
  color: ${props => props.isUser ? 'rgba(255, 255, 255, 0.9)' : '#374151'};
  overflow-x: auto;
  position: relative;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid ${props => props.isUser ? 'rgba(255, 255, 255, 0.1)' : '#e5e7eb'};
  line-height: 1.4;
`;

// 工具结果状态显示 - 更小的徽章
const ResultStatus = styled.span`
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 500;
  background-color: ${props => 
    props.isError ? '#fef2f2' : '#f0fdf4'};
  color: ${props => 
    props.isError ? '#dc2626' : '#16a34a'};
  border: 1px solid ${props => 
    props.isError ? '#fecaca' : '#bbf7d0'};
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

// 在最外层容器加样式 - 去掉多余margin
const ToolCallWrapper = styled.div`
  width: 100%;
  box-sizing: border-box;
  margin: 4px 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: stretch;
`;

/**
 * 工具调用显示组件
 * @param {Object} props 组件属性
 * @param {Object} props.data 工具调用数据
 * @param {boolean} props.isUser 是否为用户消息
 */
const ToolCallDisplay = ({ data, isUser, compact = false }) => {
  // 状态和数据处理 - 默认收起，用户可以点击展开查看详情
  const [expanded, setExpanded] = useState(false); // 默认收起
  
  // 如果数据是字符串，尝试解析
  let toolData = data;
  
  // 提取工具信息
  const toolName = toolData?.tool_name || toolData?.name || '未知工具';
  const args = toolData?.arguments || {};
  const result = toolData?.result || toolData?.return || {};
  const error = toolData?.error;
  const hasError = Boolean(error);
  const hasResult = Boolean(result && Object.keys(result).length > 0);
  
  // 格式化JSON为字符串
  const formatJSON = (obj) => {
    try {
      if (obj === null || typeof obj === 'undefined') return "{}";
      return JSON.stringify(obj, null, 2);
    } catch (e) {
      console.error('JSON格式化错误:', e, '对象:', obj);
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
  
  // 如果是 compact 模式，返回简化版本
  if (compact) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: '8px',
        padding: '6px 0',
        fontSize: '13px',
        color: '#6b7280'
      }}>
        {getToolIcon(toolName)}
        <span style={{ fontWeight: '500' }}>{getDisplayName()}</span>
        {queryPreview && <span style={{ fontStyle: 'italic' }}>{queryPreview}</span>}
        {hasError && <span style={{ color: '#dc2626' }}>失败</span>}
        {hasResult && !hasError && <span style={{ color: '#059669' }}>成功</span>}
        {!hasResult && !hasError && <span style={{ color: '#d97706' }}>处理中</span>}
      </div>
    );
  }
  
  return (
    <ToolCallWrapper>
      <ToolCallContainer isUser={isUser} compact={compact}>
        <ToolCallHeader 
          isUser={isUser} 
          expanded={expanded}
          onClick={() => setExpanded(!expanded)}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <ToolName isUser={isUser}>
              {getToolIcon(toolName)}
              {getDisplayName()}
              {hasError && <ResultStatus isError={true}>失败</ResultStatus>}
              {hasResult && !hasError && <ResultStatus isError={false}>成功</ResultStatus>}
              {!hasResult && !hasError && <ResultStatus isError={false}>处理中</ResultStatus>}
            </ToolName>
            {/* 只在展开时显示查询预览 */}
            {expanded && queryPreview && (
              <ToolPreview isUser={isUser}>
                {queryPreview}
              </ToolPreview>
            )}
          </div>
          <div style={{ flexShrink: 0, marginLeft: '8px' }}>
            {expanded ? <FaChevronUp size={12} /> : <FaChevronDown size={12} />}
          </div>
        </ToolCallHeader>
        
        <ToolCallContent expanded={expanded} isUser={isUser}>
          <ResultContainer>
            {/* 只在有参数且参数不为空时显示 */}
            {Object.keys(args).length > 0 && (
              <div>
                <Label isUser={isUser}>参数</Label>
                <Value isUser={isUser}>
                  {formatJSON(args)}
                  <FaCopy 
                    size={10} 
                    style={{
                      position: 'absolute',
                      top: 6,
                      right: 6,
                      cursor: 'pointer',
                      opacity: 0.6,
                      transition: 'opacity 0.2s'
                    }}
                    onMouseEnter={(e) => e.target.style.opacity = '1'}
                    onMouseLeave={(e) => e.target.style.opacity = '0.6'}
                    onClick={(e) => {
                      e.stopPropagation();
                      copyToClipboard(formatJSON(args));
                    }}
                  />
                </Value>
              </div>
            )}
            
            {/* 显示结果或错误 */}
            {(hasResult || hasError) && (
              <div>
                <Label isUser={isUser}>{hasError ? '错误' : '结果'}</Label>
                <Value isUser={isUser}>
                  {hasError ? error : (resultContent || formatJSON(result) || '无结果')}
                  <FaCopy 
                    size={10} 
                    style={{
                      position: 'absolute',
                      top: 6,
                      right: 6,
                      cursor: 'pointer',
                      opacity: 0.6,
                      transition: 'opacity 0.2s'
                    }}
                    onMouseEnter={(e) => e.target.style.opacity = '1'}
                    onMouseLeave={(e) => e.target.style.opacity = '0.6'}
                    onClick={(e) => {
                      e.stopPropagation();
                      copyToClipboard(hasError ? error : (resultContent || formatJSON(result)));
                    }}
                  />
                </Value>
              </div>
            )}
          </ResultContainer>
        </ToolCallContent>
      </ToolCallContainer>
    </ToolCallWrapper>
  );
};

export default ToolCallDisplay; 