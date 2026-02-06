"""
MCP (Model Context Protocol) Module - v0.2
===========================================

实现 Model Context Protocol，为 Agent 提供与外部资源交互的标准化接口。

MCP 协议概述
-----------
MCP 是 Anthropic 提出的用于 AI Agent 与外部系统交互的标准协议。
它定义了以下核心概念：

1. **Resources（资源）**
   - 提供上下文数据给 LLM
   - 如：用户持仓、基金数据、市场信息等
   - 支持订阅机制，实时更新

2. **Tools（工具）**
   - 允许 LLM 执行操作
   - 与 Agent Tools 模块无缝集成
   - 标准化的工具定义和调用接口

3. **Prompts（提示模板）**
   - 动态生成的提示模板
   - 支持参数化和上下文注入
   - 可重用的提示片段

4. **Sampling（采样）**
   - 请求 LLM 完成特定任务
   - 支持多轮对话和工具调用
   - 模型偏好设置

模块结构
--------
```
mcp/
├── __init__.py              # 本文件
├── protocol.py              # MCP 协议核心定义 ✅
├── server.py                # MCP 服务端实现
├── client.py                # MCP 客户端实现
├── resources/               # 资源提供者
│   ├── __init__.py
│   ├── base.py              # 资源基类
│   ├── position.py          # 持仓资源
│   ├── fund.py              # 基金资源
│   └── news.py              # 新闻资源
└── transports/              # 传输层
    ├── __init__.py
    ├── stdio.py             # 标准 I/O 传输
    ├── http.py              # HTTP/SSE 传输
    └── websocket.py         # WebSocket 传输
```

v0.2 实现状态
-------------
✅ 已完成：
- MCP 协议核心定义 (protocol.py)
- 消息类型和数据结构
- Resources、Tools、Prompts、Sampling 数据模型
- 错误处理机制

🚧 进行中：
- MCP 服务端实现 (server.py)
- MCP 客户端实现 (client.py)
- 资源提供者实现
- 传输层实现

📅 计划中：
- 完整的订阅机制
- 双向流式通信
- 高级错误恢复

使用示例
--------
```python
from services.agent.mcp import MCPServer, MCPResource, MCPTool
from services.agent.mcp.resources import PositionResourceProvider

# 创建 MCP 服务器
server = MCPServer(
    name="U0 Agent MCP Server",
    version="0.2.0",
)

# 注册资源提供者
server.register_resource_provider(PositionResourceProvider())

# 注册工具（自动从 Agent Tools 注册表导入）
server.auto_register_tools()

# 启动服务器
await server.start(transport="http", port=3001)

# 客户端使用
from services.agent.mcp import MCPClient

client = MCPClient(url="http://localhost:3001")
await client.connect()

# 列出资源
resources = await client.list_resources()

# 读取资源
content = await client.read_resource("user://positions")

# 调用工具
result = await client.call_tool("search_funds", {"query": "AI"})

# 获取提示模板
prompt = await client.get_prompt("analyze_portfolio", {"user_id": "xxx"})
```

与 Agent 集成
------------
MCP 服务器可以作为 Agent 的扩展，提供标准化的资源访问接口：

```python
from services.agent import Agent
from services.agent.mcp import MCPServer

# 创建 Agent
agent = Agent()

# 启动 MCP 服务器（可选）
mcp_server = MCPServer.from_agent(agent)
await mcp_server.start()

# Agent 现在可以通过 MCP 协议被外部系统访问
# 包括 Claude Desktop、其他 AI 应用等
```

参考资料
--------
- MCP 规范: https://modelcontextprotocol.io/
- Anthropic MCP SDK: https://github.com/anthropics/mcp
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
"""

from typing import TYPE_CHECKING

# 版本信息
__version__ = "0.2.0"
__status__ = "in_progress"

# 导出核心协议类型
from services.agent.mcp.protocol import (
    # 消息类型
    MCPMessage,
    MCPRequest,
    MCPResponse,
    MCPNotification,
    MCPError,

    # 资源
    MCPResource,
    MCPResourceContent,

    # 工具
    MCPTool,
    MCPToolParameter,
    MCPToolCall,
    MCPToolResult,

    # 提示
    MCPPrompt,
    MCPPromptArgument,
    MCPPromptMessage,

    # 采样
    MCPSamplingRequest,

    # 进度
    MCPProgress,

    # 能力
    MCPServerCapabilities,
    MCPClientCapabilities,

    # 初始化
    MCPInitializeParams,
    MCPInitializeResult,

    # 枚举
    MCPMessageType,
    MCPErrorCode,

    # 常量
    MCP_VERSION,
    MCP_PROTOCOL_VERSION,

    # 辅助函数
    create_request,
    create_response,
    create_notification,
    create_error_response,
)

# 服务端和客户端（待实现）
# from services.agent.mcp.server import MCPServer
# from services.agent.mcp.client import MCPClient

# 资源提供者（待实现）
# from services.agent.mcp.resources import (
#     ResourceProvider,
#     PositionResourceProvider,
#     FundResourceProvider,
#     NewsResourceProvider,
# )

# 传输层（待实现）
# from services.agent.mcp.transports import (
#     Transport,
#     StdioTransport,
#     HttpTransport,
#     WebSocketTransport,
# )

__all__ = [
    # 版本
    "__version__",
    "__status__",

    # 协议常量
    "MCP_VERSION",
    "MCP_PROTOCOL_VERSION",

    # 枚举
    "MCPMessageType",
    "MCPErrorCode",

    # 消息
    "MCPMessage",
    "MCPRequest",
    "MCPResponse",
    "MCPNotification",
    "MCPError",

    # 资源
    "MCPResource",
    "MCPResourceContent",

    # 工具
    "MCPTool",
    "MCPToolParameter",
    "MCPToolCall",
    "MCPToolResult",

    # 提示
    "MCPPrompt",
    "MCPPromptArgument",
    "MCPPromptMessage",

    # 采样
    "MCPSamplingRequest",

    # 其他
    "MCPProgress",
    "MCPServerCapabilities",
    "MCPClientCapabilities",
    "MCPInitializeParams",
    "MCPInitializeResult",

    # 辅助函数
    "create_request",
    "create_response",
    "create_notification",
    "create_error_response",

    # 服务端/客户端（v0.3）
    # "MCPServer",
    # "MCPClient",

    # 资源提供者（v0.3）
    # "ResourceProvider",
    # "PositionResourceProvider",
    # "FundResourceProvider",
    # "NewsResourceProvider",

    # 传输层（v0.3）
    # "Transport",
    # "StdioTransport",
    # "HttpTransport",
    # "WebSocketTransport",
]


def get_implementation_status() -> dict:
    """
    获取 MCP 模块的实现状态

    Returns:
        实现状态字典
    """
    return {
        "version": __version__,
        "status": __status__,
        "protocol": {
            "implemented": True,
            "version": MCP_PROTOCOL_VERSION,
        },
        "server": {
            "implemented": False,
            "planned_version": "0.3.0",
        },
        "client": {
            "implemented": False,
            "planned_version": "0.3.0",
        },
        "resources": {
            "implemented": False,
            "planned_version": "0.3.0",
        },
        "transports": {
            "stdio": {"implemented": False, "planned_version": "0.3.0"},
            "http": {"implemented": False, "planned_version": "0.3.0"},
            "websocket": {"implemented": False, "planned_version": "0.3.0"},
        },
    }


def print_status() -> None:
    """打印 MCP 模块实现状态"""
    import json
    status = get_implementation_status()
    print("MCP Module Implementation Status:")
    print(json.dumps(status, indent=2))


# 开发提示
_DEVELOPMENT_NOTE = """
MCP v0.2 Development Status
===========================

已完成 ✅:
- 完整的 MCP 协议定义 (protocol.py)
- 所有核心数据结构和消息类型
- JSON-RPC 2.0 兼容的消息格式

待实现 🚧:
1. MCPServer - MCP 服务端实现
   - 资源管理和订阅
   - 工具注册和执行
   - 提示模板管理
   - 采样请求处理

2. MCPClient - MCP 客户端实现
   - 连接管理
   - 请求/响应处理
   - 流式通信支持

3. ResourceProvider - 资源提供者
   - PositionResourceProvider - 持仓资源
   - FundResourceProvider - 基金资源
   - NewsResourceProvider - 新闻资源

4. Transport Layer - 传输层
   - StdioTransport - 标准 I/O (Claude Desktop)
   - HttpTransport - HTTP/SSE
   - WebSocketTransport - WebSocket

参与开发:
请参考 protocol.py 中的数据结构和注释
按照 MCP 规范实现相应的服务端/客户端功能
"""
