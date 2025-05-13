import axios from 'axios';

// 创建一个简单的axios实例，完全依赖代理转发
const instance = axios.create({
  timeout: 30000
});

// 拦截器：在每次请求前添加认证token
instance.interceptors.request.use(
  config => {
    const token = localStorage.getItem('authToken');
    console.log(`[Request Interceptor] URL: ${config.url}`);
    console.log(`[Request Interceptor] Method: ${config.method.toUpperCase()}`);
    console.log(`[Request Interceptor] Token from localStorage: ${token ? token.substring(0,15) + '...' : 'null'}`);
    
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
      console.log(`[Request Interceptor] Authorization header SET for ${config.url}`);
    } else {
      delete config.headers['Authorization'];
      console.warn(`[Request Interceptor] Authorization header DELETED or not set for ${config.url} (token not found)`);
    }

    // Content-Type handling (important for FormData vs JSON)
    if (config.data instanceof FormData) {
      // Let browser set Content-Type for FormData
      delete config.headers['Content-Type'];
    } else if (config.headers['Content-Type'] === undefined && !(config.method === 'get' || config.method === 'delete')) {
      // Set default Content-Type for POST/PUT/PATCH if not already set and not FormData
      config.headers['Content-Type'] = 'application/json';
    }
    
    console.log(`[Request Interceptor] Final headers for ${config.url}:`, JSON.parse(JSON.stringify(config.headers)));
    return config;
  },
  error => {
    console.error('[Request Interceptor] Error:', error);
    return Promise.reject(error);
  }
);

// 添加响应拦截器
instance.interceptors.response.use(
  (response) => {
    console.log(`[Response Interceptor] Success response for ${response.config.url}:`, {
      status: response.status,
      statusText: response.statusText
    });
    return response;
  },
  (error) => {
    console.error(`[Response Interceptor] Error for URL: ${error.config?.url}`, error.response?.status, error.response?.data);
    
    // 处理401错误
    if (error.response && error.response.status === 401) {
      console.error('====== AUTHENTICATION FAILURE DETECTED ======');
      console.error('URL:', error.config?.url);
      console.error('Method:', error.config?.method?.toUpperCase());
      console.error('Headers:', error.config?.headers);
      console.error('Error data:', error.response?.data);
      
      // 如果是token失效，可以在这里处理
      if (error.response.data.detail === "认证凭据无效或已过期") {
        console.warn('Token expired, clearing authentication data');
        // localStorage.removeItem('authToken'); // 取消注释以自动清除过期token
      }
    }
    return Promise.reject(error);
  }
);

// 导出axios实例
export default instance; 