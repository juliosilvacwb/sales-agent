# TEST003-service-level-bottlenecks — Test Coverage Specification

> **Source Incident:** [B003-service-level-bottlenecks.md](../incidents/B003-service-level-bottlenecks.md)

## Coverage Overview

This specification details the test coverage requirement for resolving **Incident B003: SLA Bottlenecks False Positive**. The underlying domain service `AdvancedMetricsService.analyze_service_level_bottlenecks` was previously picking an arbitrary warehouse as a "critical SLA bottleneck" when all warehouses in the dataset had identical average service levels (98.00%).

The test suite validates:

1. End-to-end behavior on DuckDB analytical sales data.
2. Equal/Tied SLA handling across multiple locations.
3. Floating-point accumulation imprecision safety.
4. Edge cases (empty dataset, single warehouse).
5. Distinct SLA bottleneck identification regression prevention.

## Test Checklist

### Task 001 — Reproduction & Integration Test (added on 2026-08-28)

- [COMPLETED] [TEST003-01] [Integration] **`test_service_level_bottlenecks_equal_sla_reproduction`**
  - **Target:** `tests/integration/test_service_level_incident_b003.py` → `test_service_level_bottlenecks_equal_sla_reproduction()`
  - **Scenario:** Validates SLA bottleneck analysis when all warehouses in `dataset/sales.csv` have an average service level of 98.00%.
  - **Arrange:** Instantiate `DuckDbSalesAdapter` with `dataset/sales.csv` and initialize `SalesMetricsApplicationService`.
  - **Act:** Execute `service.analyze_service_level_bottlenecks()`.
  - **Assert:** Verify `worst_location` is `"N/A"` (not `'Whse_A'`) and `summary` does not contain `"critical SLA bottleneck"`.
  - **Priority:** P0

### Task 002 — Domain Logic & Equal SLA Detection (added on 2026-08-28)

- [COMPLETED] [TEST003-02] [Unit] **`test_analyze_service_level_bottlenecks_equal_sla`**
  - **Target:** `src/domain/service/advanced_metrics_service.py` → `analyze_service_level_bottlenecks()`
  - **Scenario:** Evaluates SLA calculation when synthetic input records across 3 warehouses (Whse_A, Whse_B, Whse_C) have equal SLA of 0.98.
  - **Arrange:** Construct sequence of `SaleRecord` instances for Whse_A, Whse_B, and Whse_C with `service_level=0.98`.
  - **Act:** Call `AdvancedMetricsService().analyze_service_level_bottlenecks(records)`.
  - **Assert:** Assert `worst_location == "N/A"`, `worst_service_level == 0.98`, `overall_average_service_level == 0.98`, and `summary` states `"No logistics SLA bottleneck identified"`.
  - **Priority:** P0

- [COMPLETED] [TEST003-03] [Unit] **`test_analyze_service_level_bottlenecks_empty_records`**
  - **Target:** `src/domain/service/advanced_metrics_service.py` → `analyze_service_level_bottlenecks()`
  - **Scenario:** Evaluates SLA bottleneck analysis when an empty dataset is provided.
  - **Arrange:** Set `records = []`.
  - **Act:** Call `AdvancedMetricsService().analyze_service_level_bottlenecks(records)`.
  - **Assert:** Assert `worst_location == "N/A"`, `worst_service_level == 0.0`, `overall_average_service_level == 0.0`, and `summary == "No records to analyze for SLA bottlenecks"`.
  - **Priority:** P1

- [COMPLETED] [TEST003-04] [Unit] **`test_analyze_service_level_bottlenecks_distinct_sla`**
  - **Target:** `src/domain/service/advanced_metrics_service.py` → `analyze_service_level_bottlenecks()`
  - **Scenario:** Regression guard confirming that a genuine bottleneck is correctly identified when locations have distinct SLAs.
  - **Arrange:** Construct `SaleRecord` instances where Whse_A has average SLA 0.985 and Whse_B has average SLA 0.825.
  - **Act:** Call `AdvancedMetricsService().analyze_service_level_bottlenecks(records)`.
  - **Assert:** Assert `worst_location == "Whse_B"`, `worst_service_level == 0.825`, and `summary` contains `"The critical SLA bottleneck is at location 'Whse_B'"`.
  - **Priority:** P0

### Task 003 — Security, Precision & Edge Cases (added on 2026-08-28)

- [COMPLETED] [TEST003-05] [Unit] **`test_analyze_service_level_bottlenecks_floating_imprecision`**
  - **Target:** `src/domain/service/advanced_metrics_service.py` → `analyze_service_level_bottlenecks()`
  - **Scenario:** Verifies that minute floating-point accumulation discrepancies (`0.9799999999996978` vs `0.9800000000003375`) do not trigger false positive bottleneck reports.
  - **Arrange:** Construct `SaleRecord` for Whse_A with `0.9799999999996978` and Whse_B with `0.9800000000003375`.
  - **Act:** Call `AdvancedMetricsService().analyze_service_level_bottlenecks(records)`.
  - **Assert:** Assert `worst_location == "N/A"`, `worst_service_level == 0.98`, and `summary` contains `"No logistics SLA bottleneck identified"`.
  - **Priority:** P0

- [COMPLETED] [TEST003-06] [Unit] **`test_analyze_service_level_bottlenecks_single_location`**
  - **Target:** `src/domain/service/advanced_metrics_service.py` → `analyze_service_level_bottlenecks()`
  - **Scenario:** Verifies behavior when dataset contains records for only one single warehouse.
  - **Arrange:** Construct `SaleRecord` instances belonging exclusively to `Whse_A` (e.g. SLA 0.95).
  - **Act:** Call `AdvancedMetricsService().analyze_service_level_bottlenecks(records)`.
  - **Assert:** Assert `worst_location == "N/A"` (since there are no other locations to compare against for a bottleneck), `overall_average_service_level == 0.95`.
  - **Priority:** P2
