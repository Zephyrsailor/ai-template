"""
认证相关API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ...domain.schemas.user import UserLogin, UserCreate, UserResponse, Token, PasswordChange
from ...domain.schemas.base import ApiResponse
from ...services.user import UserService
from ...domain.models.user import User
from ..deps import get_user_service, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=ApiResponse[Token])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service)
):
    """
    用户登录
    """
    user = await user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        return ApiResponse(
            success=False,
            code=401,
            message="用户名或密码错误",
            data=None
        )
    
    # 创建访问令牌
    token = user_service.create_access_token_for_user(user)
    
    return ApiResponse(
        success=True,
        code=200,
        message="登录成功",
        data={"access_token": token, "token_type": "bearer"}
    )

@router.post("/register", response_model=ApiResponse[UserResponse])
async def register(
    user_create: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    用户注册
    """
    try:
        # 检查用户是否已存在
        existing_user = await user_service.get_user_by_username(user_create.username)
        if existing_user:
            return ApiResponse(
                success=False,
                code=400,
                message="用户名已存在"
            )
        
        # 创建用户
        user = await user_service.create_user(user_create)
        
        # 转换为响应格式
        user_response = UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else None
        )
        
        return ApiResponse(
            success=True,
            code=200,
            message="注册成功",
            data=user_response
        )
    except ValueError as e:
        return ApiResponse(
            success=False,
            code=400,
            message=str(e)
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            code=500,
            message=f"注册失败: {str(e)}"
        )

@router.get("/me", response_model=ApiResponse[UserResponse])
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户信息
    """
    user_response = UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None
    )
    
    return ApiResponse(
        success=True,
        code=200,
        message="获取用户信息成功",
        data=user_response
    )

@router.post("/change-password", response_model=ApiResponse)
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    修改密码
    """
    try:
        # 验证旧密码
        if not user_service.verify_password(password_change.old_password, current_user.password_hash):
            return ApiResponse(
                success=False,
                code=400,
                message="旧密码错误"
            )
        
        # 更新密码
        await user_service.update_password(current_user.id, password_change.new_password)
        
        return ApiResponse(
            success=True,
            code=200,
            message="密码修改成功"
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            code=500,
            message=f"密码修改失败: {str(e)}"
        )

@router.post("/logout", response_model=ApiResponse)
async def logout():
    """
    用户登出（客户端删除token即可）
    """
    return ApiResponse(
        success=True,
        code=200,
        message="登出成功"
    ) 