# Product Strategy: Segment-Based Price Elasticity of Demand

## Strategic Context

The **Sales Data Analysis Agent** currently offers a "Price Elasticity" Domain Tool. However, the initial implementation calculates this metric by aggregating the prices and quantities of *all* products in the dataset to compute a global average before applying the elasticity formula.

This approach introduces severe statistical distortion (Simpson's Paradox). Averaging the price of a high-ticket item with a low-ticket item before calculating elasticity renders the final coefficient economically invalid. To maintain trust with enterprise users and provide mathematically sound business insights, we must transition from a "global average" model to a strictly **Segment-Based Elasticity Model**, calculating the Price Elasticity of Demand (PED) independently for homogeneous segments (e.g., at the `product_id` level).

## Market & Competitor Analysis

In the fields of Data Science and Retail Economics, Price Elasticity is never calculated across an entire heterogeneous catalog as a flat average.

- **Industry Standard:** Analytics platforms (like Tableau, Mixpanel, or custom Data Science models) group data by SKUs, Product Categories, or Customer Segments before performing comparative analysis.
- **Data Integrity:** A 5% discount on a premium product behaves entirely differently from a 50% discount on a cheap accessory. Treating them as a single entity masks the true demand curve.
- Our current analytical engine risks returning "garbage-in, garbage-out" (GIGO) insights if users ask broad questions without specifying a single product. Evolving this metric establishes our agent as a mathematically rigorous tool.

## Ideation Results

**1. Idea Name: Segment-Based Elasticity (Group by Product)**

- **Problem Statement:** Global average elasticity calculations produce statistically invalid coefficients.
- **Proposed Solution:** Refactor the calculation logic. The system must group sales records by `product_id` first. It will calculate the baseline vs. promotional metrics for *each* product independently, and then return a structured list of elasticities per product (or highlight the most/least elastic products).
- **Inspiration/Evidence:** Foundational microeconomics and standard SQL `GROUP BY` logic.

**2. Idea Name: Weighted Global Elasticity**

- **Problem Statement:** Users sometimes want to know the "overall store elasticity", even if mathematically complex.
- **Proposed Solution:** Calculate the elasticity per product, then calculate a global weighted average based on the total revenue volume of each product to provide a single macro-number.
- **Inspiration/Evidence:** Financial portfolio weighting practices.

**3. Idea Name: Predictive ML Elasticity Curve**

- **Problem Statement:** Simple linear PED formulas don't capture complex market behaviors.
- **Proposed Solution:** Introduce a Scikit-Learn integration to perform linear regression on price/quantity arrays over time to predict the true demand curve for each segment.
- **Inspiration/Evidence:** Advanced Data Science forecasting pipelines.

## Prioritization Matrix

| Idea | Business Value (1-5) | User Impact (1-5) | Strategic Alignment (1-5) | Effort (1-5, lower=better) | Risk (1-5, lower=better) | Weighted Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Segment-Based Elasticity (Group by Product)** | 5 | 5 | 5 | 3 | 4 | **22** |
| Weighted Global Elasticity | 3 | 3 | 3 | 2 | 3 | **14** |
| Predictive ML Elasticity Curve | 5 | 5 | 2 | 1 | 1 | **14** |

*Note: Effort and Risk are inverted for scoring (lower effort/risk = higher score).*

## Recommendations

**Top Recommendation: Implement Segment-Based Elasticity (Group by Product)**

We must refactor the elasticity metric to be strictly segment-controlled. This is the minimum baseline for mathematical validity in any analytical product.

- **Tradeoff Analysis:** We are rejecting the immediate addition of ML regression to keep the application architecture lean, focusing instead on fixing the deterministic mathematical logic. Returning data for multiple products might increase the token payload to the LLM, but this tradeoff is absolutely necessary to ensure analytical accuracy.
- **Recommended Sequencing & Scope:**
  1. Modify `AdvancedMetricsService.calculate_price_elasticity` to accept an optional `segment_by` parameter (defaulting to `product_id`).
  2. Implement grouping logic to separate the dataset into cohorts per product.
  3. Calculate the baseline price, promotional price, baseline quantity, and promotional quantity isolated within each cohort.
  4. Return a dictionary or list of `PriceElasticityResult` objects instead of a single scalar result.
  5. *Optional/Synergy:* If the OLAP Pushdown Aggregation (PS003) is implemented, this logic should simply be an advanced DuckDB SQL query with a `GROUP BY product_id`.

## Parking Lot

- **Predictive ML Elasticity Curve:** Highly desirable for a future "v2.0" Data Science capability, but represents significant scope creep for the current deterministic analytics engine.
- **Weighted Global Elasticity:** While nice to have for executive summaries, it can still mask individual product behaviors. Focus first on getting per-product elasticity correct.
