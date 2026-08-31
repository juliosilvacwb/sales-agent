"""Integration and E2E tests for Agentic Self-Correction and Error Resilience (T009 / R009).

Validates:
1. SQL hallucinated column repair via self-correction loop in a single turn (AC04).
2. Domain tool input validation error self-correction (DD/MM/YYYY repair) (AC01, AC04).
3. Retry budget exhaustion leading to polite fallback business apology (AC05, AC06).
4. Telemetry logging of [AGENT_SELF_CORRECTION] markers on tool failures (AC07).
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


class FakeToolCallingChatModel(BaseChatModel):
    """Deterministic fake LLM producing sequenced tool calls or text responses."""

    responses: List[Any] = []
    _call_count: int = 0

    def __init__(self, responses: List[Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.responses = responses
        self._call_count = 0

    @property
    def _llm_type(self) -> str:
        return "fake-tool-calling-chat-model"

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
            resp = "Resposta padrão simulada."

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

    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeToolCallingChatModel":
        return self


@pytest.fixture
def self_correction_csv():
    """Provides a realistic test CSV for self-correction test runs."""
    content = (
        "product_id;local;date;planned_quantity;actual_quantity;planned_price;promotion_type;actual_price;service_level\n"
        "Product_0001;Whse_A;01/01/2023;100;120;50.0;None;50.0;0.95\n"
        "Product_0001;Whse_B;15/01/2023;80;80;50.0;None;50.0;0.90\n"
        "Product_0002;Whse_A;10/02/2023;200;180;100.0;SummerSale;90.0;0.85\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def self_correction_stack(self_correction_csv):
    """Instantiates full real hexagonal persistence, application service, and tools."""
    persistence = DuckDbSalesAdapter(dataset_path=self_correction_csv)
    service = SalesMetricsApplicationService(sales_data_port=persistence)
    domain_tools = create_domain_tools(service)
    sql_tool = create_sql_fallback_tool(service)
    return {
        "persistence": persistence,
        "service": service,
        "tools": [*domain_tools, sql_tool],
        "csv_path": self_correction_csv,
    }


def test_sql_column_hallucination_self_correction_e2e(self_correction_stack, caplog):
    """
    Test AC04 & AC07: Agent hallucinates a non-existent column 'total_price',
    receives ToolException feedback, emits [AGENT_SELF_CORRECTION], corrects query
    to 'SUM(actual_quantity * actual_price)', and returns the correct answer.
    """
    # Step 1: Model calls SQL with hallucinated column `total_price` -> Fails on DuckDB
    # Step 2: Model receives ToolException feedback, analyzes error, calls corrected SQL
    # Step 3: Model receives successful result and outputs final executive response
    fake_llm = FakeToolCallingChatModel(
        responses=[
            {
                "tool_name": "secured_sql_query",
                "args": {"query": "SELECT SUM(total_price) AS faturamento FROM sales_data WHERE product_id = 'Product_0001'"},
            },
            {
                "tool_name": "secured_sql_query",
                "args": {"query": "SELECT SUM(actual_quantity * actual_price) AS faturamento FROM sales_data WHERE product_id = 'Product_0001'"},
            },
            "O faturamento total do produto Product_0001 foi de R$ 10.000,00.",
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=self_correction_stack["tools"])

    with caplog.at_level(logging.WARNING):
        response = agent.ask("Qual é o faturamento total do produto Product_0001?")

    assert "10.000,00" in response or "Product_0001" in response
    assert "Erro" not in response
    assert "[AGENT_SELF_CORRECTION]" in caplog.text


def test_domain_tool_date_validation_self_correction_e2e(self_correction_stack, caplog):
    """
    Test AC01 & AC07: Agent calls domain tool get_total_sales_in_period with an invalid date format,
    receives ToolException, catches and self-corrects the date format to DD/MM/YYYY,
    completing the query successfully.
    """
    fake_llm = FakeToolCallingChatModel(
        responses=[
            {
                "tool_name": "get_total_sales_in_period",
                "args": {"start_date": "not-a-valid-date", "end_date": "31/01/2023"},
            },
            {
                "tool_name": "get_total_sales_in_period",
                "args": {"start_date": "01/01/2023", "end_date": "31/01/2023"},
            },
            "O total de vendas no período de janeiro de 2023 foi de 200 unidades com receita de R$ 10.000,00.",
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=self_correction_stack["tools"])

    with caplog.at_level(logging.WARNING):
        response = agent.ask("Qual o total de vendas em janeiro de 2023?")

    assert "janeiro de 2023" in response or "10.000" in response
    assert "[AGENT_SELF_CORRECTION]" in caplog.text


def test_retry_exhaustion_returns_polite_fallback_e2e(self_correction_stack, caplog):
    """
    Test AC05 & AC06: When the agent attempts multiple failing queries (irrecoverable error),
    it halts and delivers the standardized polite business fallback message with zero raw error exposure.
    """
    fake_llm = FakeToolCallingChatModel(
        responses=[
            {"tool_name": "secured_sql_query", "args": {"query": "SELECT * FROM non_existent_table"}},
            {"tool_name": "secured_sql_query", "args": {"query": "SELECT * FROM still_non_existent"}},
            {"tool_name": "secured_sql_query", "args": {"query": "SELECT * FROM invalid_table_3"}},
            FALLBACK_ERROR_MESSAGE,
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=self_correction_stack["tools"])

    with caplog.at_level(logging.WARNING):
        response = agent.ask("Qual a margem dos produtos da tabela confidencial?")

    # Verify standardized apology is returned without exposing DuckDB / SQL tracebacks
    assert "Não foi possível localizar os dados necessários" in response
    assert "Traceback" not in response
    assert "Catalog Error" not in response
    assert "Table with name" not in response
    assert "[AGENT_SELF_CORRECTION]" in caplog.text
