# PRD: Asymmetric JWT Authentication Microservice

## Summary

Origin: [PS006-microservice-jwt-authentication.md](file:///c:/Code/challenge_ai_engineer/docs/product-strategy/PS006-microservice-jwt-authentication.md), Recommendation: Top Recommendation (Implement Dedicated Auth Microservice with Asymmetric JWT RS256).

The Sales Data Analysis Agent currently operates without an authentication and authorization layer, exposing its analytical endpoints and underlying LLM infrastructure to unauthenticated access. As the product transitions to an enterprise-ready distributed cluster (K3s/Kubernetes), establishing a secure identity boundary is critical.

Monolithic authentication architectures that rely on symmetric shared keys (`HS256`) introduce severe security vulnerabilities in distributed systems: compromising an analytical worker pod exposes the shared secret, enabling attackers to forge administrative tokens across the entire cluster.

This PRD defines the requirements for a Zero Trust, microservice-based authentication architecture. A lightweight, dedicated **Authentication Microservice** acts as the sole identity provider responsible for verifying credentials and issuing JSON Web Tokens (JWT) signed with an asymmetric Private Key (`RS256`). The core **Sales Data Analysis Agent** operates strictly as a token consumer, verifying incoming signatures mathematically using the corresponding Public Key without ever possessing or handling the private signing key.

## Functional Requirements

- **PRD01 (Dedicated Authentication Microservice):** The system must provide a standalone, lightweight Authentication Microservice decoupled from the core analytical compute container.
- **PRD02 (User Login & Token Issuance):** The Auth Microservice must expose a login endpoint (`POST /auth/login`) that validates client credentials against configured environment variables (e.g., `AUTH_USER`, `AUTH_PASSWORD`) and issues an asymmetric RS256 JWT access token upon successful authentication.
- **PRD03 (Asymmetric RSA Key Management):** The Auth Microservice must manage an RSA key pair (minimum 2048-bit), loading existing keys from secure environment/volume configurations or generating a persistent key pair to sign tokens with the RSA Private Key.
- **PRD04 (Public Key Distribution Endpoint):** The Auth Microservice must expose a public endpoint (`GET /auth/public-key`) returning the RSA Public Key in standard PEM format (or JWKS format) to allow downstream microservices to retrieve and cache the verification key.
- **PRD05 (Sales Agent Inbound Security Guard):** The core Sales Agent must implement an authentication guard/middleware (e.g., FastAPI `Depends` / `HTTPBearer`) protecting analytical endpoints (`POST /chat`, analytical query routes), requiring an `Authorization: Bearer <token>` header.
- **PRD06 (Cryptographic Signature & Claims Verification):** The Sales Agent must mathematically verify incoming JWTs using the Auth Microservice's RSA Public Key, asserting token signature integrity, expiration (`exp`), issuer (`iss`), and subject (`sub`) claims.
- **PRD07 (Standardized Security Error Handling):** The system must return deterministic HTTP status codes: `401 Unauthorized` for missing, expired, or invalid signatures; and `403 Forbidden` for insufficient scopes/permissions, providing structured error responses without leaking internal stack traces.
- **PRD08 (Cluster Orchestration & Service Deployment):** The project must provide declarative deployment manifests (K3s/Kubernetes and Docker Compose) deploying the Auth Microservice (1 replica), Redis session store (1 replica), and the Sales Agent application (2+ replicas) with independent health probes (`livenessProbe`, `readinessProbe`).

## Non-Functional Requirements

- **Zero Trust Security & Cryptographic Segregation:** The Sales Agent and analytical worker pods must never possess or have access to the RSA Private Key, ensuring that even a total compromise of analytical pods cannot lead to token forgery.
- **Verification Performance & Latency:** Local cryptographic token validation in the Sales Agent must complete in sub-2ms latency. Public keys must be cached in memory by the Sales Agent to avoid synchronous HTTP roundtrips to the Auth Service on every incoming analytical request.
- **High Availability & Decoupling:** The Sales Agent must continue validating active tokens using its cached Public Key even if the Auth Microservice experiences temporary downtime or restart.
- **Architectural Decoupling (Hexagonal Architecture):** Token validation and security dependencies in the Sales Agent must implement inbound security ports, keeping domain logic and use cases isolated from HTTP authentication frameworks.
- **Clean Configuration & 12-Factor Adherence:** All sensitive credentials, token expiration settings (`JWT_EXPIRATION_MINUTES`), and service URLs (`AUTH_SERVICE_URL`) must be configurable via environment variables.

## Business Rules

- **BR01 (Private Key Confidentiality):** The RSA Private Key must remain strictly confidential to the Authentication Microservice container. No other service, container, or logs may store or print private key contents.
- **BR02 (Token Expiration & Replay Protection):** All issued JWTs must carry a strict Time-To-Live expiration claim (`exp`, default 60 minutes). Expired tokens must be rejected unconditionally.
- **BR03 (Stateless Mathematical Verification):** The Sales Agent must validate tokens offline and statelessly via public key cryptography, eliminating the need for a centralized session lookup on every API invocation.
- **BR04 (Public Key Resilient Caching):** The Sales Agent must load the Public Key at startup (or on first request) and cache it. If token verification fails due to an unknown key ID, the cache may be refreshed asynchronously against `GET /auth/public-key`.
- **BR05 (Sanitized Security Responses):** Failed authentication attempts must return generic, sanitized error messages (e.g., `"Credenciais inválidas"` or `"Token de acesso inválido ou expirado"`) to prevent credential harvesting.

## Critical Data (Conceptual)

- **Client Credentials:** Username and password transmitted during login over TLS.
- **RSA Key Pair:** RSA Private Key (PEM format, private to Auth Service) and RSA Public Key (PEM format, publicly distributed).
- **JWT Payload Claims:**
  - `sub` (Subject / User Identifier).
  - `iss` (Issuer identifier, e.g., `sales-auth-service`).
  - `iat` (Issued At timestamp).
  - `exp` (Expiration timestamp).
  - `roles` (User role or permissions list).
- **Access Token Response:** JSON structure containing `access_token`, `token_type` (`Bearer`), and `expires_in` (seconds).
- **Cluster Auth Config:** Service URLs, key paths, expiration durations, and mock user settings.

## User Flow

### Happy Path (Authentication and Protected Query Execution)

1. The client sends authentication credentials to the Auth Microservice: `POST /auth/login` with username and password.
2. The Auth Microservice validates the credentials against configured environment variables.
3. The Auth Microservice generates an RS256 JWT containing identity claims (`sub`, `exp`, `iss`), signs it with the RSA Private Key, and returns the access token to the client.
4. The client sends an analytical request to the Sales Agent (`POST /chat`) including the header `Authorization: Bearer <access_token>`.
5. The Sales Agent intercepts the request, verifies the signature using the cached RSA Public Key, and validates claim expiration (`exp`).
6. The Sales Agent extracts the user identity (`sub`), executes the analytical use case, and returns the response payload.

### Exception Path 1 (Invalid Credentials on Login)

1. The client sends incorrect username or password to `POST /auth/login`.
2. The Auth Microservice verifies the credentials and detects a mismatch.
3. The Auth Microservice returns `401 Unauthorized` with payload `{"detail": "Credenciais inválidas"}`.
4. No token is generated or issued.

### Exception Path 2 (Missing or Malformed Authorization Header)

1. The client sends a request to `POST /chat` without an `Authorization` header or with an invalid scheme (e.g., `Basic` instead of `Bearer`).
2. The Sales Agent security middleware intercepts the request.
3. The request is rejected immediately with `401 Unauthorized` and `WWW-Authenticate: Bearer` header before invoking domain logic.

### Exception Path 3 (Expired or Tampered JWT Token)

1. The client sends a request to `POST /chat` with a modified payload or an expired token (`exp < now`).
2. The Sales Agent validates the cryptographic signature or checks the expiration timestamp.
3. The signature fails mathematical verification or expiration validation fails.
4. The Sales Agent rejects the request with `401 Unauthorized` and a sanitized error message (`"Token inválido ou expirado"`).

### Exception Path 4 (Auth Microservice Temporary Restart)

1. The Auth Microservice is temporarily restarted or undergoing deployment in the cluster.
2. A client with an already issued, valid JWT sends a request to the Sales Agent.
3. The Sales Agent validates the token using its locally cached RSA Public Key without calling the Auth Microservice.
4. The request completes successfully with zero disruption to analytical operations.

## Acceptance Criteria

| ID | Criterion | Validation Method |
| --- | --- | --- |
| AC01 | Standalone Auth Microservice starts cleanly and exposes `POST /auth/login` and `GET /auth/public-key`. | Automated service startup and endpoint HTTP status integration test. |
| AC02 | Valid user credentials generate a signed RS256 JWT containing `sub`, `exp`, `iat`, and `iss` claims. | Unit tests validating token generation and claim payload structure. |
| AC03 | Invalid credentials return `401 Unauthorized` with sanitized error responses. | Automated API test verifying rejection of invalid passwords/usernames. |
| AC04 | Sales Agent protects analytical endpoints (`POST /chat`), requiring valid Bearer tokens. | Integration tests asserting `401 Unauthorized` when `Authorization` header is missing. |
| AC05 | Sales Agent successfully verifies valid RS256 tokens using the Auth Service's Public Key. | End-to-end integration test from token issuance to successful `/chat` execution. |
| AC06 | Expired tokens, forged signatures, or tampered tokens are rejected with `401 Unauthorized`. | Security test suite evaluating tampered payloads and expired timestamps. |
| AC07 | Declarative manifests (Docker Compose / K3s) deploy Auth Service, Sales Agent replicas, and Redis seamlessly. | Manifest dry-run validation and multi-container orchestration smoke test. |
