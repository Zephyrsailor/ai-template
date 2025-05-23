**MCP (模型上下文协议) **

**一、 MCP 核心概念与目标**

*   **是什么？** MCP (Model Context Protocol) 是一个由 Anthropic 发起并开源的标准化协议，旨在统一大型语言模型 (LLM) 应用（如 AI 助手、IDE 插件、智能体）与外部数据源和工具进行交互的方式。 
*   **目标与价值：** 解决当前 LLM 应用集成方式碎片化、开发复杂的问题。通过提供一个类似“AI 应用的 USB-C”的通用接口，让 LLM 应用能更安全、便捷、实时地接入所需的上下文信息（文件、数据库、API、代码库等）和功能（如执行代码、发送邮件、搜索网页），从而显著提升 LLM 的能力、相关性和准确性。对用户而言，这意味着更强大的 AI 助手；对开发者而言，意味着更低的集成成本和更广阔的可组合生态。 
*   **设计原则：** 服务器易于构建、高度可组合、安全隔离（服务器不读取完整对话）、功能可渐进添加。

**二、 核心架构**

MCP 采用 **客户端-宿主-服务器 (Client-Host-Server)** 架构：

1.  **宿主 (Host):** 指运行 MCP 客户端的应用程序，通常是面向用户的 LLM 应用（如 Claude Desktop、Dify、Cherry Studio、你的智能体架构）。宿主负责：
    *   管理一个或多个 MCP 客户端实例。
    *   决定连接哪些 MCP 服务器。
    *   处理用户权限和批准流程（尤其是工具调用）。
    *   协调与底层 LLM 的交互（将工具信息传给 LLM，将 LLM 的调用请求路由给相应的客户端）。
    *   聚合来自不同服务器的能力。
2.  **客户端 (Client):** 由宿主创建和管理，嵌入在宿主应用内部。每个客户端与一个服务器建立 **1:1** 的状态化连接。负责：
    *   处理与特定服务器的 MCP 协议通信（JSON-RPC 消息）。
    *   进行协议版本和能力协商。
    *   维护连接状态。
3.  **服务器 (Server):** 独立的进程或服务，负责连接具体的数据源或工具，并通过 MCP 协议向客户端暴露能力。服务器可以是：
    *   本地运行的脚本或应用（通过 `stdio` 通信）。
    *   网络上可访问的服务（通过 HTTP/SSE 等通信）。

**三、 核心功能原语**

MCP 服务器通过以下三种主要原语向客户端（宿主）暴露能力：

1.  **资源 (Resources):**
    *   **控制权:** 应用控制 (Application-controlled)。宿主应用决定何时以及如何使用资源。
    *   **作用:** 提供上下文数据给 LLM 或用户（如文件内容、数据库记录、API 响应）。
    *   **特点:** 通过唯一 URI 标识，可以是文本或二进制数据。通常是“只读”的。
2.  **工具 (Tools):**
    *   **控制权:** 模型控制 (Model-controlled)。由 LLM 根据当前对话和目标决定调用哪个工具。
    *   **作用:** 允许 LLM 执行动作、与外部系统交互或进行计算（如联网搜索、写文件、调用 API）。
    *   **特点:** 每个工具有名称、描述、输入参数的 JSON Schema 和可选的行为注解。**执行前必须得到用户批准。**
3.  **提示 (Prompts):**
    *   **控制权:** 用户控制 (User-controlled)。通常由用户在客户端界面显式选择触发（如斜杠命令、按钮）。
    *   **作用:** 提供可重用的交互模板或引导式工作流，生成与 LLM 交互的消息序列。
    *   **特点:** 包含名称、描述和可选参数。

**四、 通信与协议基础**

*   **消息格式:** 所有通信遵循 **JSON-RPC 2.0** 规范，包括请求 (Request)、响应 (Response - 成功或错误) 和通知 (Notification)。
*   **传输协议 (Transports):** 定义消息如何在客户端和服务器间传递。 
    *   **`stdio` (标准输入/输出):** 客户端启动服务器作为子进程，通过 stdin/stdout 通信。适用于本地集成。
    *   **Streamable HTTP (取代旧的 HTTP+SSE):** 服务器监听 HTTP 端点。客户端通过 POST 发送消息，服务器可以通过 HTTP 响应或 SSE 流响应/发送通知。适用于网络连接和独立运行的服务器。
*   **生命周期 (Lifecycle):** 连接建立后有明确的初始化 (initialize) 握手阶段，用于交换版本信息和协商双方支持的能力 (Capabilities)，然后进入操作阶段，最后是关闭连接。 
*   **能力协商 (Capabilities):** 客户端和服务器在初始化时声明各自支持的可选功能（如资源订阅、工具列表变更通知、采样、日志级别设置等）。后续交互必须基于协商成功的能力。 

---

**五、 开发实践 (Python SDK 重点详述)**

官方提供了 `mcp` Python SDK，极大简化了 MCP 客户端和服务器的开发。 

**(一) 安装 SDK**

推荐使用 `uv` (或其他包管理器如 `pip`) 安装。`[cli]` 选项会额外安装命令行工具 (`mcp`)。 

```bash
# 使用 uv
uv add "mcp[cli]"

# 使用 pip
pip install "mcp[cli]"
```

**(二) 开发 MCP 服务器 (使用 FastMCP - 推荐的高级接口)**

`FastMCP` 利用 Python 类型提示和装饰器，让服务器开发更简洁、更 Pythonic。 

1.  **初始化服务器:**
    ```python
    from mcp.server.fastmcp import FastMCP

    # 创建实例，提供服务器名称
    # 可选参数：version, description, dependencies, lifespan 等
    mcp = FastMCP(
        name="MyAwesomeServer",
        version="1.1.0",
        description="Provides awesome tools and resources.",
        # dependencies=["pandas", "requests"], # 告知 mcp install 需要安装的额外依赖
        # lifespan=my_lifespan_manager # 用于管理启动/关闭时的资源
    )
    ```

2.  **定义工具 (`@mcp.tool()`):**
    *   使用装饰器 `@mcp.tool()` 标记一个函数作为 MCP 工具。
    *   **函数签名 (类型提示):** `FastMCP` 会自动将函数的参数类型提示转换为工具的 `inputSchema`。
    *   **文档字符串 (Docstring):** 函数的文档字符串会被用作工具的 `description`，参数的描述（如果遵循 Google/Numpy/Sphinx 等风格）也会被提取到 Schema 中。这对于 LLM 理解工具至关重要。
    *   **返回值:** 函数的返回值会被包装成 `CallToolResult`。可以直接返回字符串、数字、列表、字典，或者返回 `mcp.types` 中定义的标准内容对象 (如 `TextContent`, `ImageContent`, `EmbeddedResource`) 列表。
    *   **上下文对象 (`ctx: Context`):** 可以将 `Context` 对象作为最后一个参数添加到工具函数签名中，用于访问 MCP 功能（日志、进度报告、读资源等）。

    ```python
    from mcp.server.fastmcp import Context
    from mcp.types import TextContent, ImageContent
    import httpx

    @mcp.tool()
    async def get_website_text(url: str, ctx: Context) -> list[TextContent]:
        """
        Fetches the main text content of a given URL.

        Args:
            url: The URL of the website to fetch.
        """
        ctx.info(f"Fetching text from {url}") # 使用 Context 记录日志
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, follow_redirects=True, timeout=10)
                response.raise_for_status()
                # ... (省略 HTML 解析逻辑) ...
                text_content = "Extracted text..."
                # 返回标准内容对象列表
                return [TextContent(type="text", text=text_content)]
        except Exception as e:
            ctx.error(f"Failed to fetch {url}: {e}")
            # 可以在 CallToolResult 中报告错误
            return [TextContent(type="text", text=f"Error fetching URL: {e}")]
    ```

3.  **定义资源 (`@mcp.resource()`):**
    *   使用装饰器 `@mcp.resource()` 标记函数，提供资源内容。
    *   装饰器的参数是资源的 **URI 模板** (RFC 6570)。花括号 `{}` 中的部分是动态参数，会从函数参数中获取。
    *   函数参数需要与 URI 模板中的变量名匹配，并带类型提示。
    *   返回值是资源的内容（通常是字符串或字节）。SDK 会处理 `ReadResourceResult` 的包装。

    ```python
    # 静态资源
    @mcp.resource("config://app/settings")
    def get_app_settings() -> str:
        """Returns the application settings."""
        return '{"theme": "dark", "language": "en"}'

    # 动态资源
    @mcp.resource("users://{user_id}/profile.json")
    async def get_user_profile(user_id: str, ctx: Context) -> str:
        """Gets the profile for a specific user."""
        ctx.info(f"Fetching profile for user: {user_id}")
        # ... (从数据库或其他地方获取用户信息) ...
        profile_data = f'{{"id": "{user_id}", "name": "User {user_id}"}}'
        return profile_data
    ```

4.  **定义提示 (`@mcp.prompt()`):**
    *   使用装饰器 `@mcp.prompt()` 标记函数，生成提示消息序列。
    *   装饰器的参数是提示的**名称 (name)**。文档字符串用作 `description`。
    *   函数参数是提示所需的动态参数，带类型提示。
    *   返回值可以是单个字符串（默认为 user 角色的 TextContent），也可以是一个 `mcp.server.fastmcp.prompts.base.Message` 对象列表（允许定义多轮对话和 assistant 角色）。

    ```python
    from mcp.server.fastmcp.prompts import base as prompt_base

    @mcp.prompt()
    def summarize_text(text_to_summarize: str) -> str:
        """Creates a prompt to summarize the given text."""
        return f"Please summarize the following text:\n\n{text_to_summarize}"

    @mcp.prompt()
    def debug_error_flow(error_message: str) -> list[prompt_base.Message]:
        """Starts a debugging workflow for an error."""
        return [
            prompt_base.UserMessage(f"I encountered this error: {error_message}"),
            prompt_base.AssistantMessage("Okay, I can help. What were you doing when it happened?"),
        ]
    ```

5.  **使用上下文对象 (`ctx: Context`):**
    *   `ctx.info(msg)`, `ctx.warning(msg)`, `ctx.error(msg)`: 发送日志通知给客户端。 
    *   `await ctx.report_progress(current, total, message)`: 发送进度更新通知。 
    *   `await ctx.read_resource(uri)`: 从**其他**已连接的 MCP 服务器读取资源（如果 Host 支持并配置了此能力，较为高级的用法）。
    *   `ctx.request_context`: 访问低级请求上下文信息，包括 `lifespan_context`。

6.  **处理图像 (`Image` 类):**
    *   SDK 提供了 `mcp.server.fastmcp.Image` 类，方便在工具或资源中返回图像数据。你需要提供字节数据和格式。 [Source 17]

```python
from mcp.server.fastmcp import Image
# from PIL import Image as PILImage # 假设使用 Pillow 处理图像

@mcp.tool()
def generate_qr_code(data: str) -> Image:
    """Generates a QR code for the given data."""
    #... (使用 qrcode 库生成图像到 bytes_io) ...
    qr_img = qrcode.make(data)
    bytes_io = io.BytesIO()
    qr_img.save(bytes_io, format='PNG')
    image_bytes = bytes_io.getvalue()
    image_bytes = b"..." # 示例字节
    return Image(data=image_bytes, format="png") # 返回 Image 对象
```

7.  **生命周期管理 (`lifespan`):**
    *   可以为 `FastMCP` 提供一个异步上下文管理器函数 (`asynccontextmanager`) 作为 `lifespan` 参数。
    *   这个管理器在服务器启动时执行 `yield` 之前的代码（例如，建立数据库连接池），在服务器关闭时执行 `finally` 块中的代码（例如，关闭连接池）。
    *   `yield` 可以返回一个上下文对象，该对象可通过 `ctx.request_context.lifespan_context` 在工具/资源处理器中访问。 

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from your_db_lib import AsyncDatabase # 示例

@asynccontextmanager
async def manage_db_connection(server: FastMCP) -> AsyncIterator[Dict[str, AsyncDatabase]]:
    db_conn = await AsyncDatabase.connect("...")
    print("INFO: Database connected.", file=sys.stderr)
    try:
        yield {"db": db_conn} # 通过字典传递上下文
    finally:
        await db_conn.close()
        print("INFO: Database disconnected.", file=sys.stderr)

mcp = FastMCP("DBServer", lifespan=manage_db_connection)

@mcp.tool()
async def query_db(sql: str, ctx: Context) -> str:
    db = ctx.request_context.lifespan_context["db"] # 访问连接
    result = await db.query(sql)
    return str(result)
```

**(三) 开发 MCP 服务器 (使用低级 Low-Level API)**

如果你需要更精细的控制，可以直接使用 `mcp.server.Server` 类。你需要手动注册每个请求的处理函数，并自己构造响应对象。 
```python
import mcp.server.stdio
import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions, NotificationOptions

server = Server("low-level-example")

@server.list_tools() # 手动注册处理器
async def handle_list_tools() -> list[types.Tool]:
    # 手动构造 Tool 对象
    return [ types.Tool(...) ]

@server.call_tool() # 手动注册处理器
async def handle_call_tool(name: str, arguments: dict) -> types.CallToolResult:
    # 手动处理调用逻辑和构造 CallToolResult
    if name == "my_tool":
        # ...
        return types.CallToolResult(content=[types.TextContent(...)])
    raise ValueError("Unknown tool")

async def run_low_level():
    # 手动配置和运行
    init_opts = InitializationOptions(...)
    async with mcp.server.stdio.stdio_server() as (r, w):
        await server.run(r, w, init_opts)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_low_level())
```

**(四) 运行与部署 MCP 服务器**

有多种方式运行你开发好的服务器：

1.  **开发模式 (`mcp dev`):** 
    *   命令: `mcp dev your_script.py [--with dependency] [--with-editable .]`
    *   作用: **启动服务器并通过 `stdio` 连接到内置的 MCP Inspector (Web UI)**。这是开发和调试服务器功能的**最佳方式**。Inspector 允许你直接调用工具、查看资源/提示、观察日志和协议消息。
    *   `--with` / `--with-editable`: 可以临时安装依赖或本地代码。
2.  **安装到 Claude Desktop (`mcp install`):** 
    *   命令: `mcp install your_script.py [--name ServerName] [-v KEY=VAL] [-f .env]`
    *   作用: **自动修改** Claude Desktop 的 `claude_desktop_config.json` 文件，添加一个条目，让 Claude Desktop 在启动时**自动运行**你的服务器（通常使用 `uv run` 或 `python` 通过 `stdio` 启动）。这是将服务器集成给最终用户使用的便捷方式。
    *   `-v` / `-f`: 用于将环境变量传递给服务器进程。
3.  **直接执行脚本 (`python your_script.py` 或 `mcp run`):** 
    *   前提: 脚本中需要包含 `if __name__ == "__main__": mcp.run(transport='stdio')` 这样的代码。
    *   作用: 直接启动服务器，默认监听 `stdio`。主要用于简单测试或与其他期望通过 stdio 连接的进程集成。
4.  **集成到现有 ASGI 服务器 (如 Uvicorn, Hypercorn):** 
    *   前提: 服务器脚本定义了 `mcp = FastMCP(...)` 实例。
    *   命令: `uvicorn your_script:mcp.sse_app() --host 127.0.0.1 --port 8000 [--reload]`
    *   作用: 使用 ASGI 服务器运行你的 MCP 应用，使其能够通过 **HTTP (Streamable HTTP/SSE)** 协议在网络端口上提供服务。这是实现**本地调试时让 Claude Desktop 通过 `url` 连接**的首选方式，也适用于将 MCP 服务器部署为网络服务。
    *   `mcp.sse_app()`: `FastMCP` 实例提供的 ASGI 兼容应用。

**(五) 开发 MCP 客户端 (Python SDK)**

SDK 也提供了构建 MCP 客户端（即扮演 Host 角色的一部分）的能力。 

1.  **创建会话 (`ClientSession`):**
    *   需要提供底层的读写流 (Transport)。
    *   可以提供回调函数来处理服务器发起的请求（如 Sampling）。

2.  **连接与初始化:**
    *   **`stdio_client`:** 用于连接通过 `stdio` 启动的服务器进程。返回一个上下文管理器，提供读写流。
    *   **HTTP/SSE 连接:** (需要使用 `httpx` 等库) 手动实现 Streamable HTTP 客户端逻辑，或等待未来 SDK 可能提供的更高级封装。
    *   **`session.initialize()`:** 建立连接后必须调用此方法完成协议握手和能力协商。

3.  **调用服务器功能:**
    *   `session.list_tools()`, `session.list_resources()`, `session.list_prompts()`
    *   `session.call_tool(name, args)`
    *   `session.read_resource(uri)`
    *   `session.get_prompt(name, args)`
    *   `session.add_root()`, `session.remove_root()`, `session.roots_list_changed_notification()` (如果服务器需要根信息)
    *   `session.set_logging_level()`

4.  **处理 Sampling (如果客户端支持):**
    *   在创建 `ClientSession` 时传入 `sampling_callback` 异步函数。
    *   当服务器发送 `sampling/createMessage` 请求时，此回调会被调用。
    *   回调函数需要与 LLM 交互（可能需要用户批准），并返回 `CreateMessageResult`。

```python
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio

async def my_sampling_handler(params: types.CreateMessageRequestParams) -> types.CreateMessageResult:
    print(f"INFO: Received sampling request from server: {params.messages}")
    # !!! 在这里与 LLM 交互，并获取用户批准 !!!
    print("WARN: Skipping LLM call and approval in example.")
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(type="text", text="[Host Simulated LLM Response]"),
        model="simulated-model-v1",
        stopReason="endTurn"
    )

async def run_client():
    server_params = StdioServerParameters(command="/path/to/uv", args=["...", "run", "server.py"], env={...})
    async with stdio_client(server_params) as (reader, writer):
        # 传入 sampling_callback
        async with ClientSession(reader, writer, sampling_callback=my_sampling_handler) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"Client found tools: {[t.name for t in tools.tools]}")
            # ... 调用工具等 ...

if __name__ == "__main__":
    asyncio.run(run_client())
```

**(六) 调试技巧总结**

*   **`mcp dev` + Inspector:** 是调试服务器逻辑的首选。
*   **本地 `uvicorn` + Claude `url` 配置:** 是调试服务器与 Claude Desktop 交互的最佳方式，允许使用 IDE 调试器。
*   **日志:** 在服务器脚本中使用 `print(..., file=sys.stderr)` 或 `ctx.info/error/warning`。日志会出现在 `mcp dev` 的 Inspector 界面或 Claude Desktop 的 `mcp-server-*.log` 文件中。
*   **绝对路径:** 在 `claude_desktop_config.json` 的 `command` 和 `args` 中尽量使用绝对路径，避免因工作目录或 PATH 问题导致找不到命令或文件。
*   **环境变量:** 确保环境变量通过 `claude_desktop_config.json` 的 `env` 块正确传递，或在你手动启动服务器的终端中设置。检查 Python 脚本中读取环境变量的名称是否完全匹配。
*   **依赖管理:** 使用 `pyproject.toml` 定义依赖，确保 `uv run` 能在临时环境中安装它们。如果需要代理访问 PyPI，也要在 `env` 中配置代理。

**(七) 安全与信任**

*   **用户批准:** 调用 **工具 (Tools)** 前**必须**获得用户明确批准，尤其是那些可能修改文件、发送数据或产生费用的工具。UI 设计应清晰展示待执行的操作和参数。 
*   **数据隐私:** Host 应用（如你的智能体）不应在未经用户同意的情况下将用户的私有数据（如通过 Resources 读取的内容）发送给不相关的第三方或 MCP 服务器。 
*   **服务器信任:** 用户和 Host 应用需要判断所连接的 MCP 服务器的可信度。对于通过 `command` 启动的本地服务器，要考虑其执行权限。


**(八) 参考网站**
- https://mcp.so/  mcp服务的收集网站
- https://github.com/modelcontextprotocol/python-sdk mcp python-sdk
- https://modelcontextprotocol.io/tutorials/building-mcp-with-llms 使用大模型快速创建一个mcp 服务
- https://deepwiki.com/ deepwiki 开源项目解读（内部项目不要尝试，解读的项目会存档，公网访问）
- https://deepwiki.com/modelcontextprotocol/python-sdk/2.1-fastmcp-server mcp python-sdk 代码解读内容
- https://claude.ai/download claude 桌面应用下载地址
- https://github.com/luminati-io/brightdata-mcp 