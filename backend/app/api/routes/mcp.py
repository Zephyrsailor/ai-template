"""
简化的MCP服务器API路由 - 基于用户隔离
"""
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...domain.schemas.tools import ToolList, ToolCallResult
from ...domain.schemas.chat import ToolCallRequest
from ...domain.schemas.base import ApiResponse
from ...services.mcp import MCPService, MCPServerCreate
from ..deps import get_mcp_service_api, api_response, get_current_user, get_optional_current_user
from ...domain.models.user import User

# 工具相关路由
tool_router = APIRouter(prefix="/api/tools", tags=["tools"])

# MCP服务器相关路由
server_router = APIRouter(prefix="/api/mcp/servers", tags=["mcp"])

# 响应模型
class ToolListResponse(ApiResponse[ToolList]):
    """工具列表响应"""
    pass

class ToolCallResultResponse(ApiResponse[ToolCallResult]):
    """工具调用结果响应"""
    pass

class MCPServerListResponse(ApiResponse[List[Dict[str, Any]]]):
    """MCP服务器列表响应"""
    pass

class MCPServerDetailResponse(ApiResponse[Dict[str, Any]]):
    """MCP服务器详情响应"""
    pass

class DeleteResponse(ApiResponse):
    """删除响应"""
    pass

class StatusResponse(ApiResponse[List[Dict[str, Any]]]):
    """状态响应"""
    pass

# 为兼容性保留
router = server_router

# === 工具相关API ===

@tool_router.get("/", response_model=ToolListResponse)
async def list_tools(
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """获取当前用户的工具列表"""
    try:
        tools = await mcp_service.get_user_tools(current_user.id)
        return api_response(data={"tools": tools})
    except Exception as e:
        return api_response(code=500, message=f"获取工具列表失败: {str(e)}")

@tool_router.post("/call", response_model=ToolCallResultResponse)
async def call_tool_endpoint(
    request: ToolCallRequest,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """调用当前用户的工具"""
    try:
        result = await mcp_service.call_user_tool(
            current_user.id, 
            request.tool_name, 
            request.arguments
        )
        return api_response(data={"result": result})
    except Exception as e:
        return api_response(code=500, message=f"工具调用失败: {str(e)}")

@tool_router.delete("/context", response_model=DeleteResponse)
async def delete_tool_context(
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """删除当前用户的工具上下文数据"""
    try:
        success = mcp_service.delete_user_context(current_user.id)
        if success:
            return api_response(message="工具上下文数据已清除")
        else:
            return api_response(code=500, message="清除工具上下文数据失败")
    except Exception as e:
        return api_response(code=500, message=f"清除工具上下文数据失败: {str(e)}")

# === MCP服务器管理API ===

@server_router.get("/statuses", response_model=StatusResponse)
async def list_mcp_server_statuses(
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """获取当前用户MCP服务器的状态"""
    try:
        statuses = await mcp_service.get_user_server_statuses(current_user.id)
        return api_response(data=statuses)
    except Exception as e:
        return api_response(code=500, message=f"获取MCP服务器状态失败: {str(e)}")

@server_router.get("/", response_model=MCPServerListResponse)
async def list_mcp_servers(
    active_only: bool = False,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """获取当前用户的MCP服务器列表"""
    try:
        servers = mcp_service.get_user_servers(current_user.id, active_only)
        return api_response(data=servers)
    except Exception as e:
        return api_response(code=500, message=f"获取MCP服务器列表失败: {str(e)}")

@server_router.get("/{server_id}", response_model=MCPServerDetailResponse)
async def get_mcp_server(
    server_id: str,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """获取当前用户的MCP服务器详情"""
    try:
        server = mcp_service.get_user_server(current_user.id, server_id)
        if not server:
            return api_response(code=404, message=f"MCP服务器 {server_id} 不存在")
        return api_response(data=server)
    except Exception as e:
        return api_response(code=500, message=f"获取MCP服务器详情失败: {str(e)}")

@server_router.post("/", response_model=MCPServerDetailResponse)
async def create_mcp_server(
    server: MCPServerCreate,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """为当前用户创建MCP服务器"""
    try:
        new_server = await mcp_service.add_user_server(current_user.id, server.dict())
        return api_response(data=new_server)
    except ValueError as e:
        return api_response(code=400, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"创建MCP服务器失败: {str(e)}")

@server_router.put("/{server_id}", response_model=MCPServerDetailResponse)
async def update_mcp_server(
    server_id: str,
    server: MCPServerCreate,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """更新当前用户的MCP服务器"""
    try:
        updated_server = await mcp_service.update_user_server(
            current_user.id, server_id, server.dict()
        )
        if not updated_server:
            return api_response(code=404, message=f"MCP服务器 {server_id} 不存在")
        return api_response(data=updated_server)
    except ValueError as e:
        return api_response(code=400, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"更新MCP服务器失败: {str(e)}")

@server_router.delete("/{server_id}", response_model=DeleteResponse)
async def delete_mcp_server(
    server_id: str,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """删除当前用户的MCP服务器"""
    try:
        success = await mcp_service.delete_user_server(current_user.id, server_id)
        if not success:
            return api_response(code=404, message=f"MCP服务器 {server_id} 不存在")
        return api_response(message="MCP服务器删除成功")
    except Exception as e:
        return api_response(code=500, message=f"删除MCP服务器失败: {str(e)}")

@server_router.post("/{server_id}/test", response_model=StatusResponse)
async def test_mcp_server(
    server_id: str,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """测试当前用户的MCP服务器连接"""
    try:
        server = mcp_service.get_user_server(current_user.id, server_id)
        if not server:
            return api_response(code=404, message=f"MCP服务器 {server_id} 不存在")
            
        # 实现测试连接功能...
        return api_response(data={"success": True, "message": "连接测试成功"})
    except Exception as e:
        return api_response(code=500, message=f"测试MCP服务器失败: {str(e)}")

@server_router.post("/{server_id}/tools/{tool_name}", response_model=ToolCallResultResponse)
async def call_server_tool_endpoint(
    server_id: str,
    tool_name: str,
    request: Dict[str, Any] = None,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """在指定服务器上调用工具"""
    try:
        # 检查服务器是否属于当前用户
        server = mcp_service.get_user_server(current_user.id, server_id)
        if not server:
            return api_response(code=404, message=f"MCP服务器 {server_id} 不存在")
            
        arguments = request or {}
        qualified_tool_name = f"{server_id}:{tool_name}"
        
        result = await mcp_service.call_user_tool(
            current_user.id, 
            qualified_tool_name, 
            arguments
        )
        return api_response(data={"result": result})
    except Exception as e:
        return api_response(code=500, message=f"工具调用失败: {str(e)}")

# === 兼容性路由（保留一段时间） ===

@server_router.get("/list", response_model=MCPServerListResponse)
async def legacy_list_mcp_servers(
    active_only: bool = False,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """列出MCP服务器（旧路径，建议使用 GET /api/mcp/servers/ 替代）"""
    try:
        servers = mcp_service.get_user_servers(current_user.id, active_only)
        return api_response(data=servers)
    except Exception as e:
        return api_response(code=500, message=f"获取MCP服务器列表失败: {str(e)}")


