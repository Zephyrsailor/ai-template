from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Callable, AsyncGenerator, Any, Union
import asyncio
import json
from app.domain.constants import supports_function_calling, get_model_capability, ModelCapability

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
    
    def supports_function_calling(self, model_name: str) -> bool:
        """检查当前模型是否支持Function Calling"""
        return supports_function_calling(model_name)
    
    def get_model_capability(self, model_name: str) -> ModelCapability:
        """获取模型能力"""
        return get_model_capability(model_name)
        
    def _build_prompt(self, base_prompt: str, tools: List[Any]) -> str:
        """构建ReAct专用的系统提示 - 单工具调用模式"""
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
        
        # 使用单工具调用模式的提示词模板
        from datetime import datetime
        current_time_str = datetime.now().strftime("%Y-%m-%d %A, %H:%M:%S %Z")

        react_prompt = f"""### System Environment
Current Date and Time: {current_time_str}
Output Language Expectation: Respond in the same language as the user's question.
{base_prompt or "You are a helpful AI assistant that uses tools when necessary."} **IMPORTANT: Respond in the same language as the user's question for all parts of your answer, including explanations.**

### Available Tools
You have access to the following tools. Use them when required to answer the user's question:
{formatted_tools}

### Instructions
1. Analyze the user's question ('User:').
2. Determine if you can answer directly or if you need to use tools.
3. **If you can answer directly:**
   * Provide your reasoning (your thought process).
   * Followed by the complete answer.

4. **If you need to use tools:**
   * **CRITICALLY IMPORTANT: You MUST first output your thought process.**
     * This thought process should clearly explain *why* you need the tool and your *plan* for using it.
     * **This thought process section MUST NOT be empty.** Even if your reasoning is brief, provide at least one sentence.

   * **Single Tool Call Rule:**
     * **You can only call ONE tool at a time.** Each response should contain exactly one tool call.
     * If you need multiple tools to complete a task, call them sequentially across multiple turns.
     * Plan your tool usage carefully and explain your strategy in the thought process.

   * **Outputting Tool Calls:**
     * After your thought process, starting on a new line, output the required tool call as a single, valid JSON object.
     * The object must include 'tool_name' (string) and 'arguments' (object).

   * **Your response when using tools MUST conclude with the closing bracket `}}` of the JSON object.** Ensure absolutely no extra text, pleasantries, or explanations follow the JSON object.

   * **Structure for tool use:**
     [Your detailed thought process text here. This must not be empty. Clearly explain your plan.]
     ```json
     {{"tool_name": "tool_name", "arguments": {{"arg1": "value1", "arg2": "value2"}}}}
     ```

5. Using the language of the user's question, answer the user's question for all parts of your response.

### Output Format Examples
**Note: The examples below illustrate the output format. Always use the tool names and arguments as defined in the "Available Tools" section above.**

Example 1: Single Tool Call Required
User: What's the current price of Bitcoin?
Assistant:
I need to get up-to-date information about Bitcoin's current price. Since I don't have real-time data, I'll use a web search to find the latest price information.
```json
{{"tool_name": "web-search", "arguments": {{"query": "current Bitcoin price USD"}}}}
```
Example 2: Direct Answer
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
        
    def get_model_limits(self, model_name: str) -> Dict[str, int]:
        """获取模型的token限制参数
        
        Returns:
            dict: {
                "context_length": int,  # 上下文窗口大小
                "max_tokens": int       # 单次生成最大token数
            }
        """
        # 基础的模型参数推断，子类可以重写以提供更精确的值
        model_lower = model_name.lower()
        
        # 默认值
        context_length = 32768
        max_tokens = 4096
        
        # OpenAI模型
        if "gpt-4" in model_lower:
            if "turbo" in model_lower or "1106" in model_lower or "0125" in model_lower:
                context_length = 128000
                max_tokens = 4096
            elif "32k" in model_lower:
                context_length = 32768
                max_tokens = 4096
            else:
                context_length = 8192
                max_tokens = 4096
        elif "gpt-3.5" in model_lower:
            if "16k" in model_lower:
                context_length = 16384
                max_tokens = 4096
            else:
                context_length = 4096
                max_tokens = 4096
        elif "gpt-4o" in model_lower:
            context_length = 128000
            max_tokens = 4096
        
        # Anthropic Claude模型
        elif "claude-3" in model_lower:
            if "opus" in model_lower or "sonnet" in model_lower:
                context_length = 200000
                max_tokens = 4096
            elif "haiku" in model_lower:
                context_length = 200000
                max_tokens = 4096
        elif "claude-2" in model_lower:
            context_length = 100000
            max_tokens = 4096
        elif "claude" in model_lower:
            context_length = 100000
            max_tokens = 4096
        
        # DeepSeek模型
        elif "deepseek" in model_lower:
            if "coder" in model_lower:
                context_length = 16384
                max_tokens = 4096
            else:
                context_length = 32768
                max_tokens = 4096
        
        # Google Gemini模型
        elif "gemini" in model_lower:
            if "pro" in model_lower:
                context_length = 1000000
                max_tokens = 8192
            else:
                context_length = 32768
                max_tokens = 4096
        
        # Ollama本地模型
        elif any(x in model_lower for x in ["llama", "mistral", "qwen", "yi"]):
            if "7b" in model_lower or "8b" in model_lower:
                context_length = 8192
                max_tokens = 2048
            elif "13b" in model_lower or "14b" in model_lower:
                context_length = 4096
                max_tokens = 2048
            elif "70b" in model_lower or "72b" in model_lower:
                context_length = 4096
                max_tokens = 4096
            else:
                context_length = 4096
                max_tokens = 2048
        
        # Qwen模型特殊处理
        elif "qwen" in model_lower:
            if "72b" in model_lower:
                context_length = 32768
                max_tokens = 2048
            elif "14b" in model_lower:
                context_length = 8192
                max_tokens = 2048
            elif "7b" in model_lower:
                context_length = 8192
                max_tokens = 2048
            else:
                context_length = 8192
                max_tokens = 2048
        
        return {
            "context_length": context_length,
            "max_tokens": max_tokens
        }
    
    def validate_token_params(self, model_name: str, max_tokens: Optional[int] = None, 
                            context_length: Optional[int] = None) -> Dict[str, int]:
        """验证并调整token参数
        
        Args:
            model_name: 模型名称
            max_tokens: 用户设置的max_tokens
            context_length: 用户设置的context_length
            
        Returns:
            dict: 验证后的参数
        """
        model_limits = self.get_model_limits(model_name)
        
        # 如果用户没有设置，使用模型默认值
        if context_length is None:
            context_length = model_limits["context_length"]
        if max_tokens is None:
            max_tokens = model_limits["max_tokens"]
        
        # 确保max_tokens不超过context_length的一半（为上下文预留空间）
        max_allowed_tokens = min(max_tokens, context_length // 2)
        
        return {
            "context_length": context_length,
            "max_tokens": max_allowed_tokens
        }
        