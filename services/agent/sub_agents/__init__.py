"""
Agent SubAgents Module
======================

子代理模块，提供专门化的子代理用于处理特定领域任务。

子代理是具有特定角色和能力的 Agent 实例，可以被主 Agent 调度执行特定任务。
每个子代理有自己的系统提示、技能集和工具集。

子代理类型:
- ResearcherAgent: 研究员代理，负责信息收集和整理
- AnalystAgent: 分析师代理，负责数据分析和洞察
- AdvisorAgent: 顾问代理，负责生成投资建议

使用示例:
---------
```python
from services.agent.sub_agents import SubAgent, SubAgentRegistry

# 定义子代理
class MySubAgent(SubAgent):
    name = "my_sub_agent"
    description = "子代理描述"
    role = "专家角色"

    system_prompt = '''
    你是一个专业的...
    '''

    skills = ["skill1", "skill2"]
    tools = ["tool1", "tool2"]

    async def process(self, task: str, context: dict) -> str:
        # 处理任务
        return result

# 注册子代理
registry = SubAgentRegistry()
registry.register(MySubAgent)

# 调度子代理
result = await registry.dispatch("my_sub_agent", task="...", context={...})
```
"""

from services.agent.sub_agents.base import (
    SubAgent,
    SubAgentContext,
    SubAgentResult,
    SubAgentRole,
)
from services.agent.sub_agents.registry import (
    SubAgentRegistry,
    get_default_sub_agent_registry,
)

# 预定义的子代理
# from services.agent.sub_agents.researcher import ResearcherAgent
# from services.agent.sub_agents.analyst import AnalystAgent
# from services.agent.sub_agents.advisor import AdvisorAgent

__all__ = [
    # 基类
    "SubAgent",
    "SubAgentContext",
    "SubAgentResult",
    "SubAgentRole",
    # 注册表
    "SubAgentRegistry",
    "get_default_sub_agent_registry",
    # 预定义子代理（待实现）
    # "ResearcherAgent",
    # "AnalystAgent",
    # "AdvisorAgent",
]
