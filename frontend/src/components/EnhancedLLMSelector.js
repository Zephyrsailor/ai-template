import React, { useState, useEffect, useRef } from 'react';
import { FiChevronDown, FiSearch, FiRefreshCw, FiPlus } from 'react-icons/fi';
import { RiRobot2Line } from 'react-icons/ri';
import { HiLightningBolt } from 'react-icons/hi';
import styled from 'styled-components';
import { fetchAvailableModelsForUser, fetchUserLLMConfigs } from '../api';

const SelectorContainer = styled.div`
  position: relative;
  display: inline-block;
`;

const SelectorButton = styled.button`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  color: #374151;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 180px;
  justify-content: space-between;
  
  &:hover {
    border-color: #d1d5db;
    background: #f9fafb;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }
  
  &:focus {
    outline: none;
    border-color: #6366f1;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
  }
`;

const ModelIcon = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 4px;
  background: ${props => props.color || '#f3f4f6'};
  color: white;
  font-size: 12px;
  font-weight: 600;
`;

const ModelInfo = styled.div`
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  flex: 1;
`;

const ModelName = styled.div`
  font-size: 14px;
  font-weight: 500;
  color: #111827;
  line-height: 1.2;
`;

const ModelProvider = styled.div`
  font-size: 12px;
  color: #6b7280;
  line-height: 1.2;
`;

const DropdownMenu = styled.div`
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 8px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  z-index: 1000;
  max-height: 500px;
  overflow: hidden;
  display: ${props => props.isOpen ? 'block' : 'none'};
`;

const SearchContainer = styled.div`
  padding: 12px;
  border-bottom: 1px solid #f3f4f6;
  position: sticky;
  top: 0;
  background: white;
  z-index: 10;
`;

const SearchInput = styled.input`
  width: 100%;
  padding: 8px 12px 8px 36px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  background: #f9fafb;
  
  &:focus {
    outline: none;
    border-color: #6366f1;
    background: white;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
  }
  
  &::placeholder {
    color: #9ca3af;
    font-style: italic;
  }
`;

const SearchIcon = styled.div`
  position: absolute;
  left: 24px;
  top: 50%;
  transform: translateY(-50%);
  color: #9ca3af;
  pointer-events: none;
`;

const RefreshButton = styled.button`
  position: absolute;
  right: 24px;
  top: 50%;
  transform: translateY(-50%);
  padding: 4px;
  border: none;
  background: none;
  color: #6b7280;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s ease;
  
  &:hover {
    background: #f3f4f6;
    color: #374151;
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const ModelList = styled.div`
  max-height: 400px;
  overflow-y: auto;
`;

const ProviderSection = styled.div`
  border-bottom: 1px solid #f3f4f6;
  
  &:last-child {
    border-bottom: none;
  }
`;

const ProviderHeader = styled.div`
  padding: 12px 16px 8px;
  background: #f9fafb;
  border-bottom: 1px solid #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const ProviderTitle = styled.div`
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
  gap: 6px;
`;

const ModelCount = styled.span`
  background: #e5e7eb;
  color: #6b7280;
  font-size: 10px;
  font-weight: 500;
  padding: 2px 6px;
  border-radius: 10px;
  text-transform: none;
`;

const DynamicBadge = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  background: #10b981;
  color: white;
  font-size: 10px;
  font-weight: 500;
  border-radius: 4px;
  text-transform: uppercase;
`;

const ModelItem = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background-color: #f9fafb;
  }
  
  &.selected {
    background-color: #eef2ff;
    
    ${ModelName} {
      color: #6366f1;
    }
  }
`;

const DefaultIndicator = styled.div`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  background: linear-gradient(135deg, #f59e0b, #f97316);
  border-radius: 50%;
  margin-left: 6px;
  
  svg {
    color: white;
    font-size: 10px;
  }
`;

const EmptyState = styled.div`
  padding: 24px 16px;
  text-align: center;
  color: #6b7280;
  font-size: 14px;
`;

const AddProviderButton = styled.button`
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 12px 16px;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
  background: #f9fafb;
  color: #6b7280;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin: 12px;
  margin-bottom: 0;
  
  &:hover {
    border-color: #6366f1;
    background: #eef2ff;
    color: #6366f1;
  }
`;

const LoadingState = styled.div`
  padding: 24px 16px;
  text-align: center;
  color: #6b7280;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
`;

// 获取提供商的图标颜色
const getProviderColor = (provider) => {
  const colors = {
    'openai': '#10a37f',
    'deepseek': '#1e40af',
    'azure': '#0078d4',
    'ollama': '#ff6b35',
    'anthropic': '#d97706',
    'gemini': '#4285f4'
  };
  return colors[provider] || '#6b7280';
};

// 获取提供商的简称
const getProviderAbbr = (provider) => {
  const abbrs = {
    'openai': 'AI',
    'deepseek': 'DS',
    'azure': 'AZ',
    'ollama': 'OL',
    'anthropic': 'AN',
    'gemini': 'GM'
  };
  return abbrs[provider] || provider.substring(0, 2).toUpperCase();
};

const EnhancedLLMSelector = ({ selectedModel, onModelChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [availableModels, setAvailableModels] = useState([]);
  const [userConfigs, setUserConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    loadData();
  }, []);

  // 点击外部关闭下拉菜单
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [modelsData, configsData] = await Promise.all([
        fetchAvailableModelsForUser(),
        fetchUserLLMConfigs()
      ]);
      
      setAvailableModels(modelsData);
      setUserConfigs(configsData);
    } catch (error) {
      console.error('加载数据失败:', error);
      setAvailableModels([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      await loadData();
    } finally {
      setRefreshing(false);
    }
  };

  const handleModelSelect = (modelName) => {
    if (onModelChange) {
      onModelChange(modelName);
    }
    setIsOpen(false);
  };

  const getSelectedModelInfo = () => {
    if (!selectedModel) return null;
    
    // 查找用户配置中的模型
    const userConfig = userConfigs.find(config => config.model_name === selectedModel);
    
    if (userConfig) {
      return {
        name: selectedModel,
        provider: userConfig.provider,
        isUserConfig: true,
        isDefault: userConfig.is_default
      };
    }
    
    // 查找可用模型中的模型
    for (const providerData of availableModels) {
      if (providerData.models.includes(selectedModel)) {
        return {
          name: selectedModel,
          provider: providerData.provider,
          providerLabel: providerData.provider_label,
          isUserConfig: false,
          isDefault: false
        };
      }
    }
    
    // 如果都没找到，尝试根据模型名称推断提供商
    const inferredProvider = inferProviderFromModel(selectedModel);
    
    return {
      name: selectedModel,
      provider: inferredProvider || 'system',
      providerLabel: getProviderLabel(inferredProvider || 'system'),
      isUserConfig: false,
      isDefault: false
    };
  };

  // 根据模型名称推断提供商
  const inferProviderFromModel = (modelName) => {
    if (!modelName) return null;
    
    const modelLower = modelName.toLowerCase();
    
    if (modelLower.startsWith('gpt-') || modelLower.startsWith('o1-')) {
      return 'openai';
    } else if (modelLower.startsWith('deepseek')) {
      return 'deepseek';
    } else if (modelLower.startsWith('gemini')) {
      return 'gemini';
    } else if (modelLower.startsWith('claude')) {
      return 'anthropic';
    } else if (['llama', 'qwen', 'mistral', 'phi', 'codellama'].some(pattern => modelLower.includes(pattern))) {
      return 'ollama';
    }
    
    return null;
  };

  // 获取提供商显示名称
  const getProviderLabel = (provider) => {
    const labels = {
      'openai': 'OpenAI',
      'deepseek': 'DeepSeek',
      'gemini': 'Google Gemini',
      'anthropic': 'Anthropic',
      'ollama': 'Ollama',
      'azure': 'Azure OpenAI',
      'system': 'System'
    };
    return labels[provider] || provider.charAt(0).toUpperCase() + provider.slice(1);
  };

  // 过滤模型
  const filteredModels = availableModels.map(providerData => ({
    ...providerData,
    models: providerData.models.filter(model =>
      model.toLowerCase().includes(searchTerm.toLowerCase())
    )
  })).filter(providerData => providerData.models.length > 0);

  const selectedInfo = getSelectedModelInfo();

  if (loading) {
    return (
      <SelectorContainer ref={containerRef}>
        <SelectorButton disabled>
          <ModelIcon color="#6b7280">
            <RiRobot2Line size={12} />
          </ModelIcon>
          <ModelInfo>
            <ModelName>加载中...</ModelName>
          </ModelInfo>
        </SelectorButton>
      </SelectorContainer>
    );
  }

  return (
    <SelectorContainer ref={containerRef}>
      <SelectorButton onClick={() => setIsOpen(!isOpen)}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ModelIcon color={selectedInfo ? getProviderColor(selectedInfo.provider) : '#6b7280'}>
            {selectedInfo ? getProviderAbbr(selectedInfo.provider) : <RiRobot2Line size={12} />}
          </ModelIcon>
          <ModelInfo>
            <ModelName>{selectedInfo ? selectedInfo.name : '选择模型'}</ModelName>
            {selectedInfo && (
              <ModelProvider>
                {selectedInfo.providerLabel || selectedInfo.provider.toUpperCase()}
                {selectedInfo.isDefault && (
                  <span style={{ marginLeft: '4px' }}>
                    <HiLightningBolt size={10} style={{ color: '#f59e0b' }} />
                  </span>
                )}
              </ModelProvider>
            )}
          </ModelInfo>
        </div>
        <FiChevronDown size={16} style={{ 
          transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.2s ease'
        }} />
      </SelectorButton>

      <DropdownMenu isOpen={isOpen}>
        {/* 搜索栏 */}
        <SearchContainer>
          <div style={{ position: 'relative' }}>
            <SearchIcon>
              <FiSearch size={16} />
            </SearchIcon>
            <SearchInput
              type="text"
              placeholder="搜索模型..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <RefreshButton
              onClick={handleRefresh}
              disabled={refreshing}
              title="刷新模型列表"
            >
              <FiRefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
            </RefreshButton>
          </div>
        </SearchContainer>

        {/* 模型列表 */}
        <ModelList>
          {loading ? (
            <LoadingState>
              <FiRefreshCw size={16} className="animate-spin" />
              加载中...
            </LoadingState>
          ) : filteredModels.length > 0 ? (
            filteredModels.map((providerData) => {
              const defaultConfig = userConfigs.find(
                config => config.provider === providerData.provider && config.is_default
              );
              
              return (
                <ProviderSection key={providerData.provider}>
                  <ProviderHeader>
                    <ProviderTitle>
                      {providerData.provider_label}
                      <ModelCount>{providerData.models.length}</ModelCount>
                      {!providerData.is_configured && (
                        <span style={{ 
                          fontSize: '10px', 
                          color: '#9ca3af', 
                          marginLeft: '4px',
                          fontWeight: 'normal'
                        }}>
                          (未配置)
                        </span>
                      )}
                    </ProviderTitle>
                    <div style={{ display: 'flex', gap: '4px' }}>
                      {providerData.is_dynamic && (
                        <DynamicBadge>实时</DynamicBadge>
                      )}
                      {providerData.error && (
                        <span style={{
                          fontSize: '10px',
                          color: '#ef4444',
                          background: '#fef2f2',
                          padding: '2px 6px',
                          borderRadius: '4px'
                        }}>
                          错误
                        </span>
                      )}
                    </div>
                  </ProviderHeader>
                  {providerData.models.map((model) => {
                    const isDefault = defaultConfig?.model_name === model;
                    
                    return (
                      <ModelItem
                        key={`${providerData.provider}-${model}`}
                        className={selectedModel === model ? 'selected' : ''}
                        onClick={() => handleModelSelect(model)}
                      >
                        <ModelIcon color={getProviderColor(providerData.provider)}>
                          {getProviderAbbr(providerData.provider)}
                        </ModelIcon>
                        <ModelInfo>
                          <div style={{ display: 'flex', alignItems: 'center' }}>
                            <ModelName>{model}</ModelName>
                            {isDefault && (
                              <DefaultIndicator title="默认模型">
                                <HiLightningBolt size={10} />
                              </DefaultIndicator>
                            )}
                          </div>
                          <ModelProvider>{providerData.provider_label}</ModelProvider>
                        </ModelInfo>
                      </ModelItem>
                    );
                  })}
                </ProviderSection>
              );
            })
          ) : (
            <>
              <EmptyState>
                <RiRobot2Line size={24} style={{ marginBottom: '8px', opacity: 0.5 }} />
                <div>
                  {searchTerm ? `未找到包含 "${searchTerm}" 的模型` : '暂无可用模型'}
                </div>
                <div style={{ fontSize: '12px', marginTop: '4px' }}>
                  {searchTerm ? '尝试修改搜索关键词' : '请在设置中配置您的LLM'}
                </div>
              </EmptyState>
              {!searchTerm && (
                <AddProviderButton onClick={() => {
                  setIsOpen(false);
                  // 这里可以触发打开设置页面的回调
                  if (window.openLLMSettings) {
                    window.openLLMSettings();
                  } else {
                    alert('请点击右上角用户菜单 -> 设置 -> LLM配置');
                  }
                }}>
                  <FiPlus size={16} />
                  添加自定义服务商
                </AddProviderButton>
              )}
            </>
          )}
        </ModelList>
      </DropdownMenu>
    </SelectorContainer>
  );
};

export default EnhancedLLMSelector; 