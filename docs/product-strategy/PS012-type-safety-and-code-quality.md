# Product Strategy: Strict Type Safety & Code Quality

## Strategic Context

Currently, the **Sales Data Analysis Agent** relies on Python's native dynamic typing. While the codebase uses type hints (e.g., `-> str`), these are not strictly enforced during the build process. Relying on dynamic typing without rigorous static analysis introduces a high risk of runtime exceptions (`AttributeError`, `TypeError`) slipping into production, especially as the application grows in complexity with LLM orchestrations and dynamic SQL executions.

To achieve Enterprise Readiness and guarantee zero preventable runtime bugs, the engineering standard must evolve. The strategic objective is to enforce strict **Type Safety** and unified **Code Formatting/Linting** acting as a highly restrictive gate in our CI/CD pipeline, ensuring that poor-quality or unsafely typed code never merges into the main branch.

## Market & Competitor Analysis

The Python ecosystem has rapidly matured to adopt "shift-left" quality paradigms:

- **Type Safety (MyPy):** Created by Dropbox and the Python core team, MyPy is the industry standard for static type checking. When run in `--strict` mode, it forces developers to handle every edge case (e.g., `Optional` returns, explicit casting), transforming Python into a mathematically safer language akin to TypeScript or Go.
- **Code Linting/Formatting (Ruff):** Historically, teams used a bloated stack of tools (Flake8, Black, Isort, Bandit). The modern industry standard is **Ruff**, an extraordinarily fast linter and formatter written in Rust that replaces the entire legacy stack, reducing CI execution times from minutes to milliseconds.

Competitors and top-tier engineering teams uniformly utilize this combination (MyPy + Ruff) to guarantee code cleanliness and type safety before any code reaches a production environment.

## Ideation Results

**1. Idea Name: MyPy Strict + Ruff in CI/CD Integration**

- **Problem Statement:** Lack of strict static analysis allows formatting inconsistencies and runtime type errors to reach production.
- **Proposed Solution:** Introduce `mypy` and `ruff` as core development dependencies. Configure `pyproject.toml` to enforce strict type checking (`strict = true`). Integrate these tools into the GitHub Actions CI pipeline to block any Pull Request that violates type safety or formatting standards.
- **Inspiration/Evidence:** The modern Python enterprise standard (replacing legacy Flake8/Black stacks).

**2. Idea Name: Minimal Pyright (Status Quo)**

- **Problem Statement:** Adopting strict type checking requires refactoring existing code.
- **Proposed Solution:** Keep the current basic `[tool.pyright]` configuration, which acts merely as an IDE helper without CI/CD enforcement.
- **Inspiration/Evidence:** Prototyping and MVP development phases.

**3. Idea Name: Pyre / Pytype**

- **Problem Statement:** Need advanced type inference.
- **Proposed Solution:** Adopt alternative type checkers built by Meta (Pyre) or Google (Pytype) instead of MyPy.
- **Inspiration/Evidence:** Niche use-cases in massive monorepos.

## Prioritization Matrix

| Idea | Business Value (1-5) | User Impact (1-5) | Strategic Alignment (1-5) | Effort (1-5, lower=better) | Risk (1-5, lower=better) | Weighted Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **MyPy Strict + Ruff** | 5 | 4 | 5 | 3 | 4 | **21** |
| Minimal Pyright (Status Quo) | 1 | 2 | 1 | 5 | 1 | **10** |
| Pyre / Pytype | 4 | 4 | 4 | 2 | 2 | **16** |

*Note: Effort and Risk are inverted for scoring (lower effort/risk = higher score).*

## Recommendations

**Top Recommendation: Implement MyPy Strict + Ruff**

We must immediately transition our code quality standards by adopting the `mypy` + `ruff` stack. This forces architectural discipline and proves a high level of engineering maturity.

- **Tradeoff Analysis:** Enabling MyPy in `--strict` mode will initially "break" the build and require developer effort to refactor existing code (adding missing type annotations, handling `None` returns explicitly). We accept this upfront friction because the long-term compounding benefits of zero `TypeError` production crashes vastly outweigh the initial implementation cost.
- **Recommended Sequencing & Scope:**
  1. Add `mypy` and `ruff` to the development requirements.
  2. Update `pyproject.toml` with explicit configurations:
     - `[tool.mypy]`: Set `strict = true`, `disallow_untyped_defs = true`, etc.
     - `[tool.ruff]`: Configure line length (e.g., 88) and enable standard rulesets (E, F, I for import sorting).
  3. Execute `ruff check --fix .` and `ruff format .` across the repository to auto-fix formatting.
  4. Execute `mypy src/` and manually resolve all typing violations.
  5. Add a `Code Quality` job to the `.github/workflows/ci.yml` pipeline that executes these tools prior to running the test suite.

## Parking Lot

- **Pyre / Pytype:** Discarded. MyPy has broader community support and integration with major frameworks like Pydantic and FastAPI.
- **Minimal Pyright:** Deprecated as a CI strategy. We must evolve beyond IDE-only hints.
