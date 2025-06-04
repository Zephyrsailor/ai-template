"""
API路由模块
"""
from fastapi import APIRouter

from . import auth, user, chat, knowledge, conversation, mcp, user_llm_config

# 创建主路由器
api_router = APIRouter(prefix="/api")

# 包含各个模块的路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(user.router, prefix="/users", tags=["用户"])
api_router.include_router(chat.router, prefix="/chat", tags=["聊天"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["知识库"])
api_router.include_router(conversation.router, prefix="/conversations", tags=["会话"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["MCP"])
api_router.include_router(user_llm_config.router, prefix="/llm-config", tags=["LLM配置"])

# 健康检查路由
@api_router.get("/health")
async def api_health():
    """API健康检查"""
    return {"status": "ok", "message": "API正常运行"}

__all__ = ["api_router"] 