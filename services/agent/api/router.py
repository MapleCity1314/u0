"""
Agent API Router

提供 Agent 的 FastAPI 路由接口。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sse_starlette import EventSourceResponse

from services.agent.api.schemas import (
    AgentStatusResponse,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    SkillInfo,
    StreamChunk,
    StreamChunkType,
    ToolInfo,
    UsageInfo,
)
from services.agent.config import get_config
from services.agent.core.agent import Agent
from services.agent.core.state import StreamChunk as AgentStreamChunk
from services.agent.tools.registry import get_default_registry

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/agent", tags=["agent"])

# Agent 实例（全局单例）
_agent_instance: Optional[Agent] = None
_agent_start_time: float = time.time()


def get_agent() -> Agent:
    """获取或创建 Agent 实例"""
    global _agent_instance
    if _agent_instance is None:
        config = get_config()
        _agent_instance = Agent(config)
        logger.info(f"Agent initialized: {_agent_instance}")
    return _agent_instance


def get_user_id(request: Request) -> Optional[str]:
    """从请求中提取用户 ID"""
    # 从 Authorization header 或 session 中提取
    # 这里需要根据实际的认证系统调整
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        # 解析 JWT token 获取 user_id
        # 简化实现：直接从 header 中读取
        return request.headers.get("x-user-id")
    return None


async def convert_agent_stream_to_sse(
    stream: AsyncIterator[AgentStreamChunk],
) -> AsyncIterator[str]:
    """
    将 Agent 流式响应转换为 SSE 格式

    Args:
        stream: Agent 流式响应

    Yields:
        SSE 格式的消息
    """
    try:
        async for chunk in stream:
            # 转换为 API schema
            api_chunk = StreamChunk(
                type=StreamChunkType(chunk.type),
                content=chunk.content,
                tool_call=chunk.tool_call.to_dict() if chunk.tool_call else None,
                metadata=chunk.metadata,
            )

            # 转换为 SSE 格式
            data = api_chunk.model_dump_json(exclude_none=True)
            yield f"data: {data}\n\n"

    except Exception as e:
        logger.error(f"Stream error: {e}", exc_info=True)
        error_chunk = StreamChunk(
            type=StreamChunkType.ERROR,
            content=str(e),
        )
        yield f"data: {error_chunk.model_dump_json()}\n\n"


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: Agent = Depends(get_agent),
    user_id: Optional[str] = Depends(get_user_id),
) -> ChatResponse:
    """
    对话接口（非流式）

    处理用户消息并返回完整响应。
    """
    try:
        # 转换消息格式
        messages = [
            {
                "role": msg.role.value,
                "content": msg.content,
                "name": msg.name,
                "tool_call_id": msg.tool_call_id,
            }
            for msg in request.messages
        ]

        # 调用 Agent
        response = await agent.chat(
            messages=messages,
            user_id=user_id or request.user_id,
            session_id=request.session_id,
            max_iterations=request.max_iterations,
            metadata=request.metadata or {},
        )

        # 转换响应
        return ChatResponse(
            content=response.content,
            tool_calls=[
                {
                    "id": tc.id,
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "result": tc.result,
                    "error": tc.error,
                    "duration_ms": tc.duration_ms,
                }
                for tc in response.tool_calls
            ],
            usage=UsageInfo(**response.usage) if response.usage else None,
            duration_ms=response.duration_ms,
            session_id=response.state.session_id if response.state else None,
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    agent: Agent = Depends(get_agent),
    user_id: Optional[str] = Depends(get_user_id),
):
    """
    对话接口（流式）

    使用 Server-Sent Events (SSE) 流式返回响应。
    """
    try:
        # 转换消息格式
        messages = [
            {
                "role": msg.role.value,
                "content": msg.content,
                "name": msg.name,
                "tool_call_id": msg.tool_call_id,
            }
            for msg in request.messages
        ]

        # 创建流式响应
        stream = agent.stream(
            messages=messages,
            user_id=user_id or request.user_id,
            session_id=request.session_id,
            max_iterations=request.max_iterations,
            metadata=request.metadata or {},
        )

        # 转换为 SSE 格式并返回
        return EventSourceResponse(
            convert_agent_stream_to_sse(stream),
            media_type="text/event-stream",
        )

    except Exception as e:
        logger.error(f"Stream error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools", response_model=list[ToolInfo])
async def list_tools(
    category: Optional[str] = None,
    tag: Optional[str] = None,
) -> list[ToolInfo]:
    """
    获取可用工具列表

    Args:
        category: 按分类过滤
        tag: 按标签过滤
    """
    try:
        registry = get_default_registry()

        # 获取工具列表
        tools = registry.list_tools()

        # 应用过滤
        if category:
            tools = [t for t in tools if t.category.value == category]
        if tag:
            tools = [t for t in tools if tag in t.tags]

        # 转换为响应格式
        return [
            ToolInfo(
                name=tool.name,
                description=tool.description,
                category=tool.category.value,
                parameters=tool.definition.to_json_schema(),
                tags=tool.tags,
            )
            for tool in tools
        ]

    except Exception as e:
        logger.error(f"List tools error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/skills", response_model=list[SkillInfo])
async def list_skills(
    tag: Optional[str] = None,
) -> list[SkillInfo]:
    """
    获取可用技能列表

    Args:
        tag: 按标签过滤
    """
    try:
        from services.agent.skills.registry import get_default_skill_registry

        registry = get_default_skill_registry()

        # 获取技能信息
        skills_info = registry.list_skill_info(tags=[tag] if tag else None)

        # 转换为响应格式
        return [
            SkillInfo(
                name=info["name"],
                description=info["description"],
                required_tools=info["required_tools"],
                optional_tools=info["optional_tools"],
                tags=info["tags"],
            )
            for info in skills_info
        ]

    except Exception as e:
        logger.error(f"List skills error: {e}", exc_info=True)
        # 如果技能注册表不可用，返回空列表
        return []


@router.get("/status", response_model=AgentStatusResponse)
async def get_status(
    agent: Agent = Depends(get_agent),
) -> AgentStatusResponse:
    """获取 Agent 状态"""
    try:
        config = get_config()
        registry = get_default_registry()

        # 尝试获取技能数量
        skills_count = 0
        try:
            from services.agent.skills.registry import get_default_skill_registry
            skills_registry = get_default_skill_registry()
            skills_count = len(skills_registry)
        except Exception:
            pass

        return AgentStatusResponse(
            status="running",
            version="0.1.0",
            llm_provider=config.llm.provider.value,
            llm_model=config.llm.model,
            tools_count=len(registry),
            skills_count=skills_count,
            features={
                "web_search": config.enable_web_search,
                "tools": config.enable_tools,
                "sub_agents": config.enable_sub_agents,
                "memory": config.enable_memory,
                "streaming": config.streaming,
            },
            uptime_seconds=time.time() - _agent_start_time,
        )

    except Exception as e:
        logger.error(f"Status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": time.time()}


def setup_agent_routes(app) -> None:
    """
    设置 Agent 路由

    Args:
        app: FastAPI 应用实例
    """
    app.include_router(router)
    logger.info("Agent routes registered")
