"""
认证相关API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ...domain.schemas.user import UserLogin, UserCreate, UserResponse, Token, PasswordChange
from ...domain.schemas.base import ApiResponse
from ...services.user import UserService
from ...domain.models.user import User
from ..deps import get_user_service, get_current_user, api_response

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 响应模型
class TokenResponse(ApiResponse[Token]):
    """Token响应"""
    pass

class UserResponseWrapper(ApiResponse[UserResponse]):
    """用户响应"""
    pass

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service)
):
    """
    用户登录
    """
    user = user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 创建访问令牌
    token = user_service.create_access_token_for_user(user)
    
    return api_response(data={"access_token": token, "token_type": "bearer"})

@router.post("/register", response_model=UserResponseWrapper)
async def register(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    用户注册
    """
    try:
        user = user_service.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name
        )
        
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
    except ValueError as e:
        return api_response(code=400, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"注册失败: {str(e)}")

@router.get("/me", response_model=UserResponseWrapper)
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
        created_at=current_user.created_at
    )
    
    return api_response(data=user_response)

@router.post("/change-password", response_model=ApiResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    修改密码
    """
    success = user_service.change_password(
        user_id=current_user.id,
        current_password=password_data.current_password,
        new_password=password_data.new_password
    )
    
    if not success:
        return api_response(code=400, message="当前密码不正确")
    
    return api_response(message="密码修改成功") 