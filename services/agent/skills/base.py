"""
技能基类

技能是 Agent 的核心能力单元，封装一组相关的功能。
每个技能可以调用多个工具，并组合它们的结果来完成复杂任务。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from services.agent.tools.registry import ToolRegistry
    from services.agent.tools.base import ToolContext, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class SkillContext:
    """
    技能执行上下文

    包含技能执行所需的所有上下文信息。
    """
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # 运行时填充
    tool_registry: Optional["ToolRegistry"] = None

    def get(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        return self.metadata.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置元数据"""
        self.metadata[key] = value


@dataclass
class SkillResult:
    """技能执行结果"""
    skill_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        data = {
            "skill_name": self.skill_name,
            "success": self.success,
        }
        if self.result is not None:
            data["result"] = self.result
        if self.error:
            data["error"] = self.error
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.duration_ms is not None:
            data["duration_ms"] = self.duration_ms
        if self.metadata:
            data["metadata"] = self.metadata
        return data

    def to_string(self) -> str:
        """转换为字符串（用于传回 LLM）"""
        if not self.success:
            return f"技能执行失败: {self.error}"
        if isinstance(self.result, (dict, list)):
            import json
            return json.dumps(self.result, ensure_ascii=False, indent=2)
        return str(self.result)


class Skill(ABC):
    """
    技能基类

    所有技能都应该继承此类并实现 execute 方法。
    技能可以调用多个工具并组合结果。

    示例:
    ------
    ```python
    class PortfolioAnalysisSkill(Skill):
        name = "portfolio_analysis"
        description = "分析用户的投资组合，提供持仓概况和收益分析"
        required_tools = ["get_positions", "get_fund_nav"]

        async def execute(self, ctx: SkillContext, **kwargs) -> Any:
            # 获取持仓
            positions = await self.use_tool("get_positions")

            # 获取每个持仓的最新净值
            nav_data = []
            for pos in positions.get("positions", []):
                nav = await self.use_tool("get_fund_nav", fund_code=pos["code"])
                nav_data.append(nav)

            # 组合分析结果
            return self.analyze(positions, nav_data)
    ```
    """

    # 技能元数据（子类应覆盖）
    name: str = ""
    description: str = ""
    required_tools: list[str] = []
    optional_tools: list[str] = []
    tags: list[str] = []

    # 技能配置
    timeout: int = 60  # 执行超时（秒）
    max_tool_calls: int = 10  # 单次执行最大工具调用数

    def __init__(self):
        if not self.name:
            # 使用类名作为默认名称
            self.name = self._camel_to_snake(self.__class__.__name__)

        # 运行时状态
        self._ctx: Optional[SkillContext] = None
        self._tool_call_count: int = 0
        self._tool_calls: list[dict[str, Any]] = []

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """将 CamelCase 转换为 snake_case"""
        import re
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        if name.endswith("_skill"):
            name = name[:-6]
        return name

    @property
    def ctx(self) -> SkillContext:
        """获取当前执行上下文"""
        if self._ctx is None:
            raise RuntimeError("Skill not initialized. Call skill within proper context.")
        return self._ctx

    def _get_tool_context(self) -> "ToolContext":
        """创建工具执行上下文"""
        from services.agent.tools.base import ToolContext
        return ToolContext(
            user_id=self.ctx.user_id,
            session_id=self.ctx.session_id,
            metadata=self.ctx.metadata,
        )

    async def use_tool(self, tool_name: str, **kwargs) -> Any:
        """
        调用工具

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            工具执行结果

        Raises:
            RuntimeError: 工具调用次数超限或工具不存在
        """
        if self._tool_call_count >= self.max_tool_calls:
            raise RuntimeError(
                f"Tool call limit exceeded ({self.max_tool_calls})"
            )

        if self.ctx.tool_registry is None:
            raise RuntimeError("Tool registry not available")

        if not self.ctx.tool_registry.has(tool_name):
            raise RuntimeError(f"Tool not found: {tool_name}")

        self._tool_call_count += 1
        tool_call_id = str(uuid4())

        logger.debug(f"Skill {self.name} calling tool {tool_name}: {kwargs}")

        # 执行工具
        tool_ctx = self._get_tool_context()
        result = await self.ctx.tool_registry.call(
            name=tool_name,
            ctx=tool_ctx,
            tool_call_id=tool_call_id,
            **kwargs,
        )

        # 记录工具调用
        self._tool_calls.append({
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "arguments": kwargs,
            "success": result.success,
            "duration_ms": result.duration_ms,
        })

        if not result.success:
            logger.warning(f"Tool {tool_name} failed: {result.error}")
            return {"error": result.error}

        # 解析结果
        if isinstance(result.result, str):
            try:
                import json
                return json.loads(result.result)
            except (json.JSONDecodeError, TypeError):
                return result.result
        return result.result

    async def use_tools_parallel(
        self,
        calls: list[tuple[str, dict[str, Any]]],
    ) -> list[Any]:
        """
        并行调用多个工具

        Args:
            calls: 工具调用列表，每项为 (tool_name, kwargs) 元组

        Returns:
            结果列表，顺序与输入对应
        """
        import asyncio

        tasks = [
            self.use_tool(tool_name, **kwargs)
            for tool_name, kwargs in calls
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def validate_tools(self) -> bool:
        """
        验证所需工具是否可用

        Returns:
            所有必需工具是否都可用
        """
        if self.ctx.tool_registry is None:
            return False

        for tool_name in self.required_tools:
            if not self.ctx.tool_registry.has(tool_name):
                logger.warning(
                    f"Skill {self.name} missing required tool: {tool_name}"
                )
                return False
        return True

    @abstractmethod
    async def execute(self, ctx: SkillContext, **kwargs) -> Any:
        """
        执行技能

        Args:
            ctx: 技能执行上下文
            **kwargs: 技能参数

        Returns:
            技能执行结果
        """
        pass

    async def __call__(
        self,
        ctx: SkillContext,
        **kwargs,
    ) -> SkillResult:
        """
        调用技能并返回结果

        Args:
            ctx: 技能执行上下文
            **kwargs: 技能参数

        Returns:
            技能执行结果
        """
        self._ctx = ctx
        self._tool_call_count = 0
        self._tool_calls = []

        start_time = datetime.now(timezone.utc)

        try:
            # 验证工具
            if not self.validate_tools():
                return SkillResult(
                    skill_name=self.name,
                    success=False,
                    error="Required tools not available",
                )

            # 执行技能
            result = await self.execute(ctx, **kwargs)

            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000

            return SkillResult(
                skill_name=self.name,
                success=True,
                result=result,
                tool_calls=self._tool_calls,
                duration_ms=round(duration_ms, 2),
            )

        except Exception as e:
            logger.error(f"Skill {self.name} failed: {e}", exc_info=True)

            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000

            return SkillResult(
                skill_name=self.name,
                success=False,
                error=str(e),
                tool_calls=self._tool_calls,
                duration_ms=round(duration_ms, 2),
            )

        finally:
            self._ctx = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"


class CompositeSkill(Skill):
    """
    组合技能

    可以组合多个子技能按顺序或并行执行。

    示例:
    ------
    ```python
    class FullAnalysisSkill(CompositeSkill):
        name = "full_analysis"
        description = "完整的投资组合分析"
        sub_skills = [
            PortfolioAnalysisSkill,
            RiskAssessmentSkill,
            RecommendationSkill,
        ]

        async def execute(self, ctx: SkillContext, **kwargs) -> Any:
            results = await self.run_all_sequential(ctx, **kwargs)
            return self.combine_results(results)
    ```
    """

    sub_skills: list[type[Skill]] = []

    def __init__(self):
        super().__init__()
        self._skill_instances: list[Skill] = [
            skill_cls() for skill_cls in self.sub_skills
        ]

    async def run_skill(
        self,
        skill: Skill,
        ctx: SkillContext,
        **kwargs,
    ) -> SkillResult:
        """运行单个子技能"""
        return await skill(ctx, **kwargs)

    async def run_all_sequential(
        self,
        ctx: SkillContext,
        **kwargs,
    ) -> list[SkillResult]:
        """按顺序运行所有子技能"""
        results = []
        for skill in self._skill_instances:
            result = await self.run_skill(skill, ctx, **kwargs)
            results.append(result)
            # 如果某个技能失败，可以选择是否继续
            if not result.success:
                logger.warning(f"Sub-skill {skill.name} failed, continuing...")
        return results

    async def run_all_parallel(
        self,
        ctx: SkillContext,
        **kwargs,
    ) -> list[SkillResult]:
        """并行运行所有子技能"""
        import asyncio

        tasks = [
            self.run_skill(skill, ctx, **kwargs)
            for skill in self._skill_instances
        ]
        return await asyncio.gather(*tasks)

    def combine_results(self, results: list[SkillResult]) -> dict[str, Any]:
        """
        组合子技能结果

        子类可以覆盖此方法以自定义结果组合逻辑。
        """
        combined = {
            "skills": [],
            "all_success": all(r.success for r in results),
            "total_duration_ms": sum(r.duration_ms or 0 for r in results),
        }

        for result in results:
            combined["skills"].append({
                "name": result.skill_name,
                "success": result.success,
                "result": result.result,
                "error": result.error,
            })

        return combined

    async def execute(self, ctx: SkillContext, **kwargs) -> Any:
        """默认实现：按顺序执行所有子技能并组合结果"""
        results = await self.run_all_sequential(ctx, **kwargs)
        return self.combine_results(results)
