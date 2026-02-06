"""
Agent API Module
================

提供 Agent 的 HTTP API 接口，用于与前端 AI SDK 集成。

接口列表:
- POST /api/agent/chat: 标准对话接口
- POST /api/agent/chat/stream: 流式对话接口
- GET /api/agent/tools: 获取可用工具列表
- GET /api/agent/skills: 获取可用技能列表
- GET /api/agent/status: 获取 Agent 状态

使用示例:
---------
```python
from services.agent.api import router, setup_agent_routes

# FastAPI 集成
app = FastAPI()
setup_agent_routes(app)

# 或直接使用 router
app.include_router(router, prefix="/api/agent")
```
"""

from services.agent.api.schemas import (
    ChatRequest,
    ChatResponse,
    StreamChunk,
    ToolInfo,
    SkillInfo,
    AgentStatusResponse,
)
from services.agent.api.router import router

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "StreamChunk",
    "ToolInfo",
    "SkillInfo",
    "AgentStatusResponse",
    "router",
]
