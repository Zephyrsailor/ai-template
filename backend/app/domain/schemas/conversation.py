"""
会话相关的数据模型
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ConversationBase(BaseModel):
    """会话基础模型"""
    title: str = Field(..., description="会话标题")
    description: Optional[str] = Field(default=None, description="会话描述")

class ConversationCreate(ConversationBase):
    """会话创建模型"""
    pass

class ConversationUpdate(BaseModel):
    """会话更新模型"""
    title: Optional[str] = Field(default=None, description="会话标题")
    description: Optional[str] = Field(default=None, description="会话描述")

class MessageBase(BaseModel):
    """消息基础模型"""
    content: str = Field(..., description="消息内容")
    role: str = Field(..., description="角色：user/assistant/system")
    thinking: Optional[str] = Field(default=None, description="思考过程")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="工具调用")

class MessageCreate(MessageBase):
    """消息创建模型"""
    conversation_id: str = Field(..., description="会话ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")

class MessageResponse(MessageBase):
    """消息响应模型"""
    id: str = Field(..., description="消息ID")
    conversation_id: str = Field(..., description="会话ID")
    created_at: str = Field(..., description="创建时间")
    timestamp: str = Field(..., description="时间戳")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    
    class Config:
        """Pydantic配置"""
        from_attributes = True

class ConversationResponse(ConversationBase):
    """会话响应模型"""
    id: str = Field(..., description="会话ID")
    created_at: str = Field(..., description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")
    message_count: int = Field(default=0, description="消息数量")
    is_pinned: bool = Field(default=False, description="是否置顶")
    last_message: Optional[MessageResponse] = Field(default=None, description="最后一条消息")
    model_id: Optional[str] = Field(default=None, description="模型ID")
    
    class Config:
        """Pydantic配置"""
        from_attributes = True

class ConversationDetailResponse(ConversationBase):
    """会话详情响应模型（包含消息）"""
    id: str = Field(..., description="会话ID")
    created_at: str = Field(..., description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")
    message_count: int = Field(default=0, description="消息数量")
    is_pinned: bool = Field(default=False, description="是否置顶")
    model_id: Optional[str] = Field(default=None, description="模型ID")
    system_prompt: Optional[str] = Field(default=None, description="系统提示")
    messages: Optional[List[MessageResponse]] = Field(default_factory=list, description="消息列表")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    
    class Config:
        """Pydantic配置"""
        from_attributes = True

class PaginationInfo(BaseModel):
    """分页信息"""
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    per_page: int = Field(..., description="每页记录数")
    total_pages: int = Field(..., description="总页数")

class ConversationListResponse(BaseModel):
    """会话列表响应 - 简化格式"""
    conversations: List[ConversationResponse] = Field(..., description="会话列表")
    pagination: PaginationInfo = Field(..., description="分页信息")

class MessageListResponse(BaseModel):
    """消息列表响应"""
    messages: List[MessageResponse] = Field(..., description="消息列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="页码")
    page_size: int = Field(..., description="页大小") 