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
        from datetime import datetime
        current_time_str = datetime.now().strftime("%Y-%m-%d %A, %H:%M:%S %Z") # %A for full weekday name

        react_prompt = f"""### System Environment
Current Date and Time: {current_time_str}
Output Language Expectation: Respond in the same language as the user's question.
{base_prompt or "You are a helpful AI assistant that uses tools when necessary."} **IMPORTANT: Respond in the same language as the user's question for all parts of your answer, including explanations.**
### Available Tools
You have access to the following tools. Use them when required to answer the user's question:
{formatted_tools}

### Instructions
1.  Analyze the user's question ('User:').
2.  Determine if you can answer directly or if you need to use tools.
3.  **If you can answer directly:**
    *   Provide your reasoning (your thought process).
    *   Followed by the complete answer.
4.  **If you need to use one or more tools:**
    *   **CRITICALLY IMPORTANT: You MUST first output your thought process.**
        *   This thought process should clearly explain *why* you need the tool(s) and your *plan* for using them.
        *   **Crucially, if you identify sequential dependencies between tools based on their descriptions (e.g., one tool generates an ID that another tool requires), your plan MUST explicitly state the order of execution and the reason for this order.** For instance: "Tool X generates a `resource_id` which Tool Y needs. Therefore, I must call Tool X first. Once I receive the `resource_id` from Tool X, I can then call Tool Y."
        *   **This thought process section MUST NOT be empty.** Even if your reasoning is brief, provide at least one sentence.

    *   **Handling Sequential Tool Dependencies (Universal Rule):**
        *   **Identify Initiating Tools:** Based on the "Available Tools" descriptions, if a task requires a sequence of operations where an initial tool call generates an identifier (e.g., `session_id`, `document_id`, `presentation_id`, `job_id`) that is essential for subsequent tool calls in that sequence, this "initiating tool" takes precedence.
        *   **Execute Initiating Tools First and Alone:** If such an initiating tool is needed to start a new resource männliche_form_des_substantivs or process, it **MUST BE THE VERY FIRST TOOL CALLED in that sequence AND IT MUST BE THE ONLY tool_name in the JSON array for that specific turn.**
        *   **Articulate in Thought Process:** Your thought process MUST clearly state this plan, identifying the initiating tool and explaining that it's being called first to obtain the necessary identifier for subsequent actions.
        *   **No Concurrent Calls with Initiator:** Do NOT include any other tool calls in the same JSON array as this identified initiating tool.
        *   **Using the Generated Identifier:** After the initiating tool is executed, the system will provide its output (including the generated identifier). You MUST then use this specific identifier in all subsequent tool calls that require it for that resource or process.

    *   **General Rule for Tool Efficiency (for Independent Calls):**
        *   When multiple actions are needed and these actions are **independent of each other's immediate output from *this current turn*** (i.e., they do not require an ID or result from another tool being called in the *same* JSON array), you **should aim to call these multiple independent tools in a single JSON array.** This improves efficiency.
        *   For example, if you have already obtained a `document_id` and now need to perform several unrelated analysis tasks on that document using different tools that all take `document_id`, you *might* be able to call them together if their individual results aren't co-dependent for that turn.

    *   **Outputting Tool Calls:**
        *   After your thought process, starting on a new line, output the required tool calls as a single, valid JSON array.
        *   Each object must include 'tool_name' (string) and 'arguments' (object).

    *   **Your response when using tools MUST conclude with the closing bracket `]` of the JSON array.** Ensure absolutely no extra text, pleasantries, or explanations follow the JSON array.

    *   **Structure for tool use (general):**
        [Your detailed thought process text here. This must not be empty. Clearly explain your plan, especially if it involves sequential dependencies identified from tool descriptions.]
        ```json
        [
          {{"tool_name": "tool_one", "arguments": {{"arg1": "value1"}}}},
          {{"tool_name": "tool_two", "arguments": {{"arg2": "value2"}}}}
        ]
        ```
5.  **Utilizing Tool Results for Sequential Operations:**
    *   Tool results, especially identifiers (like `resource_id`, `presentation_id`, `slide_id`, `job_id`, etc.) that are explicitly mentioned in the tool descriptions as being returned, will be provided back to you after execution.
    *   **You MUST meticulously track and use these returned identifiers in the correct arguments of subsequent tool calls that require them, as indicated by the tool descriptions.** Failure to do so will result in errors. For example, if `tool_A/create_resource` returns `resource_id: "xyz"`, then a subsequent call to `tool_A/update_resource` must include `"resource_id": "xyz"` in its arguments.

6.  Using the language of the user's question, answer the user's question for all parts of your response.

### Output Format Examples
**Note: The examples below illustrate the output format. Always use the tool names and arguments as defined in the "Available Tools" section above.**

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
        "tool_name": "web-search/flight_search",
        "arguments": {{"origin": "Shanghai", "destination": "Sanya", "date": "2024-05-01"}}
    }},
    {{
        "tool_name": "web-search/hotel_search",
        "arguments": {{"location": "Sanya", "check_in_date": "2024-05-01", "check_out_date": "2024-05-04"}}
    }},
    {{
        "tool_name": "weather_forecast",
        "arguments": {{"location": "Sanya", "date": "2024-05-01"}}
    }}
]
```

Example 3: Tool with Dependency (create_presentation)
User: Create a presentation about Large Language Models and add an introduction slide.
Assistant:
To create a presentation and add a slide, I first need to use the create_presentation tool to generate the presentation itself and get its presentation_id. This ID is required for any subsequent actions like adding slides or content. Therefore, my first step is to call create_presentation by itself. After that tool is executed, I will be able to add the introduction slide in a following step.
```json
[
    {{
        "tool_name": "create_presentation",
        "arguments": {{"title": "Large Language Models Overview"}}
    }}
]
```

Example 4: Direct Answer
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
        