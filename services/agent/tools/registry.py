"""
工具注册表

管理工具的注册、发现和调用。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Type, Union

from services.agent.tools.base import (
    FunctionTool,
    Tool,
    ToolCategory,
    ToolContext,
    ToolDefinition,
    ToolResult,
    _REGISTERED_TOOLS,
)

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    工具注册表

    集中管理所有可用工具，提供注册、发现、调用能力。

    示例:
    ------
    ```python
    registry = ToolRegistry()

    # 注册工具类
    registry.register(GetPositionsTool)

    # 注册已装饰的函数
    registry.register(search_web)

    # 列出所有工具
    tools = registry.list_tools()

    # 调用工具
    ctx = ToolContext(user_id="xxx")
    result = await registry.call("get_positions", ctx)
    ```
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[ToolCategory, List[str]] = {
            cat: [] for cat in ToolCategory
        }

    def register(
        self,
        tool: Union[Type[Tool], Tool, Callable[..., Any]],
        **kwargs,
    ) -> "ToolRegistry":
        """
        注册工具

        支持多种注册方式：
        - Tool 类
        - Tool 实例
        - 被 @tool 装饰的函数
        - 普通函数（会自动转换为 FunctionTool）

        Args:
            tool: 要注册的工具
            **kwargs: 传递给 FunctionTool 的额外参数

        Returns:
            self，支持链式调用

        Raises:
            ValueError: 工具名称重复或无效
        """
        tool_instance: Tool

        # 处理不同类型的输入
        if isinstance(tool, type) and issubclass(tool, Tool):
            # Tool 类
            tool_instance = tool()
        elif isinstance(tool, Tool):
            # Tool 实例
            tool_instance = tool
        elif hasattr(tool, "_tool"):
            # 被 @tool 装饰的函数
            tool_instance = tool._tool  # type: ignore
        elif callable(tool):
            # 普通函数，转换为 FunctionTool
            tool_instance = FunctionTool(func=tool, **kwargs)
        else:
            raise ValueError(f"Invalid tool type: {type(tool)}")

        # 验证工具名称
        if not tool_instance.name:
            raise ValueError("Tool name cannot be empty")

        # 检查重复注册
        if tool_instance.name in self._tools:
            logger.warning(
                f"Tool '{tool_instance.name}' already registered, overwriting"
            )

        # 注册工具
        self._tools[tool_instance.name] = tool_instance

        # 更新分类索引
        category = tool_instance.category
        if tool_instance.name not in self._categories[category]:
            self._categories[category].append(tool_instance.name)

        logger.debug(f"Registered tool: {tool_instance.name}")
        return self

    def register_many(
        self,
        tools: List[Union[Type[Tool], Tool, Callable[..., Any]]],
    ) -> "ToolRegistry":
        """
        批量注册工具

        Args:
            tools: 工具列表

        Returns:
            self，支持链式调用
        """
        for tool in tools:
            self.register(tool)
        return self

    def unregister(self, name: str) -> bool:
        """
        取消注册工具

        Args:
            name: 工具名称

        Returns:
            是否成功取消注册
        """
        if name not in self._tools:
            return False

        tool = self._tools.pop(name)

        # 从分类索引中移除
        if name in self._categories[tool.category]:
            self._categories[tool.category].remove(name)

        logger.debug(f"Unregistered tool: {name}")
        return True

    def get(self, name: str) -> Optional[Tool]:
        """
        获取工具

        Args:
            name: 工具名称

        Returns:
            工具实例，如果不存在则返回 None
        """
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """
        检查工具是否存在

        Args:
            name: 工具名称

        Returns:
            工具是否存在
        """
        return name in self._tools

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Tool]:
        """
        列出工具

        Args:
            category: 按分类过滤
            tags: 按标签过滤（任一匹配）

        Returns:
            工具列表
        """
        tools = list(self._tools.values())

        # 按分类过滤
        if category is not None:
            tools = [t for t in tools if t.category == category]

        # 按标签过滤
        if tags:
            tools = [
                t for t in tools
                if any(tag in t.tags for tag in tags)
            ]

        return tools

    def list_tool_names(
        self,
        category: Optional[ToolCategory] = None,
    ) -> List[str]:
        """
        列出工具名称

        Args:
            category: 按分类过滤

        Returns:
            工具名称列表
        """
        if category is not None:
            return self._categories[category].copy()
        return list(self._tools.keys())

    def get_definitions(
        self,
        category: Optional[ToolCategory] = None,
        tags: Optional[List[str]] = None,
    ) -> List[ToolDefinition]:
        """
        获取工具定义（用于传递给 LLM）

        Args:
            category: 按分类过滤
            tags: 按标签过滤

        Returns:
            工具定义列表
        """
        tools = self.list_tools(category=category, tags=tags)
        return [t.definition for t in tools]

    def get_openai_tools(
        self,
        category: Optional[ToolCategory] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取 OpenAI 格式的工具定义

        Args:
            category: 按分类过滤
            tags: 按标签过滤

        Returns:
            OpenAI 格式的工具定义列表
        """
        definitions = self.get_definitions(category=category, tags=tags)
        return [d.to_openai_format() for d in definitions]

    def get_anthropic_tools(
        self,
        category: Optional[ToolCategory] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取 Anthropic 格式的工具定义

        Args:
            category: 按分类过滤
            tags: 按标签过滤

        Returns:
            Anthropic 格式的工具定义列表
        """
        definitions = self.get_definitions(category=category, tags=tags)
        return [d.to_anthropic_format() for d in definitions]

    async def call(
        self,
        name: str,
        ctx: Optional[ToolContext] = None,
        tool_call_id: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """
        调用工具

        Args:
            name: 工具名称
            ctx: 工具执行上下文
            tool_call_id: 工具调用 ID
            **kwargs: 工具参数

        Returns:
            工具执行结果

        Raises:
            ValueError: 工具不存在
        """
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                tool_name=name,
                tool_call_id=tool_call_id or "",
                success=False,
                error=f"Tool not found: {name}",
            )

        # 创建默认上下文
        if ctx is None:
            ctx = ToolContext()

        logger.debug(f"Calling tool: {name} with args: {kwargs}")

        return await tool(ctx, tool_call_id=tool_call_id, **kwargs)

    async def call_many(
        self,
        calls: List[Dict[str, Any]],
        ctx: Optional[ToolContext] = None,
        parallel: bool = True,
    ) -> List[ToolResult]:
        """
        批量调用工具

        Args:
            calls: 调用列表，每项包含 name, tool_call_id, arguments
            ctx: 工具执行上下文
            parallel: 是否并行执行

        Returns:
            工具执行结果列表
        """
        if ctx is None:
            ctx = ToolContext()

        if parallel:
            # 并行执行
            tasks = [
                self.call(
                    name=call["name"],
                    ctx=ctx,
                    tool_call_id=call.get("tool_call_id"),
                    **call.get("arguments", {}),
                )
                for call in calls
            ]
            return await asyncio.gather(*tasks)
        else:
            # 串行执行
            results = []
            for call in calls:
                result = await self.call(
                    name=call["name"],
                    ctx=ctx,
                    tool_call_id=call.get("tool_call_id"),
                    **call.get("arguments", {}),
                )
                results.append(result)
            return results

    def clear(self) -> None:
        """清空所有注册的工具"""
        self._tools.clear()
        self._categories = {cat: [] for cat in ToolCategory}
        logger.debug("Cleared all tools from registry")

    def merge(self, other: "ToolRegistry") -> "ToolRegistry":
        """
        合并另一个注册表

        Args:
            other: 要合并的注册表

        Returns:
            self，支持链式调用
        """
        for tool in other._tools.values():
            self.register(tool)
        return self

    def __len__(self) -> int:
        """返回注册的工具数量"""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools

    def __iter__(self):
        """迭代所有工具"""
        return iter(self._tools.values())

    def __repr__(self) -> str:
        return f"ToolRegistry(name={self.name!r}, tools={len(self._tools)})"


# 默认注册表实例
_default_registry: Optional[ToolRegistry] = None


def get_default_registry() -> ToolRegistry:
    """
    获取默认工具注册表

    默认注册表会自动加载所有通过 @tool 装饰器注册的工具。

    Returns:
        默认工具注册表
    """
    global _default_registry

    if _default_registry is None:
        _default_registry = ToolRegistry(name="default")

        # 加载通过装饰器注册的工具
        for name, tool in _REGISTERED_TOOLS.items():
            _default_registry._tools[name] = tool
            if name not in _default_registry._categories[tool.category]:
                _default_registry._categories[tool.category].append(name)

    return _default_registry


def reset_default_registry() -> None:
    """重置默认注册表（用于测试）"""
    global _default_registry
    _default_registry = None


def create_registry(
    name: str = "custom",
    include_default: bool = False,
) -> ToolRegistry:
    """
    创建新的工具注册表

    Args:
        name: 注册表名称
        include_default: 是否包含默认注册表的工具

    Returns:
        新的工具注册表
    """
    registry = ToolRegistry(name=name)

    if include_default:
        default = get_default_registry()
        registry.merge(default)

    return registry
