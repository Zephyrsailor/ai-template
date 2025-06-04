"""
API工具函数模块

提供标准化的响应构建、错误处理等工具函数。
"""
from typing import Any, Dict, List, Optional, TypeVar, Union
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from ..domain.schemas.base import (
    ApiResponse, ErrorResponse, PageResponse, PageInfo,
    SuccessResponse, IdResponse, MessageResponse
)
from ..core.logging import get_api_logger
from ..core.constants import APIConstants, ValidationConstants

logger = get_api_logger()
T = TypeVar('T')


def create_response(
    data: Optional[T] = None,
    message: str = "操作成功",
    code: int = 200,
    request_id: Optional[str] = None
) -> ApiResponse[T]:
    """创建标准API响应"""
    return ApiResponse(
        success=True,
        code=code,
        message=message,
        data=data,
        request_id=request_id
    )


def create_error_response(
    message: str = "操作失败",
    code: int = APIConstants.HTTP_INTERNAL_ERROR,
    error_type: str = "ServerError",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """创建错误响应"""
    return ErrorResponse(
        success=False,
        code=code,
        message=message,
        error_type=error_type,
        details=details,
        request_id=request_id
    )


def create_page_response(
    data: List[T],
    page: int,
    size: int,
    total: int,
    message: str = "查询成功",
    request_id: Optional[str] = None
) -> PageResponse[T]:
    """创建分页响应"""
    page_info = PageInfo.create(page=page, size=size, total=total)
    return PageResponse(
        success=True,
        code=200,
        message=message,
        data=data,
        page_info=page_info,
        request_id=request_id
    )


def create_success_response(
    data: Any = None,
    message: str = "操作成功",
    code: int = APIConstants.HTTP_OK,
    request_id: Optional[str] = None
) -> ApiResponse:
    """创建成功响应（无数据）"""
    return create_response(data=data, message=message, code=code, request_id=request_id)


def create_id_response(
    resource_id: str,
    message: str = "创建成功",
    request_id: Optional[str] = None
) -> ApiResponse[IdResponse]:
    """创建ID响应"""
    return create_response(
        data=IdResponse(id=resource_id),
        message=message,
        request_id=request_id
    )


def create_message_response(
    message: str,
    request_id: Optional[str] = None
) -> ApiResponse[MessageResponse]:
    """创建消息响应"""
    return create_response(
        data=MessageResponse(message=message),
        message="操作成功",
        request_id=request_id
    )


def get_request_id(request: Request) -> Optional[str]:
    """从请求中获取request_id"""
    return getattr(request.state, "request_id", None)


def handle_api_error(
    error: Exception,
    request: Optional[Request] = None,
    default_message: str = "服务器内部错误"
) -> JSONResponse:
    """统一处理API错误"""
    request_id = get_request_id(request) if request else None
    
    # 根据异常类型确定状态码和消息
    if isinstance(error, HTTPException):
        code = error.status_code
        message = error.detail
        error_type = "HTTPException"
    elif isinstance(error, ValueError):
        code = status.HTTP_400_BAD_REQUEST
        message = str(error)
        error_type = "ValueError"
    elif isinstance(error, PermissionError):
        code = status.HTTP_403_FORBIDDEN
        message = "权限不足"
        error_type = "PermissionError"
    elif isinstance(error, FileNotFoundError):
        code = status.HTTP_404_NOT_FOUND
        message = "资源不存在"
        error_type = "FileNotFoundError"
    else:
        code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = default_message
        error_type = type(error).__name__
        
        # 记录未知错误
        logger.error(f"未处理的API错误: {error}", exc_info=True)
    
    # 创建错误响应
    error_response = create_error_response(
        message=message,
        code=code,
        error_type=error_type,
        details={"original_error": str(error)} if code == APIConstants.HTTP_INTERNAL_ERROR else None,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=code,
        content=error_response.model_dump()
    )


def validate_pagination_params(
    page: int = APIConstants.DEFAULT_PAGE,
    size: int = APIConstants.DEFAULT_PAGE_SIZE,
    max_size: int = APIConstants.MAX_PAGE_SIZE
) -> tuple[int, int]:
    """验证分页参数"""
    if page < APIConstants.DEFAULT_PAGE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="页码必须大于0"
        )
    
    if size < APIConstants.MIN_PAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="每页数量必须大于0"
        )
    
    if size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"每页数量不能超过{max_size}"
        )
    
    return page, size


def validate_resource_id(resource_id: str, resource_name: str = "资源") -> str:
    """验证资源ID"""
    if not resource_id or not resource_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{resource_name}ID不能为空"
        )
    
    return resource_id.strip()


def parse_query_params(
    request: Request,
    allowed_params: Optional[List[str]] = None
) -> Dict[str, Any]:
    """解析查询参数"""
    params = dict(request.query_params)
    
    if allowed_params:
        # 过滤允许的参数
        params = {k: v for k, v in params.items() if k in allowed_params}
    
    return params


def format_validation_error(error: Exception) -> Dict[str, Any]:
    """格式化验证错误"""
    if hasattr(error, 'errors'):
        # Pydantic验证错误
        return {
            "validation_errors": error.errors()
        }
    
    return {
        "error": str(error)
    }


class APIResponseBuilder:
    """API响应构建器"""
    
    def __init__(self, request: Optional[Request] = None):
        self.request = request
        self.request_id = get_request_id(request) if request else None
    
    def success(
        self,
        data: Optional[T] = None,
        message: str = "操作成功",
        code: int = 200
    ) -> ApiResponse[T]:
        """构建成功响应"""
        return create_response(
            data=data,
            message=message,
            code=code,
            request_id=self.request_id
        )
    
    def error(
        self,
        message: str,
        code: int = 500,
        error_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> ErrorResponse:
        """构建错误响应"""
        return create_error_response(
            message=message,
            code=code,
            error_type=error_type,
            details=details,
            request_id=self.request_id
        )
    
    def page(
        self,
        data: List[T],
        page: int,
        size: int,
        total: int,
        message: str = "查询成功"
    ) -> PageResponse[T]:
        """构建分页响应"""
        return create_page_response(
            data=data,
            page=page,
            size=size,
            total=total,
            message=message,
            request_id=self.request_id
        )
    
    def created(
        self,
        resource_id: str,
        message: str = "创建成功"
    ) -> ApiResponse[IdResponse]:
        """构建创建成功响应"""
        return create_id_response(
            resource_id=resource_id,
            message=message,
            request_id=self.request_id
        )
    
    def deleted(self, message: str = "删除成功") -> SuccessResponse:
        """构建删除成功响应"""
        return create_success_response(
            message=message,
            request_id=self.request_id
        )
    
    def updated(
        self,
        data: Optional[T] = None,
        message: str = "更新成功"
    ) -> ApiResponse[T]:
        """构建更新成功响应"""
        return create_response(
            data=data,
            message=message,
            request_id=self.request_id
        )


def create_paginated_response(
    data: List[Any],
    total: int,
    page: int,
    size: int,
    message: str = "查询成功",
    code: int = APIConstants.HTTP_OK
) -> ApiResponse:
    """构建分页响应"""
    page_info = PageInfo.create(page=page, size=size, total=total)
    return ApiResponse(
        success=True,
        code=code,
        message=message,
        data=data,
        page_info=page_info,
        request_id=None
    )


def create_api_response(
    data: Any = None,
    message: str = "操作成功",
    success: bool = True,
    code: int = APIConstants.HTTP_OK,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """构建API响应"""
    return {
        "success": success,
        "code": code,
        "message": message,
        "data": data,
        "request_id": request_id
    }


def handle_service_error(
    error: Exception,
    default_message: str = "服务处理失败",
    code: int = APIConstants.HTTP_INTERNAL_ERROR,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """处理服务错误"""
    message = default_message
    error_type = "ServerError"
    
    # 记录未知错误
    logger.error(f"未处理的API错误: {error}", exc_info=True)
    
    # 创建错误响应
    error_response = create_error_response(
        message=message,
        code=code,
        error_type=error_type,
        details={"original_error": str(error)} if code == APIConstants.HTTP_INTERNAL_ERROR else None,
        request_id=request_id
    )
    
    return error_response 