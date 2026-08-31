"""Unit test verifying the Golden Evals execution harness with deterministic fake LLM."""
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from tests.evals.assertions import assert_metrics_match
from tests.evals.eval_models import GoldenEvalRecord, load_golden_dataset
from tests.evals.interceptor import ToolInterceptionCallbackHandler
from tests.evals.test_golden_evals import execute_with_retry
from tests.integration.test_agent_integration import FakeToolCallingChatModel
from src.adapter.inbound.llm.domain_tools import create_domain_tools
from src.adapter.inbound.llm.sales_agent import SalesAgent
from src.adapter.inbound.llm.sql_fallback_tool import create_sql_fallback_tool
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.application.service.sales_metrics_service import SalesMetricsApplicationService


@pytest.fixture
def eval_stack():
    """Sets up the real analytical stack wired to the evaluation dataset fixture."""
    fixture_path = Path(__file__).resolve().parent.parent / "fixtures" / "eval_dataset.csv"
    adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=str(fixture_path))
    use_case = SalesMetricsApplicationService(sales_data_port=adapter)
    domain_tools = create_domain_tools(sales_use_case=use_case)
    sql_tool = create_sql_fallback_tool(sales_use_case=use_case)
    all_tools = domain_tools + [sql_tool]
    return {"use_case": use_case, "tools": all_tools}


def test_golden_eval_runner_passes_canonical_case(eval_stack):
    """Test that Golden Eval harness executes query, intercepts tool and matches exact metrics."""
    # Setup deterministic fake LLM that routes to get_top_selling_product
    fake_llm = FakeToolCallingChatModel(
        responses=[
            {"tool_name": "get_top_selling_product", "args": {}},
            "O produto mais vendido foi Prod_B com 280 unidades.",
        ]
    )
    agent = SalesAgent(llm=fake_llm, tools=eval_stack["tools"])
    interceptor = ToolInterceptionCallbackHandler()

    record = GoldenEvalRecord(
        eval_id="EVAL_001_TEST",
        category="REVENUE",
        question="Qual o produto mais vendido?",
        expected_tool="get_top_selling_product",
        expected_metrics={
            "product_id": "Prod_B",
            "total_quantity": 280.0,
            "total_revenue": 26200.0,
        },
    )

    agent.ask(record.question, callbacks=[interceptor])

    assert interceptor.has_invocations
    assert interceptor.actual_tool_name == record.expected_tool
    assert_metrics_match(
        record.expected_metrics,
        interceptor.parsed_tool_output,
        eval_id=record.eval_id,
        expected_tool=record.expected_tool,
        actual_tool=interceptor.actual_tool_name,
    )


def test_golden_eval_runner_catches_routing_mismatch(eval_stack):
    """Test that harness fails when agent routes to wrong tool (Prompt Drift)."""
    # Fake LLM incorrectly routes to secured_sql_query instead of domain tool
    fake_llm = FakeToolCallingChatModel(
        responses=[
            {"tool_name": "secured_sql_query", "args": {"query": "SELECT 1"}},
            "Resultado.",
        ]
    )
    agent = SalesAgent(llm=fake_llm, tools=eval_stack["tools"])
    interceptor = ToolInterceptionCallbackHandler()

    record = GoldenEvalRecord(
        eval_id="EVAL_001_MISROUTE",
        category="REVENUE",
        question="Qual o produto mais vendido?",
        expected_tool="get_top_selling_product",
        expected_metrics={"product_id": "Prod_B"},
    )

    agent.ask(record.question, callbacks=[interceptor])

    assert interceptor.actual_tool_name != record.expected_tool
    assert interceptor.actual_tool_name == "secured_sql_query"


def test_golden_eval_runner_catches_metric_regression(eval_stack):
    """Test that harness raises AssertionError when mathematical metric regresses."""
    fake_llm = FakeToolCallingChatModel(
        responses=[
            {"tool_name": "get_top_selling_product", "args": {}},
            "O produto mais vendido foi Prod_B.",
        ]
    )
    agent = SalesAgent(llm=fake_llm, tools=eval_stack["tools"])
    interceptor = ToolInterceptionCallbackHandler()

    # Intentionally wrong expected revenue
    record = GoldenEvalRecord(
        eval_id="EVAL_001_REGRESSION",
        category="REVENUE",
        question="Qual o produto mais vendido?",
        expected_tool="get_top_selling_product",
        expected_metrics={
            "product_id": "Prod_B",
            "total_revenue": 99999.0,  # Actual is 26200.0
        },
    )

    agent.ask(record.question, callbacks=[interceptor])

    with pytest.raises(AssertionError, match="GOLDEN EVALUATION FAILURE"):
        assert_metrics_match(
            record.expected_metrics,
            interceptor.parsed_tool_output,
            eval_id=record.eval_id,
            expected_tool=record.expected_tool,
            actual_tool=interceptor.actual_tool_name,
        )


def test_golden_eval_retry_mechanism_on_transient_errors():
    """Test that execute_with_retry recovers from transient errors and raises permanent ones."""
    attempts = {"count": 0}

    def transient_fn():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("429 Too Many Requests: Rate limit exceeded")
        return "success"

    result = execute_with_retry(transient_fn, max_retries=3, base_delay=0.001)
    assert result == "success"
    assert attempts["count"] == 3

    # Permanent error fails immediately
    def permanent_error_fn():
        raise ValueError("Invalid configuration")

    with pytest.raises(ValueError, match="Invalid configuration"):
        execute_with_retry(permanent_error_fn, max_retries=3, base_delay=0.001)

    # 401 Unauthorized fails immediately on first attempt without retrying
    auth_attempts = {"count": 0}

    def auth_error_fn():
        auth_attempts["count"] += 1
        raise RuntimeError("401 Unauthorized: Invalid API key")

    with pytest.raises(RuntimeError, match="401 Unauthorized"):
        execute_with_retry(auth_error_fn, max_retries=3, base_delay=0.001)
    assert auth_attempts["count"] == 1


def test_github_actions_workflow_specification():
    """Test that GitHub Actions evals workflow file exists and has correct triggers and steps."""
    workflow_path = Path(__file__).resolve().parent.parent.parent / ".github" / "workflows" / "evals.yml"
    assert workflow_path.exists(), "Workflow file .github/workflows/evals.yml must exist"

    content = workflow_path.read_text(encoding="utf-8")
    assert "name: Golden Evals CI" in content
    assert "pytest tests/evals/test_golden_evals.py" in content
    assert "OPENAI_API_KEY" in content

