# Incident Summary

- **Test Coverage:** [TEST002-data-analysis-promotions.md](../tests/TEST002-data-analysis-promotions.md)
- **Security Audit:** [S002-data-analysis-promotions.md](../security/S002-data-analysis-promotions.md)

The AI reports that the overall average discount is 0% and that there were no promotional sales or discounts applied, even though the dataset clearly contains "Flash" promotions with sales.

## Technical Analysis of Root Cause

The bug lies in `AdvancedMetricsService.calculate_average_discount` located in `src/domain/service/advanced_metrics_service.py`. There are two main issues:

1. **Total Discount Calculation:** `total_discount_val` is calculated as `max(0.0, total_planned_rev - total_actual_rev)` over all records globally. Because the total actual revenue is greater than the total planned revenue across the entire dataset (due to some items being sold at a premium), this global subtraction evaluates to `< 0`, making the `max()` return `0.0`. The calculation must sum the discounts *only* for the records where `actual_price < planned_price`.
2. **Average Discount Percentage:** `avg_discount_pct` is computed by averaging `r.discount_rate` across all records. Since `discount_rate` can be negative (when `actual_price > planned_price`), the positive and negative rates cancel each other out across 200,000+ records, resulting in ~0.001%, which rounds down to `0.0%`.

As a consequence, the `average_discount_in_promotion` might show a 20% discount for "Flash", but the overall discount value reads as 0, which confuses the AI into believing no discounts were actually applied.

## Reproduction Script (MANDATORY)

```python
import pytest
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.domain.service.advanced_metrics_service import AdvancedMetricsService
from src.domain.service.basic_metrics_service import BasicMetricsService
from src.application.service.sales_metrics_service import SalesMetricsApplicationService


def test_data_analysis_promotions_reproduction():
    """
    Automated Reproduction Test for the Data Analysis Promotions Error.
    Validates that the total discount value and overall discount percentage
    are calculated correctly instead of returning 0.0.
    """
    adapter = DuckDbSalesAdapter(dataset_path="dataset/sales.csv")
    service = SalesMetricsApplicationService(
        sales_data_port=adapter,
        basic_metrics_service=BasicMetricsService(),
        advanced_metrics_service=AdvancedMetricsService(),
    )

    result = service.calculate_average_discount()

    # We expect this test to FAIL currently because result.total_discount_value is 0.0
    # and result.overall_average_discount_percentage is 0.0.
    # The Engineer Agent will fix the logic in AdvancedMetricsService.
    assert result.total_discount_value > 0.0, (
        f"Expected positive discount value, got {result.total_discount_value}"
    )
    assert result.overall_average_discount_percentage > 0.0, (
        f"Expected positive discount percentage, got {result.overall_average_discount_percentage}"
    )
```

## Correction Checklist (Atomic Tasks)

- [COMPLETED] Task 001 - [Test] Implement the reproduction script in `tests/integration/test_data_analysis_incident_b002.py` and confirm the failure (Red).
- [COMPLETED] Task 002 - [Logic] Fix `calculate_average_discount` in `src/domain/service/advanced_metrics_service.py` to only accumulate positive discount rates and properly sum individual positive discount values.
- [COMPLETED] Task 003 - [Security/Perf] Add unit tests in `tests/unit/test_advanced_metrics_service.py` for edge cases where there are mixed price increases and decreases.

