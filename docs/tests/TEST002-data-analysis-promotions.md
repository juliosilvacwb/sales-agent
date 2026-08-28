# TEST002-data-analysis-promotions -- Test Coverage Specification

> **Source Task:** [B002-data-analysis-promotions.md](../incidents/B002-data-analysis-promotions.md)

## Coverage Overview

This specification details test scenarios for validating the fix to `AdvancedMetricsService.calculate_average_discount`. It covers integration reproduction testing against DuckDB sales dataset and unit tests covering positive discount filtering, mixed price increases, and edge cases.

## Test Checklist

### Task 001 - Implement the reproduction script

- [COMPLETED] [TEST002-01] [Type: Integration] **test_data_analysis_promotions_reproduction**
  - **Target:** `tests/integration/test_data_analysis_incident_b002.py` -> `test_data_analysis_promotions_reproduction()`
  - **Scenario:** Validates end-to-end dataset reading and verifies that positive discount values and discount percentages are calculated instead of returning 0.0.
  - **Arrange:** Instantiate `DuckDbSalesAdapter` with `dataset/sales.csv` and `SalesMetricsApplicationService`.
  - **Act:** Call `service.calculate_average_discount()`.
  - **Assert:** Verify `total_discount_value > 0.0` and `overall_average_discount_percentage > 0.0`.
  - **Priority:** P0

### Task 002 - Fix calculate_average_discount logic

- [COMPLETED] [TEST002-02] [Type: Unit] **test_calculate_average_discount**
  - **Target:** `tests/unit/test_advanced_metrics_service.py` -> `test_calculate_average_discount()`
  - **Scenario:** Validate that average discount percentage and total discount value calculate positive discounts correctly across standard sample records.
  - **Arrange:** Setup `sample_advanced_sales_records` fixture containing items with 20% and 10% discounts.
  - **Act:** Call `service.calculate_average_discount(sample_records)`.
  - **Assert:** Verify `overall_average_discount_percentage == 15.0`, `total_discount_value == 6400.0`, and `discount_by_promotion["Promo_Flash"] == 20.0`.
  - **Priority:** P0

### Task 003 - Add unit tests for mixed price increases and edge cases

- [COMPLETED] [TEST002-03] [Type: Unit] **test_calculate_average_discount_mixed_price_increases**
  - **Target:** `tests/unit/test_advanced_metrics_service.py` -> `test_calculate_average_discount_mixed_price_increases()`
  - **Scenario:** Validate that records with price increases (actual_price > planned_price) do not reduce total discount value or dilute the average positive discount percentage.
  - **Arrange:** Construct SaleRecord list with 1 item discounted by 20% and 1 item with a 50% price increase.
  - **Act:** Call `service.calculate_average_discount(records)`.
  - **Assert:** Verify `total_discount_value == 2000.0`, `overall_average_discount_percentage == 20.0`, and `discount_by_promotion == {"Flash": 20.0}`.
  - **Priority:** P0
