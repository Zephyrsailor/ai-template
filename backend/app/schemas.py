from pydantic import BaseModel
from typing import List, Dict, Optional

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = [] # Expecting [{'role': 'user', 'content': '...'}, ...]
    model_id: str | None = None # Allow overriding model per request
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    knowledge_base_ids: List[str] = [] # List of knowledge base IDs to query, if empty will not use knowledge base