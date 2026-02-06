"""
LLM Provider Abstraction Layer
==============================

提供统一的 LLM 接口抽象，支持多种 LLM 提供商。

支持的提供商:
- OpenAI (GPT-4o, GPT-4o-mini, etc.)
- Anthropic (Claude 3.5 Sonnet, Claude 3 Opus, etc.)
- DeepSeek (DeepSeek Chat, DeepSeek Coder)
- Ollama (本地模型)

使用示例:
---------
```python
from services.agent.llm import create_llm, BaseLLM
from services.agent.config import LLMConfig

config = LLMConfig(provider="openai", model="gpt-4o-mini")
llm = create_llm(config)

# 同步调用
response = await llm.generate(messages=[...])

# 流式调用
async for chunk in llm.stream(messages=[...]):
    print(chunk.content)
```
"""

from services.agent.llm.base import (
    BaseLLM,
    LLMResponse,
    LLMStreamChunk,
)
from services.agent.llm.factory import create_llm

__all__ = [
    "BaseLLM",
    "LLMResponse",
    "LLMStreamChunk",
    "create_llm",
]
