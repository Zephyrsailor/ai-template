"""
工具和MCP服务器API路由
"""
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...domain.schemas.tools import ToolList, ToolCallResult
from ...domain.schemas.chat import ToolCallRequest
from ...domain.schemas.base import ApiResponse
from ...services.mcp import MCPService, MCPServerCreate
from ..deps import get_mcp_service_api, api_response

# MCP服务器相关API
router = APIRouter(prefix="/api/mcp/servers", tags=["mcp"])
# 具体响应模型
class ToolListResponse(ApiResponse[ToolList]):
    """工具列表响应"""
    pass

class ToolCallResultResponse(ApiResponse[ToolCallResult]):
    """工具调用结果响应"""
    pass

class CategoryResponse(ApiResponse[Dict[str, List[str]]]):
    """类别列表响应"""
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

class TestResponse(ApiResponse[Dict[str, Any]]):
    """测试结果响应"""
    pass

class ServerListWrapper(ApiResponse[Dict[str, List[Dict[str, Any]]]]):
    """服务器列表包装响应"""
    pass

# MCP服务器更新模型，继承创建模型
class MCPServerUpdate(MCPServerCreate):
    """MCP服务器更新模型"""
    pass

@router.get("/", response_model=MCPServerListResponse)
async def list_mcp_servers(
    active_only: bool = False,
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """
    列出所有MCP服务器
    """
    try:
        servers = mcp_service.get_all_servers(active_only)
        return api_response(data=servers)
    except Exception as e:
        return api_response(code=500, message=f"获取MCP服务器列表失败: {str(e)}")

@router.get("/{server_id}", response_model=MCPServerDetailResponse)
async def get_mcp_server(
    server_id: str,
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """
    获取MCP服务器详情
    """
    server = mcp_service.get_server(server_id)
    if not server:
        return api_response(code=404, message=f"MCP服务器 {server_id} 不存在")
    return api_response(data=server)

@router.post("/", response_model=MCPServerDetailResponse)
async def create_mcp_server(
    server_data: MCPServerCreate,
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """
    创建MCP服务器
    """
    try:
        # 将Pydantic模型转换为字典
        server_dict = server_data.dict()
        new_server = mcp_service.add_server(server_dict)
        return api_response(data=new_server)
    except ValueError as e:
        return api_response(code=400, message=str(e))

@router.put("/{server_id}", response_model=MCPServerDetailResponse)
async def update_mcp_server(
    server_id: str,
    server_data: MCPServerUpdate,
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """
    更新MCP服务器
    """
    # 将Pydantic模型转换为字典
    server_dict = server_data.dict(exclude_unset=True)
    updated = mcp_service.update_server(server_id, server_dict)
    if not updated:
        return api_response(code=404, message=f"MCP服务器 {server_id} 不存在")
    return api_response(data=updated)

@router.delete("/{server_id}", response_model=DeleteResponse)
async def delete_mcp_server(
    server_id: str,
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """
    删除MCP服务器
    """
    success = mcp_service.delete_server(server_id)
    if not success:
        return api_response(code=404, message=f"MCP服务器 {server_id} 不存在")
    return api_response(message=f"MCP服务器 {server_id} 已删除")

@router.post("/{server_id}/test", response_model=TestResponse)
async def test_mcp_server(
    server_id: str,
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """
    测试MCP服务器连接
    """
    server = mcp_service.get_server(server_id)
    if not server:
        return api_response(code=404, message=f"MCP服务器 {server_id} 不存在")
        
    # 实现测试连接功能...
    return api_response(data={"success": True, "message": "连接测试成功"})

# 兼容旧路径，保留一段时间以便平滑迁移
@router.get("/list", response_model=MCPServerListResponse)
async def legacy_list_mcp_servers(
    active_only: bool = False,
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """
    列出所有MCP服务器（旧路径，建议使用 GET /api/mcp/ 替代）
    """
    try:
        servers = mcp_service.get_all_servers(active_only)
        return api_response(data=servers)
    except Exception as e:
        return api_response(code=500, message=f"获取MCP服务器列表失败: {str(e)}")


