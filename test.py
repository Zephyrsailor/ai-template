import os

os.environ["OPENAI_API_KEY"] = "sk-..."


def multiply(a: int, b: int) -> int:
    """Multiply two integers and returns the result integer"""
    return a * b


def add(a: int, b: int) -> int:
    """Add two integers and returns the result integer"""
    return a + b


from llama_index.llms.deepseek import DeepSeek
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.workflow import Context
from llama_index.core.agent.workflow import AgentStream, ToolCallResult
import asyncio


llm = DeepSeek(model="deepseek-reasoner",api_key='sk-40009c94b8da464b8a9a9c11e29b6e31')
agent = ReActAgent(tools=[multiply, add], llm=llm)

# Create a context to store the conversation history/session state
ctx = Context(agent)


async def run_agent():
    handler = agent.run("今日猪肉价格?", ctx=ctx)

    async for ev in handler.stream_events():
        # if isinstance(ev, ToolCallResult):
        #     print(f"\nCall {ev.tool_name} with {ev.tool_kwargs}\nReturned: {ev.tool_result}")
        if isinstance(ev, AgentStream):
            print(f"{ev.delta}", end="", flush=True)

    response = await handler
    return response


if __name__ == "__main__":
    asyncio.run(run_agent())