import React, { useState, useEffect } from 'react';
import { FiX, FiPlus, FiTrash2, FiEdit3 } from 'react-icons/fi';
import styled from 'styled-components';
import ConfirmDialog from './ConfirmDialog';
import { fetchLLMProviders, fetchUserLLMConfigs, saveLLMConfig, deleteLLMConfig, fetchOllamaModels } from '../api';

const ModalOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`;

const ModalContent = styled.div`
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
`;

const ModalHeader = styled.div`
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const ModalTitle = styled.h2`
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
`;

const CloseButton = styled.button`
  padding: 8px;
  border: none;
  background: none;
  color: #6b7280;
  cursor: pointer;
  border-radius: 6px;
  
  &:hover {
    background: #f3f4f6;
    color: #374151;
  }
`;

const ModalBody = styled.div`
  padding: 24px;
`;

const ConfigList = styled.div`
  margin-bottom: 24px;
`;

const ConfigItem = styled.div`
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  
  &:last-child {
    margin-bottom: 0;
  }
`;

const ConfigHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: between;
  margin-bottom: 8px;
`;

const ConfigName = styled.div`
  font-weight: 500;
  color: #111827;
  flex: 1;
`;

const ConfigActions = styled.div`
  display: flex;
  gap: 8px;
`;

const ActionButton = styled.button`
  padding: 4px 8px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: white;
  color: #6b7280;
  cursor: pointer;
  font-size: 12px;
  
  &:hover {
    background: #f9fafb;
    color: #374151;
  }
`;

const ConfigDetails = styled.div`
  font-size: 14px;
  color: #6b7280;
  line-height: 1.4;
`;

const Form = styled.form`
  border-top: 1px solid #e5e7eb;
  padding-top: 24px;
`;

const FormGroup = styled.div`
  margin-bottom: 16px;
`;

const Label = styled.label`
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
`;

const Input = styled.input`
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  
  &:focus {
    outline: none;
    border-color: #6366f1;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
  }
`;

const Select = styled.select`
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  
  &:focus {
    outline: none;
    border-color: #6366f1;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
  }
`;

const Checkbox = styled.input`
  margin-right: 8px;
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
`;

const Button = styled.button`
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  
  ${props => props.variant === 'primary' ? `
    background: #6366f1;
    color: white;
    border: 1px solid #6366f1;
    
    &:hover {
      background: #5856eb;
    }
  ` : `
    background: white;
    color: #374151;
    border: 1px solid #d1d5db;
    
    &:hover {
      background: #f9fafb;
    }
  `}
`;

const LLMConfigModal = ({ isOpen, onClose, onConfigChange, selectedModel, setSelectedModel }) => {
  const [configs, setConfigs] = useState([]);
  const [providers, setProviders] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingConfig, setEditingConfig] = useState(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [configToDelete, setConfigToDelete] = useState(null);
  const [ollamaModels, setOllamaModels] = useState([]);
  const [loadingOllamaModels, setLoadingOllamaModels] = useState(false);
  const [customModelName, setCustomModelName] = useState('');
  const [showCustomModel, setShowCustomModel] = useState(false);
  const [formData, setFormData] = useState({
    provider: 'openai',
    model_name: '',
    api_key: '',
    base_url: '',
    temperature: 0.7,
    max_tokens: 1024,
    is_default: false,
    config_name: ''
  });

  useEffect(() => {
    if (isOpen) {
      loadProviders();
      loadConfigs();
    }
  }, [isOpen]);

  // 当提供商改变时，加载对应的模型
  useEffect(() => {
    if (formData.provider === 'ollama' && formData.base_url) {
      loadOllamaModels(formData.base_url);
    }
  }, [formData.provider, formData.base_url]);

  const loadProviders = async () => {
    try {
      const data = await fetchLLMProviders();
      setProviders(data);
    } catch (error) {
      console.error('加载提供商失败:', error);
    }
  };

  const loadConfigs = async () => {
    try {
      const token = localStorage.getItem('authToken');
      if (!token) return;

      const data = await fetchUserLLMConfigs();
      setConfigs(data);
    } catch (error) {
      console.error('加载配置失败:', error);
    }
  };

  const loadOllamaModels = async (baseUrl) => {
    setLoadingOllamaModels(true);
    try {
      const models = await fetchOllamaModels(baseUrl);
      setOllamaModels(models);
    } catch (error) {
      console.error('加载Ollama模型失败:', error);
      setOllamaModels([]);
    } finally {
      setLoadingOllamaModels(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const token = localStorage.getItem('authToken');
      if (!token) return;

      // 准备提交数据，如果是编辑且API密钥为空，则不包含api_key字段
      const submitData = { ...formData };
      if (editingConfig && !formData.api_key) {
        delete submitData.api_key;
      }

      await saveLLMConfig(submitData);
      await loadConfigs();
      setShowForm(false);
      setEditingConfig(null);
      setFormData({
        provider: 'openai',
        model_name: '',
        api_key: '',
        base_url: '',
        temperature: 0.7,
        max_tokens: 1024,
        is_default: false,
        config_name: ''
      });
      setShowCustomModel(false);
      setCustomModelName('');
      // If the saved config is set as default, update the selected model
      if (formData.is_default && setSelectedModel) {
        setSelectedModel(formData.model_name);
      }
      onConfigChange?.();
    } catch (error) {
      console.error('保存配置失败:', error);
    }
  };

  const handleDelete = (configName) => {
    setConfigToDelete(configName);
    setShowConfirmDialog(true);
  };

  const confirmDelete = async () => {
    if (!configToDelete) return;
    
    try {
      const token = localStorage.getItem('authToken');
      if (!token) return;

      await deleteLLMConfig(configToDelete);
      await loadConfigs();
      onConfigChange?.();
    } catch (error) {
      console.error('删除配置失败:', error);
    } finally {
      setShowConfirmDialog(false);
      setConfigToDelete(null);
    }
  };

  const handleEdit = (config) => {
    setEditingConfig(config);
    setFormData({
      provider: config.provider,
      model_name: config.model_name,
      api_key: '', // 不显示现有密钥
      base_url: config.base_url || '',
      temperature: config.temperature,
      max_tokens: config.max_tokens,
      is_default: config.is_default,
      config_name: config.config_name
    });
    setShowForm(true);
  };

  const selectedProvider = providers.find(p => p.value === formData.provider);

  if (!isOpen) return null;

  return (
    <ModalOverlay onClick={onClose}>
      <ModalContent onClick={e => e.stopPropagation()}>
        <ModalHeader>
          <ModalTitle>LLM 配置管理</ModalTitle>
          <CloseButton onClick={onClose}>
            <FiX size={20} />
          </CloseButton>
        </ModalHeader>
        
        <ModalBody>
          <ConfigList>
            {configs.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#6b7280', padding: '20px' }}>
                暂无配置，点击下方按钮添加
              </div>
            ) : (
              configs.map((config, index) => (
                <ConfigItem key={index}>
                  <ConfigHeader>
                    <ConfigName>
                      {config.config_name} {config.is_default && <span style={{ color: '#10b981', fontSize: '12px' }}>(默认)</span>}
                    </ConfigName>
                    <ConfigActions>
                      <ActionButton onClick={() => handleEdit(config)}>
                        <FiEdit3 size={12} />
                      </ActionButton>
                      <ActionButton onClick={() => handleDelete(config.config_name)}>
                        <FiTrash2 size={12} />
                      </ActionButton>
                    </ConfigActions>
                  </ConfigHeader>
                  <ConfigDetails>
                    提供商: {config.provider} | 模型: {config.model_name}<br/>
                    {config.base_url && `API地址: ${config.base_url}`}
                  </ConfigDetails>
                </ConfigItem>
              ))
            )}
          </ConfigList>

          {!showForm && (
            <Button variant="primary" onClick={() => setShowForm(true)}>
              <FiPlus size={16} style={{ marginRight: '6px' }} />
              添加新配置
            </Button>
          )}

          {showForm && (
            <Form onSubmit={handleSubmit}>
              <FormGroup>
                <Label>配置名称</Label>
                <Input
                  type="text"
                  value={formData.config_name}
                  onChange={e => setFormData({...formData, config_name: e.target.value})}
                  placeholder="例如：我的OpenAI配置"
                  required
                />
              </FormGroup>

              <FormGroup>
                <Label>提供商</Label>
                <Select
                  value={formData.provider}
                  onChange={e => setFormData({...formData, provider: e.target.value})}
                >
                  {providers.map(provider => (
                    <option key={provider.value} value={provider.value}>
                      {provider.label}
                    </option>
                  ))}
                </Select>
              </FormGroup>

              <FormGroup>
                <Label>模型</Label>
                {selectedProvider?.supports_custom_models ? (
                  <div>
                    <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                      <Button 
                        type="button" 
                        variant={!showCustomModel ? "primary" : "secondary"}
                        onClick={() => setShowCustomModel(false)}
                        style={{ fontSize: '12px', padding: '4px 8px' }}
                      >
                        预设模型
                      </Button>
                      <Button 
                        type="button" 
                        variant={showCustomModel ? "primary" : "secondary"}
                        onClick={() => setShowCustomModel(true)}
                        style={{ fontSize: '12px', padding: '4px 8px' }}
                      >
                        自定义模型
                      </Button>
                      {selectedProvider?.supports_dynamic_models && (
                        <Button 
                          type="button" 
                          variant="secondary"
                          onClick={() => loadOllamaModels(formData.base_url || selectedProvider.default_base_url)}
                          disabled={loadingOllamaModels}
                          style={{ fontSize: '12px', padding: '4px 8px' }}
                        >
                          {loadingOllamaModels ? '加载中...' : '刷新模型'}
                        </Button>
                      )}
                    </div>
                    
                    {showCustomModel ? (
                      <Input
                        type="text"
                        value={formData.model_name}
                        onChange={e => setFormData({...formData, model_name: e.target.value})}
                        placeholder="输入自定义模型名称，如：llama3.1:8b"
                        required
                      />
                    ) : (
                      <Select
                        value={formData.model_name}
                        onChange={e => setFormData({...formData, model_name: e.target.value})}
                        required
                      >
                        <option value="">选择模型</option>
                        {/* 显示预设模型 */}
                        {selectedProvider?.models.map(model => (
                          <option key={model} value={model}>{model}</option>
                        ))}
                        {/* 如果是Ollama，显示动态加载的模型 */}
                        {selectedProvider?.supports_dynamic_models && ollamaModels.length > 0 && (
                          <>
                            <optgroup label="已安装的模型">
                              {ollamaModels.map(model => (
                                <option key={`ollama-${model}`} value={model}>{model}</option>
                              ))}
                            </optgroup>
                          </>
                        )}
                      </Select>
                    )}
                  </div>
                ) : (
                  <Select
                    value={formData.model_name}
                    onChange={e => setFormData({...formData, model_name: e.target.value})}
                    required
                  >
                    <option value="">选择模型</option>
                    {selectedProvider?.models.map(model => (
                      <option key={model} value={model}>{model}</option>
                    ))}
                  </Select>
                )}
              </FormGroup>

              {selectedProvider?.requires_api_key && (
                <FormGroup>
                  <Label>API密钥</Label>
                  <Input
                    type="password"
                    value={formData.api_key}
                    onChange={e => setFormData({...formData, api_key: e.target.value})}
                    placeholder={editingConfig ? "留空保持原有密钥不变" : "输入API密钥"}
                    required={!editingConfig}
                  />
                  {editingConfig && (
                    <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                      留空将保持原有密钥不变
                    </div>
                  )}
                </FormGroup>
              )}

              <FormGroup>
                <Label>API地址 (可选)</Label>
                <Input
                  type="url"
                  value={formData.base_url}
                  onChange={e => {
                    setFormData({...formData, base_url: e.target.value});
                    // 如果是Ollama且支持动态模型，当base_url改变时自动刷新模型列表
                    if (selectedProvider?.supports_dynamic_models && e.target.value) {
                      setTimeout(() => loadOllamaModels(e.target.value), 500); // 延迟500ms避免频繁请求
                    }
                  }}
                  placeholder={selectedProvider?.default_base_url || "使用默认地址"}
                />
                {selectedProvider?.supports_dynamic_models && (
                  <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                    修改地址后将自动刷新可用模型列表
                  </div>
                )}
              </FormGroup>

              <FormGroup>
                <Label>
                  <Checkbox
                    type="checkbox"
                    checked={formData.is_default}
                    onChange={e => setFormData({...formData, is_default: e.target.checked})}
                  />
                  设为默认配置
                </Label>
              </FormGroup>

              <ButtonGroup>
                <Button type="button" onClick={() => {
                  setShowForm(false);
                  setEditingConfig(null);
                  setShowCustomModel(false);
                  setCustomModelName('');
                }}>
                  取消
                </Button>
                <Button type="submit" variant="primary">
                  {editingConfig ? '更新' : '保存'}
                </Button>
              </ButtonGroup>
            </Form>
          )}
        </ModalBody>
      </ModalContent>

      <ConfirmDialog
        isOpen={showConfirmDialog}
        onClose={() => setShowConfirmDialog(false)}
        onConfirm={confirmDelete}
        title="删除LLM配置"
        message={`确定要删除配置"${configToDelete}"吗？此操作无法撤销。`}
        confirmText="删除"
        cancelText="取消"
        type="danger"
      />
    </ModalOverlay>
  );
};

export default LLMConfigModal;
