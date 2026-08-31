"""Deterministic Assertion Engine with float tolerance for Golden Evaluations."""
import math
import re
from typing import Any, Dict, List, Optional, Tuple, Union

# Regex pattern for host filesystem absolute paths (Windows and Unix)
PATH_SANITIZATION_REGEX = re.compile(
    r"(?:[a-zA-Z]:[\\/][^\s,;\"'<>\[\]{}]+)|(?:/(?:Users|home|root|etc|var|tmp|private|opt|usr|app|Code|work)/[^\s,;\"'<>\[\]{}]+)",
    re.IGNORECASE,
)


def sanitize_diagnostic_text(text: Any, max_length: int = 500) -> str:
    """Sanitizes text output in diagnostic reports to redact file paths and limit output size."""
    if text is None:
        return ""
    str_val = str(text)
    redacted = PATH_SANITIZATION_REGEX.sub("[REDACTED_PATH]", str_val)
    if len(redacted) > max_length:
        return redacted[:max_length] + "... [TRUNCATED]"
    return redacted


def compare_metric_value(
    expected: Any,
    actual: Any,
    abs_tol: float = 0.01,
    rel_tol: float = 1e-3,
) -> Tuple[bool, Optional[str]]:
    """Compares a single expected metric value against actual value.

    Returns:
        Tuple of (is_match: bool, error_detail: Optional[str])
    """
    # Exact type match for booleans to avoid bool being treated as int (True == 1)
    if isinstance(expected, bool):
        if not isinstance(actual, bool):
            return False, f"Expected boolean {expected}, but received {type(actual).__name__} ({actual})"
        return (expected == actual), f"Expected {expected}, but received {actual}"

    # Numerical float / int comparison with tolerance
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        exp_f = float(expected)
        act_f = float(actual)
        is_close = math.isclose(exp_f, act_f, abs_tol=abs_tol, rel_tol=rel_tol)
        delta = act_f - exp_f
        detail = f"Expected {exp_f}, but received {act_f} (delta: {delta:+.4f})"
        return is_close, detail

    # Nested dictionary comparison
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False, f"Expected dictionary, but received {type(actual).__name__}"
        for sub_key, sub_exp in expected.items():
            if sub_key not in actual:
                return False, f"Missing nested key '{sub_key}' in actual output"
            match, err = compare_metric_value(sub_exp, actual[sub_key], abs_tol=abs_tol, rel_tol=rel_tol)
            if not match:
                return False, f"Nested key '{sub_key}': {err}"
        return True, None

    # List comparison
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False, f"Expected list, but received {type(actual).__name__}"
        if len(expected) != len(actual):
            return False, f"List length mismatch (Expected {len(expected)}, Actual {len(actual)})"
        for idx, (exp_item, act_item) in enumerate(zip(expected, actual)):
            match, err = compare_metric_value(exp_item, act_item, abs_tol=abs_tol, rel_tol=rel_tol)
            if not match:
                return False, f"List index [{idx}]: {err}"
        return True, None

    # String or fallback equality
    exp_str = str(expected).strip()
    act_str = str(actual).strip()
    is_eq = (exp_str == act_str)
    return is_eq, f"Expected '{exp_str}', but received '{act_str}'"


def format_diagnostic_report(
    eval_id: str,
    expected_tool: str,
    actual_tool: Optional[str],
    mismatches: List[Tuple[str, Any, Any, Any]],
    raw_payload: Optional[Any] = None,
) -> str:
    """Formats a structured diagnostic error report when an evaluation fails with sanitized text."""
    clean_eval_id = sanitize_diagnostic_text(eval_id).replace("\r", " ").replace("\n", " ")
    clean_expected_tool = sanitize_diagnostic_text(expected_tool).replace("\r", " ").replace("\n", " ")
    clean_actual_tool = (
        sanitize_diagnostic_text(actual_tool).replace("\r", " ").replace("\n", " ")
        if actual_tool
        else "NONE (No tool intercepted)"
    )

    lines = [
        "",
        "=" * 70,
        f"❌ GOLDEN EVALUATION FAILURE: {clean_eval_id}",
        "=" * 70,
        f"Expected Tool : {clean_expected_tool}",
        f"Actual Tool   : {clean_actual_tool}",
        "-" * 70,
        "METRIC MISMATCHES DETECTED:",
    ]
    for key, expected_val, actual_val, delta in mismatches:
        delta_str = f" | Delta: {delta:+.4f}" if delta is not None else ""
        clean_key = sanitize_diagnostic_text(key).replace("\r", " ").replace("\n", " ")
        clean_exp = sanitize_diagnostic_text(expected_val, max_length=200)
        clean_act = sanitize_diagnostic_text(actual_val, max_length=200)
        lines.append(f"  • [{clean_key}] Expected: {clean_exp} | Actual: {clean_act}{delta_str}")

    if raw_payload is not None:
        lines.append("-" * 70)
        lines.append(f"Intercepted Raw Tool Payload: {sanitize_diagnostic_text(raw_payload, max_length=1000)}")

    lines.append("=" * 70)
    return "\n".join(lines)


def assert_metrics_match(
    expected: Dict[str, Any],
    actual: Dict[str, Any],
    abs_tol: float = 0.01,
    rel_tol: float = 1e-3,
    eval_id: str = "EVAL_UNKNOWN",
    expected_tool: str = "UNKNOWN_TOOL",
    actual_tool: Optional[str] = None,
) -> None:
    """Asserts that all expected metrics match the actual output payload within tolerances.

    Args:
        expected: Dictionary of expected ground-truth metric values.
        actual: Dictionary of actual intercepted tool metric values.
        abs_tol: Absolute float tolerance (default: 0.01).
        rel_tol: Relative float tolerance (default: 1e-3).
        eval_id: Evaluation identifier for reporting.
        expected_tool: Expected tool name for reporting.
        actual_tool: Actual intercepted tool name for reporting.

    Raises:
        AssertionError: If any metric is missing or deviates from tolerance.
    """
    if not isinstance(actual, dict):
        raise AssertionError(
            f"Actual tool output is not a dictionary ({type(actual).__name__}): {actual}"
        )

    mismatches: List[Tuple[str, Any, Any, Any]] = []

    for key, expected_val in expected.items():
        if key not in actual:
            raise AssertionError(
                f"Missing expected metric key '{key}' in actual tool output. Available keys: {list(actual.keys())}"
            )

        actual_val = actual[key]
        match, err_detail = compare_metric_value(
            expected_val, actual_val, abs_tol=abs_tol, rel_tol=rel_tol
        )
        if not match:
            delta = None
            if isinstance(expected_val, (int, float)) and isinstance(actual_val, (int, float)) and not isinstance(expected_val, bool):
                delta = float(actual_val) - float(expected_val)
            mismatches.append((key, expected_val, actual_val, delta))

    if mismatches:
        report = format_diagnostic_report(
            eval_id=eval_id,
            expected_tool=expected_tool,
            actual_tool=actual_tool or expected_tool,
            mismatches=mismatches,
            raw_payload=actual,
        )
        raise AssertionError(report)
