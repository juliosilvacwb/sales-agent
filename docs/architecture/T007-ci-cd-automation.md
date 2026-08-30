# T007: CI/CD Automation and Push-Based Deployment

## PRD Reference

- **PRD:** [R007-ci-cd-automation.md](../business-requirements/R007-ci-cd-automation.md)
- **Product Strategy:** [PS007-ci-cd-automation.md](../product-strategy/PS007-ci-cd-automation.md)

## Technical Goal

Implement a fully automated, push-based CI/CD pipeline
using GitHub Actions that enforces a strict three-stage
delivery sequence (Test → Build & Push → Deploy) for the
Sales Data Analysis Agent. The pipeline runs the complete
`pytest` test suite as a quality gate, builds and publishes
immutable, commit-SHA-tagged Docker images to Docker Hub,
and executes zero-downtime rolling updates to the target
K3s production cluster via `kubectl set image`. Feature
branches are restricted to the test stage only; production
deployments are exclusively gated to the `master` branch
(Ref: R007, PRD01–PRD07, BR01–BR04).

## Architecture Decisions (ADRs)

### ADR-01: GitHub Actions as the CI/CD Platform

- **Decision:** Use GitHub Actions as the sole CI/CD
  pipeline platform.
- **Alternatives Evaluated:**
  - *GitLab CI*: Requires a separate GitLab instance or
    migration from GitHub. Adds operational overhead.
  - *Jenkins*: Self-hosted, requires infrastructure
    management, plugin maintenance, and security patching.
  - *CircleCI / TravisCI*: External SaaS with additional
    cost and credential management surface.
- **Trade-offs:** GitHub Actions is natively integrated
  with the existing GitHub repository, provides free
  CI/CD minutes for public repositories, supports
  encrypted secrets, Docker Buildx caching, and has
  first-class YAML workflow syntax. Zero additional
  infrastructure required.
- **Requirement Link:** PRD01, PRD02, PRD03, NFR04.

### ADR-02: Three-Job Sequential Pipeline Architecture

- **Decision:** Structure the workflow as three discrete,
  sequential jobs with explicit `needs` dependencies:

  1. `test` — Run `pytest` on Python 3.11.
  2. `build-and-push` — Build Docker image, tag with
     commit SHA + `latest`, push to Docker Hub.
     Depends on `test` passing.
  3. `deploy` — Execute `kubectl set image` rolling
     update to K3s. Depends on `build-and-push`
     completing. Branch-gated to `master` only.

- **Alternatives Evaluated:**
  - *Single-job pipeline*: Simpler but loses job-level
    isolation. A Docker build failure would pollute the
    test job's status. No parallel caching benefits.
  - *Reusable workflow calls*: Overengineered for the
    current three-step linear sequence.
- **Trade-offs:** Three separate jobs provide clear
  failure attribution, independent retry capability per
  stage, and explicit sequential gating (BR01). The
  overhead of job spin-up (~5s per job) is negligible
  against the 5-minute total budget (NFR01).
- **Requirement Link:** BR01 (Strict Gating), PRD04
  (Branch-Gated Deploy).

### ADR-03: Docker Buildx with GitHub Actions Cache

- **Decision:** Use Docker Buildx (`docker/build-push-action`)
  with `cache-from: type=gha` and `cache-to: type=gha` for
  layer caching across pipeline runs.
- **Rationale:** The existing
  [Dockerfile](file:///c:/Code/challenge_ai_engineer/Dockerfile)
  is structured with dependency installation
  (`requirements.txt`) before source code copy, enabling
  effective layer caching. GitHub Actions cache backend
  provides persistent cross-run caching without external
  registry configuration.
- **Trade-offs:** GitHub Actions cache has a 10GB limit
  per repository. Docker layer caches for a Python 3.11
  slim image typically consume ~500MB, well within limits.
- **Requirement Link:** NFR01 (5-minute execution target).

### ADR-04: Commit SHA Immutable Tagging

- **Decision:** Tag every production image with the Git
  commit SHA (`juliosilvacwb/sales-agent:${{ github.sha }}`)
  as the primary identifier, plus `latest` as a convenience
  tag. The K3s deployment always references the SHA tag.
- **Rationale:** SHA tags are cryptographically unique and
  immutable, enabling direct traceability from any running
  pod to its exact source code version (NFR05). The `latest`
  tag is pushed for developer convenience but NEVER used
  in production deployments.
- **Requirement Link:** BR02 (Immutable Tagging), NFR05
  (Auditability).

### ADR-05: Push-Based Deployment via kubectl

- **Decision:** Use imperative `kubectl set image` for
  rolling updates rather than GitOps pull-based tools
  (Argo CD, Flux).
- **Alternatives Evaluated:**
  - *Argo CD / Flux*: Pull-based GitOps controllers
    watching a Git manifest repository. Superior for
    multi-cluster enterprise deployments but introduces
    significant operational complexity (additional
    controller pods, Git manifest repos, reconciliation
    loops) disproportionate to the current single-cluster
    topology.
  - *Helm chart upgrade*: Adds templating complexity
    without clear benefit for the current static manifest
    structure.
- **Trade-offs:** Push-based `kubectl` is simpler,
  requires zero additional cluster components, and
  provides immediate feedback via `kubectl rollout status`.
  The trade-off is reduced drift detection (no
  reconciliation loop), acceptable for the current
  single-cluster, single-team deployment model.
- **Requirement Link:** PRD06 (Imperative Rollout),
  PRD07 (Failure Detection).

### ADR-06: K8s Deployment Strategy Hardening

- **Decision:** Update the existing
  [app-deployment.yaml](file:///c:/Code/challenge_ai_engineer/k8s/app-deployment.yaml)
  to include explicit `RollingUpdate` strategy with
  `maxSurge: 1` and `maxUnavailable: 0`, ensuring zero
  downtime during deployments. The existing
  `readinessProbe` and `livenessProbe` configurations are
  already present and correctly defined.
- **Rationale:** The current manifest lacks an explicit
  `strategy` block (defaults to `RollingUpdate` with
  `maxSurge: 25%`, `maxUnavailable: 25%`). Making
  `maxUnavailable: 0` explicit guarantees that K8s never
  terminates an existing pod before a new pod passes its
  readiness probe (BR04, NFR03).
- **Requirement Link:** NFR03 (Zero Downtime), BR04
  (Probed Traffic Readiness).

### ADR-07: No New Dependencies

- **Decision:** This specification introduces zero new
  Python dependencies. All changes are infrastructure
  artifacts (YAML workflow files, K8s manifests). The
  existing `requirements.txt`, `Dockerfile`, and source
  code remain unchanged.
- **Requirement Link:** Dependency Guardian principle.

## Security and Reliability

### Security Mitigations

- **Secret Protection (NFR02):** All credentials
  (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `KUBECONFIG`)
  are stored as GitHub Encrypted Secrets. GitHub Actions
  automatically masks secret values from all workflow logs.
  Secrets are NEVER printed, echoed, or committed to
  version control.
- **Branch Protection (BR03):** The `deploy` job contains
  an explicit `if: github.ref == 'refs/heads/master'`
  condition, preventing feature branch pushes from
  triggering production deployments. Combined with GitHub
  Branch Protection Rules (required status checks,
  required PR reviews), this forms a two-layer defense.
- **Minimal Permissions:** The workflow uses
  `permissions: contents: read` to limit the GitHub token
  scope to read-only repository access. Docker Hub
  authentication uses a scoped access token (not the
  account password).
- **No Credential Leakage in Logs:** The `KUBECONFIG`
  secret is written to a temporary file (`$HOME/.kube/config`)
  within the ephemeral runner and is automatically destroyed
  when the runner terminates.

### Reliability

- **Rollout Timeout Detection (PRD07):** The deploy step
  uses `kubectl rollout status --timeout=120s` to detect
  and fail on unhealthy deployments (CrashLoopBackOff,
  readiness probe failures, image pull errors) within a
  configurable timeout.
- **Idempotency (NFR04):** Re-running a workflow with the
  same commit SHA produces the identical Docker image tag
  and `kubectl set image` command. K8s recognizes the image
  is unchanged and performs a no-op rollout.
- **Zero Downtime (NFR03):** `maxUnavailable: 0` combined
  with HTTP readiness probes ensures existing pods continue
  serving traffic until new pods are fully healthy.

## Technical Checklist (Atomic Tasks)

> **Note:** This specification is infrastructure-focused
> (YAML workflow files and K8s manifests). The hexagonal
> 3-phase model (Domain → Ports → Adapters) does not
> directly apply since there is no domain code, ports, or
> application adapters involved. Tasks are organized in a
> linear dependency chain reflecting the CI/CD pipeline
> structure itself: Foundation → Pipeline Stages →
> K8s Hardening → Validation.

### 🔵 Phase 1 — Foundation (Scaffolding and prerequisites)

- [ ] Task 001 - [Scaffolding]: Create `.github/workflows/`
  directory structure (Depends On: —)
- [ ] Task 002 - [Adapter-Infra]: Harden K8s deployment
  manifest with explicit RollingUpdate strategy
  (Depends On: —)

### 🟡 Phase 2 — Pipeline Definition (Depends on Phase 1)

#### Phase 2 tasks (all parallel-safe)

- [ ] Task 003 - [Adapter-Infra]: Implement `test` job
  in CI/CD workflow (Depends On: Task 001)
- [ ] Task 004 - [Adapter-Infra]: Implement
  `build-and-push` job in CI/CD workflow
  (Depends On: Task 001)
- [ ] Task 005 - [Adapter-Infra]: Implement `deploy` job
  in CI/CD workflow (Depends On: Task 001)

### 🟢 Phase 3 — Assembly, Docs, and Validation (Depends on Phase 2)

#### Phase 3 tasks (all parallel-safe)

- [ ] Task 006 - [Adapter-Infra]: Assemble complete
  `ci-cd.yml` workflow file
  (Depends On: Task 003, Task 004, Task 005)
- [ ] Task 007 - [Config]: Document GitHub Secrets
  setup requirements (Depends On: —)
- [ ] Task 008 - [Test-Integration]: Validate workflow
  YAML syntax and dry-run (Depends On: Task 006)
- [ ] Task 009 - [Test-Integration]: End-to-end pipeline
  execution verification (Depends On: Task 006, Task 002)

## Task Detailing (Summary Tasks)

### Task 001 - [Scaffolding]: Create GitHub Actions directory

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 002
- **Objective:** Create the `.github/workflows/` directory
  structure required for GitHub Actions workflow discovery.
- **Files/Path:** `.github/workflows/` (new directory)
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Directory `.github/workflows/` exists in the
    repository root.
  - An empty placeholder or the initial `ci-cd.yml` file
    is created to validate GitHub detects the workflow.

---

### Task 002 - [Adapter-Infra]: Harden K8s deployment manifest

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 001
- **Objective:** Update the existing K8s deployment
  manifest to include explicit zero-downtime rolling
  update parameters.
- **Files/Path:**
  [app-deployment.yaml](file:///c:/Code/challenge_ai_engineer/k8s/app-deployment.yaml)
- **Reuse:** Existing manifest structure (2 replicas,
  liveness/readiness probes already defined).
- **Technical Acceptance Criteria:**
  - Add explicit `strategy` block:

    ```yaml
    strategy:
      type: RollingUpdate
      rollingUpdate:
        maxSurge: 1
        maxUnavailable: 0
    ```

  - `maxUnavailable: 0` ensures K8s never terminates an
    existing pod before the new pod passes readiness.
  - `maxSurge: 1` allows one extra pod during rollout
    (total 3 pods briefly with 2 replicas).
  - Change `imagePullPolicy` from `IfNotPresent` to
    `Always` to ensure SHA-tagged images are pulled on
    every deployment (required for immutable tag rollouts).
  - Existing `readinessProbe` (HTTP GET `/`, port 8000,
    initialDelay 5s, period 10s) is preserved.
  - Existing `livenessProbe` (HTTP GET `/`, port 8000,
    initialDelay 10s, period 15s) is preserved.
  - Validate with `kubectl apply --dry-run=client -f k8s/`
    to confirm YAML validity.

---

### Task 003 - [Adapter-Infra]: Implement test job

- **Phase:** 2
- **Depends On:** Task 001
- **Parallel With:** Task 004, Task 005
- **Objective:** Define the `test` job in the GitHub
  Actions workflow that runs the complete `pytest` suite
  as a quality gate.
- **Files/Path:** `.github/workflows/ci-cd.yml`
  (test job section)
- **Reuse:** Existing
  [pyproject.toml](file:///c:/Code/challenge_ai_engineer/pyproject.toml)
  pytest configuration (`testpaths = ["tests"]`,
  `pythonpath = ["."]`).
- **Technical Acceptance Criteria:**
  - Triggers on: `push` (all branches), `pull_request`
    (all branches).
  - Runner: `ubuntu-latest`.
  - Steps:
    1. `actions/checkout@v4` — Clone repository.
    2. `actions/setup-python@v5` — Python 3.11.
    3. Install dependencies:
       `pip install -r requirements.txt`.
    4. Run tests: `python -m pytest --tb=short -q`.
  - If any test fails, the job exits non-zero and halts
    the pipeline.
  - `PYTHONPATH` set to `.` (matching `pyproject.toml`).
  - Dummy `OPENAI_API_KEY`, `LLM_PROVIDER`, `MODEL_NAME`
    env vars for tests that load `.env` defaults.

---

### Task 004 - [Adapter-Infra]: Implement build-and-push job

- **Phase:** 2
- **Depends On:** Task 001
- **Parallel With:** Task 003, Task 005
- **Objective:** Define the `build-and-push` job that
  builds the Docker image with Buildx layer caching and
  pushes it to Docker Hub with commit SHA and `latest`
  tags.
- **Files/Path:** `.github/workflows/ci-cd.yml`
  (build-and-push job section)
- **Reuse:** Existing
  [Dockerfile](file:///c:/Code/challenge_ai_engineer/Dockerfile).
- **Technical Acceptance Criteria:**
  - `needs: test` — Only runs after test job succeeds.
  - Condition: `if: github.ref == 'refs/heads/master'`
    — Only builds on `master` branch pushes (BR03).
  - Steps:
    1. `actions/checkout@v4`.
    2. `docker/setup-buildx-action@v3` — Enable Buildx.
    3. `docker/login-action@v3` — Authenticate with
       Docker Hub using `DOCKERHUB_USERNAME` and
       `DOCKERHUB_TOKEN` secrets.
    4. `docker/build-push-action@v6` — Build and push
       with tags:
       `juliosilvacwb/sales-agent:${{ github.sha }}`,
       `juliosilvacwb/sales-agent:latest`.
    5. Cache config: `cache-from: type=gha`,
       `cache-to: type=gha,mode=max`.
  - Image is pushed only on `master`; feature branches
    skip this job entirely (AC05).
  - Docker context is the repository root (`.`).

---

### Task 005 - [Adapter-Infra]: Implement deploy job

- **Phase:** 2
- **Depends On:** Task 001
- **Parallel With:** Task 003, Task 004
- **Objective:** Define the `deploy` job that authenticates
  with the K3s cluster and performs a rolling update via
  `kubectl set image`.
- **Files/Path:** `.github/workflows/ci-cd.yml`
  (deploy job section)
- **Reuse:** Existing K8s manifest names
  (`sales-agent-deployment`, container name `sales-agent`).
- **Technical Acceptance Criteria:**
  - `needs: build-and-push` — Sequential dependency.
  - Condition: `if: github.ref == 'refs/heads/master'`
    — Deploy only from `master` (PRD04, BR03).
  - Steps:
    1. `actions/checkout@v4`.
    2. Configure kubectl:
       - Write `KUBECONFIG` secret to
         `$HOME/.kube/config`.
       - Verify cluster connectivity with
         `kubectl cluster-info`.
    3. Rolling update:
       `kubectl set image
       deployment/sales-agent-deployment
       sales-agent=juliosilvacwb/sales-agent:${{ github.sha }}`.
    4. Monitor rollout:
       `kubectl rollout status deployment/sales-agent-deployment --timeout=120s`.
  - Timeout of 120 seconds for rollout completion
    (PRD07). If pods fail readiness probes or crash,
    `rollout status` exits non-zero and fails the
    pipeline.
  - On timeout failure, the job logs indicate which
    pods are unhealthy without leaking secrets.

---

### Task 006 - [Adapter-Infra]: Assemble complete ci-cd.yml

- **Phase:** 3
- **Depends On:** Task 003, Task 004, Task 005
- **Parallel With:** Task 007
- **Objective:** Combine the three job definitions into
  the final, complete workflow file with proper top-level
  configuration.
- **Files/Path:**
  `.github/workflows/ci-cd.yml` (complete file)
- **Reuse:** Job sections from Tasks 003, 004, 005.
- **Technical Acceptance Criteria:**
  - Workflow `name: CI/CD Pipeline`.
  - Trigger `on`:

    ```yaml
    on:
      push:
        branches: ['**']
      pull_request:
        branches: ['**']
    ```

  - Top-level `permissions: contents: read` (minimal
    GitHub token scope).
  - Three jobs in correct `needs` chain:
    `test` → `build-and-push` → `deploy`.
  - `build-and-push` and `deploy` both gated with
    `if: github.ref == 'refs/heads/master'`.
  - File validates against
    `actionlint` or `yamllint` without errors.

---

### Task 007 - [Config]: Document GitHub Secrets setup

- **Phase:** 3
- **Depends On:** —
- **Parallel With:** Task 006, Task 008
- **Objective:** Document the required GitHub repository
  secrets and branch protection configuration.
- **Files/Path:**
  `.github/SECRETS_SETUP.md` (new documentation file)
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Lists all required secrets with descriptions:
    - `DOCKERHUB_USERNAME`: Docker Hub account username.
    - `DOCKERHUB_TOKEN`: Docker Hub access token (NOT
      the account password — scoped token recommended).
    - `KUBECONFIG`: Base64-encoded kubeconfig for the
      target K3s cluster.
  - Step-by-step instructions for creating each secret
    in GitHub repository settings.
  - Recommended GitHub Branch Protection Rules:
    (1) Require PR reviews before merging to `master`,
    (2) Require `test` status check to pass,
    (3) Disable force pushes to `master`.
  - Warning: NEVER commit secrets to version control.

---

### Task 008 - [Test-Integration]: Validate workflow YAML syntax

- **Phase:** 3
- **Depends On:** Task 006
- **Parallel With:** Task 007
- **Objective:** Validate that the complete workflow file
  is syntactically correct and follows GitHub Actions
  schema.
- **Files/Path:**
  `.github/workflows/ci-cd.yml` (validation only)
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - YAML syntax validation:
    `python -c "import yaml;
    yaml.safe_load(
    open('.github/workflows/ci-cd.yml'))"` succeeds.
  - Workflow file contains exactly three jobs:
    `test`, `build-and-push`, `deploy`.
  - `build-and-push.needs` equals `["test"]`.
  - `deploy.needs` equals `["build-and-push"]`.
  - Both `build-and-push` and `deploy` contain the
    `if: github.ref == 'refs/heads/master'` condition.
  - All secret references use
    `${{ secrets.SECRET_NAME }}` syntax.
  - No hardcoded credentials, tokens, or passwords.

---

### Task 009 - [Test-Integration]: End-to-end pipeline verification

- **Phase:** 3
- **Depends On:** Task 006, Task 002
- **Parallel With:** —
- **Objective:** Full end-to-end verification of the
  CI/CD pipeline on GitHub Actions and K8s manifest
  correctness.
- **Files/Path:** N/A (pipeline execution verification)
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - **AC01:** Workflow file exists at
    `.github/workflows/ci-cd.yml` and is detected by
    GitHub Actions upon push.
  - **AC02:** Push to a feature branch triggers the
    `test` job ONLY. `build-and-push` and `deploy` are
    skipped (AC05).
  - **AC03:** Push to `master` with passing tests triggers
    all three jobs sequentially: `test` → `build-and-push`
    → `deploy`.
  - **AC04:** Docker Hub shows new image with commit SHA
    tag after successful `build-and-push` (AC03).
  - **AC05:** `kubectl rollout status` completes
    successfully within 120s timeout (AC06).
  - **AC06:** K8s manifest dry-run validation:
    `kubectl apply --dry-run=client -f k8s/`
    returns no errors with the updated strategy block.
  - **AC07:** Intentionally failing test (temporary
    `assert False`) triggers pipeline halt at the test
    job, preventing build and deploy stages.
  - **Zero Downtime Validation:** HTTP health check
    (`GET /health`) returns 200 throughout the rolling
    update window (AC07 from PRD acceptance criteria).

## Verification Plan

### Automated Tests

```bash
# Validate YAML syntax of the workflow file
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci-cd.yml'))"

# Validate K8s manifests with dry-run
kubectl apply --dry-run=client -f k8s/

# Run the full project test suite locally
python -m pytest

# Verify Docker image builds locally
docker build -t sales-agent:test .
```

### Manual Verification

- Push a commit to a feature branch and verify that
  only the `test` job runs in GitHub Actions (no build
  or deploy).
- Merge a PR into `master` and verify the full pipeline
  executes: test → build → push → deploy.
- Check Docker Hub for the new commit SHA tag on the
  `juliosilvacwb/sales-agent` repository.
- Run `kubectl get pods -l app=sales-agent -o wide` and
  confirm all pods are running the new SHA-tagged image.
- During a rolling update, run continuous health checks
  (`watch curl -s http://localhost:8000/health`) to
  confirm zero downtime.
