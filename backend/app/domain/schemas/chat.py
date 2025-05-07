"""
聊天相关的数据验证模型
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    history: List[Dict[str, str]] = Field(
        default=[],
        description="消息历史记录，格式为[{'role': 'user', 'content': '...'}, ...]"
    )
    model_id: Optional[str] = Field(
        default=None,
        description="模型ID，用于覆盖默认模型"
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="系统提示词"
    )
    temperature: Optional[float] = Field(
        default=None,
        description="温度参数，控制随机性"
    )
    max_tokens: Optional[int] = Field(
        default=None, 
        description="最大生成token数"
    )
    knowledge_base_ids: List[str] = Field(
        default=[],
        description="要查询的知识库ID列表"
    )
    use_tools: bool = Field(
        default=False,
        description="是否启用工具"
    )
    tools_category: Optional[str] = Field(
        default=None,
        description="工具类别"
    )
    mcp_server_ids: List[str] = Field(
        default=[],
        description="要使用的MCP服务器ID列表"
    )

class ToolCallRequest(BaseModel):
    """工具调用请求"""
    tool_name: str = Field(..., description="工具名称")
    arguments: Dict[str, Union[str, int, float, bool, List, Dict]] = Field(
        default={},
        description="工具参数"
    )

class StreamEvent(BaseModel):
    """流式事件模型"""
    type: str = Field(..., description="事件类型，如content, tool_result, error等")
    data: Union[str, Dict, List] = Field(..., description="事件数据")

class ChatResponse(BaseModel):
    """聊天响应模型（用于非流式响应）"""
    message: str = Field(..., description="模型生成的消息")
    tool_calls: List[Dict[str, Union[str, Dict]]] = Field(
        default=[],
        description="工具调用列表"
    )
    references: List[Dict[str, str]] = Field(
        default=[],
        description="知识库引用列表"
    ) 