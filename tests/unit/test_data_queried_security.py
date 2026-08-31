"""Unit tests for S013 Security Audit specifications.

Validates fail-closed behaviors, tool name resolution, and whitelist enforcement in ToolTrackingCallbackHandler.
"""
import pytest
from src.adapter.inbound.llm.sales_agent import DATA_QUERY_TOOLS, ToolTrackingCallbackHandler


def test_tool_tracking_callback_handler_fail_closed_on_unresolved_tool_name():
    """[S013-01 / CWE-1188] Assert that on_tool_end with missing/None tool_name remains fail-closed (False)."""
    handler = ToolTrackingCallbackHandler()
    assert handler.has_queried_data is False

    # Dispatch tool end with None tool_name and empty kwargs/serialized
    handler.on_tool_end(output="any output", name=None)
    assert handler.has_queried_data is False

    # Dispatch tool start with empty serialized dict
    handler.on_tool_start(serialized={}, input_str="{}")
    assert handler.has_queried_data is False


def test_tool_tracking_callback_handler_fail_closed_on_empty_data_tools_whitelist():
    """[S013-02 / CWE-184] Assert that an empty data_tools collection never flags queries as True."""
    handler = ToolTrackingCallbackHandler(data_tools=[])
    assert handler.has_queried_data is False

    # Dispatch known domain tool when whitelist is explicitly empty
    handler.on_tool_start(serialized={"name": "get_top_selling_product"}, input_str="{}")
    assert handler.has_queried_data is False

    handler.on_tool_end(output="{}", name="get_top_selling_product")
    assert handler.has_queried_data is False


def test_tool_tracking_callback_handler_flags_true_only_for_whitelisted_data_tools():
    """[S013-01 / S013-02] Assert that only explicitly whitelisted tools trigger has_queried_data=True."""
    handler = ToolTrackingCallbackHandler()

    # Non-data utility tool execution (e.g. calculator or formatter)
    handler.on_tool_start(serialized={"name": "calculator_tool"}, input_str="{}")
    handler.on_tool_end(output="42", name="calculator_tool")
    assert not handler.has_queried_data

    # Data query tool execution from DATA_QUERY_TOOLS
    handler.on_tool_start(serialized={"name": "secured_sql_query"}, input_str="{}")
    assert handler.has_queried_data

    handler_end = ToolTrackingCallbackHandler()
    handler_end.on_tool_end(output="Product_0001", name="get_top_selling_product")
    assert handler_end.has_queried_data is True
