import React, { useState, useEffect, useCallback } from 'react';
import axios from '../api/http';
import { 
  Container, Box, Typography, TextField, Button, List, ListItem, 
  ListItemText, ListItemSecondaryAction, IconButton, Divider, 
  Paper, CircularProgress, Grid, Chip, Dialog, DialogTitle,
  DialogContent, DialogContentText, DialogActions, Alert,
  Card, CardContent, Tooltip, Radio, RadioGroup, FormControlLabel, FormControl,
  FormLabel, Tab, Tabs, Badge, LinearProgress, Switch
} from '@mui/material';
import { 
  Add, Delete, Refresh, ArrowBack, Edit, Check,
  PlayArrow, PowerSettingsNew, Sync, Science, CheckCircle, Error,
  Warning, Circle, Visibility, VisibilityOff, Code, Storage, Psychology, Stop
} from '@mui/icons-material';
import { 
  fetchMCPServers, 
  createMCPServer, 
  updateMCPServer, 
  testMCPServerConnection, 
  fetchMCPServerStatuses, 
  refreshMCPServerConnection, 
  connectMCPServer, 
  disconnectMCPServer, 
  getMCPServerStatus 
} from '../api/index';

// MCP服务器管理组件
const MCPManager = () => {
  // 状态管理
  const [mcpServers, setMcpServers] = useState([]);
  const [serverStatuses, setServerStatuses] = useState([]);
  const [selectedServer, setSelectedServer] = useState(null);
  const [createMode, setCreateMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [serverToDelete, setServerToDelete] = useState(null);
  const [serverLoadingStates, setServerLoadingStates] = useState({}); // 每个服务器的独立loading状态
  const [autoRefresh, setAutoRefresh] = useState(true); // 自动刷新开关
  const [refreshInterval, setRefreshInterval] = useState(null);

  // 表单状态
  const [formData, setFormData] = useState({
    name: '',
    transport: 'stdio',
    command: '',
    args: '',
    env: '',
    url: '',
    active: true
  });

  // 获取服务器状态的颜色和图标
  const getStatusDisplay = useCallback((status) => {
    if (!status) {
      return {
        color: 'default',
        icon: <Circle />,
        text: '未知',
        description: '状态未知'
      };
    }

    // 检查服务器是否激活（从服务器配置中获取）
    const server = mcpServers.find(s => s.id === status.server_id);
    if (!server || !server.active) {
      return {
        color: 'default',
        icon: <Circle />,
        text: '未激活',
        description: '服务器未激活'
      };
    }

    if (status.connected && status.healthy) {
      return {
        color: 'success',
        icon: <CheckCircle />,
        text: '已连接',
        description: '连接正常'
      };
    }

    if (status.status === 'connecting') {
      return {
        color: 'info',
        icon: <CircularProgress size={16} />,
        text: '连接中',
        description: '正在建立连接'
      };
    }

    if (status.connected && !status.healthy) {
      return {
        color: 'warning',
        icon: <Warning />,
        text: '连接异常',
        description: status.error_message || '连接不稳定'
      };
    }

    return {
      color: 'error',
      icon: <Error />,
      text: '连接失败',
      description: status.error_message || '无法连接到服务器'
    };
  }, [mcpServers]);

  // 获取单个服务器状态
  const getServerStatus = useCallback((serverId) => {
    return serverStatuses.find(s => s.server_id === serverId) || {};
  }, [serverStatuses]);

  // 加载服务器列表
  const loadMcpServers = useCallback(async () => {
    try {
      const response = await fetchMCPServers();
      if (response.success) {
      setMcpServers(response.data || []);
      }
    } catch (err) {
      console.error('加载MCP服务器失败:', err);
      setError('加载服务器列表失败：' + (err.response?.data?.detail || err.message));
    }
  }, []);

  // 加载服务器状态
  const loadServerStatuses = useCallback(async () => {
    try {
      const response = await fetchMCPServerStatuses();
      if (response.success) {
        setServerStatuses(response.data || []);
      }
    } catch (err) {
      console.error('加载服务器状态失败:', err);
    }
  }, []);

  // 自动刷新逻辑
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        loadServerStatuses();
      }, 5000); // 每5秒刷新一次状态
      setRefreshInterval(interval);
      return () => clearInterval(interval);
    } else if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
  }, [autoRefresh, loadServerStatuses]);

  // 初始加载
  useEffect(() => {
    loadMcpServers();
      loadServerStatuses();
  }, [loadMcpServers, loadServerStatuses]);

  // 创建服务器相关
  const [serverName, setServerName] = useState('');
  const [serverDescription, setServerDescription] = useState('');
  const [serverUrl, setServerUrl] = useState('');
  const [serverType, setServerType] = useState('stdio'); // stdio, sse, streamableHttp
  const [serverCommand, setServerCommand] = useState('');
  const [serverArgs, setServerArgs] = useState('');
  const [serverEnv, setServerEnv] = useState('');
  const [editMode, setEditMode] = useState(false);
  
  // 当前编辑的选项卡
  const [activeTab, setActiveTab] = useState(0);

  // 选择服务器
  const selectServer = (server) => {
    setSelectedServer(server);
    setServerName(server.name);
    setServerDescription(server.description || '');
    setServerUrl(server.url || '');
    setServerType(server.transport || 'stdio');
    setServerCommand(server.command || '');
    setServerArgs(Array.isArray(server.args) ? server.args.join('\n') : server.args || '');
    setServerEnv(typeof server.env === 'object' ? 
      Object.entries(server.env).map(([key, value]) => `${key}=${value}`).join('\n') : 
      server.env || '');
    setCreateMode(false);
    setEditMode(false);
  };

  // 清除表单
  const clearForm = () => {
    setServerName('');
    setServerDescription('');
    setServerUrl('');
    setServerType('stdio');
    setServerCommand('');
    setServerArgs('');
    setServerEnv('');
  };

  // 启动创建模式
  const startCreateMode = () => {
    setSelectedServer(null);
    clearForm();
    setCreateMode(true);
    setEditMode(false);
    setActiveTab(0);
  };

  // 启动编辑模式
  const startEditMode = () => {
    setEditMode(true);
  };

  // 取消创建/编辑
  const cancelEdit = () => {
    if (selectedServer) {
      selectServer(selectedServer);
    } else {
      clearForm();
    }
    setCreateMode(false);
    setEditMode(false);
  };

  // 创建MCP服务器
  const createServer = async () => {
    if (!serverName.trim()) {
      setError('服务器名称不能为空');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // 处理环境变量字符串转换为对象
      const envObject = {};
      if (serverEnv.trim()) {
        serverEnv.trim().split('\n').forEach(line => {
          if (line.trim()) {
            const [key, ...valueParts] = line.split('=');
            if (key && valueParts.length > 0) {
              envObject[key.trim()] = valueParts.join('=').trim();
            }
          }
        });
      }
      
      // 处理参数字符串转换为数组
      const argsArray = serverArgs.trim() ? 
        serverArgs.trim().split('\n').filter(arg => arg.trim()) : [];
      
      const serverData = {
        name: serverName.trim(),
        description: serverDescription.trim(),
        url: serverUrl.trim(),
        transport: serverType,
        command: serverCommand.trim(),
        args: argsArray,
        env: envObject,
        active: true
      };
      
      const response = await createMCPServer(serverData);
      
      if (response.data) {
        setSuccess('MCP服务器创建成功');
        clearForm();
        setCreateMode(false);
        loadMcpServers();
        loadServerStatuses();
      } else {
        setError('创建MCP服务器失败');
      }
    } catch (err) {
      setError('创建MCP服务器失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // 更新MCP服务器
  const updateServer = async () => {
    if (!selectedServer) return;
    if (!serverName.trim()) {
      setError('服务器名称不能为空');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // 处理环境变量字符串转换为对象
      const envObject = {};
      if (serverEnv.trim()) {
        serverEnv.trim().split('\n').forEach(line => {
          if (line.trim()) {
            const [key, ...valueParts] = line.split('=');
            if (key && valueParts.length > 0) {
              envObject[key.trim()] = valueParts.join('=').trim();
            }
          }
        });
      }
      // 处理参数字符串转换为数组
      const argsArray = serverArgs.trim() ? 
        serverArgs.trim().split('\n').filter(arg => arg.trim()) : [];
      const serverData = {
        name: serverName.trim(),
        description: serverDescription.trim(),
        url: serverUrl.trim(),
        transport: serverType,
        command: serverCommand.trim(),
        args: argsArray,
        env: envObject
      };
      const response = await updateMCPServer(selectedServer.id, serverData);
      const updatedServer = response.data?.data || response.data;
      if (updatedServer) {
        setSuccess('MCP服务器更新成功');
        setEditMode(false);
        loadMcpServers();
        loadServerStatuses();
        selectServer(updatedServer);
      } else {
        setError('更新MCP服务器失败');
      }
    } catch (err) {
      setError('更新MCP服务器失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // 删除MCP服务器
  const deleteServer = async () => {
    if (!serverToDelete) return;
    
    setLoading(true);
    setError(null);
    
    try {
      await axios.delete(`/api/mcp/servers/${serverToDelete.id}?user_specific=true`);
      setSuccess('MCP服务器删除成功');
      setDeleteDialogOpen(false);
      loadMcpServers();
      loadServerStatuses();
      
      if (selectedServer && selectedServer.id === serverToDelete.id) {
        setSelectedServer(null);
        clearForm();
      }
    } catch (err) {
      setError('删除MCP服务器失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
      setServerToDelete(null);
    }
  };

  // 测试服务器连接
  const testConnection = async (server) => {
    if (!server) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await testMCPServerConnection(server.id);

      if (response.data.success) {
        setSuccess('连接测试成功！');
      } else {
        setError('连接测试失败：' + response.data.message);
      }
    } catch (err) {
      setError('连接测试失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // 切换服务器状态(启用/禁用)
  const toggleServerStatus = async (server, active) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await updateMCPServer(server.id, {
        ...server,
        active
      });
      
      if (response.data) {
        setSuccess(`MCP服务器已${active ? '启用' : '禁用'}`);
        loadMcpServers();
        loadServerStatuses();
        
        if (selectedServer && selectedServer.id === server.id) {
          selectServer(response.data);
        }
      } else {
        setError(`${active ? '启用' : '禁用'}MCP服务器失败`);
      }
    } catch (err) {
      setError(`${active ? '启用' : '禁用'}MCP服务器失败：` + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // 处理删除确认对话框
  const openDeleteDialog = (server) => {
    setServerToDelete(server);
    setDeleteDialogOpen(true);
  };

  // Tab切换处理
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  // 状态指示器组件
  const StatusIndicator = ({ status }) => {
    const { active, connected, healthy } = status;
    
    const getStatusColor = () => {
      if (!active) return '#ccc'; // 灰色：未激活
      if (healthy && connected) return '#4caf50'; // 绿色：激活且健康
      if (connected) return '#ff9800'; // 橙色：激活且连接但不健康
      return '#f44336'; // 红色：激活但未连接
    };
    
    const getStatusText = () => {
      if (!active) return '未激活';
      if (healthy && connected) return '在线';
      if (connected) return '连接异常';
      return '离线';
    };
    
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <Box
          sx={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            backgroundColor: getStatusColor(),
            flexShrink: 0
          }}
          title={getStatusText()}
        />
        <Typography 
          variant="caption" 
          sx={{ 
            color: active ? (healthy && connected ? 'success.main' : 'warning.main') : 'text.disabled',
            fontSize: '0.75rem'
          }}
        >
          {getStatusText()}
        </Typography>
      </Box>
    );
  };

  // 状态统计组件
  const StatusSummary = () => {
    const totalServers = mcpServers.length;
    const activeServers = mcpServers.filter(server => server.active).length;
    
    // 修复：在线服务器应该是激活且实际连接的服务器
    const onlineServers = serverStatuses.filter(status => {
      // 找到对应的服务器配置
      const server = mcpServers.find(s => s.id === status.server_id);
      // 只有激活且实际连接健康的才算在线
      return server && server.active && status.connected && status.healthy;
    }).length;
    
    // 修复：激活但未连接的服务器数量
    const activatedButOffline = serverStatuses.filter(status => {
      const server = mcpServers.find(s => s.id === status.server_id);
      return server && server.active && (!status.connected || !status.healthy);
    }).length;
    
    return (
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>服务器状态概览</Typography>
        <Box sx={{ display: 'flex', gap: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="body2" color="text.secondary">总计:</Typography>
            <Chip label={totalServers} size="small" variant="outlined" />
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="body2" color="text.secondary">激活:</Typography>
            <Chip label={activeServers} size="small" color="primary" />
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="body2" color="text.secondary">在线:</Typography>
            <Chip label={onlineServers} size="small" color="success" />
          </Box>
          {activatedButOffline > 0 && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Typography variant="body2" color="text.secondary">离线:</Typography>
              <Chip label={activatedButOffline} size="small" color="warning" />
            </Box>
          )}
        </Box>
      </Paper>
    );
  };

  // 重连单个服务器 - 修复独立loading状态
  const refreshServerConnection = async (server) => {
    if (!server) return;
    
    // 设置该服务器的loading状态
    setServerLoadingStates(prev => ({
      ...prev,
      [server.id]: true
    }));
    setError(null);
    
    try {
      const response = await refreshMCPServerConnection(server.id);
      
      if (response.success || response.code === 200) {
        setSuccess(`服务器 "${server.name}" 重连成功！`);
        // 刷新服务器状态
        loadServerStatuses();
      } else {
        setError(`服务器 "${server.name}" 重连失败：` + (response.message || '未知错误'));
      }
    } catch (err) {
      setError(`服务器 "${server.name}" 重连失败：` + (err.response?.data?.detail || err.message));
    } finally {
      // 清除该服务器的loading状态
      setServerLoadingStates(prev => ({
        ...prev,
        [server.id]: false
      }));
    }
  };

  // 连接服务器
  const connectServer = async (server) => {
    if (!server) return;
    
    setServerLoadingStates(prev => ({
      ...prev,
      [server.id]: true
    }));
    setError(null);
    
    try {
      const response = await connectMCPServer(server.id);
      
      if (response.success || response.code === 200) {
        setSuccess(`服务器 "${server.name}" 连接成功！`);
        loadServerStatuses();
      } else {
        setError(`服务器 "${server.name}" 连接失败：` + (response.message || '未知错误'));
      }
    } catch (err) {
      setError(`服务器 "${server.name}" 连接失败：` + (err.response?.data?.detail || err.message));
    } finally {
      setServerLoadingStates(prev => ({
        ...prev,
        [server.id]: false
      }));
    }
  };

  // 断开服务器连接
  const disconnectServer = async (server) => {
    if (!server) return;
    
    setServerLoadingStates(prev => ({
      ...prev,
      [server.id]: true
    }));
    setError(null);
    
    try {
      const response = await disconnectMCPServer(server.id);
      
      if (response.success || response.code === 200) {
        setSuccess(`服务器 "${server.name}" 已断开连接！`);
        loadServerStatuses();
      } else {
        setError(`服务器 "${server.name}" 断开连接失败：` + (response.message || '未知错误'));
      }
    } catch (err) {
      setError(`服务器 "${server.name}" 断开连接失败：` + (err.response?.data?.detail || err.message));
    } finally {
      setServerLoadingStates(prev => ({
        ...prev,
        [server.id]: false
      }));
    }
  };

  // 切换服务器激活状态
  const toggleServerActive = async (server) => {
    if (!server) return;
    
    setServerLoadingStates(prev => ({
      ...prev,
      [server.id]: true
    }));
    setError(null);
    
    try {
      const updateData = { active: !server.active };
      const response = await updateMCPServer(server.id, updateData);
      
      if (response.success || response.code === 200) {
        setSuccess(`服务器 "${server.name}" ${!server.active ? '已激活' : '已停用'}！`);
        loadMcpServers();
        loadServerStatuses();
      } else {
        setError(`更新服务器状态失败：` + (response.message || '未知错误'));
      }
    } catch (err) {
      setError(`更新服务器状态失败：` + (err.response?.data?.detail || err.message));
    } finally {
      setServerLoadingStates(prev => ({
        ...prev,
        [server.id]: false
      }));
    }
  };

  // 渲染主界面
  return (
    <Container maxWidth="lg" sx={{ mt: 2 }}>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}
      
      <Paper sx={{ mb: 3, p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5">
            {createMode ? '创建MCP服务器' : 
             editMode ? '编辑MCP服务器' : 
             selectedServer ? selectedServer.name : 'MCP服务器管理'}
          </Typography>
          
          <Box>
            {!createMode && !editMode && !selectedServer && (
              <Button 
                variant="contained" 
                color="primary" 
                startIcon={<Add />}
                onClick={startCreateMode}
              >
                添加服务器
              </Button>
            )}
            
            {!createMode && !editMode && selectedServer && (
              <>
                <Button 
                  variant="outlined"
                  sx={{ mr: 1 }}
                  startIcon={<ArrowBack />}
                  onClick={() => setSelectedServer(null)}
                >
                  返回
                </Button>
                <Button 
                  variant="contained" 
                  color="primary"
                  sx={{ mr: 1 }} 
                  startIcon={<Edit />}
                  onClick={startEditMode}
                >
                  编辑
                </Button>
                <Button 
                  variant="outlined"
                  color="info"
                  sx={{ mr: 1 }}
                  startIcon={<Sync />}
                  onClick={() => testConnection(selectedServer)}
                >
                  测试连接
                </Button>
                <Button 
                  variant="outlined"
                  color="secondary"
                  sx={{ mr: 1 }}
                  startIcon={<Delete />}
                  onClick={() => openDeleteDialog(selectedServer)}
                >
                  删除
                </Button>
              </>
            )}
            
            {(createMode || editMode) && (
              <>
                <Button 
                  variant="contained"
                  color="primary"
                  sx={{ mr: 1 }}
                  startIcon={<Check />}
                  onClick={createMode ? createServer : updateServer}
                  disabled={loading}
                >
                  {createMode ? '创建' : '保存'}
                </Button>
                <Button 
                  variant="outlined"
                  onClick={cancelEdit}
                  disabled={loading}
                >
                  取消
                </Button>
              </>
            )}
          </Box>
        </Box>
        
        {loading && <CircularProgress size={24} sx={{ display: 'block', mx: 'auto', my: 2 }} />}
        
        <Box sx={{ display: 'flex' }}>
          {/* 服务器列表 */}
          {!createMode && !selectedServer && (
            <Box sx={{ width: '100%' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6">可用MCP服务器</Typography>
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={autoRefresh}
                        onChange={(e) => setAutoRefresh(e.target.checked)}
                        size="small"
                      />
                    }
                    label="自动刷新"
                  />
                <Button 
                  startIcon={<Refresh />}
                  onClick={() => {
                    loadMcpServers();
                    loadServerStatuses();
                  }}
                  disabled={loading}
                    size="small"
                >
                    手动刷新
                </Button>
                </Box>
              </Box>
              
              {/* 状态概览 */}
              {mcpServers.length > 0 && <StatusSummary />}
              
              {/* 控制面板 */}
              <Paper sx={{ p: 2, mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="h6">MCP服务器控制面板</Typography>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={autoRefresh}
                          onChange={(e) => setAutoRefresh(e.target.checked)}
                          size="small"
                        />
                      }
                      label="自动刷新"
                    />
                    <Button 
                      startIcon={<Refresh />}
                      onClick={() => {
                        loadMcpServers();
                        loadServerStatuses();
                      }}
                      disabled={loading}
                      size="small"
                    >
                      手动刷新
                    </Button>
                            </Box>
                </Box>
              </Paper>
              
              {/* 服务器列表 */}
              <List>
                {mcpServers.map((server) => {
                  const status = getServerStatus(server.id);
                  const statusDisplay = getStatusDisplay(status);
                  const isLoading = serverLoadingStates[server.id];
                  
                  return (
                    <Card key={server.id} sx={{ mb: 2 }}>
                      <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          {/* 服务器信息 */}
                          <Box sx={{ flex: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                              <Typography variant="h6">{server.name}</Typography>
                              <Chip 
                                icon={statusDisplay.icon}
                                label={statusDisplay.text}
                                color={statusDisplay.color}
                                size="small"
                              />
                              {server.active && (
                                <Chip 
                                  label="已激活" 
                                  color="primary" 
                                  size="small" 
                                  variant="outlined"
                                />
                              )}
                              {/* 等待者数量显示 */}
                              {status.waiting_count > 0 && (
                                <Chip 
                                  label={`等待中: ${status.waiting_count}`}
                                  color="warning" 
                                  size="small" 
                                  variant="outlined"
                                  icon={<CircularProgress size={12} />}
                                />
                              )}
                            </Box>
                            
                            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                              传输类型: {server.transport} | 
                              {server.transport === 'stdio' && server.command && ` 命令: ${server.command}`}
                              {server.transport !== 'stdio' && server.url && ` URL: ${server.url}`}
                            </Typography>
                            
                            {status.error_message && (
                              <Alert severity="error" sx={{ mt: 1 }}>
                                {status.error_message}
                              </Alert>
                            )}
                            
                            {status.last_ping && (
                              <Typography variant="caption" color="text.secondary">
                                最后连接: {new Date(status.last_ping).toLocaleString()}
                              </Typography>
                            )}
                          </Box>
                          
                          {/* 控制按钮 */}
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 120 }}>
                            {/* 激活/停用开关 */}
                            <FormControlLabel
                              control={
                                <Switch
                                  checked={server.active}
                                  onChange={() => toggleServerActive(server)}
                                  disabled={isLoading}
                                  size="small"
                                />
                              }
                              label={server.active ? "已激活" : "已停用"}
                              labelPlacement="start"
                            />
                            
                            {/* 连接控制按钮 */}
                            {server.active && (
                              <Box sx={{ display: 'flex', gap: 0.5 }}>
                                {!status.connected ? (
                                  <Tooltip title={status.waiting_count > 0 ? `有 ${status.waiting_count} 个操作在等待，请稍后` : "连接服务器"}>
                            <IconButton 
                                      onClick={() => connectServer(server)}
                                      disabled={isLoading || status.waiting_count > 0}
                                      color="primary"
                                      size="small"
                            >
                                      {isLoading ? <CircularProgress size={16} /> : <PlayArrow />}
                            </IconButton>
                          </Tooltip>
                                ) : (
                                  <Tooltip title={status.waiting_count > 0 ? `有 ${status.waiting_count} 个操作在等待，请稍后` : "断开连接"}>
                            <IconButton 
                                      onClick={() => disconnectServer(server)}
                                      disabled={isLoading || status.waiting_count > 0}
                                      color="error"
                                      size="small"
                                    >
                                      {isLoading ? <CircularProgress size={16} /> : <Stop />}
                                    </IconButton>
                                  </Tooltip>
                                )}
                                
                                <Tooltip title={status.waiting_count > 0 ? `有 ${status.waiting_count} 个操作在等待，请稍后` : "重新连接"}>
                                  <IconButton
                                    onClick={() => refreshServerConnection(server)}
                                    disabled={isLoading || status.waiting_count > 0}
                                    color="warning"
                                    size="small"
                            >
                                    {isLoading ? <CircularProgress size={16} /> : <Sync />}
                            </IconButton>
                          </Tooltip>
                                
                                <Tooltip title={status.waiting_count > 0 ? `有 ${status.waiting_count} 个操作在等待，请稍后` : "测试连接"}>
                            <IconButton 
                                    onClick={() => testConnection(server)}
                                    disabled={isLoading || status.waiting_count > 0}
                                    color="info"
                                    size="small"
                                  >
                                    {isLoading ? <CircularProgress size={16} /> : <Science />}
                                  </IconButton>
                                </Tooltip>
                              </Box>
                            )}
                            
                            {/* 编辑和删除按钮 */}
                            <Box sx={{ display: 'flex', gap: 0.5 }}>
                              <Tooltip title="编辑服务器">
                                <IconButton
                                  onClick={() => selectServer(server)}
                                  disabled={isLoading}
                                  size="small"
                            >
                              <Edit />
                            </IconButton>
                          </Tooltip>
                              
                              <Tooltip title="删除服务器">
                            <IconButton 
                                  onClick={() => {
                                    setServerToDelete(server);
                                    setDeleteDialogOpen(true);
                              }}
                                  disabled={isLoading}
                                  color="error"
                                  size="small"
                            >
                              <Delete />
                            </IconButton>
                          </Tooltip>
                            </Box>
                          </Box>
                        </Box>
                      </CardContent>
                    </Card>
                  );
                })}
                </List>
            </Box>
          )}
          
          {/* 创建/编辑表单 */}
          {(createMode || editMode || selectedServer) && (
            <Box sx={{ width: '100%' }}>
              {(createMode || editMode) ? (
                <Box sx={{ width: '100%' }}>
                  <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                    <Tabs value={activeTab} onChange={handleTabChange}>
                      <Tab label="通用" />
                      <Tab label="参数" />
                      <Tab label="环境变量" />
                    </Tabs>
                  </Box>
                  
                  {/* 通用信息 */}
                  {activeTab === 0 && (
                    <Box sx={{ p: 2 }}>
                      <TextField
                        label="名称"
                        fullWidth
                        required
                        margin="normal"
                        value={serverName}
                        onChange={(e) => setServerName(e.target.value)}
                        disabled={loading}
                      />
                      
                      <TextField
                        label="描述"
                        fullWidth
                        multiline
                        rows={2}
                        margin="normal"
                        value={serverDescription}
                        onChange={(e) => setServerDescription(e.target.value)}
                        disabled={loading}
                      />
                      
                      <TextField
                        label="URL"
                        fullWidth
                        margin="normal"
                        value={serverUrl}
                        onChange={(e) => setServerUrl(e.target.value)}
                        disabled={loading}
                        placeholder="http://localhost:3030"
                      />
                      
                      <FormControl component="fieldset" margin="normal">
                        <FormLabel component="legend">类型</FormLabel>
                        <RadioGroup 
                          value={serverType} 
                          onChange={(e) => setServerType(e.target.value)}
                          row
                        >
                          <FormControlLabel 
                            value="stdio" 
                            control={<Radio />} 
                            label="标准输入/输出 (stdio)" 
                            disabled={loading}
                          />
                          <FormControlLabel 
                            value="sse" 
                            control={<Radio />} 
                            label="服务器发送事件 (sse)" 
                            disabled={loading}
                          />
                          <FormControlLabel 
                            value="streamableHttp" 
                            control={<Radio />} 
                            label="可流式传输的HTTP (streamableHttp)" 
                            disabled={loading}
                          />
                        </RadioGroup>
                      </FormControl>
                    </Box>
                  )}
                  
                  {/* 参数设置 */}
                  {activeTab === 1 && (
                    <Box sx={{ p: 2 }}>
                      <TextField
                        label="命令"
                        fullWidth
                        margin="normal"
                        value={serverCommand}
                        onChange={(e) => setServerCommand(e.target.value)}
                        disabled={loading}
                        placeholder="uvx or npx"
                      />
                      
                      <TextField
                        label="参数"
                        fullWidth
                        multiline
                        rows={4}
                        margin="normal"
                        value={serverArgs}
                        onChange={(e) => setServerArgs(e.target.value)}
                        disabled={loading}
                        placeholder="arg1&#10;arg2"
                      />
                    </Box>
                  )}
                  
                  {/* 环境变量 */}
                  {activeTab === 2 && (
                    <Box sx={{ p: 2 }}>
                      <TextField
                        label="环境变量"
                        fullWidth
                        multiline
                        rows={4}
                        margin="normal"
                        value={serverEnv}
                        onChange={(e) => setServerEnv(e.target.value)}
                        disabled={loading}
                        placeholder="KEY1=value1&#10;KEY2=value2"
                      />
                    </Box>
                  )}
                </Box>
              ) : selectedServer ? (
                <Card>
                  <CardContent>
                    <Typography variant="h6">服务器信息</Typography>
                    <Divider sx={{ my: 1 }} />
                    
                    <Grid container spacing={2}>
                      <Grid item xs={12} sm={6}>
                        <Typography variant="subtitle2" color="textSecondary">名称</Typography>
                        <Typography variant="body1">{selectedServer.name}</Typography>
                      </Grid>
                      
                      <Grid item xs={12} sm={6}>
                        <Typography variant="subtitle2" color="textSecondary">状态</Typography>
                        <Chip 
                          label={selectedServer.active ? "已启用" : "已禁用"} 
                          color={selectedServer.active ? "success" : "default"} 
                          size="small"
                        />
                      </Grid>
                      
                      <Grid item xs={12}>
                        <Typography variant="subtitle2" color="textSecondary">URL</Typography>
                        <Typography variant="body1">{selectedServer.url}</Typography>
                      </Grid>
                      
                      <Grid item xs={12}>
                        <Typography variant="subtitle2" color="textSecondary">描述</Typography>
                        <Typography variant="body1">
                          {selectedServer.description || "无描述"}
                        </Typography>
                      </Grid>
                      
                      <Grid item xs={12} sm={6}>
                        <Typography variant="subtitle2" color="textSecondary">类型</Typography>
                        <Typography variant="body1">
                          {selectedServer.transport === 'stdio' ? '标准输入/输出 (stdio)' :
                           selectedServer.transport === 'sse' ? '服务器发送事件 (sse)' :
                           selectedServer.transport === 'streamableHttp' ? '可流式传输的HTTP' : '未设置'}
                        </Typography>
                      </Grid>
                      
                      <Grid item xs={12} sm={6}>
                        <Typography variant="subtitle2" color="textSecondary">创建时间</Typography>
                        <Typography variant="body1">
                          {selectedServer.created_at ? new Date(selectedServer.created_at).toLocaleString() : "未知"}
                        </Typography>
                      </Grid>
                      
                      {selectedServer.command && (
                        <Grid item xs={12}>
                          <Typography variant="subtitle2" color="textSecondary">命令</Typography>
                          <Typography variant="body1">{selectedServer.command}</Typography>
                        </Grid>
                      )}
                      
                      {selectedServer.args && (
                        <Grid item xs={12}>
                          <Typography variant="subtitle2" color="textSecondary">参数</Typography>
                          <Typography variant="body1" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                            {Array.isArray(selectedServer.args) ? 
                              selectedServer.args.join('\n') : 
                              selectedServer.args}
                          </Typography>
                        </Grid>
                      )}
                      
                      {selectedServer.env && (
                        <Grid item xs={12}>
                          <Typography variant="subtitle2" color="textSecondary">环境变量</Typography>
                          <Typography variant="body1" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                            {typeof selectedServer.env === 'object' ? 
                              Object.entries(selectedServer.env).map(([key, value]) => 
                                `${key}=${value}`
                              ).join('\n') : 
                              JSON.stringify(selectedServer.env, null, 2)}
                          </Typography>
                        </Grid>
                      )}
                    </Grid>
                  </CardContent>
                </Card>
              ) : null}
            </Box>
          )}
        </Box>
      </Paper>
      
      {/* 删除确认对话框 */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>确认删除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            确定要删除MCP服务器 "{serverToDelete?.name}" 吗？此操作不可撤销。
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>取消</Button>
          <Button onClick={deleteServer} color="error" autoFocus>
            删除
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default MCPManager; 