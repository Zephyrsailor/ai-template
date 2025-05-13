/**
 * 认证API模块 - 处理用户认证相关操作
 */

import axios from './http';

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
    // 标准格式响应
    return {
      success: response.code >= 200 && response.code < 300,
      code: response.code,
      data: response.data,
      message: response.message
    };
  }
  
  // 其他格式，直接返回
  return {
    success: true,
    data: response,
    message: ""
  };
};

/**
 * 设置认证令牌，用于后续请求
 * @param {string} token 认证令牌
 */
export const setAuthToken = (token) => {
  console.log('设置认证令牌:', token ? `${token.substring(0, 10)}...` : 'null');
  
  if (token) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    localStorage.setItem('authToken', token);
    console.log('认证令牌已设置到axios和localStorage');
  } else {
    delete axios.defaults.headers.common['Authorization'];
    localStorage.removeItem('authToken');
    console.log('认证令牌已清除');
  }
};

/**
 * 初始化认证令牌
 */
export const initAuthToken = () => {
  const token = localStorage.getItem('authToken');
  console.log('初始化认证令牌, localStorage中token存在:', !!token);
  
  if (token) {
    setAuthToken(token);
    return true;
  }
  return false;
};

/**
 * 用户登录
 * @param {string} username 用户名
 * @param {string} password 密码
 * @returns {Promise<Object>} 登录结果
 */
export const login = async (username, password) => {
  try {
    // 1. 创建表单数据
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    // 2. 发送登录请求
    console.log(`登录请求: ${username}`);
    const response = await axios.post(`${API_BASE_URL}/auth/login`, formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    console.log('登录响应:', response);
    
    // 3. 处理响应结果
    if (response.data && response.data.data && response.data.data.access_token) {
      const token = response.data.data.access_token;
      
      // 4. 保存token到localStorage和axios
      localStorage.setItem('authToken', token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      console.log('认证令牌已保存', token.substring(0, 15) + '...');
      
      return { 
        success: true, 
        data: response.data.data,
        message: '登录成功'
      };
    }
    
    // 登录失败 - 服务器返回了结果，但没有token
    return { 
      success: false, 
      message: response.data?.message || '登录失败，未返回有效令牌'
    };
  } catch (error) {
    // 登录失败 - 请求出错
    console.error('登录请求失败:', error);
    return { 
      success: false, 
      message: error.response?.data?.detail || error.message || '登录失败',
      error: error
    };
  }
};

/**
 * 用户注册
 * @param {Object} userData 用户数据
 * @returns {Promise<Object>} 注册结果
 */
export const register = async (userData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/auth/register`, userData);
    return handleApiResponse(response.data);
  } catch (error) {
    console.error('注册失败:', error);
    return { 
      success: false, 
      message: error.response?.data?.message || error.message || '注册失败'
    };
  }
};

/**
 * 获取当前用户信息
 * @returns {Promise<Object>} 用户信息
 */
export const getCurrentUser = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/auth/me`);
    return handleApiResponse(response.data);
  } catch (error) {
    console.error('获取用户信息失败:', error);
    return { success: false, message: '获取用户信息失败' };
  }
};

/**
 * 修改密码
 * @param {string} currentPassword 当前密码
 * @param {string} newPassword 新密码
 * @returns {Promise<Object>} 修改结果
 */
export const changePassword = async (currentPassword, newPassword) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/auth/change-password`, {
      current_password: currentPassword,
      new_password: newPassword
    });
    return handleApiResponse(response.data);
  } catch (error) {
    console.error('修改密码失败:', error);
    return { 
      success: false, 
      message: error.response?.data?.message || error.message || '修改密码失败'
    };
  }
};

/**
 * 用户退出登录
 */
export const logout = () => {
  setAuthToken(null);
}; 