"""
知识库相关的数据验证模型
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union, Any
from datetime import datetime

class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., title="知识库名称")
    description: Optional[str] = Field(None, title="知识库描述")
    embedding_model: Optional[str] = Field(None, title="嵌入模型")
    is_public: Optional[bool] = Field(False, title="是否公开")

class KnowledgeBaseResponse(BaseModel):
    """知识库信息响应"""
    id: str = Field(..., title="知识库ID")
    name: str = Field(..., title="知识库名称")
    description: Optional[str] = Field(None, title="知识库描述")
    document_count: int = Field(0, title="文档数量")
    file_count: int = Field(0, title="文件数量")
    created_at: str = Field(..., title="创建时间")
    updated_at: Optional[str] = Field(None, title="更新时间")
    embedding_model: str = Field(..., title="使用的嵌入模型")
    is_public: bool = Field(False, title="是否公开")
    owner_id: Optional[str] = Field(None, title="所有者ID")
    status: str = Field(..., title="状态")
    kb_type: str = Field(..., title="知识库类型")

class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求"""
    name: Optional[str] = Field(None, title="知识库名称")
    description: Optional[str] = Field(None, title="知识库描述")
    is_public: Optional[bool] = Field(None, title="是否公开")

class DocumentMetadata(BaseModel):
    """文档元数据"""
    source: str = Field(..., description="文档来源")
    author: Optional[str] = Field(None, description="作者")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    file_type: Optional[str] = Field(None, description="文件类型")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")
    page_count: Optional[int] = Field(None, description="页数")
    custom_metadata: Optional[Dict[str, Any]] = Field(None, description="自定义元数据")

class DocumentResponse(BaseModel):
    """文档信息响应"""
    id: str = Field(..., title="文件ID")
    file_name: str = Field(..., title="文件名")
    file_type: Optional[str] = Field(None, title="文件类型")
    file_size: int = Field(..., title="文件大小")
    status: str = Field(..., title="状态")
    created_at: str = Field(..., title="创建时间")
    updated_at: Optional[str] = Field(None, title="更新时间")
    metadata: Optional[Dict[str, Any]] = Field({}, title="元数据")
    chunk_count: int = Field(0, title="文档块数量")

class QueryRequest(BaseModel):
    """知识库查询请求"""
    query: str = Field(..., title="查询内容")
    top_k: Optional[int] = Field(5, title="返回结果数量")

class QueryResult(BaseModel):
    """查询结果"""
    document: str = Field(..., title="文档内容")
    metadata: Dict[str, Any] = Field({}, title="元数据")
    score: float = Field(..., title="相关性分数")
    source_knowledge_base: Optional[Dict[str, Any]] = Field(None, title="源知识库信息")

class QueryResponse(BaseModel):
    """知识库查询响应"""
    query: str = Field(..., title="查询内容")
    results: List[QueryResult] = Field(..., title="查询结果")

class KnowledgeShareRequest(BaseModel):
    """共享知识库请求"""
    user_id: str = Field(..., title="用户ID") 