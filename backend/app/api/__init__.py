"""
API包 - 提供所有API路由
"""
from fastapi import APIRouter, Depends
from .deps import get_current_user

from .routes.chat import router as chat_router
from .routes.knowledge import router as knowledge_router
from .routes.mcp import router as mcp_router, tool_router as tools_router
from .routes.auth import router as auth_router
from .routes.user import router as user_router
from .routes.conversation import router as conversation_router
from .routes.user_llm_config import router as user_llm_config_router

# 公开API路由（只包含无需认证的接口）
public_router = APIRouter()
public_router.include_router(auth_router)

# 添加公开的LLM提供商信息端点
from .routes.user_llm_config import get_available_providers
public_router.add_api_route("/api/user/llm-config/providers", get_available_providers, methods=["GET"])

# 需要认证的API路由，统一加全局依赖
protected_router = APIRouter(dependencies=[Depends(get_current_user)])
protected_router.include_router(chat_router)
protected_router.include_router(knowledge_router)
protected_router.include_router(mcp_router)
protected_router.include_router(tools_router)
protected_router.include_router(user_router)
protected_router.include_router(conversation_router)
protected_router.include_router(user_llm_config_router)

# 主路由
api_router = APIRouter()
api_router.include_router(public_router)
api_router.include_router(protected_router)
