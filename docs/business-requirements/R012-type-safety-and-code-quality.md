# PRD: Strict Type Safety and Code Quality

## Summary

Origin: [PS012-type-safety-and-code-quality.md](file:///c:/Code/challenge_ai_engineer/docs/product-strategy/PS012-type-safety-and-code-quality.md), Recommendation: Top Recommendation (Implement MyPy Strict + Ruff).

The **Sales Data Analysis Agent** currently relies on Python's dynamic typing without mandatory static type verification or automated code formatting in the build pipeline. As the codebase scales with complex LLM orchestrations, distributed session handlers, and dynamic SQL query processing, dynamic typing introduces significant risks of runtime defects (`TypeError`, `AttributeError`, and unexpected `NoneType` dereferences) escaping into production.

Legacy Python tooling stacks (Flake8, Black, Isort) add excessive complexity and slow down continuous integration workflows.

This PRD specifies the implementation of a modern, enterprise-grade static analysis and code craftsmanship standard powered by **MyPy** (in `--strict` mode) and **Ruff** (for ultra-fast linting, formatting, and import sorting). Configured centrally in `pyproject.toml` and enforced as a blocking quality gate in GitHub Actions CI/CD, this standard guarantees zero preventable runtime typing errors, deterministic code styling, and architectural discipline across the entire codebase.

## Functional Requirements

- **PRD01 (Development Dependencies Integration):** The project must integrate `mypy` (latest stable) and `ruff` (latest stable) into the core development dependencies in `pyproject.toml`.
- **PRD02 (Centralized pyproject.toml Configuration):** All linter, formatter, and type-checker configurations must be consolidated in `pyproject.toml`:
  - `[tool.mypy]`: Enforce strict typing with flags `strict = true`, `disallow_untyped_defs = true`, `disallow_incomplete_defs = true`, `check_untyped_defs = true`, `no_implicit_optional = true`, and `warn_return_any = true`.
  - `[tool.ruff]`: Configure target Python version, line length (e.g., 88 or 100), and enable core rulesets: `E` (Pycodestyle errors), `W` (warnings), `F` (Pyflakes), `I` (Isort / import sorting), `B` (Flake8-bugbear), `UP` (Pyupgrade), and `C4` (Comprehensions).
  - `[tool.ruff.format]`: Enforce consistent quote styles, indentation, and docstring formatting.
- **PRD03 (Complete Source Typing Refactoring):** All modules, classes, methods, and functions across `src/` must be 100% typed with explicit argument types, return types, and explicit nullability annotations (`Optional[T]` or `T | None`).
- **PRD04 (Automated Codebase Formatting & Import Sorting):** The entire repository must be formatted using Ruff, ensuring consistent import ordering and formatting without manual style debates.
- **PRD05 (CI/CD Quality Gate Enforcement):** The GitHub Actions pipeline (`.github/workflows/ci-cd.yml`) must include a dedicated `lint-and-typecheck` job that runs `ruff check .`, `ruff format --check .`, and `mypy src/` as a prerequisite before running unit/integration tests or building containers.
- **PRD06 (Local Developer Ergonomics):** The repository must provide local execution instructions or standard task scripts (e.g., `ruff check --fix . && ruff format . && mypy src/`) allowing developers to validate code compliance locally before pushing commits.

## Non-Functional Requirements

- **Static Analysis Execution Speed:** Ruff linting and formatting verification in CI must execute in sub-1 second; MyPy strict type checking must complete in under 10 seconds.
- **Zero Runtime Type Regressions:** Eliminates all unhandled `TypeError`s, `AttributeError`s, and `NoneType` crashes in the production container environment.
- **Code Cleanliness & Maintainability:** Enforces uniform aesthetic standards and readable idioms across all layers (domain, application, and adapters).
- **Tooling Consolidation:** Eliminates fragmented legacy configuration files (`.flake8`, `.isort.cfg`, `setup.cfg`), establishing `pyproject.toml` as the single source of truth for tool settings.

## Business Rules

- **BR01 (Zero-Violation CI Gating):** Any Pull Request or commit with even a single MyPy type error or Ruff linting/formatting violation must be rejected by CI.
- **BR02 (Mandatory Type Annotations):** No function, method, or class attribute in `src/` may be merged without comprehensive type signatures (no implicit `Any`).
- **BR03 (Explicit Nullability Verification):** Values that may be `None` (such as optional query results or missing dictionary keys) must be typed as `Optional[T]` and guarded with explicit conditional checks (`if val is not None:`) before property or method access.
- **BR04 (Third-Party Library Typing Rules):** For third-party libraries lacking native type stubs, appropriate stub packages (e.g., `types-redis`, `types-requests`) or explicitly configured `[[tool.mypy.overrides]]` with `ignore_missing_imports = true` must be defined.

## Critical Data (Conceptual)

- **Static Analysis Ruleset:** Enabled rule codes (Flake8, Pyflakes, Isort, Bugbear, Pyupgrade) and exception overrides.
- **Type Checking Policy Flags:** Strict mode settings, untyped definition prohibitions, and missing stub handling.
- **CI Quality Metrics:** Count of typing errors, lint warnings, and unformatted files.

## User Flow

### Happy Path (Developer Submits Type-Safe Code)

1. A developer implements a new domain entity or use case in `src/`.
2. The developer adds complete type annotations to all parameters, returns, and variables.
3. The developer runs `ruff check --fix . && ruff format . && mypy src/` locally; all checks return 0 errors.
4. The developer opens a Pull Request on GitHub.
5. GitHub Actions executes the `lint-and-typecheck` job in ~5 seconds, reporting a clean pass.
6. The PR proceeds to unit and integration testing with confidence in type safety.

### Exception Path 1 (Missing Return Type Annotation)

1. A developer adds a new helper method without specifying `-> str` or `-> None`.
2. The developer (or CI runner) executes `mypy src/`.
3. MyPy reports: `error: Function is missing a return type annotation [no-untyped-def]`.
4. The CI build fails immediately, prompting the developer to add the missing annotation.

### Exception Path 2 (Potential NoneType Dereference)

1. A developer attempts to access a property on an `Optional[Product]` without checking if the object is `None`.
2. MyPy flags the violation: `error: Item "None" of "Optional[Product]" has no attribute "product_id"`.
3. The developer adds a defensive check `if product is not None:` and resolves the issue before code ever reaches staging.

### Exception Path 3 (Formatting or Unsorted Import Violation)

1. A developer merges code with unsorted imports or inconsistent indentation.
2. The CI pipeline runs `ruff check .` and `ruff format --check .`, flagging formatting discrepancies.
3. The developer runs `ruff format .` locally, which automatically reorganizes imports and fixes formatting in milliseconds, allowing the subsequent push to pass CI.

## Acceptance Criteria

| ID | Criterion | Validation Method |
| --- | --- | --- |
| AC01 | `mypy` and `ruff` are installed as development dependencies and configured in `pyproject.toml`. | Dependency check and validation of `[tool.mypy]` and `[tool.ruff]` tables in `pyproject.toml`. |
| AC02 | `mypy src/` runs in strict mode (`--strict`) and passes with 0 errors across the entire codebase. | Execution of `mypy src/` verifying a clean exit code (0). |
| AC03 | `ruff check .` and `ruff format --check .` pass with 0 errors and 0 formatting discrepancies. | Execution of Ruff linter and formatter assertions. |
| AC04 | All functions, methods, and classes in `src/` possess explicit parameter and return type hints. | MyPy strict check validation asserting `disallow_untyped_defs = true`. |
| AC05 | Potential `NoneType` dereferences are statically caught and guarded across all adapters and services. | Static analysis verification against optional return types. |
| AC06 | GitHub Actions CI (`.github/workflows/ci-cd.yml`) includes `lint-and-typecheck` gating job blocking PRs on errors. | Workflow file audit and dry-run execution on GitHub Actions. |
| AC07 | Linter and type checker execute in under 10 seconds total in the CI environment. | Duration measurement of quality gate step in CI runner. |
