"""Unit tests for CLI Main chat interface."""
from unittest.mock import MagicMock, patch
import pytest

from src.adapter.inbound.cli.main import bootstrap_agent, main


def test_bootstrap_agent_executes_profiling_and_configures_agent():
    """[TEST011-14] Test bootstrapping of the sales agent and all underlying hexagonal adapters including profiling."""
    with patch("src.adapter.inbound.cli.main.DuckDbSalesAdapter") as mock_adapter_cls, \
         patch("src.adapter.inbound.cli.main.SalesMetricsApplicationService") as mock_service_cls, \
         patch("src.adapter.inbound.cli.main.create_domain_tools") as mock_create_tools, \
         patch("src.adapter.inbound.cli.main.create_sql_fallback_tool") as mock_create_sql_tool, \
         patch("src.adapter.inbound.cli.main.LLMFactory.create_llm") as mock_create_llm, \
         patch("src.adapter.inbound.cli.main.SalesAgent") as mock_agent_cls:
        
        mock_create_tools.return_value = [MagicMock()]
        mock_create_sql_tool.return_value = MagicMock()
        mock_agent_instance = MagicMock()
        mock_agent_cls.return_value = mock_agent_instance
        mock_adapter_instance = MagicMock()
        mock_adapter_cls.return_value = mock_adapter_instance
        mock_profile = MagicMock()
        mock_adapter_instance.profile_dataset.return_value = mock_profile

        agent = bootstrap_agent()

        assert agent == mock_agent_instance
        mock_adapter_cls.assert_called_once()
        mock_adapter_instance.profile_dataset.assert_called_once()
        mock_service_cls.assert_called_once()
        mock_create_tools.assert_called_once()
        mock_create_sql_tool.assert_called_once()
        mock_create_llm.assert_called_once()
        mock_agent_cls.assert_called_once()
        _, kwargs = mock_agent_cls.call_args
        assert kwargs.get("dataset_profile") == mock_profile



def test_cli_main_exit_flow():
    """Test CLI main loop when user enters exit command."""
    mock_agent = MagicMock()
    with patch("src.adapter.inbound.cli.main.bootstrap_agent", return_value=mock_agent), \
         patch("builtins.input", side_effect=["sair"]), \
         patch("builtins.print") as mock_print:
        
        main()
        mock_agent.ask.assert_not_called()


def test_cli_main_interaction_flow():
    """Test CLI main loop with user question and subsequent exit."""
    mock_agent = MagicMock()
    mock_agent.ask.return_value = "O total vendido foi 1000 unidades."

    with patch("src.adapter.inbound.cli.main.bootstrap_agent", return_value=mock_agent), \
         patch("builtins.input", side_effect=["Qual o total de vendas?", "exit"]), \
         patch("builtins.print") as mock_print:
        
        main()
        mock_agent.ask.assert_called_once_with("Qual o total de vendas?")
