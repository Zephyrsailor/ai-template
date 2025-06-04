"""
改进的日志管理系统

提供统一的日志配置、结构化日志、敏感信息脱敏等功能。
"""
import logging
import logging.config
import sys
import json
import re
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
from contextlib import contextmanager

from .config import get_settings
from .constants import LoggingConstants

settings = get_settings()


class SensitiveDataFilter(logging.Filter):
    """敏感信息过滤器"""
    
    SENSITIVE_PATTERNS = [
        (re.compile(r'password["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', re.IGNORECASE), 'password'),
        (re.compile(r'token["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', re.IGNORECASE), 'token'),
        (re.compile(r'api_key["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', re.IGNORECASE), 'api_key'),
        (re.compile(r'secret["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', re.IGNORECASE), 'secret'),
        (re.compile(r'authorization:\s*bearer\s+([^\s]+)', re.IGNORECASE), 'auth_token'),
        (re.compile(r'(\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})', re.IGNORECASE), 'card_number'),
    ]
    
    def filter(self, record):
        """过滤敏感信息"""
        if hasattr(record, 'msg'):
            record.msg = self._mask_sensitive_data(str(record.msg))
        
        if hasattr(record, 'args') and record.args:
            record.args = tuple(
                self._mask_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        
        return True
    
    def _mask_sensitive_data(self, text: str) -> str:
        """脱敏敏感数据"""
        for pattern, field_type in self.SENSITIVE_PATTERNS:
            text = pattern.sub(lambda m: f'{field_type}=***masked***', text)
        return text


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def format(self, record):
        """格式化日志记录"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # 添加额外的结构化数据
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # 添加请求上下文（如果存在）
        for attr in ['request_id', 'user_id', 'session_id', 'trace_id']:
            if hasattr(record, attr):
                log_entry[attr] = getattr(record, attr)
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)


def get_logging_config() -> Dict[str, Any]:
    """获取日志配置"""
    log_level = settings.LOG_LEVEL.upper()
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "structured": {
                "()": StructuredFormatter,
            },
        },
        "filters": {
            "sensitive_filter": {
                "()": SensitiveDataFilter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "default",
                "stream": sys.stdout,
                "filters": ["sensitive_filter"],
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": log_dir / "app.log",
                "maxBytes": LoggingConstants.MAX_LOG_FILE_SIZE,
                "backupCount": LoggingConstants.LOG_BACKUP_COUNT,
                "encoding": "utf-8",
                "filters": ["sensitive_filter"],
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": log_dir / "error.log",
                "maxBytes": LoggingConstants.MAX_LOG_FILE_SIZE,
                "backupCount": LoggingConstants.LOG_BACKUP_COUNT,
                "encoding": "utf-8",
                "filters": ["sensitive_filter"],
            },
            "structured_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "structured",
                "filename": log_dir / "structured.log",
                "maxBytes": LoggingConstants.MAX_LOG_FILE_SIZE,
                "backupCount": LoggingConstants.LOG_BACKUP_COUNT,
                "encoding": "utf-8",
                "filters": ["sensitive_filter"],
            },
            "performance_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "structured",
                "filename": log_dir / "performance.log",
                "maxBytes": LoggingConstants.MAX_LOG_FILE_SIZE,
                "backupCount": LoggingConstants.LOG_BACKUP_COUNT,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "app": {
                "level": log_level,
                "handlers": ["console", "file", "error_file", "structured_file"],
                "propagate": False,
            },
            "app.performance": {
                "level": "INFO",
                "handlers": ["performance_file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console", "error_file"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
    }
    
    # 生产环境配置调整
    if settings.ENVIRONMENT == "production":
        config["handlers"]["console"]["formatter"] = "structured"
        config["loggers"]["uvicorn.access"]["level"] = "WARNING"
        config["loggers"]["sqlalchemy.engine"]["level"] = "ERROR"
    
    return config


def setup_logging() -> None:
    """设置日志配置"""
    config = get_logging_config()
    logging.config.dictConfig(config)
    
    # 禁用第三方库的调试日志以避免格式化错误
    logging.getLogger("pdfminer").setLevel(logging.WARNING)
    logging.getLogger("pdfminer.pdfparser").setLevel(logging.WARNING)
    logging.getLogger("pdfminer.pdfdocument").setLevel(logging.WARNING)
    logging.getLogger("pdfminer.psparser").setLevel(logging.WARNING)
    logging.getLogger("unstructured").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # 获取应用logger
    logger = logging.getLogger("app")
    logger.info(f"日志系统初始化完成 - 环境: {settings.ENVIRONMENT}, 级别: {settings.LOG_LEVEL}")


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的logger"""
    return logging.getLogger(f"app.{name}")


# 便捷的logger获取函数
def get_api_logger() -> logging.Logger:
    """获取API层logger"""
    return get_logger("api")


def get_service_logger() -> logging.Logger:
    """获取服务层logger"""
    return get_logger("service")


def get_repository_logger() -> logging.Logger:
    """获取仓库层logger"""
    return get_logger("repository")


def get_lib_logger() -> logging.Logger:
    """获取库层logger"""
    return get_logger("lib")


def get_performance_logger() -> logging.Logger:
    """获取性能监控logger"""
    return logging.getLogger("app.performance")


class LoggerMixin:
    """Logger Mixin类，为其他类提供日志功能"""
    
    @property
    def logger(self) -> logging.Logger:
        """获取当前类的logger"""
        class_name = self.__class__.__name__
        module_name = self.__class__.__module__.replace("app.", "")
        return get_logger(f"{module_name}.{class_name}")


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.logger = get_logger(name)
        self.performance_logger = get_performance_logger()
    
    def log_with_context(self, level: int, message: str, **context) -> None:
        """带上下文的日志记录"""
        extra_data = {
            'event_type': context.pop('event_type', 'general'),
            **context
        }
        self.logger.log(level, message, extra={'extra_data': extra_data})
    
    def info(self, message: str, **context) -> None:
        """记录信息日志"""
        self.log_with_context(logging.INFO, message, **context)
    
    def warning(self, message: str, **context) -> None:
        """记录警告日志"""
        self.log_with_context(logging.WARNING, message, **context)
    
    def error(self, message: str, **context) -> None:
        """记录错误日志"""
        self.log_with_context(logging.ERROR, message, **context)
    
    def debug(self, message: str, **context) -> None:
        """记录调试日志"""
        self.log_with_context(logging.DEBUG, message, **context)
    
    def log_request(self, method: str, path: str, user_id: str = None, **kwargs) -> None:
        """记录请求日志"""
        self.info(
            f"请求开始: {method} {path}",
            event_type="request_start",
            http_method=method,
            path=path,
            user_id=user_id,
            **kwargs
        )
    
    def log_response(self, status_code: int, duration: float, **kwargs) -> None:
        """记录响应日志"""
        level_map = {
            range(200, 300): logging.INFO,
            range(300, 400): logging.INFO,
            range(400, 500): logging.WARNING,
            range(500, 600): logging.ERROR,
        }
        
        level = logging.INFO
        for status_range, log_level in level_map.items():
            if status_code in status_range:
                level = log_level
                break
        
        self.log_with_context(
            level,
            f"请求完成: {status_code} - 耗时: {duration*1000:.1f}ms",
            event_type="request_end",
            status_code=status_code,
            duration_ms=duration * 1000,
            **kwargs
        )
    
    def log_database_operation(self, operation: str, table: str, duration: float = None, **kwargs) -> None:
        """记录数据库操作日志"""
        message = f"数据库操作: {operation} {table}"
        if duration:
            message += f" - 耗时: {duration*1000:.1f}ms"
        
        self.info(
            message,
            event_type="database_operation",
            operation=operation,
            table=table,
            duration_ms=duration * 1000 if duration else None,
            **kwargs
        )
    
    def log_external_api_call(self, service: str, endpoint: str, status_code: int = None, duration: float = None, **kwargs) -> None:
        """记录外部API调用日志"""
        message = f"外部API调用: {service} {endpoint}"
        if status_code:
            message += f" - 状态: {status_code}"
        if duration:
            message += f" - 耗时: {duration*1000:.1f}ms"
        
        level = logging.INFO
        if status_code and status_code >= 400:
            level = logging.WARNING if status_code < 500 else logging.ERROR
        
        self.log_with_context(
            level,
            message,
            event_type="external_api_call",
            service=service,
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=duration * 1000 if duration else None,
            **kwargs
        )
    
    def log_business_event(self, event: str, entity_type: str = None, entity_id: str = None, **kwargs) -> None:
        """记录业务事件日志"""
        message = f"业务事件: {event}"
        if entity_type and entity_id:
            message += f" - {entity_type}:{entity_id}"
        
        self.info(
            message,
            event_type="business_event",
            business_event=event,
            entity_type=entity_type,
            entity_id=entity_id,
            **kwargs
        )
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = None, **kwargs) -> None:
        """记录性能指标"""
        message = f"性能指标: {metric_name} = {value}"
        if unit:
            message += f" {unit}"
        
        self.performance_logger.info(
            message,
            extra={
                'extra_data': {
                    'event_type': 'performance_metric',
                    'metric_name': metric_name,
                    'value': value,
                    'unit': unit,
                    **kwargs
                }
            }
        )
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None, **kwargs) -> None:
        """记录错误日志"""
        error_context = {
            'event_type': 'error',
            'error_type': type(error).__name__,
            'error_message': str(error),
            **(context or {}),
            **kwargs
        }
        
        self.logger.error(
            f"错误发生: {type(error).__name__}: {str(error)}",
            exc_info=True,
            extra={'extra_data': error_context}
        )


@contextmanager
def log_operation(logger: StructuredLogger, operation: str, **context):
    """操作日志上下文管理器"""
    start_time = datetime.now()
    logger.info(f"开始操作: {operation}", event_type="operation_start", operation=operation, **context)
    
    try:
        yield
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"操作完成: {operation} - 耗时: {duration*1000:.1f}ms",
            event_type="operation_end",
            operation=operation,
            duration_ms=duration * 1000,
            status="success",
            **context
        )
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(
            f"操作失败: {operation} - 耗时: {duration*1000:.1f}ms - 错误: {str(e)}",
            event_type="operation_end",
            operation=operation,
            duration_ms=duration * 1000,
            status="error",
            error_type=type(e).__name__,
            error_message=str(e),
            **context
        )
        raise


# 全局结构化日志记录器实例
structured_logger = StructuredLogger("main")
api_logger = StructuredLogger("api")
service_logger = StructuredLogger("service")
repository_logger = StructuredLogger("repository")


def mask_sensitive_data(data: Union[str, dict], fields: list = None) -> Union[str, dict]:
    """脱敏敏感数据的工具函数"""
    if fields is None:
        fields = ['password', 'token', 'api_key', 'secret', 'authorization']
    
    if isinstance(data, str):
        for field in fields:
            pattern = re.compile(f'{field}["\']?\\s*[:=]\\s*["\']?([^"\'}}\\s,]+)', re.IGNORECASE)
            data = pattern.sub(f'{field}=***masked***', data)
        return data
    
    elif isinstance(data, dict):
        masked_data = {}
        for key, value in data.items():
            if key.lower() in [f.lower() for f in fields]:
                masked_data[key] = '***masked***'
            elif isinstance(value, (dict, str)):
                masked_data[key] = mask_sensitive_data(value, fields)
            else:
                masked_data[key] = value
        return masked_data
    
    return data 