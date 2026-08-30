# Product Strategy: Robust SQL Validation via AST Parsing

## Strategic Context

The **Sales Data Analysis Agent** features a powerful "Secured SQL Fallback Tool" to handle ad-hoc analytical queries that fall outside the deterministic Domain Tools. Currently, this tool relies on Regular Expressions (Regex) to block dangerous Data Manipulation Language (DML) and Data Definition Language (DDL) commands (e.g., `DROP`, `DELETE`, `UPDATE`).

While this Regex-based approach was a conscious architectural tradeoff to minimize external dependencies and maintain a lightweight footprint during initial phases, it introduces two significant operational risks as we scale to enterprise environments:

1. **False Positives:** A valid analytical query containing a restricted keyword as a string literal (e.g., `SELECT * FROM sales WHERE product_name = 'Drop Table'`) will be unjustly blocked.
2. **False Negatives:** Regex pattern matching is notoriously brittle against cleverly obfuscated SQL injections or obscure dialect-specific commands.

To guarantee enterprise-grade security without compromising the flexibility of ad-hoc analytics, we must evolve our SQL validation mechanism from semantic text-matching to structural code comprehension.

## Market & Competitor Analysis

In the modern Data Engineering and AI ecosystem, relying on Regex for SQL sanitization is considered a legacy or prototyping anti-pattern.

- **The AST Standard:** The industry standard for analyzing, transpiling, and securing SQL is **Abstract Syntax Tree (AST)** parsing.
- **Tools:** Libraries like `sqlglot` parse SQL strings into hierarchical node structures. This allows the system to definitively verify that the root node of the query is a `SELECT` statement, regardless of what string literals or aliases are nested within the query tree.
- Competitors offering secure Text-to-SQL products uniformly rely on AST parsing to ensure absolute deterministic safety before executing LLM-generated payloads against a database.

## Ideation Results

**1. Idea Name: AST Parsing with SQLGlot**

- **Problem Statement:** Regex validation causes false positives on string literals and provides brittle security against SQL injection.
- **Proposed Solution:** Introduce `sqlglot` to parse the LLM-generated SQL into an AST. Traverse the tree to guarantee the root operation is strictly a read operation (`SELECT` or `WITH`) and structurally reject any DDL/DML nodes.
- **Inspiration/Evidence:** Best practices in database security and modern Text-to-SQL architectures.

**2. Idea Name: Advanced Regex Expansion**

- **Problem Statement:** Current regex patterns are too simplistic.
- **Proposed Solution:** Maintain a zero-dependency architecture by writing highly complex, multi-line Regular Expressions that attempt to ignore keywords inside single quotes or comments.
- **Inspiration/Evidence:** Traditional low-dependency software development.

**3. Idea Name: LLM-based Safety Gateway (Self-Correction)**

- **Problem Statement:** Need to ensure queries are safe to execute.
- **Proposed Solution:** Before executing the query, send it to a secondary, cheaper LLM prompt (e.g., "Is this query purely a SELECT statement without malicious intent?").
- **Inspiration/Evidence:** Agentic validation patterns (LLM-as-a-judge).

## Prioritization Matrix

| Idea | Business Value (1-5) | User Impact (1-5) | Strategic Alignment (1-5) | Effort (1-5, lower=better) | Risk (1-5, lower=better) | Weighted Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **AST Parsing with SQLGlot** | 5 | 5 | 5 | 3 | 5 | **23** |
| Advanced Regex Expansion | 2 | 2 | 2 | 2 | 1 | **9** |
| LLM-based Safety Gateway | 3 | 3 | 3 | 3 | 2 | **14** |

*Note: Effort and Risk are inverted for scoring (lower effort/risk = higher score).*

## Recommendations

**Top Recommendation: Implement AST Parsing with SQLGlot**

We must deprecate the Regex-based validation in favor of AST structural parsing using `sqlglot`.

- **Tradeoff Analysis (Why we are opting for this):** We are consciously accepting the tradeoff of adding a heavy external dependency (`sqlglot` parses multiple SQL dialects and has a larger footprint) in exchange for absolute, mathematical certainty regarding query safety. The elimination of false positives significantly improves the user experience, while the elimination of false negatives ensures enterprise data integrity. The initial decision to use Regex optimized for a lightweight footprint; the new decision optimizes for enterprise security.
- **Recommended Sequencing & Scope:**
  1. Add `sqlglot` to `requirements.txt`.
  2. Refactor `src/adapter/inbound/llm/sql_fallback_tool.py` to remove `re` module usage.
  3. Implement `sqlglot.parse_one()` to evaluate the query's AST root node.
  4. Expand the unit test suite (`tests/unit/adapter/test_sql_fallback_tool.py`) to specifically test false-positive scenarios (e.g., restricted keywords inside string literals).

## Parking Lot

- **LLM-based Safety Gateway:** Discarded due to non-deterministic behavior, added latency, and increased token costs. Security must be deterministic, not probabilistic.
- **Advanced Regex Expansion:** Discarded. Parsing nested SQL structures with Regex is mathematically flawed (SQL is not a regular language) and leads to an unmaintainable codebase.
