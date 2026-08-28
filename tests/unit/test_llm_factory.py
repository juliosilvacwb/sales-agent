"""Unit tests for LLMFactory."""
import os
from unittest.mock import MagicMock, patch
import pytest

from src.adapter.outbound.llm.llm_factory import LLMFactory


def test_llm_factory_default_environment(monkeypatch):
    """Test LLMFactory reading defaults from environment."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("MODEL_NAME", "gpt-4o-mini")
    monkeypatch.setenv("TEMPERATURE", "0.0")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with patch("src.adapter.outbound.llm.llm_factory.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock()
        model = LLMFactory.create_llm()

        mock_init.assert_called_once_with(
            model="gpt-4o-mini",
            model_provider="openai",
            temperature=0.0,
        )
        assert model is not None


def test_llm_factory_explicit_parameters(monkeypatch):
    """Test LLMFactory with explicit parameters overriding environment."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    with patch("src.adapter.outbound.llm.llm_factory.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock()
        model = LLMFactory.create_llm(
            provider="anthropic",
            model_name="claude-3-5-sonnet-20241022",
            temperature=0.2,
        )

        mock_init.assert_called_once_with(
            model="claude-3-5-sonnet-20241022",
            model_provider="anthropic",
            temperature=0.2,
        )
        assert model is not None


def test_llm_factory_google_alias_normalization(monkeypatch):
    """Test normalization of google / gemini aliases to google_genai."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    with patch("src.adapter.outbound.llm.llm_factory.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock()
        LLMFactory.create_llm(
            provider="google",
            model_name="gemini-1.5-flash",
        )

        mock_init.assert_called_once_with(
            model="gemini-1.5-flash",
            model_provider="google_genai",
            temperature=0.0,
        )
