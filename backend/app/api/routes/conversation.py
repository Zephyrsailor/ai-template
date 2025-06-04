"""
会话API路由
"""
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...domain.schemas.conversation import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    ConversationDetailResponse, ConversationListResponse, MessageCreate, MessageResponse,
    MessageListResponse
)
from ...domain.schemas.base import ApiResponse
from ...services.conversation import ConversationService
from ...domain.models.user import User
from ...core.messages import get_message, MessageKeys
from ..deps import get_current_user, get_conversation_service
from ...core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

@router.get("/", response_model=ApiResponse[List[ConversationResponse]])
async def list_conversations(
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    获取用户的会话列表
    
    Args:
        page: 页码，默认为1
        page_size: 每页大小，默认为50
    """
    try:
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 服务层现在返回包含分页信息的字典
        conversation_data = await conversation_service.list_conversations(
            current_user.id, 
            limit=page_size, 
            offset=offset
        )
        
        # 返回标准格式，data字段直接是会话数组
        return ApiResponse(
            success=True,
            code=200,
            message=get_message(MessageKeys.SUCCESS),
            data=conversation_data.get('conversations', [])
        )
    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}", exc_info=True)
        return ApiResponse(
            success=False,
            code=500,
            message=get_message(MessageKeys.INTERNAL_ERROR),
            data=[]
        )

@router.post("/", response_model=ApiResponse[ConversationResponse])
async def create_conversation(
    conversation_create: ConversationCreate,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    创建新会话
    """
    try:
        conversation = await conversation_service.create_conversation(
            user_id=current_user.id,
            title=conversation_create.title
        )
        return ApiResponse(
            success=True,
            code=200,
            message=get_message(MessageKeys.CONVERSATION_CREATED),
            data=conversation
        )
    except Exception as e:
        logger.error(f"创建会话失败: {str(e)}", exc_info=True)
        return ApiResponse(
            success=False,
            code=500,
            message=get_message(MessageKeys.INTERNAL_ERROR)
        )

@router.get("/{conversation_id}", response_model=ApiResponse[ConversationDetailResponse])
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    获取特定会话详情（包含消息）
    """
    try:
        conversation = await conversation_service.get_conversation(current_user.id, conversation_id)
        if not conversation:
            return ApiResponse(
                success=False,
                code=404,
                message=get_message(MessageKeys.CONVERSATION_NOT_FOUND, conversation_id=conversation_id),
                data=None
            )
        
        # 获取消息列表
        messages = await conversation_service.get_conversation_messages(current_user.id, conversation_id)
        
        # 构造响应数据
        response_data = {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "message_count": conversation.message_count,
            "is_pinned": conversation.is_pinned,
            "model_id": conversation.model_id,
            "system_prompt": conversation.system_prompt,
            "metadata": conversation.metadata,
            "messages": messages
        }
        
        return ApiResponse(
            success=True,
            code=200,
            message=get_message(MessageKeys.SUCCESS),
            data=response_data
        )
    except Exception as e:
        logger.error(f"获取会话详情失败 {conversation_id}: {str(e)}", exc_info=True)
        return ApiResponse(
            success=False,
            code=500,
            message=get_message(MessageKeys.INTERNAL_ERROR),
            data=None
        )

@router.put("/{conversation_id}", response_model=ApiResponse[ConversationResponse])
async def update_conversation(
    conversation_id: str,
    conversation_update: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    更新会话信息
    """
    try:
        conversation = await conversation_service.update_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
            title=conversation_update.title
        )
        
        if not conversation:
            return ApiResponse(
                success=False,
                code=404,
                message=get_message(MessageKeys.CONVERSATION_NOT_FOUND, conversation_id=conversation_id)
            )
        
        return ApiResponse(
            success=True,
            code=200,
            message=get_message(MessageKeys.CONVERSATION_UPDATED),
            data=conversation
        )
    except Exception as e:
        logger.error(f"更新会话失败 {conversation_id}: {str(e)}", exc_info=True)
        return ApiResponse(
            success=False,
            code=500,
            message=get_message(MessageKeys.INTERNAL_ERROR)
        )

@router.delete("/{conversation_id}", response_model=ApiResponse)
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    删除会话
    """
    try:
        success = await conversation_service.delete_conversation(current_user.id, conversation_id)
        if not success:
            return ApiResponse(
                success=False,
                code=404,
                message=get_message(MessageKeys.CONVERSATION_NOT_FOUND, conversation_id=conversation_id)
            )
        
        return ApiResponse(
            success=True,
            code=200,
            message=get_message(MessageKeys.CONVERSATION_DELETED, conversation_id=conversation_id)
        )
    except Exception as e:
        logger.error(f"删除会话失败 {conversation_id}: {str(e)}", exc_info=True)
        return ApiResponse(
            success=False,
            code=500,
            message=get_message(MessageKeys.INTERNAL_ERROR)
        )

@router.get("/{conversation_id}/messages", response_model=ApiResponse[List[Dict[str, Any]]])
async def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    获取会话的消息列表
    """
    try:
        # 首先验证会话是否存在且属于当前用户
        conversation = await conversation_service.get_conversation(current_user.id, conversation_id)
        if not conversation:
            return ApiResponse(
                success=False,
                code=404,
                message=get_message(MessageKeys.CONVERSATION_NOT_FOUND, conversation_id=conversation_id)
            )
        
        messages = await conversation_service.get_conversation_messages(current_user.id, conversation_id)
        return ApiResponse(
            success=True,
            code=200,
            message=get_message(MessageKeys.SUCCESS),
            data=messages
        )
    except Exception as e:
        logger.error(f"获取会话消息失败 {conversation_id}: {str(e)}", exc_info=True)
        return ApiResponse(
            success=False,
            code=500,
            message=get_message(MessageKeys.INTERNAL_ERROR)
        )

@router.post("/{conversation_id}/messages", response_model=ApiResponse[MessageResponse])
async def add_message(
    conversation_id: str,
    message_create: MessageCreate,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    向会话添加消息
    """
    try:
        # 首先验证会话是否存在且属于当前用户
        conversation = await conversation_service.get_conversation(current_user.id, conversation_id)
        if not conversation:
            return ApiResponse(
                success=False,
                code=404,
                message=get_message(MessageKeys.CONVERSATION_NOT_FOUND, conversation_id=conversation_id)
            )
        
        message = await conversation_service.add_message(
            user_id=current_user.id,
            conversation_id=conversation_id,
            role=message_create.role,
            content=message_create.content,
            metadata=message_create.metadata,
            thinking=message_create.thinking,
            tool_calls=message_create.tool_calls
        )
        
        return ApiResponse(
            success=True,
            code=200,
            message=get_message(MessageKeys.SUCCESS),
            data=message
        )
    except Exception as e:
        logger.error(f"添加消息失败 {conversation_id}: {str(e)}", exc_info=True)
        return ApiResponse(
            success=False,
            code=500,
            message=get_message(MessageKeys.INTERNAL_ERROR)
        ) 
