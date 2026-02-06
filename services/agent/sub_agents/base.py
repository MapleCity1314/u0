"""
子代理基类

子代理是专门化的 Agent，负责处理特定领域的任务。
主 Agent 可以将任务委托给子代理，实现更复杂的协作。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from services.agent.tools.registry import ToolRegistry
    from services.agent.tools.base import ToolContext
    from services.agent.skills.base import Skill, SkillContext
    from services.agent.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class SubAgentRole(str, Enum):
    """子代理角色枚举"""
    RESEARCHER = "researcher"      # 研究员：信息收集与整理
    ANALYST = "analyst"            # 分析师：数据分析与洞察
    ADVISOR = "advisor"            # 顾问：提供建议和决策支持
    EXECUTOR = "executor"          # 执行者：执行具体操作
    MONITOR = "monitor"            # 监控者：监控和预警
    CUSTOM = "custom"              # 自定义角色


class SubAgentStatus(str, Enum):
    """子代理状态枚举"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SubAgentContext:
    """
    子代理执行上下文

    包含子代理执行任务所需的所有信息。
    """
    # 基础信息
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    task_id: str = field(default_factory=lambda: str(uuid4()))

    # 任务信息
    task: str = ""
    parent_context: Optional[dict[str, Any]] = None

    # 运行时资源
    tool_registry: Optional["ToolRegistry"] = None
    llm: Optional["BaseLLM"] = None

    # 元数据
    metadata: dict[str, Any] = field(default_factory=dict)

    # 执行历史
    messages: list[dict[str, Any]] = field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        return self.metadata.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置元数据"""
        self.metadata[key] = value

    def add_message(self, role: str, content: str, **kwargs) -> None:
        """添加消息到历史"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        })


@dataclass
class SubAgentResult:
    """子代理执行结果"""
    agent_name: str
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    reasoning: Optional[str] = None  # 推理过程
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    skill_calls: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        data = {
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "success": self.success,
        }
        if self.result is not None:
            data["result"] = self.result
        if self.error:
            data["error"] = self.error
        if self.reasoning:
            data["reasoning"] = self.reasoning
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.skill_calls:
            data["skill_calls"] = self.skill_calls
        if self.duration_ms is not None:
            data["duration_ms"] = self.duration_ms
        if self.metadata:
            data["metadata"] = self.metadata
        return data

    def to_string(self) -> str:
        """转换为字符串（用于传回主 Agent）"""
        if not self.success:
            return f"子代理 {self.agent_name} 执行失败: {self.error}"
        if isinstance(self.result, (dict, list)):
            import json
            return json.dumps(self.result, ensure_ascii=False, indent=2)
        return str(self.result)


class SubAgent(ABC):
    """
    子代理基类

    子代理是专门化的 Agent，负责处理特定领域的任务。

    示例:
    ------
    ```python
    class ResearcherAgent(SubAgent):
        name = "researcher"
        role = SubAgentRole.RESEARCHER
        description = "负责收集和整理信息"

        system_prompt = '''
        你是一个专业的研究员，负责：
        1. 收集相关信息
        2. 整理和归纳资料
        3. 提供信息摘要
        '''

        skills = ["web_search", "document_analysis"]
        tools = ["search_web", "fetch_webpage", "extract_content"]

        async def execute(self, ctx: SubAgentContext) -> Any:
            # 1. 分析任务
            task_analysis = await self.think(f"分析任务: {ctx.task}")

            # 2. 执行搜索
            search_result = await self.use_tool(
                "search_web",
                query=ctx.task
            )

            # 3. 整理结果
            summary = await self.think(
                f"整理搜索结果: {search_result}"
            )

            return {
                "analysis": task_analysis,
                "search_result": search_result,
                "summary": summary,
            }
    ```
    """

    # 子代理元数据（子类应覆盖）
    name: str = ""
    role: SubAgentRole = SubAgentRole.CUSTOM
    description: str = ""

    # 系统提示（定义子代理的行为和专长）
    system_prompt: str = ""

    # 可用的技能和工具
    skills: list[str] = []
    tools: list[str] = []

    # 配置
    max_iterations: int = 5
    max_tool_calls: int = 20
    timeout: int = 120
    temperature: float = 0.7

    def __init__(self):
        if not self.name:
            # 使用类名作为默认名称
            self.name = self._camel_to_snake(self.__class__.__name__)

        # 运行时状态
        self._ctx: Optional[SubAgentContext] = None
        self._status: SubAgentStatus = SubAgentStatus.IDLE
        self._tool_call_count: int = 0
        self._tool_calls: list[dict[str, Any]] = []
        self._skill_calls: list[dict[str, Any]] = []
        self._reasoning_steps: list[str] = []

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """将 CamelCase 转换为 snake_case"""
        import re
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        if name.endswith("_agent"):
            name = name[:-6]
        return name

    @property
    def ctx(self) -> SubAgentContext:
        """获取当前执行上下文"""
        if self._ctx is None:
            raise RuntimeError(
                "SubAgent not initialized. Call within proper context."
            )
        return self._ctx

    @property
    def status(self) -> SubAgentStatus:
        """获取当前状态"""
        return self._status

    def _get_tool_context(self) -> "ToolContext":
        """创建工具执行上下文"""
        from services.agent.tools.base import ToolContext
        return ToolContext(
            user_id=self.ctx.user_id,
            session_id=self.ctx.session_id,
            metadata=self.ctx.metadata,
        )

    def _get_skill_context(self) -> "SkillContext":
        """创建技能执行上下文"""
        from services.agent.skills.base import SkillContext
        return SkillContext(
            user_id=self.ctx.user_id,
            session_id=self.ctx.session_id,
            metadata=self.ctx.metadata,
            tool_registry=self.ctx.tool_registry,
        )

    async def think(self, prompt: str) -> str:
        """
        使用 LLM 进行思考/推理

        Args:
            prompt: 思考提示

        Returns:
            LLM 响应
        """
        if self.ctx.llm is None:
            raise RuntimeError("LLM not available")

        self._status = SubAgentStatus.THINKING

        # 构建消息
        messages = [
            {"role": "system", "content": self.system_prompt},
        ]

        # 添加历史消息
        for msg in self.ctx.messages:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        # 添加当前思考提示
        messages.append({"role": "user", "content": prompt})

        # 转换消息格式
        from services.agent.core.state import Message, MessageRole
        llm_messages = [
            Message(
                role=MessageRole(m["role"]),
                content=m["content"],
            )
            for m in messages
        ]

        # 调用 LLM
        response = await self.ctx.llm.generate(
            messages=llm_messages,
            temperature=self.temperature,
        )

        result = response.content or ""

        # 记录推理步骤
        self._reasoning_steps.append(f"思考: {prompt}\n结果: {result}")

        # 记录到上下文
        self.ctx.add_message("user", prompt)
        self.ctx.add_message("assistant", result)

        return result

    async def use_tool(self, tool_name: str, **kwargs) -> Any:
        """
        调用工具

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        if self._tool_call_count >= self.max_tool_calls:
            raise RuntimeError(
                f"Tool call limit exceeded ({self.max_tool_calls})"
            )

        if self.ctx.tool_registry is None:
            raise RuntimeError("Tool registry not available")

        # 检查工具是否在允许列表中
        if self.tools and tool_name not in self.tools:
            logger.warning(
                f"SubAgent {self.name} tried to use unauthorized tool: {tool_name}"
            )
            # 可以选择拒绝或允许

        if not self.ctx.tool_registry.has(tool_name):
            raise RuntimeError(f"Tool not found: {tool_name}")

        self._status = SubAgentStatus.EXECUTING
        self._tool_call_count += 1
        tool_call_id = str(uuid4())

        logger.debug(
            f"SubAgent {self.name} calling tool {tool_name}: {kwargs}"
        )

        # 执行工具
        tool_ctx = self._get_tool_context()
        result = await self.ctx.tool_registry.call(
            name=tool_name,
            ctx=tool_ctx,
            tool_call_id=tool_call_id,
            **kwargs,
        )

        # 记录工具调用
        call_record = {
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "arguments": kwargs,
            "success": result.success,
            "duration_ms": result.duration_ms,
        }
        self._tool_calls.append(call_record)

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

    async def use_skill(self, skill_name: str, **kwargs) -> Any:
        """
        调用技能

        Args:
            skill_name: 技能名称
            **kwargs: 技能参数

        Returns:
            技能执行结果
        """
        # 检查技能是否在允许列表中
        if self.skills and skill_name not in self.skills:
            logger.warning(
                f"SubAgent {self.name} tried to use unauthorized skill: {skill_name}"
            )

        self._status = SubAgentStatus.EXECUTING

        # 这里需要技能注册表的支持
        # 暂时返回未实现
        logger.warning(f"Skill execution not yet implemented: {skill_name}")

        self._skill_calls.append({
            "skill_name": skill_name,
            "arguments": kwargs,
            "success": False,
            "error": "Not implemented",
        })

        return {"error": "Skill execution not yet implemented"}

    async def delegate_to(
        self,
        agent: "SubAgent",
        task: str,
        **kwargs,
    ) -> SubAgentResult:
        """
        委托任务给另一个子代理

        Args:
            agent: 目标子代理
            task: 任务描述
            **kwargs: 额外参数

        Returns:
            子代理执行结果
        """
        # 创建子上下文
        sub_ctx = SubAgentContext(
            user_id=self.ctx.user_id,
            session_id=self.ctx.session_id,
            task=task,
            parent_context=self.ctx.metadata,
            tool_registry=self.ctx.tool_registry,
            llm=self.ctx.llm,
            metadata=kwargs,
        )

        logger.info(
            f"SubAgent {self.name} delegating to {agent.name}: {task[:100]}"
        )

        return await agent(sub_ctx)

    def validate(self) -> bool:
        """
        验证子代理配置是否有效

        Returns:
            配置是否有效
        """
        if self.ctx.tool_registry is None:
            logger.warning(f"SubAgent {self.name}: tool registry not available")
            return False

        # 验证所需工具
        for tool_name in self.tools:
            if not self.ctx.tool_registry.has(tool_name):
                logger.warning(
                    f"SubAgent {self.name} missing tool: {tool_name}"
                )
                # 工具缺失可能不是致命错误

        return True

    @abstractmethod
    async def execute(self, ctx: SubAgentContext) -> Any:
        """
        执行任务

        Args:
            ctx: 子代理执行上下文

        Returns:
            执行结果
        """
        pass

    async def __call__(self, ctx: SubAgentContext) -> SubAgentResult:
        """
        调用子代理执行任务

        Args:
            ctx: 子代理执行上下文

        Returns:
            子代理执行结果
        """
        self._ctx = ctx
        self._status = SubAgentStatus.IDLE
        self._tool_call_count = 0
        self._tool_calls = []
        self._skill_calls = []
        self._reasoning_steps = []

        start_time = datetime.now(timezone.utc)

        logger.info(
            f"SubAgent {self.name} starting task: {ctx.task[:100]}..."
        )

        try:
            # 验证配置
            self.validate()

            # 执行任务
            self._status = SubAgentStatus.EXECUTING
            result = await self.execute(ctx)

            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000

            self._status = SubAgentStatus.COMPLETED

            logger.info(
                f"SubAgent {self.name} completed task in {duration_ms:.2f}ms"
            )

            return SubAgentResult(
                agent_name=self.name,
                task_id=ctx.task_id,
                success=True,
                result=result,
                reasoning="\n---\n".join(self._reasoning_steps) if self._reasoning_steps else None,
                tool_calls=self._tool_calls,
                skill_calls=self._skill_calls,
                duration_ms=round(duration_ms, 2),
            )

        except Exception as e:
            logger.error(
                f"SubAgent {self.name} failed: {e}",
                exc_info=True
            )

            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000

            self._status = SubAgentStatus.ERROR

            return SubAgentResult(
                agent_name=self.name,
                task_id=ctx.task_id,
                success=False,
                error=str(e),
                reasoning="\n---\n".join(self._reasoning_steps) if self._reasoning_steps else None,
                tool_calls=self._tool_calls,
                skill_calls=self._skill_calls,
                duration_ms=round(duration_ms, 2),
            )

        finally:
            self._ctx = None

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"role={self.role.value!r})"
        )


class CoordinatorSubAgent(SubAgent):
    """
    协调者子代理

    可以协调多个子代理完成复杂任务。

    示例:
    ------
    ```python
    class InvestmentAdvisorCoordinator(CoordinatorSubAgent):
        name = "investment_advisor"
        description = "协调研究员和分析师提供投资建议"

        sub_agents = [
            ResearcherAgent,
            AnalystAgent,
        ]

        async def execute(self, ctx: SubAgentContext) -> Any:
            # 1. 让研究员收集信息
            research = await self.delegate("researcher",
                f"收集关于 {ctx.task} 的信息")

            # 2. 让分析师分析数据
            analysis = await self.delegate("analyst",
                f"分析以下信息: {research.result}")

            # 3. 综合给出建议
            advice = await self.think(
                f"基于以下分析给出投资建议:\\n{analysis.result}"
            )

            return {
                "research": research.result,
                "analysis": analysis.result,
                "advice": advice,
            }
    ```
    """

    role = SubAgentRole.ADVISOR
    sub_agents: list[type[SubAgent]] = []

    def __init__(self):
        super().__init__()
        self._agent_instances: dict[str, SubAgent] = {}

        # 实例化子代理
        for agent_cls in self.sub_agents:
            agent = agent_cls()
            self._agent_instances[agent.name] = agent

    def get_agent(self, name: str) -> Optional[SubAgent]:
        """获取子代理实例"""
        return self._agent_instances.get(name)

    async def delegate(self, agent_name: str, task: str, **kwargs) -> SubAgentResult:
        """
        委托任务给指定的子代理

        Args:
            agent_name: 子代理名称
            task: 任务描述
            **kwargs: 额外参数

        Returns:
            子代理执行结果
        """
        agent = self.get_agent(agent_name)
        if agent is None:
            return SubAgentResult(
                agent_name=agent_name,
                task_id=str(uuid4()),
                success=False,
                error=f"SubAgent not found: {agent_name}",
            )

        return await self.delegate_to(agent, task, **kwargs)

    async def delegate_all_sequential(
        self,
        task: str,
        **kwargs,
    ) -> list[SubAgentResult]:
        """按顺序委托任务给所有子代理"""
        results = []
        for agent in self._agent_instances.values():
            result = await self.delegate_to(agent, task, **kwargs)
            results.append(result)
        return results

    async def delegate_all_parallel(
        self,
        task: str,
        **kwargs,
    ) -> list[SubAgentResult]:
        """并行委托任务给所有子代理"""
        import asyncio

        tasks = [
            self.delegate_to(agent, task, **kwargs)
            for agent in self._agent_instances.values()
        ]
        return await asyncio.gather(*tasks)

    async def execute(self, ctx: SubAgentContext) -> Any:
        """
        默认实现：按顺序执行所有子代理

        子类应覆盖此方法以实现自定义协调逻辑。
        """
        results = await self.delegate_all_sequential(ctx.task)

        return {
            "sub_agent_results": [r.to_dict() for r in results],
            "all_success": all(r.success for r in results),
        }
