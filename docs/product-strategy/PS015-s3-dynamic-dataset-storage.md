# Product Strategy: Zero-Copy Remote S3 Direct Querying for Big Data Scalability

## Strategic Context

The **Sales Data Analysis Agent** is scaling toward enterprise-grade data volumes, where sales datasets can scale to hundreds of millions or billions of records. 

In this scale regime, loading entire datasets into container RAM (in-memory tables) is not viable:

- **Memory Exhaustion (OOM):** High memory consumption leads to expensive pod provisioning and risks crashing containers.
- **Data Stale Window:** In-memory caching requires sync pipelines, cache invalidation, or pod restarts whenever the source data is updated in S3.
- **Compute-Storage Decoupling:** Modern data architectures require compute to remain completely stateless and query external storage directly on demand.

To achieve infinite dataset scalability, zero memory footprint, and instant data freshness, the platform strategy pivots to **Direct S3 Zero-Copy Analytical Querying**. DuckDB will query the remote CSV directly on AWS S3 (`s3://juliosilvacwb-private/sales.csv`) with pushdown predicates and streaming aggregates.

## Market & Competitor Analysis

The modern data lakehouse paradigm (Snowflake, AWS Athena, Trino, DuckDB) separates storage from compute:

- **Zero-Copy Remote Querying:** Modern OLAP engines stream byte-ranges from S3 on demand, filtering and aggregating data in streaming chunks without ever loading the full file into application memory.
- **Immediate Data Freshness:** External ETL pipelines (Spark, Glue, Airflow) can overwrite or append data in S3, and every subsequent query immediately reflects the latest data without application cache invalidation or pod restarts.
- **Cost Optimization:** Pods run with minimal, predictable memory footprint (e.g., 256MB-512MB RAM), drastically reducing cloud infrastructure costs even when querying multi-gigabyte or terabyte datasets.

## Ideation Results

### 1. Remote S3 Query Pushdown via DuckDB httpfs (Primary Strategy)

- **Problem Statement:** Storing billions of rows in container RAM causes OOM crashes and high memory costs.
- **Proposed Solution:** Configure DuckDB to use remote S3 extensions (`httpfs` / S3 credential provider) and point analytical views directly to the S3 bucket URI (`s3://juliosilvacwb-private/sales.csv`). DuckDB executes SQL queries directly over HTTP/S3 with streaming aggregation.
- **Inspiration/Evidence:** Native DuckDB S3 `httpfs` integration pattern.

### 2. Format Evolution Roadmap (CSV to Parquet / Partitioned Lake)

- **Problem Statement:** Scanning billions of rows in uncompressed CSV across HTTP adds network overhead and scan latency.
- **Proposed Solution:** While supporting CSV direct S3 queries initially, provide a strategic roadmap for external ETL pipelines to store data in columnar Parquet format on S3. DuckDB can then perform column projection and row-group pruning, downloading only relevant byte ranges.
- **Inspiration/Evidence:** Standard Data Lakehouse format best practice.

### 3. S3 Credential Provider & Secure Access

- **Problem Statement:** Containers require secure, environment-driven access to private S3 buckets.
- **Proposed Solution:** Use standard AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_SESSION_TOKEN`) or IAM Roles for Service Accounts (IRSA) configured via Kubernetes Secrets, transparently injected into DuckDB S3 session configuration.
- **Inspiration/Evidence:** 12-factor cloud security standards.

## Prioritization Matrix

| Idea | Business Value (1-5) | User Impact (1-5) | Strategic Alignment (1-5) | Effort (1-5, lower=better) | Risk (1-5, lower=better) | Weighted Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Remote S3 Query Pushdown (Direct Query)** | 5 | 5 | 5 | 4 | 4 | **23** |
| **S3 Credential Provider & Security** | 5 | 4 | 5 | 4 | 5 | **23** |
| Parquet Format Evolution Roadmap | 4 | 5 | 5 | 3 | 4 | **21** |

*Note: Effort and Risk are inverted for scoring (lower effort/risk = higher score).*

## Recommendations

### Top Recommendation: Direct S3 Analytical Execution

We fully adopt direct S3 querying without in-memory dataset loading:

1. **Direct S3 Query Execution:**
   - Configure `DuckDbSalesAdapter` to initialize DuckDB with `httpfs` / `aws` extensions.
   - Point queries or analytical views directly to the remote S3 URL (`s3://juliosilvacwb-private/sales.csv` or configured via `DATASET_S3_URI`).
   - Eliminate local CSV loading into RAM, keeping container memory usage constant and minimal.
2. **Instant Data Freshness:**
   - Queries always hit the current state of S3, enabling external ETL pipelines to update the dataset in real time without triggering container restarts or cache syncs.
3. **Resilience & Fallback:**
   - Support both local file path (for offline unit tests) and S3 remote URI (for staging/production).

- **Dependencies:**
  - AWS IAM credentials or S3 bucket read permissions configured in Kubernetes secrets / environment variables.
- **Validation Suggestions:**
  - Execute aggregation queries against `s3://juliosilvacwb-private/sales.csv` and measure RAM utilization (which must remain flat).
  - Update a record in S3 and verify the next query immediately reflects the updated value.

## Parking Lot

- **Columnar Parquet Lakehouse Transition:** As data grows past tens of millions of rows, evaluate converting the S3 CSV pipeline to Parquet for sub-second remote query execution via column-pruning range requests.

## Finalization

- **Commit Message:** `docs(strategy): update product strategy for zero-copy S3 direct querying (PS015)`
- **Handoff:** Ready for Product Owner (PO) refinement via `/po-agent create a PRD for direct S3 querying based on PS015-s3-dynamic-dataset-storage.md`.
