"""
日志配置
"""
from typing import Dict, Any
from pydantic import BaseModel, Field

class LoggingConfig(BaseModel):
    """日志配置"""
    
    # 基础配置
    level: str = Field(default="INFO", description="日志级别")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    
    # 文件配置
    file_enabled: bool = Field(default=True, description="是否启用文件日志")
    file_path: str = Field(default="logs/app.log", description="日志文件路径")
    file_max_size: int = Field(default=10485760, description="日志文件最大大小（字节）")
    file_backup_count: int = Field(default=5, description="日志文件备份数量")
    
    # 控制台配置
    console_enabled: bool = Field(default=True, description="是否启用控制台日志")
    console_level: str = Field(default="INFO", description="控制台日志级别")
    
    # 结构化日志配置
    structured_enabled: bool = Field(default=False, description="是否启用结构化日志")
    structured_format: str = Field(default="json", description="结构化日志格式")
    
    # 性能日志配置
    performance_enabled: bool = Field(default=True, description="是否启用性能日志")
    performance_threshold: float = Field(default=1.0, description="性能日志阈值（秒）")
    
    # 错误日志配置
    error_file_enabled: bool = Field(default=True, description="是否启用错误日志文件")
    error_file_path: str = Field(default="logs/error.log", description="错误日志文件路径")
    
    # 访问日志配置
    access_enabled: bool = Field(default=True, description="是否启用访问日志")
    access_file_path: str = Field(default="logs/access.log", description="访问日志文件路径")
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取logging配置字典"""
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": self.format,
                },
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s",
                },
            },
            "handlers": {},
            "loggers": {
                "": {  # root logger
                    "level": self.level,
                    "handlers": [],
                },
                "uvicorn": {
                    "level": "INFO",
                    "handlers": [],
                    "propagate": False,
                },
                "uvicorn.access": {
                    "level": "INFO",
                    "handlers": [],
                    "propagate": False,
                },
            },
        }
        
        # 添加控制台处理器
        if self.console_enabled:
            config["handlers"]["console"] = {
                "class": "logging.StreamHandler",
                "level": self.console_level,
                "formatter": "default",
                "stream": "ext://sys.stdout",
            }
            config["loggers"][""]["handlers"].append("console")
            config["loggers"]["uvicorn"]["handlers"].append("console")
        
        # 添加文件处理器
        if self.file_enabled:
            config["handlers"]["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": self.level,
                "formatter": "detailed",
                "filename": self.file_path,
                "maxBytes": self.file_max_size,
                "backupCount": self.file_backup_count,
                "encoding": "utf-8",
            }
            config["loggers"][""]["handlers"].append("file")
        
        # 添加错误文件处理器
        if self.error_file_enabled:
            config["handlers"]["error_file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": self.error_file_path,
                "maxBytes": self.file_max_size,
                "backupCount": self.file_backup_count,
                "encoding": "utf-8",
            }
            config["loggers"][""]["handlers"].append("error_file")
        
        # 添加访问日志处理器
        if self.access_enabled:
            config["handlers"]["access_file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "default",
                "filename": self.access_file_path,
                "maxBytes": self.file_max_size,
                "backupCount": self.file_backup_count,
                "encoding": "utf-8",
            }
            config["loggers"]["uvicorn.access"]["handlers"].append("access_file")
        
        return config
    
    class Config:
        """Pydantic配置"""
        env_prefix = "LOG_" 