import os
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import AsyncGenerator

from .schemas import ChatRequest
from .providers.openai import OpenAIProvider # Import your provider

load_dotenv() # Load .env file

# --- Configuration ---
PROVIDER_TYPE = os.getenv("PROVIDER_TYPE", "openai") # Default to openai
API_KEY = ""
BASE_URL = None
DEFAULT_MODEL = ""

if PROVIDER_TYPE == "openai":
    API_KEY = os.getenv("OPENAI_API_KEY")
    BASE_URL = os.getenv("OPENAI_BASE_URL") # Can be None
    DEFAULT_MODEL = "gpt-4o-mini" # Or your preferred default OpenAI model
elif PROVIDER_TYPE == "deepseek":
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEFAULT_MODEL = "deepseek-reasoner" # Or your preferred default DeepSeek model
else:
    raise ValueError(f"Unsupported PROVIDER_TYPE: {PROVIDER_TYPE}")

if not API_KEY:
    raise ValueError(f"API Key not found for provider: {PROVIDER_TYPE}. Please set the environment variable.")

# --- Initialize Provider ---
llm_provider = OpenAIProvider(api_key=API_KEY, base_url=BASE_URL)

# --- FastAPI App ---
app = FastAPI(title="AI Template API")

# --- CORS Middleware ---
# Adjust origins as needed for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins for simplicity, restrict in production
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

# --- API Endpoint ---
@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """
    Handles chat requests and streams responses back.
    """
    messages = request.history + [{"role": "user", "content": request.message}]
    model_to_use = request.model_id or DEFAULT_MODEL
    system_p = request.system_prompt # Use provided or None
    temp = request.temperature
    max_t = request.max_tokens

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            stream_gen = await llm_provider.completions(
                messages=messages,
                model_id=model_to_use,
                system_prompt=system_p,
                temperature=temp,
                max_tokens=max_t,
                stream=True # Force stream=True for this endpoint
            )
            # Ensure we got an async generator
            if isinstance(stream_gen, AsyncGenerator):
                async for chunk in stream_gen:
                    # Send plain text chunks. Frontend JS will handle appending.
                    yield chunk
                    await asyncio.sleep(0.01) # Small sleep to allow other tasks
            elif isinstance(stream_gen, str): # Handle error strings yielded by generator
                 yield stream_gen
            elif stream_gen is None: # Handle None return on initial call error
                 yield "[ERROR: Failed to start stream]"

        except Exception as e:
            print(f"Error in event_generator: {e}")
            yield f"[INTERNAL_SERVER_ERROR: {str(e)}]" # Send error message to client

    # Use StreamingResponse with the async generator
    # media_type='text/plain' because we send raw text chunks
    return StreamingResponse(event_generator(), media_type='text/plain')

# --- Basic Root Endpoint (Optional) ---
@app.get("/")
async def root():
    return {"message": "AI Template Backend is running!"}