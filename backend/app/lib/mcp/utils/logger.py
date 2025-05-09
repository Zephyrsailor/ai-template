"""MCP模块的日志记录工具"""

import logging
import sys
from typing import Any, Dict, Optional, Union


class Logger:
    """
    简单的日志记录器，支持格式化输出和不同级别的日志。
    """
    
    def __init__(
        self, 
        name: str, 
        level: Union[int, str] = logging.INFO,
        log_to_stderr: bool = True
    ):
        """
        初始化日志记录器
        
        Args:
            name: 日志记录器名称
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_stderr: 是否输出到标准错误
        """
        self.logger = logging.getLogger(f"mcp.{name}")
        
        # 设置日志级别
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        self.logger.setLevel(level)
        
        # 如果没有处理器，添加一个处理器
        if not self.logger.handlers and log_to_stderr:
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def debug(self, message: str, data: Any = None) -> None:
        """
        记录调试级别的日志
        
        Args:
            message: 日志消息
            data: 附加数据
        """
        self._log(logging.DEBUG, message, data)
    
    def info(self, message: str, data: Any = None) -> None:
        """
        记录信息级别的日志
        
        Args:
            message: 日志消息
            data: 附加数据
        """
        self._log(logging.INFO, message, data)
    
    def warning(self, message: str, data: Any = None) -> None:
        """
        记录警告级别的日志
        
        Args:
            message: 日志消息
            data: 附加数据
        """
        self._log(logging.WARNING, message, data)
    
    def error(self, message: str, data: Any = None) -> None:
        """
        记录错误级别的日志
        
        Args:
            message: 日志消息
            data: 附加数据
        """
        self._log(logging.ERROR, message, data)
    
    def critical(self, message: str, data: Any = None) -> None:
        """
        记录关键错误级别的日志
        
        Args:
            message: 日志消息
            data: 附加数据
        """
        self._log(logging.CRITICAL, message, data)
    
    def _log(self, level: int, message: str, data: Any = None) -> None:
        """
        内部日志记录方法
        
        Args:
            level: 日志级别
            message: 日志消息
            data: 附加数据
        """
        if data is not None:
            if isinstance(data, dict):
                for k, v in data.items():
                    message = f"{message} | {k}={v}"
            else:
                message = f"{message} | data={data}"
        
        self.logger.log(level, message) 