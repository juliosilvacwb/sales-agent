"""Domain models and schema definitions for Golden Evaluations."""
from enum import Enum
import json
from pathlib import Path
from typing import Any, Dict, List, Set, Union
from pydantic import BaseModel, Field, field_validator


class GoldenEvalCategory(str, Enum):
    """Categories of golden evaluation benchmarks."""
    REVENUE = "REVENUE"
    PROMOTION = "PROMOTION"
    LOGISTICS = "LOGISTICS"
    SEASONALITY = "SEASONALITY"
    ELASTICITY = "ELASTICITY"
    AD_HOC_SQL = "AD_HOC_SQL"


KNOWN_TOOLS: Set[str] = {
    "get_top_selling_product",
    "get_top_locations_by_volume",
    "get_total_sales_in_period",
    "compare_planned_vs_actual_quantity",
    "analyze_promotion_impact",
    "analyze_service_level_bottlenecks",
    "calculate_revenue_deficit",
    "calculate_average_discount",
    "identify_sales_seasonality",
    "calculate_price_elasticity",
    "secured_sql_query",
}


class GoldenEvalRecord(BaseModel):
    """Schema representing a single benchmark evaluation record."""
    eval_id: str = Field(..., description="Unique evaluation identifier")
    category: GoldenEvalCategory = Field(..., description="Analytical category")
    question: str = Field(..., description="Natural language business question")
    expected_tool: str = Field(..., description="Expected tool the agent must route to")
    expected_metrics: Dict[str, Any] = Field(..., description="Ground-truth metrics to assert against")

    @field_validator("eval_id", "question")
    @classmethod
    def validate_non_empty_string(cls, value: str, info) -> str:
        if not value or not value.strip():
            raise ValueError(f"Field '{info.field_name}' cannot be empty.")
        return value.strip()

    @field_validator("expected_tool")
    @classmethod
    def validate_known_tool(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in KNOWN_TOOLS:
            raise ValueError(
                f"Unknown expected_tool '{cleaned}'. Must be one of {sorted(KNOWN_TOOLS)}."
            )
        return cleaned

    @field_validator("expected_metrics")
    @classmethod
    def validate_expected_metrics(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if not value:
            raise ValueError("Field 'expected_metrics' cannot be empty.")
        for k, v in value.items():
            if not k or not str(k).strip():
                raise ValueError("Metric key cannot be empty.")
            if v is None:
                raise ValueError(f"Metric value for key '{k}' cannot be None.")
        return value


def load_golden_dataset(file_path: Union[str, Path]) -> List[GoldenEvalRecord]:
    """Loads and validates a Golden Benchmark dataset from a JSON file.

    Args:
        file_path: Path to the JSON dataset file.

    Returns:
        List of validated GoldenEvalRecord instances.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If JSON is malformed or records fail schema validation.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Golden dataset file not found at: {path}")

    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse golden dataset JSON at {path}: {exc}") from exc

    if not isinstance(raw_data, list):
        raise ValueError(f"Golden dataset root must be a JSON array (list), got {type(raw_data).__name__}.")

    records: List[GoldenEvalRecord] = []
    for idx, item in enumerate(raw_data):
        try:
            record = GoldenEvalRecord.model_validate(item)
            records.append(record)
        except Exception as exc:
            raise ValueError(f"Validation failed for record index {idx}: {exc}") from exc

    return records
