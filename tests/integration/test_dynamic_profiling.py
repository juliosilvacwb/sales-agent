"""Integration tests for Dynamic Data Profiling and Context Injection (T011 / R011)."""
import os
import tempfile
from typing import Any, List, Optional
import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from src.adapter.inbound.cli.main import bootstrap_agent
from src.adapter.inbound.llm.domain_tools import create_domain_tools
from src.adapter.inbound.llm.sales_agent import SalesAgent, SYSTEM_PROMPT
from src.adapter.inbound.llm.sql_fallback_tool import create_sql_fallback_tool
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.application.service.sales_metrics_service import SalesMetricsApplicationService


class FakeProfilingChatModel(BaseChatModel):
    """Deterministic fake chat model that inspects system prompt and invokes sql fallback tool."""

    responses: List[Any] = []
    _call_count: int = 0
    received_system_prompt: Optional[str] = None

    def __init__(self, responses: List[Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.responses = responses
        self._call_count = 0

    @property
    def _llm_type(self) -> str:
        return "fake-profiling-chat-model"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeProfilingChatModel":
        return self

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Capture system message / prompt
        for msg in messages:
            if hasattr(msg, "content") and "Sales Data Analysis Agent" in str(msg.content):
                self.received_system_prompt = str(msg.content)

        if self._call_count < len(self.responses):
            resp = self.responses[self._call_count]
            self._call_count += 1
        else:
            resp = "Resposta simulada padrão."

        if isinstance(resp, str):
            ai_msg = AIMessage(content=resp)
        elif isinstance(resp, dict) and "tool_name" in resp:
            ai_msg = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": resp["tool_name"],
                        "args": resp.get("args", {}),
                        "id": "call_profiling_001",
                        "type": "tool_call",
                    }
                ],
            )
        else:
            ai_msg = AIMessage(content=str(resp))

        return ChatResult(generations=[ChatGeneration(message=ai_msg)])


@pytest.fixture
def profile_test_csv():
    """Seeds a CSV dataset with sentinel 'None' strings for promotion_type and constant service_level 0.99."""
    content = (
        "product_id;local;date;planned_quantity;actual_quantity;planned_price;promotion_type;actual_price;service_level\n"
        "Prod_A;Whse_1;01/01/2024;100;90;50.0;None;50.0;0.99\n"
        "Prod_A;Whse_1;02/01/2024;120;110;50.0;PromoX;45.0;0.99\n"
        "Prod_B;Whse_2;05/01/2024;200;210;30.0;None;30.0;0.99\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_dynamic_data_profiling_prompt_injection_e2e(profile_test_csv, monkeypatch):
    """[TEST011-15] Verify that bootstrap_agent extracts profile and injects dynamic insights block into SalesAgent."""
    monkeypatch.setattr(
        "src.adapter.outbound.llm.llm_factory.LLMFactory.create_llm",
        lambda: FakeProfilingChatModel([]),
    )
    agent = bootstrap_agent(dataset_path=profile_test_csv)

    assert "### DYNAMIC DATA INSIGHTS:" in agent.system_prompt
    assert "Total de registros no dataset: 3" in agent.system_prompt
    assert "01/01/2024 até 05/01/2024" in agent.system_prompt
    assert "'promotion_type': Vendas não promocionais/valores nulos utilizam a string 'None'" in agent.system_prompt
    assert "WHERE promotion_type = 'None'" in agent.system_prompt
    assert "'service_level': Coluna constante com valor fixo 0.99 em todos os registros." in agent.system_prompt


def test_dynamic_profiling_sql_generation_with_sentinel_none(profile_test_csv):
    """[TEST011-16] Verify end-to-end question handling with SQL query using detected sentinel 'None'."""
    adapter = DuckDbSalesAdapter(dataset_path=profile_test_csv)
    metrics_service = SalesMetricsApplicationService(sales_data_port=adapter)
    domain_tools = create_domain_tools(metrics_service)
    sql_tool = create_sql_fallback_tool(metrics_service)
    tools = [*domain_tools, sql_tool]

    profile = adapter.profile_dataset()

    target_sql = "SELECT count(*) AS total_non_promo FROM sales_data WHERE promotion_type = 'None'"
    fake_llm = FakeProfilingChatModel(
        responses=[
            {
                "tool_name": "secured_sql_query",
                "args": {"query": target_sql},
            },
            "Foram realizadas 2 vendas sem promoção no período.",
        ]
    )

    agent = SalesAgent(llm=fake_llm, tools=tools, dataset_profile=profile)
    response = agent.ask("Quantas vendas não tiveram promoção?")

    # Verify LLM was passed dynamic prompt
    assert fake_llm.received_system_prompt is not None
    assert "### DYNAMIC DATA INSIGHTS:" in fake_llm.received_system_prompt
    assert "WHERE promotion_type = 'None'" in fake_llm.received_system_prompt

    # Verify tool execution succeeded and final response received
    assert "2 vendas sem promoção" in response


def test_dynamic_profiling_safe_fallback_on_corrupted_dataset(monkeypatch):
    """[TEST011-17] Verify that if profiling fails (e.g. missing file/table), bootstrap proceeds safely with default prompt."""
    monkeypatch.setattr(
        "src.adapter.outbound.llm.llm_factory.LLMFactory.create_llm",
        lambda: FakeProfilingChatModel([]),
    )
    agent = bootstrap_agent(dataset_path="non_existent_dataset.csv")

    assert agent is not None
    assert agent.system_prompt == SYSTEM_PROMPT
    assert "### DYNAMIC DATA INSIGHTS:" not in agent.system_prompt

