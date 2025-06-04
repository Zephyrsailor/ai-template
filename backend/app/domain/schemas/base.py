"""
基础数据模型 - 提供通用的数据验证模型
"""
from datetime import datetime
from typing import TypeVar, Generic, Optional, Any, Dict, List, Union
from pydantic import BaseModel, Field, ConfigDict

# 泛型类型T，用于数据响应
T = TypeVar('T')

class BaseSchema(BaseModel):
    """基础Schema类"""
    model_config = ConfigDict(
        # 允许使用字段别名
        populate_by_name=True,
        # 验证赋值
        validate_assignment=True,
        # 使用枚举值
        use_enum_values=True,
        # 序列化时排除None值
        exclude_none=True,
    )

class ApiResponse(BaseSchema, Generic[T]):
    """标准API响应模型"""
    success: bool = Field(True, description="操作是否成功")
    code: int = Field(200, description="HTTP状态码")
    message: str = Field("操作成功", description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    request_id: Optional[str] = Field(None, description="请求ID")

class ErrorResponse(BaseSchema):
    """错误响应模型"""
    success: bool = Field(False, description="操作是否成功")
    code: int = Field(..., description="错误状态码")
    message: str = Field(..., description="错误消息")
    error_type: Optional[str] = Field(None, description="错误类型")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    request_id: Optional[str] = Field(None, description="请求ID")

class PageInfo(BaseSchema):
    """分页信息"""
    page: int = Field(1, ge=1, description="当前页码")
    size: int = Field(10, ge=1, le=100, description="每页数量")
    total: int = Field(0, ge=0, description="总记录数")
    pages: int = Field(0, ge=0, description="总页数")
    has_next: bool = Field(False, description="是否有下一页")
    has_prev: bool = Field(False, description="是否有上一页")
    
    @classmethod
    def create(cls, page: int, size: int, total: int) -> "PageInfo":
        """创建分页信息"""
        pages = (total + size - 1) // size if total > 0 else 0
        return cls(
            page=page,
            size=size,
            total=total,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )
    
class PageResponse(BaseSchema, Generic[T]):
    """分页响应"""
    success: bool = Field(True, description="操作是否成功")
    code: int = Field(200, description="HTTP状态码")
    message: str = Field("操作成功", description="响应消息")
    data: List[T] = Field(default_factory=list, description="响应数据")
    page_info: PageInfo = Field(..., description="分页信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    request_id: Optional[str] = Field(None, description="请求ID")

class HealthResponse(BaseSchema):
    """健康检查响应"""
    status: str = Field("ok", description="服务状态")
    version: str = Field("1.1.0", description="服务版本")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    uptime: Optional[float] = Field(None, description="运行时间(秒)")
    
class IdResponse(BaseSchema):
    """ID响应模型"""
    id: str = Field(..., description="资源ID")
    
class MessageResponse(BaseSchema):
    """消息响应模型"""
    message: str = Field(..., description="消息内容")

# 常用的响应类型别名
SuccessResponse = ApiResponse[None]
StringResponse = ApiResponse[str]
IntResponse = ApiResponse[int]
BoolResponse = ApiResponse[bool]
DictResponse = ApiResponse[Dict[str, Any]]
ListResponse = ApiResponse[List[Any]] 