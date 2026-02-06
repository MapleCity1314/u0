"""
OpenAI LLM 适配器

支持 OpenAI API 及其兼容服务（如 Azure OpenAI, DeepSeek 等）。
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional
from uuid import uuid4

from services.agent.core.state import Message, MessageRole, ToolCall
from services.agent.llm.base import (
    BaseLLM,
    LLMResponse,
    LLMStreamChunk,
    LLMUsage,
    ToolDefinition,
)


class OpenAILLM(BaseLLM):
    """
    OpenAI LLM 适配器

    支持:
    - OpenAI GPT-4o, GPT-4o-mini, GPT-4-turbo, GPT-3.5-turbo 等
    - Azure OpenAI Service
    - 兼容 OpenAI API 的其他服务

    示例:
    ------
    ```python
    llm = OpenAILLM(
        model="gpt-4o-mini",
        api_key="sk-xxx",
        temperature=0.7,
    )

    response = await llm.generate(messages=[...])
    ```
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 60,
        max_retries: int = 3,
        **kwargs,
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )
        self.organization = organization

    @property
    def provider_name(self) -> str:
        return "openai"

    def _validate_config(self) -> None:
        """验证配置"""
        super()._validate_config()
        # API key 可以通过环境变量 OPENAI_API_KEY 提供

    def _init_client(self) -> Any:
        """初始化同步客户端"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )

        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            organization=self.organization,
            timeout=float(self.timeout),
            max_retries=self.max_retries,
        )

    def _init_async_client(self) -> Any:
        """初始化异步客户端"""
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )

        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            organization=self.organization,
            timeout=float(self.timeout),
            max_retries=self.max_retries,
        )

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """转换消息格式为 OpenAI 格式"""
        openai_messages = []

        for msg in messages:
            openai_msg: dict[str, Any] = {
                "role": msg.role.value,
            }

            # 处理内容
            if msg.content:
                openai_msg["content"] = msg.content
            elif msg.role == MessageRole.ASSISTANT and msg.tool_calls:
                # 如果是助手消息且有工具调用但无内容，设置为 None
                openai_msg["content"] = None

            # 处理工具调用（助手消息）
            if msg.role == MessageRole.ASSISTANT and msg.tool_calls:
                openai_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        },
                    }
                    for tc in msg.tool_calls
                ]

            # 处理工具结果消息
            if msg.role == MessageRole.TOOL:
                openai_msg["tool_call_id"] = msg.tool_call_id
                openai_msg["content"] = msg.content

            # 添加 name 字段（如果有）
            if msg.name and msg.role != MessageRole.TOOL:
                openai_msg["name"] = msg.name

            openai_messages.append(openai_msg)

        return openai_messages

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        """转换工具定义为 OpenAI 格式"""
        return [tool.to_openai_format() for tool in tools]

    def _parse_tool_calls(self, tool_calls: list[Any]) -> list[ToolCall]:
        """解析 OpenAI 工具调用响应"""
        result = []
        for tc in tool_calls:
            try:
                arguments = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, AttributeError):
                arguments = {}

            result.append(
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=arguments,
                )
            )
        return result

    def _parse_response(self, response: Any) -> LLMResponse:
        """解析 OpenAI 响应"""
        choice = response.choices[0]
        message = choice.message

        # 解析工具调用
        tool_calls = []
        if message.tool_calls:
            tool_calls = self._parse_tool_calls(message.tool_calls)

        # 解析 usage
        usage = None
        if response.usage:
            usage = LLMUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

        return LLMResponse(
            content=message.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            usage=usage,
            model=response.model,
            raw_response=response,
        )

    def _parse_stream_chunk(self, chunk: Any) -> LLMStreamChunk:
        """解析流式响应块"""
        if not chunk.choices:
            # 最后一个 chunk 可能只有 usage 信息
            usage = None
            if hasattr(chunk, "usage") and chunk.usage:
                usage = LLMUsage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                )
            return LLMStreamChunk(finish_reason="stop", usage=usage)

        choice = chunk.choices[0]
        delta = choice.delta

        # 解析内容增量
        delta_content = delta.content if hasattr(delta, "content") else None

        # 解析工具调用增量
        delta_tool_call = None
        if hasattr(delta, "tool_calls") and delta.tool_calls:
            tc = delta.tool_calls[0]
            delta_tool_call = {
                "index": tc.index,
                "id": getattr(tc, "id", None),
                "type": getattr(tc, "type", None),
                "function": {
                    "name": getattr(tc.function, "name", None) if tc.function else None,
                    "arguments": getattr(tc.function, "arguments", "") if tc.function else "",
                },
            }

        return LLMStreamChunk(
            delta_content=delta_content,
            delta_tool_call=delta_tool_call,
            finish_reason=choice.finish_reason,
        )

    async def generate(
        self,
        messages: list[Message],
        tools: Optional[list[ToolDefinition]] = None,
        **kwargs,
    ) -> LLMResponse:
        """生成响应"""
        # 构建请求参数
        request_params: dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }

        # 添加工具
        if tools:
            request_params["tools"] = self._convert_tools(tools)
            request_params["tool_choice"] = kwargs.get("tool_choice", "auto")

        # 添加额外参数
        for key in ["top_p", "frequency_penalty", "presence_penalty", "stop", "seed"]:
            if key in kwargs:
                request_params[key] = kwargs[key]

        # 调用 API
        response = await self.async_client.chat.completions.create(**request_params)

        return self._parse_response(response)

    async def stream(
        self,
        messages: list[Message],
        tools: Optional[list[ToolDefinition]] = None,
        **kwargs,
    ) -> AsyncIterator[LLMStreamChunk]:
        """流式生成响应"""
        # 构建请求参数
        request_params: dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        # 添加工具
        if tools:
            request_params["tools"] = self._convert_tools(tools)
            request_params["tool_choice"] = kwargs.get("tool_choice", "auto")

        # 添加额外参数
        for key in ["top_p", "frequency_penalty", "presence_penalty", "stop", "seed"]:
            if key in kwargs:
                request_params[key] = kwargs[key]

        # 调用流式 API
        stream = await self.async_client.chat.completions.create(**request_params)

        async for chunk in stream:
            yield self._parse_stream_chunk(chunk)

    def count_tokens(self, text: str) -> int:
        """
        计算文本的 token 数量

        使用 tiktoken 进行精确计算（如果可用）。
        """
        try:
            import tiktoken

            # 获取对应模型的编码器
            try:
                encoding = tiktoken.encoding_for_model(self.model)
            except KeyError:
                # 回退到 cl100k_base（GPT-4 使用的编码器）
                encoding = tiktoken.get_encoding("cl100k_base")

            return len(encoding.encode(text))
        except ImportError:
            # 如果 tiktoken 不可用，使用估算
            return super().count_tokens(text)


class DeepSeekLLM(OpenAILLM):
    """
    DeepSeek LLM 适配器

    DeepSeek API 与 OpenAI 兼容，使用相同的接口。

    支持模型:
    - deepseek-chat: 通用对话模型
    - deepseek-reasoner: 推理增强模型（R1）
    """

    def __init__(
        self,
        model: str = "deepseek-reasoner",
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        **kwargs,
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )

    @property
    def provider_name(self) -> str:
        return "deepseek"


class KimiLLM(OpenAILLM):
    """
    Kimi (Moonshot AI) LLM 适配器

    Moonshot AI API 与 OpenAI 兼容，使用相同的接口。

    支持模型:
    - moonshot-v1-8k: 8K 上下文
    - moonshot-v1-32k: 32K 上下文
    - moonshot-v1-128k: 128K 上下文
    - kimi-k2-0711-preview: Kimi K2 预览版
    - kimi-latest: 最新版本

    示例:
    ------
    ```python
    llm = KimiLLM(
        model="kimi-latest",
        api_key="sk-xxx",
        temperature=0.7,
    )
    ```
    """

    def __init__(
        self,
        model: str = "kimi-latest",
        api_key: Optional[str] = None,
        base_url: str = "https://api.moonshot.cn/v1",
        **kwargs,
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )

    @property
    def provider_name(self) -> str:
        return "kimi"


class AzureOpenAILLM(BaseLLM):
    """
    Azure OpenAI LLM 适配器

    用于 Azure OpenAI Service。
    """

    def __init__(
        self,
        model: str,  # Azure 中称为 deployment_name
        api_key: Optional[str] = None,
        azure_endpoint: Optional[str] = None,
        api_version: str = "2024-02-15-preview",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 60,
        max_retries: int = 3,
        **kwargs,
    ):
        self.azure_endpoint = azure_endpoint
        self.api_version = api_version
        super().__init__(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )

    @property
    def provider_name(self) -> str:
        return "azure_openai"

    def _init_client(self) -> Any:
        """初始化同步客户端"""
        try:
            from openai import AzureOpenAI
        except ImportError:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )

        return AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.azure_endpoint,
            api_version=self.api_version,
            timeout=float(self.timeout),
            max_retries=self.max_retries,
        )

    def _init_async_client(self) -> Any:
        """初始化异步客户端"""
        try:
            from openai import AsyncAzureOpenAI
        except ImportError:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )

        return AsyncAzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.azure_endpoint,
            api_version=self.api_version,
            timeout=float(self.timeout),
            max_retries=self.max_retries,
        )

    # 继承 OpenAILLM 的消息转换和解析方法
    _convert_messages = OpenAILLM._convert_messages
    _convert_tools = OpenAILLM._convert_tools
    _parse_response = OpenAILLM._parse_response
    _parse_stream_chunk = OpenAILLM._parse_stream_chunk
    _parse_tool_calls = OpenAILLM._parse_tool_calls
    generate = OpenAILLM.generate
    stream = OpenAILLM.stream
