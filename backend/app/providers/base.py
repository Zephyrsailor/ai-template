from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Callable, AsyncGenerator, Any

class MessageDict(Dict[str, str]): # Simple type alias
    pass

class BaseProvider(ABC):
    @abstractmethod
    async def completions(
        self,
        messages: List[MessageDict],
        model_id: str,
        system_prompt: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        stream: bool,
        **kwargs: Any
    ) -> AsyncGenerator[str, None] | str | None: # Return type depends on stream
        """
        Performs chat completions.
        If stream=True, returns an async generator yielding text chunks.
        If stream=False, returns the complete response string or None on error.
        """
        pass