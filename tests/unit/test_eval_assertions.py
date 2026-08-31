"""Unit tests for the Deterministic Assertion Engine."""
import pytest

from tests.evals.assertions import (
    assert_metrics_match,
    compare_metric_value,
    format_diagnostic_report,
    sanitize_diagnostic_text,
)


def test_assert_metrics_match_exact_values():
    """Test exact equality for scalar numbers, strings and booleans."""
    expected = {
        "product_id": "Prod_A",
        "total_records": 5,
        "has_deficit": True,
        "summary": "OK",
    }
    actual = {
        "product_id": "Prod_A",
        "total_records": 5,
        "has_deficit": True,
        "summary": "OK",
        "extra_field": "ignored_or_present",
    }
    assert_metrics_match(expected, actual)


def test_assert_metrics_match_float_within_tolerance():
    """Test float values matching within default abs_tol=0.01 and rel_tol=1e-3."""
    expected = {
        "total_quantity": 550.0,
        "total_revenue": 37300.0,
        "achievement_percentage": 94.827,
    }
    actual = {
        "total_quantity": 550.004,
        "total_revenue": 37300.008,
        "achievement_percentage": 94.8271,
    }
    assert_metrics_match(expected, actual)


def test_assert_metrics_match_float_exceeding_tolerance():
    """Test assertion failure when float difference exceeds tolerance."""
    expected = {"total_revenue": 37300.0}
    actual = {"total_revenue": 37400.0}

    with pytest.raises(AssertionError, match="total_revenue"):
        assert_metrics_match(expected, actual)


def test_assert_metrics_match_missing_key_in_actual():
    """Test assertion failure when expected metric key is missing from actual output."""
    expected = {"product_id": "Prod_A", "total_quantity": 100.0}
    actual = {"product_id": "Prod_A"}

    with pytest.raises(AssertionError, match="Missing expected metric key 'total_quantity'"):
        assert_metrics_match(expected, actual)


def test_assert_metrics_match_nested_dict():
    """Test assertion matching on nested dictionary structures."""
    expected = {
        "location_averages": {
            "Whse_North": 0.95,
            "Whse_South": 0.775,
        }
    }
    actual = {
        "location_averages": {
            "Whse_North": 0.9501,
            "Whse_South": 0.7752,
        }
    }
    assert_metrics_match(expected, actual)


def test_assert_metrics_match_boolean_strictness():
    """Test that boolean is strictly compared and not confused with 0/1."""
    expected = {"has_deficit": True}
    actual = {"has_deficit": False}

    with pytest.raises(AssertionError, match="has_deficit"):
        assert_metrics_match(expected, actual)


def test_assert_metrics_match_list():
    """Test assertion matching on list structures."""
    expected = {"items": [10.0, 20.0, "Prod_A"]}
    actual = {"items": [10.001, 19.999, "Prod_A"]}
    assert_metrics_match(expected, actual)


def test_assert_metrics_match_list_mismatch():
    """Test assertion failure on list length or item mismatch."""
    expected = {"items": [10.0, 20.0]}
    actual = {"items": [10.0, 30.0]}
    with pytest.raises(AssertionError):
        assert_metrics_match(expected, actual)


def test_assert_metrics_match_non_dict_actual():
    """Test assertion failure when actual payload is not a dictionary."""
    with pytest.raises(AssertionError, match="not a dictionary"):
        assert_metrics_match({"key": 1}, "string_payload")


def test_format_diagnostic_report():
    """Test formatted diagnostic error reporting."""
    report = format_diagnostic_report(
        eval_id="EVAL_001",
        expected_tool="get_top_selling_product",
        actual_tool="get_top_selling_product",
        mismatches=[("total_revenue", 26200.0, 25000.0, -1200.0)],
    )

    assert "EVAL_001" in report
    assert "total_revenue" in report
    assert "26200" in report
    assert "25000" in report
    assert "Delta" in report or "delta" in report.lower()


def test_format_diagnostic_report_sanitizes_paths_and_crlf():
    """Test that file paths are redacted and CRLF characters sanitized in diagnostic reports."""
    report = format_diagnostic_report(
        eval_id="EVAL_001\r\nINJECTED",
        expected_tool="get_top_selling_product",
        actual_tool="get_top_selling_product",
        mismatches=[("error_msg", "Expected OK", "Error reading C:\\Users\\secret\\dataset.csv", None)],
        raw_payload={"path": "/home/ubuntu/app/secret/config.json", "details": "Error at C:\\Users\\admin\\app.py"},
    )

    assert "[REDACTED_PATH]" in report
    assert "C:\\Users\\secret\\dataset.csv" not in report
    assert "/home/ubuntu/app/secret/config.json" not in report
    assert "C:\\Users\\admin\\app.py" not in report
    assert "\r\nINJECTED" not in report


def test_sanitize_diagnostic_text_truncation():
    """Test that overly long diagnostic text payloads are truncated."""
    long_text = "A" * 1200
    sanitized = sanitize_diagnostic_text(long_text, max_length=100)
    assert len(sanitized) <= 125
    assert "[TRUNCATED]" in sanitized

