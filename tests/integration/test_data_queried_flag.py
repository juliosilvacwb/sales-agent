"""Integration tests for Data Queried Flag and Response Grounding (T013 / R013).

Validates turn isolation, deterministic flag generation across domain and SQL tools,
error fallback handling, and zero observable callback latency.
"""
import time
from typing import Any, List, Optional
from unittest.mock import MagicMock, patch
import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from src.adapter.inbound.llm.domain_tools import create_domain_tools
from src.adapter.inbound.llm.sales_agent import SalesAgent, ToolTrackingCallbackHandler
from src.adapter.inbound.llm.sql_fallback_tool import create_sql_fallback_tool
from src.adapter.outbound.memory.session_memory_adapter import SessionMemoryAdapter
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.application.dto.chat_dto import ChatRequestDTO, ChatResponseDTO
from src.application.service.sales_metrics_service import SalesMetricsApplicationService
from src.application.service.web_chat_application_service import WebChatApplicationService


class DeterministicSequenceChatModel(BaseChatModel):
    """Deterministic LLM for testing chained conversation turns and tool calling."""

    responses: List[Any] = []
    _call_count: int = 0

    def __init__(self, responses: List[Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.responses = responses
        self._call_count = 0

    @property
    def _llm_type(self) -> str:
        return "deterministic-sequence-chat-model"

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
            resp = AIMessage(content="Resposta final padrão.")

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
                        "args": resp.get("tool_args", resp.get("args", {})),
                        "id": resp.get("tool_id", resp.get("id", f"call_{self._call_count}")),
                        "type": "tool_call",
                    }
                ],
            )
        else:
            ai_msg = AIMessage(content=str(resp))

        return ChatResult(generations=[ChatGeneration(message=ai_msg)])

    def bind_tools(self, tools: Any, **kwargs: Any) -> "DeterministicSequenceChatModel":
        return self


@pytest.fixture
def sample_sales_service(tmp_path):
    """Fixture providing initialized SalesMetricsApplicationService with temporary CSV."""
    csv_file = tmp_path / "sales.csv"
    csv_file.write_text(
        "product_id;local;date;planned_quantity;actual_quantity;planned_price;actual_price;service_level;promotion_type\n"
        "Product_0001;Whse_A;01/03/2024;100;120;10.0;9.5;0.98;Promo_A\n"
        "Product_0002;Whse_B;02/03/2024;200;180;15.0;15.0;0.95;None\n"
    )
    adapter = DuckDbSalesAdapter(dataset_path=str(csv_file))
    return SalesMetricsApplicationService(sales_data_port=adapter)


def test_analytical_turn_returns_data_queried_true(sample_sales_service):
    """[TEST013-17 / AC02 / T013-006] Verify analytical turn executing a Domain Tool yields data_queried=True."""
    mock_llm = DeterministicSequenceChatModel(
        responses=[
            {"tool_name": "get_top_selling_product", "tool_args": {}},
            AIMessage(content="O produto mais vendido foi Product_0001 com 120 unidades."),
        ]
    )
    domain_tools = create_domain_tools(sample_sales_service)
    sql_tool = create_sql_fallback_tool(sample_sales_service)
    agent = SalesAgent(llm=mock_llm, tools=[*domain_tools, sql_tool])

    result = agent.ask("Qual foi o produto mais vendido?")

    assert result.data_queried is True
    assert "Product_0001" in result.response


def test_casual_greeting_turn_returns_data_queried_false(sample_sales_service):
    """[TEST013-18 / AC03 / T013-006] Verify casual conversation without tool invocation yields data_queried=False."""
    mock_llm = DeterministicSequenceChatModel(
        responses=[
            AIMessage(content="Olá! Sou o assistente de dados de vendas. Como posso ajudar?"),
        ]
    )
    domain_tools = create_domain_tools(sample_sales_service)
    sql_tool = create_sql_fallback_tool(sample_sales_service)
    agent = SalesAgent(llm=mock_llm, tools=[*domain_tools, sql_tool])

    result = agent.ask("Olá! Tudo bem?")

    assert result.data_queried is False
    assert "assistente de dados" in result.response


def test_multi_turn_turn_isolation(sample_sales_service):
    """[TEST013-19 / AC04 / PRD04 / T013-006] Verify multi-turn session maintains strict per-turn isolation without flag bleeding."""
    # Sequence of 3 turns in same session:
    # Turn 1: Analytical (Tool call -> Answer) -> True
    # Turn 2: Greeting (Direct LLM text) -> False
    # Turn 3: Analytical via SQL Fallback (Tool call -> Answer) -> True
    responses = [
        # Turn 1
        {"tool_name": "get_total_sales_in_period", "tool_args": {}},
        AIMessage(content="O total de vendas foi de 300 unidades."),
        # Turn 2
        AIMessage(content="Muito obrigado! Fico à disposição para outras dúvidas."),
        # Turn 3
        {"tool_name": "secured_sql_query", "tool_args": {"sql_query": "SELECT SUM(actual_quantity) FROM sales_data"}},
        AIMessage(content="A soma calculada via consulta direta foi de 300 unidades."),
    ]
    mock_llm = DeterministicSequenceChatModel(responses=responses)
    domain_tools = create_domain_tools(sample_sales_service)
    sql_tool = create_sql_fallback_tool(sample_sales_service)

    session_store = SessionMemoryAdapter()
    service = WebChatApplicationService(
        agent_factory=lambda: SalesAgent(llm=mock_llm, tools=[*domain_tools, sql_tool]),
        session_store=session_store,
    )
    session_id = "isolation-session-test"

    # Turn 1: Analytical
    res1 = service.process_chat_message(ChatRequestDTO(message="Qual o total de vendas?", session_id=session_id))
    assert res1.data_queried is True
    assert "300 unidades" in res1.response

    # Turn 2: Casual Chit-Chat
    res2 = service.process_chat_message(ChatRequestDTO(message="Obrigado pela informação!", session_id=session_id))
    assert res2.data_queried is False
    assert "Muito obrigado" in res2.response

    # Turn 3: Ad-hoc SQL Query
    res3 = service.process_chat_message(ChatRequestDTO(message="Pode checar a soma total via SQL?", session_id=session_id))
    assert res3.data_queried is True
    assert "300 unidades" in res3.response


def test_exception_fallback_returns_data_queried_false(sample_sales_service):
    """[TEST013-20 / BR01 / Exception Path 1 / T013-006] Verify unhandled error or recursion failure returns data_queried=False."""
    domain_tools = create_domain_tools(sample_sales_service)
    sql_tool = create_sql_fallback_tool(sample_sales_service)

    mock_llm = MagicMock()
    with patch("src.adapter.inbound.llm.sales_agent.create_agent") as mock_create_agent:
        mock_executor = MagicMock()
        mock_executor.invoke.side_effect = RuntimeError("Recursion limit exhausted")
        mock_create_agent.return_value = mock_executor

        agent = SalesAgent(llm=mock_llm, tools=[*domain_tools, sql_tool])
        result = agent.ask("Gere relatório de erro")

        assert result.data_queried is False
        assert "Não foi possível localizar os dados" in result.response



def test_callback_handler_sub_millisecond_latency_overhead():
    """[NFR02 / AC07 / T013-006] Assert ToolTrackingCallbackHandler in-memory execution takes less than 1ms."""
    handler = ToolTrackingCallbackHandler()
    iterations = 1000

    start_time = time.perf_counter()
    for _ in range(iterations):
        handler.on_tool_start({"name": "get_top_selling_product"}, input_str="{}")
        handler.on_tool_end("{}", name="get_top_selling_product")
    elapsed_total = time.perf_counter() - start_time

    avg_overhead_ms = (elapsed_total / iterations) * 1000
    assert avg_overhead_ms < 0.1, f"Average callback handler overhead exceeded 0.1ms: {avg_overhead_ms:.4f}ms"
