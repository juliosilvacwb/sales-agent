# Architecture Specification: Distributed Session Scalability (T004)

## PRD Reference

- **PRD:** [R004-distributed-session-scalability.md](../business-requirements/R004-distributed-session-scalability.md)

## Technical Goal

Transition the Sales Data Analysis Agent compute tier into a completely stateless architecture by decoupling conversational session state from local memory into a centralized, low-latency Redis store. Enable horizontal multi-replica scaling in K3s/Kubernetes with zero context loss across pod lifecycles and rolling deployments.

## Architecture Decisions (ADRs)

- **ADR-001: Centralized Redis Session Store vs Relational/Sticky Sessions:** Evaluated Sticky Sessions at the Load Balancer vs PostgreSQL Session Table vs Redis Key-Value Store. Chose Redis because it delivers sub-millisecond retrieval latency necessary for LLM conversational context injection, avoids uneven load distribution (hot pods) inherent in sticky sessions, and eliminates overhead on primary relational databases.
- **ADR-002: Hexagonal Session Store Port Abstraction (`SessionStorePort`):** Evaluated coupling LangChain agent directly to Redis client vs abstracting session storage behind an outbound port interface. Chose to define `SessionStorePort` in the application layer and implement both `SessionMemoryAdapter` (for zero-dependency local dev) and `RedisSessionAdapter` (for production/K3s clusters). This preserves 100% architectural decoupling, testability with mocks, and zero framework leakage into domain core.
- **ADR-003: Stateless Agent Invocation in Application Service:** Evaluated holding stateful `SalesAgent` instances per session in memory vs instantiating/injecting chat history dynamically per request into the agent reasoning loop. Chose dynamic context injection so that any compute replica can serve any incoming request without maintaining in-memory session pools.
- **ADR-004: Declarative Infrastructure via K3s Manifests:** Created modular Kubernetes manifests (`k8s/`) separating Redis backing service, application multi-replica deployment with readiness/liveness probes, and load-balancing services. Configured through environment variables (`SESSION_STORE`, `REDIS_URL`, `SESSION_TTL_SECONDS`) complying with the 12-Factor App methodology.

## Security & Reliability

- **Key Injection Mitigation & Namespacing:** Session keys in Redis are enforced through strict regex validation (`^[a-zA-Z0-9_-]+$`) and namespaced with the prefix `sales_agent:session:<session_id>` to prevent key collision and injection attacks.
- **TTL & Resource Leak Protection:** All session keys are stored with a configurable Time-To-Live (default 86,400s / 24h), refreshed on every write, preventing unbounded RAM consumption in Redis.
- **Graceful Connection Degradation:** Transient Redis network failures are intercepted by retry logic and structured error logging, returning clean HTTP 503/sanitized error responses without exposing internal connection strings or stack traces.

## Technical Checklist (Atomic Tasks)

### 🔵 Phase 1 — Domain Core

- [x] Task 001 - [Domain-Model]: Enhance `SessionContext` and create session domain entities and value objects (Depends On: —)
- [x] Task 002 - [Domain-Exception]: Create domain-specific session exceptions (`SessionStorageError`, `InvalidSessionIdError`) (Depends On: —)

### 🟡 Phase 2 — Ports & Use Cases

- [x] Task 003 - [Port-Out]: Define `SessionStorePort` output port interface for chat history persistence (Depends On: Task 001, Task 002)
- [x] Task 004 - [UseCase]: Refactor `WebChatApplicationService` to be completely stateless using `SessionStorePort` (Depends On: Task 003)

### 🟢 Phase 3 — Adapters

- [x] Task 005 - [Adapter-Persistence]: Refactor `SessionMemoryAdapter` to implement `SessionStorePort` (Depends On: Task 003)
- [x] Task 006 - [Adapter-Persistence]: Implement `RedisSessionAdapter` with connection pooling and TTL management (Depends On: Task 003)
- [x] Task 007 - [Adapter-Infra]: Implement `SessionFactory` / Provider Resolver based on `SESSION_STORE` environment variable (Depends On: Task 005, Task 006)
- [x] Task 008 - [Adapter-Web]: Update `chat_controller` and dependency injection to wire stateless use case with session factory (Depends On: Task 004, Task 007)
- [x] Task 009 - [Adapter-Infra]: Update `requirements.txt` with `redis>=5.0.0` dependency (Depends On: —)
- [x] Task 010 - [Adapter-Infra]: Create production-ready K3s declarative manifests in `k8s/` (Depends On: Task 008)
- [x] Task 011 - [Test-Integration]: Implement integration and multi-replica simulation tests verifying distributed session continuity (Depends On: Task 007, Task 008)

## Task Detailing (Summary Tasks)

### Task 001 - [Domain-Model]: Enhance SessionContext and domain models

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 002
- **Objective:** Create and enhance domain models for session state representation, timestamps, and session key validation rules.
- **Files/Path:** `src/domain/model/session_context.py`
- **Reuse:** Existing `SessionContext` dataclass.
- **Technical Acceptance Criteria:** Pure Python dataclass with zero framework or database imports. Validates session identifier formatting.

### Task 002 - [Domain-Exception]: Create domain session exceptions

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 001
- **Objective:** Create explicit domain exceptions for session retrieval errors, connection timeouts, and invalid session keys.
- **Files/Path:** `src/domain/exception/session_exceptions.py` (New File)
- **Reuse:** None.
- **Technical Acceptance Criteria:** Defines `SessionStorageError`, `SessionConnectionError`, and `InvalidSessionIdError`.

### Task 003 - [Port-Out]: Define SessionStorePort interface

- **Phase:** 2
- **Depends On:** Task 001, Task 002
- **Parallel With:** —
- **Objective:** Define the abstract output port for getting, saving, and clearing chat message histories for a given `session_id`.
- **Files/Path:** `src/application/port/outbound/session_store_port.py` (New File)
- **Reuse:** `langchain_core.chat_history.BaseChatMessageHistory` / message models.
- **Technical Acceptance Criteria:** Abstract base class defining `get_history(session_id: str) -> BaseChatMessageHistory`, `save_history(session_id: str, history: BaseChatMessageHistory) -> None`, and `clear_history(session_id: str) -> None`.

### Task 004 - [UseCase]: Refactor WebChatApplicationService to be stateless

- **Phase:** 2
- **Depends On:** Task 003
- **Parallel With:** —
- **Objective:** Remove in-memory `_active_sessions` dictionary from `WebChatApplicationService`. Fetch session history from `SessionStorePort` on demand per request, pass history to `SalesAgent`, and persist updated history.
- **Files/Path:** `src/application/service/web_chat_application_service.py`
- **Reuse:** `WebChatUseCase`, `ChatRequestDTO`, `ChatResponseDTO`.
- **Technical Acceptance Criteria:** Application service maintains zero in-memory session state across calls. Unit tests pass with mocked `SessionStorePort`.

### Task 005 - [Adapter-Persistence]: Refactor SessionMemoryAdapter

- **Phase:** 3
- **Depends On:** Task 003
- **Parallel With:** Task 006, Task 009
- **Objective:** Ensure `SessionMemoryAdapter` implements `SessionStorePort` with thread-safe LRU in-memory storage.
- **Files/Path:** `src/adapter/outbound/memory/session_memory_adapter.py`
- **Reuse:** Existing `InMemoryChatMessageHistory`.
- **Technical Acceptance Criteria:** Fully adheres to `SessionStorePort`. Unit tests validate LRU eviction and memory bounds.

### Task 006 - [Adapter-Persistence]: Implement RedisSessionAdapter

- **Phase:** 3
- **Depends On:** Task 003
- **Parallel With:** Task 005, Task 009
- **Objective:** Implement `RedisSessionAdapter` implementing `SessionStorePort` using Redis client, with connection pooling, JSON message serialization, namespaced keys (`sales_agent:session:<session_id>`), and TTL expiration.
- **Files/Path:** `src/adapter/outbound/redis/redis_session_adapter.py` (New File)
- **Reuse:** `redis.Redis` / `redis.ConnectionPool`, `langchain_core.messages`.
- **Technical Acceptance Criteria:** Methods serialize messages to JSON and store in Redis with `EXPIRE` set to `SESSION_TTL_SECONDS`. Deserializes messages cleanly back to `BaseChatMessageHistory`.

### Task 007 - [Adapter-Infra]: Implement SessionFactory

- **Phase:** 3
- **Depends On:** Task 005, Task 006
- **Parallel With:** Task 008, Task 009
- **Objective:** Create a factory that reads `SESSION_STORE` (`redis` vs `memory`), `REDIS_URL`, and `SESSION_TTL_SECONDS` to return the appropriate `SessionStorePort` implementation singleton.
- **Files/Path:** `src/adapter/outbound/session_factory.py` (New File)
- **Reuse:** `SessionMemoryAdapter`, `RedisSessionAdapter`.
- **Technical Acceptance Criteria:** Returns `RedisSessionAdapter` when `SESSION_STORE=redis`; returns `SessionMemoryAdapter` when `SESSION_STORE=memory` or unset.

### Task 008 - [Adapter-Web]: Update chat_controller and Dependency Injection

- **Phase:** 3
- **Depends On:** Task 004, Task 007
- **Parallel With:** Task 010
- **Objective:** Wire `get_web_chat_use_case_singleton` to instantiate `WebChatApplicationService` with the resolved `SessionStorePort` from `SessionFactory`.
- **Files/Path:** `src/adapter/inbound/web/chat_controller.py`
- **Reuse:** FastAPI router, `get_web_chat_use_case_singleton`.
- **Technical Acceptance Criteria:** API endpoints correctly invoke the stateless application service with the configured session adapter.

### Task 009 - [Adapter-Infra]: Update requirements.txt

- **Phase:** 3
- **Depends On:** —
- **Parallel With:** Task 005, Task 006
- **Objective:** Add `redis>=5.0.0` to project dependencies.
- **Files/Path:** `requirements.txt`
- **Reuse:** Existing requirements.
- **Technical Acceptance Criteria:** Dependency is declared with compatible version bounds.

### Task 010 - [Adapter-Infra]: Create K3s Declarative Manifests

- **Phase:** 3
- **Depends On:** Task 008
- **Parallel With:** Task 011
- **Objective:** Create production-ready Kubernetes manifests in `k8s/` folder:
  - `k8s/redis-deployment.yaml`: Redis standalone pod with container port 6379.
  - `k8s/redis-service.yaml`: ClusterIP service for Redis (`redis-service:6379`).
  - `k8s/app-deployment.yaml`: Sales Agent deployment with `replicas: 2`, environment variables (`SESSION_STORE=redis`, `REDIS_URL=redis://redis-service:6379/0`), `livenessProbe`, `readinessProbe`, and resource limits.
  - `k8s/app-service.yaml`: Service routing traffic evenly across application replicas.
- **Files/Path:** `k8s/redis-deployment.yaml`, `k8s/redis-service.yaml`, `k8s/app-deployment.yaml`, `k8s/app-service.yaml`
- **Reuse:** None.
- **Technical Acceptance Criteria:** Valid YAML syntax conforming to Kubernetes v1 schemas, verified via dry-run linter.

### Task 011 - [Test-Integration]: Distributed Session Multi-Replica Integration Tests

- **Phase:** 3
- **Depends On:** Task 007, Task 008
- **Parallel With:** Task 010
- **Objective:** Implement comprehensive integration tests simulating multi-pod round-robin requests on the same `session_id`, verifying context preservation, TTL renewal, and pod failover behavior.
- **Files/Path:** `tests/integration/test_distributed_session_integration.py` (New File)
- **Reuse:** `WebChatApplicationService`, `RedisSessionAdapter`, `SessionMemoryAdapter`.
- **Technical Acceptance Criteria:** Validates end-to-end multi-turn conversation across distinct worker service instances sharing the same Redis session store with 100% context parity.
