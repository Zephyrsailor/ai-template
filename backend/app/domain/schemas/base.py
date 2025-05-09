"""
基础数据模型 - 提供通用的数据验证模型
"""
from typing import TypeVar, Generic, Optional, Any, Dict, List, Union
from pydantic import BaseModel, Field

# 泛型类型T，用于数据响应
T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """标准API响应模型"""
    code: int = Field(200, description="状态码，200表示成功，其他表示错误")
    message: str = Field("操作成功", description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")

class PageInfo(BaseModel):
    """分页信息"""
    page: int = Field(1, description="当前页码")
    size: int = Field(10, description="每页数量")
    total: int = Field(0, description="总记录数")
    
class PageResponse(BaseModel, Generic[T]):
    """分页响应"""
    code: int = Field(200, description="状态码，200表示成功，其他表示错误")
    message: str = Field("操作成功", description="响应消息")
    data: Optional[List[T]] = Field(None, description="响应数据")
    page_info: PageInfo = Field(..., description="分页信息") 