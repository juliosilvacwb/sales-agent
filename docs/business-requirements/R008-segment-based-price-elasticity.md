# PRD: Segment-Based Price Elasticity of Demand

## Summary

Origin: [PS008-segment-based-price-elasticity.md](file:///c:/Code/challenge_ai_engineer/docs/product-strategy/PS008-segment-based-price-elasticity.md), Recommendation: Top Recommendation (Implement Segment-Based Elasticity - Group by Product).

The Sales Data Analysis Agent currently provides a Price Elasticity Domain Tool (`calculate_price_elasticity`). However, the existing calculation aggregates prices and quantities across all heterogeneous items in the dataset into a single global average before computing the elasticity formula.

This global aggregation creates severe statistical distortion (Simpson's Paradox). Averaging premium high-ticket items with low-ticket accessories before measuring price sensitivity produces economically invalid coefficients, misleading business decision-makers.

This PRD specifies the transition to a mathematically sound, **Segment-Based Price Elasticity of Demand (PED)** model. The system will group transactions by homogeneous cohorts (primarily at the `product_id` level), computing baseline and promotional metrics independently for each product. The revised engine supports querying elasticity for specific products or analyzing cross-catalog elasticity distributions, providing rigorous economic insights.

## Functional Requirements

- **PRD01 (Product-Level Cohort Grouping):** The analytical engine must group sales transactions by product identifier (`product_id`) prior to calculating price and volume variations.
- **PRD02 (Isolated Baseline vs. Promotional Metrics):** For each product segment, the system must independently calculate:
  - Baseline metrics: average regular price (`non_promoted_avg_price`), average regular quantity (`non_promoted_avg_qty`), and count of regular sales records.
  - Promotional metrics: average promotional price (`promoted_avg_price`), average promotional quantity (`promoted_avg_qty`), and count of promotional sales records.
- **PRD03 (Deterministic PED Formula per Segment):** The system must compute Price Elasticity of Demand per segment using the standard economic formula:
  - `PED = (% Delta Quantity) / (% Delta Price)`
  - Where `% Delta Price = ((promoted_avg_price - non_promoted_avg_price) / non_promoted_avg_price) * 100`
  - Where `% Delta Quantity = ((promoted_avg_qty - non_promoted_avg_qty) / non_promoted_avg_qty) * 100`
- **PRD04 (Standard Economic Demand Classification):** Each evaluated segment must be classified deterministically:
  - `Elastic`: `|PED| > 1.0` (demand is highly sensitive to price changes).
  - `Inelastic`: `|PED| < 1.0` (demand is relatively insensitive to price changes).
  - `Unit Elastic`: `|PED| == 1.0`.
  - `Undefined / Inconclusive`: when baseline or promotional records are missing, or price delta is zero.
- **PRD05 (Targeted Single-Product Analysis):** The use case and domain tool must support an optional `product_id` filter (e.g., `calculate_price_elasticity(product_id="PROD_01")`) to compute and return the elasticity profile for a specific product.
- **PRD06 (Multi-Product Overview & Ranking):** When no specific `product_id` is supplied, the system must compute elasticities across all valid products, returning a structured summary ranking the most elastic (highest sensitivity) and most inelastic (lowest sensitivity) products.
- **PRD07 (Graceful Handling of Sparse Data):** If a product contains only baseline records or only promotional records, the system must mark that segment as `Inconclusive` with clear explanatory feedback, without halting the calculation for other valid segments.
- **PRD08 (Domain Tool Interface Update):** The LLM Domain Tool (`calculate_price_elasticity`) must be updated to accept `product_id: Optional[str] = None` with comprehensive docstrings explaining the tool parameters to the AI Agent.

## Non-Functional Requirements

- **Mathematical Accuracy & Integrity:** Eliminates aggregation bias and Simpson's Paradox by enforcing strict cohort isolation across all calculations.
- **Performance & Latency:** Grouped segment calculations across the dataset must execute in sub-50ms, utilizing optimized DuckDB aggregations or vectorized processing.
- **Maintainability & Clean Architecture:** Domain models (`ProductPriceElasticityResult`, `CatalogPriceElasticityOverview`) and calculation logic must reside in the domain layer (`AdvancedMetricsService`), decoupled from LLM tool definitions and database drivers.
- **LLM Token Optimization:** Responses returned to the AI agent must be serialized into concise, structured JSON payloads with executive summaries, avoiding excessive token consumption when analyzing large catalogs.

## Business Rules

- **BR01 (Cohort Isolation Rule):** Transactions belonging to different `product_id` values must never be averaged together into a shared baseline or promotional price.
- **BR02 (Dual-Cohort Sufficiency):** A valid segment elasticity calculation requires at least one regular transaction (`non_promoted_count > 0`) and at least one promotional transaction (`promoted_count > 0`) with non-zero average baseline price and quantity.
- **BR03 (Economic Classification Rules):**
  - If `% Delta Price == 0.0`, classification is `"Unitary / Zero price change"`.
  - If `|PED| > 1.0`, classification is `"Elastic (Quantity highly responsive to price change)"`.
  - If `|PED| < 1.0`, classification is `"Inelastic (Quantity less responsive to price change)"`.
  - If `|PED| == 1.0`, classification is `"Unit Elastic"`.
- **BR04 (Independent Error Isolation):** A data anomaly or missing cohort in one product must not invalidate or fail the calculation for other products in a multi-product query.

## Critical Data (Conceptual)

- **Segment Key:** `product_id` (unique alphanumeric product identifier).
- **Segment Cohort Metrics:**
  - Non-promoted transactions count, average unit price, and average volume.
  - Promoted transactions count, average unit price, and average volume.
- **Elasticity Output Metrics (per Segment):**
  - `product_id`: Identifier of the evaluated product.
  - `elasticity_coefficient`: Decimal PED value rounded to 2 decimal places.
  - `percentage_change_in_price`: Percentage change in average price.
  - `percentage_change_in_quantity`: Percentage change in average volume.
  - `demand_classification`: Standard economic category.
  - `summary`: Business-oriented textual interpretation.
- **Catalog Elasticity Overview:**
  - Total products evaluated.
  - Most elastic products list.
  - Most inelastic products list.
  - Inconclusive products count.

## User Flow

### Happy Path 1 (Specific Product Elasticity Inquiry)

1. The user asks: "Qual é a elasticidade-preço do produto PROD_01?".
2. The AI Agent invokes the tool: `calculate_price_elasticity(product_id="PROD_01")`.
3. The application executes the segment aggregation for `PROD_01`.
4. The system validates both baseline and promotional cohorts exist for `PROD_01`.
5. The system computes `% Delta Price = -15.0%` and `% Delta Quantity = +30.0%`, resulting in `PED = -2.00` (`Elastic`).
6. The tool returns the structured JSON payload to the agent.
7. The agent formulates a clear business answer explaining that `PROD_01` is highly elastic and that discounts drive significant sales volume growth.

### Happy Path 2 (Catalog-Wide Elasticity Ranking)

1. The user asks: "Quais são os produtos mais sensíveis a desconto no catálogo?".
2. The AI Agent invokes the tool: `calculate_price_elasticity()`.
3. The system groups the entire dataset by `product_id` and calculates individual elasticity coefficients for every product.
4. The system filters out inconclusive products and ranks the valid products by elasticity magnitude.
5. The tool returns a structured catalog overview highlighting the top elastic and inelastic products.
6. The agent synthesizes the results, identifying the top promotional candidates for sales growth.

### Exception Path 1 (Product Lacks Promotional History)

1. The user asks for elasticity of `PROD_99`.
2. The AI Agent invokes `calculate_price_elasticity(product_id="PROD_99")`.
3. The system finds transactions for `PROD_99`, but `promoted_count == 0`.
4. The system returns `demand_classification="Inconclusive"` and summary `"O produto PROD_99 não possui histórico de promoções registrado; impossível calcular elasticidade."`.
5. The agent explains to the user that historical promotion data is required to measure elasticity.

### Exception Path 2 (Product Not Found)

1. The user queries a non-existent product identifier: `PROD_UNKNOWN`.
2. The system finds zero records for `PROD_UNKNOWN`.
3. The system returns `demand_classification="Undefined"` with message `"Produto 'PROD_UNKNOWN' não encontrado no conjunto de dados."`.
4. The agent informs the user that the product does not exist in the dataset.

### Exception Path 3 (Zero Price Variation During Promotion)

1. A product was flagged as promoted in transactions, but the recorded price was identical to the baseline price (`% Delta Price == 0.0`).
2. The system prevents division-by-zero, setting `elasticity_coefficient = 0.0` and classification `"Unitary / Zero price change"`.
3. The tool returns a safe, explanatory message without raising runtime exceptions.

## Acceptance Criteria

| ID | Criterion | Validation Method |
| --- | --- | --- |
| AC01 | `AdvancedMetricsService` calculates price elasticity grouped by `product_id` instead of a global catalog average. | Unit test verifying that product cohorts are isolated and do not blend prices. |
| AC02 | Targeted query `calculate_price_elasticity(product_id="...")` returns isolated metrics and classification for the specified product. | Integration test verifying single-product parameter dispatching and result structure. |
| AC03 | Catalog query `calculate_price_elasticity()` returns ranked overview of valid segment elasticities across all products. | Unit test verifying catalog-wide grouping, ranking, and JSON serialization. |
| AC04 | Products with only baseline or only promotional records are flagged as `Inconclusive` without raising exceptions. | Parameterized test with sparse dataset asserting graceful fallback handling. |
| AC05 | Division-by-zero protection is enforced when `% Delta Price == 0.0`, returning `Undefined / Zero price change`. | Unit test with identical baseline and promotional prices. |
| AC06 | Domain tool signature in `domain_tools.py` exposes `product_id: Optional[str] = None` with updated LLM docstrings. | Tool schema inspection asserting parameter definition and tool description. |
| AC07 | End-to-end agent query correctly handles specific product elasticity questions and general elasticity overview questions. | Agent integration test evaluating prompt reasoning with the updated tool. |
