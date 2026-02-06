"""
MCP (Model Context Protocol) 协议核心定义

基于 Anthropic 的 MCP 规范实现，提供 Agent 与外部资源交互的标准化接口。

MCP 协议版本: 1.0
参考: https://modelcontextprotocol.io/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional, Union
from uuid import uuid4


# ============================================================================
# Protocol Constants
# ============================================================================

MCP_VERSION = "1.0"
MCP_PROTOCOL_VERSION = "2024-11-05"


# ============================================================================
# Message Types
# ============================================================================

class MCPMessageType(str, Enum):
    """MCP 消息类型"""
    # 初始化
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"

    # 资源相关
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    RESOURCES_UNSUBSCRIBE = "resources/unsubscribe"

    # 工具相关
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"

    # 提示相关
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"

    # 采样相关
    SAMPLING_CREATE = "sampling/createMessage"

    # 通知
    NOTIFICATION = "notification"
    PROGRESS = "progress"

    # 错误
    ERROR = "error"


class MCPErrorCode(str, Enum):
    """MCP 错误码"""
    PARSE_ERROR = "ParseError"
    INVALID_REQUEST = "InvalidRequest"
    METHOD_NOT_FOUND = "MethodNotFound"
    INVALID_PARAMS = "InvalidParams"
    INTERNAL_ERROR = "InternalError"
    RESOURCE_NOT_FOUND = "ResourceNotFound"
    TOOL_NOT_FOUND = "ToolNotFound"
    PROMPT_NOT_FOUND = "PromptNotFound"


# ============================================================================
# Base Message Structure
# ============================================================================

@dataclass
class MCPMessage:
    """MCP 消息基类"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        result = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            result["id"] = self.id
        return result


@dataclass
class MCPRequest(MCPMessage):
    """MCP 请求消息"""
    method: str = ""
    params: Optional[dict[str, Any]] = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid4())

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["method"] = self.method
        if self.params is not None:
            result["params"] = self.params
        return result


@dataclass
class MCPResponse(MCPMessage):
    """MCP 响应消息"""
    result: Optional[Any] = None
    error: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.error is not None:
            result["error"] = self.error
        else:
            result["result"] = self.result
        return result


@dataclass
class MCPNotification(MCPMessage):
    """MCP 通知消息（无需响应）"""
    method: str = ""
    params: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        result = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            result["params"] = self.params
        return result


@dataclass
class MCPError:
    """MCP 错误"""
    code: MCPErrorCode
    message: str
    data: Optional[Any] = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "code": self.code.value,
            "message": self.message,
        }
        if self.data is not None:
            result["data"] = self.data
        return result


# ============================================================================
# Resources
# ============================================================================

@dataclass
class MCPResource:
    """MCP 资源"""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "uri": self.uri,
            "name": self.name,
        }
        if self.description:
            result["description"] = self.description
        if self.mime_type:
            result["mimeType"] = self.mime_type
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class MCPResourceContent:
    """MCP 资源内容"""
    uri: str
    mime_type: str
    text: Optional[str] = None
    blob: Optional[str] = None  # Base64 encoded
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "uri": self.uri,
            "mimeType": self.mime_type,
        }
        if self.text is not None:
            result["text"] = self.text
        if self.blob is not None:
            result["blob"] = self.blob
        if self.metadata:
            result["metadata"] = self.metadata
        return result


# ============================================================================
# Tools
# ============================================================================

@dataclass
class MCPToolParameter:
    """MCP 工具参数"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[list[Any]] = None

    def to_json_schema(self) -> dict[str, Any]:
        """转换为 JSON Schema 格式"""
        schema = {
            "type": self.type,
            "description": self.description,
        }
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        return schema


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class MCPToolCall:
    """MCP 工具调用"""
    name: str
    arguments: dict[str, Any]
    call_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "arguments": self.arguments,
        }


@dataclass
class MCPToolResult:
    """MCP 工具调用结果"""
    call_id: str
    content: list[dict[str, Any]]
    is_error: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "content": self.content,
            "isError": self.is_error,
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result


# ============================================================================
# Prompts
# ============================================================================

@dataclass
class MCPPromptArgument:
    """MCP 提示参数"""
    name: str
    description: str
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "required": self.required,
        }


@dataclass
class MCPPrompt:
    """MCP 提示模板"""
    name: str
    description: str
    arguments: list[MCPPromptArgument] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "name": self.name,
            "description": self.description,
        }
        if self.arguments:
            result["arguments"] = [arg.to_dict() for arg in self.arguments]
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class MCPPromptMessage:
    """MCP 提示消息"""
    role: Literal["system", "user", "assistant"]
    content: Union[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
        }


# ============================================================================
# Sampling
# ============================================================================

@dataclass
class MCPSamplingRequest:
    """MCP 采样请求"""
    messages: list[dict[str, Any]]
    model_preferences: Optional[dict[str, Any]] = None
    system_prompt: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stop_sequences: Optional[list[str]] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {"messages": self.messages}
        if self.model_preferences:
            result["modelPreferences"] = self.model_preferences
        if self.system_prompt:
            result["systemPrompt"] = self.system_prompt
        if self.max_tokens is not None:
            result["maxTokens"] = self.max_tokens
        if self.temperature is not None:
            result["temperature"] = self.temperature
        if self.stop_sequences:
            result["stopSequences"] = self.stop_sequences
        if self.metadata:
            result["metadata"] = self.metadata
        return result


# ============================================================================
# Progress & Notifications
# ============================================================================

@dataclass
class MCPProgress:
    """MCP 进度通知"""
    progress: float
    total: Optional[float] = None
    message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        result = {"progress": self.progress}
        if self.total is not None:
            result["total"] = self.total
        if self.message:
            result["message"] = self.message
        return result


# ============================================================================
# Server Capabilities
# ============================================================================

@dataclass
class MCPServerCapabilities:
    """MCP 服务端能力"""
    resources: bool = False
    tools: bool = False
    prompts: bool = False
    sampling: bool = False
    experimental: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {}
        if self.resources:
            result["resources"] = {"subscribe": True}
        if self.tools:
            result["tools"] = {}
        if self.prompts:
            result["prompts"] = {}
        if self.sampling:
            result["sampling"] = {}
        if self.experimental:
            result["experimental"] = self.experimental
        return result


@dataclass
class MCPClientCapabilities:
    """MCP 客户端能力"""
    sampling: bool = False
    roots: bool = False
    experimental: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {}
        if self.sampling:
            result["sampling"] = {}
        if self.roots:
            result["roots"] = {"listChanged": True}
        if self.experimental:
            result["experimental"] = self.experimental
        return result


# ============================================================================
# Initialize
# ============================================================================

@dataclass
class MCPInitializeParams:
    """MCP 初始化参数"""
    protocol_version: str
    capabilities: MCPClientCapabilities
    client_info: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocolVersion": self.protocol_version,
            "capabilities": self.capabilities.to_dict(),
            "clientInfo": self.client_info,
        }


@dataclass
class MCPInitializeResult:
    """MCP 初始化结果"""
    protocol_version: str
    capabilities: MCPServerCapabilities
    server_info: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocolVersion": self.protocol_version,
            "capabilities": self.capabilities.to_dict(),
            "serverInfo": self.server_info,
        }


# ============================================================================
# Helper Functions
# ============================================================================

def create_request(
    method: str,
    params: Optional[dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> MCPRequest:
    """创建 MCP 请求"""
    return MCPRequest(
        id=request_id or str(uuid4()),
        method=method,
        params=params,
    )


def create_response(
    request_id: str,
    result: Optional[Any] = None,
    error: Optional[MCPError] = None,
) -> MCPResponse:
    """创建 MCP 响应"""
    return MCPResponse(
        id=request_id,
        result=result,
        error=error.to_dict() if error else None,
    )


def create_notification(
    method: str,
    params: Optional[dict[str, Any]] = None,
) -> MCPNotification:
    """创建 MCP 通知"""
    return MCPNotification(
        method=method,
        params=params,
    )


def create_error_response(
    request_id: str,
    code: MCPErrorCode,
    message: str,
    data: Optional[Any] = None,
) -> MCPResponse:
    """创建错误响应"""
    error = MCPError(code=code, message=message, data=data)
    return create_response(request_id, error=error)
