"""
Agent 模块配置管理

使用 pydantic-settings 进行环境变量管理
"""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """LLM 提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"
    KIMI = "kimi"  # Moonshot AI


class SearchProvider(str, Enum):
    """搜索提供商枚举"""
    TAVILY = "tavily"
    SERPER = "serper"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"


class MCPTransport(str, Enum):
    """MCP 传输层类型"""
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


class MemoryType(str, Enum):
    """记忆存储类型"""
    MEMORY = "memory"
    REDIS = "redis"
    POSTGRES = "postgres"


class LLMConfig(BaseSettings):
    """LLM 配置"""
    model_config = SettingsConfigDict(
        env_prefix="AGENT_LLM_",
        env_file=".env",
        extra="ignore",
    )

    provider: LLMProvider = Field(
        default=LLMProvider.DEEPSEEK,
        description="LLM 提供商",
    )
    model: str = Field(
        default="deepseek-reasoner",
        description="模型名称",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="温度参数",
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=128000,
        description="最大 token 数",
    )
    timeout: int = Field(
        default=60,
        ge=1,
        description="请求超时时间（秒）",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="最大重试次数",
    )


class FallbackLLMConfig(BaseSettings):
    """备用 LLM 配置（用于主模型失败时的降级）"""
    model_config = SettingsConfigDict(
        env_prefix="AGENT_FALLBACK_LLM_",
        env_file=".env",
        extra="ignore",
    )

    enabled: bool = Field(
        default=True,
        description="是否启用备用模型",
    )
    provider: LLMProvider = Field(
        default=LLMProvider.KIMI,
        description="备用 LLM 提供商",
    )
    model: str = Field(
        default="kimi-latest",
        description="备用模型名称",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="温度参数",
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=128000,
        description="最大 token 数",
    )


class SubAgentLLMConfig(BaseSettings):
    """子代理 LLM 配置"""
    model_config = SettingsConfigDict(
        env_prefix="AGENT_SUBAGENT_LLM_",
        env_file=".env",
        extra="ignore",
    )

    provider: LLMProvider = Field(
        default=LLMProvider.KIMI,
        description="子代理 LLM 提供商",
    )
    model: str = Field(
        default="kimi-latest",
        description="子代理模型名称（Kimi K2.5）",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="温度参数",
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=128000,
        description="最大 token 数",
    )


class APIKeysConfig(BaseSettings):
    """API 密钥配置"""
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    openai_api_key: Optional[str] = Field(
        default=None,
        alias="OPENAI_API_KEY",
        description="OpenAI API Key",
    )
    openai_base_url: Optional[str] = Field(
        default=None,
        alias="OPENAI_BASE_URL",
        description="OpenAI API Base URL（用于代理或兼容服务）",
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        alias="ANTHROPIC_API_KEY",
        description="Anthropic API Key",
    )
    deepseek_api_key: Optional[str] = Field(
        default=None,
        alias="DEEPSEEK_API_KEY",
        description="DeepSeek API Key",
    )
    kimi_api_key: Optional[str] = Field(
        default=None,
        alias="KIMI_API_KEY",
        description="Kimi (Moonshot) API Key",
    )
    tavily_api_key: Optional[str] = Field(
        default=None,
        alias="TAVILY_API_KEY",
        description="Tavily Search API Key",
    )
    serper_api_key: Optional[str] = Field(
        default=None,
        alias="SERPER_API_KEY",
        description="Serper Search API Key",
    )


class SearchConfig(BaseSettings):
    """搜索配置"""
    model_config = SettingsConfigDict(
        env_prefix="AGENT_SEARCH_",
        env_file=".env",
        extra="ignore",
    )

    provider: SearchProvider = Field(
        default=SearchProvider.TAVILY,
        description="搜索提供商",
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="最大搜索结果数",
    )
    include_domains: list[str] = Field(
        default_factory=list,
        description="限制搜索的域名列表",
    )
    exclude_domains: list[str] = Field(
        default_factory=list,
        description="排除的域名列表",
    )
    search_depth: str = Field(
        default="basic",
        description="搜索深度: basic / advanced",
    )


class MCPConfig(BaseSettings):
    """MCP 配置"""
    model_config = SettingsConfigDict(
        env_prefix="AGENT_MCP_",
        env_file=".env",
        extra="ignore",
    )

    enabled: bool = Field(
        default=True,
        description="是否启用 MCP",
    )
    transport: MCPTransport = Field(
        default=MCPTransport.HTTP,
        description="传输层类型",
    )
    host: str = Field(
        default="127.0.0.1",
        description="MCP 服务器主机",
    )
    port: int = Field(
        default=3001,
        ge=1,
        le=65535,
        description="MCP 服务器端口",
    )


class MemoryConfig(BaseSettings):
    """记忆配置"""
    model_config = SettingsConfigDict(
        env_prefix="AGENT_MEMORY_",
        env_file=".env",
        extra="ignore",
    )

    type: MemoryType = Field(
        default=MemoryType.MEMORY,
        description="记忆存储类型",
    )
    ttl_sec: int = Field(
        default=3600,
        ge=0,
        description="记忆过期时间（秒），0 表示永不过期",
    )
    max_messages: int = Field(
        default=100,
        ge=1,
        description="最大记忆消息数",
    )
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis 连接 URL",
    )


class AgentConfig(BaseSettings):
    """Agent 主配置"""
    model_config = SettingsConfigDict(
        env_prefix="AGENT_",
        env_file=".env",
        extra="ignore",
    )

    # 功能开关
    enable_web_search: bool = Field(
        default=True,
        description="是否启用网络搜索",
    )
    enable_tools: bool = Field(
        default=True,
        description="是否启用工具调用",
    )
    enable_sub_agents: bool = Field(
        default=True,
        description="是否启用子代理",
    )
    enable_memory: bool = Field(
        default=True,
        description="是否启用记忆系统",
    )

    # 行为配置
    max_iterations: int = Field(
        default=10,
        ge=1,
        le=50,
        description="最大迭代次数（防止无限循环）",
    )
    max_tool_calls: int = Field(
        default=20,
        ge=1,
        le=100,
        description="单次请求最大工具调用次数",
    )
    streaming: bool = Field(
        default=True,
        description="默认是否启用流式响应",
    )

    # 系统提示
    system_prompt: str = Field(
        default="""你是 U0 平台的智能投资助手，专注于基金投资领域。

你的能力包括：
1. 查询和分析用户的基金持仓
2. 获取基金净值、估值和行情数据
3. 搜索最新的财经新闻和市场动态
4. 提供专业的投资分析和建议

请用专业、准确、友好的语气与用户交流。在提供投资建议时，请注意风险提示。""",
        description="系统提示词",
    )

    # 子配置
    llm: LLMConfig = Field(default_factory=LLMConfig)
    fallback_llm: FallbackLLMConfig = Field(default_factory=FallbackLLMConfig)
    subagent_llm: SubAgentLLMConfig = Field(default_factory=SubAgentLLMConfig)
    api_keys: APIKeysConfig = Field(default_factory=APIKeysConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)

    def _get_api_key_for_provider(self, provider: LLMProvider) -> Optional[str]:
        """获取指定提供商的 API Key"""
        provider_key_map = {
            LLMProvider.OPENAI: self.api_keys.openai_api_key,
            LLMProvider.ANTHROPIC: self.api_keys.anthropic_api_key,
            LLMProvider.DEEPSEEK: self.api_keys.deepseek_api_key,
            LLMProvider.KIMI: self.api_keys.kimi_api_key,
            LLMProvider.OLLAMA: None,  # Ollama 不需要 API Key
        }
        return provider_key_map.get(provider)

    def get_llm_api_key(self) -> Optional[str]:
        """获取主 LLM 提供商的 API Key"""
        return self._get_api_key_for_provider(self.llm.provider)

    def get_fallback_llm_api_key(self) -> Optional[str]:
        """获取备用 LLM 提供商的 API Key"""
        return self._get_api_key_for_provider(self.fallback_llm.provider)

    def get_subagent_llm_api_key(self) -> Optional[str]:
        """获取子代理 LLM 提供商的 API Key"""
        return self._get_api_key_for_provider(self.subagent_llm.provider)

    def get_search_api_key(self) -> Optional[str]:
        """获取当前搜索提供商的 API Key"""
        provider_key_map = {
            SearchProvider.TAVILY: self.api_keys.tavily_api_key,
            SearchProvider.SERPER: self.api_keys.serper_api_key,
            SearchProvider.BING: None,
            SearchProvider.DUCKDUCKGO: None,
        }
        return provider_key_map.get(self.search.provider)


@lru_cache()
def get_config() -> AgentConfig:
    """获取 Agent 配置单例"""
    return AgentConfig()


# 便捷访问
config = get_config()
