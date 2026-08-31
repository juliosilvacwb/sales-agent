<!-- markdownlint-disable MD013 -->
# T008: Segment-Based Price Elasticity of Demand

## PRD Reference

- **PRD:** [R008-segment-based-price-elasticity.md](../business-requirements/R008-segment-based-price-elasticity.md)
- **Test Coverage:** [TEST008-segment-based-price-elasticity.md](../tests/TEST008-segment-based-price-elasticity.md)
- **Security Audit:** [S008-segment-based-price-elasticity.md](../security/S008-segment-based-price-elasticity.md)

## Technical Goal

Transition the Price Elasticity of Demand (PED) calculation from a globally
aggregated model to a segment-based model grouped by `product_id`. This
eliminates Simpson's Paradox by isolating price and volume variations within
homogeneous product cohorts. The system must support both targeted single-product
elasticity queries and catalog-wide elasticity rankings.

## Architecture Decisions (ADRs)

### ADR-01: Domain Model Expansion for Multi-Product Results

- **Decision:** Introduce a new `CatalogPriceElasticityOverview` domain model
  to represent the ranked catalog-wide results, while updating the existing
  `PriceElasticityResult` to represent a single product's segment. The
  `AdvancedMetricsService` will return a `Union` of these two types depending
  on the query context.
- **Rationale:** The business requirement (PRD05, PRD06) demands two distinct
  return shapes: a targeted profile for a specific product and a macro-level
  ranking across all products. Returning a unified `Union` keeps the domain
  boundary explicit and typed.

### ADR-02: SQL Pushdown for Grouping (Adapter Layer)

- **Decision:** The grouping by `product_id` (`GROUP BY product_id`) will be
  pushed down to the `SalesDataPort` implementation (DuckDB adapter). The
  adapter will return a `List[PriceElasticityAggregation]` (one per product)
  rather than a single global aggregation.
- **Rationale:** Pushing the `GROUP BY` to the SQL engine is significantly
  faster (sub-50ms target) and more memory-efficient than returning all raw
  transactions to Python and grouping them in the domain service.

### ADR-03: Graceful Inconclusive Handling (Domain Service)

- **Decision:** Products lacking either a promotional or baseline cohort will be
  classified as `Inconclusive` and filtered out of the top/bottom rankings in
  the `CatalogPriceElasticityOverview`, rather than throwing exceptions.
- **Rationale:** Real-world sales data is sparse (PRD07). Halting a catalog-wide
  calculation because a single new product hasn't been promoted yet would make
  the tool fragile.

## Security and Reliability

### Security Mitigations

- **SQL Injection Prevention:** The `product_id` parameter injected into the
  SQL adapter must be treated as untrusted input. It must be passed using
  parameterized queries (e.g., `execute(query, [product_id])`), strictly
  avoiding string concatenation/f-strings in the SQL adapter.

### Performance

- **DuckDB Vectorization:** The adapter must leverage DuckDB's native aggregate
  functions (`AVG()`, `COUNT()`) combined with `GROUP BY product_id`. If a
  specific `product_id` is queried, the `WHERE` clause must be applied before
  aggregation to minimize the scanned dataset.

## Technical Checklist (Atomic Tasks)

### 🔵 Phase 1 — Domain Core (Zero framework dependencies)

#### Leaf nodes (fully parallel — no domain dependencies)

- [COMPLETED] Task 001 - [Domain-Model]: Update `PriceElasticityAggregation`
  (Depends On: —)
- [COMPLETED] Task 002 - [Domain-Model]: Update `PriceElasticityResult` (Depends On: —)
- [COMPLETED] Task 003 - [Domain-Model]: Create `CatalogPriceElasticityOverview`
  (Depends On: Task 002)

#### Domain service (depends on models above)

- [COMPLETED] Task 004 - [Domain-Service]: Update `calculate_price_elasticity`
  in `AdvancedMetricsService` (Depends On: Task 001, Task 003)

### 🟡 Phase 2 — Ports and Use Cases (Depends on Phase 1)

#### Phase 2 tasks (all parallel-safe)

- [COMPLETED] Task 005 - [Port-Out]: Update `SalesDataPort` interface
  (Depends On: Task 001)
- [COMPLETED] Task 006 - [Port-In]: Update `SalesAnalysisUseCase` interface
  (Depends On: Task 003, Task 004)
- [COMPLETED] Task 007 - [UseCase]: Update `SalesMetricsApplicationService` implementation
  (Depends On: Task 005, Task 006)

### 🟢 Phase 3 — Adapters (Depends on Phase 2)

#### Phase 3 tasks (all parallel-safe)

- [COMPLETED] Task 008 - [Adapter-Persistence]: Update `SalesDataDuckDbAdapter` query
  logic (Depends On: Task 005)
- [COMPLETED] Task 009 - [Adapter-Web]: Update LLM `domain_tools.py` signature
  and docstrings (Depends On: Task 006, Task 007)
- [COMPLETED] Task 010 - [Test-Integration]: E2E test for specific product and catalog
  overview (Depends On: Task 008, Task 009)

## Task Detailing (Summary Tasks)

### Task 001 - [Domain-Model]: Update PriceElasticityAggregation

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 002
- **Objective:** Add `product_id` to the existing aggregation model so it can
  represent a specific segment.
- **Files/Path:** `src/domain/model/aggregation_models.py`
- **Reuse:** Existing `PriceElasticityAggregation` class.
- **Technical Acceptance Criteria:**
  - Add `product_id: str` field to `PriceElasticityAggregation`.
  - Ensure zero framework dependencies.

---

### Task 002 - [Domain-Model]: Update PriceElasticityResult

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 001
- **Objective:** Add `product_id` to the result model.
- **Files/Path:** `src/domain/model/metric_result.py`
- **Reuse:** Existing `PriceElasticityResult` class.
- **Technical Acceptance Criteria:**
  - Add `product_id: Optional[str]` field (optional for backwards compatibility).
  - Ensure zero framework dependencies.

---

### Task 003 - [Domain-Model]: Create CatalogPriceElasticityOverview

- **Phase:** 1
- **Depends On:** Task 002
- **Parallel With:** —
- **Objective:** Create a new result model for the multi-product catalog ranking.
- **Files/Path:** `src/domain/model/metric_result.py`
- **Reuse:** Uses `PriceElasticityResult` as the type for list items.
- **Technical Acceptance Criteria:**
  - Create `CatalogPriceElasticityOverview` dataclass/Pydantic model.
  - Fields: `total_products_evaluated: int`,
    `inconclusive_products_count: int`,
    `most_elastic_products: List[PriceElasticityResult]`,
    `most_inelastic_products: List[PriceElasticityResult]`.
  - Ensure zero framework dependencies.

---

### Task 004 - [Domain-Service]: Update AdvancedMetricsService

- **Phase:** 1
- **Depends On:** Task 001, Task 003
- **Parallel With:** —
- **Objective:** Refactor elasticity math to process a list of product
  aggregations, apply business rules (BR02, BR03), and return either a single
  result or a ranked catalog overview.
- **Files/Path:** `src/domain/service/advanced_metrics_service.py`
- **Reuse:** Extract existing math logic into a helper method.
- **Technical Acceptance Criteria:**
  - Update signature: `calculate_price_elasticity(self, aggregations: List[PriceElasticityAggregation], target_product_id: Optional[str] = None) -> Union[PriceElasticityResult, CatalogPriceElasticityOverview]`.
  - If `target_product_id` is provided, find it in the list, compute,
    and return `PriceElasticityResult`.
  - If `target_product_id` is None, compute elasticity for all products.
  - Handle division by zero safely (BR03).
  - Rank valid products into `most_elastic` and `most_inelastic`.
  - Exclude `Inconclusive` products from the rankings.

---

### Task 005 - [Port-Out]: Update SalesDataPort interface

- **Phase:** 2
- **Depends On:** Task 001
- **Parallel With:** Task 006
- **Objective:** Update the database port interface to accept an optional
  product ID and return a list of aggregations.
- **Files/Path:** `src/application/port/outbound/sales_data_port.py`
- **Reuse:** Existing `aggregate_price_elasticity` method definition.
- **Technical Acceptance Criteria:**
  - Update signature: `aggregate_price_elasticity(self, product_id: Optional[str] = None) -> List[PriceElasticityAggregation]`.

---

### Task 006 - [Port-In]: Update SalesAnalysisUseCase interface

- **Phase:** 2
- **Depends On:** Task 003, Task 004
- **Parallel With:** Task 005
- **Objective:** Update the driving use case interface for elasticity.
- **Files/Path:** `src/application/port/inbound/sales_analysis_usecase.py`
- **Reuse:** Existing `calculate_price_elasticity` method definition.
- **Technical Acceptance Criteria:**
  - Update signature: `calculate_price_elasticity(self, product_id: Optional[str] = None) -> Union[PriceElasticityResult, CatalogPriceElasticityOverview]`.

---

### Task 007 - [UseCase]: Update SalesMetricsApplicationService

- **Phase:** 2
- **Depends On:** Task 005, Task 006
- **Parallel With:** —
- **Objective:** Implement the updated interface, passing the `product_id`
  to both the adapter and the domain service.
- **Files/Path:** `src/application/service/sales_metrics_service.py`
- **Reuse:** Existing `calculate_price_elasticity` implementation.
- **Technical Acceptance Criteria:**
  - Update signature to accept `product_id: Optional[str] = None`.
  - Fetch aggregations:
    `aggs = self._sales_data_port.aggregate_price_elasticity(product_id)`.
  - Pass to domain:
    `self._advanced_metrics.calculate_price_elasticity(aggs, product_id)`.

---

### Task 008 - [Adapter-Persistence]: Update SalesDataDuckDbAdapter query

- **Phase:** 3
- **Depends On:** Task 005
- **Parallel With:** Task 009
- **Objective:** Refactor the SQL query to group by `product_id` and apply
  a parameterized filter if `product_id` is specified.
- **Files/Path:** `src/adapter/outbound/persistence/duckdb_adapter.py`
- **Reuse:** Existing base query logic.
- **Technical Acceptance Criteria:**
  - Modify query to include `GROUP BY product_id`.
  - If `product_id` is provided, append `WHERE product_id = ?` to the base
    data extraction layer using parameterized inputs.
  - Map query results to a `List[PriceElasticityAggregation]`.
  - Ensure execution time remains performant.

---

### Task 009 - [Adapter-Web]: Update LLM domain_tools.py signature

- **Phase:** 3
- **Depends On:** Task 006, Task 007
- **Parallel With:** Task 008
- **Objective:** Expose the new `product_id` capability to the LLM Agent.
- **Files/Path:** `src/adapter/inbound/llm/domain_tools.py`
- **Reuse:** Existing `calculate_price_elasticity` tool definition.
- **Technical Acceptance Criteria:**
  - Update function signature:
    `def calculate_price_elasticity(product_id: Optional[str] = None) -> str:`.
  - Expand the docstring to explain that `product_id` should be provided
    for specific products, or omitted to receive a catalog-wide ranking.
  - Pass `product_id` to `sales_use_case.calculate_price_elasticity(product_id)`.

---

### Task 010 - [Test-Integration]: E2E test for product and catalog overview

- **Phase:** 3
- **Depends On:** Task 008, Task 009
- **Parallel With:** —
- **Objective:** Verify both happy paths and exception handling across the stack.
- **Files/Path:** `tests/integration/test_price_elasticity.py`
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Test querying a specific product with known data returns `Elastic` or
    `Inelastic` accurately.
  - Test querying without a product ID returns a ranking list.
  - Test querying a product with zero price variation returns `Undefined`.
  - Test querying an unknown product returns `Undefined`.

## Verification Plan

### Automated Tests

- Run unit tests for `AdvancedMetricsService` testing domain math,
  division-by-zero, and grouping logic independently of SQL.
- Run integration tests validating DuckDB grouping queries.
- Run the full test suite (`pytest`) to ensure no regressions.

### Manual Verification

- Initiate a chat with the Sales Agent.
- Ask: "Qual é a elasticidade do produto X?" and verify the tool is invoked
  with the parameter and returns a targeted answer.
- Ask: "Quais os produtos com maior elasticidade no catálogo?" and verify
  the tool is invoked without parameters and returns the ranking list.
