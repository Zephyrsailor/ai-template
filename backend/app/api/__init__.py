"""
API包 - 提供所有API路由
"""
from fastapi import APIRouter

from .routes.chat import router as chat_router
from .routes.knowledge import router as knowledge_router
from .routes.mcp import router as mcp_router

# 创建主路由
api_router = APIRouter()

# 包含所有子路由
api_router.include_router(chat_router)
api_router.include_router(knowledge_router)
api_router.include_router(mcp_router)
