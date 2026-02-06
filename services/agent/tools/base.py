"""
工具基类与装饰器

提供工具定义的基础设施，支持声明式工具定义和自动 JSON Schema 生成。
"""

from __future__ import annotations

import inspect
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import (
    Any,
    Callable,
    Optional,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)
from uuid import uuid4

# Type variable for tool functions
F = TypeVar("F", bound=Callable[..., Any])


class ToolCategory(str, Enum):
    """工具分类"""
    SYSTEM = "system"      # 系统集成工具
    WEB = "web"            # 网络工具
    ANALYSIS = "analysis"  # 分析工具
    DATA = "data"          # 数据工具
    UTILITY = "utility"    # 通用工具


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[list[Any]] = None

    def to_json_schema(self) -> dict[str, Any]:
        """转换为 JSON Schema 格式"""
        schema: dict[str, Any] = {
            "type": self.type,
            "description": self.description,
        }
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        return schema


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: list[ToolParameter] = field(default_factory=list)
    category: ToolCategory = ToolCategory.UTILITY
    requires_confirmation: bool = False
    is_async: bool = True
    tags: list[str] = field(default_factory=list)

    def to_json_schema(self) -> dict[str, Any]:
        """转换为 JSON Schema 格式（用于 LLM）"""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def to_openai_format(self) -> dict[str, Any]:
        """转换为 OpenAI 工具格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.to_json_schema(),
            },
        }

    def to_anthropic_format(self) -> dict[str, Any]:
        """转换为 Anthropic 工具格式"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.to_json_schema(),
        }


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    tool_call_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        data = {
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "success": self.success,
        }
        if self.result is not None:
            data["result"] = self.result
        if self.error:
            data["error"] = self.error
        if self.duration_ms is not None:
            data["duration_ms"] = self.duration_ms
        if self.metadata:
            data["metadata"] = self.metadata
        return data

    def to_string(self) -> str:
        """转换为字符串（用于传回 LLM）"""
        if not self.success:
            return f"Error: {self.error}"
        if isinstance(self.result, (dict, list)):
            return json.dumps(self.result, ensure_ascii=False, indent=2)
        return str(self.result)


class ToolContext:
    """
    工具执行上下文

    提供工具执行时需要的上下文信息。
    """

    def __init__(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.metadata = metadata or {}
        self._db_session = None

    @property
    def db_session(self):
        """获取数据库会话（懒加载）"""
        if self._db_session is None:
            from services.core.database import get_session
            self._db_session = get_session()
        return self._db_session

    def get(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        return self.metadata.get(key, default)


class Tool(ABC):
    """
    工具基类

    所有工具都应该继承此类并实现 execute 方法。

    示例:
    ------
    ```python
    class GetPositionsTool(Tool):
        name = "get_positions"
        description = "获取用户的持仓列表"
        category = ToolCategory.SYSTEM

        async def execute(self, ctx: ToolContext, **kwargs) -> Any:
            # 实现逻辑
            return positions
    ```
    """

    name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.UTILITY
    parameters: list[ToolParameter] = []
    requires_confirmation: bool = False
    tags: list[str] = []

    def __init__(self):
        if not self.name:
            # 使用类名作为默认名称
            self.name = self._camel_to_snake(self.__class__.__name__)

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """将 CamelCase 转换为 snake_case"""
        import re
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        if name.endswith("_tool"):
            name = name[:-5]
        return name

    @property
    def definition(self) -> ToolDefinition:
        """获取工具定义"""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
            category=self.category,
            requires_confirmation=self.requires_confirmation,
            is_async=True,
            tags=self.tags,
        )

    @abstractmethod
    async def execute(self, ctx: ToolContext, **kwargs) -> Any:
        """
        执行工具

        Args:
            ctx: 工具执行上下文
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        pass

    async def __call__(
        self,
        ctx: ToolContext,
        tool_call_id: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """
        调用工具并返回结果

        Args:
            ctx: 工具执行上下文
            tool_call_id: 工具调用 ID
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        tool_call_id = tool_call_id or str(uuid4())
        start_time = datetime.now(timezone.utc)

        try:
            result = await self.execute(ctx, **kwargs)
            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000

            return ToolResult(
                tool_name=self.name,
                tool_call_id=tool_call_id,
                success=True,
                result=result,
                duration_ms=duration_ms,
            )
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000

            return ToolResult(
                tool_name=self.name,
                tool_call_id=tool_call_id,
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )


# 用于存储装饰器创建的工具函数
_REGISTERED_TOOLS: dict[str, "FunctionTool"] = {}


class FunctionTool(Tool):
    """
    基于函数的工具

    通过 @tool 装饰器创建。
    """

    def __init__(
        self,
        func: Callable[..., Any],
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: ToolCategory = ToolCategory.UTILITY,
        requires_confirmation: bool = False,
        tags: Optional[list[str]] = None,
    ):
        self._func = func
        self._is_async = inspect.iscoroutinefunction(func)
        self.name = name or func.__name__
        self.description = description or func.__doc__ or ""
        self.category = category
        self.requires_confirmation = requires_confirmation
        self.tags = tags or []

        # 自动解析参数
        self.parameters = self._parse_parameters()

    def _parse_parameters(self) -> list[ToolParameter]:
        """从函数签名解析参数"""
        params = []
        sig = inspect.signature(self._func)
        type_hints = get_type_hints(self._func) if hasattr(self._func, "__annotations__") else {}

        for param_name, param in sig.parameters.items():
            # 跳过 ctx 参数
            if param_name == "ctx":
                continue

            # 获取类型
            param_type = type_hints.get(param_name, Any)
            json_type = self._python_type_to_json(param_type)

            # 获取默认值
            has_default = param.default is not inspect.Parameter.empty
            default = param.default if has_default else None

            # 获取枚举值
            enum_values = None
            if get_origin(param_type) is Union:
                # 处理 Optional 类型
                args = get_args(param_type)
                param_type = args[0] if len(args) == 2 and type(None) in args else param_type

            if isinstance(param_type, type) and issubclass(param_type, Enum):
                enum_values = [e.value for e in param_type]

            # 获取描述（从 docstring 解析）
            param_desc = self._get_param_description(param_name)

            params.append(
                ToolParameter(
                    name=param_name,
                    type=json_type,
                    description=param_desc,
                    required=not has_default,
                    default=default,
                    enum=enum_values,
                )
            )

        return params

    def _python_type_to_json(self, py_type: Type) -> str:
        """将 Python 类型转换为 JSON Schema 类型"""
        origin = get_origin(py_type)

        # 处理泛型
        if origin is Union:
            args = get_args(py_type)
            # Optional[X] = Union[X, None]
            non_none_args = [a for a in args if a is not type(None)]
            if len(non_none_args) == 1:
                return self._python_type_to_json(non_none_args[0])
            return "string"  # 默认使用 string

        if origin is list:
            return "array"
        if origin is dict:
            return "object"

        # 基本类型映射
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
            type(None): "null",
        }

        return type_map.get(py_type, "string")

    def _get_param_description(self, param_name: str) -> str:
        """从 docstring 获取参数描述"""
        if not self._func.__doc__:
            return param_name

        doc = self._func.__doc__
        # 简单解析 Google 风格 docstring
        lines = doc.split("\n")
        in_args = False

        for line in lines:
            line = line.strip()
            if line.lower().startswith("args:"):
                in_args = True
                continue
            if in_args:
                if line.startswith(param_name):
                    # 提取描述
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        return parts[1].strip()
                if line and not line[0].isspace() and ":" not in line:
                    # 新的部分，停止解析
                    break

        return param_name

    async def execute(self, ctx: ToolContext, **kwargs) -> Any:
        """执行工具函数"""
        # 检查函数是否需要 ctx 参数
        sig = inspect.signature(self._func)
        if "ctx" in sig.parameters:
            kwargs["ctx"] = ctx

        if self._is_async:
            return await self._func(**kwargs)
        else:
            return self._func(**kwargs)


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: ToolCategory = ToolCategory.UTILITY,
    requires_confirmation: bool = False,
    tags: Optional[list[str]] = None,
) -> Callable[[F], F]:
    """
    工具装饰器

    将普通函数转换为工具。

    Args:
        name: 工具名称，默认使用函数名
        description: 工具描述，默认使用函数 docstring
        category: 工具分类
        requires_confirmation: 是否需要用户确认
        tags: 标签列表

    Returns:
        装饰后的函数

    示例:
    ------
    ```python
    @tool(
        name="search_web",
        description="搜索网页信息",
        category=ToolCategory.WEB,
    )
    async def search_web(query: str, max_results: int = 10) -> str:
        '''
        搜索网页信息。

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            搜索结果的 JSON 字符串
        '''
        # 实现逻辑
        return results
    ```
    """

    def decorator(func: F) -> F:
        # 创建 FunctionTool 实例
        tool_instance = FunctionTool(
            func=func,
            name=name,
            description=description,
            category=category,
            requires_confirmation=requires_confirmation,
            tags=tags,
        )

        # 注册工具
        _REGISTERED_TOOLS[tool_instance.name] = tool_instance

        # 保留原函数的属性
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)

        # 附加工具实例和定义
        wrapper._tool = tool_instance  # type: ignore
        wrapper._tool_definition = tool_instance.definition  # type: ignore

        return wrapper  # type: ignore

    return decorator


def get_registered_tools() -> dict[str, FunctionTool]:
    """获取所有注册的工具"""
    return _REGISTERED_TOOLS.copy()


def get_tool(name: str) -> Optional[FunctionTool]:
    """根据名称获取工具"""
    return _REGISTERED_TOOLS.get(name)


def clear_registered_tools() -> None:
    """清空注册的工具（用于测试）"""
    _REGISTERED_TOOLS.clear()
