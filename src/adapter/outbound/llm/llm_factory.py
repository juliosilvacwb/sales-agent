"""LLM Factory for agnostic chat model initialization via environment configuration."""
import os
import logging
from typing import Any, Optional

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory creating agnostic LLM chat models based on environment variables or parameters."""

    # Map aliases to standard LangChain provider names
    PROVIDER_ALIASES = {
        "google": "google_genai",
        "gemini": "google_genai",
        "google-genai": "google_genai",
        "google_genai": "google_genai",
        "openai": "openai",
        "anthropic": "anthropic",
        "ollama": "ollama",
    }

    @classmethod
    def create_llm(
        cls,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> BaseChatModel:
        """Instantiates a BaseChatModel using init_chat_model.
        
        Falls back to environment variables:
          - LLM_PROVIDER (default: 'openai')
          - MODEL_NAME (default: 'gpt-4o-mini')
          - TEMPERATURE (default: 0.0)
        """
        raw_provider = provider or os.getenv("LLM_PROVIDER", "openai").lower()
        normalized_provider = cls.PROVIDER_ALIASES.get(raw_provider, raw_provider)
        
        resolved_model = model_name or os.getenv("MODEL_NAME", "gpt-4o-mini")
        
        env_temp = os.getenv("TEMPERATURE")
        if temperature is not None:
            resolved_temp = float(temperature)
        elif env_temp is not None:
            resolved_temp = float(env_temp)
        else:
            resolved_temp = 0.0

        logger.info(
            "Initializing LLM with provider='%s' (original: '%s'), model='%s', temperature=%.2f",
            normalized_provider,
            raw_provider,
            resolved_model,
            resolved_temp,
        )

        return init_chat_model(
            model=resolved_model,
            model_provider=normalized_provider,
            temperature=resolved_temp,
            **kwargs,
        )
