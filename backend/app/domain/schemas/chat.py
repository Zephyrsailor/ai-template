"""
聊天相关的数据验证模型
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class StreamEvent(BaseModel):
    """流式事件模型"""
    type: str
    data: Any

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    history: Optional[List[Dict[str, str]]] = None
    model_id: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_k: Optional[int] = None
    # 知识库相关
    knowledge_base_ids: Optional[List[str]] = None
    # 工具相关
    mcp_server_ids: Optional[List[str]] = None
    tools_category: Optional[str] = "default"
    use_tools: Optional[bool] = False
    use_web_search: Optional[bool] = False
    # 会话相关
    conversation_id: Optional[str] = None
    conversation_title: Optional[str] = None

class ToolCallRequest(BaseModel):
    """工具调用请求"""
    tool_name: str
    arguments: Dict[str, Any]

class QueryResponseWrapper(BaseModel):
    """知识库查询结果包装器"""
    data: Optional[Dict[str, Any]] = None
    code: int = 200
    message: str = "查询成功"

class ChatResponse(BaseModel):
    """聊天响应模型"""
    message: str
    events: Optional[List[StreamEvent]] = None
    query_results: Optional[List[Dict[str, Any]]] = None 