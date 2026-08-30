# Product Strategy: Distributed Session Scalability (Stateless Architecture)

## Strategic Context

The **Sales Data Analysis Agent** currently manages conversational contexts (sessions) locally within the application's RAM (`SessionMemoryAdapter`). While highly performant for a single-node deployment, this stateful design creates a critical bottleneck for High Availability (HA) and Horizontal Scalability. As we prepare to deploy the application into a Kubernetes orchestration environment (specifically K3s) to handle increased enterprise traffic, we must transition to a stateless architecture.

If we run multiple replicas of the application without a centralized session store, users will experience "context amnesia" if their requests are routed to different pods by the load balancer, and all active sessions will be lost during pod restarts or scaling events. The strategic objective is to decouple conversational state from the application compute nodes, enabling infinite horizontal scaling and robust fault tolerance.

## Market & Competitor Analysis

In the modern Cloud-Native ecosystem, adhering to the **12-Factor App methodology** is the gold standard.

- **Stateless Processes:** Enterprise applications run as stateless processes, offloading all state to backing services.
- **In-Memory Datastores:** For low-latency conversational AI (where context must be fetched instantly before LLM generation), **Redis** is the industry standard. It provides sub-millisecond read/write speeds, essential for maintaining the "instant" chat feel.
- **Orchestration:** Lightweight Kubernetes distributions like **K3s** are increasingly favored for scalable, edge-ready, and resource-efficient infrastructure deployments.

## Ideation Results

**1. Idea Name: Redis-Backed Distributed Sessions on K3s**

- **Problem Statement:** In-memory session storage prevents horizontal scaling and causes data loss on pod restarts.
- **Proposed Solution:** Implement a distributed session architecture.
  1. Introduce **Redis** as the centralized state store.
  2. Create a `RedisSessionAdapter` in the codebase to fetch and save LangChain message histories.
  3. Deploy the infrastructure using **K3s**, featuring a Redis deployment and the Application Deployment configured with 2+ replicas.
- **Inspiration/Evidence:** Industry-standard architectural pattern for scalable microservices.

**2. Idea Name: Sticky Sessions (Session Affinity) at Load Balancer**

- **Problem Statement:** Need to route users to the container holding their specific session memory.
- **Proposed Solution:** Configure the K3s Ingress/Load Balancer to use "Sticky Sessions" based on cookies or IP, ensuring a user always hits the same pod.
- **Inspiration/Evidence:** Legacy approach used before distributed caches became ubiquitous.

**3. Idea Name: Relational Database Session Store (PostgreSQL)**

- **Problem Statement:** Need a centralized place to store chat history.
- **Proposed Solution:** Store the LangChain history in a standard SQL database like PostgreSQL alongside other relational data.
- **Inspiration/Evidence:** Common for monolithic applications where caching layers are not yet introduced.

## Prioritization Matrix

| Idea | Business Value (1-5) | User Impact (1-5) | Strategic Alignment (1-5) | Effort (1-5, lower=better) | Risk (1-5, lower=better) | Weighted Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Redis-Backed Distributed Sessions** | 5 | 5 | 5 | 3 | 4 | **22** |
| Relational Database Session Store | 4 | 4 | 4 | 3 | 3 | **18** |
| Sticky Sessions at Load Balancer | 3 | 2 | 2 | 4 | 2 | **13** |

*Note: Effort and Risk are inverted for scoring (lower effort/risk = higher score).*

## Recommendations

**Top Recommendation: Implement Redis-Backed Distributed Sessions on K3s**

We must migrate to a stateless application tier by centralizing session context in Redis. This unlocks seamless horizontal scaling via K3s and ensures conversation durability across pod lifecycles.

- **Recommended Sequencing & Scope:**
  1. **Application Code Modification:** Develop a `RedisSessionAdapter` (implementing the outbound port) utilizing LangChain's native Redis integration to read/write chat history using the `session_id`. Inject this adapter via `.env` configuration (e.g., `SESSION_STORE=redis`, `REDIS_URL=redis://...`).
  2. **Infrastructure Definition (K3s YAMLs):** Create the Kubernetes manifests to define the complete scalable environment:
     - `redis-deployment.yaml` & `redis-service.yaml` (The centralized cache).
     - `app-deployment.yaml` (Configured with `replicas: 2` and environment variables pointing to the Redis service).
     - `app-service.yaml` (To balance traffic between the two application pods).
- **Dependencies:** The application must gracefully handle connection pooling to Redis. The Docker image (`juliosilvacwb/sales-agent:latest`) must include the necessary Redis client libraries (e.g., `redis` python package).
- **Validation Suggestions:** Deploy the K3s YAMLs locally. Start a chat session, manually delete one of the application pods (`kubectl delete pod`), and send a follow-up message to verify the context is seamlessly retrieved by the surviving replica.

## Parking Lot

- **Relational Database Session Store:** Slower than Redis and adds unnecessary I/O load to the primary database. Might be useful later for long-term historical cold-storage of chats, but not for active session caching.
- **Sticky Sessions:** High risk of uneven load distribution (hot pods) and does not solve the problem of data loss when a pod crashes. Discarded as a primary solution.
