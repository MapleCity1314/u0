"""
子代理注册表

管理子代理的注册、发现和调度。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type, Union

from services.agent.sub_agents.base import (
    SubAgent,
    SubAgentContext,
    SubAgentResult,
    SubAgentRole,
)

logger = logging.getLogger(__name__)


class SubAgentRegistry:
    """
    子代理注册表

    集中管理所有可用子代理，提供注册、发现、调度能力。

    示例:
    ------
    ```python
    registry = SubAgentRegistry()

    # 注册子代理类
    registry.register(ResearcherAgent)

    # 注册子代理实例
    registry.register(my_agent_instance)

    # 列出所有子代理
    agents = registry.list_agents()

    # 调度子代理
    ctx = SubAgentContext(user_id="xxx", task="分析市场")
    result = await registry.dispatch("researcher", ctx)
    ```
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._agents: Dict[str, SubAgent] = {}
        self._roles: Dict[SubAgentRole, List[str]] = {
            role: [] for role in SubAgentRole
        }

    def register(
        self,
        agent: Union[Type[SubAgent], SubAgent],
        **kwargs,
    ) -> "SubAgentRegistry":
        """
        注册子代理

        支持多种注册方式：
        - SubAgent 类
        - SubAgent 实例

        Args:
            agent: 要注册的子代理
            **kwargs: 传递给子代理构造函数的额外参数

        Returns:
            self，支持链式调用

        Raises:
            ValueError: 子代理名称重复或无效
        """
        agent_instance: SubAgent

        # 处理不同类型的输入
        if isinstance(agent, type) and issubclass(agent, SubAgent):
            # SubAgent 类
            agent_instance = agent(**kwargs)
        elif isinstance(agent, SubAgent):
            # SubAgent 实例
            agent_instance = agent
        else:
            raise ValueError(f"Invalid agent type: {type(agent)}")

        # 验证子代理名称
        if not agent_instance.name:
            raise ValueError("SubAgent name cannot be empty")

        # 检查重复注册
        if agent_instance.name in self._agents:
            logger.warning(
                f"SubAgent '{agent_instance.name}' already registered, overwriting"
            )

        # 注册子代理
        self._agents[agent_instance.name] = agent_instance

        # 更新角色索引
        role = agent_instance.role
        if agent_instance.name not in self._roles[role]:
            self._roles[role].append(agent_instance.name)

        logger.debug(f"Registered sub-agent: {agent_instance.name}")
        return self

    def register_many(
        self,
        agents: List[Union[Type[SubAgent], SubAgent]],
    ) -> "SubAgentRegistry":
        """
        批量注册子代理

        Args:
            agents: 子代理列表

        Returns:
            self，支持链式调用
        """
        for agent in agents:
            self.register(agent)
        return self

    def unregister(self, name: str) -> bool:
        """
        取消注册子代理

        Args:
            name: 子代理名称

        Returns:
            是否成功取消注册
        """
        if name not in self._agents:
            return False

        agent = self._agents.pop(name)

        # 从角色索引中移除
        if name in self._roles[agent.role]:
            self._roles[agent.role].remove(name)

        logger.debug(f"Unregistered sub-agent: {name}")
        return True

    def get(self, name: str) -> Optional[SubAgent]:
        """
        获取子代理

        Args:
            name: 子代理名称

        Returns:
            子代理实例，如果不存在则返回 None
        """
        return self._agents.get(name)

    def has(self, name: str) -> bool:
        """
        检查子代理是否存在

        Args:
            name: 子代理名称

        Returns:
            子代理是否存在
        """
        return name in self._agents

    def list_agents(
        self,
        role: Optional[SubAgentRole] = None,
    ) -> List[SubAgent]:
        """
        列出子代理

        Args:
            role: 按角色过滤

        Returns:
            子代理列表
        """
        agents = list(self._agents.values())

        # 按角色过滤
        if role is not None:
            agents = [a for a in agents if a.role == role]

        return agents

    def list_agent_names(
        self,
        role: Optional[SubAgentRole] = None,
    ) -> List[str]:
        """
        列出子代理名称

        Args:
            role: 按角色过滤

        Returns:
            子代理名称列表
        """
        if role is not None:
            return self._roles[role].copy()
        return list(self._agents.keys())

    def get_agent_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取子代理信息

        Args:
            name: 子代理名称

        Returns:
            子代理信息字典
        """
        agent = self.get(name)
        if agent is None:
            return None

        return {
            "name": agent.name,
            "role": agent.role.value,
            "description": agent.description,
            "skills": agent.skills,
            "tools": agent.tools,
            "max_iterations": agent.max_iterations,
            "max_tool_calls": agent.max_tool_calls,
            "timeout": agent.timeout,
        }

    def list_agent_info(
        self,
        role: Optional[SubAgentRole] = None,
    ) -> List[Dict[str, Any]]:
        """
        列出所有子代理的信息

        Args:
            role: 按角色过滤

        Returns:
            子代理信息列表
        """
        agents = self.list_agents(role=role)
        return [
            self.get_agent_info(a.name)
            for a in agents
            if self.get_agent_info(a.name)
        ]

    def get_agents_by_role(self, role: SubAgentRole) -> List[SubAgent]:
        """
        按角色获取子代理

        Args:
            role: 子代理角色

        Returns:
            该角色的子代理列表
        """
        return [
            self._agents[name]
            for name in self._roles[role]
            if name in self._agents
        ]

    async def dispatch(
        self,
        name: str,
        ctx: Optional[SubAgentContext] = None,
        task: Optional[str] = None,
        **kwargs,
    ) -> SubAgentResult:
        """
        调度子代理执行任务

        Args:
            name: 子代理名称
            ctx: 子代理执行上下文
            task: 任务描述（如果 ctx 中没有设置）
            **kwargs: 额外参数

        Returns:
            子代理执行结果

        Raises:
            ValueError: 子代理不存在
        """
        agent = self.get(name)
        if agent is None:
            return SubAgentResult(
                agent_name=name,
                task_id="",
                success=False,
                error=f"SubAgent not found: {name}",
            )

        # 创建默认上下文
        if ctx is None:
            ctx = SubAgentContext()

        # 设置任务
        if task:
            ctx.task = task
        elif not ctx.task:
            return SubAgentResult(
                agent_name=name,
                task_id=ctx.task_id,
                success=False,
                error="No task specified",
            )

        # 注入工具注册表和 LLM
        if ctx.tool_registry is None:
            try:
                from services.agent.tools.registry import get_default_registry
                ctx.tool_registry = get_default_registry()
            except ImportError:
                logger.warning("Tool registry not available")

        if ctx.llm is None:
            try:
                from services.agent.llm.factory import create_llm_from_env
                ctx.llm = create_llm_from_env()
            except Exception as e:
                logger.warning(f"Failed to create LLM: {e}")

        # 合并额外参数
        for key, value in kwargs.items():
            ctx.set(key, value)

        logger.info(f"Dispatching task to sub-agent: {name}")

        return await agent(ctx)

    async def dispatch_by_role(
        self,
        role: SubAgentRole,
        ctx: Optional[SubAgentContext] = None,
        task: Optional[str] = None,
        **kwargs,
    ) -> SubAgentResult:
        """
        按角色调度子代理

        如果该角色有多个子代理，选择第一个。

        Args:
            role: 子代理角色
            ctx: 子代理执行上下文
            task: 任务描述
            **kwargs: 额外参数

        Returns:
            子代理执行结果
        """
        agents = self.get_agents_by_role(role)
        if not agents:
            return SubAgentResult(
                agent_name=f"[{role.value}]",
                task_id="",
                success=False,
                error=f"No agent found for role: {role.value}",
            )

        # 选择第一个可用的子代理
        return await self.dispatch(agents[0].name, ctx, task, **kwargs)

    async def dispatch_many(
        self,
        calls: List[Dict[str, Any]],
        ctx: Optional[SubAgentContext] = None,
        parallel: bool = False,
    ) -> List[SubAgentResult]:
        """
        批量调度子代理

        Args:
            calls: 调用列表，每项包含 name, task 和可选的 kwargs
            ctx: 子代理执行上下文
            parallel: 是否并行执行

        Returns:
            子代理执行结果列表
        """
        if ctx is None:
            ctx = SubAgentContext()

        if parallel:
            # 并行执行
            tasks = [
                self.dispatch(
                    name=call["name"],
                    ctx=SubAgentContext(
                        user_id=ctx.user_id,
                        session_id=ctx.session_id,
                        task=call.get("task", ""),
                        tool_registry=ctx.tool_registry,
                        llm=ctx.llm,
                        metadata=call.get("kwargs", {}),
                    ),
                )
                for call in calls
            ]
            return await asyncio.gather(*tasks)
        else:
            # 串行执行
            results = []
            for call in calls:
                result = await self.dispatch(
                    name=call["name"],
                    ctx=SubAgentContext(
                        user_id=ctx.user_id,
                        session_id=ctx.session_id,
                        task=call.get("task", ""),
                        tool_registry=ctx.tool_registry,
                        llm=ctx.llm,
                        metadata=call.get("kwargs", {}),
                    ),
                )
                results.append(result)
            return results

    def clear(self) -> None:
        """清空所有注册的子代理"""
        self._agents.clear()
        self._roles = {role: [] for role in SubAgentRole}
        logger.debug("Cleared all sub-agents from registry")

    def merge(self, other: "SubAgentRegistry") -> "SubAgentRegistry":
        """
        合并另一个注册表

        Args:
            other: 要合并的注册表

        Returns:
            self，支持链式调用
        """
        for agent in other._agents.values():
            self.register(agent)
        return self

    def __len__(self) -> int:
        """返回注册的子代理数量"""
        return len(self._agents)

    def __contains__(self, name: str) -> bool:
        """检查子代理是否存在"""
        return name in self._agents

    def __iter__(self):
        """迭代所有子代理"""
        return iter(self._agents.values())

    def __repr__(self) -> str:
        return f"SubAgentRegistry(name={self.name!r}, agents={len(self._agents)})"


# 默认注册表实例
_default_registry: Optional[SubAgentRegistry] = None


def get_default_sub_agent_registry() -> SubAgentRegistry:
    """
    获取默认子代理注册表

    Returns:
        默认子代理注册表
    """
    global _default_registry

    if _default_registry is None:
        _default_registry = SubAgentRegistry(name="default")

    return _default_registry


def reset_default_sub_agent_registry() -> None:
    """重置默认注册表（用于测试）"""
    global _default_registry
    _default_registry = None


def create_sub_agent_registry(
    name: str = "custom",
    include_default: bool = False,
) -> SubAgentRegistry:
    """
    创建新的子代理注册表

    Args:
        name: 注册表名称
        include_default: 是否包含默认注册表的子代理

    Returns:
        新的子代理注册表
    """
    registry = SubAgentRegistry(name=name)

    if include_default:
        default = get_default_sub_agent_registry()
        registry.merge(default)

    return registry
