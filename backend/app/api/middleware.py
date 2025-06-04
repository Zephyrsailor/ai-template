"""
API中间件模块

提供请求日志、性能监控、错误处理等中间件功能。
"""
import time
import uuid
from typing import Callable, Dict, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.logging import StructuredLogger, get_api_logger
from ..core.constants import APIConstants

logger = get_api_logger()
structured_logger = StructuredLogger("api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录日志"""
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 获取用户信息（如果有）
        user_id = getattr(request.state, "user_id", None)
        
        # 记录请求日志
        structured_logger.log_request(
            method=request.method,
            path=str(request.url.path),
            user_id=user_id,
            request_id=request_id,
            query_params=dict(request.query_params),
            client_ip=request.client.host if request.client else None,
        )
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            duration = time.time() - start_time
            
            # 记录响应日志
            structured_logger.log_response(
                status_code=response.status_code,
                duration=duration,
                request_id=request_id,
                user_id=user_id,
            )
            
            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(duration)
            
            return response
            
        except Exception as e:
            # 计算处理时间
            duration = time.time() - start_time
            
            # 记录错误日志
            structured_logger.log_error(
                error=e,
                context={
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "user_id": user_id,
                    "duration": duration,
                }
            )
            
            # 重新抛出异常
            raise


class CORSMiddleware(BaseHTTPMiddleware):
    """自定义CORS中间件"""
    
    def __init__(self, app, allow_origins=None, allow_methods=None, allow_headers=None):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理CORS"""
        if request.method == "OPTIONS":
            # 处理预检请求
            response = Response()
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
            response.headers["Access-Control-Max-Age"] = str(APIConstants.CORS_MAX_AGE)
            return response
        
        # 处理实际请求
        response = await call_next(request)
        
        # 添加CORS头
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """添加安全头"""
        response = await call_next(request)
        
        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简单的速率限制中间件"""
    
    def __init__(self, app, calls: int = APIConstants.DEFAULT_RATE_LIMIT_CALLS, period: int = APIConstants.DEFAULT_RATE_LIMIT_PERIOD):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients: Dict[str, deque] = defaultdict(deque)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """实现简单的速率限制"""
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # 清理过期记录
        self.clients = {
            ip: timestamps for ip, timestamps in self.clients.items()
            if any(t > current_time - self.period for t in timestamps)
        }
        
        # 检查当前客户端的请求次数
        if client_ip in self.clients:
            # 过滤出时间窗口内的请求
            recent_requests = [
                t for t in self.clients[client_ip]
                if t > current_time - self.period
            ]
            
            if len(recent_requests) >= self.calls:
                # 超过限制
                raise HTTPException(
                    status_code=APIConstants.HTTP_TOO_MANY_REQUESTS,
                    detail=f"请求过于频繁，请稍后再试"
                )
            
            # 添加当前请求时间
            self.clients[client_ip] = recent_requests + [current_time]
        else:
            # 新客户端
            self.clients[client_ip] = [current_time]
        
        return await call_next(request) 