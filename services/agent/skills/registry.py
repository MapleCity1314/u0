"""
技能注册表

管理技能的注册、发现和执行。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type, Union

from services.agent.skills.base import (
    Skill,
    SkillContext,
    SkillResult,
)

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    技能注册表

    集中管理所有可用技能，提供注册、发现、执行能力。

    示例:
    ------
    ```python
    registry = SkillRegistry()

    # 注册技能类
    registry.register(PortfolioAnalysisSkill)

    # 注册技能实例
    registry.register(my_skill_instance)

    # 列出所有技能
    skills = registry.list_skills()

    # 执行技能
    ctx = SkillContext(user_id="xxx")
    result = await registry.execute("portfolio_analysis", ctx)
    ```
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._skills: Dict[str, Skill] = {}
        self._tags: Dict[str, List[str]] = {}

    def register(
        self,
        skill: Union[Type[Skill], Skill],
        **kwargs,
    ) -> "SkillRegistry":
        """
        注册技能

        支持多种注册方式：
        - Skill 类
        - Skill 实例

        Args:
            skill: 要注册的技能
            **kwargs: 传递给技能构造函数的额外参数

        Returns:
            self，支持链式调用

        Raises:
            ValueError: 技能名称重复或无效
        """
        skill_instance: Skill

        # 处理不同类型的输入
        if isinstance(skill, type) and issubclass(skill, Skill):
            # Skill 类
            skill_instance = skill(**kwargs)
        elif isinstance(skill, Skill):
            # Skill 实例
            skill_instance = skill
        else:
            raise ValueError(f"Invalid skill type: {type(skill)}")

        # 验证技能名称
        if not skill_instance.name:
            raise ValueError("Skill name cannot be empty")

        # 检查重复注册
        if skill_instance.name in self._skills:
            logger.warning(
                f"Skill '{skill_instance.name}' already registered, overwriting"
            )

        # 注册技能
        self._skills[skill_instance.name] = skill_instance

        # 更新标签索引
        for tag in skill_instance.tags:
            if tag not in self._tags:
                self._tags[tag] = []
            if skill_instance.name not in self._tags[tag]:
                self._tags[tag].append(skill_instance.name)

        logger.debug(f"Registered skill: {skill_instance.name}")
        return self

    def register_many(
        self,
        skills: List[Union[Type[Skill], Skill]],
    ) -> "SkillRegistry":
        """
        批量注册技能

        Args:
            skills: 技能列表

        Returns:
            self，支持链式调用
        """
        for skill in skills:
            self.register(skill)
        return self

    def unregister(self, name: str) -> bool:
        """
        取消注册技能

        Args:
            name: 技能名称

        Returns:
            是否成功取消注册
        """
        if name not in self._skills:
            return False

        skill = self._skills.pop(name)

        # 从标签索引中移除
        for tag in skill.tags:
            if tag in self._tags and name in self._tags[tag]:
                self._tags[tag].remove(name)

        logger.debug(f"Unregistered skill: {name}")
        return True

    def get(self, name: str) -> Optional[Skill]:
        """
        获取技能

        Args:
            name: 技能名称

        Returns:
            技能实例，如果不存在则返回 None
        """
        return self._skills.get(name)

    def has(self, name: str) -> bool:
        """
        检查技能是否存在

        Args:
            name: 技能名称

        Returns:
            技能是否存在
        """
        return name in self._skills

    def list_skills(
        self,
        tags: Optional[List[str]] = None,
    ) -> List[Skill]:
        """
        列出技能

        Args:
            tags: 按标签过滤（任一匹配）

        Returns:
            技能列表
        """
        skills = list(self._skills.values())

        # 按标签过滤
        if tags:
            skills = [
                s for s in skills
                if any(tag in s.tags for tag in tags)
            ]

        return skills

    def list_skill_names(
        self,
        tags: Optional[List[str]] = None,
    ) -> List[str]:
        """
        列出技能名称

        Args:
            tags: 按标签过滤

        Returns:
            技能名称列表
        """
        if tags:
            names = set()
            for tag in tags:
                if tag in self._tags:
                    names.update(self._tags[tag])
            return list(names)
        return list(self._skills.keys())

    def get_skill_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取技能信息

        Args:
            name: 技能名称

        Returns:
            技能信息字典
        """
        skill = self.get(name)
        if skill is None:
            return None

        return {
            "name": skill.name,
            "description": skill.description,
            "required_tools": skill.required_tools,
            "optional_tools": skill.optional_tools,
            "tags": skill.tags,
            "timeout": skill.timeout,
            "max_tool_calls": skill.max_tool_calls,
        }

    def list_skill_info(
        self,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        列出所有技能的信息

        Args:
            tags: 按标签过滤

        Returns:
            技能信息列表
        """
        skills = self.list_skills(tags=tags)
        return [self.get_skill_info(s.name) for s in skills if self.get_skill_info(s.name)]

    async def execute(
        self,
        name: str,
        ctx: Optional[SkillContext] = None,
        **kwargs,
    ) -> SkillResult:
        """
        执行技能

        Args:
            name: 技能名称
            ctx: 技能执行上下文
            **kwargs: 技能参数

        Returns:
            技能执行结果

        Raises:
            ValueError: 技能不存在
        """
        skill = self.get(name)
        if skill is None:
            return SkillResult(
                skill_name=name,
                success=False,
                error=f"Skill not found: {name}",
            )

        # 创建默认上下文
        if ctx is None:
            ctx = SkillContext()

        # 注入工具注册表
        if ctx.tool_registry is None:
            try:
                from services.agent.tools.registry import get_default_registry
                ctx.tool_registry = get_default_registry()
            except ImportError:
                logger.warning("Tool registry not available")

        logger.debug(f"Executing skill: {name} with kwargs: {kwargs}")

        return await skill(ctx, **kwargs)

    async def execute_many(
        self,
        calls: List[Dict[str, Any]],
        ctx: Optional[SkillContext] = None,
        parallel: bool = False,
    ) -> List[SkillResult]:
        """
        批量执行技能

        Args:
            calls: 调用列表，每项包含 name 和可选的 kwargs
            ctx: 技能执行上下文
            parallel: 是否并行执行

        Returns:
            技能执行结果列表
        """
        if ctx is None:
            ctx = SkillContext()

        if parallel:
            # 并行执行
            tasks = [
                self.execute(
                    name=call["name"],
                    ctx=ctx,
                    **call.get("kwargs", {}),
                )
                for call in calls
            ]
            return await asyncio.gather(*tasks)
        else:
            # 串行执行
            results = []
            for call in calls:
                result = await self.execute(
                    name=call["name"],
                    ctx=ctx,
                    **call.get("kwargs", {}),
                )
                results.append(result)
            return results

    def clear(self) -> None:
        """清空所有注册的技能"""
        self._skills.clear()
        self._tags.clear()
        logger.debug("Cleared all skills from registry")

    def merge(self, other: "SkillRegistry") -> "SkillRegistry":
        """
        合并另一个注册表

        Args:
            other: 要合并的注册表

        Returns:
            self，支持链式调用
        """
        for skill in other._skills.values():
            self.register(skill)
        return self

    def __len__(self) -> int:
        """返回注册的技能数量"""
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        """检查技能是否存在"""
        return name in self._skills

    def __iter__(self):
        """迭代所有技能"""
        return iter(self._skills.values())

    def __repr__(self) -> str:
        return f"SkillRegistry(name={self.name!r}, skills={len(self._skills)})"


# 默认注册表实例
_default_registry: Optional[SkillRegistry] = None


def get_default_skill_registry() -> SkillRegistry:
    """
    获取默认技能注册表

    Returns:
        默认技能注册表
    """
    global _default_registry

    if _default_registry is None:
        _default_registry = SkillRegistry(name="default")

    return _default_registry


def reset_default_skill_registry() -> None:
    """重置默认注册表（用于测试）"""
    global _default_registry
    _default_registry = None


def create_skill_registry(
    name: str = "custom",
    include_default: bool = False,
) -> SkillRegistry:
    """
    创建新的技能注册表

    Args:
        name: 注册表名称
        include_default: 是否包含默认注册表的技能

    Returns:
        新的技能注册表
    """
    registry = SkillRegistry(name=name)

    if include_default:
        default = get_default_skill_registry()
        registry.merge(default)

    return registry
