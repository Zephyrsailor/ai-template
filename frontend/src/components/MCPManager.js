import React, { useState, useEffect } from 'react';
import axios from '../api/http';
import { 
  Container, Box, Typography, TextField, Button, List, ListItem, 
  ListItemText, ListItemSecondaryAction, IconButton, Divider, 
  Paper, CircularProgress, Grid, Chip, Dialog, DialogTitle,
  DialogContent, DialogContentText, DialogActions, Alert,
  Card, CardContent, InputAdornment, Collapse, 
  Tooltip, Radio, RadioGroup, FormControlLabel, FormControl,
  FormLabel, Tab, Tabs
} from '@mui/material';
import { 
  Add, Delete, Refresh, ArrowBack, Edit, Check,
  PlayArrow, Settings, PowerSettingsNew
} from '@mui/icons-material';

// MCP服务器管理组件
const MCPManager = () => {
  // 状态管理
  const [mcpServers, setMcpServers] = useState([]);
  const [selectedServer, setSelectedServer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  // 创建服务器相关
  const [serverName, setServerName] = useState('');
  const [serverDescription, setServerDescription] = useState('');
  const [serverUrl, setServerUrl] = useState('');
  const [serverType, setServerType] = useState('stdio'); // stdio, sse, streamableHttp
  const [serverCommand, setServerCommand] = useState('');
  const [serverArgs, setServerArgs] = useState('');
  const [serverEnv, setServerEnv] = useState('');
  const [createMode, setCreateMode] = useState(false);
  const [editMode, setEditMode] = useState(false);
  
  // 当前编辑的选项卡
  const [activeTab, setActiveTab] = useState(0);
  
  // 删除确认
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [serverToDelete, setServerToDelete] = useState(null);

  // 加载MCP服务器列表
  const loadMcpServers = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get('/api/mcp/servers/');
      setMcpServers(response.data.data || []);
    } catch (err) {
      setError('加载MCP服务器列表失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    loadMcpServers();
  }, []);

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
      
      const response = await axios.post('/api/mcp/servers/', serverData);
      
      if (response.data) {
        setSuccess('MCP服务器创建成功');
        clearForm();
        setCreateMode(false);
        loadMcpServers();
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
      
      const response = await axios.put(`/api/mcp/servers/${selectedServer.id}`, serverData);
      
      if (response.data) {
        setSuccess('MCP服务器更新成功');
        setEditMode(false);
        loadMcpServers();
        selectServer(response.data.data);
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
      await axios.delete(`/api/mcp/servers/${serverToDelete.id}`);
      setSuccess('MCP服务器删除成功');
      setDeleteDialogOpen(false);
      loadMcpServers();
      
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
      const response = await axios.post(`/api/mcp/servers/${server.id}/test`);

      if (response.data.data.success) {
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
      const response = await axios.put(`/api/mcp/servers/${server.id}`, {
        ...server,
        active
      });
      
      if (response.data) {
        setSuccess(`MCP服务器已${active ? '启用' : '禁用'}`);
        loadMcpServers();
        
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
                  color="secondary"
                  sx={{ mr: 1 }}
                  startIcon={<Delete />}
                  onClick={() => openDeleteDialog(selectedServer)}
                >
                  删除
                </Button>
                <Button 
                  variant="outlined"
                  color="info"
                  startIcon={<PlayArrow />}
                  onClick={() => testConnection(selectedServer)}
                >
                  测试连接
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
                <Button 
                  startIcon={<Refresh />}
                  onClick={loadMcpServers}
                  disabled={loading}
                >
                  刷新
                </Button>
              </Box>
              
              {mcpServers.length === 0 ? (
                <Paper sx={{ p: 3, textAlign: 'center' }}>
                  <Typography color="textSecondary">
                    暂无MCP服务器，请点击"添加服务器"按钮创建
                  </Typography>
                </Paper>
              ) : (
                <List>
                  {mcpServers.map((server) => (
                    <React.Fragment key={server.id}>
                      <ListItem 
                        button 
                        onClick={() => selectServer(server)}
                        selected={selectedServer?.id === server.id}
                      >
                        <ListItemText 
                          primary={server.name} 
                          secondary={
                            <React.Fragment>
                              <Typography component="span" variant="body2" color="textPrimary">
                                {server.url}
                              </Typography>
                              <br />
                              {server.description}
                            </React.Fragment>
                          } 
                        />
                        <ListItemSecondaryAction>
                          <Tooltip title={server.active ? '已启用' : '已禁用'}>
                            <IconButton 
                              edge="end" 
                              color={server.active ? 'success' : 'default'}
                              onClick={() => toggleServerStatus(server, !server.active)}
                            >
                              <PowerSettingsNew />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="编辑">
                            <IconButton 
                              edge="end" 
                              onClick={(e) => {
                                e.stopPropagation();
                                selectServer(server);
                                startEditMode();
                              }}
                            >
                              <Edit />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="删除">
                            <IconButton 
                              edge="end" 
                              color="error"
                              onClick={(e) => {
                                e.stopPropagation();
                                openDeleteDialog(server);
                              }}
                            >
                              <Delete />
                            </IconButton>
                          </Tooltip>
                        </ListItemSecondaryAction>
                      </ListItem>
                      <Divider />
                    </React.Fragment>
                  ))}
                </List>
              )}
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