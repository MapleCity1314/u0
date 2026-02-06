"""
Agent Skills Module
===================

技能模块，封装 Agent 的高级能力单元。

技能是多个工具的组合，提供更高级的功能抽象。

技能分类:
- portfolio: 持仓分析技能
- research: 研究分析技能
- web: 网络搜索技能

使用示例:
---------
```python
from services.agent.skills import Skill, SkillRegistry

# 定义技能
class MySkill(Skill):
    name = "my_skill"
    description = "技能描述"

    async def execute(self, context: dict) -> str:
        # 使用工具
        result = await self.use_tool("tool_name", param="value")
        return self.format_response(result)

# 注册技能
registry = SkillRegistry()
registry.register(MySkill)

# 执行技能
result = await registry.execute("my_skill", context={...})
```
"""

from services.agent.skills.base import (
    Skill,
    SkillContext,
    SkillResult,
)
from services.agent.skills.registry import (
    SkillRegistry,
    get_default_skill_registry,
)

__all__ = [
    "Skill",
    "SkillContext",
    "SkillResult",
    "SkillRegistry",
    "get_default_skill_registry",
]
