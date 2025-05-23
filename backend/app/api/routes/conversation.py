"""
会话API路由
"""
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...domain.schemas.conversation import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    ConversationListResponse, MessageCreate, MessageResponse
)
from ...domain.schemas.base import ApiResponse
from ...services.conversation import ConversationService
from ...domain.models.user import User
from ..deps import get_current_user, api_response

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

# 具体响应模型
class ConversationListResponseWrapper(ApiResponse[List[ConversationListResponse]]):
    """会话列表响应"""
    pass

class ConversationResponseWrapper(ApiResponse[ConversationResponse]):
    """会话详情响应"""
    pass

class MessageResponseWrapper(ApiResponse[MessageResponse]):
    """消息响应"""
    pass

def get_conversation_service() -> ConversationService:
    """获取会话服务"""
    return ConversationService()

@router.post("/", response_model=ConversationResponseWrapper)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    创建新会话
    """
    conversation = conversation_service.create_conversation(
        user_id=current_user.id,
        title=data.title
    )
    
    if data.system_prompt:
        conversation.system_prompt = data.system_prompt
        
    if data.model_id:
        conversation.model_id = data.model_id
        
    if data.metadata:
        conversation.metadata = data.metadata
    
    conversation_service.update_conversation(conversation)
    
    # 转换为响应格式
    response = _conversation_to_response(conversation)
    
    return api_response(data=response)

@router.get("/", response_model=ConversationListResponseWrapper)
async def list_conversations(
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    获取用户所有会话列表
    """
    conversations = conversation_service.list_conversations(current_user.id)
    
    # 转换为响应格式
    response = []
    for conv in conversations:
        last_message = None
        if conv.messages:
            msg = conv.messages[-1]
            last_message = MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                metadata=msg.metadata,
                thinking=msg.thinking,
                tool_calls=msg.tool_calls or []
            )
            
        response.append(ConversationListResponse(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=len(conv.messages),
            is_pinned=conv.is_pinned,
            last_message=last_message,
            model_id=conv.model_id
        ))
    
    return api_response(data=response)

@router.get("/{conversation_id}", response_model=ConversationResponseWrapper)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    获取会话详情
    """
    conversation = conversation_service.get_conversation(current_user.id, conversation_id)
    if not conversation:
        return api_response(code=404, message=f"会话 {conversation_id} 不存在")
    
    # 转换为响应格式
    response = _conversation_to_response(conversation)
    
    return api_response(data=response)

@router.put("/{conversation_id}", response_model=ConversationResponseWrapper)
async def update_conversation(
    conversation_id: str,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    更新会话信息
    """
    conversation = conversation_service.get_conversation(current_user.id, conversation_id)
    if not conversation:
        return api_response(code=404, message=f"会话 {conversation_id} 不存在")
    
    # 更新字段
    if data.title is not None:
        conversation.title = data.title
        
    if data.system_prompt is not None:
        conversation.system_prompt = data.system_prompt
        
    if data.model_id is not None:
        conversation.model_id = data.model_id
        
    if data.is_pinned is not None:
        conversation.is_pinned = data.is_pinned
        
    if data.metadata is not None:
        conversation.metadata = data.metadata or {}
    
    # 保存更新
    conversation_service.update_conversation(conversation)
    
    # 转换为响应格式
    response = _conversation_to_response(conversation)
    
    return api_response(data=response)

@router.delete("/{conversation_id}", response_model=ApiResponse)
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    删除会话
    """
    success = conversation_service.delete_conversation(current_user.id, conversation_id)
    if not success:
        return api_response(code=404, message=f"会话 {conversation_id} 不存在")
    
    return api_response(message=f"会话 {conversation_id} 已删除")

@router.post("/{conversation_id}/messages", response_model=MessageResponseWrapper)
async def add_message(
    conversation_id: str,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    向会话添加消息
    """
    message = conversation_service.add_message(
        user_id=current_user.id,
        conversation_id=conversation_id,
        role=data.role,
        content=data.content,
        metadata=data.metadata,
        thinking=data.thinking,
        tool_calls=data.tool_calls
    )
    
    if not message:
        return api_response(code=404, message=f"会话 {conversation_id} 不存在")
    
    # 转换为响应格式
    response = MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        timestamp=message.timestamp,
        metadata=message.metadata,
        thinking=message.thinking,
        tool_calls=message.tool_calls or []
    )
    
    return api_response(data=response)

@router.delete("/{conversation_id}/messages", response_model=ApiResponse)
async def clear_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    清空会话消息
    """
    success = conversation_service.clear_messages(current_user.id, conversation_id)
    if not success:
        return api_response(code=404, message=f"会话 {conversation_id} 不存在")
    
    return api_response(message=f"会话 {conversation_id} 的消息已清空")

@router.post("/{conversation_id}/pin", response_model=ApiResponse)
async def pin_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    置顶会话
    """
    success = conversation_service.pin_conversation(current_user.id, conversation_id, True)
    if not success:
        return api_response(code=404, message=f"会话 {conversation_id} 不存在")
    
    return api_response(message=f"会话 {conversation_id} 已置顶")

@router.post("/{conversation_id}/unpin", response_model=ApiResponse)
async def unpin_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    取消置顶会话
    """
    success = conversation_service.pin_conversation(current_user.id, conversation_id, False)
    if not success:
        return api_response(code=404, message=f"会话 {conversation_id} 不存在")
    
    return api_response(message=f"会话 {conversation_id} 已取消置顶")

def _conversation_to_response(conversation) -> ConversationResponse:
    """将会话对象转换为响应格式"""
    messages = []
    for msg in conversation.messages:
        messages.append(MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp,
            metadata=msg.metadata,
            thinking=msg.thinking,
            tool_calls=msg.tool_calls or []
        ))
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        messages=messages,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        model_id=conversation.model_id,
        system_prompt=conversation.system_prompt,
        is_pinned=conversation.is_pinned,
        metadata=conversation.metadata
    ) 