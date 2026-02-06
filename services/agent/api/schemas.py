"""
Agent API Schemas

定义 Agent API 的请求和响应数据模型。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """对话消息"""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


class ToolCallRequest(BaseModel):
    """工具调用"""
    id: str
    name: str
    arguments: dict[str, Any]


class ChatRequest(BaseModel):
    """聊天请求"""
    messages: list[ChatMessage]
    stream: bool = Field(default=True, description="是否启用流式响应")
    user_id: Optional[str] = Field(default=None, description="用户 ID")
    session_id: Optional[str] = Field(default=None, description="会话 ID")
    max_iterations: Optional[int] = Field(default=None, description="最大迭代次数")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    metadata: Optional[dict[str, Any]] = Field(default=None, description="额外元数据")


class ToolCallResponse(BaseModel):
    """工具调用响应"""
    id: str
    name: str
    arguments: dict[str, Any]
    result: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None


class UsageInfo(BaseModel):
    """Token 使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    """聊天响应（非流式）"""
    content: str
    tool_calls: list[ToolCallResponse] = Field(default_factory=list)
    usage: Optional[UsageInfo] = None
    duration_ms: Optional[float] = None
    session_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class StreamChunkType(str, Enum):
    """流式响应块类型"""
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    DONE = "done"


class StreamChunk(BaseModel):
    """流式响应块"""
    type: StreamChunkType
    content: Optional[str] = None
    tool_call: Optional[ToolCallResponse] = None
    metadata: Optional[dict[str, Any]] = None


class ToolInfo(BaseModel):
    """工具信息"""
    name: str
    description: str
    category: str
    parameters: dict[str, Any]
    tags: list[str] = Field(default_factory=list)


class SkillInfo(BaseModel):
    """技能信息"""
    name: str
    description: str
    required_tools: list[str] = Field(default_factory=list)
    optional_tools: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class AgentStatusResponse(BaseModel):
    """Agent 状态响应"""
    status: str
    version: str
    llm_provider: str
    llm_model: str
    tools_count: int
    skills_count: int = 0
    features: dict[str, bool]
    uptime_seconds: Optional[float] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    message: str
    details: Optional[dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
