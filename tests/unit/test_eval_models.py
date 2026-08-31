"""Unit tests for GoldenEvalRecord and dataset loader domain models."""
import json
import pytest
from pathlib import Path

from tests.evals.eval_models import (
    GoldenEvalCategory,
    GoldenEvalRecord,
    KNOWN_TOOLS,
    load_golden_dataset,
)


def test_golden_eval_record_valid_creation():
    """Test instantiating a valid GoldenEvalRecord."""
    record = GoldenEvalRecord(
        eval_id="EVAL_001_TEST",
        category=GoldenEvalCategory.REVENUE,
        question="Qual o total de vendas?",
        expected_tool="get_total_sales_in_period",
        expected_metrics={"total_quantity": 100.0, "total_revenue": 5000.0},
    )
    assert record.eval_id == "EVAL_001_TEST"
    assert record.category == GoldenEvalCategory.REVENUE
    assert record.expected_tool == "get_total_sales_in_period"
    assert record.expected_metrics["total_quantity"] == 100.0


def test_golden_eval_record_validation_errors():
    """Test validation errors for empty fields or invalid tool."""
    with pytest.raises(ValueError, match="eval_id"):
        GoldenEvalRecord(
            eval_id="",
            category=GoldenEvalCategory.REVENUE,
            question="Qual o total?",
            expected_tool="get_total_sales_in_period",
            expected_metrics={"total": 10},
        )

    with pytest.raises(ValueError, match="question"):
        GoldenEvalRecord(
            eval_id="EVAL_002",
            category=GoldenEvalCategory.REVENUE,
            question="   ",
            expected_tool="get_total_sales_in_period",
            expected_metrics={"total": 10},
        )

    with pytest.raises(ValueError, match="expected_metrics"):
        GoldenEvalRecord(
            eval_id="EVAL_003",
            category=GoldenEvalCategory.REVENUE,
            question="Pergunta válida",
            expected_tool="get_total_sales_in_period",
            expected_metrics={},
        )

    with pytest.raises(ValueError, match="cannot be None"):
        GoldenEvalRecord(
            eval_id="EVAL_003_NULL",
            category=GoldenEvalCategory.REVENUE,
            question="Pergunta válida",
            expected_tool="get_total_sales_in_period",
            expected_metrics={"total": None},
        )

    with pytest.raises(ValueError, match="cannot be empty"):
        GoldenEvalRecord(
            eval_id="EVAL_003_EMPTY_KEY",
            category=GoldenEvalCategory.REVENUE,
            question="Pergunta válida",
            expected_tool="get_total_sales_in_period",
            expected_metrics={"": 100.0},
        )

    with pytest.raises(ValueError, match="expected_tool"):
        GoldenEvalRecord(
            eval_id="EVAL_004",
            category=GoldenEvalCategory.REVENUE,
            question="Pergunta válida",
            expected_tool="unknown_non_existent_tool",
            expected_metrics={"total": 10},
        )


def test_golden_dataset_structure_and_completeness():
    """Test that golden_dataset.json contains at least 10 records covering all categories."""
    dataset_path = Path(__file__).resolve().parent.parent / "evals" / "golden_dataset.json"
    assert dataset_path.exists(), "golden_dataset.json must exist"

    raw_data = json.loads(dataset_path.read_text(encoding="utf-8"))
    assert isinstance(raw_data, list)
    assert len(raw_data) >= 10

    categories = {item["category"] for item in raw_data}
    expected_categories = {"REVENUE", "LOGISTICS", "PROMOTION", "SEASONALITY", "ELASTICITY"}
    assert expected_categories.issubset(categories)

    for item in raw_data:
        assert item["eval_id"].strip()
        assert item["question"].strip()
        assert item["expected_tool"].strip() in KNOWN_TOOLS
        assert len(item["expected_metrics"]) > 0


def test_load_golden_dataset_from_real_file():
    """Test loading the canonical golden_dataset.json file."""
    dataset_path = Path(__file__).resolve().parent.parent / "evals" / "golden_dataset.json"
    records = load_golden_dataset(dataset_path)

    assert len(records) >= 10
    eval_ids = [r.eval_id for r in records]
    assert "EVAL_001_TOP_SELLING_PRODUCT" in eval_ids
    assert "EVAL_010_PRICE_ELASTICITY" in eval_ids

    for r in records:
        assert r.expected_tool in KNOWN_TOOLS
        assert len(r.expected_metrics) > 0


def test_load_golden_dataset_file_not_found(tmp_path):
    """Test error when loading a non-existent dataset file."""
    non_existent = tmp_path / "does_not_exist.json"
    with pytest.raises(FileNotFoundError):
        load_golden_dataset(non_existent)


def test_load_golden_dataset_invalid_json(tmp_path):
    """Test error when parsing invalid JSON file."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON"):
        load_golden_dataset(invalid_file)


def test_load_golden_dataset_not_a_list(tmp_path):
    """Test error when dataset JSON is a dictionary instead of a list."""
    dict_file = tmp_path / "dict.json"
    dict_file.write_text(json.dumps({"eval_id": "test"}), encoding="utf-8")

    with pytest.raises(ValueError, match="JSON array"):
        load_golden_dataset(dict_file)
