/**
 * API模块 - 处理与后端的通信
 */

// 后端API基础URL
const API_BASE_URL = '/api';

/**
 * 获取知识库列表
 * @returns {Promise<Object>} 包含知识库列表的响应对象
 */
export const fetchKnowledgeBases = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/knowledge/list`);
    if (!response.ok) {
      throw new Error(`获取知识库失败: ${response.status} ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('获取知识库出错:', error);
    return { success: false, message: error.message };
  }
}; 