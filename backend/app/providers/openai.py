import os
import json
from openai import OpenAI, AsyncOpenAI, APIError, APITimeoutError, RateLimitError # Use Async client
from typing import List, Dict, Optional, AsyncGenerator, Any
from .base import BaseProvider, MessageDict
import asyncio

class OpenAIProvider(BaseProvider):
    """
    Async Provider for OpenAI and compatible APIs using the openai library.
    Focuses on core chat completion functionality.
    """
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        if not api_key:
            raise ValueError("API key is required.")
        self.api_key = api_key
        self.base_url = base_url
        try:
            # Use AsyncOpenAI for FastAPI integration
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=60.0,
            )
            print(f"AsyncOpenAI client initialized. Target URL: {self.client.base_url}")
        except Exception as e:
            print(f"Error initializing AsyncOpenAI client: {e}")
            raise

    def _prepare_messages(self, messages: List[MessageDict], system_prompt: Optional[str]) -> List[Dict[str, str]]:
        # Same as before
        request_messages: List[Dict[str, str]] = []
        if system_prompt:
            request_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            if isinstance(msg, dict) and \
               msg.get('role') in ['user', 'assistant'] and \
               isinstance(msg.get('content'), str) and \
               msg['content'].strip():
                request_messages.append({"role": msg['role'], "content": msg['content']})
        return request_messages

    async def completions(
        self,
        messages: List[MessageDict],
        model_id: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = 0.7,
        top_p: Optional[float] = 1.0,
        max_tokens: Optional[int] = 1024,
        stream: bool = False,
        **kwargs: Any
    ) -> AsyncGenerator[str, None] | str | None: # Updated return type hint
        """
        Performs chat completion. Returns AsyncGenerator for stream=True.
        """
        request_messages = self._prepare_messages(messages, system_prompt)
        if len(request_messages) <= (1 if system_prompt else 0):
            print("Error: No valid user/assistant messages to send.")
            if stream:
                async def empty_gen():
                    if False: yield # Creates an empty async generator
                return empty_gen()
            else:
                return None

        params = {
            "model": model_id,
            "messages": request_messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs
        }
        filtered_params = {k: v for k, v in params.items() if v is not None}

        try:
            response = await self.client.chat.completions.create(**filtered_params) # type: ignore

            if stream:
                # Return the async generator directly
                async def stream_generator():
                    try:
                        async for chunk in response: # type: ignore
                            delta = getattr(chunk.choices[0], 'delta', None)
                            # --- 处理推理/思考 (示例，字段名可能不同) ---
                            reasoning_chunk = getattr(delta, 'reasoning_content', getattr(delta, 'thinking', None))
                            if reasoning_chunk:
                                 # 转换为JSON字符串
                                 yield json.dumps({"type": "reasoning", "data": reasoning_chunk})
                            content_chunk = getattr(delta, 'content', None)
                            if content_chunk:
                                # 转换为JSON字符串
                                yield json.dumps({"type": "content", "data": content_chunk})
                    except APIError as e_stream:
                         print(f"\nError during stream processing: {e_stream}")
                         # Optionally yield an error message?
                         yield f"[STREAM_ERROR: {e_stream.message}]"
                    except Exception as e_gen:
                         print(f"\nUnexpected error in stream generator: {e_gen}")
                         yield f"[UNEXPECTED_STREAM_ERROR: {str(e_gen)}]"

                return stream_generator() # Return the async generator
            else:
                # Non-streaming: return the content string
                message_content = getattr(response.choices[0].message, 'content', None) # type: ignore
                return message_content

        except (APITimeoutError, RateLimitError, APIError) as e:
            print(f"\nAPI Error during completions call: {e}")
            if stream:
                async def error_gen():
                     yield f"[API_ERROR: {str(e)}]"
                     if False: yield # Make it an async generator
                return error_gen()
            else:
                return None # Indicate failure for non-streaming
        except Exception as e:
            import traceback
            print(f"\nUnexpected error during completions call: {e}")
            # traceback.print_exc()
            if stream:
                async def unexpected_error_gen():
                     yield f"[UNEXPECTED_ERROR: {str(e)}]"
                     if False: yield
                return unexpected_error_gen()
            else:
                return None