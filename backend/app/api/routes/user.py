"""
用户管理API路由
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from ...domain.schemas.user import UserResponse, UserUpdate
from ...domain.schemas.base import ApiResponse
from ...services.user import UserService
from ...domain.models.user import User, UserRole
from ...core.messages import get_message, MessageKeys
from ..deps import get_user_service, get_current_admin, api_response

router = APIRouter(prefix="/api/users", tags=["users"])

# 响应模型
class UserListResponse(ApiResponse[List[UserResponse]]):
    """用户列表响应"""
    pass

class UserDetailResponse(ApiResponse[UserResponse]):
    """用户详情响应"""
    pass

class DeleteResponse(ApiResponse):
    """删除响应"""
    pass

@router.get("/", response_model=UserListResponse)
async def list_users(
    current_admin: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    获取用户列表（仅管理员）
    """
    try:
        users = user_service.list_users()
        user_responses = []
        
        for user in users:
            user_responses.append(UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at
            ))
        
        return api_response(
            data=user_responses,
            message=get_message(MessageKeys.SUCCESS)
        )
    except Exception as e:
        return api_response(
            code=500,
            message=get_message(MessageKeys.INTERNAL_ERROR)
        )

@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    获取用户详情（仅管理员）
    """
    try:
        user = user_service.get_user_by_id(user_id)
        if not user:
            return api_response(
                code=404,
                message=get_message(MessageKeys.USER_NOT_FOUND)
            )
        
        user_response = UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at
        )
        
        return api_response(
            data=user_response,
            message=get_message(MessageKeys.SUCCESS)
        )
    except Exception as e:
        return api_response(
            code=500,
            message=get_message(MessageKeys.INTERNAL_ERROR)
        )

@router.put("/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_admin: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    更新用户信息（仅管理员）
    """
    try:
        user = user_service.get_user_by_id(user_id)
        if not user:
            return api_response(
                code=404,
                message=get_message(MessageKeys.USER_NOT_FOUND)
            )
        
        # 更新用户信息
        updated_user = user_service.update_user(
            user_id=user_id,
            email=user_update.email,
            role=user_update.role,
            is_active=user_update.is_active
        )
        
        if not updated_user:
            return api_response(
                code=500,
                message=get_message(MessageKeys.INTERNAL_ERROR)
            )
        
        user_response = UserResponse(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            role=updated_user.role,
            is_active=updated_user.is_active,
            created_at=updated_user.created_at
        )
        
        return api_response(
            data=user_response,
            message=get_message(MessageKeys.USER_UPDATED)
        )
    except Exception as e:
        return api_response(
            code=500,
            message=get_message(MessageKeys.INTERNAL_ERROR)
        )

@router.delete("/{user_id}", response_model=DeleteResponse)
async def delete_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    删除用户（仅管理员）
    """
    try:
        # 不能删除自己
        if user_id == current_admin.id:
            return api_response(
                code=400,
                message=get_message(MessageKeys.BAD_REQUEST)
            )
        
        user = user_service.get_user_by_id(user_id)
        if not user:
            return api_response(
                code=404,
                message=get_message(MessageKeys.USER_NOT_FOUND)
            )
        
        success = user_service.delete_user(user_id)
        if not success:
            return api_response(
                code=500,
                message=get_message(MessageKeys.INTERNAL_ERROR)
            )
        
        return api_response(message=get_message(MessageKeys.USER_DELETED))
    except Exception as e:
        return api_response(
            code=500,
            message=get_message(MessageKeys.INTERNAL_ERROR)
        ) 
