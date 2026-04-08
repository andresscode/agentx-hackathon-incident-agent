"""
LLM provider abstraction for multi-provider support.

To switch providers, set these environment variables:
  LLM_PROVIDER = openai | anthropic | google | openrouter
  LLM_MODEL    = model name for the chosen provider (e.g. gpt-4o, claude-3-5-sonnet-20241022)

Only the API key for the active provider is required:
  OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, or OPENROUTER_API_KEY

OpenRouter (https://openrouter.ai) is OpenAI-compatible and gives access to
many models (GPT, Claude, Gemini, Llama…) with a single key. It's the default.
"""

import os

from langchain_core.language_models.chat_models import BaseChatModel


def get_llm() -> BaseChatModel:
    """Return a LangChain chat model based on LLM_PROVIDER env var."""
    provider = os.getenv("LLM_PROVIDER", "openrouter").lower()
    model = os.getenv("LLM_MODEL")

    if provider == "openai":
        api_key = _require_key("OPENAI_API_KEY", provider)
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model or "gpt-4o-mini",
            api_key=api_key,  # type: ignore[arg-type]
        )

    if provider == "anthropic":
        api_key = _require_key("ANTHROPIC_API_KEY", provider)
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model or "claude-3-5-haiku-20241022",
            api_key=api_key,  # type: ignore[arg-type]
        )

    if provider == "google":
        api_key = _require_key("GOOGLE_API_KEY", provider)
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model or "gemini-2.0-flash",
            google_api_key=api_key,  # type: ignore[arg-type]
        )

    if provider == "openrouter":
        api_key = _require_key("OPENROUTER_API_KEY", provider)
        from langchain_openai import ChatOpenAI

        # OpenRouter is OpenAI-compatible — just point to a different base URL.
        return ChatOpenAI(
            model=model or "openai/gpt-4o-mini",
            api_key=api_key,  # type: ignore[arg-type]
            base_url="https://openrouter.ai/api/v1",
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}'. "
        "Valid options: openai | anthropic | google | openrouter"
    )


def _require_key(env_var: str, provider: str) -> str:
    value = os.getenv(env_var)
    if not value:
        raise EnvironmentError(
            f"LLM_PROVIDER is set to '{provider}' but {env_var} is not set. "
            f"Add {env_var} to your .env file."
        )
    return value
