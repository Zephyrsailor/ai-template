"""
聊天相关的数据模型
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    conversation_id: Optional[str] = Field(default=None, description="会话ID")
    conversation_title: Optional[str] = Field(default=None, description="会话标题")
    model_id: Optional[str] = Field(default=None, description="模型ID")
    system_prompt: Optional[str] = Field(default=None, description="系统提示")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=1024, description="最大token数")
    stream: bool = Field(default=True, description="是否流式输出")
    history: List[Dict[str, str]] = Field(default_factory=list, description="对话历史")
    knowledge_base_ids: List[str] = Field(default_factory=list, description="知识库ID列表")
    mcp_server_ids: List[str] = Field(default_factory=list, description="MCP服务器ID列表")
    use_web_search: bool = Field(default=False, description="是否使用网络搜索")
    use_tools: bool = Field(default=False, description="是否使用工具")

class ChatResponse(BaseModel):
    """聊天响应"""
    message: str = Field(..., description="回复消息")
    conversation_id: str = Field(..., description="会话ID")
    model_id: str = Field(..., description="使用的模型ID")
    usage: Optional[Dict[str, Any]] = Field(default=None, description="使用统计")

class ToolCallRequest(BaseModel):
    """工具调用请求"""
    tool_name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    conversation_id: Optional[str] = Field(default=None, description="会话ID")

class StreamEvent(BaseModel):
    """流事件"""
    type: str = Field(..., description="事件类型")
    data: Any = Field(..., description="事件数据")
    
    class Config:
        """Pydantic配置"""
        arbitrary_types_allowed = True 