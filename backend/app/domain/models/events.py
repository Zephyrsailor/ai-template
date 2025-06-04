"""
事件模型定义
"""
from typing import Any, Optional
from pydantic import BaseModel
from ..constants import EventType

class ModelEvent(BaseModel):
    """模型事件"""
    type: str
    data: Any
    
    def __init__(self, event_type: str = None, event_data: Any = None, **kwargs):
        """初始化方法，支持位置参数"""
        if event_type is not None:
            kwargs['type'] = event_type
        if event_data is not None:
            kwargs['data'] = event_data
        super().__init__(**kwargs)
    
    class Config:
        """Pydantic配置"""
        arbitrary_types_allowed = True

class StreamEvent(BaseModel):
    """流事件"""
    type: str
    data: Any
    
    def __init__(self, event_type: str = None, event_data: Any = None, **kwargs):
        """初始化方法，支持位置参数"""
        if event_type is not None:
            kwargs['type'] = event_type
        if event_data is not None:
            kwargs['data'] = event_data
        super().__init__(**kwargs)
    
    class Config:
        """Pydantic配置"""
        arbitrary_types_allowed = True 