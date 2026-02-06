"""
Agent 核心引擎

主代理类，协调 LLM、工具、技能、子代理等组件完成用户请求。
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Optional, Union
from uuid import UUID, uuid4

from services.agent.config import AgentConfig, get_config
from services.agent.core.state import (
    AgentState,
    AgentStatus,
    Message,
    MessageRole,
    StreamChunk,
    ToolCall,
    UserContext,
)
from services.agent.llm.base import BaseLLM, LLMResponse, ToolDefinition
from services.agent.llm.factory import create_llm
from services.agent.tools.base import ToolContext, ToolResult
from services.agent.tools.registry import ToolRegistry, get_default_registry

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Agent 响应结构"""
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    state: Optional[AgentState] = None
    usage: Optional[dict[str, int]] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "content": self.content,
            "success": self.success,
        }
        if self.tool_calls:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.tool_results:
            result["tool_results"] = [tr.to_dict() for tr in self.tool_results]
        if self.usage:
            result["usage"] = self.usage
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        if self.error:
            result["error"] = self.error
        return result


class Agent:
    """
    U0 智能代理核心引擎

    协调 LLM、工具、技能等组件，处理用户请求。

    示例:
    ------
    ```python
    from services.agent import Agent, AgentConfig

    # 创建 Agent
    config = AgentConfig()
    agent = Agent(config)

    # 处理请求
    response = await agent.chat(
        messages=[{"role": "user", "content": "查看我的持仓"}],
        user_id="xxx-xxx-xxx",
    )
    print(response.content)

    # 流式响应
    async for chunk in agent.stream(
        messages=[{"role": "user", "content": "分析基金 000001"}],
        user_id="xxx-xxx-xxx",
    ):
        print(chunk.content, end="", flush=True)
    ```
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        llm: Optional[BaseLLM] = None,
        tools: Optional[ToolRegistry] = None,
    ):
        """
        初始化 Agent

        Args:
            config: Agent 配置，如果为 None 则使用默认配置
            llm: LLM 实例，如果为 None 则根据配置创建
            tools: 工具注册表，如果为 None 则使用默认注册表
        """
        self.config = config or get_config()
        self._llm = llm
        self._tools = tools
        self._initialized = False

        # 回调函数
        self._on_tool_start: Optional[Callable[[str, dict], None]] = None
        self._on_tool_end: Optional[Callable[[ToolResult], None]] = None
        self._on_llm_start: Optional[Callable[[list[Message]], None]] = None
        self._on_llm_end: Optional[Callable[[LLMResponse], None]] = None

    @property
    def llm(self) -> BaseLLM:
        """获取 LLM 实例（懒加载）"""
        if self._llm is None:
            self._llm = create_llm(
                config=self.config.llm,
                api_keys=self.config.api_keys,
            )
        return self._llm

    @property
    def tools(self) -> ToolRegistry:
        """获取工具注册表（懒加载）"""
        if self._tools is None:
            self._tools = get_default_registry()
            self._load_default_tools()
        return self._tools

    def _load_default_tools(self) -> None:
        """加载默认工具"""
        if self._initialized:
            return

        try:
            # 导入系统工具（触发装饰器注册）
            from services.agent.tools.system import (
                get_user_positions,
                get_fund_nav,
                get_news,
                get_watchlist,
            )
            logger.info("Loaded system tools")
        except ImportError as e:
            logger.warning(f"Failed to load system tools: {e}")

        try:
            # 导入网络工具
            from services.agent.tools.web import (
                web_search,
                fetch_webpage,
            )
            logger.info("Loaded web tools")
        except ImportError as e:
            logger.warning(f"Failed to load web tools: {e}")

        self._initialized = True

    def _get_tool_definitions(self) -> list[ToolDefinition]:
        """获取工具定义列表"""
        if not self.config.enable_tools:
            return []

        definitions = []
        for tool_def in self.tools.get_definitions():
            definitions.append(
                ToolDefinition(
                    name=tool_def.name,
                    description=tool_def.description,
                    parameters=tool_def.to_json_schema(),
                )
            )
        return definitions

    def _create_tool_context(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ToolContext:
        """创建工具执行上下文"""
        return ToolContext(
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
        )

    def _build_messages(
        self,
        messages: list[Union[dict[str, Any], Message]],
        system_prompt: Optional[str] = None,
    ) -> list[Message]:
        """构建消息列表"""
        result = []

        # 添加系统提示
        system_content = system_prompt or self.config.system_prompt
        if system_content:
            result.append(Message(
                role=MessageRole.SYSTEM,
                content=system_content,
            ))

        # 添加用户消息
        for msg in messages:
            if isinstance(msg, Message):
                result.append(msg)
            else:
                # 从字典创建消息
                role = MessageRole(msg.get("role", "user"))
                content = msg.get("content", "")
                result.append(Message(
                    id=msg.get("id", str(uuid4())),
                    role=role,
                    content=content,
                    name=msg.get("name"),
                    tool_call_id=msg.get("tool_call_id"),
                    tool_calls=[
                        ToolCall(
                            id=tc["id"],
                            name=tc["name"],
                            arguments=tc.get("arguments", {}),
                        )
                        for tc in msg.get("tool_calls", [])
                    ],
                ))

        return result

    async def _execute_tool_calls(
        self,
        tool_calls: list[ToolCall],
        ctx: ToolContext,
    ) -> list[ToolResult]:
        """执行工具调用"""
        results = []

        for tc in tool_calls:
            tc.started_at = datetime.now(timezone.utc)

            # 回调
            if self._on_tool_start:
                self._on_tool_start(tc.name, tc.arguments)

            logger.info(f"Executing tool: {tc.name} with args: {tc.arguments}")

            # 执行工具
            result = await self.tools.call(
                name=tc.name,
                ctx=ctx,
                tool_call_id=tc.id,
                **tc.arguments,
            )

            tc.completed_at = datetime.now(timezone.utc)
            tc.result = result.result if result.success else None
            tc.error = result.error if not result.success else None

            # 回调
            if self._on_tool_end:
                self._on_tool_end(result)

            results.append(result)

            logger.info(
                f"Tool {tc.name} completed: success={result.success}, "
                f"duration={result.duration_ms:.2f}ms"
            )

        return results

    async def chat(
        self,
        messages: list[Union[dict[str, Any], Message]],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_iterations: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        处理聊天请求（非流式）

        Args:
            messages: 对话消息列表
            user_id: 用户 ID
            session_id: 会话 ID
            system_prompt: 自定义系统提示（覆盖默认）
            max_iterations: 最大迭代次数（覆盖默认）
            metadata: 额外元数据

        Returns:
            Agent 响应
        """
        start_time = datetime.now(timezone.utc)
        max_iterations = max_iterations or self.config.max_iterations

        # 初始化状态
        state = AgentState(
            session_id=session_id or str(uuid4()),
            user_context=UserContext(user_id=UUID(user_id)) if user_id else None,
        )

        # 构建消息
        built_messages = self._build_messages(messages, system_prompt)
        for msg in built_messages:
            state.add_message(msg)

        # 创建工具上下文
        tool_ctx = self._create_tool_context(
            user_id=user_id,
            session_id=state.session_id,
            metadata=metadata,
        )

        # 获取工具定义
        tool_definitions = self._get_tool_definitions()

        # 迭代处理
        all_tool_calls = []
        all_tool_results = []
        final_content = ""
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        try:
            for iteration in range(max_iterations):
                state.iteration = iteration + 1
                state.status = AgentStatus.THINKING

                logger.debug(f"Iteration {state.iteration}: calling LLM")

                # 调用 LLM
                if self._on_llm_start:
                    self._on_llm_start(state.messages)

                response = await self.llm.generate(
                    messages=state.messages,
                    tools=tool_definitions if tool_definitions else None,
                )

                if self._on_llm_end:
                    self._on_llm_end(response)

                # 累计 token 使用
                if response.usage:
                    total_usage["prompt_tokens"] += response.usage.prompt_tokens
                    total_usage["completion_tokens"] += response.usage.completion_tokens
                    total_usage["total_tokens"] += response.usage.total_tokens

                # 检查是否需要调用工具
                if response.has_tool_calls:
                    state.status = AgentStatus.CALLING_TOOL

                    # 添加助手消息（包含工具调用）
                    assistant_msg = Message(
                        role=MessageRole.ASSISTANT,
                        content=response.content or "",
                        tool_calls=response.tool_calls,
                    )
                    state.add_message(assistant_msg)

                    # 执行工具
                    tool_results = await self._execute_tool_calls(
                        response.tool_calls,
                        tool_ctx,
                    )

                    all_tool_calls.extend(response.tool_calls)
                    all_tool_results.extend(tool_results)

                    # 添加工具结果消息
                    for tc, result in zip(response.tool_calls, tool_results):
                        tool_msg = Message(
                            role=MessageRole.TOOL,
                            content=result.to_string(),
                            name=tc.name,
                            tool_call_id=tc.id,
                        )
                        state.add_message(tool_msg)
                        state.add_tool_call(tc)

                    # 继续下一次迭代
                    continue

                # 没有工具调用，返回最终响应
                final_content = response.content or ""
                state.add_assistant_message(final_content)
                break

            else:
                # 达到最大迭代次数
                logger.warning(f"Max iterations ({max_iterations}) reached")
                final_content = (
                    final_content or
                    "抱歉，处理您的请求时遇到了问题。请尝试简化您的问题或稍后重试。"
                )

            state.status = AgentStatus.COMPLETED

        except Exception as e:
            logger.error(f"Agent chat failed: {e}", exc_info=True)
            state.status = AgentStatus.ERROR
            state.error = str(e)

            return AgentResponse(
                content="",
                error=str(e),
                state=state,
            )

        # 计算耗时
        end_time = datetime.now(timezone.utc)
        duration_ms = (end_time - start_time).total_seconds() * 1000

        return AgentResponse(
            content=final_content,
            tool_calls=all_tool_calls,
            tool_results=all_tool_results,
            state=state,
            usage=total_usage if any(total_usage.values()) else None,
            duration_ms=round(duration_ms, 2),
        )

    async def stream(
        self,
        messages: list[Union[dict[str, Any], Message]],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_iterations: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        处理聊天请求（流式）

        Args:
            messages: 对话消息列表
            user_id: 用户 ID
            session_id: 会话 ID
            system_prompt: 自定义系统提示
            max_iterations: 最大迭代次数
            metadata: 额外元数据

        Yields:
            流式响应块
        """
        max_iterations = max_iterations or self.config.max_iterations

        # 初始化状态
        state = AgentState(
            session_id=session_id or str(uuid4()),
            user_context=UserContext(user_id=UUID(user_id)) if user_id else None,
        )

        # 构建消息
        built_messages = self._build_messages(messages, system_prompt)
        for msg in built_messages:
            state.add_message(msg)

        # 创建工具上下文
        tool_ctx = self._create_tool_context(
            user_id=user_id,
            session_id=state.session_id,
            metadata=metadata,
        )

        # 获取工具定义
        tool_definitions = self._get_tool_definitions()

        try:
            for iteration in range(max_iterations):
                state.iteration = iteration + 1
                state.status = AgentStatus.STREAMING

                # 流式调用 LLM
                accumulated_content = ""
                accumulated_tool_calls: dict[int, dict[str, Any]] = {}

                async for chunk in self.llm.stream(
                    messages=state.messages,
                    tools=tool_definitions if tool_definitions else None,
                ):
                    # 处理文本内容
                    if chunk.delta_content:
                        accumulated_content += chunk.delta_content
                        yield StreamChunk(
                            type="text",
                            content=chunk.delta_content,
                        )

                    # 处理工具调用增量
                    if chunk.delta_tool_call:
                        tc_delta = chunk.delta_tool_call
                        index = tc_delta.get("index", 0)

                        if index not in accumulated_tool_calls:
                            accumulated_tool_calls[index] = {
                                "id": tc_delta.get("id", ""),
                                "name": "",
                                "arguments": "",
                            }

                        if tc_delta.get("id"):
                            accumulated_tool_calls[index]["id"] = tc_delta["id"]
                        if tc_delta.get("function", {}).get("name"):
                            accumulated_tool_calls[index]["name"] = tc_delta["function"]["name"]
                        if tc_delta.get("function", {}).get("arguments"):
                            accumulated_tool_calls[index]["arguments"] += tc_delta["function"]["arguments"]

                    # 检查是否完成
                    if chunk.is_done:
                        break

                # 处理累积的工具调用
                if accumulated_tool_calls:
                    state.status = AgentStatus.CALLING_TOOL

                    # 解析工具调用
                    tool_calls = []
                    for tc_data in accumulated_tool_calls.values():
                        try:
                            arguments = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
                        except json.JSONDecodeError:
                            arguments = {}

                        tc = ToolCall(
                            id=tc_data["id"] or str(uuid4()),
                            name=tc_data["name"],
                            arguments=arguments,
                        )
                        tool_calls.append(tc)

                        # 发送工具调用开始事件
                        yield StreamChunk(
                            type="tool_call",
                            tool_call=tc,
                            metadata={"status": "started"},
                        )

                    # 添加助手消息
                    assistant_msg = Message(
                        role=MessageRole.ASSISTANT,
                        content=accumulated_content,
                        tool_calls=tool_calls,
                    )
                    state.add_message(assistant_msg)

                    # 执行工具
                    for tc in tool_calls:
                        tc.started_at = datetime.now(timezone.utc)

                        result = await self.tools.call(
                            name=tc.name,
                            ctx=tool_ctx,
                            tool_call_id=tc.id,
                            **tc.arguments,
                        )

                        tc.completed_at = datetime.now(timezone.utc)
                        tc.result = result.result if result.success else None
                        tc.error = result.error if not result.success else None

                        # 发送工具结果事件
                        yield StreamChunk(
                            type="tool_result",
                            tool_call=tc,
                            content=result.to_string(),
                            metadata={
                                "success": result.success,
                                "duration_ms": result.duration_ms,
                            },
                        )

                        # 添加工具结果消息
                        tool_msg = Message(
                            role=MessageRole.TOOL,
                            content=result.to_string(),
                            name=tc.name,
                            tool_call_id=tc.id,
                        )
                        state.add_message(tool_msg)
                        state.add_tool_call(tc)

                    # 继续下一次迭代
                    continue

                # 没有工具调用，完成
                if accumulated_content:
                    state.add_assistant_message(accumulated_content)

                break

            state.status = AgentStatus.COMPLETED

            # 发送完成事件
            yield StreamChunk(
                type="done",
                metadata={
                    "session_id": state.session_id,
                    "iteration": state.iteration,
                },
            )

        except Exception as e:
            logger.error(f"Agent stream failed: {e}", exc_info=True)
            state.status = AgentStatus.ERROR
            state.error = str(e)

            yield StreamChunk(
                type="error",
                content=str(e),
            )

    def on_tool_start(self, callback: Callable[[str, dict], None]) -> "Agent":
        """注册工具开始回调"""
        self._on_tool_start = callback
        return self

    def on_tool_end(self, callback: Callable[[ToolResult], None]) -> "Agent":
        """注册工具结束回调"""
        self._on_tool_end = callback
        return self

    def on_llm_start(self, callback: Callable[[list[Message]], None]) -> "Agent":
        """注册 LLM 开始回调"""
        self._on_llm_start = callback
        return self

    def on_llm_end(self, callback: Callable[[LLMResponse], None]) -> "Agent":
        """注册 LLM 结束回调"""
        self._on_llm_end = callback
        return self

    def __repr__(self) -> str:
        return (
            f"Agent(llm={self.llm.provider_name}/{self.llm.model}, "
            f"tools={len(self.tools)})"
        )


# ============================================================================
# Convenience Functions
# ============================================================================


async def quick_chat(
    message: str,
    user_id: Optional[str] = None,
    **kwargs,
) -> str:
    """
    快速对话接口

    Args:
        message: 用户消息
        user_id: 用户 ID
        **kwargs: 传递给 Agent.chat 的额外参数

    Returns:
        Agent 响应文本
    """
    agent = Agent()
    response = await agent.chat(
        messages=[{"role": "user", "content": message}],
        user_id=user_id,
        **kwargs,
    )
    return response.content


async def quick_stream(
    message: str,
    user_id: Optional[str] = None,
    **kwargs,
) -> AsyncIterator[str]:
    """
    快速流式对话接口

    Args:
        message: 用户消息
        user_id: 用户 ID
        **kwargs: 传递给 Agent.stream 的额外参数

    Yields:
        文本块
    """
    agent = Agent()
    async for chunk in agent.stream(
        messages=[{"role": "user", "content": message}],
        user_id=user_id,
        **kwargs,
    ):
        if chunk.type == "text" and chunk.content:
            yield chunk.content
