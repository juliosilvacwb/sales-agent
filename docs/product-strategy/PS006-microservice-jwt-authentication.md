# Product Strategy: Asymmetric JWT Authentication Microservice

## Strategic Context

Currently, the **Sales Data Analysis Agent** operates without an authentication layer, exposing its analytical capabilities and underlying LLM infrastructure to unauthorized access. As we evolve the product toward Enterprise Readiness and transition to a distributed orchestration environment (K3s), securing the application is paramount.

Implementing a basic monolithic authentication pattern using symmetric keys (HS256) poses a severe security risk in distributed architectures: if the primary application container is compromised, the shared secret key is exposed, allowing attackers to forge administrative tokens.

To achieve a true **Zero Trust Architecture**, our strategic objective is to decouple authentication from the core business logic. We must establish a dedicated Authentication Microservice that alone holds the power to issue identity tokens via asymmetric cryptography (RS256), while the main Sales Agent application is restricted strictly to validating those tokens.

## Market & Competitor Analysis

In modern Cloud-Native and Microservices ecosystems, the **Identity Provider (IdP)** pattern is the industry standard.

- **Asymmetric Cryptography (RS256):** Standardized by OAuth2 and OIDC (OpenID Connect). An IdP generates a Private Key to sign JSON Web Tokens (JWTs) and distributes a Public Key for other services to mathematically verify the signature without being able to forge it.
- **Microservices Segregation:** Enterprise systems (like those using Auth0, Keycloak, or AWS Cognito) never bundle user management and token issuance within the same compute boundary as the core domain services.
- Adopting this distributed pattern not only fortifies our security posture but also future-proofs the application for eventual integration with corporate Single Sign-On (SSO) systems.

## Ideation Results

**1. Idea Name: Dedicated Auth Microservice with Asymmetric JWT (RS256)**

- **Problem Statement:** The system lacks secure, scalable authentication, and symmetric keys pose an unacceptable risk in distributed environments.
- **Proposed Solution:** Deploy a separate, lightweight container solely responsible for authentication. It will contain mocked user credentials via environment variables. It will generate a Private/Public RSA key pair, sign JWTs with the Private Key upon successful login, and expose the Public Key. The Sales Agent application will fetch the Public Key to validate incoming requests.
- **Inspiration/Evidence:** Industry-standard JWT architecture (OAuth2/JWKS pattern).

**2. Idea Name: Symmetric JWT within the Monolith (HS256)**

- **Problem Statement:** Need a quick way to lock down the application.
- **Proposed Solution:** Build the `/token` login route directly into the existing Sales Agent FastAPI app, using a single shared secret key (`JWT_SECRET_KEY`) for both creation and validation.
- **Inspiration/Evidence:** Common MVP (Minimum Viable Product) approach for monolithic apps.

**3. Idea Name: API Gateway Authentication Offloading**

- **Problem Statement:** We don't want to write custom authentication code.
- **Proposed Solution:** Use an advanced K3s Ingress Controller (like Kong or Traefik Enterprise) to handle JWT validation at the edge of the cluster before traffic ever reaches the application pods.
- **Inspiration/Evidence:** Modern API Gateway patterns.

## Prioritization Matrix

| Idea | Business Value (1-5) | User Impact (1-5) | Strategic Alignment (1-5) | Effort (1-5, lower=better) | Risk (1-5, lower=better) | Weighted Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dedicated Auth Microservice (RS256)** | 5 | 5 | 5 | 3 | 5 | **23** |
| API Gateway Authentication Offloading | 4 | 5 | 4 | 3 | 3 | **19** |
| Symmetric JWT within the Monolith | 3 | 5 | 2 | 4 | 1 | **15** |

*Note: Effort and Risk are inverted for scoring (lower effort/risk = higher score).*

## Recommendations

**Top Recommendation: Implement Dedicated Auth Microservice with Asymmetric JWT (RS256)**

We must strictly separate the responsibility of identity verification from analytical data processing by introducing a dedicated Authentication Microservice to our cluster.

- **Tradeoff Analysis:** We are choosing the slightly higher effort of managing a second codebase/container over the simplicity of a monolithic approach (HS256). This tradeoff is justified by the massive increase in enterprise-grade security (eliminating the risk of forged tokens if the analytical pod is compromised) and architectural purity.
- **Recommended Sequencing & Scope:**
  1. **Auth Service Construction:** Create a new, lightweight application (e.g., using FastAPI or plain Python) that implements a `POST /login` route. It should validate users against mocked environment variables (e.g., `TEST_USER`, `TEST_PASSWORD`).
  2. **Asymmetric Key Management:** The Auth Service must generate or load a Private/Public RSA key pair, signing tokens with the Private Key.
  3. **Sales Agent Refactoring:** The core Sales Agent must be updated with an authentication middleware (or FastAPI `Depends`) that uses the Auth Service's Public Key to validate the `Authorization: Bearer` header mathematically.
  4. **Infrastructure Updates (K3s):** Add the Auth Service to the deployment manifest. The cluster will now consist of: The Auth Service (replicas: 1), the Sales Agent (replicas: 2+), and Redis (replicas: 1).

## Parking Lot

- **API Gateway Authentication Offloading:** A highly effective pattern, but it introduces heavy dependency on specific Ingress Controller implementations (which may require paid enterprise versions). We will revisit this if cluster ingress complexity grows.
- **Symmetric JWT within the Monolith:** Discarded. Unsuitable for the distributed, stateless microservices architecture we established in PS004.
