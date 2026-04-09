"""
LLM provider abstraction for multi-provider support.

Environment:
  LLM_PROVIDER — one of LLMProvider values (default: openrouter)
  LLM_MODEL    — optional; must be a known model id for the active provider
                 (see *Model enums below). If unset or invalid, the default
                 for that provider is used.

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


class AnthropicModel(StrEnum):
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"


class GoogleModel(StrEnum):
    GEMINI_2_FLASH = "gemini-2.0-flash"


class OpenRouterModel(StrEnum):
    GPT_4O_MINI = "openai/gpt-4o-mini"


class AIGatewayModel(StrEnum):
    GEMINI_2_5_FLASH_LITE = "google/gemini-2.5-flash-lite"


# ---------------------------------------------------------------------------
# Task — use this for autocomplete at call sites: get_llm(LLMTask.TRIAGE)
# ---------------------------------------------------------------------------


class LLMTask(StrEnum):
    TRIAGE = "triage"
    SUMMARIZE = "summarize"
    CLASSIFY = "classify"
    NOTIFY = "notify"
    GENERAL = "general"


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
    # Always accept the model from .env — no hardcoded restrictions
    return candidate


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_llm(task: LLMTask = LLMTask.GENERAL) -> BaseChatModel:
    """
    Build a LangChain chat model from ``LLM_PROVIDER`` / ``LLM_MODEL``.

    ``task`` is for logging and future per-task routing (model selection).
    Use :class:`LLMTask` so editors autocomplete valid values.
    """
    provider = _parse_provider(os.getenv("LLM_PROVIDER"))
    model = _resolve_model(provider, os.getenv("LLM_MODEL"))
    logger.debug(
        "get_llm provider=%s model=%s task=%s",
        provider.value,
        model,
        task.value,
    )

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
