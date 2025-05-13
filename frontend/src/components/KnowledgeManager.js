import React, { useState, useEffect, useRef } from 'react';
import axios from '../api/http';
import styled from 'styled-components';
import { CgSpinner } from 'react-icons/cg';
import { FaTrash, FaSync, FaFile, FaFolder, FaSearch, FaPlus, FaCopy, FaTimes, FaFileAlt, FaFilePdf, FaFileWord, FaFileExcel, FaFileCode, FaFileImage, FaFileArchive, FaFileAudio, FaFileVideo, FaDatabase, FaTools, FaUpload, FaDownload, FaQuestion, FaCog } from 'react-icons/fa';
import { IoChevronDown, IoChevronUp } from 'react-icons/io5';
import { HeaderIcon, TooltipContainer, Tooltip as HeaderTooltip } from './Header';
import { 
  fetchKnowledgeBases, 
  createKnowledgeBase, 
  deleteKnowledgeBase, 
  getKnowledgeBaseFiles, 
  uploadFileToKnowledgeBase, 
  queryKnowledgeBase,
  updateKnowledgeBase
} from '../api/index';

// ===== Core Layout Components =====
const KnowledgeContainer = styled.div`
  display: flex;
  flex-direction: column;
  width: 100%;
  color: #374151;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  max-width: ${props => props.isInSettings ? '100%' : '1400px'};
  margin: 0 auto;
  padding: 0 ${props => props.isInSettings ? '0' : '16px'};
  min-height: ${props => props.isInSettings ? 'auto' : 'calc(100vh - 80px)'};
  height: 100%;
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: ${props => props.isInSettings ? '16px' : '24px'};
  flex: 1;
  min-height: ${props => props.isInSettings ? '550px' : '700px'};
  
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
    gap: 20px;
  }
`;

// ===== Card Design =====
const Card = styled.div`
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  background-color: white;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.2s ease;
  
  &:hover {
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.07);
  }
`;

const CardHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #F3F4F6;
  background-color: #F9FAFB;
`;

const CardTitle = styled.h3`
  font-size: 0.9rem;
  font-weight: 600;
  margin: 0;
  color: #4B5563;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const CardContent = styled.div`
  padding: 0;
  flex: 1;
  overflow-y: auto;
  height: 100%;
  max-height: ${props => props.isInSettings ? 'calc(75vh - 180px)' : 'calc(90vh - 230px)'};
  scrollbar-width: thin;
  
  &::-webkit-scrollbar {
    width: 6px;
  }
  
  &::-webkit-scrollbar-track {
    background: #F9FAFB;
  }
  
  &::-webkit-scrollbar-thumb {
    background-color: #D1D5DB;
    border-radius: 8px;
  }
`;

// ===== Typography =====
const Title = styled.h2`
  font-size: 1.5rem;
  font-weight: 600;
  color: #1F2937;
  margin-bottom: 12px;
`;

const PageDescription = styled.p`
  color: #6B7280;
  font-size: 0.95rem;
  margin-bottom: 24px;
  line-height: 1.5;
`;

// ===== List Items =====
const ListItem = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #F3F4F6;
  cursor: ${props => props.clickable ? 'pointer' : 'default'};
  background-color: ${props => props.selected ? '#EFF6FF' : 'white'};
  border-left: ${props => props.selected ? '3px solid #3B82F6' : '3px solid transparent'};
  transition: all 0.15s ease;
  
  &:hover {
    background-color: ${props => props.clickable ? (props.selected ? '#EFF6FF' : '#F9FAFB') : props.selected ? '#EFF6FF' : '#FFFFFF'};
  }
  
  &:hover .delete-button {
    opacity: 1;
  }
  
  &:last-child {
    border-bottom: none;
  }
`;

const EmptyMessage = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  padding: 60px 20px;
  color: #6B7280;
  font-style: italic;
  font-size: 0.95rem;
  text-align: center;
  gap: 16px;
  
  svg {
    font-size: 32px;
    opacity: 0.6;
    color: #9CA3AF;
  }
`;

// ===== File & KB Entry Styles =====
const FileName = styled.div`
  font-weight: 500;
  font-size: 0.95rem;
  color: #1F2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
  transition: color 0.15s ease;
`;

const FileDetails = styled.div`
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  
  &:hover ${FileName} {
    color: #2563EB;
  }
`;

const FileInfo = styled.div`
  font-size: 0.8rem;
  color: #6B7280;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
  padding-right: 8px;
`;

const FileEntry = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  
  svg {
    font-size: 18px;
    flex-shrink: 0;
    color: #6B7280;
  }
`;

// ===== Status Indicators =====
const FileStatus = styled.span`
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  background-color: #D1FAE5;
  color: #065F46;
  border: 1px solid #A7F3D0;
  margin-right: 4px;
  white-space: nowrap;
  
  ${props => props.status === 'processing' && `
    background-color: #EFF6FF;
    color: #1E40AF;
    border-color: #BFDBFE;
  `}
  
  ${props => props.status === 'error' && `
    background-color: #FEF2F2;
    color: #B91C1C;
    border-color: #FEE2E2;
  `}
`;

// ===== Buttons & Actions =====
const ButtonGroup = styled.div`
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
`;

const ActionButtonsContainer = styled.div`
  display: flex;
  gap: 12px;
  align-items: center;
  
  @media (max-width: 768px) {
    flex-wrap: wrap;
  }
`;

const ActionButton = styled.button`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: ${props => props.iconOnly ? '8px' : '8px 12px'};
  font-size: 14px;
  font-weight: 500;
  border-radius: 6px;
  background-color: ${props => props.primary ? '#3B82F6' : 'white'};
  color: ${props => props.primary ? 'white' : '#6B7280'};
  border: 1px solid ${props => props.primary ? '#2563EB' : '#E5E7EB'};
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  
  &:hover:not(:disabled) {
    background-color: ${props => props.primary ? '#2563EB' : '#F9FAFB'};
    border-color: ${props => props.primary ? '#1D4ED8' : '#D1D5DB'};
  }
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  
  svg {
    ${props => props.iconOnly ? '' : 'margin-right: 6px;'}
  }
`;

const DeleteButton = styled(ActionButton)`
  color: #EF4444;
  min-width: 28px;
  height: 28px;
  padding: 5px;
  border-color: transparent;
  opacity: 0;
  transition: all 0.2s ease-in-out;
  
  &:hover {
    background-color: #FEF2F2;
    border-color: #FEE2E2;
  }
`;

const Button = styled.button`
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: none;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  
  ${props => props.primary ? `
    background-color: #4f46e5;
    color: white;
    border: 1px solid #4338ca;
    
    &:hover:not(:disabled) {
      background-color: #4338ca;
    }
    
    &:active:not(:disabled) {
      background-color: #3730a3;
    }
  ` : `
    background-color: white;
    color: #4B5563;
    border: 1px solid #E5E7EB;
    
    &:hover:not(:disabled) {
      background-color: #F9FAFB;
      border-color: #D1D5DB;
    }
    
    &:active:not(:disabled) {
      background-color: #F3F4F6;
    }
  `}
`;

const CreateButton = styled(ActionButton)`
  background-color: #f8fafc;
  color: #64748b;
  border-color: #e2e8f0;
  font-weight: 500;
  font-size: 0.75rem;
  padding: 6px;
  width: 28px;
  height: 28px;
  min-width: 28px;
  margin-left: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  
  &:hover:not(:disabled) {
    background-color: #f1f5f9;
    border-color: #cbd5e1;
    color: #334155;
  }
  
  &:active:not(:disabled) {
    background-color: #e2e8f0;
  }
  
  svg {
    font-size: 12px;
  }
`;

// ===== Tooltips =====
const ButtonTooltip = styled.div`
  position: absolute;
  top: -32px;
  left: 50%;
  transform: translateX(-50%);
  background-color: #1F2937;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
  visibility: hidden;
  opacity: 0;
  transition: all 0.2s ease;
  pointer-events: none;
  z-index: 50;
  
  &:before {
    content: '';
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    border-width: 4px;
    border-style: solid;
    border-color: #1F2937 transparent transparent transparent;
  }
`;

const ActionButtonWrapper = styled.div`
  position: relative;
  display: inline-flex;
  
  &:hover ${ButtonTooltip} {
    visibility: visible;
    opacity: 1;
  }
`;

// 上传按钮包装器 (特殊处理)
const UploadButtonWrapper = styled(ActionButtonWrapper)`
  margin-right: 4px;
`;

// ===== Dialog & Modal Styles =====
const DialogOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(17, 24, 39, 0.5);
  display: ${props => props.open ? 'flex' : 'none'};
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
  padding: 16px;
`;

const DialogContainer = styled.div`
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  width: ${props => props.fullWidth ? '90%' : '460px'};
  max-width: ${props => props.maxWidth === 'lg' ? '950px' : '460px'};
  min-height: ${props => props.minHeight || 'auto'};
  max-height: ${props => props.maxHeight || '90vh'};
  overflow: hidden;
  
  @media (max-width: 640px) {
    width: 100%;
    max-width: none;
    max-height: 95vh;
  }
`;

const DialogHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #F3F4F6;
  background-color: #F9FAFB;
`;

const DialogTitle = styled.h3`
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #1F2937;
  display: flex;
  align-items: center;

  svg {
    margin-right: 10px;
    color: #4B5563;
  }
`;

const DialogBody = styled.div`
  padding: 20px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
`;

const DialogDescription = styled.p`
  margin-top: 0;
  margin-bottom: 16px;
  color: #4B5563;
  font-size: 14px;
  line-height: 1.5;
`;

const DialogFooter = styled.div`
  display: flex;
  justify-content: flex-end;
  padding: 16px 20px;
  border-top: 1px solid #F3F4F6;
  gap: 12px;
`;

const IconButton = styled.button`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background-color: transparent;
  color: #6B7280;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background-color: #F3F4F6;
    color: #4B5563;
  }
  
  &:active {
    transform: scale(0.95);
  }
  
  svg {
    font-size: 16px;
  }
`;

// ===== Form Components =====
const TextField = styled.div`
  display: flex;
  flex-direction: column;
  margin-bottom: 16px;
  
  label {
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 6px;
    color: #4B5563;
  }
  
  input, textarea {
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 10px 12px;
    font-size: 14px;
    color: #1F2937;
    transition: border-color 0.2s;
    
    &:focus {
      outline: none;
      border-color: #93C5FD;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
    }
    
    &::placeholder {
      color: #9CA3AF;
    }
  }
  
  textarea {
    resize: vertical;
    min-height: 80px;
  }
`;

const InputGroup = styled.div`
  display: flex;
  width: 100%;
  gap: 10px;
  margin-bottom: 20px;
`;

// 表单组件样式
const FormGroup = styled.div`
  margin-bottom: 15px;
  width: 100%;
`;

const Label = styled.label`
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #333;
`;

const Input = styled.input`
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.2s;
  
  &:focus {
    border-color: #5c9efa;
    outline: none;
  }
`;

const TextArea = styled.textarea`
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  resize: vertical;
  min-height: 80px;
  transition: border-color 0.2s;
  
  &:focus {
    border-color: #5c9efa;
    outline: none;
  }
`;

const CheckboxContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
`;

const Checkbox = styled.input`
  cursor: pointer;
  width: 16px;
  height: 16px;
`;

const CheckboxLabel = styled.label`
  cursor: pointer;
  user-select: none;
`;

// ===== Miscellaneous UI Components =====
const Divider = styled.hr`
  border: none;
  border-top: 1px solid #F3F4F6;
  margin: 16px 0;
`;

// ===== Message & Alert Components =====
const AlertMessage = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 14px;
  background-color: ${props => props.type === 'error' ? '#FEF2F2' : '#ECFDF5'};
  color: ${props => props.type === 'error' ? '#B91C1C' : '#065F46'};
  border: 1px solid ${props => props.type === 'error' ? '#FEE2E2' : '#A7F3D0'};
  
  button {
    background: none;
    border: none;
    cursor: pointer;
    color: currentColor;
    padding: 2px;
    display: flex;
    align-items: center;
    opacity: 0.7;
    
    &:hover {
      opacity: 1;
    }
  }
`;

// ===== Loading Indicators =====
const LoadingOverlay = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  width: 100%;
`;

const Spinner = styled(CgSpinner)`
  font-size: 32px;
  color: #6B7280;
  animation: spin 1s linear infinite;
  
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
`;

// ===== Query Result Components =====
const QueryResultList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 20px;
`;

const QueryResultItem = styled.div`
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  overflow: hidden;
  background-color: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.2s;
  
  &:hover {
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }
`;

const QueryResultHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background-color: #F9FAFB;
  border-bottom: 1px solid #F3F4F6;
`;

const ScoreLabel = styled.div`
  display: flex;
  align-items: center;
  font-size: 12px;
  font-weight: 500;
  color: #4B5563;
  gap: 4px;
  
  svg {
    color: #10B981;
  }
`;

const QueryResultContent = styled.div`
  padding: 16px;
  font-size: 14px;
  line-height: 1.5;
  color: #1F2937;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
`;

const QueryResultFooter = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #F9FAFB;
  border-top: 1px solid #F3F4F6;
  font-size: 12px;
  color: #6B7280;
  
  svg {
    font-size: 14px;
  }
`;

const EmptyQueryState = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #9CA3AF;
  gap: 16px;
  text-align: center;
  
  svg {
    font-size: 32px;
    opacity: 0.4;
  }
`;

// 获取文件类型图标
const getFileIcon = (fileName) => {
  if (!fileName) return <FaFileAlt style={{ color: '#9CA3AF' }} />;
  
  const extension = fileName.split('.').pop().toLowerCase();
  
  // Color map for different file types
  const colorMap = {
    pdf: '#EF4444',   // Red for PDFs
    doc: '#3B82F6',   // Blue for Word docs
    docx: '#3B82F6',
    xls: '#10B981',   // Green for Excel
    xlsx: '#10B981',
    ppt: '#F59E0B',   // Amber for PowerPoint
    pptx: '#F59E0B',
    txt: '#6B7280',   // Gray for text files
    csv: '#8B5CF6',   // Purple for data files
    json: '#8B5CF6',
    xml: '#8B5CF6',
    html: '#EC4899',  // Pink for web files
    htm: '#EC4899',
    css: '#EC4899',
    js: '#F59E0B',    // Amber for code files
    py: '#F59E0B',
    java: '#F59E0B',
    cpp: '#F59E0B',
    c: '#F59E0B',
    zip: '#9CA3AF',   // Gray for archives
    rar: '#9CA3AF',
    tar: '#9CA3AF',
    gz: '#9CA3AF',
    jpg: '#EC4899',   // Pink for images
    jpeg: '#EC4899',
    png: '#EC4899',
    gif: '#EC4899',
    svg: '#EC4899',
    mp3: '#8B5CF6',   // Purple for audio
    wav: '#8B5CF6',
    mp4: '#3B82F6',   // Blue for video
    avi: '#3B82F6',
    mov: '#3B82F6'
  };
  
  // Get the color based on extension, default to gray
  const iconColor = colorMap[extension] || '#9CA3AF';
  
  switch (extension) {
    case 'pdf':
      return <FaFilePdf style={{ color: iconColor }} />;
    case 'doc':
    case 'docx':
      return <FaFileWord style={{ color: iconColor }} />;
    case 'xls':
    case 'xlsx':
    case 'csv':
      return <FaFileExcel style={{ color: iconColor }} />;
    case 'js':
    case 'py':
    case 'java':
    case 'cpp':
    case 'c':
    case 'html':
    case 'css':
    case 'json':
    case 'xml':
      return <FaFileCode style={{ color: iconColor }} />;
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'gif':
    case 'svg':
      return <FaFileImage style={{ color: iconColor }} />;
    case 'zip':
    case 'rar':
    case 'tar':
    case 'gz':
      return <FaFileArchive style={{ color: iconColor }} />;
    case 'mp3':
    case 'wav':
      return <FaFileAudio style={{ color: iconColor }} />;
    case 'mp4':
    case 'avi':
    case 'mov':
      return <FaFileVideo style={{ color: iconColor }} />;
    default:
      return <FaFileAlt style={{ color: iconColor }} />;
  }
};

// 添加对话框按钮包装器
const DialogActionButtonWrapper = styled(ActionButtonWrapper)`
  ${ButtonTooltip} {
    top: auto;
    bottom: 38px;
    &:before {
      top: 100%;
      bottom: auto;
      border-color: #1F2937 transparent transparent transparent;
    }
  }
`;

// 知识库管理组件
const KnowledgeManager = ({ isInSettings = false }) => {
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
  
  // 知识库设置相关状态
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  const [knowledgeToEdit, setKnowledgeToEdit] = useState(null);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  
  // 初始加载知识库列表
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

  // 加载知识库列表
  const loadKnowledgeBases = async () => {
    setLoading(true);
    setError(null);
    try {
      const { success, data, message } = await fetchKnowledgeBases();
      if (success) {
        setKnowledgeBases(data || []);
      } else {
        setKnowledgeBases([]);
        setError(message || '加载知识库失败');
      }
      if (selectedKnowledge) {
        const updated = (data || []).find(kb => kb.id === selectedKnowledge.id);
        if (updated) {
          setSelectedKnowledge(updated);
          loadFiles(updated.id);
        }
      }
    } catch (err) {
      setError('加载知识库列表失败：' + (err.message));
    } finally {
      setLoading(false);
    }
  };

  // 加载文件列表
  const loadFiles = async (knowledgeId) => {
    if (!knowledgeId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await getKnowledgeBaseFiles(knowledgeId);
      if (response.success) {
        // 处理响应数据
        let fileArray = response.data;
        
        // 如果不是数组，尝试找到数组数据
        if (!Array.isArray(fileArray)) {
          console.warn('文件列表不是数组:', fileArray);
          if (fileArray && Array.isArray(fileArray.data)) {
            fileArray = fileArray.data;
          } else {
            console.error('无法找到文件列表数组');
            fileArray = [];
          }
        }
        
        console.log('文件列表数据类型:', Object.prototype.toString.call(fileArray), '长度:', fileArray.length);
        
        // 映射字段名，确保与前端组件兼容
        const mappedFiles = fileArray.map(file => ({
          file_name: file.file_name || file.filename || '',
          file_size: file.file_size || file.size || 0,
          created_at: file.created_at || file.last_modified || new Date().toISOString(),
          status: file.status || 'unknown',
          // 保留原始属性以防需要
          ...file
        }));
        setFiles(mappedFiles);
      } else {
        setError(response.message || '加载文件列表失败');
        setFiles([]);
      }
    } catch (err) {
      console.error('加载文件列表失败:', err);
      setError('加载文件列表失败：' + (err.message || err));
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  // 选择知识库
  const selectKnowledge = (knowledge) => {
    setSelectedKnowledge(knowledge);
    loadFiles(knowledge.id);
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
      const { success, data, message } = await createKnowledgeBase({
        name: newKnowledgeName.trim(),
        description: newKnowledgeDesc.trim()
      });
      if (success) {
        setSuccess('知识库创建成功');
        setNewKnowledgeName('');
        setNewKnowledgeDesc('');
        setCreateDialogOpen(false);
        loadKnowledgeBases();
      } else {
        setError('创建知识库失败：' + message);
      }
    } catch (err) {
      setError('创建知识库失败：' + (err.message));
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
      // 只支持单文件上传
      const { success, data, message } = await uploadFileToKnowledgeBase(selectedKnowledge.id, files[0]);
      if (success) {
        setSuccess('文件上传成功');
        loadKnowledgeBases();
      } else {
        setError('上传文件失败：' + message);
      }
    } catch (err) {
      setError('上传文件失败：' + (err.message));
    } finally {
      setUploadProgress(false);
    }
  };

  // 文件上传点击事件
  const handleFileUploadClick = () => {
    fileInputRef.current?.click();
  };

  // 文件上传变更事件
  const handleFileChange = (e) => {
    uploadFiles(e.target.files);
    e.target.value = null; // 清空input，允许上传相同文件
  };

  // 文件夹上传点击事件
  const handleFolderUploadClick = () => {
    folderInputRef.current?.click();
  };

  // 文件夹上传变更事件
  const handleFolderChange = (e) => {
    uploadFiles(e.target.files);
    e.target.value = null; // 清空input，允许上传相同文件夹
  };

  // 删除知识库
  const deleteKnowledge = async () => {
    if (!itemToDelete) return;
    setLoading(true);
    setError(null);
    try {
      const { success, message } = await deleteKnowledgeBase(itemToDelete.id);
      if (success) {
        setSuccess(`知识库 ${itemToDelete.name} 删除成功`);
        if (selectedKnowledge && selectedKnowledge.name === itemToDelete.name) {
          setSelectedKnowledge(null);
          setFiles([]);
        }
        loadKnowledgeBases();
      } else {
        setError('删除知识库失败：' + message);
      }
    } catch (err) {
      setError('删除知识库失败：' + (err.message));
    } finally {
      setLoading(false);
    }
  };

  // 删除文件
  const deleteFile = async () => {
    if (!selectedKnowledge || !itemToDelete) return;
    
    const fileName = itemToDelete.file_name;
    if (!fileName) {
      setError('无效的文件名');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // 使用导入的axios实例，确保带有认证信息
      const response = await axios.delete(`/api/knowledge/${selectedKnowledge.id}/files/${encodeURIComponent(fileName)}/`);
      
      if (response.data.code === 200) {
        setSuccess(`文件 ${fileName} 删除成功`);
        // 移除本地列表中的文件
        setFiles(files.filter(f => f.file_name !== fileName));
        
        // 更新知识库信息
        loadKnowledgeBases();
      } else {
        setError('删除文件失败：' + response.data.message);
      }
    } catch (err) {
      setError('删除文件失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
      setItemToDelete(null);
    }
  };

  // 处理删除确认
  const handleDeleteConfirm = async () => {
    try {
      if (deleteType === 'knowledge') {
        await deleteKnowledge();
      } else if (deleteType === 'file') {
        await deleteFile();
      }
    } finally {
      setDeleteDialogOpen(false);
    }
  };
  
  // 打开设置对话框
  const openSettingsDialog = (knowledge) => {
    setKnowledgeToEdit(knowledge);
    setEditName(knowledge.name);
    setEditDescription(knowledge.description || '');
    setSettingsDialogOpen(true);
  };
  
  // 关闭设置对话框
  const closeSettingsDialog = () => {
    setSettingsDialogOpen(false);
    setKnowledgeToEdit(null);
    setEditName('');
    setEditDescription('');
  };
  
  // 更新知识库
  const updateKnowledgeSettings = async () => {
    if (!knowledgeToEdit) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const updateData = {
        name: editName.trim(),
        description: editDescription.trim()
      };
      
      const { success, data, message } = await updateKnowledgeBase(knowledgeToEdit.id, updateData);
      
      if (success) {
        setSuccess(`知识库 ${knowledgeToEdit.name} 更新成功`);
        closeSettingsDialog();
        
        // 更新知识库列表和选中的知识库
        loadKnowledgeBases();
        
        // 如果当前选中的是被更新的知识库，更新显示信息
        if (selectedKnowledge && selectedKnowledge.id === knowledgeToEdit.id) {
          setSelectedKnowledge({
            ...selectedKnowledge,
            name: editName.trim(),
            description: editDescription.trim()
          });
        }
      } else {
        setError('更新知识库失败：' + message);
      }
    } catch (err) {
      setError('更新知识库失败：' + (err.message));
    } finally {
      setLoading(false);
    }
  };

  // 重建索引
  const rebuildIndex = async () => {
    if (!selectedKnowledge) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // 使用导入的axios实例，确保带有认证信息
      const response = await axios.post(`/api/knowledge/${selectedKnowledge.id}/rebuild/`);
      
      if (response.data.code === 200) {
        setSuccess(`知识库 ${selectedKnowledge.name} 索引重建成功`);
        // 更新知识库信息
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
    if (!selectedKnowledge) {
      setQueryError('请先选择一个知识库');
      return;
    }
    if (!queryText.trim()) {
      setQueryError('请输入查询内容');
      return;
    }
    setIsQuerying(true);
    setQueryError(null);
    setQueryResults([]);
    try {
      const { success, data, message } = await queryKnowledgeBase({
        knowledge_base_id: selectedKnowledge.id,
        query: queryText.trim(),
        top_k: topK
      });
      if (success) {
        const results = data || [];
        if (results.length === 0) {
          setQueryError('没有找到匹配的结果，请尝试其他关键词');
        } else {
          setQueryResults(results);
        }
      } else {
        setQueryError('查询失败：' + message);
      }
    } catch (err) {
      setQueryError('查询失败：' + (err.message));
    } finally {
      setIsQuerying(false);
    }
  };

  // 打开查询对话框
  const openQueryDialog = () => {
    if (!selectedKnowledge) {
      setError('请先选择一个知识库');
      return;
    }
    
    setQueryDialogOpen(true);
    setQueryResults([]);
    setQueryError(null);
  };

  // 关闭查询对话框
  const closeQueryDialog = () => {
    setQueryDialogOpen(false);
  };

  // 复制到剪贴板
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
      .then(() => {
        setSuccess('已复制到剪贴板');
      })
      .catch((err) => {
        setError('复制失败：' + err.message);
      });
  };

  // 格式化文件大小
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    
    return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + sizes[i];
  };

  // 格式化日期
  const formatDate = (dateString) => {
    if (!dateString) return '未知';
    
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Rendering functions
  const renderEmptyMessage = (message, icon) => (
    <EmptyMessage>
      {icon}
      <div>{message}</div>
    </EmptyMessage>
  );

  return (
    <KnowledgeContainer isInSettings={isInSettings}>
      {!isInSettings && (
        <>
          <Title>知识库管理</Title>
          <PageDescription>
            管理您的知识库和文档。上传文件后系统会自动处理并建立索引，以便您可以通过搜索快速检索信息。
          </PageDescription>
        </>
      )}
      
      {/* 错误和成功提示 */}
      {error && (
        <AlertMessage type="error">
          {error}
          <button onClick={() => setError(null)}><FaTimes /></button>
        </AlertMessage>
      )}
      
      {success && (
        <AlertMessage type="success">
          {success}
          <button onClick={() => setSuccess(null)}><FaTimes /></button>
        </AlertMessage>
      )}
      
      <Grid isInSettings={isInSettings}>
        {/* 知识库列表 */}
        <Card>
          <CardHeader>
            <CardTitle>知识库列表</CardTitle>
            <CreateButton 
              onClick={() => setCreateDialogOpen(true)}
              aria-label="创建知识库"
              title="创建知识库"
            >
              <FaPlus />
            </CreateButton>
          </CardHeader>
          
          <CardContent isInSettings={isInSettings}>
            {loading && knowledgeBases.length === 0 ? (
              <LoadingOverlay>
                <Spinner />
              </LoadingOverlay>
            ) : knowledgeBases.length === 0 ? (
              renderEmptyMessage('暂无知识库，点击"创建"按钮开始添加', <FaDatabase />)
            ) : (
              knowledgeBases.map((kb) => (
                <ListItem 
                  key={kb.id || kb.name}
                  clickable
                  selected={selectedKnowledge && selectedKnowledge.name === kb.name}
                  onClick={() => selectKnowledge(kb)}
                >
                  <FileDetails>
                    <FileName>{kb.name}</FileName>
                    <FileInfo>
                      {kb.file_count || 0}个文件 / {kb.document_count || 0}个文档块
                      {kb.description && ` • ${kb.description}`}
                    </FileInfo>
                  </FileDetails>
                  
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <ActionButtonWrapper>
                      <DeleteButton
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeleteType('knowledge');
                          setItemToDelete(kb);
                          setDeleteDialogOpen(true);
                        }}
                        className="delete-button"
                      >
                        <FaTrash />
                      </DeleteButton>
                      <ButtonTooltip>删除知识库</ButtonTooltip>
                    </ActionButtonWrapper>
                    
                    <ActionButtonWrapper>
                      <ActionButton
                        onClick={(e) => {
                          e.stopPropagation();
                          openSettingsDialog(kb);
                        }}
                      >
                        <FaCog />
                      </ActionButton>
                      <ButtonTooltip>知识库设置</ButtonTooltip>
                    </ActionButtonWrapper>
                  </div>
                </ListItem>
              ))
            )}
          </CardContent>
        </Card>
        
        {/* 文件列表与操作 */}
        <Card>
          <CardHeader>
            <CardTitle>
              {selectedKnowledge ? `${selectedKnowledge.name}的文件` : '文件列表'}
            </CardTitle>
            
            {selectedKnowledge && (
              <ActionButtonsContainer>
                <ActionButtonWrapper>
                  <ActionButton 
                    iconOnly
                    onClick={openQueryDialog}
                    aria-label="查询知识库"
                  >
                    <FaSearch />
                  </ActionButton>
                  <ButtonTooltip>查询知识库</ButtonTooltip>
                </ActionButtonWrapper>
                
                <UploadButtonWrapper>
                  <ActionButton 
                    iconOnly
                    onClick={handleFileUploadClick} 
                    disabled={uploadProgress}
                    aria-label="上传文件"
                  >
                    <FaUpload />
                  </ActionButton>
                  <ButtonTooltip>上传文件</ButtonTooltip>
                </UploadButtonWrapper>
                
                <UploadButtonWrapper>
                  <ActionButton 
                    iconOnly
                    onClick={handleFolderUploadClick} 
                    disabled={uploadProgress}
                    aria-label="上传文件夹"
                  >
                    <FaFolder />
                  </ActionButton>
                  <ButtonTooltip>上传文件夹</ButtonTooltip>
                </UploadButtonWrapper>
                
                <UploadButtonWrapper>
                  <ActionButton 
                    iconOnly
                    onClick={rebuildIndex} 
                    disabled={loading || files.length === 0}
                    aria-label="重建索引"
                  >
                    <FaDatabase />
                  </ActionButton>
                  <ButtonTooltip>重建向量索引</ButtonTooltip>
                </UploadButtonWrapper>
                
                {/* 隐藏的文件输入 */}
                <input
                  type="file"
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                  multiple
                  aria-hidden="true"
                />
                
                {/* 隐藏的文件夹输入 */}
                <input
                  type="file"
                  ref={folderInputRef}
                  style={{ display: 'none' }}
                  onChange={handleFolderChange}
                  directory=""
                  webkitdirectory=""
                  aria-hidden="true"
                />
              </ActionButtonsContainer>
            )}
          </CardHeader>
          
          <CardContent isInSettings={isInSettings}>
            {!selectedKnowledge ? (
              renderEmptyMessage('请从左侧选择一个知识库', <FaQuestion />)
            ) : loading || uploadProgress ? (
              <LoadingOverlay>
                <Spinner />
              </LoadingOverlay>
            ) : !Array.isArray(files) ? (
              renderEmptyMessage('文件列表格式错误', <FaQuestion />)
            ) : files.length === 0 ? (
              renderEmptyMessage('该知识库暂无文件，请点击上传按钮添加文件', <FaUpload />)
            ) : (
              files.map((file) => (
                <ListItem key={file.id || file.file_name}>
                  <FileEntry>
                    {getFileIcon(file.file_name)}
                    <FileDetails>
                      <FileName>{file.file_name}</FileName>
                      <FileInfo>
                        {formatFileSize(file.file_size)} • 更新于 {formatDate(file.created_at || file.updated_at)}
                      </FileInfo>
                    </FileDetails>
                  </FileEntry>
                  
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <FileStatus status={file.status && file.status.toLowerCase()}>
                      {file.status || '已量化'}
                    </FileStatus>
                    <ActionButtonWrapper>
                      <DeleteButton 
                        iconOnly
                        danger
                        className="delete-button"
                        onClick={() => {
                          setItemToDelete(file);
                          setDeleteType('file');
                          setDeleteDialogOpen(true);
                        }}
                        aria-label="删除文件"
                      >
                        <FaTrash />
                      </DeleteButton>
                      <ButtonTooltip>删除文件</ButtonTooltip>
                    </ActionButtonWrapper>
                  </div>
                </ListItem>
              ))
            )}
          </CardContent>
        </Card>
      </Grid>
      
      {/* 查询知识库对话框 */}
      <DialogOverlay open={queryDialogOpen} onClick={(e) => {
        if (e.target === e.currentTarget) closeQueryDialog();
      }}>
        <DialogContainer fullWidth maxWidth="lg">
          <DialogHeader>
            <DialogTitle>
              <FaSearch /> 查询知识库: {selectedKnowledge?.name}
            </DialogTitle>
            <IconButton onClick={closeQueryDialog}>
              <FaTimes />
            </IconButton>
          </DialogHeader>
          
          <DialogBody>
            <InputGroup>
              <input
                type="text"
                placeholder="输入查询内容..."
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
                disabled={isQuerying}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && !isQuerying && queryText.trim()) {
                    queryKnowledge();
                  }
                }}
              />
              <input
                type="number"
                placeholder="结果数量"
                value={topK}
                onChange={(e) => setTopK(Math.max(1, parseInt(e.target.value) || 1))}
                style={{ width: '80px' }}
                min="1"
                max="20"
              />
              <Button
                primary
                onClick={queryKnowledge}
                disabled={isQuerying || !queryText.trim()}
              >
                <FaSearch /> 查询
              </Button>
            </InputGroup>
            
            {queryError && (
              <AlertMessage type="error">
                {queryError}
                <button onClick={() => setQueryError(null)}><FaTimes /></button>
              </AlertMessage>
            )}
            
            {isQuerying ? (
              <LoadingOverlay>
                <Spinner />
              </LoadingOverlay>
            ) : queryResults.length > 0 ? (
              <QueryResultList>
                {queryResults.map((result, index) => (
                  <QueryResultItem key={index}>
                    <QueryResultHeader>
                      <ScoreLabel>
                        <IoChevronUp /> 相关度: {Math.round((result.score || 0) * 100)}%
                      </ScoreLabel>
                      <DialogActionButtonWrapper>
                        <IconButton 
                          onClick={() => copyToClipboard(result.document)}
                          aria-label="复制到剪贴板"
                        >
                          <FaCopy />
                        </IconButton>
                        <ButtonTooltip>复制到剪贴板</ButtonTooltip>
                      </DialogActionButtonWrapper>
                    </QueryResultHeader>
                    
                    <QueryResultContent>
                      {result.document}
                    </QueryResultContent>
                    
                    {result.metadata && Object.keys(result.metadata).length > 0 && (
                      <QueryResultFooter>
                        {getFileIcon(result.metadata.source)}
                        来源: {result.metadata.source || '未知'}
                      </QueryResultFooter>
                    )}
                  </QueryResultItem>
                ))}
              </QueryResultList>
            ) : queryText.trim() && !queryError ? (
              renderEmptyMessage('没有找到匹配的结果，请尝试其他关键词', <FaSearch />)
            ) : (
              renderEmptyMessage('输入关键词开始查询知识库', <FaSearch />)
            )}
          </DialogBody>
        </DialogContainer>
      </DialogOverlay>
      
      {/* 创建知识库对话框 */}
      <DialogOverlay open={createDialogOpen} onClick={(e) => {
        if (e.target === e.currentTarget) setCreateDialogOpen(false);
      }}>
        <DialogContainer>
          <DialogHeader>
            <DialogTitle>
              <FaPlus /> 创建新的知识库
            </DialogTitle>
            <IconButton onClick={() => setCreateDialogOpen(false)}>
              <FaTimes />
            </IconButton>
          </DialogHeader>
          
          <DialogBody>
            <DialogDescription>
              请输入知识库的名称和描述信息
            </DialogDescription>
            
            <TextField>
              <label htmlFor="knowledge-name">知识库名称</label>
              <input
                id="knowledge-name"
                type="text"
                value={newKnowledgeName}
                onChange={(e) => setNewKnowledgeName(e.target.value)}
                placeholder="输入知识库名称（必填）"
                autoFocus
              />
            </TextField>
            
            <TextField>
              <label htmlFor="knowledge-desc">描述信息</label>
              <textarea
                id="knowledge-desc"
                value={newKnowledgeDesc}
                onChange={(e) => setNewKnowledgeDesc(e.target.value)}
                placeholder="输入知识库描述（选填）"
                rows={3}
              />
            </TextField>
          </DialogBody>
          
          <DialogFooter>
            <Button onClick={() => setCreateDialogOpen(false)}>
              取消
            </Button>
            <Button 
              primary
              onClick={createKnowledge}
              disabled={!newKnowledgeName.trim() || loading}
            >
              创建
            </Button>
          </DialogFooter>
        </DialogContainer>
      </DialogOverlay>
      
      {/* 删除确认对话框 */}
      <DialogOverlay open={deleteDialogOpen} onClick={(e) => {
        if (e.target === e.currentTarget) setDeleteDialogOpen(false);
      }}>
        <DialogContainer>
          <DialogHeader>
            <DialogTitle>
              <FaTrash /> 确认删除
            </DialogTitle>
            <IconButton onClick={() => setDeleteDialogOpen(false)}>
              <FaTimes />
            </IconButton>
          </DialogHeader>
          
          <DialogBody>
            <DialogDescription>
              {deleteType === 'knowledge' && itemToDelete && (
                `确定要删除知识库 "${itemToDelete.name}" 吗？这将删除所有相关文件和索引，且无法恢复。`
              )}
              {deleteType === 'file' && itemToDelete && (
                `确定要删除文件 "${itemToDelete.file_name}" 吗？`
              )}
            </DialogDescription>
          </DialogBody>
          
          <DialogFooter>
            <Button onClick={() => setDeleteDialogOpen(false)}>
              取消
            </Button>
            <Button 
              danger
              onClick={handleDeleteConfirm}
              disabled={loading}
            >
              删除
            </Button>
          </DialogFooter>
        </DialogContainer>
      </DialogOverlay>
      
      {/* 知识库设置对话框 */}
      <DialogOverlay open={settingsDialogOpen} onClick={(e) => {
        if (e.target === e.currentTarget) closeSettingsDialog();
      }}>
        <DialogContainer>
          <DialogHeader>
            <DialogTitle>
              知识库设置
            </DialogTitle>
            <IconButton onClick={closeSettingsDialog}>
              <FaTimes />
            </IconButton>
          </DialogHeader>
          
          <DialogBody>
            <DialogDescription>
              编辑知识库信息，您可以修改知识库名称和描述。
            </DialogDescription>
            
            <FormGroup>
              <Label htmlFor="editKnowledgeName">知识库名称</Label>
              <Input
                id="editKnowledgeName"
                type="text"
                placeholder="请输入知识库名称"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
              />
            </FormGroup>
            
            <FormGroup>
              <Label htmlFor="editKnowledgeDesc">知识库描述</Label>
              <TextArea
                id="editKnowledgeDesc"
                placeholder="请输入知识库描述（可选）"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                rows={3}
              />
            </FormGroup>
          </DialogBody>
          
          <DialogFooter>
            <Button onClick={closeSettingsDialog}>
              取消
            </Button>
            <Button
              style={{ backgroundColor: !editName.trim() || loading ? '#ccc' : '#4385f5', color: 'white' }}
              onClick={updateKnowledgeSettings}
              disabled={!editName.trim() || loading}
            >
              {loading ? <CgSpinner className="spin" /> : '保存更改'}
            </Button>
          </DialogFooter>
        </DialogContainer>
      </DialogOverlay>
    </KnowledgeContainer>
  );
};

export default KnowledgeManager; 