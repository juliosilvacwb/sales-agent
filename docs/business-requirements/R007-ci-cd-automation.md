# PRD: CI/CD Automation and Push-Based Deployment

## Summary

Origin: [PS007-ci-cd-automation.md](file:///c:/Code/challenge_ai_engineer/docs/product-strategy/PS007-ci-cd-automation.md), Recommendation: Top Recommendation (Implement Push-Based CD via GitHub Actions).

Currently, the **Sales Data Analysis Agent** relies on manual execution of build, test, and deployment commands. While functional during initial prototyping, manual operations are error-prone, lack auditability, and introduce deployment friction that hinders rapid iteration.

As the system evolves to an Enterprise-Ready distributed architecture across a K3s cluster, a standardized, automated software delivery pipeline is mandatory.

This PRD defines the functional and non-functional specifications for a Continuous Integration and Continuous Deployment (CI/CD) pipeline built with GitHub Actions. The pipeline enforces rigorous automated testing as a prerequisite for build, publishes immutable container images tagged by commit SHA to Docker Hub, and executes automated push-based zero-downtime rolling updates to the target K3s production cluster.

## Functional Requirements

- **PRD01 (Automated Test Execution & Quality Gate):** The pipeline must automatically execute the complete automated test suite (`pytest`) on every push and pull request to any branch. If any test fails, the workflow must halt immediately.
- **PRD02 (Container Image Build & Multi-Tagging):** Upon successful test execution on the default branch (`master`), the pipeline must build the application Docker image and assign deterministic tags: the specific commit SHA (`${{ github.sha }}`) and the `latest` tag.
- **PRD03 (Container Registry Publishing):** The pipeline must authenticate securely with Docker Hub using encrypted repository secrets (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`) and push the built images to the designated repository (`juliosilvacwb/sales-agent`).
- **PRD04 (Branch-Gated Deployment Trigger):** Deployment to the production cluster must be strictly gated to commits merged into the default branch (`master`), preventing feature branches from triggering unauthorized deployments.
- **PRD05 (Secure Kubernetes Cluster Authentication):** The deployment job must authenticate with the target K3s cluster using an encrypted repository secret (`KUBECONFIG`), establishing a secure communication channel without exposing cluster credentials in workflow logs.
- **PRD06 (Imperative Zero-Downtime Rollout):** The deployment step must trigger a rolling update imperatively using `kubectl set image deployment/sales-agent sales-agent=juliosilvacwb/sales-agent:${{ github.sha }}` and monitor progression via `kubectl rollout status deployment/sales-agent`.
- **PRD07 (Rollout Failure & Timeout Detection):** The pipeline must detect rollout failures (such as `CrashLoopBackOff`, readiness probe failures, or image pull errors) and fail the pipeline step if the deployment does not reach a healthy steady state within a configurable timeout.

## Non-Functional Requirements

- **Pipeline Execution Performance:** The entire end-to-end CI/CD workflow (test, build, push, deploy) should complete within 5 minutes, utilizing Docker layer caching (e.g., GitHub Actions cache backend) to optimize build durations.
- **Security & Secret Protection:** All sensitive credentials (`DOCKERHUB_TOKEN`, `KUBECONFIG`) must be stored in encrypted GitHub Secrets. Secrets must be masked from all build output logs and never committed to version control.
- **Zero Downtime Guarantee:** The application must maintain 100% availability during deployments. The K3s deployment manifest must define rolling update parameters (`maxUnavailable: 0` or reasonable surge constraints) alongside HTTP health probes (`livenessProbe`, `readinessProbe`) to ensure traffic is only routed to healthy pods.
- **Idempotency & Reproducibility:** Pipeline steps must be deterministic and idempotent. Re-running a failed workflow with identical commit inputs must produce the identical artifact and deployment state.
- **Auditability & Traceability:** Every running pod in the cluster must be easily correlated to its exact source code version through its commit SHA container tag.

## Business Rules

- **BR01 (Strict Gating Sequence):** The pipeline execution order is strictly sequential: Test -> Build & Push -> Deploy. A failure at any stage immediately prevents downstream stages from executing.
- **BR02 (Immutable Tagging Policy):** Deployments must always reference the specific, immutable commit SHA tag (`:${{ github.sha }}`) rather than mutable tags like `:latest`, ensuring auditability and reproducible rollback targets.
- **BR03 (Protected Branch Enforcement):** Deployments to production must only originate from the `master` branch. Pull requests and feature branches execute the test stage only.
- **BR04 (Probed Traffic Readiness):** The Kubernetes cluster must not route traffic to newly spawned pods until their readiness probes succeed. Existing pods must not be terminated until new pods are fully operational.

## Critical Data (Conceptual)

- **Git Commit Metadata:** Commit SHA, branch name, commit message, author, and timestamp.
- **Registry Credentials:** Docker Hub username and access token.
- **Cluster Access Configuration:** Base64-encoded Kubeconfig credentials and API server endpoint.
- **Container Image Identifier:** Image namespace (`juliosilvacwb/sales-agent`), SHA tag, and image digest.
- **Deployment Status Metrics:** Desired replicas, updated replicas, available replicas, and rollout duration.

## User Flow

### Happy Path (Continuous Integration & Continuous Deployment)

1. A developer merges a pull request into the `master` branch.
2. GitHub Actions detects the push event and triggers `.github/workflows/ci-cd.yml`.
3. **Job 1 (Test):** Sets up Python, installs dependencies, and runs `pytest`. All test cases pass.
4. **Job 2 (Build & Push):** Authenticates with Docker Hub, builds the container image with Docker Buildx, and pushes `juliosilvacwb/sales-agent:${{ github.sha }}` and `juliosilvacwb/sales-agent:latest`.
5. **Job 3 (Deploy):** Configures `kubectl` using the `KUBECONFIG` secret.
6. The deploy job executes `kubectl set image deployment/sales-agent sales-agent=juliosilvacwb/sales-agent:${{ github.sha }}`.
7. K3s performs a zero-downtime rolling update, verifying readiness probes before terminating old replicas.
8. `kubectl rollout status` confirms successful rollout, and the GitHub Actions workflow marks the run as successful.

### Exception Path 1 (Test Suite Failure in CI Gate)

1. A push is made with code that breaks an existing unit or integration test.
2. **Job 1 (Test):** `pytest` reports one or more failed assertions and exits with a non-zero status code.
3. GitHub Actions marks Job 1 as failed and aborts the workflow.
4. Jobs 2 (Build) and 3 (Deploy) are skipped.
5. No Docker image is pushed, and the cluster remains completely unaffected.

### Exception Path 2 (Docker Registry Authentication / Push Failure)

1. Tests pass successfully, but Docker Hub credentials are invalid or registry is unreachable.
2. **Job 2 (Build & Push):** Docker push fails with authentication or network timeout error.
3. Job 2 halts with error; Job 3 (Deploy) is skipped.
4. The deployment is halted, and notifications alert the team of the registry issue.

### Exception Path 3 (Cluster Authentication or Connectivity Failure)

1. Image build and push succeed, but the K3s cluster endpoint is unreachable or `KUBECONFIG` certificate has expired.
2. **Job 3 (Deploy):** `kubectl` commands fail with connection timeout or unauthorized error.
3. The deploy step fails and logs an error without leaking credentials.
4. The previously running stable application version continues serving traffic in the cluster.

### Exception Path 4 (Unhealthy Deployment / Rollout Timeout)

1. The new image contains a startup bug causing pods to crash (`CrashLoopBackOff`) or fail readiness probes.
2. K3s keeps existing healthy replicas running while withholding traffic from the failing new pod.
3. `kubectl rollout status` waits for healthy pods until reaching the configured timeout, then exits with an error code.
4. Job 3 marks the pipeline run as failed, alerting maintainers to investigate the failing pod logs while the live application remains functional on previous pods.

## Acceptance Criteria

| ID | Criterion | Validation Method |
| --- | --- | --- |
| AC01 | GitHub Actions workflow file (`.github/workflows/ci-cd.yml`) is defined and syntactically valid. | Workflow linting and dry-run execution on GitHub Actions. |
| AC02 | Automated test stage executes `pytest` across all project tests and halts pipeline upon any failure. | CI test validation with passing and intentionally failing test cases. |
| AC03 | Successful master build produces Docker images tagged with both commit SHA (`${{ github.sha }}`) and `latest`. | Verification of published image tags in Docker Hub repository. |
| AC04 | Pipeline uses encrypted secrets (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `KUBECONFIG`) with zero plaintext leaks in logs. | Workflow execution log audit verifying proper secret masking. |
| AC05 | Feature branch pushes run test verification only, without triggering image push or deployment. | Push to non-master branch asserting deploy job exclusion. |
| AC06 | Deploy stage executes `kubectl set image` with commit SHA tag and verifies rollout completion. | Deployment execution log inspection and cluster status check. |
| AC07 | Zero downtime is achieved during rolling update while serving simulated concurrent requests. | HTTP synthetic load testing during rolling deployment execution. |
