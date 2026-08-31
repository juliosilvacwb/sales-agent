"""Unit tests for ToolInterceptionCallbackHandler."""
import json
from uuid import uuid4
import pytest
from langchain_core.messages import ToolMessage

from tests.evals.interceptor import ToolInterceptionCallbackHandler, ToolInvocationRecord


def test_interceptor_initial_state():
    """Test initial empty state of interceptor."""
    handler = ToolInterceptionCallbackHandler()
    assert not handler.has_invocations
    assert handler.invocation_count == 0
    assert handler.actual_tool_name is None
    assert handler.parsed_tool_output is None
    assert handler.raw_tool_output is None
    assert handler.all_invocations == []


def test_interceptor_captures_tool_lifecycle():
    """Test capturing tool start and tool end with JSON payload."""
    handler = ToolInterceptionCallbackHandler()
    run_id = uuid4()
    serialized = {"name": "get_top_selling_product"}
    input_str = "{}"

    handler.on_tool_start(serialized, input_str, run_id=run_id)
    assert handler.has_invocations
    assert handler.actual_tool_name == "get_top_selling_product"
    assert handler.invocation_count == 1

    tool_data = {
        "product_id": "Prod_B",
        "total_quantity": 280.0,
        "total_revenue": 26200.0,
    }
    json_output = json.dumps(tool_data)

    handler.on_tool_end(json_output, run_id=run_id)

    assert handler.actual_tool_name == "get_top_selling_product"
    assert handler.raw_tool_output == json_output
    assert handler.parsed_tool_output == tool_data
    assert handler.all_invocations[0].error is None


def test_interceptor_handles_tool_message_output():
    """Test capturing tool end when output is wrapped in a ToolMessage."""
    handler = ToolInterceptionCallbackHandler()
    run_id = uuid4()
    handler.on_tool_start({"name": "analyze_promotion_impact"}, "", run_id=run_id)

    tool_data = {"volume_lift_percentage": 25.5}
    tool_msg = ToolMessage(content=json.dumps(tool_data), tool_call_id="call_123")

    handler.on_tool_end(tool_msg, run_id=run_id)

    assert handler.actual_tool_name == "analyze_promotion_impact"
    assert handler.parsed_tool_output == tool_data


def test_interceptor_handles_non_json_output():
    """Test capturing non-JSON string output."""
    handler = ToolInterceptionCallbackHandler()
    run_id = uuid4()
    handler.on_tool_start({"name": "secured_sql_query"}, "SELECT 1", run_id=run_id)
    handler.on_tool_end("Plain text output without JSON", run_id=run_id)

    assert handler.actual_tool_name == "secured_sql_query"
    assert handler.raw_tool_output == "Plain text output without JSON"
    assert handler.parsed_tool_output == "Plain text output without JSON"


def test_interceptor_captures_tool_error():
    """Test capturing tool error."""
    handler = ToolInterceptionCallbackHandler()
    run_id = uuid4()
    handler.on_tool_start({"name": "secured_sql_query"}, "INVALID SQL", run_id=run_id)
    
    err = ValueError("Syntax error near INVALID")
    handler.on_tool_error(err, run_id=run_id)

    assert handler.has_invocations
    assert handler.all_invocations[0].error == "Syntax error near INVALID"


def test_interceptor_multiple_invocations_and_clear():
    """Test capturing multiple tool runs and clearing state."""
    handler = ToolInterceptionCallbackHandler()
    
    # Tool 1
    run1 = uuid4()
    handler.on_tool_start({"name": "get_top_selling_product"}, "", run_id=run1)
    handler.on_tool_end(json.dumps({"product_id": "P1"}), run_id=run1)

    # Tool 2
    run2 = uuid4()
    handler.on_tool_start({"name": "calculate_price_elasticity"}, "", run_id=run2)
    handler.on_tool_end(json.dumps({"elasticity_coefficient": -1.5}), run_id=run2)

    assert handler.invocation_count == 2
    assert handler.actual_tool_name == "get_top_selling_product"
    assert handler.all_invocations[1].tool_name == "calculate_price_elasticity"
    assert handler.all_invocations[1].parsed_output == {"elasticity_coefficient": -1.5}

    handler.clear()
    assert not handler.has_invocations
    assert handler.invocation_count == 0
