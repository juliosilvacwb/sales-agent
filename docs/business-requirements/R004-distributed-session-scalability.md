# PRD: Distributed Session Scalability (Stateless Architecture)

## Summary

Origin: [PS004-distributed-session-scalability.md](file:///c:/Code/challenge_ai_engineer/docs/product-strategy/PS004-distributed-session-scalability.md), Recommendation: Top Recommendation (Redis-Backed Distributed Sessions on K3s).

The Sales Data Analysis Agent currently manages conversational context in local application memory (`SessionMemoryAdapter`). While sufficient for single-instance development, this stateful design creates a critical bottleneck for horizontal scalability, zero-downtime rolling deployments, and high availability (HA). When multiple application replicas run behind a load balancer in an orchestrated environment like K3s/Kubernetes, requests routed across different pods cause conversational context loss ("context amnesia"), and pod restarts immediately erase all active sessions.

This PRD specifies the transition of the application to a fully stateless compute model adhering to the 12-Factor App methodology. By decoupling conversational memory into a centralized, low-latency Redis session store and orchestrating the workload with K3s manifests (2+ application replicas and a dedicated Redis backing service), the system guarantees seamless multi-turn conversation durability, fault tolerance, and linear horizontal scalability.

## Functional Requirements

- **PRD01 (Pluggable Session Storage Provider):** The system must support pluggable session persistence providers configurable via environment variables (e.g., `SESSION_STORE=redis` or `SESSION_STORE=memory`), defaulting to memory for local standalone development.
- **PRD02 (Distributed Redis Session Adapter):** The system must implement an outbound Redis session adapter (`RedisSessionAdapter`) that reads and writes LangChain conversational histories directly to and from Redis using the client's `session_id`.
- **PRD03 (Compute Tier Statelessness):** The application compute layer must not store persistent conversational state in process memory, enabling any application replica in the cluster to handle any turn of a conversation interchangeably.
- **PRD04 (Configurable Session TTL & Lifecycle):** The session persistence mechanism must enforce a configurable Time-To-Live (TTL) on Redis keys (e.g., `SESSION_TTL_SECONDS=86400`) to automatically purge stale conversational histories and prevent memory exhaustion.
- **PRD05 (Declarative K3s/Kubernetes Manifests):** The project must provide production-ready declarative manifests (`k8s/`) specifying:
  - Redis Deployment and Service (backing store).
  - Sales Agent Application Deployment with 2 or more replicas, resource requests/limits, and health probes (`livenessProbe`, `readinessProbe`).
  - Application Service configured to balance traffic evenly across application pods.
  - ConfigMaps / Secret templates for Redis connection parameters (`REDIS_URL`).

## Non-Functional Requirements

- **Performance & Latency:** Redis session read and write operations must complete in sub-5ms latency, keeping overall API chat response times within established SLA benchmarks.
- **High Availability & Scalability:** The system must support horizontal auto-scaling and manual scaling of application pods without disruption to active conversational flows.
- **Resilience & Fault Tolerance:** If an application pod crashes or is terminated during an active multi-turn session, subsequent requests from the user must transparently retrieve the full historical context from Redis without data loss.
- **Architectural Decoupling (Hexagonal Architecture):** The Redis integration must strictly implement an outbound port interface, ensuring core domain logic and application services remain decoupled from Redis-specific libraries.
- **Security & Key Isolation:** Redis keys must use isolated namespaces (e.g., `sales_agent:session:{session_id}`) and validate `session_id` strings to prevent key-injection vulnerabilities.

## Business Rules

- **BR01 (Context Durability Across Replicas):** Consecutive messages within the same `session_id` must maintain 100% conversational memory consistency regardless of which pod replica serves the request.
- **BR02 (Zero-Config Development Fallback):** When `SESSION_STORE=memory` is active or Redis configuration is omitted, the application must seamlessly fall back to local in-memory storage for developer convenience.
- **BR03 (Key Isolation & Format):** All session keys written to Redis must adhere to the standardized prefix schema `sales_agent:session:<session_id>` with automated TTL renewal upon active writes.
- **BR04 (Graceful Connection Degradation):** In case of transient Redis connection dropouts, the system must log structured diagnostic errors and handle retries cleanly, avoiding unhandled 500 crashes.

## Critical Data (Conceptual)

- **Session Identifier (`session_id`):** Unique alphanumeric token identifying the conversational thread.
- **Conversational Messages History:** Serialized sequence of chat messages (Human, AI, Tool execution results, and metadata).
- **Session Expiration Metadata (`ttl`):** Expiration duration in seconds defining the lifetime of an inactive session.
- **Cluster Configuration Parameters:** Storage provider selector (`SESSION_STORE`), Redis connection URI (`REDIS_URL`), and pool connection limits.

## User Flow

### Happy Path (Multi-Replica Distributed Conversation)

1. The client sends a chat request to the K3s cluster endpoint (`POST /chat`) with a `session_id` and query.
2. The K3s Service routes the request to Pod A.
3. Pod A fetches the existing chat history for `session_id` from the centralized Redis service.
4. Pod A executes the agent reasoning loop with DuckDB analytics and generates the response.
5. Pod A updates the chat history in Redis with the new human message and AI response, resetting the TTL timer.
6. Pod A returns the response to the client.
7. The client sends a follow-up query with the same `session_id`.
8. The K3s Service routes the second request to Pod B (a different replica).
9. Pod B fetches the up-to-date conversational history from Redis, retains full context, and produces a coherent contextual response.

### Exception Path 1 (Pod Failover During Active Session)

1. A user conducts a multi-turn conversation on Pod A.
2. Pod A crashes or is terminated (e.g., node drain, rollout upgrade, or OOM event).
3. The client sends the next query with the existing `session_id`.
4. The load balancer routes the request to surviving Pod B or newly spawned Pod C.
5. Pod B connects to Redis, retrieves the intact session history, and answers without context amnesia.

### Exception Path 2 (Redis Unavailability / Connection Error)

1. The client sends a request while Redis is temporarily unreachable or undergoing maintenance.
2. The application captures the connection timeout or failure gracefully.
3. The system logs a structured error with connection diagnostics and returns a polite error message to the client without exposing internal stack traces.

### Exception Path 3 (Session Inactivity Expiration)

1. A user leaves a session inactive for longer than the configured TTL (e.g., > 24 hours).
2. Redis automatically purges the expired key.
3. Upon a new incoming request with that `session_id`, the system initializes a fresh conversation context without errors.

## Acceptance Criteria

| ID | Criterion | Validation Method |
| --- | --- | --- |
| AC01 | Application dynamically switches between `memory` and `redis` session adapters based on environment configuration (`SESSION_STORE`). | Unit and configuration loading tests. |
| AC02 | `RedisSessionAdapter` correctly writes and retrieves serialized LangChain message histories by `session_id`. | Integration tests against a live/testcontainer Redis instance. |
| AC03 | Consecutive requests for the same `session_id` dispatched across different application worker processes retain complete conversational context. | Multi-process/Multi-replica integration test. |
| AC04 | Redis session keys are created with the standard prefix and respect the configured `ttl_seconds` expiration. | Verification of Redis key TTL and auto-eviction during integration test. |
| AC05 | Pod termination test (Chaos/Kill test) demonstrates zero session loss on surviving replicas in a K3s cluster. | End-to-end verification in K3s test environment with pod deletion. |
| AC06 | K3s manifests (`k8s/redis-*.yaml`, `k8s/app-*.yaml`) validate successfully with `kubectl apply --dry-run=client` and deploy clean pods with health probes. | Manifest schema validation and deployment smoke test. |
