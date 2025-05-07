"""
全局依赖注入模块
"""
from typing import Optional

from .config import get_settings, get_provider
from ..services.mcp import MCPService
from ..services.knowledge import KnowledgeService

# 单例对象
_mcp_service: Optional[MCPService] = None
_knowledge_service: Optional[KnowledgeService] = None

async def get_mcp_service() -> MCPService:
    """获取MCP服务单例"""
    global _mcp_service
    
    if _mcp_service is None:
        settings = get_settings()
        _mcp_service = MCPService(config_path=getattr(settings, "MCP_CONFIG_PATH", None))
        await _mcp_service.initialize()
        
    return _mcp_service

def get_knowledge_service() -> KnowledgeService:
    """获取知识库服务单例"""
    global _knowledge_service
    
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
        
    return _knowledge_service 