# T006: Asymmetric JWT Authentication Microservice

## PRD Reference

- **PRD:** [R006-microservice-jwt-authentication.md](../business-requirements/R006-microservice-jwt-authentication.md)
- **Product Strategy:** [PS006-microservice-jwt-authentication.md](../product-strategy/PS006-microservice-jwt-authentication.md)
- **Test Coverage:** [TEST006-microservice-jwt-authentication.md](../tests/TEST006-microservice-jwt-authentication.md)
- **Security Audit:** [S006-microservice-jwt-authentication.md](../security/S006-microservice-jwt-authentication.md)

## Technical Goal

Implement a Zero Trust, microservice-based authentication
architecture consisting of two decoupled components:

1. **Authentication Microservice** (`auth-service/`): A
   standalone, lightweight FastAPI application responsible
   exclusively for credential validation, RSA key pair
   management, and RS256 JWT token issuance. This service
   is the sole custodian of the RSA Private Key.
2. **Sales Agent Security Guard**: An inbound security
   middleware integrated into the existing Sales Agent
   FastAPI application that intercepts protected endpoints
   (`POST /chat`), validates Bearer tokens using the Auth
   Service's RSA Public Key (cached in memory), and rejects
   unauthenticated or expired requests with deterministic
   HTTP 401/403 responses.

The architecture ensures cryptographic segregation: even
a total compromise of all Sales Agent pods cannot lead to
token forgery, as the Private Key never leaves the Auth
Microservice container (Ref: R006, PRD01-PRD08, BR01).

## Architecture Decisions (ADRs)

### ADR-01: Standalone Auth Microservice (Separate Codebase)

- **Decision:** Create the Auth Microservice as a separate
  Python package inside a new `auth-service/` directory at
  the project root, with its own `requirements.txt`,
  `Dockerfile`, and FastAPI application.
- **Alternatives Evaluated:**
  - *Embedded auth module within Sales Agent*: Violates
    Zero Trust (BR01) — the Private Key would reside in
    the same process as analytical endpoints. Compromising
    one pod exposes the signing key.
  - *External identity provider (Keycloak, Auth0)*:
    Overengineered for the current single-tenant,
    env-configured credential model. Adds operational
    complexity and external dependencies.
- **Trade-offs:** A separate microservice introduces
  deployment complexity (one more container) but provides
  absolute cryptographic isolation of the Private Key,
  independent scaling, and clear security boundaries.
- **Requirement Link:** PRD01, BR01.

### ADR-02: PyJWT with `cryptography` for RS256

- **Decision:** Use `PyJWT>=2.8.0` with the `cryptography`
  backend for RS256 token signing (Auth Service) and
  verification (Sales Agent).
- **Alternatives Evaluated:**
  - `python-jose`: Less actively maintained, broader
    attack surface with multiple backend options.
  - `authlib`: Full OAuth2 framework — overscoped for
    simple JWT sign/verify operations.
  - `PyJWT` (HS256 only): Symmetric keys violate the
    asymmetric requirement (PRD03).
- **Trade-offs:** `PyJWT` + `cryptography` is the
  industry-standard combination for RS256 in Python. The
  `cryptography` package adds ~15MB to Docker images but
  provides FIPS-compliant RSA operations and is already a
  transitive dependency of many Python packages.
- **Requirement Link:** PRD02, PRD03, PRD06.

### ADR-03: RSA Key Generation and Management Strategy

- **Decision:** The Auth Microservice generates an RSA-2048
  key pair at startup if no existing keys are found in the
  configured paths (`RSA_PRIVATE_KEY_PATH` /
  `RSA_PUBLIC_KEY_PATH` environment variables). Keys are
  persisted to the filesystem for container restarts.
  Alternatively, keys can be injected via environment
  variables (`RSA_PRIVATE_KEY_PEM`, `RSA_PUBLIC_KEY_PEM`)
  for Kubernetes Secret mounting.
- **Rationale:** 12-Factor compliance (config via
  environment). Supports both local dev (auto-generation)
  and production K8s deployments (Secret volume mount).
- **Requirement Link:** PRD03, NFR05.

### ADR-04: Public Key Distribution via REST Endpoint

- **Decision:** The Auth Microservice exposes
  `GET /auth/public-key` returning the RSA Public Key in
  PEM format as a JSON response
  (`{"public_key": "-----BEGIN PUBLIC KEY-----..."}`).
- **Alternatives Evaluated:**
  - JWKS endpoint (`/.well-known/jwks.json`): Standard
    for multi-key rotation scenarios. Deferred as
    future enhancement since the current design uses a
    single static key pair.
- **Trade-offs:** Simple PEM distribution is sufficient
  for the current single-key architecture. Migration to
  JWKS is non-breaking (additive endpoint).
- **Requirement Link:** PRD04, BR04.

### ADR-05: Sales Agent Security Guard (Hexagonal Inbound Adapter)

- **Decision:** Implement the JWT verification middleware
  as an inbound adapter following the existing hexagonal
  architecture. The guard is a FastAPI `Depends` dependency
  injected into protected routes, NOT a global middleware.
  This preserves access to public endpoints (`/health`,
  `/static/`, `/`) without authentication.
- **Rationale:** Route-level dependency injection
  (`Depends(verify_jwt_token)`) provides granular control
  over which endpoints require authentication. Follows
  the existing `Depends(get_web_chat_use_case_singleton)`
  pattern in
  [chat_controller.py](file:///c:/Code/challenge_ai_engineer/src/adapter/inbound/web/chat_controller.py).
- **Requirement Link:** PRD05, NFR04.

### ADR-06: Public Key Caching with Lazy Loading

- **Decision:** The Sales Agent loads the Auth Service's
  RSA Public Key on first authenticated request (lazy
  initialization) and caches it in a module-level singleton.
  Cache invalidation occurs only when an explicit
  verification failure suggests key rotation (future
  enhancement). The key fetch URL is configured via
  `AUTH_SERVICE_URL` environment variable.
- **Rationale:** Lazy loading ensures the Sales Agent can
  start even if the Auth Service is temporarily unavailable
  (NFR03 — High Availability). The cached key enables
  offline validation without synchronous HTTP calls on
  every request (NFR02 — sub-2ms latency).
- **Requirement Link:** PRD06, BR03, BR04, NFR02, NFR03.

### ADR-07: Docker Compose for Multi-Container Orchestration

- **Decision:** Create a `docker-compose.yml` at the
  project root deploying three services: `auth-service`
  (port 8001), `sales-agent` (port 8000), and `redis`
  (port 6379). K8s manifests are updated with an
  additional Auth Service Deployment and Service.
- **Requirement Link:** PRD08, AC07.

## Security and Reliability

### Security Mitigations

- **Private Key Isolation (BR01):** The RSA Private Key
  exists only within the `auth-service` container. The
  Sales Agent container never possesses, receives, or logs
  the Private Key. Environment variable
  `RSA_PRIVATE_KEY_PEM` is only injected into the Auth
  Service pod.
- **Token Forgery Prevention:** RS256 asymmetric signing
  ensures that possessing the Public Key (which is public
  by design) is insufficient to create valid tokens.
- **Replay / Expiration Protection (BR02):** All tokens
  carry a mandatory `exp` claim (default 60 minutes via
  `JWT_EXPIRATION_MINUTES`). The Sales Agent validates
  `exp` on every request, rejecting expired tokens with
  HTTP 401.
- **Credential Harvesting Prevention (BR05):** Failed
  login attempts return generic `"Credenciais inválidas"`
  without differentiating between invalid username and
  invalid password. No stack traces in error responses.
- **Timing Attack Mitigation:** Credential comparison
  uses `hmac.compare_digest()` for constant-time string
  comparison, preventing timing-based side-channel attacks.

### Performance

- **Token Verification Latency:** RS256 signature
  verification with a cached Public Key completes in
  < 0.5ms on modern hardware, well under the 2ms NFR
  threshold.
- **Zero Network Overhead:** After initial Public Key
  fetch, all token verifications are local cryptographic
  operations with zero HTTP round-trips to the Auth
  Service.
- **Auth Service Downtime Resilience (NFR03):** Active
  tokens remain valid and verifiable using the cached
  Public Key even during Auth Service restarts or
  redeployments.

## Technical Checklist (Atomic Tasks)

### 🔵 Phase 1 — Domain Core (Zero framework dependencies)

#### Leaf nodes (fully parallel — no domain dependencies)

- [COMPLETED] Task 001 - [Domain-Exception]: Create
  `AuthenticationError` exception hierarchy
  (Depends On: —)
- [COMPLETED] Task 002 - [Domain-Model]: Create
  `TokenClaims` value object (Depends On: —)
- [COMPLETED] Task 003 - [Domain-Model]: Create
  `AuthCredentials` value object (Depends On: —)
- [COMPLETED] Task 004 - [Domain-Model]: Create
  `TokenResponse` value object (Depends On: —)

#### Domain service (depends on models above)

- [COMPLETED] Task 005 - [Domain-Service]: Implement
  `CredentialValidator` domain service
  (Depends On: Task 001, Task 003)

### 🟡 Phase 2 — Ports and Use Cases (Depends on Phase 1)

#### Phase 2 tasks (all parallel-safe)

- [COMPLETED] Task 006 - [Port-Out]: Define `TokenSignerPort`
  output port interface (Depends On: Task 002, Task 004)
- [COMPLETED] Task 007 - [Port-Out]: Define `TokenVerifierPort`
  output port interface (Depends On: Task 002)
- [COMPLETED] Task 008 - [Port-Out]: Define
  `PublicKeyProviderPort` output port interface
  (Depends On: —)
- [COMPLETED] Task 009 - [Port-In]: Define
  `AuthenticateUserUseCase` input port interface
  (Depends On: Task 003, Task 004)
- [COMPLETED] Task 010 - [UseCase]: Implement
  `AuthenticationApplicationService`
  (Depends On: Task 005, Task 006, Task 009)
- [COMPLETED] Task 011 - [Config]: Add `PyJWT` and
  `cryptography` to dependencies (Depends On: —)

### 🟢 Phase 3 — Adapters (Depends on Phase 2)

#### Phase 3 tasks (all parallel-safe)

- [COMPLETED] Task 012 - [Adapter-External]: Implement
  `JwtRs256TokenAdapter` (sign + verify)
  (Depends On: Task 006, Task 007, Task 011)
- [COMPLETED] Task 013 - [Adapter-External]: Implement
  `RsaKeyManager` for key generation and loading
  (Depends On: Task 011)
- [COMPLETED] Task 014 - [Adapter-Web]: Implement Auth
  Microservice FastAPI app with login and public-key
  endpoints (Depends On: Task 010, Task 012, Task 013)
- [COMPLETED] Task 015 - [Adapter-Web]: Implement
  `HttpPublicKeyProvider` for Sales Agent
  (Depends On: Task 008)
- [COMPLETED] Task 016 - [Adapter-Web]: Implement
  `JwtSecurityGuard` FastAPI dependency for Sales Agent
  (Depends On: Task 007, Task 015)
- [COMPLETED] Task 017 - [Adapter-Web]: Integrate
  `JwtSecurityGuard` into `chat_controller.py`
  (Depends On: Task 016)
- [COMPLETED] Task 018 - [Adapter-Infra]: Create Auth Service
  Dockerfile and update docker-compose.yml
  (Depends On: Task 014)
- [COMPLETED] Task 019 - [Adapter-Infra]: Update K8s manifests
  with Auth Service Deployment and ConfigMap
  (Depends On: Task 014)
- [COMPLETED] Task 020 - [Config]: Update `.env.example` with
  auth environment variables (Depends On: —)
- [COMPLETED] Task 021 - [Test-Unit]: Unit tests for
  `CredentialValidator` and domain models
  (Depends On: Task 005)
- [COMPLETED] Task 022 - [Test-Unit]: Unit tests for
  `JwtRs256TokenAdapter` (Depends On: Task 012)
- [COMPLETED] Task 023 - [Test-Unit]: Unit tests for
  `JwtSecurityGuard` (Depends On: Task 016)
- [COMPLETED] Task 024 - [Test-Integration]: End-to-end auth
  flow integration test (Depends On: Task 014,
  Task 016, Task 017)

## Task Detailing (Summary Tasks)

### Task 001 - [Domain-Exception]: Create AuthenticationError hierarchy

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 002, Task 003, Task 004
- **Objective:** Define domain exceptions for
  authentication failures, maintaining the existing
  exception pattern.
- **Files/Path:**
  `src/domain/exception/auth_exceptions.py`
- **Reuse:** Follow the hierarchy pattern from
  [session_exceptions.py](file:///c:/Code/challenge_ai_engineer/src/domain/exception/session_exceptions.py).
- **Technical Acceptance Criteria:**
  - `AuthenticationError(Exception)`: Base exception.
  - `InvalidCredentialsError(AuthenticationError)`:
    Wrong username or password.
  - `InvalidTokenError(AuthenticationError)`: Malformed
    or tampered JWT token, with `reason` attribute.
  - `ExpiredTokenError(InvalidTokenError)`: Token `exp`
    has passed.
  - `MissingTokenError(AuthenticationError)`: No
    `Authorization` header present.
  - Zero framework imports. Pure Python.
  - Unit test validates instantiation and message.

---

### Task 002 - [Domain-Model]: Create TokenClaims value object

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 001, Task 003, Task 004
- **Objective:** Define an immutable domain representation
  of JWT token claims, decoupled from any JWT library.
- **Files/Path:** `src/domain/model/auth_models.py`
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Immutable dataclass with fields: `sub` (str),
    `iss` (str), `iat` (int, Unix timestamp),
    `exp` (int, Unix timestamp),
    `roles` (tuple[str, ...]).
  - Property `is_expired` → bool (compares `exp` with
    current UTC timestamp).
  - Zero framework imports. Pure Python `dataclass`.
  - Unit test validates construction, immutability, and
    `is_expired` logic.

---

### Task 003 - [Domain-Model]: Create AuthCredentials value object

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 001, Task 002, Task 004
- **Objective:** Define an immutable value object for
  user login credentials.
- **Files/Path:** `src/domain/model/auth_models.py`
  (same file as Task 002)
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Immutable dataclass with fields: `username` (str),
    `password` (str).
  - Zero framework imports. Pure Python `dataclass`.
  - Unit test validates construction.

---

### Task 004 - [Domain-Model]: Create TokenResponse value object

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 001, Task 002, Task 003
- **Objective:** Define an immutable domain representation
  of a successful authentication response.
- **Files/Path:** `src/domain/model/auth_models.py`
  (same file as Task 002)
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Immutable dataclass with fields: `access_token` (str),
    `token_type` (str, default `"Bearer"`),
    `expires_in` (int, seconds until expiration).
  - Zero framework imports. Pure Python `dataclass`.
  - Unit test validates construction and defaults.

---

### Task 005 - [Domain-Service]: Implement CredentialValidator

- **Phase:** 1
- **Depends On:** Task 001, Task 003
- **Parallel With:** —
- **Objective:** Pure domain service that validates
  user credentials against configured expected values
  using constant-time comparison.
- **Files/Path:** `src/domain/service/credential_validator.py`
- **Reuse:** Uses `AuthCredentials` (Task 003), raises
  `InvalidCredentialsError` (Task 001).
- **Technical Acceptance Criteria:**
  - Class `CredentialValidator` with method
    `validate(credentials: AuthCredentials,
    expected_username: str,
    expected_password: str) -> bool`.
  - Uses `hmac.compare_digest()` for constant-time
    string comparison (timing attack mitigation).
  - Raises `InvalidCredentialsError` on mismatch.
  - Returns `True` on match.
  - Zero framework imports. Pure Python + `hmac` stdlib.
  - Unit tests: valid credentials → `True`, invalid
    username → raises, invalid password → raises.

---

### Task 006 - [Port-Out]: Define TokenSignerPort

- **Phase:** 2
- **Depends On:** Task 002 (`TokenClaims`), Task 004
  (`TokenResponse`)
- **Parallel With:** Task 007, Task 008, Task 009,
  Task 011
- **Objective:** Define the output port interface for
  JWT token creation and signing.
- **Files/Path:**
  `src/application/port/outbound/token_port.py`
- **Reuse:** References `TokenClaims`, `TokenResponse`
  from Domain layer.
- **Technical Acceptance Criteria:**
  - Abstract class `TokenSignerPort(ABC)` with method
    `sign(claims: TokenClaims) -> TokenResponse`.
  - Docstring specifying the RS256 signing contract.
  - Unit test: verify the interface is abstract.

---

### Task 007 - [Port-Out]: Define TokenVerifierPort

- **Phase:** 2
- **Depends On:** Task 002 (`TokenClaims`)
- **Parallel With:** Task 006, Task 008, Task 009,
  Task 011
- **Objective:** Define the output port interface for
  JWT token verification.
- **Files/Path:**
  `src/application/port/outbound/token_port.py`
  (same file as Task 006)
- **Reuse:** References `TokenClaims` from Domain layer.
- **Technical Acceptance Criteria:**
  - Abstract class `TokenVerifierPort(ABC)` with method
    `verify(token: str, public_key_pem: str)
    -> TokenClaims`.
  - Raises `InvalidTokenError` on verification failure.
  - Raises `ExpiredTokenError` on expired tokens.
  - Docstring specifying RS256 verification contract.
  - Unit test: verify the interface is abstract.

---

### Task 008 - [Port-Out]: Define PublicKeyProviderPort

- **Phase:** 2
- **Depends On:** —
- **Parallel With:** Task 006, Task 007, Task 009,
  Task 011
- **Objective:** Define the output port interface for
  fetching and caching the Auth Service's RSA Public Key.
- **Files/Path:**
  `src/application/port/outbound/public_key_provider_port.py`
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Abstract class `PublicKeyProviderPort(ABC)` with
    method `get_public_key() -> str` (returns PEM string).
  - Docstring: "Fetches the RSA Public Key from the
    Auth Service. Implementations SHOULD cache the key
    in memory."
  - Unit test: verify the interface is abstract.

---

### Task 009 - [Port-In]: Define AuthenticateUserUseCase

- **Phase:** 2
- **Depends On:** Task 003 (`AuthCredentials`), Task 004
  (`TokenResponse`)
- **Parallel With:** Task 006, Task 007, Task 008,
  Task 011
- **Objective:** Define the input port for the
  authentication use case (Auth Microservice side).
- **Files/Path:**
  `src/application/port/inbound/authenticate_user_use_case.py`
- **Reuse:** References `AuthCredentials`, `TokenResponse`.
- **Technical Acceptance Criteria:**
  - Abstract class `AuthenticateUserUseCase(ABC)` with
    method `authenticate(credentials: AuthCredentials)
    -> TokenResponse`.
  - Raises `InvalidCredentialsError` on failure.
  - Unit test: verify the interface is abstract.

---

### Task 010 - [UseCase]: Implement AuthenticationApplicationService

- **Phase:** 2
- **Depends On:** Task 005 (`CredentialValidator`),
  Task 006 (`TokenSignerPort`),
  Task 009 (`AuthenticateUserUseCase`)
- **Parallel With:** Task 011
- **Objective:** Application service orchestrating
  credential validation and token issuance.
- **Files/Path:**
  `src/application/service/authentication_service.py`
- **Reuse:** `CredentialValidator` (Task 005),
  `TokenSignerPort` (Task 006).
- **Technical Acceptance Criteria:**
  - Class `AuthenticationApplicationService` implements
    `AuthenticateUserUseCase`.
  - Constructor receives `CredentialValidator`,
    `TokenSignerPort`, `expected_username` (str),
    `expected_password` (str),
    `token_expiration_minutes` (int, default 60),
    `issuer` (str, default `"sales-auth-service"`).
  - `authenticate()` flow: (1) validate credentials
    via `CredentialValidator`, (2) build `TokenClaims`
    with `sub`, `iss`, `iat`, `exp`, `roles`,
    (3) sign via `TokenSignerPort`, (4) return
    `TokenResponse`.
  - Unit test with mocked `TokenSignerPort`: valid
    credentials → token returned, invalid →
    `InvalidCredentialsError` raised.

---

### Task 011 - [Config]: Add PyJWT and cryptography dependencies

- **Phase:** 2
- **Depends On:** —
- **Parallel With:** Task 006, Task 007, Task 008,
  Task 009, Task 010
- **Objective:** Add JWT and RSA cryptography
  dependencies.
- **Files/Path:**
  [requirements.txt](file:///c:/Code/challenge_ai_engineer/requirements.txt),
  `auth-service/requirements.txt` (new file)
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Add `PyJWT>=2.8.0` and `cryptography>=42.0.0` to
    both `requirements.txt` files.
  - Verify `pip install` completes without conflicts.
  - Verify `python -c "import jwt; print(jwt.__version__)"`.

---

### Task 012 - [Adapter-External]: Implement JwtRs256TokenAdapter

- **Phase:** 3
- **Depends On:** Task 006, Task 007, Task 011
- **Parallel With:** Task 013, Task 015, Task 016,
  Task 020
- **Objective:** Implement both `TokenSignerPort` and
  `TokenVerifierPort` using `PyJWT` with RS256 algorithm.
- **Files/Path:**
  `src/adapter/outbound/auth/jwt_token_adapter.py`
- **Reuse:** Implements `TokenSignerPort` (Task 006)
  and `TokenVerifierPort` (Task 007).
- **Technical Acceptance Criteria:**
  - Class `JwtRs256TokenAdapter(TokenSignerPort,
    TokenVerifierPort)`.
  - `sign(claims)`: encodes JWT with `jwt.encode()`
    using RS256 algorithm and the provided Private Key.
  - `verify(token, public_key_pem)`: decodes JWT with
    `jwt.decode()` using RS256, validates `exp`, `iss`.
    Returns `TokenClaims`. Catches `jwt.ExpiredSignatureError`
    → raises `ExpiredTokenError`. Catches
    `jwt.InvalidTokenError` → raises `InvalidTokenError`.
  - Constructor accepts `private_key_pem` (Optional[str])
    for signing (only Auth Service needs it) and
    `allowed_algorithms` (default `["RS256"]`).
  - Integration test: generate RSA key pair → sign →
    verify round-trip.

---

### Task 013 - [Adapter-External]: Implement RsaKeyManager

- **Phase:** 3
- **Depends On:** Task 011
- **Parallel With:** Task 012, Task 015, Task 016,
  Task 020
- **Objective:** Manage RSA key pair generation, loading
  from file/environment, and persistence.
- **Files/Path:**
  `src/adapter/outbound/auth/rsa_key_manager.py`
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Class `RsaKeyManager` with class methods:
    `generate_key_pair(key_size=2048)
    -> tuple[str, str]` (private_pem, public_pem),
    `load_or_generate(
    private_key_path, public_key_path)
    -> tuple[str, str]`.
  - Supports loading keys from environment variables
    (`RSA_PRIVATE_KEY_PEM`, `RSA_PUBLIC_KEY_PEM`) or
    filesystem paths.
  - If no keys found, generates new pair and persists.
  - Uses `cryptography` library for RSA key generation.
  - **Security:** Never logs or prints Private Key
    content.
  - Unit test: generate → load round-trip, verify PEM
    format headers.

---

### Task 014 - [Adapter-Web]: Implement Auth Microservice FastAPI app

- **Phase:** 3
- **Depends On:** Task 010, Task 012, Task 013
- **Parallel With:** Task 015, Task 016, Task 020
- **Objective:** Create the standalone Auth Microservice
  application with login and public-key endpoints.
- **Files/Path:** `auth-service/` directory:
  - `auth-service/app.py` (FastAPI app)
  - `auth-service/requirements.txt`
  - `auth-service/__init__.py`
- **Reuse:** `AuthenticationApplicationService`
  (Task 010), `JwtRs256TokenAdapter` (Task 012),
  `RsaKeyManager` (Task 013).
- **Technical Acceptance Criteria:**
  - `POST /auth/login`: Accepts JSON body
    `{"username": "...", "password": "..."}`. Returns
    `{"access_token": "...", "token_type": "Bearer",
    "expires_in": 3600}`. Returns HTTP 401 with
    `{"detail": "Credenciais inválidas"}` on failure.
  - `GET /auth/public-key`: Returns
    `{"public_key": "-----BEGIN PUBLIC KEY-----..."}`.
  - `GET /health`: Returns `{"status": "ok"}`.
  - Configuration via env vars: `AUTH_USER`,
    `AUTH_PASSWORD`, `JWT_EXPIRATION_MINUTES`,
    `RSA_PRIVATE_KEY_PATH`, `RSA_PUBLIC_KEY_PATH`.
  - All error responses are sanitized (BR05).
  - CORS enabled for local development.

---

### Task 015 - [Adapter-Web]: Implement HttpPublicKeyProvider

- **Phase:** 3
- **Depends On:** Task 008
- **Parallel With:** Task 012, Task 013, Task 014,
  Task 020
- **Objective:** Implement the `PublicKeyProviderPort`
  adapter that fetches and caches the RSA Public Key from
  the Auth Service via HTTP.
- **Files/Path:**
  `src/adapter/outbound/auth/http_public_key_provider.py`
- **Reuse:** Implements `PublicKeyProviderPort` (Task 008).
- **Technical Acceptance Criteria:**
  - Class `HttpPublicKeyProvider(PublicKeyProviderPort)`.
  - Constructor accepts `auth_service_url` (str, from
    `AUTH_SERVICE_URL` env var).
  - `get_public_key()`: On first call, fetches
    `GET {auth_service_url}/auth/public-key`, caches the
    PEM string in a module-level variable, and returns it.
    Subsequent calls return the cached value.
  - Raises `AuthenticationError` if the fetch fails.
  - Uses `urllib.request` (stdlib) to avoid adding
    `httpx`/`requests` as a dependency.
  - Unit test with mocked HTTP response.

---

### Task 016 - [Adapter-Web]: Implement JwtSecurityGuard

- **Phase:** 3
- **Depends On:** Task 007, Task 015
- **Parallel With:** Task 012, Task 013, Task 014,
  Task 020
- **Objective:** FastAPI dependency that extracts,
  validates, and decodes the Bearer token from the
  `Authorization` header.
- **Files/Path:**
  `src/adapter/inbound/web/jwt_security_guard.py`
- **Reuse:** `TokenVerifierPort` (Task 007),
  `PublicKeyProviderPort` (Task 008).
- **Technical Acceptance Criteria:**
  - Function `verify_jwt_token(
    authorization: str = Header(...))
    -> TokenClaims`.
  - Extracts `Bearer <token>` from `Authorization`
    header.
  - Raises `HTTPException(401)` with
    `WWW-Authenticate: Bearer` if:
    (1) header is missing, (2) scheme is not `Bearer`,
    (3) token signature is invalid,
    (4) token is expired.
  - Raises `HTTPException(403)` if token lacks required
    role/scope (future extensibility hook).
  - Error responses are sanitized (BR05):
    `{"detail": "Token inválido ou expirado"}`.
  - Returns `TokenClaims` for downstream use (user
    identity extraction).
  - Unit test with mocked `TokenVerifierPort`.

---

### Task 017 - [Adapter-Web]: Integrate guard into chat_controller

- **Phase:** 3
- **Depends On:** Task 016
- **Parallel With:** Task 018, Task 019, Task 020
- **Objective:** Wire the `JwtSecurityGuard` into the
  existing `POST /chat` endpoint.
- **Files/Path:**
  [chat_controller.py](file:///c:/Code/challenge_ai_engineer/src/adapter/inbound/web/chat_controller.py)
- **Reuse:** Existing `chat_controller.py`, adds
  `Depends(verify_jwt_token)`.
- **Technical Acceptance Criteria:**
  - `POST /chat` route adds
    `claims: TokenClaims = Depends(verify_jwt_token)`
    as a parameter.
  - The `TokenClaims.sub` value is logged for audit:
    `logger.info("Authenticated request from user: %s",
    claims.sub)`.
  - Public endpoints (`/health`, `/`, `/static/`)
    remain unauthenticated.
  - **Backward compatibility:** When `AUTH_ENABLED` env
    var is `"false"` (default for dev), the guard is
    bypassed and returns a default `TokenClaims`.
  - Unit test: request without token → 401, request with
    valid token → 200.

---

### Task 018 - [Adapter-Infra]: Auth Service Dockerfile and docker-compose

- **Phase:** 3
- **Depends On:** Task 014
- **Parallel With:** Task 017, Task 019, Task 020
- **Objective:** Create Docker deployment manifests for
  the full multi-container topology.
- **Files/Path:**
  - `auth-service/Dockerfile`
  - `docker-compose.yml` (project root, new file)
- **Reuse:** Existing Sales Agent `Dockerfile` as
  reference.
- **Technical Acceptance Criteria:**
  - `auth-service/Dockerfile`: Python 3.11-slim base,
    installs `auth-service/requirements.txt`, runs
    FastAPI on port 8001 with non-root user.
  - `docker-compose.yml` defines three services:
    (1) `auth-service` (port 8001, env vars for
    credentials and key paths),
    (2) `sales-agent` (port 8000, depends on
    `auth-service` and `redis`),
    (3) `redis` (port 6379).
  - `docker compose up` starts all three services.
  - Health checks defined for all services.

---

### Task 019 - [Adapter-Infra]: Update K8s manifests

- **Phase:** 3
- **Depends On:** Task 014
- **Parallel With:** Task 017, Task 018, Task 020
- **Objective:** Extend K8s manifests with Auth Service
  Deployment and Service resources.
- **Files/Path:**
  - `k8s/auth-deployment.yaml` (new)
  - `k8s/auth-service.yaml` (new)
  - `k8s/configmap.yaml` (update)
- **Reuse:** Existing K8s manifest patterns from
  [app-deployment.yaml](file:///c:/Code/challenge_ai_engineer/k8s/app-deployment.yaml).
- **Technical Acceptance Criteria:**
  - Auth Deployment: 1 replica, port 8001, liveness
    probe (`/health`), readiness probe (`/health`),
    Secret mount for RSA keys, ConfigMap ref for
    `AUTH_USER`, `JWT_EXPIRATION_MINUTES`.
  - Auth Service: ClusterIP on port 8001
    (`auth-service:8001`).
  - Updated ConfigMap adds `AUTH_SERVICE_URL:
    "http://auth-service:8001"`, `AUTH_ENABLED: "true"`.
  - `kubectl apply -f k8s/` deploys without errors.

---

### Task 020 - [Config]: Update .env.example

- **Phase:** 3
- **Depends On:** —
- **Parallel With:** Task 012-019
- **Objective:** Add authentication-related environment
  variables to the example config file.
- **Files/Path:**
  [.env.example](file:///c:/Code/challenge_ai_engineer/.env.example)
- **Reuse:** Existing `.env.example` structure.
- **Technical Acceptance Criteria:**
  - New section `# Authentication Configuration`:
    `AUTH_ENABLED=false`,
    `AUTH_SERVICE_URL=http://localhost:8001`,
    `AUTH_USER=admin`,
    `AUTH_PASSWORD=changeme`,
    `JWT_EXPIRATION_MINUTES=60`,
    `RSA_PRIVATE_KEY_PATH=`,
    `RSA_PUBLIC_KEY_PATH=`.
  - Comments explaining each variable.

---

### Task 021 - [Test-Unit]: Unit tests for domain models and CredentialValidator

- **Phase:** 3
- **Depends On:** Task 005
- **Parallel With:** Task 022, Task 023
- **Objective:** Comprehensive unit tests for all domain
  models and the credential validation service.
- **Files/Path:**
  `tests/unit/test_auth_domain.py`
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - `TokenClaims`: construction, `is_expired` with
    past/future timestamps.
  - `AuthCredentials`: construction and immutability.
  - `TokenResponse`: construction and defaults.
  - `CredentialValidator`: valid credentials → `True`,
    invalid username → raises
    `InvalidCredentialsError`, invalid password → raises
    `InvalidCredentialsError`.
  - Exception hierarchy: `InvalidCredentialsError`,
    `InvalidTokenError`, `ExpiredTokenError`,
    `MissingTokenError` all inherit from
    `AuthenticationError`.

---

### Task 022 - [Test-Unit]: Unit tests for JwtRs256TokenAdapter

- **Phase:** 3
- **Depends On:** Task 012
- **Parallel With:** Task 021, Task 023
- **Objective:** Verify JWT sign/verify round-trip with
  real RSA keys.
- **Files/Path:**
  `tests/unit/test_jwt_token_adapter.py`
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Generate test RSA key pair in fixture.
  - Sign `TokenClaims` → verify → decoded claims match.
  - Expired token → raises `ExpiredTokenError`.
  - Tampered token → raises `InvalidTokenError`.
  - Token signed with different key → raises
    `InvalidTokenError`.
  - Verify `iss` claim validation.

---

### Task 023 - [Test-Unit]: Unit tests for JwtSecurityGuard

- **Phase:** 3
- **Depends On:** Task 016
- **Parallel With:** Task 021, Task 022
- **Objective:** Verify the FastAPI security guard
  behavior with mocked token verifier.
- **Files/Path:**
  `tests/unit/test_jwt_security_guard.py`
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Missing `Authorization` header → `HTTPException(401)`.
  - `Authorization: Basic xxx` → `HTTPException(401)`.
  - Valid Bearer token → returns `TokenClaims`.
  - Expired token → `HTTPException(401)` with message
    `"Token inválido ou expirado"`.
  - Tampered token → `HTTPException(401)`.
  - Verify `WWW-Authenticate: Bearer` header in 401
    responses.

---

### Task 024 - [Test-Integration]: End-to-end auth flow

- **Phase:** 3
- **Depends On:** Task 014, Task 016, Task 017
- **Parallel With:** —
- **Objective:** Full end-to-end integration test
  exercising: login → token issuance → protected
  endpoint access → rejection of invalid tokens.
- **Files/Path:**
  `tests/integration/test_jwt_auth_e2e.py`
- **Reuse:** Real `JwtRs256TokenAdapter`,
  real `RsaKeyManager`, real `AuthenticationApplicationService`,
  mocked `SalesAnalysisUseCase`.
- **Technical Acceptance Criteria:**
  - **Happy Path (AC05):** Login with valid credentials
    → receive token → `POST /chat` with Bearer token
    → HTTP 200 with analytical response.
  - **Invalid Credentials (AC03):**
    `POST /auth/login` with wrong password → HTTP 401
    with `"Credenciais inválidas"`.
  - **Missing Token (AC04):** `POST /chat` without
    `Authorization` → HTTP 401.
  - **Expired Token (AC06):** Token with `exp` in the
    past → HTTP 401 with `"Token inválido ou expirado"`.
  - **Tampered Token (AC06):** Modified JWT payload →
    HTTP 401.
  - **Public Key Endpoint (AC01):**
    `GET /auth/public-key` → HTTP 200 with PEM string
    starting with `"-----BEGIN PUBLIC KEY-----"`.
  - **Auth Service Health:** `GET /health` → HTTP 200.

## Verification Plan

### Automated Tests

```bash
# Run all domain and unit tests
python -m pytest tests/unit/test_auth_domain.py -v
python -m pytest tests/unit/test_jwt_token_adapter.py -v
python -m pytest tests/unit/test_jwt_security_guard.py -v

# Run end-to-end integration test
python -m pytest tests/integration/test_jwt_auth_e2e.py -v

# Run the full test suite to confirm zero regressions
python -m pytest

# Docker Compose smoke test
docker compose up -d
docker compose ps
curl -s http://localhost:8001/health
curl -s http://localhost:8001/auth/public-key
docker compose down
```

### Manual Verification

- Start both services locally: Auth Service on port
  8001 and Sales Agent on port 8000. Authenticate via
  `curl -X POST http://localhost:8001/auth/login` with
  valid credentials and use the returned token to
  access `POST http://localhost:8000/chat`.
- Verify that requests without a valid Bearer token to
  `/chat` return HTTP 401 with `WWW-Authenticate: Bearer`.
- Apply K8s manifests with `kubectl apply -f k8s/` and
  verify all three pods (auth, sales-agent, redis) reach
  Ready state.
