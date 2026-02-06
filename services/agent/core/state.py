"""
Agent 状态管理

定义 Agent 运行时的状态结构，用于在各组件间传递上下文。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


class MessageRole(str, Enum):
    """消息角色枚举"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class AgentStatus(str, Enum):
    """Agent 状态枚举"""
    IDLE = "idle"
    THINKING = "thinking"
    CALLING_TOOL = "calling_tool"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class Message:
    """对话消息"""
    role: MessageRole
    content: str
    id: str = field(default_factory=lambda: str(uuid4()))
    name: Optional[str] = None  # 工具名称（当 role=tool 时）
    tool_call_id: Optional[str] = None  # 关联的工具调用 ID
    tool_calls: list[ToolCall] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        result = {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }
        if self.name:
            result["name"] = self.name
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """从字典创建消息"""
        tool_calls = [
            ToolCall.from_dict(tc) for tc in data.get("tool_calls", [])
        ]
        return cls(
            id=data.get("id", str(uuid4())),
            role=MessageRole(data["role"]),
            content=data.get("content", ""),
            name=data.get("name"),
            tool_call_id=data.get("tool_call_id"),
            tool_calls=tool_calls,
            metadata=data.get("metadata", {}),
        )


@dataclass
class ToolCall:
    """工具调用记录"""
    id: str
    name: str
    arguments: dict[str, Any]
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def duration_ms(self) -> Optional[float]:
        """计算工具调用耗时（毫秒）"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() * 1000
        return None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        result = {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
        }
        if self.result is not None:
            result["result"] = self.result
        if self.error is not None:
            result["error"] = self.error
        if self.started_at:
            result["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            result["completed_at"] = self.completed_at.isoformat()
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCall:
        """从字典创建工具调用记录"""
        return cls(
            id=data["id"],
            name=data["name"],
            arguments=data.get("arguments", {}),
            result=data.get("result"),
            error=data.get("error"),
        )


@dataclass
class UserContext:
    """用户上下文信息"""
    user_id: UUID
    username: Optional[str] = None
    display_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # 缓存的用户数据（运行时填充）
    positions: list[dict[str, Any]] = field(default_factory=list)
    watchlist: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": str(self.user_id),
            "username": self.username,
            "display_id": self.display_id,
            "metadata": self.metadata,
            "positions": self.positions,
            "watchlist": self.watchlist,
        }


@dataclass
class AgentState:
    """
    Agent 运行状态

    包含对话历史、用户上下文、工具调用记录等。
    """
    # 会话标识
    session_id: str = field(default_factory=lambda: str(uuid4()))

    # 对话历史
    messages: list[Message] = field(default_factory=list)

    # 用户上下文（可选）
    user_context: Optional[UserContext] = None

    # 当前状态
    status: AgentStatus = AgentStatus.IDLE

    # 工具调用记录（当前请求）
    tool_calls: list[ToolCall] = field(default_factory=list)

    # 迭代计数
    iteration: int = 0

    # 错误信息
    error: Optional[str] = None

    # 元数据
    metadata: dict[str, Any] = field(default_factory=dict)

    # 时间戳
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_message(self, message: Message) -> None:
        """添加消息到历史"""
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)

    def add_user_message(self, content: str, **kwargs) -> Message:
        """添加用户消息"""
        message = Message(role=MessageRole.USER, content=content, **kwargs)
        self.add_message(message)
        return message

    def add_assistant_message(self, content: str, **kwargs) -> Message:
        """添加助手消息"""
        message = Message(role=MessageRole.ASSISTANT, content=content, **kwargs)
        self.add_message(message)
        return message

    def add_tool_message(
        self,
        content: str,
        name: str,
        tool_call_id: str,
        **kwargs,
    ) -> Message:
        """添加工具消息"""
        message = Message(
            role=MessageRole.TOOL,
            content=content,
            name=name,
            tool_call_id=tool_call_id,
            **kwargs,
        )
        self.add_message(message)
        return message

    def add_tool_call(self, tool_call: ToolCall) -> None:
        """添加工具调用记录"""
        self.tool_calls.append(tool_call)
        self.updated_at = datetime.now(timezone.utc)

    def get_last_message(self) -> Optional[Message]:
        """获取最后一条消息"""
        return self.messages[-1] if self.messages else None

    def get_messages_for_llm(self) -> list[dict[str, Any]]:
        """获取用于 LLM 的消息格式"""
        return [msg.to_dict() for msg in self.messages]

    def clear_tool_calls(self) -> None:
        """清空当前工具调用记录"""
        self.tool_calls = []

    def reset(self) -> None:
        """重置状态（保留会话 ID 和用户上下文）"""
        self.messages = []
        self.tool_calls = []
        self.iteration = 0
        self.status = AgentStatus.IDLE
        self.error = None
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "user_context": self.user_context.to_dict() if self.user_context else None,
            "status": self.status.value,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "iteration": self.iteration,
            "error": self.error,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentState:
        """从字典创建状态"""
        messages = [Message.from_dict(m) for m in data.get("messages", [])]
        tool_calls = [ToolCall.from_dict(tc) for tc in data.get("tool_calls", [])]

        user_context = None
        if data.get("user_context"):
            uc = data["user_context"]
            user_context = UserContext(
                user_id=UUID(uc["user_id"]),
                username=uc.get("username"),
                display_id=uc.get("display_id"),
                metadata=uc.get("metadata", {}),
            )

        return cls(
            session_id=data.get("session_id", str(uuid4())),
            messages=messages,
            user_context=user_context,
            status=AgentStatus(data.get("status", "idle")),
            tool_calls=tool_calls,
            iteration=data.get("iteration", 0),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class StreamChunk:
    """流式响应块"""
    type: str  # text, tool_call, tool_result, error, done
    content: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        result = {"type": self.type}
        if self.content is not None:
            result["content"] = self.content
        if self.tool_call is not None:
            result["tool_call"] = self.tool_call.to_dict()
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    def to_sse(self) -> str:
        """转换为 SSE 格式"""
        import json
        return f"data: {json.dumps(self.to_dict())}\n\n"
