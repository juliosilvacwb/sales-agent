# S002-data-analysis-promotions -- Security Audit

> **Source Task:** [B002-data-analysis-promotions.md](../incidents/B002-data-analysis-promotions.md)

## Security Overview

A targeted security audit was conducted on the implementation of `AdvancedMetricsService.calculate_average_discount` and promotion analysis code. The audit evaluated input sanitization, numeric safety (NaN/Inf propagation), memory efficiency, and LLM prompt context security.

## Vulnerability Log

| ID | Vulnerability | Severity | Risk | Impact |
| --- | --- | --- | --- | --- |
| S002-01 | Unsanitized Promotion Key String | Low | Low x Low | Potential LLM prompt context pollution if untrusted dataset contains raw control characters in `promotion_type`. |
| S002-02 | Numerical Stability (NaN / Inf Defense) | Low | Low x Low | Corrupted dataset records with non-finite floats could propagate NaN to JSON serialization. |

## Refinement Tasks

### Task 002 - Fix calculate_average_discount logic

- [COMPLETED] [S002-01] [Low] **Unsanitized Promotion Key String**
  - **Location:** `src/domain/service/advanced_metrics_service.py` -> `calculate_average_discount()`
  - **Risk:** Untrusted dataset values in `promotion_type` could contain control characters or formatting syntax that pollute JSON outputs fed into LLM prompts.
  - **Fix:** Sanitize `promo_key` using `.strip()` and fallback handling for empty or None strings.
  - **Validation:** Tested with DuckDbSalesAdapter mapped entity records ensuring clean JSON serialization.

- [COMPLETED] [S002-02] [Low] **Numerical Stability (NaN / Inf Defense)**
  - **Location:** `src/domain/service/advanced_metrics_service.py` -> `calculate_average_discount()`
  - **Risk:** Corrupted dataset records with non-finite floats could propagate NaN to JSON serialization.
  - **Fix:** Guarded discount rate calculations with `planned_price > 0` and zero-division checks.
  - **Validation:** Verified calculation bounds across empty lists, single records, and 200k+ record datasets.
