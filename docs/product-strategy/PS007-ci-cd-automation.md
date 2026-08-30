# Product Strategy: CI/CD Automation and Push-Based Deployment

## Strategic Context

Currently, the **Sales Data Analysis Agent** relies on manual execution of build and deployment commands. While acceptable for a local development or evaluation phase, manual deployments are intrinsically error-prone, non-auditable, and unscalable for a production environment.

As we prepare the application architecture for Enterprise Readiness (integrating distributed sessions and asymmetric authentication across a K3s cluster), we must establish an automated, reliable, and frictionless path to production. The strategic objective is to implement a robust Continuous Integration and Continuous Deployment (CI/CD) pipeline that validates code quality, packages the application, and seamlessly updates the production environment with zero downtime.

## Market & Competitor Analysis

In modern software delivery, automated CI/CD pipelines are mandatory.

- **Continuous Integration (CI):** Platforms like GitHub Actions are industry standards for running automated test suites (`pytest`) and building Docker images upon every code commit.
- **Continuous Deployment (CD):** For deploying to Kubernetes, the industry splits into two main patterns:
  - *Push-Based CD:* The CI server (e.g., GitHub Actions) authenticates with the cluster and "pushes" the update via imperative commands (e.g., `kubectl set image`).
  - *Pull-Based CD (GitOps):* An operator inside the cluster (e.g., ArgoCD) monitors Git and "pulls" the desired state.
- While GitOps is the gold standard for massive clusters, Push-Based CD is highly pragmatic, simpler to implement, and perfectly suitable for our current scale and infrastructure footprint.

## Ideation Results

**1. Idea Name: Push-Based CD via GitHub Actions**

- **Problem Statement:** Manual deployments are slow and risky.
- **Proposed Solution:** Implement a unified GitHub Actions workflow. On every push to `master`:
  1. Run automated unit and integration tests.
  2. Build and push the Docker image to Docker Hub with a unique version tag.
  3. Securely authenticate with the production K3s cluster using stored secrets.
  4. Execute a `kubectl set image` command to trigger a zero-downtime rolling update.
- **Inspiration/Evidence:** A highly pragmatic, industry-standard approach for lean engineering teams.

**2. Idea Name: Pull-Based GitOps (ArgoCD)**

- **Problem Statement:** Security and drift management in cluster deployments.
- **Proposed Solution:** Install ArgoCD inside the K3s cluster. Configure it to monitor the repository and automatically synchronize Kubernetes manifests when the image tag updates.
- **Inspiration/Evidence:** Enterprise Kubernetes deployment patterns.

**3. Idea Name: Shell Script Automation (Local Deployment)**

- **Problem Statement:** Need to automate commands without cloud dependencies.
- **Proposed Solution:** Write a `deploy.sh` script that runs tests, builds the image, and executes `kubectl` commands locally from the developer's machine.
- **Inspiration/Evidence:** Legacy deployment automation.

## Prioritization Matrix

| Idea | Business Value (1-5) | User Impact (1-5) | Strategic Alignment (1-5) | Effort (1-5, lower=better) | Risk (1-5, lower=better) | Weighted Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Push-Based CD via GitHub Actions** | 5 | 5 | 5 | 4 | 4 | **23** |
| Pull-Based GitOps (ArgoCD) | 5 | 5 | 4 | 1 | 2 | **17** |
| Shell Script Automation | 2 | 2 | 2 | 5 | 1 | **12** |

*Note: Effort and Risk are inverted for scoring (lower effort/risk = higher score).*

## Recommendations

**Top Recommendation: Implement Push-Based CD via GitHub Actions**

We strongly recommend adopting a Push-Based Continuous Deployment model managed entirely within GitHub Actions. This balances automation rigor with architectural simplicity, avoiding the steep learning curve and infrastructure overhead of full GitOps tools at this stage.

- **Tradeoff Analysis:** We consciously reject a full GitOps (ArgoCD) approach to maintain a lean infrastructure. The tradeoff is slightly less protection against manual "configuration drift" inside the cluster, which is an acceptable risk given our team size and current maturity phase.
- **Recommended Sequencing & Scope:**
  1. **Secrets Management:** Provision `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, and `KUBECONFIG` as GitHub Repository Secrets.
  2. **Pipeline Definition:** Create `.github/workflows/ci-cd.yml` defining three distinct jobs:
     - `test`: Executes `pytest`.
     - `build`: Depends on `test`. Builds and pushes the image.
     - `deploy`: Depends on `build`. Conditionally runs only on the `master` branch. Uses the `KUBECONFIG` secret to execute `kubectl set image deployment/sales-agent sales-agent=juliosilvacwb/sales-agent:${{ github.sha }}`.
  3. **Verification:** Ensure the Kubernetes deployment is configured with proper Readiness and Liveness probes to guarantee a safe, zero-downtime rolling update.

## Parking Lot

- **Pull-Based GitOps (ArgoCD):** An excellent capability to revisit if our infrastructure footprint grows to multiple clusters or if compliance requirements demand strict, auditable state synchronization.
- **Shell Script Automation:** Discarded as it violates the principle of centralized, auditable deployments.
