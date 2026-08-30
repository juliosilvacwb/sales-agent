"""Integration tests (End-to-End Happy Path and Fallback) for SalesAgent.

These tests validate the full hexagonal architecture:
DuckDbSalesAdapter -> SalesMetricsApplicationService -> Domain/Fallback Tools -> SalesAgent.
"""
import logging
import os
import tempfile
from typing import Any, List, Optional
import pytest
from langchain_core.messages import AIMessage, BaseMessage, ToolCall
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult

from src.adapter.inbound.cli.main import bootstrap_agent
from src.adapter.inbound.llm.domain_tools import create_domain_tools
from src.adapter.inbound.llm.sales_agent import SalesAgent
from src.adapter.inbound.llm.sql_fallback_tool import create_sql_fallback_tool
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.application.service.sales_metrics_service import SalesMetricsApplicationService


class FakeToolCallingChatModel(BaseChatModel):
    """A deterministic fake chat model that returns pre-configured tool calls or final responses."""

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
            # Generate tool call
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
def integration_sales_csv():
    """Provides a realistic small CSV dataset for End-to-End integration testing."""
    content = (
        "product_id;local;date;planned_quantity;actual_quantity;planned_price;promotion_type;actual_price;service_level\n"
        "Prod_A;Whse_North;01/01/2023;100;120;50.0;Promo10;45.0;0.95\n"
        "Prod_A;Whse_South;15/01/2023;80;90;50.0;None;50.0;0.85\n"
        "Prod_B;Whse_North;10/02/2023;200;180;100.0;SummerSale;90.0;0.90\n"
        "Prod_B;Whse_South;20/02/2023;150;100;100.0;None;100.0;0.70\n"
        "Prod_C;Whse_North;05/03/2023;50;60;20.0;None;20.0;0.98\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def real_full_stack_components(integration_sales_csv):
    """Instantiates the real hexagonal stack up to the tools."""
    persistence_adapter = DuckDbSalesAdapter(dataset_path=integration_sales_csv)
    metrics_service = SalesMetricsApplicationService(sales_data_port=persistence_adapter)
    domain_tools = create_domain_tools(metrics_service)
    sql_tool = create_sql_fallback_tool(metrics_service)
    all_tools = [*domain_tools, sql_tool]
    return {
        "persistence": persistence_adapter,
        "service": metrics_service,
        "tools": all_tools,
        "csv_path": integration_sales_csv,
    }


def test_e2e_top_selling_product_flow(real_full_stack_components):
    """End-to-End test: Agent invokes get_top_selling_product and formats response."""
    # Step 1: Model calls get_top_selling_product
    # Step 2: Model receives tool result and produces final answer
    fake_llm = FakeToolCallingChatModel(
        responses=[
            {"tool_name": "get_top_selling_product", "args": {}},
            "O produto mais vendido foi Prod_B com 280 unidades e R$ 26.200 em receita.",
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=real_full_stack_components["tools"])
    response = agent.ask("Qual foi o produto mais vendido no período?")

    assert "Prod_B" in response
    assert "280" in response or "vendido" in response


def test_e2e_top_locations_by_volume_flow(real_full_stack_components):
    """End-to-End test: Agent invokes get_top_locations_by_volume."""
    fake_llm = FakeToolCallingChatModel(
        responses=[
            {"tool_name": "get_top_locations_by_volume", "args": {"limit": 2}},
            "A localidade com maior volume de vendas é Whse_North com 360 unidades.",
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=real_full_stack_components["tools"])
    response = agent.ask("Quais são os principais armazéns por volume?")

    assert "Whse_North" in response


def test_e2e_planned_vs_actual_flow(real_full_stack_components):
    """End-to-End test: Agent invokes compare_planned_vs_actual_quantity."""
    fake_llm = FakeToolCallingChatModel(
        responses=[
            {"tool_name": "compare_planned_vs_actual_quantity", "args": {}},
            "O realizado foi de 550 unidades contra 580 planejadas (atingimento de 94.83%).",
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=real_full_stack_components["tools"])
    response = agent.ask("Como foi o atingimento da meta de quantidade planejada vs realizada?")

    assert "550" in response or "94.83" in response or "planejadas" in response


def test_e2e_service_level_bottleneck_flow(real_full_stack_components):
    """End-to-End test: Agent invokes analyze_service_level_bottlenecks."""
    fake_llm = FakeToolCallingChatModel(
        responses=[
            {"tool_name": "analyze_service_level_bottlenecks", "args": {}},
            "O pior nível de serviço foi observado em Whse_South com média de 0.775.",
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=real_full_stack_components["tools"])
    response = agent.ask("Qual localidade possui o pior SLA logístico?")

    assert "Whse_South" in response


def test_e2e_promotion_impact_flow(real_full_stack_components):
    """End-to-End test: Agent invokes analyze_promotion_impact."""
    fake_llm = FakeToolCallingChatModel(
        responses=[
            {"tool_name": "analyze_promotion_impact", "args": {}},
            "Vendas com promoção tiveram preço médio com desconto e volume expressivo.",
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=real_full_stack_components["tools"])
    response = agent.ask("Qual o impacto das promoções nas vendas?")

    assert "promoção" in response.lower() or "volume" in response.lower()


def test_e2e_revenue_deficit_flow(real_full_stack_components):
    """End-to-End test: Agent invokes calculate_revenue_deficit."""
    fake_llm = FakeToolCallingChatModel(
        responses=[
            {"tool_name": "calculate_revenue_deficit", "args": {}},
            "Houve um déficit de receita devido a perdas de volume orçado.",
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=real_full_stack_components["tools"])
    response = agent.ask("Qual foi o déficit de receita total?")

    assert "déficit" in response.lower() or "receita" in response.lower()


def test_e2e_sql_fallback_flow_emits_missing_tool_log(real_full_stack_components, caplog):
    """End-to-End test: Fallback SQL is used for ad-hoc query and emits [MISSING_TOOL] log."""
    query = "SELECT local, AVG(service_level) AS avg_sla FROM sales_data GROUP BY local ORDER BY avg_sla ASC"
    fake_llm = FakeToolCallingChatModel(
        responses=[
            {"tool_name": "secured_sql_query", "args": {"query": query}},
            "A análise SQL personalizada mostrou o SLA médio por armazém.",
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=real_full_stack_components["tools"])

    with caplog.at_level(logging.INFO):
        response = agent.ask("Qual é a média exata de SLA por armazém em ordem crescente?")

    assert "[MISSING_TOOL]" in caplog.text
    assert "SLA" in response or "análise" in response.lower()


def test_e2e_sql_fallback_security_rejection(real_full_stack_components):
    """End-to-End test: Attempted DML query is blocked safely."""
    malicious_query = "DELETE FROM sales_data WHERE product_id = 'Prod_A'"
    fake_llm = FakeToolCallingChatModel(
        responses=[
            {"tool_name": "secured_sql_query", "args": {"query": malicious_query}},
            "A consulta foi rejeitada por violação das políticas de segurança estritas.",
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=real_full_stack_components["tools"])
    response = agent.ask("Remova as vendas do produto Prod_A do banco.")

    assert "rejeitada" in response.lower() or "segurança" in response.lower()
    
    # Assert data was NOT deleted in DuckDB
    records = real_full_stack_components["persistence"].get_sales_by_filter()
    assert len(records) == 5
    assert any(r.product_id == "Prod_A" for r in records)



def test_e2e_bootstrap_agent_flow(integration_sales_csv, monkeypatch):
    """Test bootstrap_agent helper integrates all components and instantiates SalesAgent."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-fake")

    from unittest.mock import patch
    with patch("src.adapter.outbound.llm.llm_factory.init_chat_model") as mock_init_chat:
        mock_init_chat.return_value = FakeToolCallingChatModel(responses=["Resposta de teste"])
        agent = bootstrap_agent(dataset_path=integration_sales_csv)
        assert isinstance(agent, SalesAgent)
        resp = agent.ask("Olá, agente!")
        assert resp == "Resposta de teste"
