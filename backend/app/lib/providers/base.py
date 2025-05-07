from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Callable, AsyncGenerator, Any, Union
import asyncio
import json

class MessageDict(Dict[str, str]): # Simple type alias
    pass

class BaseProvider(ABC):
        
    @abstractmethod
    async def completions(
        self,
        messages: List[MessageDict],
        model_id: str,
        system_prompt: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs: Any
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Performs chat completions.
        If stream=True, returns an async generator yielding text chunks.
        If stream=False, returns the complete response string or None on error.
        """
        pass
        
    def _build_prompt(self, base_prompt: str, tools: List[Any]) -> str:
        """构建ReAct专用的系统提示"""
        # 格式化工具描述
        tools_desc = []
        for tool in tools:
            # 兼容处理Tool对象和字典格式
            if hasattr(tool, "name"):
                # 处理Tool对象
                name = tool.name
                description = tool.description
                param_desc = []
                for param in tool.parameters:
                    param_desc.append(f"  - {param.name}: {param.description}")
            else:
                # 处理字典格式
                name = tool.get("name", "")
                description = tool.get("description", "")
                params = tool.get("parameters", {}).get("properties", {})
                
                param_desc = []
                for param_name, param_info in params.items():
                    param_desc.append(f"  - {param_name}: {param_info.get('description', '')}")
            
            # 格式化工具描述
            tool_desc = f"{name}: {description}"
            
            # 添加参数描述（只有当有参数时才添加）
            if param_desc:
                tool_desc += "\n\nArgs:"
                for desc in param_desc:
                    tool_desc += f"\n{desc}"
            
            tools_desc.append(tool_desc)
        
        formatted_tools = "\n\n".join(tools_desc)
        
        # 使用提供的官方模板
        react_prompt = f"""{base_prompt or "You are a helpful AI assistant that uses tools when necessary."} **IMPORTANT: Respond in the same language as the user's question for all parts of your answer, including explanations.**
### Available Tools
You have access to the following tools. Use them when required to answer the user's question:
{formatted_tools}

### Instructions
1.  Analyze the user's question ('User:').
2.  Determine if you can answer directly or if you need to use tools.
3.  **If you can answer directly:** Provide your reasoning followed by the complete answer.
4.  **If you need to use one or more tools:**
    *   **First, output your thought process:** Explain clearly why you need the tool(s) and your plan.
    *   **Then, on new lines, output the required tool calls as a JSON array.** This array should contain an object for each tool call, including 'tool_name' and 'arguments'. Ensure the JSON is valid.
    *   **Your response should conclude with the JSON array.** Please ensure no extra text or explanation follows the closing bracket `]` of the JSON array.
5.  Tool results will be provided back to you later to help formulate the final answer.
6.  Using the language of the user's question, answer the user's question.

### Output Format Examples

Example 1: Single Tool Call Required
User: What's the current price of Bitcoin?
Assistant:
I need to get up-to-date information about Bitcoin's current price. Since I don't have real-time data, I'll use a web search to find the latest price information.
```json
[
    {{
        "tool_name": "web-search/search",
        "arguments": {{"query": "current Bitcoin price USD"}}
    }}
]
```

Example 2: Multiple Tool Calls Required (Travel Planning)
User: Plan a 3-day trip to Sanya from Shanghai for May 1st. I need flight, hotel, and weather info.
Assistant: 
To help plan this trip, I need to gather several pieces of information:
1. Flight options from Shanghai to Sanya on May 1st
2. Hotel availability in Sanya for May 1-4
3. Weather forecast for Sanya during those dates

I'll search for all this information at once:

```json
[
    {{
        "tool_name": "flight_search",
        "arguments": {{"origin": "Shanghai", "destination": "Sanya", "date": "2024-05-01"}}
    }},
    {{
        "tool_name": "hotel_search",
        "arguments": {{"location": "Sanya", "check_in_date": "2024-05-01", "check_out_date": "2024-05-04"}}
    }},
    {{
        "tool_name": "weather_forecast",
        "arguments": {{"location": "Sanya", "date": "2024-05-01"}}
    }}
]
```

Example 3: Direct Answer
User: What is 15 * 24?
Assistant: 
I'm calculating the product of 15 and 24.

15 * 24 = 15 * (20 + 4) = 15 * 20 + 15 * 4 = 300 + 60 = 360.

Therefore, 15 * 24 equals 360.

Begin Task!
User: {{input}}
Assistant:
"""
        return react_prompt
        