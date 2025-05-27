import React, { useState, useEffect, useRef } from 'react';
import { FiChevronDown } from 'react-icons/fi';
import { RiRobot2Line } from 'react-icons/ri';
import { HiLightningBolt } from 'react-icons/hi';
import styled from 'styled-components';
import { fetchLLMProviders, fetchUserLLMConfigs } from '../api';

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
  max-height: 400px;
  overflow-y: auto;
  display: ${props => props.isOpen ? 'block' : 'none'};
`;

const DropdownSection = styled.div`
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
  
  &:last-child {
    border-bottom: none;
  }
`;

const SectionTitle = styled.div`
  padding: 0 16px 8px;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
`;

const DropdownItem = styled.div`
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

const ConfigBadge = styled.div`
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

const LLMSelector = ({ selectedModel, onModelChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [providers, setProviders] = useState([]);
  const [userConfigs, setUserConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hasAutoSelected, setHasAutoSelected] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    loadProviders();
    loadUserConfigs();
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

  const loadProviders = async () => {
    try {
      const data = await fetchLLMProviders();
      setProviders(data);
    } catch (error) {
      console.error('加载LLM提供商失败:', error);
    }
  };

  const loadUserConfigs = async () => {
    try {
      const token = localStorage.getItem('authToken');
      if (!token) {
        setLoading(false);
        return;
      }

      const data = await fetchUserLLMConfigs();
      setUserConfigs(data);
      
      // 如果没有选中模型且还没有自动选择过，自动选择配置
      if (!selectedModel && !hasAutoSelected && onModelChange) {
        const defaultConfig = data.find(config => config.is_default);
        if (defaultConfig) {
          onModelChange(defaultConfig.model_name);
          setHasAutoSelected(true);
        } else if (data.length > 0) {
          // 如果没有默认配置但有用户配置，选择第一个
          onModelChange(data[0].model_name);
          setHasAutoSelected(true);
        } else if (providers.length > 0 && providers[0].models.length > 0) {
          // 如果没有用户配置，选择系统提供的第一个模型
          onModelChange(providers[0].models[0]);
          setHasAutoSelected(true);
        }
      }
    } catch (error) {
      console.error('加载用户配置失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleModelSelect = (modelName) => {
    
    if (onModelChange) {
      onModelChange(modelName);
    } 
    setIsOpen(false);
  };

  const handleConfigChange = () => {
    // 重新加载用户配置
    loadUserConfigs();
  };

  const getSelectedModelInfo = () => {
    if (!selectedModel) return null;
    
    // 查找用户配置中的模型
    const userConfig = userConfigs.find(config => config.model_name === selectedModel);
    
    if (userConfig) {
      return {
        name: selectedModel, // 显示模型名称而不是配置名称
        provider: userConfig.provider,
        isUserConfig: true,
        isDefault: userConfig.is_default
      };
    }
    
    // 查找系统提供商中的模型
    for (const provider of providers) {
      if (provider.models.includes(selectedModel)) {
        return {
          name: selectedModel,
          provider: provider.value,
          isUserConfig: false,
          isDefault: false
        };
      }
    }
    
    return {
      name: selectedModel,
      provider: 'system',
      isUserConfig: false,
      isDefault: false
    };
  };

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
                {selectedInfo.provider.toUpperCase()}
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
        {userConfigs.length > 0 ? (
          // 如果有用户配置，显示该提供商的所有可用模型
          <>
            {/* 用户配置的提供商分组 */}
            {Array.from(new Set(userConfigs.map(config => config.provider))).map(providerName => {
              const provider = providers.find(p => p.value === providerName);
              const providerConfigs = userConfigs.filter(config => config.provider === providerName);
              const defaultConfig = providerConfigs.find(config => config.is_default);
              
              return (
                <DropdownSection key={providerName}>
                  <SectionTitle>{provider?.label || providerName.toUpperCase()}</SectionTitle>
                  {provider?.models.map((model, modelIndex) => {
                    const isConfigured = providerConfigs.some(config => config.model_name === model);
                    const isDefault = defaultConfig?.model_name === model;
                    
                    return (
                      <DropdownItem
                        key={`${providerName}-${modelIndex}`}
                        className={selectedModel === model ? 'selected' : ''}
                        onClick={() => handleModelSelect(model)}
                      >
                        <ModelIcon color={getProviderColor(providerName)}>
                          {getProviderAbbr(providerName)}
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
                          <ModelProvider>
                            {provider?.label || providerName.toUpperCase()}
                          </ModelProvider>
                        </ModelInfo>
                      </DropdownItem>
                    );
                  })}
                </DropdownSection>
              );
            })}
          </>
        ) : (
          // 如果没有用户配置，显示系统模型
          providers.length > 0 ? (
            <DropdownSection>
              <SectionTitle>可用模型</SectionTitle>
              {providers.map((provider, index) => 
                provider.models.map((model, modelIndex) => (
                  <DropdownItem
                    key={`${index}-${modelIndex}`}
                    className={selectedModel === model ? 'selected' : ''}
                    onClick={() => handleModelSelect(model)}
                  >
                    <ModelIcon color={getProviderColor(provider.value)}>
                      {getProviderAbbr(provider.value)}
                    </ModelIcon>
                    <ModelInfo>
                      <ModelName>{model}</ModelName>
                      <ModelProvider>{provider.label}</ModelProvider>
                    </ModelInfo>
                  </DropdownItem>
                ))
              )}
            </DropdownSection>
          ) : (
            <EmptyState>
              <RiRobot2Line size={24} style={{ marginBottom: '8px', opacity: 0.5 }} />
              <div>暂无可用模型</div>
              <div style={{ fontSize: '12px', marginTop: '4px' }}>
                请在设置中配置您的LLM
              </div>
            </EmptyState>
          )
        )}
      </DropdownMenu>
    </SelectorContainer>
  );
};

export default LLMSelector; 