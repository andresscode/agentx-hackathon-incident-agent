"""
LLM provider abstraction for multi-provider support.

Environment:
  LLM_PROVIDER — one of LLMProvider values (default: openrouter)
  LLM_MODEL    — optional; fast model for prompt injection and initial image analysis
                 (see *Model enums below). If unset or invalid, the default fast
                 model for that provider is used.
  LLM_PRO_MODEL — optional; professional model for complex tasks (classification,
                  code search, summarization). If unset or invalid, the default
                  professional model for that provider is used.

API keys (only the one matching LLM_PROVIDER is required):
  OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY,
  OPENROUTER_API_KEY, AI_GATEWAY_API_KEY
"""

from __future__ import annotations

import logging
import os
from enum import StrEnum

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import SecretStr

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


class LLMProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENROUTER = "openrouter"
    AIGATEWAY = "aigateway"


# ---------------------------------------------------------------------------
# Models per provider (extend enums as you add supported models)
# ---------------------------------------------------------------------------


class OpenAIModel(StrEnum):
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o"  # For image analysis


class AnthropicModel(StrEnum):
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"


class GoogleModel(StrEnum):
    GEMINI_2_FLASH = "gemini-2.0-flash"
    GEMINI_1_5_PRO = "gemini-1.5-pro"  # For image analysis


class OpenRouterModel(StrEnum):
    GPT_4O_MINI = "openai/gpt-4o-mini"
    GPT_4O = "openai/gpt-4o"  # For image analysis


class AIGatewayModel(StrEnum):
    GEMINI_2_5_FLASH_LITE = "google/gemini-2.5-flash-lite"


# ---------------------------------------------------------------------------
# Defaults & validation
# ---------------------------------------------------------------------------

_DEFAULT_MODEL: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: OpenAIModel.GPT_4O_MINI.value,
    LLMProvider.ANTHROPIC: AnthropicModel.CLAUDE_3_5_HAIKU.value,
    LLMProvider.GOOGLE: GoogleModel.GEMINI_2_FLASH.value,
    LLMProvider.OPENROUTER: OpenRouterModel.GPT_4O_MINI.value,
    LLMProvider.AIGATEWAY: AIGatewayModel.GEMINI_2_5_FLASH_LITE.value,
}

_DEFAULT_PRO_MODEL: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: OpenAIModel.GPT_4O.value,  # More capable for complex tasks
    LLMProvider.ANTHROPIC: AnthropicModel.CLAUDE_3_5_HAIKU.value,
    LLMProvider.GOOGLE: GoogleModel.GEMINI_1_5_PRO.value,  # More capable for complex reasoning
    LLMProvider.OPENROUTER: OpenRouterModel.GPT_4O.value,  # More capable model
    LLMProvider.AIGATEWAY: AIGatewayModel.GEMINI_2_5_FLASH_LITE.value,
}

_MODEL_ENUM_BY_PROVIDER: dict[LLMProvider, type[StrEnum]] = {
    LLMProvider.OPENAI: OpenAIModel,
    LLMProvider.ANTHROPIC: AnthropicModel,
    LLMProvider.GOOGLE: GoogleModel,
    LLMProvider.OPENROUTER: OpenRouterModel,
    LLMProvider.AIGATEWAY: AIGatewayModel,
}

_ALLOWED_MODEL_IDS: dict[LLMProvider, frozenset[str]] = {
    p: frozenset(m.value for m in enum_cls)
    for p, enum_cls in _MODEL_ENUM_BY_PROVIDER.items()
}


def _parse_provider(raw: str | None) -> LLMProvider:
    if raw is None or not raw.strip():
        return LLMProvider.OPENROUTER
    key = raw.strip().lower()
    try:
        return LLMProvider(key)
    except ValueError as e:
        valid = ", ".join(p.value for p in LLMProvider)
        raise ValueError(f"Unknown LLM_PROVIDER {raw!r}. Valid options: {valid}") from e


def _resolve_model(provider: LLMProvider, env_model: str | None) -> str:
    default = _DEFAULT_MODEL[provider]
    if env_model is None or not env_model.strip():
        return default
    candidate = env_model.strip()
    if candidate in _ALLOWED_MODEL_IDS[provider]:
        return candidate
    logger.warning(
        "LLM_MODEL %r is not allowed for provider %s; using default %r. Allowed: %s",
        candidate,
        provider.value,
        default,
        sorted(_ALLOWED_MODEL_IDS[provider]),
    )
    return default


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------



def get_text_llm() -> BaseChatModel:
    """
    Fast LLM for text-only tasks: prompt injection check (Agent Step 1).

    Uses LLM_MODEL config (defaults to fast models like gpt-4o-mini).
    """
    provider = _parse_provider(os.getenv("LLM_PROVIDER"))
    model = _resolve_model(provider, os.getenv("LLM_MODEL"))
    logger.debug("get_text_llm provider=%s model=%s", provider.value, model)
    return _build_llm(provider, model)


def get_fast_llm() -> BaseChatModel:
    """
    Fast LLM for prompt injection and initial image analysis (Agent Step 1).
    
    Uses LLM_MODEL config (defaults to fast models like gpt-4o-mini).
    Can handle images for initial screenshot analysis.
    """
    provider = _parse_provider(os.getenv("LLM_PROVIDER"))
    model = _resolve_model(provider, os.getenv("LLM_MODEL"))
    logger.debug(
        "get_fast_llm provider=%s model=%s",
        provider.value,
        model,
    )

    return _build_llm(provider, model)


def get_pro_llm() -> BaseChatModel:
    """
    Professional LLM for classification, code search, and summarization (Agent Steps 2-3).
    
    Uses LLM_PRO_MODEL config (defaults to more capable models).
    Can handle complex reasoning and image analysis for detailed triage.
    """
    provider = _parse_provider(os.getenv("LLM_PROVIDER"))
    model = _resolve_pro_model(provider, os.getenv("LLM_PRO_MODEL"))
    logger.debug(
        "get_pro_llm provider=%s model=%s",
        provider.value,
        model,
    )

    return _build_llm(provider, model)


def get_image_llm() -> BaseChatModel:
    """
    Vision-capable LLM for image analysis, classification, and summarization (Agent Steps 1-3).

    Uses LLM_PRO_MODEL config (defaults to more capable/vision models).
    """
    provider = _parse_provider(os.getenv("LLM_PROVIDER"))
    model = _resolve_pro_model(provider, os.getenv("LLM_PRO_MODEL"))
    logger.debug("get_image_llm provider=%s model=%s", provider.value, model)
    return _build_llm(provider, model)


def _resolve_pro_model(provider: LLMProvider, env_model: str | None) -> str:
    """Resolve pro model for complex tasks (defaults to more capable models)."""
    default = _DEFAULT_PRO_MODEL[provider]
    if env_model is None or not env_model.strip():
        return default
    candidate = env_model.strip()
    if candidate in _ALLOWED_MODEL_IDS[provider]:
        return candidate
    logger.warning(
        "LLM_PRO_MODEL %r is not allowed for provider %s; using default %r. Allowed: %s",
        candidate,
        provider.value,
        default,
        sorted(_ALLOWED_MODEL_IDS[provider]),
    )
    return default



def _build_llm(provider: LLMProvider, model: str) -> BaseChatModel:
    """Internal helper to build the actual LLM instance."""
    if provider == LLMProvider.OPENAI:
        api_key = _require_key("OPENAI_API_KEY", provider)
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, api_key=SecretStr(api_key))

    if provider == LLMProvider.ANTHROPIC:
        api_key = _require_key("ANTHROPIC_API_KEY", provider)
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, api_key=SecretStr(api_key))

    if provider == LLMProvider.GOOGLE:
        api_key = _require_key("GOOGLE_API_KEY", provider)
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model, google_api_key=SecretStr(api_key))

    if provider == LLMProvider.OPENROUTER:
        api_key = _require_key("OPENROUTER_API_KEY", provider)
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=SecretStr(api_key),
            base_url="https://openrouter.ai/api/v1",
        )

    if provider == LLMProvider.AIGATEWAY:
        api_key = _require_key("AI_GATEWAY_API_KEY", provider)
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=SecretStr(api_key),
            base_url="https://ai-gateway.vercel.sh/v1",
        )

    raise AssertionError(f"Unhandled LLMProvider: {provider!r}")


def _require_key(env_var: str, provider: LLMProvider) -> str:
    value = os.getenv(env_var)
    if not value:
        raise OSError(
            f"LLM_PROVIDER is '{provider.value}' but {env_var} is not set. "
            f"Add {env_var} to your .env file."
        )
    return value
