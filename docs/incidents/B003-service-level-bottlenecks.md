# Incident Summary

- **Test Coverage:** [TEST003-service-level-bottlenecks.md](../tests/TEST003-service-level-bottlenecks.md)
- **Security Audit:** [S003-service-level-bottlenecks.md](../security/S003-service-level-bottlenecks.md)

The AI assistant hallucinates a false positive SLA bottleneck for `Whse_A` when asked which location presents the worst logistic service level. Although all locations in the dataset (Whse_A, Whse_J, Whse_C, Whse_S) have identical average service levels (98.00%), the system identifies `Whse_A` as the "critical SLA bottleneck", causing contradictions when challenged by the user.

## Technical Analysis of Root Cause

The issue was located in `AdvancedMetricsService.analyze_service_level_bottlenecks` in `src/domain/service/advanced_metrics_service.py`.

1. **Arbitrary Selection on Equal Values:**
   The function calculates rounded location SLA averages `loc_averages` (where all warehouses evaluate to `0.98`) and previously determined the worst location using `worst_loc, worst_sla = min(loc_averages.items(), key=lambda item: item[1])`. When all values in `loc_averages` were equal (`0.98`), Python's `min()` arbitrarily picked the first item in dictionary iteration (`Whse_A`).

2. **Floating-Point Imprecision vs. Exact Equality (`min_sla == max_sla`):**
   Using a floating-point delta check such as `abs(max_sla - min_sla) < 1e-4` proved prone to edge-case errors due to IEEE-754 float representation (e.g. `0.9800 - 0.9799` evaluating to `0.00009999999999998899 < 0.0001`). This caused legitimate small differences (such as `Whse_A` dropping to 97.99% while others stayed at 98.00%) to be incorrectly treated as equal ties, projecting `min_sla` (97.99%) onto all warehouses in the summary string.

3. **Definitive Fix:**
   The condition was refined to compare exact equality on rounded 4-decimal averages:

   ```python
   if min_sla == max_sla:
       summary = (
           f"All locations present an equal average service level of {min_sla * 100:.2f}% "
           f"(overall fleet average: {overall_avg * 100:.2f}%). No logistics SLA bottleneck identified."
       )
       return ServiceLevelBottleneckResult(
           worst_location="N/A",
           worst_service_level=min_sla,
           overall_average_service_level=overall_avg,
           location_averages=loc_averages,
           summary=summary,
       )
   ```

   When averages differ (e.g., `0.9799` vs `0.9800`), `min_sla == max_sla` evaluates to `False`, allowing the system to accurately identify `worst_location="Whse_A"` with `worst_service_level=0.9799`.

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
