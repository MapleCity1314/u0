"""
U0 Agent Module
===============

智能代理系统，提供模块化、可扩展的 AI Agent 架构。

主要组件:
- Agent: 主代理引擎
- AgentConfig: 代理配置
- Tool: 工具基类
- Skill: 技能基类
- SubAgent: 子代理基类

快速开始:
---------
```python
from services.agent import Agent, AgentConfig

config = AgentConfig(
    llm_provider="openai",
    llm_model="gpt-4o-mini",
)

agent = Agent(config)
response = await agent.chat(
    messages=[{"role": "user", "content": "你好"}],
    user_id="user-123",
)
```
"""

from services.agent.config import AgentConfig
from services.agent.core.agent import Agent
from services.agent.core.state import AgentState
from services.agent.tools.base import Tool, tool
from services.agent.skills.base import Skill
from services.agent.sub_agents.base import SubAgent

__version__ = "0.1.0"

__all__ = [
    # 核心
    "Agent",
    "AgentConfig",
    "AgentState",
    # 工具
    "Tool",
    "tool",
    # 技能
    "Skill",
    # 子代理
    "SubAgent",
]
