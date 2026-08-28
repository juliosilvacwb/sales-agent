"""Unit tests for SalesAgent orchestrator."""
from unittest.mock import MagicMock, patch
import pytest

from src.adapter.inbound.llm.sales_agent import SalesAgent, SYSTEM_PROMPT


def test_system_prompt_contains_critical_sections():
    """Test that system prompt includes data dictionary and tool prioritization rules."""
    assert "sales_data" in SYSTEM_PROMPT
    assert "product_id" in SYSTEM_PROMPT
    assert "local" in SYSTEM_PROMPT
    assert "planned_quantity" in SYSTEM_PROMPT
    assert "actual_quantity" in SYSTEM_PROMPT
    assert "service_level" in SYSTEM_PROMPT
    assert "secured_sql_query" in SYSTEM_PROMPT
    assert "Domain Tools" in SYSTEM_PROMPT or "ferramentas de domínio" in SYSTEM_PROMPT.lower()


def test_sales_agent_initialization():
    """Test initializing SalesAgent with mock LLM and tools."""
    mock_llm = MagicMock()
    mock_tools = [MagicMock()]
    mock_tools[0].name = "test_tool"

    with patch("src.adapter.inbound.llm.sales_agent.create_tool_calling_agent") as mock_create_agent, \
         patch("src.adapter.inbound.llm.sales_agent.AgentExecutor") as mock_executor_cls:
        
        mock_executor_instance = MagicMock()
        mock_executor_cls.return_value = mock_executor_instance

        agent = SalesAgent(llm=mock_llm, tools=mock_tools)
        assert agent is not None
        mock_create_agent.assert_called_once()
        mock_executor_cls.assert_called_once()


def test_sales_agent_ask():
    """Test invoking SalesAgent ask method."""
    mock_llm = MagicMock()
    mock_tools = []

    with patch("src.adapter.inbound.llm.sales_agent.create_tool_calling_agent"), \
         patch("src.adapter.inbound.llm.sales_agent.AgentExecutor") as mock_executor_cls:
        
        mock_executor_instance = MagicMock()
        mock_executor_instance.invoke.return_value = {"output": "O produto mais vendido foi Prod_01."}
        mock_executor_cls.return_value = mock_executor_instance

        agent = SalesAgent(llm=mock_llm, tools=mock_tools)
        response = agent.ask("Qual o produto mais vendido?")

        assert response == "O produto mais vendido foi Prod_01."
        mock_executor_instance.invoke.assert_called_once()
        assert len(agent.chat_history) == 2
        assert agent.chat_history[0].content == "Qual o produto mais vendido?"
        assert agent.chat_history[1].content == "O produto mais vendido foi Prod_01."


def test_sales_agent_sliding_window_memory():
    """Test that chat history enforces max_history_messages sliding window."""
    mock_llm = MagicMock()
    mock_tools = []

    with patch("src.adapter.inbound.llm.sales_agent.create_tool_calling_agent"), \
         patch("src.adapter.inbound.llm.sales_agent.AgentExecutor") as mock_executor_cls:
        
        mock_executor_instance = MagicMock()
        mock_executor_instance.invoke.return_value = {"output": "Resposta padrão."}
        mock_executor_cls.return_value = mock_executor_instance

        # Limit to 4 messages (2 exchanges)
        agent = SalesAgent(llm=mock_llm, tools=mock_tools, max_history_messages=4)

        agent.ask("Pergunta 1")
        agent.ask("Pergunta 2")
        agent.ask("Pergunta 3")

        # History should only retain the last 4 messages (Pergunta 2 and Pergunta 3 turns)
        assert len(agent.chat_history) == 4
        assert agent.chat_history[0].content == "Pergunta 2"
        assert agent.chat_history[2].content == "Pergunta 3"

        # Test reset
        agent.reset_history()
        assert len(agent.chat_history) == 0

