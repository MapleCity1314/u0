"""
Agent Tools Module
==================

工具系统，提供 Agent 可调用的原子操作。

工具分类:
- system: 系统集成工具（持仓、基金、新闻等）
- web: 网络工具（搜索、抓取、提取）
- analysis: 分析工具（计算、图表）

使用示例:
---------
```python
from services.agent.tools import tool, Tool, ToolRegistry

# 使用装饰器定义工具
@tool(
    name="my_tool",
    description="工具描述",
)
async def my_tool(param: str) -> str:
    return f"Result: {param}"

# 获取工具注册表
registry = ToolRegistry()
registry.register(my_tool)

# 列出所有工具
tools = registry.list_tools()

# 调用工具
result = await registry.call("my_tool", param="test")
```
"""

from services.agent.tools.base import (
    Tool,
    ToolResult,
    tool,
)
from services.agent.tools.registry import ToolRegistry, get_default_registry

__all__ = [
    "Tool",
    "ToolResult",
    "tool",
    "ToolRegistry",
    "get_default_registry",
]
