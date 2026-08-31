"""Deterministic Golden Evaluations Test Suite for Sales Data Analysis Agent.

Runs benchmark natural language business queries against the SalesAgent,
intercepts the intermediate structured tool payloads, and asserts exact
mathematical matches against ground-truth values in golden_dataset.json.
"""
import logging
import os
from pathlib import Path
import time
from typing import Any, Callable, List
import pytest

from src.adapter.inbound.llm.domain_tools import create_domain_tools
from src.adapter.inbound.llm.sales_agent import SalesAgent
from src.adapter.inbound.llm.sql_fallback_tool import create_sql_fallback_tool
from src.adapter.outbound.llm.llm_factory import LLMFactory
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.application.service.sales_metrics_service import SalesMetricsApplicationService
from tests.evals.assertions import assert_metrics_match
from tests.evals.eval_models import GoldenEvalRecord, load_golden_dataset
from tests.evals.interceptor import ToolInterceptionCallbackHandler

logger = logging.getLogger(__name__)

DATASET_PATH = Path(__file__).resolve().parent / "golden_dataset.json"
FIXTURE_CSV_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "eval_dataset.csv"

# Load ground-truth benchmark records
GOLDEN_RECORDS: List[GoldenEvalRecord] = load_golden_dataset(DATASET_PATH) if DATASET_PATH.exists() else []


def execute_with_retry(func: Callable[[], Any], max_retries: int = 3, base_delay: float = 2.0) -> Any:
    """Executes a function with exponential backoff retry for transient API rate limits and network errors."""
    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except Exception as exc:
            err_str = str(exc).lower()
            # Permanent errors fail immediately without exhausting retries
            is_permanent = (
                "401" in err_str
                or "403" in err_str
                or "unauthorized" in err_str
                or "forbidden" in err_str
                or "authentication" in err_str
                or "permission" in err_str
            )
            is_transient = (
                not is_permanent
                and (
                    "429" in err_str
                    or "rate limit" in err_str
                    or "503" in err_str
                    or "500" in err_str
                    or "502" in err_str
                    or "504" in err_str
                    or "timeout" in err_str
                    or "connection" in err_str
                )
            )
            if is_transient and attempt < max_retries:
                sleep_time = min(base_delay * (2 ** (attempt - 1)), 10.0)
                logger.warning(
                    "[GOLDEN_EVAL_RETRY] Transient LLM error on attempt %d/%d (%s). Retrying in %.1fs...",
                    attempt,
                    max_retries,
                    exc,
                    sleep_time,
                )
                time.sleep(sleep_time)
            else:
                raise exc


@pytest.fixture(scope="module")
def eval_agent():
    """Builds an isolated SalesAgent instance wired to the hermetic benchmark evaluation CSV."""
    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("LLM API key not found in environment. Skipping live Golden Evaluations.")

    # Validate existence of hermetic fixture
    if not FIXTURE_CSV_PATH.exists():
        raise FileNotFoundError(f"Evaluation benchmark dataset fixture not found at: {FIXTURE_CSV_PATH}")

    # Initialize DuckDB adapter with in-memory database (:memory:) and fixed evaluation dataset
    sales_adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=str(FIXTURE_CSV_PATH))
    sales_use_case = SalesMetricsApplicationService(sales_data_port=sales_adapter)

    # Initialize domain tools and fallback tool
    domain_tools = create_domain_tools(sales_use_case=sales_use_case)
    sql_tool = create_sql_fallback_tool(sales_use_case=sales_use_case)
    all_tools = domain_tools + [sql_tool]

    # Use low-temperature model for deterministic evaluation
    llm = LLMFactory.create_llm(temperature=0.0)

    return SalesAgent(llm=llm, tools=all_tools, max_history_messages=4)


@pytest.mark.parametrize("record", GOLDEN_RECORDS, ids=lambda r: r.eval_id)
def test_golden_evaluation_case(eval_agent: SalesAgent, record: GoldenEvalRecord):
    """Executes a single golden benchmark query, intercepts tool output, and asserts mathematical match."""
    interceptor = ToolInterceptionCallbackHandler()

    # Execute query with transient error retry wrapper
    execute_with_retry(
        lambda: eval_agent.ask(record.question, callbacks=[interceptor])
    )

    # 1. Assert tool invocation occurred
    assert interceptor.has_invocations, (
        f"[{record.eval_id}] Agent did not invoke any tool for question: '{record.question}'"
    )

    # 2. Assert tool routing compliance (preventing Prompt Drift)
    assert interceptor.actual_tool_name == record.expected_tool, (
        f"[{record.eval_id}] Tool routing mismatch: Expected '{record.expected_tool}', "
        f"but agent invoked '{interceptor.actual_tool_name}'."
    )

    # 3. Assert mathematical exactness with float tolerances
    assert_metrics_match(
        expected=record.expected_metrics,
        actual=interceptor.parsed_tool_output,
        eval_id=record.eval_id,
        expected_tool=record.expected_tool,
        actual_tool=interceptor.actual_tool_name,
    )
