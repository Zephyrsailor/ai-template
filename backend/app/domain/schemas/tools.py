"""
工具相关的数据验证模型
"""
import re
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union, Any

class ToolParameter(BaseModel):
    """工具参数描述"""
    name: str = Field(..., description="参数名称")
    description: str = Field(..., description="参数描述")
    type: str = Field(..., description="参数类型")
    required: bool = Field(False, description="是否必需")
    enum: Optional[List[Any]] = Field(None, description="枚举值列表")
    default: Optional[Any] = Field(None, description="默认值")

class Tool(BaseModel):
    """工具描述"""
    id: str = Field(..., description="工具ID")
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    server: Optional[str] = Field(None, description="工具所属服务器")
    category: Optional[str] = Field(None, description="工具类别")
    parameters: List[ToolParameter] = Field(default=[], description="工具参数列表")

    def to_format(self) -> str:
        """Format tool information for LLM.

        Returns:
            A formatted string describing the tool.
        """
        args_desc = []
        for param in self.parameters:
            arg_desc = f"- {param.name}: {param.description}"
            if param.required:
                arg_desc += " (required)"
            if param.type:
                arg_desc += f" (type: {param.type})"
            if param.enum:
                arg_desc += f" (options: {', '.join(map(str, param.enum))})"
            args_desc.append(arg_desc)

        return f"""
Tool: {self.name}
Description: {self.description}
Arguments:
{chr(10).join(args_desc) if args_desc else "No arguments"}
"""
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI工具格式"""
        openai_params = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param in self.parameters:
            openai_params["properties"][param.name] = {
                "type": param.type,
                "description": param.description
            }
            
            if param.enum:
                openai_params["properties"][param.name]["enum"] = param.enum
                
            if param.required:
                openai_params["required"].append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,  # 直接使用name字段，已经是OpenAI兼容格式
                "description": self.description,
                "parameters": openai_params
            }
        }
    
    def to_anthropic_format(self) -> Dict[str, Any]:
        """转换为Anthropic工具格式"""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param in self.parameters:
            schema["properties"][param.name] = {
                "type": param.type,
                "description": param.description
            }
            
            if param.enum:
                schema["properties"][param.name]["enum"] = param.enum
                
            if param.required:
                schema["required"].append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": schema
        }

class ToolList(BaseModel):
    """工具列表响应"""
    tools: List[Tool] = Field(..., description="工具列表")

class ToolCallResult(BaseModel):
    """工具调用结果"""
    result: Any = Field(..., description="工具调用结果")
    error: Optional[str] = Field(None, description="错误信息") 