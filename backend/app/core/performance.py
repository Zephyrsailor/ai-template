"""
性能监控模块 - 提供API性能监控和优化功能
"""
import time
import psutil
import asyncio
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .logging import get_logger
from .constants import APIConstants

logger = get_logger(__name__)

@dataclass
class PerformanceMetrics:
    """性能指标"""
    request_count: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    error_count: int = 0
    active_requests: int = 0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def avg_response_time(self) -> float:
        """平均响应时间"""
        return self.total_response_time / self.request_count if self.request_count > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        """错误率"""
        return self.error_count / self.request_count if self.request_count > 0 else 0.0

@dataclass
class RequestMetrics:
    """单个请求的性能指标"""
    method: str
    path: str
    status_code: int
    response_time: float
    memory_before: float
    memory_after: float
    timestamp: datetime
    user_id: Optional[str] = None
    request_id: Optional[str] = None

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics_history: deque = deque(maxlen=max_history)
        self.endpoint_metrics: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
        self.request_history: deque = deque(maxlen=max_history)
        self.alerts: List[Dict[str, Any]] = []
        self.thresholds = {
            'response_time': 2.0,  # 2秒
            'error_rate': 0.05,    # 5%
            'memory_usage': 0.8,   # 80%
            'cpu_usage': 0.8       # 80%
        }
    
    def record_request(self, request_metrics: RequestMetrics) -> None:
        """记录请求指标"""
        self.request_history.append(request_metrics)
        
        # 更新端点指标
        endpoint_key = f"{request_metrics.method} {request_metrics.path}"
        endpoint_metric = self.endpoint_metrics[endpoint_key]
        
        endpoint_metric.request_count += 1
        endpoint_metric.total_response_time += request_metrics.response_time
        endpoint_metric.min_response_time = min(
            endpoint_metric.min_response_time, 
            request_metrics.response_time
        )
        endpoint_metric.max_response_time = max(
            endpoint_metric.max_response_time, 
            request_metrics.response_time
        )
        
        if request_metrics.status_code >= 400:
            endpoint_metric.error_count += 1
        
        # 检查性能阈值
        self._check_thresholds(endpoint_key, endpoint_metric, request_metrics)
    
    def _check_thresholds(
        self, 
        endpoint_key: str, 
        endpoint_metric: PerformanceMetrics,
        request_metrics: RequestMetrics
    ) -> None:
        """检查性能阈值并生成告警"""
        alerts = []
        
        # 响应时间告警
        if request_metrics.response_time > self.thresholds['response_time']:
            alerts.append({
                'type': 'high_response_time',
                'endpoint': endpoint_key,
                'value': request_metrics.response_time,
                'threshold': self.thresholds['response_time'],
                'timestamp': datetime.now()
            })
        
        # 错误率告警
        if endpoint_metric.error_rate > self.thresholds['error_rate']:
            alerts.append({
                'type': 'high_error_rate',
                'endpoint': endpoint_key,
                'value': endpoint_metric.error_rate,
                'threshold': self.thresholds['error_rate'],
                'timestamp': datetime.now()
            })
        
        # 内存使用告警
        memory_usage = psutil.virtual_memory().percent / 100
        if memory_usage > self.thresholds['memory_usage']:
            alerts.append({
                'type': 'high_memory_usage',
                'value': memory_usage,
                'threshold': self.thresholds['memory_usage'],
                'timestamp': datetime.now()
            })
        
        # CPU使用告警
        cpu_usage = psutil.cpu_percent() / 100
        if cpu_usage > self.thresholds['cpu_usage']:
            alerts.append({
                'type': 'high_cpu_usage',
                'value': cpu_usage,
                'threshold': self.thresholds['cpu_usage'],
                'timestamp': datetime.now()
            })
        
        # 记录告警
        for alert in alerts:
            self.alerts.append(alert)
            logger.warning(f"性能告警: {alert}")
    
    def get_overall_metrics(self, time_window: Optional[timedelta] = None) -> PerformanceMetrics:
        """获取整体性能指标"""
        if time_window:
            cutoff_time = datetime.now() - time_window
            requests = [
                req for req in self.request_history 
                if req.timestamp >= cutoff_time
            ]
        else:
            requests = list(self.request_history)
        
        if not requests:
            return PerformanceMetrics()
        
        metrics = PerformanceMetrics()
        metrics.request_count = len(requests)
        metrics.total_response_time = sum(req.response_time for req in requests)
        metrics.min_response_time = min(req.response_time for req in requests)
        metrics.max_response_time = max(req.response_time for req in requests)
        metrics.error_count = sum(1 for req in requests if req.status_code >= 400)
        metrics.memory_usage = psutil.virtual_memory().percent / 100
        metrics.cpu_usage = psutil.cpu_percent() / 100
        
        return metrics
    
    def get_endpoint_metrics(self, endpoint: Optional[str] = None) -> Dict[str, PerformanceMetrics]:
        """获取端点性能指标"""
        if endpoint:
            return {endpoint: self.endpoint_metrics.get(endpoint, PerformanceMetrics())}
        return dict(self.endpoint_metrics)
    
    def get_slow_requests(self, threshold: float = 1.0, limit: int = 10) -> List[RequestMetrics]:
        """获取慢请求列表"""
        slow_requests = [
            req for req in self.request_history 
            if req.response_time > threshold
        ]
        slow_requests.sort(key=lambda x: x.response_time, reverse=True)
        return slow_requests[:limit]
    
    def get_error_requests(self, limit: int = 10) -> List[RequestMetrics]:
        """获取错误请求列表"""
        error_requests = [
            req for req in self.request_history 
            if req.status_code >= 400
        ]
        error_requests.sort(key=lambda x: x.timestamp, reverse=True)
        return error_requests[:limit]
    
    def get_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的告警"""
        return sorted(self.alerts, key=lambda x: x['timestamp'], reverse=True)[:limit]
    
    def clear_history(self) -> None:
        """清空历史数据"""
        self.metrics_history.clear()
        self.request_history.clear()
        self.endpoint_metrics.clear()
        self.alerts.clear()

# 全局性能监控器实例
performance_monitor = PerformanceMonitor()

class PerformanceMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""
    
    def __init__(self, app, monitor: PerformanceMonitor = None):
        super().__init__(app)
        self.monitor = monitor or performance_monitor
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录性能指标"""
        start_time = time.time()
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # 增加活跃请求计数
        for metric in self.monitor.endpoint_metrics.values():
            metric.active_requests += 1
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算性能指标
            end_time = time.time()
            response_time = end_time - start_time
            memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            # 创建请求指标
            request_metrics = RequestMetrics(
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                response_time=response_time,
                memory_before=memory_before,
                memory_after=memory_after,
                timestamp=datetime.now(),
                user_id=getattr(request.state, 'user_id', None),
                request_id=getattr(request.state, 'request_id', None)
            )
            
            # 记录指标
            self.monitor.record_request(request_metrics)
            
            # 添加性能头部
            response.headers["X-Response-Time"] = f"{response_time:.3f}s"
            response.headers["X-Memory-Usage"] = f"{memory_after:.1f}MB"
            
            return response
            
        except Exception as e:
            # 记录错误请求
            end_time = time.time()
            response_time = end_time - start_time
            memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            request_metrics = RequestMetrics(
                method=request.method,
                path=str(request.url.path),
                status_code=500,
                response_time=response_time,
                memory_before=memory_before,
                memory_after=memory_after,
                timestamp=datetime.now(),
                user_id=getattr(request.state, 'user_id', None),
                request_id=getattr(request.state, 'request_id', None)
            )
            
            self.monitor.record_request(request_metrics)
            raise
            
        finally:
            # 减少活跃请求计数
            for metric in self.monitor.endpoint_metrics.values():
                metric.active_requests = max(0, metric.active_requests - 1)

class PerformanceProfiler:
    """性能分析器"""
    
    def __init__(self):
        self.profiles: Dict[str, List[float]] = defaultdict(list)
    
    @asynccontextmanager
    async def profile(self, operation_name: str):
        """性能分析上下文管理器"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        try:
            yield
        finally:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss
            
            duration = end_time - start_time
            memory_delta = (end_memory - start_memory) / 1024 / 1024  # MB
            
            self.profiles[operation_name].append(duration)
            
            logger.debug(
                f"性能分析 - {operation_name}: "
                f"耗时 {duration:.3f}s, 内存变化 {memory_delta:.1f}MB"
            )
    
    def get_profile_stats(self, operation_name: str) -> Dict[str, float]:
        """获取操作的性能统计"""
        durations = self.profiles.get(operation_name, [])
        if not durations:
            return {}
        
        return {
            'count': len(durations),
            'total': sum(durations),
            'avg': sum(durations) / len(durations),
            'min': min(durations),
            'max': max(durations),
            'p95': sorted(durations)[int(len(durations) * 0.95)] if durations else 0
        }
    
    def get_all_profiles(self) -> Dict[str, Dict[str, float]]:
        """获取所有操作的性能统计"""
        return {
            operation: self.get_profile_stats(operation)
            for operation in self.profiles.keys()
        }

# 全局性能分析器实例
performance_profiler = PerformanceProfiler()

def profile_operation(operation_name: str):
    """性能分析装饰器"""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with performance_profiler.profile(operation_name):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    performance_profiler.profiles[operation_name].append(duration)
                    return result
                except Exception:
                    duration = time.time() - start_time
                    performance_profiler.profiles[operation_name].append(duration)
                    raise
            return sync_wrapper
    return decorator

class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
    
    def analyze_bottlenecks(self) -> List[Dict[str, Any]]:
        """分析性能瓶颈"""
        bottlenecks = []
        
        # 分析慢端点
        for endpoint, metrics in self.monitor.endpoint_metrics.items():
            if metrics.avg_response_time > 1.0:  # 超过1秒
                bottlenecks.append({
                    'type': 'slow_endpoint',
                    'endpoint': endpoint,
                    'avg_response_time': metrics.avg_response_time,
                    'request_count': metrics.request_count,
                    'severity': 'high' if metrics.avg_response_time > 2.0 else 'medium'
                })
        
        # 分析高错误率端点
        for endpoint, metrics in self.monitor.endpoint_metrics.items():
            if metrics.error_rate > 0.05:  # 错误率超过5%
                bottlenecks.append({
                    'type': 'high_error_rate',
                    'endpoint': endpoint,
                    'error_rate': metrics.error_rate,
                    'error_count': metrics.error_count,
                    'severity': 'high' if metrics.error_rate > 0.1 else 'medium'
                })
        
        return sorted(bottlenecks, key=lambda x: x.get('severity', 'low'), reverse=True)
    
    def suggest_optimizations(self) -> List[Dict[str, Any]]:
        """建议性能优化方案"""
        suggestions = []
        bottlenecks = self.analyze_bottlenecks()
        
        for bottleneck in bottlenecks:
            if bottleneck['type'] == 'slow_endpoint':
                suggestions.append({
                    'type': 'caching',
                    'description': f"为端点 {bottleneck['endpoint']} 添加缓存",
                    'priority': 'high' if bottleneck['avg_response_time'] > 3.0 else 'medium'
                })
                
                suggestions.append({
                    'type': 'database_optimization',
                    'description': f"优化端点 {bottleneck['endpoint']} 的数据库查询",
                    'priority': 'high'
                })
            
            elif bottleneck['type'] == 'high_error_rate':
                suggestions.append({
                    'type': 'error_handling',
                    'description': f"改进端点 {bottleneck['endpoint']} 的错误处理",
                    'priority': 'high'
                })
        
        # 系统级建议
        overall_metrics = self.monitor.get_overall_metrics()
        if overall_metrics.memory_usage > 0.8:
            suggestions.append({
                'type': 'memory_optimization',
                'description': "系统内存使用率过高，建议优化内存使用",
                'priority': 'high'
            })
        
        if overall_metrics.cpu_usage > 0.8:
            suggestions.append({
                'type': 'cpu_optimization',
                'description': "系统CPU使用率过高，建议优化计算密集型操作",
                'priority': 'high'
            })
        
        return suggestions

def get_performance_report() -> Dict[str, Any]:
    """获取性能报告"""
    overall_metrics = performance_monitor.get_overall_metrics()
    endpoint_metrics = performance_monitor.get_endpoint_metrics()
    slow_requests = performance_monitor.get_slow_requests()
    error_requests = performance_monitor.get_error_requests()
    alerts = performance_monitor.get_alerts()
    
    optimizer = PerformanceOptimizer(performance_monitor)
    bottlenecks = optimizer.analyze_bottlenecks()
    suggestions = optimizer.suggest_optimizations()
    
    return {
        'overall_metrics': {
            'request_count': overall_metrics.request_count,
            'avg_response_time': overall_metrics.avg_response_time,
            'error_rate': overall_metrics.error_rate,
            'memory_usage': overall_metrics.memory_usage,
            'cpu_usage': overall_metrics.cpu_usage
        },
        'endpoint_metrics': {
            endpoint: {
                'request_count': metrics.request_count,
                'avg_response_time': metrics.avg_response_time,
                'error_rate': metrics.error_rate,
                'min_response_time': metrics.min_response_time,
                'max_response_time': metrics.max_response_time
            }
            for endpoint, metrics in endpoint_metrics.items()
        },
        'slow_requests': [
            {
                'method': req.method,
                'path': req.path,
                'response_time': req.response_time,
                'timestamp': req.timestamp.isoformat()
            }
            for req in slow_requests
        ],
        'error_requests': [
            {
                'method': req.method,
                'path': req.path,
                'status_code': req.status_code,
                'timestamp': req.timestamp.isoformat()
            }
            for req in error_requests
        ],
        'alerts': alerts,
        'bottlenecks': bottlenecks,
        'optimization_suggestions': suggestions,
        'profile_stats': performance_profiler.get_all_profiles()
    } 