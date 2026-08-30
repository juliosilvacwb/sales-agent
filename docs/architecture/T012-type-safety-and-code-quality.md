<!-- markdownlint-disable MD013 -->
# T012: Strict Type Safety and Code Quality

## PRD Reference

- **PRD:** [R012-type-safety-and-code-quality.md](../business-requirements/R012-type-safety-and-code-quality.md)

## Technical Goal

Elevate the Sales Data Analysis Agent codebase to enterprise-grade code quality by transitioning from dynamic typing to strict static typing with comprehensive linting. This initiative implements MyPy (in strict mode) to eliminate runtime `TypeError` and `NoneType` exceptions, and Ruff to ensure instantaneous, deterministic code formatting and import sorting. These tools will be centralized in `pyproject.toml` and enforced strictly via GitHub Actions CI/CD gates.

## Architecture Decisions (ADRs)

### ADR-01: MyPy Strict Mode over Pyright/Dynamic Typing

- **Decision:** Replace the partial `pyright` setup with `mypy` in strict mode (`--strict`). The configuration will disallow untyped definitions, enforce explicit optional types, and prohibit implicit `Any` returns.
- **Rationale:** MyPy's strict mode provides the highest guarantee against runtime null-pointer dereferences (e.g., accessing methods on an `Optional` without checking `is not None`). Given the LLM orchestration complexity and strict JSON payload validations required, rigorous type safety is mandatory to prevent silent failures in production.

### ADR-02: Ruff as the Unified Linter and Formatter

- **Decision:** Replace disparate legacy tools (Black, Flake8, Isort) with a single rust-based tool: **Ruff**.
- **Rationale:** Ruff consolidates all linting, formatting, and import sorting into a single binary that executes in milliseconds. This drastically improves CI pipeline velocity (sub-1 second execution) and local developer ergonomics, fulfilling NFRs for static analysis speed.

### ADR-03: Centralized Configuration in pyproject.toml

- **Decision:** All linter, formatter, and type-checker configurations will be declared exclusively in `pyproject.toml`. Legacy config files (`.flake8`, `setup.cfg`, `mypy.ini`) are strictly prohibited.
- **Rationale:** Ensures a single source of truth for repository standards.

## Security and Reliability

### Security Mitigations

- **Supply Chain Security:** `mypy` and `ruff` will be pinned to explicit versions in `requirements.txt` to prevent sudden CI breakages from upstream dependency updates.

### Reliability

- **Zero Runtime Type Regressions:** The CI gating prevents any untested or dynamically typed code from merging, dramatically reducing production incident rates related to data malformation.

## Technical Checklist (Atomic Tasks)

> **Note:** As a codebase-wide engineering standard refactor, the phases are structured chronologically: Foundation (Tooling Config), Iterative Code Refactoring (Domain → App → Adapters), and finally CI Enforcement.

### 🔵 Phase 1 — Tooling Foundation (Zero Code Changes)

#### Phase 1 tasks (all parallel-safe)

- [ ] Task 001 - [Config]: Update `requirements.txt` with development dependencies (Depends On: —)
- [ ] Task 002 - [Config]: Configure `[tool.mypy]` and `[tool.ruff]` in `pyproject.toml` (Depends On: —)

### 🟡 Phase 2 — Codebase Refactoring (Depends on Phase 1)

#### Phase 2 tasks (all parallel-safe)

- [ ] Task 003 - [Domain-Model]: Type hint and format Domain Layer (Depends On: Task 001, Task 002)
- [ ] Task 004 - [UseCase]: Type hint and format Application Layer (Depends On: Task 003)
- [ ] Task 005 - [Adapter-Web]: Type hint and format Adapter Layer (Depends On: Task 004)

### 🟢 Phase 3 — CI/CD Validation and Gating (Depends on Phase 2)

#### Phase 3 tasks (all parallel-safe)

- [ ] Task 006 - [Adapter-Infra]: Implement `lint-and-typecheck` quality gate in CI (Depends On: Task 005)

## Task Detailing (Summary Tasks)

### Task 001 - [Config]: Update requirements.txt with development dependencies

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 002
- **Objective:** Add static analysis tooling to the project dependencies.
- **Files/Path:** `requirements.txt`
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Append `mypy>=1.10.0` and `ruff>=0.5.0` to the file.
  - Append required type stubs (e.g., `types-redis`, `types-requests`) if applicable.

---

### Task 002 - [Config]: Configure pyproject.toml

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 001
- **Objective:** Establish the strict ruleset for typing, linting, and formatting.
- **Files/Path:** `pyproject.toml`
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Remove any `[tool.pyright]` configuration.
  - Add `[tool.mypy]` block with `strict = true`, `disallow_untyped_defs = true`, `no_implicit_optional = true`, and `warn_return_any = true`.
  - Add `[tool.ruff]` block enabling rules: `E`, `W`, `F`, `I` (Isort), `B` (Bugbear), `UP` (Pyupgrade). Set line-length to 100.
  - Add `[tool.ruff.format]` block enforcing double quotes.

---

### Task 003 - [Domain-Model]: Type hint and format Domain Layer

- **Phase:** 2
- **Depends On:** Task 001, Task 002
- **Parallel With:** —
- **Objective:** Ensure the core domain is strictly typed and perfectly formatted.
- **Files/Path:** `src/domain/`
- **Reuse:** Existing domain classes.
- **Technical Acceptance Criteria:**
  - Run `ruff check --fix src/domain/` and `ruff format src/domain/`.
  - Manually annotate all missing function arguments and return types.
  - Ensure `mypy src/domain/` passes with 0 errors.

---

### Task 004 - [UseCase]: Type hint and format Application Layer

- **Phase:** 2
- **Depends On:** Task 003
- **Parallel With:** —
- **Objective:** Ensure use cases and ports are strictly typed.
- **Files/Path:** `src/application/`
- **Reuse:** Existing interfaces and services.
- **Technical Acceptance Criteria:**
  - Run Ruff fixes and formatting on `src/application/`.
  - Explicitly type all dependency injection constructors and interface boundaries.
  - Ensure `mypy src/application/` passes with 0 errors.

---

### Task 005 - [Adapter-Web]: Type hint and format Adapter Layer

- **Phase:** 2
- **Depends On:** Task 004
- **Parallel With:** —
- **Objective:** Ensure all LLM, persistence, and external adapters are typed safely.
- **Files/Path:** `src/adapter/`
- **Reuse:** Existing adapter logic.
- **Technical Acceptance Criteria:**
  - Run Ruff fixes and formatting on `src/adapter/`.
  - Address missing third-party types using `Any` explicitly or configuring `[[tool.mypy.overrides]]` for untyped libraries (e.g., duckdb, langchain).
  - Explicitly handle `Optional` returns (e.g., checking `if user is not None:` before accessing attributes).
  - Ensure `mypy src/adapter/` passes with 0 errors.

---

### Task 006 - [Adapter-Infra]: Implement lint-and-typecheck quality gate in CI

- **Phase:** 3
- **Depends On:** Task 005
- **Parallel With:** —
- **Objective:** Block PRs that violate the strict formatting and typing standards.
- **Files/Path:** `.github/workflows/ci-cd.yml`
- **Reuse:** Existing CI workflow (T007).
- **Technical Acceptance Criteria:**
  - Add a dedicated job or step `Static Analysis and Linting`.
  - Execute `ruff check .`
  - Execute `ruff format --check .`
  - Execute `mypy src/`
  - Ensure the pipeline fails instantly if any of these commands exit with a non-zero status code.

## Verification Plan

### Automated Tests

- Execute `mypy src/` locally to assert global compliance.
- Execute `ruff check .` and `ruff format --check .` to guarantee codebase visual consistency.

### Manual Verification

- Intentionally remove a return type from a function in a local branch.
- Run `mypy src/` and observe the exact missing type error.
- Open a test Pull Request and verify GitHub Actions halts the deployment pipeline due to the static analysis failure.
