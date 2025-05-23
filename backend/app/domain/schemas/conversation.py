"""
会话相关的数据验证模型
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class MessageCreate(BaseModel):
    """创建消息请求"""
    role: str = Field(..., description="消息角色，如user、assistant、system")
    content: str = Field(..., description="消息内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="消息元数据")
    thinking: Optional[str] = Field(None, description="思考过程")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="工具调用列表")

class MessageResponse(BaseModel):
    """消息响应"""
    id: str = Field(..., description="消息ID")
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(..., description="消息时间戳")
    metadata: Dict[str, Any] = Field({}, description="消息元数据")
    thinking: Optional[str] = Field(None, description="思考过程")
    tool_calls: List[Dict[str, Any]] = Field([], description="工具调用列表")

class ConversationCreate(BaseModel):
    """创建会话请求"""
    title: Optional[str] = Field(None, description="会话标题")
    system_prompt: Optional[str] = Field(None, description="系统提示")
    model_id: Optional[str] = Field(None, description="模型ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="会话元数据")

class ConversationUpdate(BaseModel):
    """更新会话请求"""
    title: Optional[str] = Field(None, description="会话标题")
    system_prompt: Optional[str] = Field(None, description="系统提示")
    model_id: Optional[str] = Field(None, description="模型ID")
    is_pinned: Optional[bool] = Field(None, description="是否置顶")
    metadata: Optional[Dict[str, Any]] = Field(None, description="会话元数据")

class ConversationResponse(BaseModel):
    """会话响应"""
    id: str = Field(..., description="会话ID")
    title: str = Field(..., description="会话标题")
    messages: List[MessageResponse] = Field([], description="消息列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    model_id: Optional[str] = Field(None, description="模型ID")
    system_prompt: Optional[str] = Field(None, description="系统提示")
    is_pinned: bool = Field(False, description="是否置顶")
    metadata: Dict[str, Any] = Field({}, description="会话元数据")

class ConversationListResponse(BaseModel):
    """会话列表响应"""
    id: str = Field(..., description="会话ID")
    title: str = Field(..., description="会话标题")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    message_count: int = Field(0, description="消息数量")
    is_pinned: bool = Field(False, description="是否置顶")
    last_message: Optional[MessageResponse] = Field(None, description="最后一条消息")
    model_id: Optional[str] = Field(None, description="模型ID") 