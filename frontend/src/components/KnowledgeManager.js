import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Container, Box, Typography, TextField, Button, List, ListItem, 
  ListItemText, ListItemSecondaryAction, IconButton, Divider, 
  Paper, CircularProgress, Grid, Chip, Dialog, DialogTitle,
  DialogContent, DialogContentText, DialogActions, Alert,
  Card, CardContent, InputAdornment, Collapse, DialogProps,
  Tooltip, Fab
} from '@mui/material';
import { 
  Add, Delete, Upload, Refresh, Folder, Description,
  Search, ExpandMore, ExpandLess, ContentCopy, Close,
  InfoOutlined, ArrowBack 
} from '@mui/icons-material';

// 知识库管理组件
const KnowledgeManager = () => {
  // 状态管理
  const [knowledgeBases, setKnowledgeBases] = useState([]);
  const [selectedKnowledge, setSelectedKnowledge] = useState(null);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  // 查询相关状态
  const [queryText, setQueryText] = useState('');
  const [queryResults, setQueryResults] = useState([]);
  const [isQuerying, setIsQuerying] = useState(false);
  const [queryError, setQueryError] = useState(null);
  const [queryDialogOpen, setQueryDialogOpen] = useState(false);
  const [topK, setTopK] = useState(5);
  
  // 创建知识库相关
  const [newKnowledgeName, setNewKnowledgeName] = useState('');
  const [newKnowledgeDesc, setNewKnowledgeDesc] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  
  // 上传相关
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const [uploadProgress, setUploadProgress] = useState(false);
  
  // 删除确认
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState(null);
  const [deleteType, setDeleteType] = useState(''); // 'knowledge' 或 'file'

  // 加载知识库列表
  const loadKnowledgeBases = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get('/api/knowledge');
      if (response.data.code === 200) {
        // 使用新格式
        setKnowledgeBases(response.data.data || []);
      }  else {
        setKnowledgeBases([]);
      }
      
      if (selectedKnowledge) {
        // 如果已选择了一个知识库，更新它的信息
        const knowledgeBases = response.data.code === 200 ? 
          (response.data.data || []) : 
          (response.data || []);
        
        const updated = knowledgeBases.find(kb => kb.name === selectedKnowledge.name);
        if (updated) {
          setSelectedKnowledge(updated);
          loadFiles(updated.name);
        }
      }
    } catch (err) {
      setError('加载知识库列表失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // 加载文件列表
  const loadFiles = async (knowledgeName) => {
    if (!knowledgeName) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(`/api/knowledge/${knowledgeName}/files`);
      if (response.data.code === 200) {
        setFiles(response.data.data || []);
      } else {
        setError('加载文件列表失败：' + response.data.message);
        setFiles([]);
      }
    } catch (err) {
      setError('加载文件列表失败：' + (err.response?.data?.detail || err.message));
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  // 选择知识库
  const selectKnowledge = (knowledge) => {
    setSelectedKnowledge(knowledge);
    loadFiles(knowledge.name);
    // 清空之前的查询结果
    setQueryResults([]);
    setQueryText('');
  };

  // 创建知识库
  const createKnowledge = async () => {
    if (!newKnowledgeName.trim()) {
      setError('知识库名称不能为空');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post('/api/knowledge', {
        name: newKnowledgeName.trim(),
        description: newKnowledgeDesc.trim()
      });
      
      if (response.data.code === 200) {
        setSuccess('知识库创建成功');
        setNewKnowledgeName('');
        setNewKnowledgeDesc('');
        setCreateDialogOpen(false);
        loadKnowledgeBases();
      } else {
        setError('创建知识库失败：' + response.data.message);
      }
    } catch (err) {
      setError('创建知识库失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // 上传文件
  const uploadFiles = async (files) => {
    if (!selectedKnowledge) {
      setError('请先选择一个知识库');
      return;
    }
    
    if (!files || files.length === 0) {
      return;
    }
    
    setUploadProgress(true);
    setError(null);
    
    try {
      // 创建FormData对象
      const formData = new FormData();
      
      // 单个文件和多个文件使用不同的API
      if (files.length === 1) {
        formData.append('file', files[0]);
        
        const response = await axios.post(
          `/api/knowledge/${selectedKnowledge.name}/upload`,
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data'
            }
          }
        );
        
        if (response.data.code === 200) {
          setSuccess(`文件 ${files[0].name} 上传成功，正在处理...`);
        } else {
          setError('上传文件失败：' + response.data.message);
        }
      } else {
        // 多个文件
        for (let i = 0; i < files.length; i++) {
          formData.append('files', files[i]);
        }
        
        const response = await axios.post(
          `/api/knowledge/${selectedKnowledge.name}/upload-multiple`,
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data'
            }
          }
        );
        
        if (response.data.code === 200) {
          setSuccess(response.data.message);
        } else {
          setError('上传文件失败：' + response.data.message);
        }
      }
      
      // 重新加载知识库和文件列表
      loadKnowledgeBases();
    } catch (err) {
      setError('上传文件失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setUploadProgress(false);
    }
  };

  // 点击文件上传按钮
  const handleFileUploadClick = () => {
    fileInputRef.current.click();
  };

  // 文件选择变化
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadFiles(e.target.files);
    }
  };

  // 文件夹上传处理
  const handleFolderUploadClick = () => {
    // 由于安全限制，HTML不能直接获取用户选择的文件夹路径
    // 这里我们使用WebkitdirectoryProperty来上传文件夹中的所有文件
    folderInputRef.current.click();
  };

  // 文件夹内容变更
  const handleFolderChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadFiles(e.target.files);
    }
  };

  // 删除知识库
  const deleteKnowledge = async () => {
    if (!itemToDelete) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.delete(`/api/knowledge/${itemToDelete.id}`);
      
      if (response.data.code === 200) {
        setSuccess(`知识库 ${itemToDelete.name} 已删除`);
        if (selectedKnowledge && selectedKnowledge.name === itemToDelete.name) {
          setSelectedKnowledge(null);
          setFiles([]);
        }
        loadKnowledgeBases();
      } else {
        setError('删除知识库失败：' + response.data.message);
      }
    } catch (err) {
      setError('删除知识库失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
      setDeleteDialogOpen(false);
      setItemToDelete(null);
    }
  };

  // 删除文件
  const deleteFile = async () => {
    if (!selectedKnowledge || !itemToDelete) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.delete(`/api/knowledge/${selectedKnowledge.name}/files/${itemToDelete.id}`);
      
      if (response.data.code === 200) {
        setSuccess(`文件 ${itemToDelete.file_name} 已删除`);
        loadFiles(selectedKnowledge.name);
        loadKnowledgeBases();  // 更新知识库信息
      } else {
        setError('删除文件失败：' + response.data.message);
      }
    } catch (err) {
      setError('删除文件失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
      setDeleteDialogOpen(false);
      setItemToDelete(null);
    }
  };

  // 确认删除对话框
  const handleDeleteConfirm = () => {
    if (deleteType === 'knowledge') {
      deleteKnowledge();
    } else if (deleteType === 'file') {
      deleteFile();
    }
  };

  // 重建索引
  const rebuildIndex = async () => {
    if (!selectedKnowledge) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post(`/api/knowledge/${selectedKnowledge.name}/rebuild`);
      
      if (response.data.code === 200) {
        setSuccess(response.data.message);
        loadKnowledgeBases();
      } else {
        setError('重建索引失败：' + response.data.message);
      }
    } catch (err) {
      setError('重建索引失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };
  
  // 查询知识库
  const queryKnowledge = async () => {
    if (!selectedKnowledge || !queryText.trim()) {
      setQueryError('请选择知识库并输入查询内容');
      return;
    }
    
    setIsQuerying(true);
    setQueryError(null);
    
    try {
      const response = await axios.post(`/api/knowledge/${selectedKnowledge.name}/query`, {
        query: queryText.trim(),
        top_k: topK
      });
      
      if (response.data.code === 200) {
        const results = response.data.data || [];
        
        // 处理每个结果，确保分数正确格式化
        const formattedResults = results.map(result => {
          // 使用服务器提供的score，后端已经处理好了
          const score = typeof result.score === 'number' ? result.score : parseFloat(result.score || '0');
          
          return {
            ...result,
            score: isNaN(score) ? 0 : score,
            // 保留原始分数用于显示
            rawScore: result.raw_score || result.rawScore || result.score
          };
        });
        
        setQueryResults(formattedResults);
        
        if (formattedResults.length === 0) {
          setQueryError('没有找到相关内容');
        }
      } else {
        setQueryError('查询失败：' + response.data.message);
      }
    } catch (err) {
      setQueryError('查询失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setIsQuerying(false);
    }
  };
  
  // 打开查询对话框
  const openQueryDialog = () => {
    setQueryDialogOpen(true);
    setQueryResults([]);
    setQueryError(null);
  };
  
  // 关闭查询对话框
  const closeQueryDialog = () => {
    setQueryDialogOpen(false);
  };
  
  // 复制文本到剪贴板
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setSuccess('已复制到剪贴板');
  };

  // 首次加载
  useEffect(() => {
    loadKnowledgeBases();
  }, []);

  // 清除提示消息
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        知识库管理
      </Typography>
      
      {/* 错误和成功提示 */}
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
      
      <Grid container spacing={3}>
        {/* 知识库列表 */}
        <Grid item xs={12} md={4}>
          <Paper
            sx={{
              p: 2,
              display: 'flex',
              flexDirection: 'column',
              height: 500,
              overflow: 'auto'
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">知识库列表</Typography>
              <Button 
                startIcon={<Add />}
                variant="contained"
                color="primary"
                size="small"
                onClick={() => setCreateDialogOpen(true)}
              >
                创建
              </Button>
            </Box>
            
            <Divider sx={{ mb: 2 }} />
            
            {loading && knowledgeBases.length === 0 ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                <CircularProgress />
              </Box>
            ) : (
              <List>
                {knowledgeBases.length === 0 ? (
                  <ListItem>
                    <ListItemText primary="暂无知识库" />
                  </ListItem>
                ) : (
                  knowledgeBases.map((kb) => (
                    <ListItem 
                      key={kb.name}
                      button
                      selected={selectedKnowledge && selectedKnowledge.name === kb.name}
                      onClick={() => selectKnowledge(kb)}
                    >
                      <ListItemText 
                        primary={kb.name} 
                        secondary={`${kb.file_count}个文件 / ${kb.document_count}个文档块`}
                      />
                      <ListItemSecondaryAction>
                        <IconButton 
                          edge="end"
                          onClick={() => {
                            setItemToDelete(kb);
                            setDeleteType('knowledge');
                            setDeleteDialogOpen(true);
                          }}
                        >
                          <Delete />
                        </IconButton>
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))
                )}
              </List>
            )}
          </Paper>
        </Grid>
        
        {/* 文件列表 */}
        <Grid item xs={12} md={8}>
          <Paper
            sx={{
              p: 2,
              display: 'flex',
              flexDirection: 'column',
              height: 500,
              overflow: 'auto'
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                {selectedKnowledge ? `${selectedKnowledge.name} 的文件` : '文件列表'}
              </Typography>
              <Box>
                {selectedKnowledge && (
                  <>
                    <Button
                      startIcon={<Upload />}
                      variant="contained"
                      color="primary"
                      size="small"
                      onClick={handleFileUploadClick}
                      sx={{ mr: 1 }}
                      disabled={uploadProgress}
                    >
                      上传文件
                    </Button>
                    <Button
                      startIcon={<Folder />}
                      variant="contained"
                      color="primary"
                      size="small"
                      onClick={handleFolderUploadClick}
                      sx={{ mr: 1 }}
                      disabled={uploadProgress}
                    >
                      上传文件夹
                    </Button>
                    <Button
                      startIcon={<Refresh />}
                      variant="outlined"
                      color="primary"
                      size="small"
                      onClick={rebuildIndex}
                      disabled={loading || files.length === 0}
                    >
                      重建索引
                    </Button>
                    
                    {/* 隐藏的文件输入 */}
                    <input
                      type="file"
                      ref={fileInputRef}
                      style={{ display: 'none' }}
                      onChange={handleFileChange}
                      multiple
                    />
                    
                    {/* 隐藏的文件夹输入 */}
                    <input
                      type="file"
                      ref={folderInputRef}
                      style={{ display: 'none' }}
                      onChange={handleFolderChange}
                      directory=""
                      webkitdirectory=""
                    />
                  </>
                )}
              </Box>
            </Box>
            
            <Divider sx={{ mb: 2 }} />
            
            {!selectedKnowledge ? (
              <Box sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="body1">请选择一个知识库</Typography>
              </Box>
            ) : loading || uploadProgress ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                <CircularProgress />
              </Box>
            ) : (
              <List>
                {files.length === 0 ? (
                  <ListItem>
                    <ListItemText primary="暂无文件" />
                  </ListItem>
                ) : (
                  files.map((file) => (
                    <ListItem key={file.id}>
                      <ListItemText 
                        primary={file.file_name} 
                        secondary={`大小: ${formatFileSize(file.file_size)} | 更新: ${formatDate(file.created_at)}`}
                      />
                      <Chip 
                        size="small" 
                        label={file.status} 
                        color="success" 
                        sx={{ mr: 1 }}
                      />
                      <ListItemSecondaryAction>
                        <IconButton 
                          edge="end"
                          onClick={() => {
                            setItemToDelete(file);
                            setDeleteType('file');
                            setDeleteDialogOpen(true);
                          }}
                        >
                          <Delete />
                        </IconButton>
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))
                )}
              </List>
            )}
          </Paper>
        </Grid>
      </Grid>
      
      {/* 添加查询按钮 */}
      {selectedKnowledge && (
        <Tooltip title={`查询 ${selectedKnowledge.name} 知识库`} placement="left">
          <Fab 
            color="primary" 
            sx={{ position: 'fixed', bottom: 30, right: 30 }}
            onClick={openQueryDialog}
          >
            <Search />
          </Fab>
        </Tooltip>
      )}
      
      {/* 查询知识库对话框 */}
      <Dialog
        open={queryDialogOpen}
        onClose={closeQueryDialog}
        fullWidth
        maxWidth="lg"
        PaperProps={{
          sx: {
            minHeight: '80vh',
            maxHeight: '90vh',
            display: 'flex',
            flexDirection: 'column'
          }
        }}
      >
        <DialogTitle sx={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          borderBottom: '1px solid #e0e0e0',
          pb: 2
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Search sx={{ mr: 1 }} />
            查询知识库: {selectedKnowledge?.name}
          </Box>
          <IconButton onClick={closeQueryDialog} size="small">
            <Close />
          </IconButton>
        </DialogTitle>
        
        <DialogContent sx={{ p: 2, flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ mb: 2, mt: 2 }}>
            <TextField
              fullWidth
              label="输入查询内容"
              variant="outlined"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              disabled={isQuerying}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !isQuerying && queryText.trim()) {
                  queryKnowledge();
                }
              }}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <TextField
                      type="number"
                      label="结果数量"
                      variant="outlined"
                      value={topK}
                      onChange={(e) => setTopK(Math.max(1, parseInt(e.target.value) || 1))}
                      sx={{ width: '100px', mr: 1 }}
                      size="small"
                    />
                    <Button
                      variant="contained"
                      color="primary"
                      startIcon={<Search />}
                      onClick={queryKnowledge}
                      disabled={isQuerying || !queryText.trim()}
                    >
                      查询
                    </Button>
                  </InputAdornment>
                )
              }}
            />
          </Box>
          
          {queryError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setQueryError(null)}>
              {queryError}
            </Alert>
          )}
          
          <Box sx={{ flexGrow: 1, overflow: 'auto', mt: 2 }}>
            {isQuerying ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <CircularProgress />
              </Box>
            ) : (
              queryResults.length > 0 ? (
                <List sx={{ p: 0 }}>
                  {queryResults.map((result, index) => (
                    <Card key={index} variant="outlined" sx={{ mb: 2, backgroundColor: '#f9f9f9' }}>
                      <CardContent>
                        <Box sx={{ 
                          display: 'flex', 
                          justifyContent: 'space-between', 
                          alignItems: 'center',
                          mb: 1.5
                        }}>
                          <Box sx={{ 
                            display: 'flex', 
                            alignItems: 'center',
                            backgroundColor: '#5cb85c', 
                            color: 'white',
                            px: 1.5,
                            py: 0.5,
                            borderRadius: 1,
                            fontSize: '0.75rem',
                            fontWeight: 500
                          }}>
                            Score: {Math.max(1, Math.round((result.score || 0) * 100))}%
                          </Box>
                          <Tooltip title="复制到剪贴板">
                            <IconButton 
                              size="small" 
                              onClick={() => copyToClipboard(result.document)}
                            >
                              <ContentCopy fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                        <Divider sx={{ mb: 1 }} />
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            whiteSpace: 'pre-wrap', 
                            overflowWrap: 'break-word',
                            maxHeight: '300px',
                            overflow: 'auto',
                            p: 1,
                            backgroundColor: '#ffffff',
                            borderRadius: 1,
                            border: '1px solid #eeeeee'
                          }}
                        >
                          {result.document}
                        </Typography>
                        {result.metadata && Object.keys(result.metadata).length > 0 && (
                          <>
                            <Divider sx={{ my: 1 }} />
                            <Typography 
                              variant="caption" 
                              color="text.secondary"
                              sx={{ display: 'flex', alignItems: 'center' }}
                            >
                              <Description fontSize="small" sx={{ mr: 0.5, fontSize: '1rem' }} />
                              来源: {result.metadata.source || '未知'}
                            </Typography>
                          </>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </List>
              ) : (
                queryText.trim() && !queryError && (
                  <Box sx={{ 
                    display: 'flex', 
                    flexDirection: 'column',
                    justifyContent: 'center', 
                    alignItems: 'center', 
                    height: '100%',
                    color: 'text.secondary' 
                  }}>
                    <Search sx={{ fontSize: 60, color: '#e0e0e0', mb: 2 }} />
                    <Typography variant="body1">输入关键词开始查询知识库</Typography>
                  </Box>
                )
              )
            )}
          </Box>
        </DialogContent>
      </Dialog>
      
      {/* 创建知识库对话框 */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)}>
        <DialogTitle>创建新的知识库</DialogTitle>
        <DialogContent>
          <DialogContentText>
            请输入知识库的名称和描述信息
          </DialogContentText>
          <TextField
            autoFocus
            margin="dense"
            label="知识库名称"
            fullWidth
            value={newKnowledgeName}
            onChange={(e) => setNewKnowledgeName(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="描述信息"
            fullWidth
            multiline
            rows={3}
            value={newKnowledgeDesc}
            onChange={(e) => setNewKnowledgeDesc(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>取消</Button>
          <Button 
            onClick={createKnowledge} 
            color="primary"
            disabled={!newKnowledgeName.trim() || loading}
          >
            创建
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* 删除确认对话框 */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>确认删除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {deleteType === 'knowledge' && itemToDelete && (
              `确定要删除知识库 "${itemToDelete.name}" 吗？这将删除所有相关文件和索引，且无法恢复。`
            )}
            {deleteType === 'file' && itemToDelete && (
              `确定要删除文件 "${itemToDelete.file_name}" 吗？`
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>取消</Button>
          <Button onClick={handleDeleteConfirm} color="error">
            删除
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

// 辅助函数：格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// 辅助函数：格式化日期
const formatDate = (dateString) => {
  try {
    const date = new Date(dateString);
    return date.toLocaleString();
  } catch (e) {
    return dateString;
  }
};

export default KnowledgeManager; 