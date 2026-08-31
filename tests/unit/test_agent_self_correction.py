"""Unit tests for Agentic Self-Correction components and error handlers (T009)."""
import logging
from unittest.mock import MagicMock
import pytest
from langchain_core.tools import ToolException

from src.adapter.inbound.llm.domain_tools import create_domain_tools
from src.adapter.inbound.llm.sales_agent import SalesAgent, _handle_tool_error, FALLBACK_ERROR_MESSAGE, SYSTEM_PROMPT
from src.adapter.inbound.llm.sql_fallback_tool import create_sql_fallback_tool
from src.application.port.inbound.sales_analysis_usecase import SalesAnalysisUseCase


def test_handle_tool_error_formatting_and_logging(caplog):
    """Test that _handle_tool_error formats the error string and emits telemetry."""
    exc = ToolException("Coluna 'total_revenue' não existe.")
    
    with caplog.at_level(logging.WARNING):
        result = _handle_tool_error(exc)
        
    assert result == "Coluna 'total_revenue' não existe."
    assert "[AGENT_SELF_CORRECTION]" in caplog.text
    assert "Coluna 'total_revenue' não existe." in caplog.text


def test_handle_tool_error_empty_args():
    """Test _handle_tool_error when exception has no explicit args."""
    exc = ToolException()
    result = _handle_tool_error(exc)
    assert isinstance(result, str)


def test_sales_agent_attaches_telemetry_handler_to_all_tools():
    """Test that SalesAgent configures _handle_tool_error on all domain and fallback tools."""
    mock_usecase = MagicMock(spec=SalesAnalysisUseCase)
    domain_tools = create_domain_tools(mock_usecase)
    sql_tool = create_sql_fallback_tool(mock_usecase)
    all_tools = [*domain_tools, sql_tool]

    mock_llm = MagicMock()
    from unittest.mock import patch
    with patch("src.adapter.inbound.llm.sales_agent.create_agent"):
        agent = SalesAgent(llm=mock_llm, tools=all_tools)
        
        for t in agent._tools:
            assert t.handle_tool_error == _handle_tool_error


def test_system_prompt_adheres_to_business_rules():
    """Verify SYSTEM_PROMPT embodies BR01, BR02, BR03, BR04 guidelines."""
    assert "DIRETRIZES DE AUTOCORREÇÃO E RECUPERAÇÃO DE ERROS" in SYSTEM_PROMPT
    assert "Tratamento Autônomo de Erros" in SYSTEM_PROMPT
    assert "Zero Exposição de Erros Técnicos" in SYSTEM_PROMPT
    assert "Limite de Tentativas e Fallback Gracioso" in SYSTEM_PROMPT
    assert FALLBACK_ERROR_MESSAGE in SYSTEM_PROMPT or "Não foi possível localizar os dados necessários" in SYSTEM_PROMPT


def test_sales_agent_returns_fallback_message_on_unhandled_exception():
    """Test that SalesAgent returns polite fallback message on unhandled exception or retry exhaustion."""
    mock_llm = MagicMock()
    mock_tools = []

    from unittest.mock import patch
    with patch("src.adapter.inbound.llm.sales_agent.create_agent") as mock_create_agent:
        mock_executor_instance = MagicMock()
        mock_executor_instance.invoke.side_effect = RuntimeError("Max retries / recursion limit reached")
        mock_create_agent.return_value = mock_executor_instance

        agent = SalesAgent(llm=mock_llm, tools=mock_tools)
        response = agent.ask("Qualquer pergunta com falha")

        assert response == FALLBACK_ERROR_MESSAGE


def test_sales_agent_chat_history_preservation_and_reset():
    """Test chat history preservation, sliding window bounding, and reset."""
    mock_llm = MagicMock()
    mock_tools = []

    from unittest.mock import patch
    with patch("src.adapter.inbound.llm.sales_agent.create_agent") as mock_create_agent:
        mock_executor_instance = MagicMock()
        mock_executor_instance.invoke.return_value = {"messages": [MagicMock(content="Resposta simulada")]}
        mock_create_agent.return_value = mock_executor_instance

        agent = SalesAgent(llm=mock_llm, tools=mock_tools, max_history_messages=4)
        agent.ask("Pergunta 1")
        agent.ask("Pergunta 2")
        agent.ask("Pergunta 3")

        # Sliding window keeps last 4 messages
        assert len(agent.chat_history) == 4
        assert agent.chat_history[0].content == "Pergunta 2"
        assert agent.chat_history[2].content == "Pergunta 3"

        # Test reset
        agent.reset_history()
        assert len(agent.chat_history) == 0

