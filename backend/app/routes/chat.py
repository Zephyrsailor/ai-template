import asyncio
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

from ..schemas import ChatRequest
from ..providers.openai import OpenAIProvider
from ..config import get_settings, get_provider

# Create router
router = APIRouter(prefix="/api/chat", tags=["chat"])

# --- API Endpoints ---
@router.post("/stream")
async def chat_stream_endpoint(request: ChatRequest, 
                               provider: OpenAIProvider = Depends(get_provider),
                               settings = Depends(get_settings)):
    """
    Handles chat requests and streams responses back.
    """
    messages = request.history + [{"role": "user", "content": request.message}]
    model_to_use = request.model_id or settings.DEFAULT_MODEL
    system_p = request.system_prompt
    temp = request.temperature
    max_t = request.max_tokens

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            stream_gen = await provider.completions(
                messages=messages,
                model_id=model_to_use,
                system_prompt=system_p,
                temperature=temp,
                max_tokens=max_t,
                stream=True  # Force stream=True for this endpoint
            )
            # Ensure we got an async generator
            if isinstance(stream_gen, AsyncGenerator):
                async for chunk in stream_gen:
                    # Send plain text chunks. Frontend JS will handle appending.
                    yield chunk
                    await asyncio.sleep(0.01)  # Small sleep to allow other tasks
            elif isinstance(stream_gen, str):  # Handle error strings yielded by generator
                yield stream_gen
            elif stream_gen is None:  # Handle None return on initial call error
                yield "[ERROR: Failed to start stream]"

        except Exception as e:
            print(f"Error in event_generator: {e}")
            yield f"[INTERNAL_SERVER_ERROR: {str(e)}]"  # Send error message to client

    # Use StreamingResponse with the async generator
    # media_type='text/plain' because we send raw text chunks
    return StreamingResponse(event_generator(), media_type='text/plain') 