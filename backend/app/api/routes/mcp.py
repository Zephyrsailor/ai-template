"""
MCP (Model Context Protocol) API路由
提供MCP服务器管理和协议交互的RESTful API
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel

from ...domain.models.user import User
from ...domain.models.mcp import (
    MCPServerCreateRequest, MCPServerCreate, MCPServerUpdate, MCPServerResponse, 
    MCPServerStatus, MCPTool, MCPResource, MCPPrompt,
    MCPToolCall, MCPToolResult, MCPConnectionTest
)
from ...domain.schemas.base import ApiResponse
from ...services.mcp import MCPService
from ...core.errors import NotFoundException, ConflictException, ValidationException
from ..deps import get_mcp_service, api_response, get_current_user
from ...core.logging import get_logger

logger = get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/mcp", tags=["MCP"])

# === 响应模型定义 ===

class ServerListResponse(ApiResponse[List[MCPServerResponse]]):
    """服务器列表响应"""
    pass

class ServerResponse(ApiResponse[MCPServerResponse]):
    """单个服务器响应"""
    pass

class ServerStatusListResponse(ApiResponse[List[MCPServerStatus]]):
    """服务器状态列表响应"""
    pass

class ConnectionTestResponse(ApiResponse[MCPConnectionTest]):
    """连接测试响应"""
    pass

class ToolListResponse(ApiResponse[Dict[str, Any]]):
    """工具列表响应"""
    pass

class ResourceListResponse(ApiResponse[List[MCPResource]]):
    """资源列表响应"""
    pass

class PromptListResponse(ApiResponse[List[MCPPrompt]]):
    """提示模板列表响应"""
    pass

class ToolCallResponse(ApiResponse[MCPToolResult]):
    """工具调用响应"""
    pass

class BatchOperationResponse(ApiResponse[Dict[str, Any]]):
    """批量操作响应"""
    pass

class StatsResponse(ApiResponse[Dict[str, Any]]):
    """统计信息响应"""
    pass

# === 基础CRUD API ===

@router.post("/servers", response_model=ServerResponse, status_code=201)
async def create_server(
    server_data: MCPServerCreateRequest,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """创建新的MCP服务器"""
    try:
        # 添加用户ID到服务器数据
        server_create_data = MCPServerCreate(**server_data.dict(), user_id=current_user.id)
        server = await mcp_service.create_server(current_user.id, server_create_data)
        return api_response(data=server, message="MCP服务器创建成功", code=201)
    except ConflictException as e:
        return api_response(code=409, message=str(e))
    except ValidationException as e:
        return api_response(code=400, message=str(e))
    except Exception as e:
        logger.error(f"创建MCP服务器失败: {str(e)}")
        return api_response(code=500, message=f"创建MCP服务器失败: {str(e)}")

@router.get("/servers", response_model=ServerListResponse)
async def list_servers(
    active_only: bool = Query(False, description="是否只返回活跃服务器"),
    connected_only: bool = Query(False, description="是否只返回已连接的服务器（聊天场景）"),
    user_specific: bool = Query(True, description="用户特定数据（兼容参数）"),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """获取用户的MCP服务器列表"""
    try:
        if connected_only:
            # 聊天场景：只返回已初始化且连接的服务器状态
            statuses = await mcp_service.get_connected_server_statuses(current_user.id)
            # 将状态转换为服务器响应格式
            servers = []
            for status in statuses:
                server = await mcp_service.get_server(status.server_id, current_user.id)
                servers.append(server)
            return api_response(data=servers)
        else:
            # 管理场景：返回所有服务器
            servers = await mcp_service.list_servers(current_user.id, active_only)
            return api_response(data=servers)
    except Exception as e:
        return api_response(code=500, message=f"获取服务器列表失败: {str(e)}")

# === 服务器状态管理API ===

@router.get("/servers/status/all", response_model=ServerStatusListResponse)
async def get_all_server_statuses(
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """获取用户所有服务器的状态"""
    try:
        statuses = await mcp_service.get_server_statuses(current_user.id)
        return api_response(data=statuses)
    except Exception as e:
        return api_response(code=500, message=f"获取服务器状态失败: {str(e)}")

# 添加前端期望的路径别名
@router.get("/servers/statuses", response_model=ServerStatusListResponse)
async def list_mcp_server_statuses(
    connected_only: bool = Query(False, description="是否只返回已连接的服务器（聊天场景）"),
    user_specific: bool = Query(True, description="用户特定数据（兼容参数）"),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """获取用户服务器状态列表"""
    try:
        if connected_only:
            # 聊天场景：只返回已初始化且连接的服务器
            statuses = await mcp_service.get_connected_server_statuses(current_user.id)
        else:
            # 管理场景：返回所有服务器状态
            statuses = await mcp_service.get_server_statuses(current_user.id)
        return api_response(data=statuses)
    except Exception as e:
        return api_response(code=500, message=f"获取服务器状态失败: {str(e)}")

# === 批量操作API ===

class BatchServerOperation(BaseModel):
    """批量服务器操作请求"""
    server_ids: List[str]

@router.post("/servers/batch/activate", response_model=BatchOperationResponse)
async def batch_activate_servers(
    operation: BatchServerOperation,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """批量激活服务器"""
    try:
        result = await mcp_service.batch_activate_servers(operation.server_ids, current_user.id)
        return api_response(data=result, message=f"成功激活 {result['activated_count']} 个服务器")
    except Exception as e:
        return api_response(code=500, message=f"批量激活服务器失败: {str(e)}")

@router.post("/servers/batch/deactivate", response_model=BatchOperationResponse)
async def batch_deactivate_servers(
    operation: BatchServerOperation,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """批量停用服务器"""
    try:
        result = await mcp_service.batch_deactivate_servers(operation.server_ids, current_user.id)
        return api_response(data=result, message=f"成功停用 {result['deactivated_count']} 个服务器")
    except Exception as e:
        return api_response(code=500, message=f"批量停用服务器失败: {str(e)}")

# === 参数化路径API（必须放在具体路径之后） ===

@router.get("/servers/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: str = Path(..., description="服务器ID"),
    user_specific: bool = Query(True, description="用户特定数据（兼容参数）"),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """获取特定MCP服务器详情"""
    try:
        server = await mcp_service.get_server(server_id, current_user.id)
        return api_response(data=server)
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"获取服务器详情失败: {str(e)}")

@router.put("/servers/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: str = Path(..., description="服务器ID"),
    update_data: MCPServerUpdate = Body(...),
    user_specific: bool = Query(True, description="用户特定数据（兼容参数）"),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """更新MCP服务器"""
    try:
        server = await mcp_service.update_server(server_id, current_user.id, update_data)
        return api_response(data=server, message="MCP服务器更新成功")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except ConflictException as e:
        return api_response(code=409, message=str(e))
    except ValidationException as e:
        return api_response(code=400, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"更新MCP服务器失败: {str(e)}")

@router.delete("/servers/{server_id}")
async def delete_server(
    server_id: str = Path(..., description="服务器ID"),
    user_specific: bool = Query(True, description="用户特定数据（兼容参数）"),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """删除MCP服务器"""
    try:
        success = await mcp_service.delete_server(server_id, current_user.id)
        if success:
            return api_response(message="MCP服务器删除成功")
        else:
            return api_response(code=500, message="删除MCP服务器失败")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"删除MCP服务器失败: {str(e)}")

@router.post("/servers/{server_id}/connect", response_model=ConnectionTestResponse)
async def connect_server(
    server_id: str = Path(..., description="服务器ID"),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """连接到MCP服务器"""
    try:
        result = await mcp_service.connect_server(server_id, current_user.id)
        return api_response(data=result, message="服务器连接成功" if result.success else "服务器连接失败")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except ValidationException as e:
        return api_response(code=400, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"连接服务器失败: {str(e)}")

@router.post("/servers/{server_id}/disconnect")
async def disconnect_server(
    server_id: str = Path(..., description="服务器ID"),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """断开MCP服务器连接"""
    try:
        success = await mcp_service.disconnect_server(server_id, current_user.id)
        if success:
            return api_response(message="服务器连接已断开")
        else:
            return api_response(code=500, message="断开服务器连接失败")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"断开服务器连接失败: {str(e)}")

@router.post("/servers/{server_id}/refresh", response_model=ConnectionTestResponse)
async def refresh_server_connection(
    server_id: str = Path(..., description="服务器ID"),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """刷新/重连MCP服务器连接"""
    try:
        # refresh_server_connection返回MCPServerStatus，不是MCPConnectionTest
        status = await mcp_service.refresh_server_connection(server_id, current_user.id)
        
        # 根据状态创建连接测试结果
        success = status.connected and status.healthy
        message = "服务器连接刷新成功" if success else f"服务器连接刷新失败: {status.error_message or '连接异常'}"
        
        # 创建MCPConnectionTest对象返回
        from app.domain.models.mcp import MCPConnectionTest
        result = MCPConnectionTest(
            success=success,
            message=message,
            latency_ms=None,  # 刷新操作不测量延迟
            capabilities=[]   # 可以从status.capabilities获取，但这里简化处理
        )
        
        return api_response(data=result, message=message)
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"刷新服务器连接失败: {str(e)}")

@router.post("/servers/{server_id}/test", response_model=ConnectionTestResponse)
async def test_server_connection(
    server_id: str = Path(..., description="服务器ID"),
    user_specific: bool = Query(True, description="用户特定数据（兼容参数）"),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """测试MCP服务器连接"""
    try:
        result = await mcp_service.test_server_connection(server_id, current_user.id)
        return api_response(data=result, message="连接测试完成")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"测试服务器连接失败: {str(e)}")

@router.get("/servers/{server_id}/status", response_model=ApiResponse[MCPServerStatus])
async def get_server_status(
    server_id: str = Path(..., description="服务器ID"),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """获取单个服务器的详细状态"""
    try:
        status = await mcp_service.get_server_status(server_id, current_user.id)
        return api_response(data=status, message="获取服务器状态成功")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"获取服务器状态失败: {str(e)}")

# === 工具管理API ===

@router.get("/tools", response_model=ToolListResponse)
async def get_user_tools(
    server_ids: Optional[List[str]] = Query(None, description="指定服务器ID列表"),
    category: Optional[str] = Query(None, description="工具分类过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=100),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """获取用户的 MCP 工具列表"""
    try:
        if search:
            # 搜索工具
            tools = await mcp_service.search_tools(current_user.id, search, limit)
        elif category:
            # 按分类获取工具 - 先获取所有工具再过滤
            all_tools = await mcp_service.get_all_user_tools(current_user.id)
            tools = [tool for tool in all_tools if tool.category == category]
            tools = tools[:limit]
        elif server_ids:
            # 获取指定服务器的工具
            tools = await mcp_service.get_user_tools(current_user.id, server_ids)
            tools = tools[:limit]
        else:
            # 获取所有工具
            tools = await mcp_service.get_all_user_tools(current_user.id)
            tools = tools[:limit]
        
        return api_response(data={
            "tools": tools,
            "total": len(tools),
            "filters": {
                "server_ids": server_ids,
                "category": category,
                "search": search
            }
        })
    except Exception as e:
        logger.error(f"获取用户工具列表失败: {str(e)}")
        return api_response(code=500, message=f"获取工具列表失败: {str(e)}")

@router.get("/tools/categories")
async def get_tool_categories(
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """获取工具分类统计"""
    try:
        categorized_tools = await mcp_service.get_tools_by_category(current_user.id)
        
        categories = []
        for category, tools in categorized_tools.items():
            categories.append({
                "name": category,
                "count": len(tools),
                "tools": [{"name": tool.name, "server_name": tool.server_name} for tool in tools[:5]]  # 只返回前5个作为预览
            })
        
        return api_response(data={
            "categories": categories,
            "total_tools": sum(len(tools) for tools in categorized_tools.values())
        })
    except Exception as e:
        logger.error(f"获取工具分类失败: {str(e)}")
        return api_response(code=500, message=f"获取工具分类失败: {str(e)}")

@router.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(
    tool_call: MCPToolCall,
    server_id: Optional[str] = Query(None, description="服务器ID（可选）"),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """调用MCP工具"""
    try:
        # MCPService.call_tool 接受 (user_id, tool_name, arguments)
        result = await mcp_service.call_tool(
            current_user.id, 
            tool_call.tool_name, 
            tool_call.arguments
        )
        return api_response(data=result, message="工具调用完成")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"工具调用失败: {str(e)}")

# === 资源管理API ===

@router.get("/resources", response_model=ResourceListResponse)
async def list_resources(
    server_id: Optional[str] = Query(None, description="服务器ID（可选）"),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """获取可用资源列表"""
    try:
        resources = await mcp_service.list_resources(current_user.id, server_id)
        return api_response(data=resources)
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"获取资源列表失败: {str(e)}")

# === 提示模板管理API ===

@router.get("/prompts", response_model=PromptListResponse)
async def list_prompts(
    server_id: Optional[str] = Query(None, description="服务器ID（可选）"),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """获取可用提示模板列表"""
    try:
        prompts = await mcp_service.list_prompts(current_user.id, server_id)
        return api_response(data=prompts)
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"获取提示模板列表失败: {str(e)}")

# === 统计信息API ===

@router.get("/stats", response_model=StatsResponse)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """获取用户MCP统计信息"""
    try:
        stats = await mcp_service.get_user_stats(current_user.id)
        return api_response(data=stats)
    except Exception as e:
        return api_response(code=500, message=f"获取统计信息失败: {str(e)}")


