"""
用户管理API路由
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from ...domain.schemas.user import UserResponse, UserUpdate
from ...domain.schemas.base import ApiResponse
from ...services.user import UserService
from ...domain.models.user import User, UserRole
from ..deps import get_user_service, get_current_admin, api_response

router = APIRouter(prefix="/api/users", tags=["users"])

# 响应模型
class UserListResponse(ApiResponse[List[UserResponse]]):
    """用户列表响应"""
    pass

class UserDetailResponse(ApiResponse[UserResponse]):
    """用户详情响应"""
    pass

@router.get("/", response_model=UserListResponse)
async def list_users(
    current_admin: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    获取所有用户列表（仅管理员）
    """
    users = user_service.list_users()
    
    # 转换为响应格式
    user_responses = []
    for user in users:
        user_responses.append(UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            created_at=user.created_at
        ))
    
    return api_response(data=user_responses)

@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    获取用户详情（仅管理员）
    """
    user = user_service.get_user_by_id(user_id)
    if not user:
        return api_response(code=404, message=f"用户 {user_id} 不存在")
    
    # 转换为响应格式
    user_response = UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        created_at=user.created_at
    )
    
    return api_response(data=user_response)

@router.put("/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_admin: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    更新用户信息（仅管理员）
    """
    try:
        role = UserRole(user_data.role) if user_data.role else None
        updated_user = user_service.update_user(
            user_id=user_id,
            email=user_data.email,
            full_name=user_data.full_name,
            role=role
        )
        
        if not updated_user:
            return api_response(code=404, message=f"用户 {user_id} 不存在")
        
        # 转换为响应格式
        user_response = UserResponse(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            full_name=updated_user.full_name,
            role=updated_user.role,
            created_at=updated_user.created_at
        )
        
        return api_response(data=user_response)
    except ValueError as e:
        return api_response(code=400, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"更新用户失败: {str(e)}") 