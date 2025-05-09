"""
事件模型 - 用于处理LLM生成的事件
"""
from enum import Enum
from typing import Any, Dict, Optional

class EventType(str, Enum):
    """事件类型枚举"""
    CONTENT = "content"      # 内容生成
    THINKING = "thinking"    # 思考/推理过程
    TOOL_CALL = "tool_call"  # 工具调用
    ERROR = "error"          # 错误事件
    END = "end"              # 结束标记

class ModelEvent:
    """LLM生成过程中产生的标准化事件"""
    def __init__(self, type: EventType, data: Any):
        self.type = type
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.type,
            "data": self.data
        } 