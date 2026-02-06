"""
LLM 工厂模块

提供统一的 LLM 实例创建接口。

支持的 LLM 提供商:
- OpenAI (GPT-4o, GPT-4o-mini 等)
- Anthropic (Claude 3.5 等)
- DeepSeek (deepseek-chat, deepseek-reasoner)
- Kimi/Moonshot (kimi-latest, moonshot-v1-* 等)
- Ollama (本地模型)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from services.agent.config import LLMConfig, LLMProvider, APIKeysConfig

if TYPE_CHECKING:
    from services.agent.llm.base import BaseLLM


def create_llm(
    config: Optional[LLMConfig] = None,
    api_keys: Optional[APIKeysConfig] = None,
    **kwargs,
) -> "BaseLLM":
    """
    创建 LLM 实例

    根据配置创建对应提供商的 LLM 实例。

    Args:
        config: LLM 配置，如果为 None 则使用默认配置
        api_keys: API 密钥配置，如果为 None 则使用默认配置
        **kwargs: 额外参数，会覆盖配置中的值

    Returns:
        LLM 实例

    Raises:
        ValueError: 不支持的 LLM 提供商
        ImportError: 缺少必要的依赖包

    示例:
    ------
    ```python
    # 使用默认配置
    llm = create_llm()

    # 使用自定义配置
    config = LLMConfig(provider="anthropic", model="claude-3-5-sonnet-20241022")
    llm = create_llm(config)

    # 使用参数覆盖
    llm = create_llm(temperature=0.5, max_tokens=2048)
    ```
    """
    # 加载默认配置
    if config is None:
        config = LLMConfig()
    if api_keys is None:
        api_keys = APIKeysConfig()

    # 合并参数
    llm_params = {
        "model": kwargs.get("model", config.model),
        "temperature": kwargs.get("temperature", config.temperature),
        "max_tokens": kwargs.get("max_tokens", config.max_tokens),
        "timeout": kwargs.get("timeout", config.timeout),
        "max_retries": kwargs.get("max_retries", config.max_retries),
    }

    # 根据提供商创建实例
    provider = kwargs.get("provider", config.provider)
    if isinstance(provider, str):
        provider = LLMProvider(provider)

    if provider == LLMProvider.OPENAI:
        from services.agent.llm.openai import OpenAILLM

        return OpenAILLM(
            api_key=kwargs.get("api_key", api_keys.openai_api_key),
            base_url=kwargs.get("base_url", api_keys.openai_base_url),
            **llm_params,
        )

    elif provider == LLMProvider.ANTHROPIC:
        raise NotImplementedError(f"Anthropic provider not yet implemented")

    elif provider == LLMProvider.DEEPSEEK:
        from services.agent.llm.openai import DeepSeekLLM

        return DeepSeekLLM(
            api_key=kwargs.get("api_key", api_keys.deepseek_api_key),
            **llm_params,
        )

    elif provider == LLMProvider.KIMI:
        from services.agent.llm.openai import KimiLLM

        return KimiLLM(
            api_key=kwargs.get("api_key", api_keys.kimi_api_key),
            **llm_params,
        )

    elif provider == LLMProvider.OLLAMA:
        raise NotImplementedError(f"Ollama provider not yet implemented")

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def create_llm_from_env(**kwargs) -> "BaseLLM":
    """
    从环境变量创建 LLM 实例

    这是一个便捷函数，会自动从环境变量加载配置。

    Args:
        **kwargs: 额外参数，会覆盖环境变量中的值

    Returns:
        LLM 实例
    """
    from services.agent.config import get_config

    agent_config = get_config()
    return create_llm(
        config=agent_config.llm,
        api_keys=agent_config.api_keys,
        **kwargs,
    )


# 提供商别名映射
PROVIDER_ALIASES = {
    # OpenAI
    "gpt": LLMProvider.OPENAI,
    "gpt-4": LLMProvider.OPENAI,
    "gpt-4o": LLMProvider.OPENAI,
    "gpt-4o-mini": LLMProvider.OPENAI,
    # Anthropic
    "claude": LLMProvider.ANTHROPIC,
    "claude-3": LLMProvider.ANTHROPIC,
    "sonnet": LLMProvider.ANTHROPIC,
    "opus": LLMProvider.ANTHROPIC,
    # DeepSeek
    "deepseek": LLMProvider.DEEPSEEK,
    "deepseek-chat": LLMProvider.DEEPSEEK,
    "deepseek-reasoner": LLMProvider.DEEPSEEK,
    # Kimi / Moonshot
    "kimi": LLMProvider.KIMI,
    "kimi-latest": LLMProvider.KIMI,
    "kimi-k2": LLMProvider.KIMI,
    "moonshot": LLMProvider.KIMI,
    "moonshot-v1": LLMProvider.KIMI,
    # Ollama (本地)
    "llama": LLMProvider.OLLAMA,
    "mistral": LLMProvider.OLLAMA,
    "qwen": LLMProvider.OLLAMA,
}


def resolve_provider(model_or_alias: str) -> tuple[LLMProvider, str]:
    """
    解析模型名称或别名，返回提供商和模型名

    Args:
        model_or_alias: 模型名称或别名

    Returns:
        (提供商, 模型名) 元组

    示例:
    ------
    ```python
    provider, model = resolve_provider("gpt-4o-mini")
    # (LLMProvider.OPENAI, "gpt-4o-mini")

    provider, model = resolve_provider("claude")
    # (LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022")
    ```
    """
    model_lower = model_or_alias.lower()

    # 检查是否是别名
    for alias, provider in PROVIDER_ALIASES.items():
        if model_lower.startswith(alias):
            # 返回原始模型名（保持大小写）
            return provider, model_or_alias

    # 检查是否包含提供商名称
    if "gpt" in model_lower or "openai" in model_lower:
        return LLMProvider.OPENAI, model_or_alias
    if "claude" in model_lower or "anthropic" in model_lower:
        return LLMProvider.ANTHROPIC, model_or_alias
    if "deepseek" in model_lower:
        return LLMProvider.DEEPSEEK, model_or_alias
    if "kimi" in model_lower or "moonshot" in model_lower:
        return LLMProvider.KIMI, model_or_alias

    # 默认使用 DeepSeek
    return LLMProvider.DEEPSEEK, model_or_alias


def create_llm_smart(model: str, **kwargs) -> "BaseLLM":
    """
    智能创建 LLM 实例

    根据模型名称自动推断提供商。

    Args:
        model: 模型名称
        **kwargs: 额外参数

    Returns:
        LLM 实例

    示例:
    ------
    ```python
    # 自动识别为 OpenAI
    llm = create_llm_smart("gpt-4o-mini")

    # 自动识别为 Anthropic
    llm = create_llm_smart("claude-3-5-sonnet-20241022")

    # 自动识别为 DeepSeek
    llm = create_llm_smart("deepseek-chat")
    ```
    """
    provider, resolved_model = resolve_provider(model)

    config = LLMConfig(provider=provider, model=resolved_model)
    return create_llm(config=config, **kwargs)


def create_fallback_llm(**kwargs) -> "BaseLLM":
    """
    创建备用 LLM 实例

    从环境变量读取 AGENT_FALLBACK_LLM_* 配置，用于主模型失败时的降级。
    默认使用 Kimi (Moonshot) 作为备用模型。

    Args:
        **kwargs: 额外参数，会覆盖环境变量中的值

    Returns:
        备用 LLM 实例

    示例:
    ------
    ```python
    fallback_llm = create_fallback_llm()
    # 或覆盖配置
    fallback_llm = create_fallback_llm(temperature=0.5)
    ```
    """
    from services.agent.config import get_config

    agent_config = get_config()
    fallback_config = agent_config.fallback_llm

    if not fallback_config.enabled:
        raise ValueError("Fallback LLM is disabled")

    # 构建 LLMConfig
    llm_config = LLMConfig(
        provider=kwargs.get("provider", fallback_config.provider),
        model=kwargs.get("model", fallback_config.model),
        temperature=kwargs.get("temperature", fallback_config.temperature),
        max_tokens=kwargs.get("max_tokens", fallback_config.max_tokens),
    )

    return create_llm(
        config=llm_config,
        api_keys=agent_config.api_keys,
        **kwargs,
    )


def create_subagent_llm(**kwargs) -> "BaseLLM":
    """
    创建子代理 LLM 实例

    从环境变量读取 AGENT_SUBAGENT_LLM_* 配置，用于子代理任务。
    默认使用 Kimi K2.5 作为子代理模型。

    Args:
        **kwargs: 额外参数，会覆盖环境变量中的值

    Returns:
        子代理 LLM 实例

    示例:
    ------
    ```python
    subagent_llm = create_subagent_llm()
    # 或覆盖配置
    subagent_llm = create_subagent_llm(model="kimi-k2-0711-preview")
    ```
    """
    from services.agent.config import get_config

    agent_config = get_config()
    subagent_config = agent_config.subagent_llm

    # 构建 LLMConfig
    llm_config = LLMConfig(
        provider=kwargs.get("provider", subagent_config.provider),
        model=kwargs.get("model", subagent_config.model),
        temperature=kwargs.get("temperature", subagent_config.temperature),
        max_tokens=kwargs.get("max_tokens", subagent_config.max_tokens),
    )

    return create_llm(
        config=llm_config,
        api_keys=agent_config.api_keys,
        **kwargs,
    )


def create_llm_with_fallback(**kwargs) -> tuple["BaseLLM", Optional["BaseLLM"]]:
    """
    创建主 LLM 和备用 LLM 实例

    Returns:
        (主 LLM, 备用 LLM) 元组，如果备用 LLM 未启用则为 None

    示例:
    ------
    ```python
    main_llm, fallback_llm = create_llm_with_fallback()

    try:
        response = await main_llm.generate(messages)
    except Exception as e:
        if fallback_llm:
            response = await fallback_llm.generate(messages)
        else:
            raise
    ```
    """
    from services.agent.config import get_config

    agent_config = get_config()

    main_llm = create_llm_from_env(**kwargs)

    fallback_llm = None
    if agent_config.fallback_llm.enabled:
        try:
            fallback_llm = create_fallback_llm(**kwargs)
        except Exception:
            pass  # Fallback LLM 创建失败时静默忽略

    return main_llm, fallback_llm
