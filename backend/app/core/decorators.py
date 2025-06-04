"""
通用装饰器 - 消除API路由中的重复代码
"""
import time
import functools
from typing import Any, Callable, Dict, List, Optional, Type, Union
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from .logging import get_api_logger
from .errors import (
    NotFoundException, ValidationException, AuthorizationException,
    ServiceException, BaseAppException
)
from .messages import get_message, MessageKeys
from ..api.utils import api_response, get_request_id

logger = get_api_logger()

def handle_exceptions(
    not_found_message: str = MessageKeys.RESOURCE_NOT_FOUND,
    forbidden_message: str = MessageKeys.FORBIDDEN,
    validation_message: str = MessageKeys.VALIDATION_ERROR,
    internal_error_message: str = MessageKeys.INTERNAL_ERROR
):
    """
    异常处理装饰器
    
    Args:
        not_found_message: 404错误消息键
        forbidden_message: 403错误消息键
        validation_message: 400错误消息键
        internal_error_message: 500错误消息键
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except NotFoundException as e:
                logger.warning(f"资源未找到: {str(e)}")
                return api_response(
                    code=404,
                    message=get_message(not_found_message, error=str(e))
                )
            except AuthorizationException as e:
                logger.warning(f"权限不足: {str(e)}")
                return api_response(
                    code=403,
                    message=get_message(forbidden_message, error=str(e))
                )
            except ValidationException as e:
                logger.warning(f"验证失败: {str(e)}")
                return api_response(
                    code=400,
                    message=get_message(validation_message, error=str(e))
                )
            except ServiceException as e:
                logger.error(f"服务错误: {str(e)}", exc_info=True)
                return api_response(
                    code=500,
                    message=get_message(internal_error_message, error=str(e))
                )
            except Exception as e:
                logger.error(f"未知错误: {str(e)}", exc_info=True)
                return api_response(
                    code=500,
                    message=get_message(internal_error_message, error="系统内部错误")
                )
        return wrapper
    return decorator

def log_api_call(
    operation: str,
    resource_type: str = "资源",
    log_request: bool = True,
    log_response: bool = False
):
    """
    API调用日志装饰器
    
    Args:
        operation: 操作名称
        resource_type: 资源类型
        log_request: 是否记录请求参数
        log_response: 是否记录响应数据
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # 提取请求信息
            request = None
            user_id = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                elif hasattr(arg, 'id'):  # 用户对象
                    user_id = arg.id
            
            request_id = get_request_id(request) if request else None
            
            # 记录请求开始
            log_data = {
                "operation": operation,
                "resource_type": resource_type,
                "user_id": user_id,
                "request_id": request_id,
                "start_time": start_time
            }
            
            if log_request:
                log_data["request_params"] = {
                    k: v for k, v in kwargs.items() 
                    if not k.startswith('_') and k not in ['current_user', 'request']
                }
            
            logger.info(f"开始{operation}{resource_type}", extra=log_data)
            
            try:
                # 执行函数
                result = await func(*args, **kwargs)
                
                # 记录成功
                duration = time.time() - start_time
                success_data = {
                    **log_data,
                    "duration": duration,
                    "status": "success"
                }
                
                if log_response and hasattr(result, 'data'):
                    success_data["response_data"] = result.data
                
                logger.info(f"完成{operation}{resource_type}", extra=success_data)
                
                return result
                
            except Exception as e:
                # 记录错误
                duration = time.time() - start_time
                error_data = {
                    **log_data,
                    "duration": duration,
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__
                }
                
                logger.error(f"{operation}{resource_type}失败", extra=error_data)
                raise
                
        return wrapper
    return decorator

def validate_request(
    required_fields: Optional[List[str]] = None,
    optional_fields: Optional[List[str]] = None,
    field_validators: Optional[Dict[str, Callable]] = None
):
    """
    请求验证装饰器
    
    Args:
        required_fields: 必需字段列表
        optional_fields: 可选字段列表
        field_validators: 字段验证器字典
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 查找请求数据
            request_data = None
            for arg in args:
                if hasattr(arg, 'dict'):  # Pydantic模型
                    request_data = arg.dict()
                    break
            
            if not request_data:
                # 从kwargs中查找
                for key, value in kwargs.items():
                    if hasattr(value, 'dict'):
                        request_data = value.dict()
                        break
            
            if request_data:
                # 验证必需字段
                if required_fields:
                    missing_fields = [
                        field for field in required_fields 
                        if field not in request_data or request_data[field] is None
                    ]
                    if missing_fields:
                        raise ValidationException(f"缺少必需字段: {', '.join(missing_fields)}")
                
                # 验证字段格式
                if field_validators:
                    for field, validator in field_validators.items():
                        if field in request_data and request_data[field] is not None:
                            try:
                                validator(request_data[field])
                            except Exception as e:
                                raise ValidationException(f"字段 {field} 验证失败: {str(e)}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def cache_response(
    ttl: int = 300,  # 缓存时间（秒）
    key_func: Optional[Callable] = None,  # 自定义缓存键函数
    condition: Optional[Callable] = None  # 缓存条件函数
):
    """
    响应缓存装饰器
    
    Args:
        ttl: 缓存生存时间（秒）
        key_func: 自定义缓存键生成函数
        condition: 缓存条件函数
    """
    def decorator(func: Callable) -> Callable:
        cache = {}  # 简单内存缓存，生产环境应使用Redis
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认缓存键生成
                key_parts = [func.__name__]
                for arg in args:
                    if isinstance(arg, (str, int, float)):
                        key_parts.append(str(arg))
                for k, v in kwargs.items():
                    if isinstance(v, (str, int, float)):
                        key_parts.append(f"{k}:{v}")
                cache_key = ":".join(key_parts)
            
            # 检查缓存
            if cache_key in cache:
                cached_data, cached_time = cache[cache_key]
                if time.time() - cached_time < ttl:
                    logger.debug(f"缓存命中: {cache_key}")
                    return cached_data
                else:
                    # 缓存过期，删除
                    del cache[cache_key]
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 检查是否应该缓存
            should_cache = True
            if condition:
                should_cache = condition(result, *args, **kwargs)
            
            # 缓存结果
            if should_cache:
                cache[cache_key] = (result, time.time())
                logger.debug(f"缓存存储: {cache_key}")
            
            return result
        return wrapper
    return decorator

def rate_limit(
    max_requests: int = 100,
    window_seconds: int = 60,
    key_func: Optional[Callable] = None
):
    """
    速率限制装饰器
    
    Args:
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口大小（秒）
        key_func: 自定义限制键函数
    """
    def decorator(func: Callable) -> Callable:
        request_counts = {}  # 简单内存存储，生产环境应使用Redis
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成限制键
            if key_func:
                limit_key = key_func(*args, **kwargs)
            else:
                # 默认使用用户ID或IP
                limit_key = "default"
                for arg in args:
                    if hasattr(arg, 'id'):  # 用户对象
                        limit_key = f"user:{arg.id}"
                        break
                    elif isinstance(arg, Request):  # 请求对象
                        limit_key = f"ip:{arg.client.host}"
                        break
            
            current_time = time.time()
            
            # 清理过期记录
            if limit_key in request_counts:
                request_counts[limit_key] = [
                    timestamp for timestamp in request_counts[limit_key]
                    if current_time - timestamp < window_seconds
                ]
            else:
                request_counts[limit_key] = []
            
            # 检查是否超过限制
            if len(request_counts[limit_key]) >= max_requests:
                logger.warning(f"速率限制触发: {limit_key}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"请求过于频繁，请在 {window_seconds} 秒后重试"
                )
            
            # 记录当前请求
            request_counts[limit_key].append(current_time)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_permissions(*permissions: str):
    """
    权限检查装饰器
    
    Args:
        permissions: 需要的权限列表
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 查找用户对象
            current_user = None
            for arg in args:
                if hasattr(arg, 'role'):  # 用户对象
                    current_user = arg
                    break
            
            if not current_user:
                # 从kwargs中查找
                current_user = kwargs.get('current_user')
            
            if not current_user:
                raise AuthorizationException("未找到用户信息")
            
            # 检查权限
            user_permissions = getattr(current_user, 'permissions', [])
            missing_permissions = [
                perm for perm in permissions 
                if perm not in user_permissions
            ]
            
            if missing_permissions:
                raise AuthorizationException(f"缺少权限: {', '.join(missing_permissions)}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def standardize_response(
    success_message: str = MessageKeys.SUCCESS,
    created_message: str = MessageKeys.CREATED,
    updated_message: str = MessageKeys.UPDATED,
    deleted_message: str = MessageKeys.DELETED
):
    """
    标准化响应装饰器
    
    Args:
        success_message: 成功消息键
        created_message: 创建成功消息键
        updated_message: 更新成功消息键
        deleted_message: 删除成功消息键
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # 如果已经是标准响应格式，直接返回
            if hasattr(result, 'success') and hasattr(result, 'code'):
                return result
            
            # 根据HTTP方法确定消息
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request:
                method = request.method.upper()
                if method == 'POST':
                    message = get_message(created_message)
                elif method == 'PUT' or method == 'PATCH':
                    message = get_message(updated_message)
                elif method == 'DELETE':
                    message = get_message(deleted_message)
                else:
                    message = get_message(success_message)
            else:
                message = get_message(success_message)
            
            # 标准化响应
            return api_response(data=result, message=message)
        return wrapper
    return decorator

# 组合装饰器
def api_endpoint(
    operation: str,
    resource_type: str = "资源",
    handle_errors: bool = True,
    log_calls: bool = True,
    standardize: bool = True,
    **decorator_kwargs
):
    """
    API端点组合装饰器
    
    Args:
        operation: 操作名称
        resource_type: 资源类型
        handle_errors: 是否处理异常
        log_calls: 是否记录日志
        standardize: 是否标准化响应
        **decorator_kwargs: 其他装饰器参数
    """
    def decorator(func: Callable) -> Callable:
        # 应用装饰器（注意顺序）
        decorated_func = func
        
        if standardize:
            decorated_func = standardize_response()(decorated_func)
        
        if handle_errors:
            decorated_func = handle_exceptions()(decorated_func)
        
        if log_calls:
            decorated_func = log_api_call(operation, resource_type)(decorated_func)
        
        return decorated_func
    return decorator 