/**
 * API模块 - 处理与后端的通信
 */

import axios from './http';

// 后端API基础URL
const API_BASE_URL = '/api';

/**
 * 检查认证状态
 * @returns {Object} 认证状态信息
 */
export const checkAuthStatus = () => {
  const token = localStorage.getItem('authToken');
  const headers = axios.defaults.headers.common || {};
  
  return {
    hasToken: !!token,
    tokenLength: token ? token.length : 0,
    hasAuthHeader: !!headers['Authorization'],
    headerValue: headers['Authorization'] ? headers['Authorization'].substring(0, 15) + '...' : null
  };
};

/**
 * 处理标准API响应
 * @param {Object} response 标准API响应对象
 * @returns {Object} 处理结果，包含success, data和message
 */
const handleApiResponse = (response) => {
    return {
      success: response.code === 200,
      data: response.data,
      message: response.message
    };
};

/**
 * 获取MCP服务器列表
 * @param {boolean} activeOnly 是否只返回激活的服务器
 * @returns {Promise<Object>} 服务器列表响应
 */
export async function fetchMCPServers(activeOnly = false) {
  try {
    // 添加user_id参数，确保只获取当前用户的数据
    const url = activeOnly 
      ? `${API_BASE_URL}/mcp/servers?active_only=true&user_specific=true&connected_only=true`
      : `${API_BASE_URL}/mcp/servers`;
      
    const response = await axios.get(url);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch MCP servers:', error);
    throw error;
  }
}

/**
 * 获取知识库列表
 * @returns {Promise<Object>} 知识库列表
 */
export const fetchKnowledgeBases = async () => {
  try {
    // 添加user_specific参数，确保只获取当前用户的数据
    const response = await axios.get(`${API_BASE_URL}/knowledge/?user_specific=true`);
    
    // 确保有正确的数据结构或返回空数组
    if (response.data && response.data.data) {
      // 适当地转换结果
      return { success: true, data: response.data.data, message: response.data.message || "获取成功" };
    } else {
      console.warn('知识库列表响应格式不正确:', response.data);
      return { success: false, data: [], message: "获取知识库列表失败：响应格式不正确" };
    }
    
  } catch (error) {
    console.error('获取知识库列表失败:', error);
    return { success: false, data: [], message: "获取知识库列表失败: " + (error.message || "未知错误") };
  }
};

/**
 * 创建知识库
 * @param {Object} knowledgeBaseData 知识库数据
 * @returns {Promise<Object>} 创建的知识库信息
 */
export const createKnowledgeBase = async (knowledgeBaseData) => {
  try {
    // 确保只发送必要的字段，不包含is_public
    const { name, description } = knowledgeBaseData;
    const cleanData = { name, description };
    
    // 确保知识库与用户关联
    const response = await axios.post(`${API_BASE_URL}/knowledge/?user_specific=true`, cleanData);
    
    // 处理响应
    const result = handleApiResponse(response.data);
    return result;
  } catch (error) {
    console.error('创建知识库失败:', error);
    const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || "创建知识库失败 (Catch)";
    return { success: false, data: null, message: errorMessage, error: error };
  }
};

/**
 * 获取知识库详情
 * @param {string} knowledgeBaseKey 知识库ID (currently name, will be actual ID)
 * @returns {Promise<Object>} 知识库详情
 */
export const getKnowledgeBase = async (knowledgeBaseKey) => {
  try {
    const encodedKey = encodeURIComponent(knowledgeBaseKey);
    const response = await axios.get(`${API_BASE_URL}/knowledge/${encodedKey}/?user_specific=true`);
    const result = handleApiResponse(response.data);
    
    return result;
  } catch (error) {
    console.error('获取知识库详情出错:', error);
    const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || "获取知识库详情出错 (Catch)";
    return { success: false, data: error.response?.data?.data || null, message: errorMessage, error: error };
  }
};

/**
 * 获取知识库文件列表
 * @param {string} knowledgeBaseKey 知识库名称 (will be ID)
 * @returns {Promise<Object>} 文件列表 { success, data, message }
 */
export const getKnowledgeBaseFiles = async (knowledgeBaseKey) => {
  try {
    const encodedKey = encodeURIComponent(knowledgeBaseKey);
    const response = await axios.get(`${API_BASE_URL}/knowledge/${encodedKey}/files/?user_specific=true`);
    const result = handleApiResponse(response.data);
    
    if (result.success) {
        return { success: true, data: result.data || [], message: result.message };
    } else {
        return { success: false, data: result.data || [], message: result.message || '获取知识库文件列表失败' };
    }
  } catch (error) {
    console.error('获取知识库文件列表出错:', error);
    const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || "获取知识库文件列表出错 (Catch)";
    return { success: false, data: [], message: errorMessage, error: error };
  }
};

/**
 * 删除知识库
 * @param {string} knowledgeBaseKey 知识库ID或名称
 * @returns {Promise<Object>} 删除结果
 */
export const deleteKnowledgeBase = async (knowledgeBaseKey) => {
  try {
    const encodedKey = encodeURIComponent(knowledgeBaseKey);
    const urlToDelete = `${API_BASE_URL}/knowledge/${encodedKey}/?user_specific=true`;
    console.log('>>> AXIOS DELETE 请求的 URL:', urlToDelete);
    const response = await axios.delete(urlToDelete);
    
    const result = handleApiResponse(response.data);
    return result;
  } catch (error) {
    console.error('删除知识库失败:', error);
    const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || "删除知识库失败";
    return { success: false, message: errorMessage, error: error };
  }
};

/**
 * 更新知识库信息
 * @param {string} knowledgeBaseId 知识库ID
 * @param {Object} updateData 更新数据，可包含name、description
 * @returns {Promise<Object>} 更新结果
 */
export const updateKnowledgeBase = async (knowledgeBaseId, updateData) => {
  try {
    // 确保只发送必要的字段，不包含is_public
    const { name, description } = updateData;
    const cleanData = { name, description };
    
    const encodedId = encodeURIComponent(knowledgeBaseId);
    const response = await axios.put(`${API_BASE_URL}/knowledge/${encodedId}/?user_specific=true`, cleanData);
    const result = handleApiResponse(response.data);
    
    return result;
  } catch (error) {
    console.error('更新知识库失败:', error);
    const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || "更新知识库失败 (Catch)";
    return { success: false, data: null, message: errorMessage, error: error };
  }
};

/**
 * 上传文件到知识库
 * @param {string} knowledgeBaseKey 知识库ID (currently name, will be actual ID)
 * @param {File} file 要上传的文件
 * @returns {Promise<Object>} 上传结果
 */
export const uploadFileToKnowledgeBase = async (knowledgeBaseKey, file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const encodedKey = encodeURIComponent(knowledgeBaseKey);
    const response = await axios.post(`${API_BASE_URL}/knowledge/${encodedKey}/files/`, formData);
    const result = handleApiResponse(response.data);

    return result;
  } catch (error) {
    console.error('上传文件出错:', error);
    const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || "上传文件出错 (Catch)";
    return { success: false, data: error.response?.data?.data || null, message: errorMessage, error: error };
  }
};

/**
 * 查询知识库
 * @param {Object} queryData 查询参数 (contains knowledge_base_id, which might be name)
 * @returns {Promise<Object>} 查询结果
 */
export const queryKnowledgeBase = async (queryData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/knowledge/${queryData.knowledge_base_id}/query/?user_specific=true`, {
      query: queryData.query,
      top_k: queryData.top_k || 5
    }); 
    const result = handleApiResponse(response.data);

    return result;
  } catch (error) {
    console.error('查询知识库出错:', error);
    const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || "查询知识库出错 (Catch)";
    return { success: false, data: error.response?.data?.data || null, message: errorMessage, error: error };
  }
};

/**
 * 获取系统可用的AI模型列表
 * @returns {Promise<Array>} 模型列表
 */
export const getAvailableModels = async () => {
  try {
    const response = await axios.get('/api/models');
    return response.data.data || [];
  } catch (error) {
    console.error('获取模型列表失败:', error);
    return []; // 返回空数组作为默认值
  }
};

/**
 * 发送消息
 * @param {string} message 用户消息
 * @param {string} model 模型名称
 * @returns {Promise<Object>} 响应数据
 */
export const sendMessage = async (message, model) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/chat`, { 
      message,
      model: model || 'gpt-3.5-turbo'
    });
    
    return response.data;
  } catch (error) {
    console.error('发送消息出错:', error);
    throw error;
  }
};

/**
 * 获取会话历史
 * @returns {Promise<Array>} 会话列表
 */
export const fetchConversations = async () => {
  try {
    // 确保GET请求的路径末尾有斜杠
    const response = await axios.get(`${API_BASE_URL}/conversations/`);
        
    // 处理后端API返回格式，获取实际数据部分
    console.log("获取会话数据：", response.data);
    
    if (response.data && response.data.code === 200) {
      // 新格式：{ code: 200, message: "...", data: [...] }
      const conversationList = response.data.data || [];
      return { 
        success: true, 
        data: conversationList, 
        message: response.data.message 
      };
    } else if (Array.isArray(response.data)) {
      // 如果直接返回数组
      return { success: true, data: response.data, message: "获取成功" };
    }
    
    console.warn('会话列表响应格式不正确:', response.data);
    return { success: false, data: [], message: "获取会话列表失败：响应格式不正确" };
  } catch (error) {
    console.error('获取会话历史出错:', error);
    // 根据实际错误处理返回，例如，如果401则可能是需要重新登录
    if (error.response && error.response.status === 401) {
      console.warn('获取会话历史失败: 未授权');
      // 可以触发登出或提示用户重新登录
    }
    return { success: false, data: [], message: `获取会话失败: ${error.message}` };
  }
};

/**
 * 获取会话详情
 * @param {string} conversationId 会话ID
 * @returns {Promise<Object>} 会话详情
 */
export const getConversationDetails = async (conversationId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/conversations/${conversationId}?user_specific=true`);
    console.log("会话详情原始响应:", response.data);
    
    // 确保响应格式正确处理
    if (response.data && response.data.data) {
      // 标准格式是 { code: 200, message: "...", data: {...} }
      return { success: true, data: response.data.data, message: response.data.message };
    } else if (response.data && response.data.id) {
      // 如果直接返回会话对象
      return { success: true, data: response.data, message: "获取成功" };
    } else {
      console.warn('会话详情响应格式不正确:', response.data);
      return { success: false, data: {}, message: "获取会话详情失败：响应格式不正确" };
    }
  } catch (error) {
    console.error('获取会话详情失败:', error);
    return { 
      success: false, 
      data: {}, 
      message: `获取会话详情失败: ${error.message}` 
    };
  }
};

/**
 * 删除聊天对话
 * @param {string} conversationId 对话ID
 * @returns {Promise<Object>} 删除结果
 */
export const deleteConversation = async (conversationId) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/conversations/${conversationId}?user_specific=true`);
    return response.data;
  } catch (error) {
    console.error('删除对话失败:', error);
    throw error;
  }
};

/**
 * 创建MCP服务器
 * @param {Object} serverData 服务器数据
 * @returns {Promise<Object>} 创建结果
 */
export const createMCPServer = async (serverData) => {
  try {
    // 确保服务器与用户关联
    const response = await axios.post(`${API_BASE_URL}/mcp/servers`, serverData);
    return response.data;
  } catch (error) {
    console.error('创建MCP服务器失败:', error);
    throw error;
  }
};

/**
 * 更新MCP服务器
 * @param {string} serverId 服务器ID
 * @param {Object} serverData 服务器数据
 * @returns {Promise<Object>} 更新结果
 */
export const updateMCPServer = async (serverId, serverData) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/mcp/servers/${serverId}?user_specific=true`, serverData);
    return response.data;
  } catch (error) {
    console.error('更新MCP服务器失败:', error);
    throw error;
  }
};

/**
 * 测试MCP服务器连接
 * @param {string} serverId 服务器ID
 * @returns {Promise<Object>} 测试结果
 */
export const testMCPServerConnection = async (serverId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/mcp/servers/${serverId}/test?user_specific=true`);
    return response.data;
  } catch (error) {
    console.error('测试MCP服务器连接失败:', error);
    throw error;
  }
};

/**
 * 刷新/重连MCP服务器连接
 * @param {string} serverId 服务器ID
 * @returns {Promise<Object>} 刷新结果
 */
export const refreshMCPServerConnection = async (serverId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/mcp/servers/${serverId}/refresh?user_specific=true`);
    return response.data;
  } catch (error) {
    console.error('刷新MCP服务器连接失败:', error);
    throw error;
  }
};

/**
 * 连接到MCP服务器
 * @param {string} serverId 服务器ID
 * @returns {Promise<Object>} 连接结果
 */
export const connectMCPServer = async (serverId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/mcp/servers/${serverId}/connect?user_specific=true`);
    return response.data;
  } catch (error) {
    console.error('连接MCP服务器失败:', error);
    throw error;
  }
};

/**
 * 断开MCP服务器连接
 * @param {string} serverId 服务器ID
 * @returns {Promise<Object>} 断开连接结果
 */
export const disconnectMCPServer = async (serverId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/mcp/servers/${serverId}/disconnect?user_specific=true`);
    return response.data;
  } catch (error) {
    console.error('断开MCP服务器连接失败:', error);
    throw error;
  }
};

/**
 * 诊断网络和认证问题
 */
export const diagnoseConnectionIssues = async () => {
  console.group('API连接诊断');
  try {
    // 1. 检查是否有授权令牌
    const token = localStorage.getItem('authToken');
    console.log('授权令牌:', token ? `${token.substring(0,15)}... (长度:${token.length})` : 'null');
    
    // 2. 检查axios配置的认证头部
    const headers = axios.defaults.headers.common || {};
    console.log('全局认证头部:', headers['Authorization'] ? 
      `${headers['Authorization'].substring(0,20)}...` : '未设置');
    
    // 3. 尝试直接fetch API
    try {
      const directResponse = await fetch('/api/knowledge/', {
        headers: token ? {
          'Authorization': `Bearer ${token}`
        } : {}
      });
      console.log('直接fetch测试:', {
        status: directResponse.status,
        statusText: directResponse.statusText,
        ok: directResponse.ok
      });
    } catch (fetchError) {
      console.error('直接fetch测试失败:', fetchError);
    }
    
    // 4. 测试无认证的API
    try {
      const publicResponse = await fetch('/api/health');
      console.log('公共API测试:', {
        status: publicResponse.status,
        statusText: publicResponse.statusText,
        ok: publicResponse.ok
      });
    } catch (publicError) {
      console.error('公共API测试失败:', publicError);
    }
    
    // 5. 使用配置好的axios实例测试
    try {
      const axiosResponse = await axios.get('/api/knowledge/'); // Added trailing slash
      console.log('Axios认证API测试成功 (数据前100字符):', JSON.stringify(axiosResponse.data).substring(0,100) + (JSON.stringify(axiosResponse.data).length > 100 ? '...' : ''));
      return { success: true, message: '诊断完成, 请检查控制台日志。' }; 
    } catch (error) {
      console.error('Axios认证API测试失败:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message
      });
      return { 
        success: false, 
        message: '诊断过程中Axios测试失败, 请检查控制台日志。',
        error: {
          status: error.response?.status,
          data: error.response?.data,
          message: error.message
        }
      };
    }
  } catch (error) {
    console.error('诊断过程意外出错:', error);
    return { success: false, message: `诊断过程意外出错: ${error.message}`, error: error };
  } finally {
    console.groupEnd();
  }
};

/**
 * 创建新会话
 * @param {Object} conversationData 会话数据
 * @returns {Promise<Object>} 创建结果
 */
export const createConversation = async (conversationData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/conversations/`, conversationData);
    return response.data;
  } catch (error) {
    console.error('创建会话失败:', error);
    return { 
      success: false, 
      message: error.response?.data?.message || '创建会话失败', 
      error 
    };
  }
};

/**
 * 调用工具
 * @param {string} toolName 工具名称
 * @param {Object} args 工具参数
 * @param {boolean} userSpecific 是否使用用户数据隔离，默认为true
 * @returns {Promise<Object>} 工具调用结果
 */
export const callTool = async (toolName, args, userSpecific = true) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/tools/call?user_specific=${userSpecific}`, {
      tool_name: toolName,
      arguments: args
    });
    return response.data;
  } catch (error) {
    console.error('工具调用失败:', error);
    throw error;
  }
};

/**
 * 在指定服务器上调用工具
 * @param {string} serverId 服务器ID
 * @param {string} toolName 工具名称
 * @param {Object} args 工具参数
 * @param {boolean} userSpecific 是否使用用户数据隔离，默认为true
 * @returns {Promise<Object>} 工具调用结果
 */
export const callServerTool = async (serverId, toolName, args, userSpecific = true) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/mcp/servers/${serverId}/tools/${toolName}?user_specific=${userSpecific}`, 
      args
    );
    return response.data;
  } catch (error) {
    console.error('服务器工具调用失败:', error);
    throw error;
  }
};

/**
 * 获取工具列表
 * @param {string} category 可选的工具类别过滤
 * @param {boolean} userSpecific 是否只返回当前用户可用的工具，默认为true
 * @returns {Promise<Object>} 工具列表
 */
export const getTools = async (category = null, userSpecific = true) => {
  try {
    let url = `${API_BASE_URL}/tools/?user_specific=${userSpecific}`;
    if (category) {
      url += `&category=${encodeURIComponent(category)}`;
    }
    const response = await axios.get(url);
    return response.data;
  } catch (error) {
    console.error('获取工具列表失败:', error);
    throw error;
  }
};

/**
 * 清除用户工具上下文
 * @returns {Promise<Object>} 操作结果
 */
export const clearToolContext = async () => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/tools/context`);
    return response.data;
  } catch (error) {
    console.error('清除工具上下文失败:', error);
    throw error;
  }
};

// MCP 服务器状态管理
export const fetchMCPServerStatuses = async (userSpecific = true) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/mcp/servers/statuses?user_specific=${userSpecific}`);
    return response.data;
  } catch (error) {
    console.error('获取MCP服务器状态失败:', error);
    throw error;
  }
};

/**
 * 获取LLM提供商列表
 * @returns {Promise<Array>} 提供商列表
 */
export const fetchLLMProviders = async () => {
  try {
    console.log('fetchLLMProviders: 开始请求...');
    const response = await axios.get(`${API_BASE_URL}/user/llm-config/providers`);
    console.log('fetchLLMProviders: 原始响应:', response);
    console.log('fetchLLMProviders: 响应数据:', response.data);
    console.log('fetchLLMProviders: 响应状态:', response.status);
    
    // 处理不同的响应格式
    if (response.data && response.data.data) {
      // 标准格式 { code: 200, message: "...", data: [...] }
      console.log('fetchLLMProviders: 使用标准格式，data字段:', response.data.data);
      return Array.isArray(response.data.data) ? response.data.data : [];
    } else if (Array.isArray(response.data)) {
      // 直接返回数组
      console.log('fetchLLMProviders: 直接返回数组格式');
      return response.data;
    } else {
      console.warn('fetchLLMProviders 响应格式不正确:', response.data);
      return [];
    }
  } catch (error) {
    console.error('获取LLM提供商失败:', error);
    console.error('错误详情:', {
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message
    });
    return []; // 返回空数组作为默认值
  }
};

/**
 * 获取用户LLM配置列表
 * @returns {Promise<Array>} 用户配置列表
 */
export const fetchUserLLMConfigs = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/user/llm-config/`);
    console.log('fetchUserLLMConfigs 原始响应:', response.data);
    
    // 处理不同的响应格式
    if (response.data && response.data.data) {
      // 标准格式 { code: 200, message: "...", data: [...] }
      return Array.isArray(response.data.data) ? response.data.data : [];
    } else if (Array.isArray(response.data)) {
      // 直接返回数组
      return response.data;
    } else {
      console.warn('fetchUserLLMConfigs 响应格式不正确:', response.data);
      return [];
    }
  } catch (error) {
    console.error('获取用户LLM配置失败:', error);
    return []; // 确保总是返回数组
  }
};

/**
 * 获取默认LLM配置
 * @returns {Promise<Object>} 默认配置
 */
export const fetchDefaultLLMConfig = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/user/llm-config/default`);
    return response.data;
  } catch (error) {
    console.error('获取默认LLM配置失败:', error);
    throw error;
  }
};

/**
 * 创建LLM配置
 * @param {Object} configData 配置数据
 * @returns {Promise<Object>} 创建结果
 */
export const createLLMConfig = async (configData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/user/llm-config/`, configData);
    return response.data;
  } catch (error) {
    console.error('创建LLM配置失败:', error);
    throw error;
  }
};

/**
 * 更新LLM配置
 * @param {string} configId 配置ID
 * @param {Object} configData 配置数据
 * @returns {Promise<Object>} 更新结果
 */
export const updateLLMConfig = async (configId, configData) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/user/llm-config/${configId}`, configData);
    return response.data;
  } catch (error) {
    console.error('更新LLM配置失败:', error);
    throw error;
  }
};

/**
 * 创建或更新LLM配置（兼容性函数）
 * @param {Object} configData 配置数据
 * @param {string} configId 配置ID（可选，如果提供则为更新操作）
 * @returns {Promise<Object>} 操作结果
 */
export const saveLLMConfig = async (configData, configId = null) => {
  if (configId) {
    // 更新操作
    return await updateLLMConfig(configId, configData);
  } else {
    // 创建操作
    return await createLLMConfig(configData);
  }
};

/**
 * 删除LLM配置
 * @param {string} configName 配置ID
 * @returns {Promise<Object>} 删除结果
 */
export const deleteLLMConfig = async (id) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/user/llm-config/${id}`);
    return response.data;
  } catch (error) {
    console.error('删除LLM配置失败:', error);
    throw error;
  }
};

/**
 * 获取Ollama实际可用的模型列表
 * @param {string} baseUrl Ollama服务器地址
 * @returns {Promise<Array>} 模型列表
 */
export const fetchOllamaModels = async (baseUrl = 'http://localhost:11434') => {
  try {
    const response = await axios.get(`${API_BASE_URL}/user/llm-config/ollama/models?base_url=${encodeURIComponent(baseUrl)}`);
    return response.data;
  } catch (error) {
    console.error('获取Ollama模型列表失败:', error);
    throw error;
  }
};

/**
 * 获取用户配置的所有提供商的可用模型列表
 * @returns {Promise<Array>} 按提供商分组的模型列表
 */
export const fetchAvailableModelsForUser = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/user/llm-config/models/available`);
    console.log('fetchAvailableModelsForUser 原始响应:', response.data);
    
    // 处理不同的响应格式
    if (response.data && response.data.data) {
      // 标准格式 { code: 200, message: "...", data: [...] }
      return Array.isArray(response.data.data) ? response.data.data : [];
    } else if (Array.isArray(response.data)) {
      // 直接返回数组
      return response.data;
    } else {
      console.warn('fetchAvailableModelsForUser 响应格式不正确:', response.data);
      return [];
    }
  } catch (error) {
    console.error('获取用户可用模型列表失败:', error);
    return []; // 确保总是返回数组
  }
};

// 在其他API函数之后添加
export const fetchModelLimits = async (modelName) => {
  try {
    const response = await axios.get(`/api/user/llm-config/model-limits/${encodeURIComponent(modelName)}`);
    if (response.data.code === 200) {
      return response.data.data;
    }
    throw new Error(response.data.message || '获取模型参数失败');
  } catch (error) {
    console.error('获取模型参数失败:', error);
    throw error;
  }
}; 