"""
LLM 提供商基类

定义所有 LLM 提供商必须实现的接口。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from services.agent.core.state import Message, ToolCall


@dataclass
class LLMResponse:
    """LLM 响应结构"""
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: Optional[str] = None
    usage: Optional[LLMUsage] = None
    model: Optional[str] = None
    raw_response: Optional[Any] = None

    @property
    def has_tool_calls(self) -> bool:
        """是否包含工具调用"""
        return len(self.tool_calls) > 0


@dataclass
class LLMUsage:
    """Token 使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class LLMStreamChunk:
    """流式响应块"""
    delta_content: Optional[str] = None
    delta_tool_call: Optional[dict[str, Any]] = None
    finish_reason: Optional[str] = None
    usage: Optional[LLMUsage] = None

    @property
    def is_done(self) -> bool:
        """是否已完成"""
        return self.finish_reason is not None


@dataclass
class ToolDefinition:
    """工具定义（用于传递给 LLM）"""
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema 格式

    def to_openai_format(self) -> dict[str, Any]:
        """转换为 OpenAI 工具格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_anthropic_format(self) -> dict[str, Any]:
        """转换为 Anthropic 工具格式"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


class BaseLLM(ABC):
    """
    LLM 提供商基类

    所有 LLM 适配器必须继承此类并实现抽象方法。
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 60,
        max_retries: int = 3,
        **kwargs,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.extra_kwargs = kwargs

        # 验证配置
        self._validate_config()

        # 初始化客户端
        self._client = None
        self._async_client = None

    def _validate_config(self) -> None:
        """验证配置"""
        if not self.model:
            raise ValueError("model is required")

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称"""
        pass

    @abstractmethod
    def _init_client(self) -> Any:
        """初始化同步客户端"""
        pass

    @abstractmethod
    def _init_async_client(self) -> Any:
        """初始化异步客户端"""
        pass

    @property
    def client(self) -> Any:
        """获取同步客户端（懒加载）"""
        if self._client is None:
            self._client = self._init_client()
        return self._client

    @property
    def async_client(self) -> Any:
        """获取异步客户端（懒加载）"""
        if self._async_client is None:
            self._async_client = self._init_async_client()
        return self._async_client

    @abstractmethod
    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """
        转换消息格式为提供商格式

        Args:
            messages: Agent 消息列表

        Returns:
            提供商格式的消息列表
        """
        pass

    @abstractmethod
    def _convert_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        """
        转换工具定义为提供商格式

        Args:
            tools: 工具定义列表

        Returns:
            提供商格式的工具定义列表
        """
        pass

    @abstractmethod
    def _parse_response(self, response: Any) -> LLMResponse:
        """
        解析提供商响应

        Args:
            response: 提供商原始响应

        Returns:
            统一的 LLMResponse 对象
        """
        pass

    @abstractmethod
    def _parse_stream_chunk(self, chunk: Any) -> LLMStreamChunk:
        """
        解析流式响应块

        Args:
            chunk: 提供商原始响应块

        Returns:
            统一的 LLMStreamChunk 对象
        """
        pass

    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        tools: Optional[list[ToolDefinition]] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        生成响应

        Args:
            messages: 对话消息列表
            tools: 可用工具列表
            **kwargs: 额外参数

        Returns:
            LLM 响应
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        tools: Optional[list[ToolDefinition]] = None,
        **kwargs,
    ) -> AsyncIterator[LLMStreamChunk]:
        """
        流式生成响应

        Args:
            messages: 对话消息列表
            tools: 可用工具列表
            **kwargs: 额外参数

        Yields:
            流式响应块
        """
        pass

    def count_tokens(self, text: str) -> int:
        """
        计算文本的 token 数量（可选实现）

        Args:
            text: 输入文本

        Returns:
            Token 数量
        """
        # 默认使用简单估算（约 4 字符 = 1 token）
        return len(text) // 4

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r}, provider={self.provider_name!r})"
