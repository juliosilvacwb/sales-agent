"""Integration tests for LangGraph State Machine Orchestration (T014 / R014).

Validates:
1. Cyclic execution flow (call_model -> tools -> call_model -> END) (AC02).
2. Direct conversational transition to END for chit-chat queries (AC03).
3. Cyclic agentic self-correction for tool error recovery (AC04).
4. Deterministic response grounding state inspection (data_queried flag) (AC05).
5. Backwards-compatible public interface (ask, chat_history, reset_history) (AC06).
6. Graceful failure on recursion limit ceiling exhaustion (AC07).
"""
import logging
import os
import tempfile
from typing import Any, List, Optional
import pytest
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult

from src.adapter.inbound.llm.domain_tools import create_domain_tools
from src.adapter.inbound.llm.sales_agent import SalesAgent, FALLBACK_ERROR_MESSAGE
from src.adapter.inbound.llm.sql_fallback_tool import create_sql_fallback_tool
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.application.service.sales_metrics_service import SalesMetricsApplicationService


class DeterministicFakeChatModel(BaseChatModel):
    """Deterministic fake chat model for testing LangGraph execution cycles."""

    responses: List[Any] = []
    _call_count: int = 0

    def __init__(self, responses: List[Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.responses = responses
        self._call_count = 0

    @property
    def _llm_type(self) -> str:
        return "deterministic-fake-chat-model"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self._call_count < len(self.responses):
            resp = self.responses[self._call_count]
            self._call_count += 1
        else:
            resp = AIMessage(content="Resposta final padrão do modelo.")

        if isinstance(resp, str):
            ai_msg = AIMessage(content=resp)
        elif isinstance(resp, AIMessage):
            ai_msg = resp
        elif isinstance(resp, dict) and "tool_name" in resp:
            ai_msg = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": resp["tool_name"],
                        "args": resp.get("args", {}),
                        "id": resp.get("id", f"call_{self._call_count}"),
                        "type": "tool_call",
                    }
                ],
            )
        else:
            ai_msg = AIMessage(content=str(resp))

        return ChatResult(generations=[ChatGeneration(message=ai_msg)])

    def bind_tools(self, tools: Any, **kwargs: Any) -> "DeterministicFakeChatModel":
        return self


@pytest.fixture
def sales_graph_csv():
    """Provides a sample CSV dataset for LangGraph orchestration integration tests."""
    content = (
        "product_id;local;date;planned_quantity;actual_quantity;planned_price;promotion_type;actual_price;service_level\n"
        "Product_0001;Whse_A;01/01/2024;100;120;50.0;None;50.0;0.95\n"
        "Product_0001;Whse_B;15/01/2024;80;90;50.0;None;50.0;0.90\n"
        "Product_0002;Whse_A;10/02/2024;200;180;100.0;Promo10;90.0;0.85\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sales_graph_stack(sales_graph_csv):
    """Instantiates DuckDB persistence, application service, and tools for LangGraph tests."""
    persistence = DuckDbSalesAdapter(dataset_path=sales_graph_csv)
    service = SalesMetricsApplicationService(sales_data_port=persistence)
    domain_tools = create_domain_tools(service)
    sql_tool = create_sql_fallback_tool(service)
    return {
        "persistence": persistence,
        "service": service,
        "tools": [*domain_tools, sql_tool],
        "csv_path": sales_graph_csv,
    }


def test_langgraph_cyclic_tool_execution(sales_graph_stack):
    """[T014-005 / AC02] Assert that a query requiring tools traverses the cyclic loop: call_model -> tools -> call_model -> END."""
    # Step 1: Model emits tool_calls for get_top_selling_product
    # Step 2: ToolNode executes on DuckDB
    # Step 3: Model receives ToolMessage and synthesizes final answer
    fake_llm = DeterministicFakeChatModel(
        responses=[
            {"tool_name": "get_top_selling_product", "args": {}},
            AIMessage(content="O produto mais vendido foi Product_0001 com 210 unidades vendidas."),
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=sales_graph_stack["tools"])
    result = agent.ask("Qual foi o produto mais vendido?")

    assert result.data_queried is True
    assert "Product_0001" in result.response
    assert "210" in result.response
    # Assert chat history updated
    assert len(agent.chat_history) == 2
    assert agent.chat_history[0].content == "Qual foi o produto mais vendido?"
    assert "Product_0001" in agent.chat_history[1].content


def test_langgraph_direct_conversational_turn(sales_graph_stack):
    """[T014-005 / AC03] Assert casual greeting query routes directly from call_model -> END without tool execution."""
    fake_llm = DeterministicFakeChatModel(
        responses=[
            AIMessage(content="Olá! Sou o assistente especialista em dados de vendas. Como posso te ajudar hoje?"),
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=sales_graph_stack["tools"])
    result = agent.ask("Olá, assistente!")

    assert result.data_queried is False
    assert "assistente especialista em dados" in result.response
    assert len(agent.chat_history) == 2


def test_langgraph_agentic_self_correction_cyclic_recovery(sales_graph_stack, caplog):
    """[T014-005 / AC04] Assert multi-turn self-correction loop in LangGraph: error feedback -> corrected query -> synthesis -> END."""
    fake_llm = DeterministicFakeChatModel(
        responses=[
            # Attempt 1: Invalid SQL with non-existent column
            {
                "tool_name": "secured_sql_query",
                "args": {"query": "SELECT SUM(non_existent_column) FROM sales_data"},
            },
            # Attempt 2: Corrected SQL after receiving ToolMessage error
            {
                "tool_name": "secured_sql_query",
                "args": {"query": "SELECT SUM(actual_quantity) AS total_qty FROM sales_data"},
            },
            # Final synthesis
            AIMessage(content="O volume total realizado foi de 390 unidades."),
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=sales_graph_stack["tools"])

    with caplog.at_level(logging.WARNING):
        result = agent.ask("Qual o volume total de unidades vendidas?")

    assert result.data_queried is True
    assert "390" in result.response
    assert "[AGENT_SELF_CORRECTION]" in caplog.text


def test_langgraph_recursion_limit_protection(sales_graph_stack):
    """[T014-005 / AC07] Assert intentional infinite loop hits recursion_limit and delivers fallback apology gracefully."""
    # Endless tool-calling loop that never produces final response
    infinite_tool_calls = [{"tool_name": "get_top_selling_product", "args": {}} for _ in range(20)]
    fake_llm = DeterministicFakeChatModel(responses=infinite_tool_calls)

    agent = SalesAgent(llm=fake_llm, tools=sales_graph_stack["tools"])
    result = agent.ask("Gere loop infinito de ferramentas")

    assert result.response == FALLBACK_ERROR_MESSAGE
    assert result.data_queried is False


def test_langgraph_external_chat_history_isolation(sales_graph_stack):
    """[T014-005 / AC06] Assert ask with external chat_history does not alter internal memory."""
    fake_llm = DeterministicFakeChatModel(
        responses=[
            AIMessage(content="Resposta para sessão externa."),
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=sales_graph_stack["tools"])
    external_history = [
        AIMessage(content="Mensagem anterior"),
    ]
    result = agent.ask("Pergunta externa", chat_history=external_history)

    assert result.response == "Resposta para sessão externa."
    # Internal history remains empty
    assert len(agent.chat_history) == 0


# ==============================================================================
# TEST014: Formalized LangGraph Integration Tests (TEST014-19 to TEST014-23)
# ==============================================================================

test_langgraph_cyclic_tool_execution_integration = test_langgraph_cyclic_tool_execution
test_langgraph_direct_conversational_turn_integration = test_langgraph_direct_conversational_turn
test_langgraph_agentic_self_correction_cyclic_recovery_integration = test_langgraph_agentic_self_correction_cyclic_recovery
test_langgraph_recursion_limit_protection_integration = test_langgraph_recursion_limit_protection


def test_langgraph_full_stack_web_chat_backward_compatibility(sales_graph_stack):
    """[TEST014-23 / T014-005] Validate WebChatApplicationService full stack execution with LangGraph SalesAgent."""
    from src.adapter.outbound.memory.session_memory_adapter import SessionMemoryAdapter
    from src.application.service.web_chat_application_service import WebChatApplicationService
    from src.application.dto.chat_dto import ChatRequestDTO

    fake_llm = DeterministicFakeChatModel(
        responses=[
            # Turn 1: Analytical
            {"tool_name": "get_top_selling_product", "args": {}},
            AIMessage(content="O produto mais vendido foi Product_0001 com 210 unidades."),
            # Turn 2: Greeting
            AIMessage(content="De nada! Posso ajudar com mais alguma análise?"),
        ]
    )

    session_store = SessionMemoryAdapter()
    service = WebChatApplicationService(
        agent_factory=lambda: SalesAgent(llm=fake_llm, tools=sales_graph_stack["tools"]),
        session_store=session_store,
    )
    session_id = "test-full-stack-langgraph"

    res1 = service.process_chat_message(ChatRequestDTO(message="Qual o produto mais vendido?", session_id=session_id))
    assert res1.data_queried is True
    assert "Product_0001" in res1.response

    res2 = service.process_chat_message(ChatRequestDTO(message="Obrigado!", session_id=session_id))
    assert res2.data_queried is False
    assert "Posso ajudar" in res2.response


def test_langgraph_security_tool_error_path_sanitization_and_cyclic_recovery(sales_graph_stack, caplog):
    """[S014-05] Integration regression test validating that internal paths are sanitized during cyclic recovery."""
    # Tool raises error containing file path, agent receives sanitized ToolMessage and recovers
    fake_llm = DeterministicFakeChatModel(
        responses=[
            {
                "tool_name": "secured_sql_query",
                "args": {"query": "SELECT * FROM 'C:\\Secret\\Path\\data.csv'"},
            },
            {
                "tool_name": "secured_sql_query",
                "args": {"query": "SELECT SUM(actual_quantity) FROM sales_data"},
            },
            AIMessage(content="Total recuperado com sucesso."),
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=sales_graph_stack["tools"])
    with caplog.at_level(logging.WARNING):
        result = agent.ask("Consulta com path no erro")

    assert result.data_queried is True
    assert "Total recuperado" in result.response
    # Assert agent self correction logs do not contain raw file paths
    agent_correction_records = [
        r.message for r in caplog.records if "[AGENT_SELF_CORRECTION]" in r.message
    ]
    assert len(agent_correction_records) > 0
    assert all("C:\\Secret\\Path" not in msg for msg in agent_correction_records)
    assert any("[REDACTED_PATH]" in msg or "[PATH_REDACTED]" in msg for msg in agent_correction_records)


