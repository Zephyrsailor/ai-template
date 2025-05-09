/**
 * API模块 - 处理与后端的通信
 */

import axios from 'axios';

// 后端API基础URL
const API_BASE_URL = '/api';

/**
 * 处理标准API响应
 * @param {Object} response 标准API响应对象
 * @returns {Object} 处理结果，包含success, data和message
 */
const handleApiResponse = (response) => {
  // 检查响应格式
  if (response && typeof response.code !== 'undefined') {
    // 新格式响应
    return {
      code: response.code,
      data: response.data,
      message: response.message
    };
  }
  
  // 旧格式响应或其他格式，直接返回
  return {
    success: true,
    data: response,
    message: ""
  };
};

/**
 * 获取MCP服务器列表
 * @param {boolean} activeOnly 是否只返回激活的服务器
 * @returns {Promise<Object>} 服务器列表响应
 */
export async function fetchMCPServers(activeOnly = false) {
  try {
    const url = activeOnly 
      ? `${API_BASE_URL}/mcp/servers?active_only=true`
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
 * @returns {Promise<Array>} 知识库列表
 */
export const fetchKnowledgeBases = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/knowledge`);
    
    const result = response.data;
    const {code, data, message } = handleApiResponse(result);
    
    if (code !== 200) {
      throw new Error(message || "获取知识库失败");
    }
    
    return {code, data, message};
  } catch (error) {
    console.error('获取知识库出错:', error);
    return [];
  }
};

/**
 * 创建知识库
 * @param {Object} knowledgeBaseData 知识库数据
 * @returns {Promise<Object>} 创建的知识库信息
 */
export const createKnowledgeBase = async (knowledgeBaseData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/knowledge`, knowledgeBaseData);
    
    const result = response.data;
    const { success, data, message } = handleApiResponse(result);
    
    if (!success) {
      return { success: false, message: message || "创建知识库失败" };
    }
    
    return { success: true, data };
  } catch (error) {
    console.error('创建知识库出错:', error);
    return { success: false, message: error.message };
  }
};

/**
 * 获取知识库详情
 * @param {string} knowledgeBaseId 知识库ID
 * @returns {Promise<Object>} 知识库详情
 */
export const getKnowledgeBase = async (knowledgeBaseId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/knowledge/${knowledgeBaseId}`);
    
    const result = response.data;
    const { success, data, message } = handleApiResponse(result);
    
    if (!success) {
      return { success: false, message: message || "获取知识库详情失败" };
    }
    
    return { success: true, data };
  } catch (error) {
    console.error('获取知识库详情出错:', error);
    return { success: false, message: error.message };
  }
};

/**
 * 获取知识库文件列表
 * @param {string} knowledgeBaseName 知识库名称
 * @returns {Promise<Array>} 文件列表
 */
export const getKnowledgeBaseFiles = async (knowledgeBaseName) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/knowledge/${knowledgeBaseName}/files`);
    
    const result = response.data;
    const { success, data, message } = handleApiResponse(result);
    
    if (!success) {
      console.error('获取知识库文件列表失败:', message);
      return [];
    }
    
    return data || [];
  } catch (error) {
    console.error('获取知识库文件列表出错:', error);
    return [];
  }
};

/**
 * 删除知识库
 * @param {string} knowledgeBaseId 知识库ID
 * @returns {Promise<Object>} 删除结果
 */
export const deleteKnowledgeBase = async (knowledgeBaseId) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/knowledge/${knowledgeBaseId}`);
    
    const result = response.data;
    const { success, message } = handleApiResponse(result);
    
    return { success, message };
  } catch (error) {
    console.error('删除知识库出错:', error);
    return { success: false, message: error.message };
  }
};

/**
 * 上传文件到知识库
 * @param {string} knowledgeBaseId 知识库ID
 * @param {File} file 要上传的文件
 * @returns {Promise<Object>} 上传结果
 */
export const uploadFileToKnowledgeBase = async (knowledgeBaseId, file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await axios.post(`${API_BASE_URL}/knowledge/${knowledgeBaseId}/upload`, formData);
    
    const result = response.data;
    const { success, data, message } = handleApiResponse(result);
    
    if (!success) {
      return { success: false, message: message || "上传文件失败" };
    }
    
    return { success: true, data };
  } catch (error) {
    console.error('上传文件出错:', error);
    return { success: false, message: error.message };
  }
};

/**
 * 查询知识库
 * @param {Object} queryData 查询参数
 * @returns {Promise<Object>} 查询结果
 */
export const queryKnowledgeBase = async (queryData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/knowledge/query`, queryData);
    
    const result = response.data;
    const { success, data, message } = handleApiResponse(result);
    
    if (!success) {
      return { success: false, message: message || "查询知识库失败" };
    }
    
    return { success: true, data };
  } catch (error) {
    console.error('查询知识库出错:', error);
    return { success: false, message: error.message };
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
    const response = await axios.get(`${API_BASE_URL}/conversations`);
    return response.data;
  } catch (error) {
    console.error('获取会话历史出错:', error);
    return [];
  }
};

/**
 * 删除会话
 * @param {string} conversationId 会话ID
 * @returns {Promise<Object>} 删除结果
 */
export const deleteConversation = async (conversationId) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/conversations/${conversationId}`);
    return response.data;
  } catch (error) {
    console.error('删除会话出错:', error);
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
    const response = await axios.put(`${API_BASE_URL}/mcp/servers/${serverId}`, serverData);
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
    const response = await axios.post(`${API_BASE_URL}/mcp/servers/${serverId}/test`);
    return response.data;
  } catch (error) {
    console.error('测试MCP服务器连接失败:', error);
    throw error;
  }
}; 