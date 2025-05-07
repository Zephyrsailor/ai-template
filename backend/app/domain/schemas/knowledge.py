"""
知识库相关的数据验证模型
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union, Any
from datetime import datetime

class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    embedding_model: Optional[str] = Field(None, description="嵌入模型，如果为空则使用默认模型")

class KnowledgeBaseResponse(BaseModel):
    """知识库信息响应"""
    id: str = Field(..., description="知识库ID")
    name: str = Field(..., description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    document_count: int = Field(0, description="文档数量")
    file_count: int = Field(0, description="文件数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    embedding_model: str = Field(..., description="使用的嵌入模型")

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
    # id: str = Field(..., description="文档ID")
    file_name: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小(字节)")
    status: str = Field(..., description="文件状态")
    # metadata: DocumentMetadata = Field(..., description="文档元数据")
    # chunk_count: int = Field(0, description="分块数量")
    created_at: datetime = Field(..., description="创建时间")
    # knowledge_base_id: str = Field(..., description="所属知识库ID")

class QueryRequest(BaseModel):
    """知识库查询请求"""
    query: str = Field(..., description="查询文本")
    # knowledge_base_ids: List[str] = Field(..., description="要查询的知识库ID列表")
    top_k: int = Field(5, description="返回的最相似结果数量")
    # threshold: Optional[float] = Field(None, description="相似度阈值，低于此值的结果将被过滤")

class QueryResult(BaseModel):
    """查询结果"""
    content: str = Field(..., description="内容片段")
    score: float = Field(..., description="相似度得分")
    metadata: Dict[str, Any] = Field(..., description="元数据")
    source_knowledge_base: Dict[str, str] = Field(..., description="来源知识库信息")

class QueryResponse(BaseModel):
    """知识库查询响应"""
    results: List[QueryResult] = Field(..., description="查询结果列表")
    query: str = Field(..., description="原始查询") 