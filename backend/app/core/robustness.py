"""
健壮性工具模块

提供重试机制、断路器模式、资源管理等通用健壮性组件。
"""
import asyncio
import time
import re
import functools
from typing import Any, Callable, Dict, List, Optional, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum

from .logging import get_logger, structured_logger
from .errors import ValidationException, ServiceException

logger = get_logger(__name__)

class CircuitBreakerState(Enum):
    """断路器状态"""
    CLOSED = "CLOSED"      # 正常状态
    OPEN = "OPEN"          # 断开状态
    HALF_OPEN = "HALF_OPEN"  # 半开状态

@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

class CircuitBreaker:
    """断路器模式实现"""
    
    def __init__(self, 
                 failure_threshold: int = 5, 
                 timeout: int = 60,
                 success_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        self.name = None
    
    def set_name(self, name: str):
        """设置断路器名称"""
        self.name = name
        return self
    
    async def call(self, func: Callable, *args, **kwargs):
        """通过断路器调用函数"""
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info(f"断路器 {self.name} 进入半开状态")
            else:
                raise ServiceException(f"服务 {self.name} 暂时不可用（断路器开启）")
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # 成功调用处理
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    logger.info(f"断路器 {self.name} 恢复正常状态")
            elif self.state == CircuitBreakerState.CLOSED:
                self.failure_count = 0  # 重置失败计数
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"断路器 {self.name} 重新开启")
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"断路器 {self.name} 开启，失败次数: {self.failure_count}")
            
            raise

class RetryManager:
    """重试管理器"""
    
    @staticmethod
    async def retry_async(func: Callable, 
                         config: RetryConfig = None,
                         exceptions: tuple = (Exception,),
                         on_retry: Optional[Callable] = None) -> Any:
        """异步重试装饰器"""
        if config is None:
            config = RetryConfig()
        
        last_exception = None
        
        for attempt in range(config.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func()
                else:
                    return func()
                    
            except exceptions as e:
                last_exception = e
                
                if attempt == config.max_attempts - 1:
                    # 最后一次尝试失败
                    logger.error(f"重试最终失败，尝试次数: {config.max_attempts}, 错误: {str(e)}")
                    raise
                
                # 计算延迟时间
                delay = min(
                    config.base_delay * (config.exponential_base ** attempt),
                    config.max_delay
                )
                
                # 添加抖动
                if config.jitter:
                    import random
                    delay *= (0.5 + random.random() * 0.5)
                
                logger.warning(f"重试第 {attempt + 1} 次失败: {str(e)}, {delay:.2f}秒后重试")
                
                if on_retry:
                    await on_retry(attempt, e, delay)
                
                await asyncio.sleep(delay)
        
        raise last_exception

def retry_on_failure(config: RetryConfig = None, 
                    exceptions: tuple = (Exception,),
                    on_retry: Optional[Callable] = None):
    """重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            async def retry_func():
                return await func(*args, **kwargs)
            
            return await RetryManager.retry_async(
                retry_func, config, exceptions, on_retry
            )
        return wrapper
    return decorator

class ResourceManager:
    """资源管理器"""
    
    def __init__(self):
        self.active_resources: Dict[str, Any] = {}
        self.resource_locks: Dict[str, asyncio.Lock] = {}
        self.cleanup_callbacks: Dict[str, List[Callable]] = {}
    
    @asynccontextmanager
    async def manage_resource(self, 
                             resource_id: str, 
                             resource_factory: Callable,
                             cleanup_func: Optional[Callable] = None):
        """资源管理上下文"""
        if resource_id not in self.resource_locks:
            self.resource_locks[resource_id] = asyncio.Lock()
        
        async with self.resource_locks[resource_id]:
            resource = None
            try:
                # 创建或获取资源
                if resource_id in self.active_resources:
                    resource = self.active_resources[resource_id]
                    logger.debug(f"复用资源: {resource_id}")
                else:
                    if asyncio.iscoroutinefunction(resource_factory):
                        resource = await resource_factory()
                    else:
                        resource = resource_factory()
                    self.active_resources[resource_id] = resource
                    logger.debug(f"创建资源: {resource_id}")
                
                yield resource
                
            except Exception as e:
                logger.error(f"资源管理错误: {resource_id}, 错误: {str(e)}")
                raise
            finally:
                # 清理资源
                await self._cleanup_resource(resource_id, resource, cleanup_func)
    
    async def _cleanup_resource(self, 
                               resource_id: str, 
                               resource: Any, 
                               cleanup_func: Optional[Callable]):
        """清理资源"""
        try:
            # 执行自定义清理函数
            if cleanup_func:
                if asyncio.iscoroutinefunction(cleanup_func):
                    await cleanup_func(resource)
                else:
                    cleanup_func(resource)
            
            # 执行注册的清理回调
            if resource_id in self.cleanup_callbacks:
                for callback in self.cleanup_callbacks[resource_id]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(resource)
                        else:
                            callback(resource)
                    except Exception as e:
                        logger.error(f"清理回调失败: {str(e)}")
            
            # 如果资源有cleanup方法，调用它
            if hasattr(resource, 'cleanup'):
                if asyncio.iscoroutinefunction(resource.cleanup):
                    await resource.cleanup()
                else:
                    resource.cleanup()
            
            # 从活跃资源中移除
            self.active_resources.pop(resource_id, None)
            logger.debug(f"资源清理完成: {resource_id}")
            
        except Exception as e:
            logger.error(f"资源清理失败: {resource_id}, 错误: {str(e)}")
    
    def register_cleanup_callback(self, resource_id: str, callback: Callable):
        """注册清理回调"""
        if resource_id not in self.cleanup_callbacks:
            self.cleanup_callbacks[resource_id] = []
        self.cleanup_callbacks[resource_id].append(callback)
    
    async def cleanup_all(self):
        """清理所有资源"""
        for resource_id in list(self.active_resources.keys()):
            resource = self.active_resources.get(resource_id)
            if resource:
                await self._cleanup_resource(resource_id, resource, None)

class RobustValidator:
    """健壮的验证器"""
    
    @staticmethod
    def validate_with_sanitization(value: Any, 
                                 validator_func: Callable, 
                                 sanitizer_func: Optional[Callable] = None) -> Any:
        """带清理的验证"""
        try:
            # 先清理输入
            if sanitizer_func:
                value = sanitizer_func(value)
            
            # 再验证
            if not validator_func(value):
                raise ValidationException(f"验证失败: {value}")
            
            return value
        except Exception as e:
            logger.error(f"输入验证错误: {str(e)}")
            raise ValidationException(f"输入验证失败: {str(e)}")
    
    @staticmethod
    def validate_string(value: str, 
                       min_length: int = 0, 
                       max_length: int = None,
                       pattern: str = None,
                       allow_empty: bool = False) -> str:
        """字符串验证"""
        if not isinstance(value, str):
            raise ValidationException("值必须是字符串")
        
        if not allow_empty and not value.strip():
            raise ValidationException("字符串不能为空")
        
        if len(value) < min_length:
            raise ValidationException(f"字符串长度不能少于 {min_length} 个字符")
        
        if max_length and len(value) > max_length:
            raise ValidationException(f"字符串长度不能超过 {max_length} 个字符")
        
        if pattern and not re.match(pattern, value):
            raise ValidationException(f"字符串格式不符合要求: {pattern}")
        
        return value
    
    @staticmethod
    def validate_file_upload(file_data: bytes, 
                           filename: str, 
                           max_size: int = None,
                           allowed_extensions: List[str] = None) -> tuple:
        """文件上传验证"""
        # 文件大小检查
        if max_size and len(file_data) > max_size:
            raise ValidationException(f"文件大小超过限制: {len(file_data)} > {max_size}")
        
        # 文件名安全检查
        if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
            raise ValidationException("文件名包含非法字符")
        
        # 文件类型检查
        if allowed_extensions:
            if not any(filename.lower().endswith(ext.lower()) for ext in allowed_extensions):
                raise ValidationException(f"不支持的文件类型，允许的类型: {', '.join(allowed_extensions)}")
        
        # 基础恶意文件检测
        dangerous_patterns = [
            b'<script',
            b'javascript:',
            b'<?php',
            b'<%',
            b'#!/bin/',
            b'#!/usr/bin/'
        ]
        
        file_data_lower = file_data.lower()
        for pattern in dangerous_patterns:
            if pattern in file_data_lower:
                raise ValidationException("文件内容可能包含恶意代码")
        
        return file_data, filename
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """HTML清理"""
        # 移除潜在的HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 移除JavaScript
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        # 移除事件处理器
        text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
        return text
    
    @staticmethod
    def sanitize_sql(text: str) -> str:
        """SQL注入清理"""
        # 移除常见的SQL注入模式
        dangerous_patterns = [
            r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
            r'(--|#|/\*|\*/)',
            r'(\bOR\b.*=.*\bOR\b)',
            r'(\bAND\b.*=.*\bAND\b)',
            r'(\'.*\')',
            r'(;.*)',
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text

class TimeoutManager:
    """超时管理器"""
    
    @staticmethod
    @asynccontextmanager
    async def timeout(seconds: float, operation_name: str = "操作"):
        """超时上下文管理器"""
        try:
            async with asyncio.timeout(seconds):
                yield
        except asyncio.TimeoutError:
            logger.warning(f"{operation_name} 超时: {seconds}秒")
            raise ServiceException(f"{operation_name} 超时")

class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
    
    def register_check(self, name: str, check_func: Callable):
        """注册健康检查"""
        self.checks[name] = check_func
    
    async def check_health(self) -> Dict[str, Any]:
        """执行健康检查"""
        results = {}
        overall_healthy = True
        
        for name, check_func in self.checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                results[name] = {
                    "status": "healthy",
                    "details": result
                }
            except Exception as e:
                results[name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                overall_healthy = False
        
        return {
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "checks": results,
            "timestamp": time.time()
        }

# 全局实例
resource_manager = ResourceManager()
health_checker = HealthChecker()

# 预定义的断路器
llm_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=30).set_name("LLM服务")
mcp_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60).set_name("MCP服务")
knowledge_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=45).set_name("知识库服务")

# 预定义的重试配置
default_retry_config = RetryConfig(max_attempts=3, base_delay=1.0)
file_upload_retry_config = RetryConfig(max_attempts=2, base_delay=2.0, max_delay=10.0)
api_call_retry_config = RetryConfig(max_attempts=3, base_delay=0.5, max_delay=5.0) 