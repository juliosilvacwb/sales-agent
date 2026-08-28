# Incident Summary

- **Test Coverage:** [TEST003-service-level-bottlenecks.md](../tests/TEST003-service-level-bottlenecks.md)
- **Security Audit:** [S003-service-level-bottlenecks.md](../security/S003-service-level-bottlenecks.md)

The AI assistant hallucinates a false positive SLA bottleneck for `Whse_A` when asked which location presents the worst logistic service level. Although all locations in the dataset (Whse_A, Whse_J, Whse_C, Whse_S) have identical average service levels (98.00%), the system identifies `Whse_A` as the "critical SLA bottleneck", causing contradictions when challenged by the user.

## Technical Analysis of Root Cause

The issue is located in `AdvancedMetricsService.analyze_service_level_bottlenecks` in `src/domain/service/advanced_metrics_service.py`.

1. **Arbitrary Selection on Equal Values:**
   The function calculates rounded location SLA averages `loc_averages` (where all warehouses evaluate to `0.98`) and determines the worst location using `worst_loc, worst_sla = min(loc_averages.items(), key=lambda item: item[1])`. When all values in `loc_averages` are equal (`0.98`), Python's `min()` arbitrarily picks the first item in dictionary iteration (`Whse_A`).

2. **False Positive Bottleneck Summary:**
   The domain model generates a summary explicitly claiming `Whse_A` is the "critical SLA bottleneck" with 98.00% service level, despite the fleet average also being 98.00% and no warehouse performing worse than another.

3. **Floating Point Accumulation Imprecision:**
   Unrounded float accumulation over thousands of rows produces minute floating-point discrepancies (`0.9799999999996978` vs `0.9800000000003375`), which can mislead raw min/max evaluations prior to rounding.

As a result, the tool output fed into the LLM states `worst_location: "Whse_A"`, prompting the LLM to present `Whse_A` as having the worst service level, even though all warehouses operate at identical 98.00% SLA.

## Reproduction Script (MANDATORY)

```python
import pytest
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.domain.service.advanced_metrics_service import AdvancedMetricsService
from src.domain.service.basic_metrics_service import BasicMetricsService
from src.application.service.sales_metrics_service import SalesMetricsApplicationService


def test_service_level_bottlenecks_equal_sla_reproduction():
    """
    Automated Reproduction Test for SLA Bottlenecks when service levels are identical.
    Validates that when all locations present equal service levels (98.00%),
    the metric does not arbitrarily highlight one warehouse as a bottleneck.
    """
    adapter = DuckDbSalesAdapter(dataset_path="dataset/sales.csv")
    service = SalesMetricsApplicationService(
        sales_data_port=adapter,
        basic_metrics_service=BasicMetricsService(),
        advanced_metrics_service=AdvancedMetricsService(),
    )

    result = service.analyze_service_level_bottlenecks()

    # In dataset/sales.csv, all warehouses have an average SLA of 98.00%.
    # Currently, result.worst_location returns 'Whse_A' and summary claims Whse_A is a bottleneck.
    # Expected behavior when all SLAs are equal:
    # 1. worst_location should return "N/A" or "None" (or indicate no bottleneck).
    # 2. summary should state that all locations operate at equal service levels with no bottleneck.
    assert result.worst_location in ("N/A", "None", "TIE", "Nenhum"), (
        f"Expected no specific location as bottleneck when all SLAs are equal, got '{result.worst_location}'"
    )
    assert "critical sla bottleneck" not in result.summary.lower(), (
        f"Summary incorrectly reports a critical bottleneck: '{result.summary}'"
    )
```

## Correction Checklist (Atomic Tasks)

- [COMPLETED] Task 001 - [Test] Implement the reproduction script in `tests/integration/test_service_level_incident_b003.py` and confirm the failure (Red).
- [COMPLETED] Task 002 - [Logic] Fix `analyze_service_level_bottlenecks` in `src/domain/service/advanced_metrics_service.py` to check for uniform/tied SLA averages across locations, setting `worst_location` to `"N/A"` (or `"None"`) and generating a summary indicating that no location bottleneck exists when all SLAs are equal.
- [COMPLETED] Task 003 - [Security/Perf] Add unit tests in `tests/unit/test_advanced_metrics_service.py` verifying tied SLA handling, floating-point tolerance, and distinct location bottleneck calculations.
