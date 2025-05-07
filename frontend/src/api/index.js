/**
 * 获取MCP服务器列表
 * @param {boolean} activeOnly 是否只返回激活的服务器
 * @returns {Promise<Object>} 服务器列表响应
 */
export async function fetchMCPServers(activeOnly = false) {
  try {
    const response = await fetch(`/api/mcp/servers?active_only=${activeOnly}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch MCP servers:', error);
    throw error;
  }
} 