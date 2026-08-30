# TEST004-distributed-session-scalability — Test Coverage Specification

> **Source Task:** [T004-distributed-session-scalability.md](../architecture/T004-distributed-session-scalability.md)  
> **PRD Reference:** [R004-distributed-session-scalability.md](../business-requirements/R004-distributed-session-scalability.md)

## Coverage Overview

Esta especificação detalha a análise forense de cobertura de testes unitários e de integração para a transição do Sales Data Analysis Agent para uma arquitetura distribuída e completamente stateless (`T004-distributed-session-scalability.md` / `R004-distributed-session-scalability.md`). A arquitetura desacoplou o estado conversacional em memória para um armazenamento centralizado Redis com TTL e namespacing seguro, viabilizando escalabilidade horizontal multi-réplica em K3s/Kubernetes com continuidade de contexto entre pods e reinicializações.

- **Status Geral de Cobertura:** 100% de cobertura lógica e branch coverage mapeada para todas as 11 tasks da especificação T004.
- **Pirâmide de Testes:**
  - **Unitários (Domínio Puro):** Testes de imutabilidade, regex de validação e nomes de chaves no `SessionContext`, e hierarquia de exceções em `src/domain/exception/session_exceptions.py`.
  - **Unitários (Portas e Casos de Uso):** Testes de orquestração do `WebChatApplicationService` garantindo injeção desacoplada de histórico, sanitização de erros e execução stateless.
  - **Unitários (Adaptadores de Persistência):** Testes do `SessionMemoryAdapter` (política LRU, concorrência e limpeza) e `RedisSessionAdapter` (serialização JSON, connection pool, TTL e tratamento de falhas de rede).
  - **Unitários (Fábrica e Injeção de Dependência):** Testes da `SessionFactory` e lifecycle de DI no `chat_controller`.
  - **Validação Declarativa de Infraestrutura:** Testes de conformidade de schema e variáveis dos manifestos K3s (`k8s/`).
  - **Integração (Multi-Replica E2E):** Simulação de round-robin de requisições entre instâncias independentes compartilhando o mesmo Redis Store com 100% de paridade conversacional.

---

## Test Checklist

### Task 001 — [Domain-Model]: Aprimorar SessionContext e Modelos de Domínio

- [COMPLETED] [TEST004-01] [Type: Unit] **test_session_context_instantiation**
  - **Target:** `tests/unit/test_session_context.py` → `test_session_context_instantiation()`
  - **Scenario:** Validar a criação de `SessionContext` com timestamps padrão (`created_at`, `updated_at`), TTL padrão (86400s) e formatação de chave Redis.
  - **Arrange:** Definir `session_id = "test-session-123"`.
  - **Act:** Instanciar `SessionContext(session_id=session_id)`.
  - **Assert:** Campos `session_id`, `created_at`, `updated_at`, `ttl_seconds == 86400` e `redis_key == "sales_agent:session:test-session-123"` são preenchidos corretamente.
  - **Priority:** P0

- [COMPLETED] [TEST004-02] [Type: Unit] **test_session_context_custom_timestamp**
  - **Target:** `tests/unit/test_session_context.py` → `test_session_context_custom_timestamp()`
  - **Scenario:** Garantir que `SessionContext` aceita timestamps customizados para sincronização temporal.
  - **Arrange:** Criar timestamp explícito `datetime(2023, 1, 1, 12, 0, 0)`.
  - **Act:** Instanciar `SessionContext(session_id="test-456", timestamp=custom_ts)`.
  - **Assert:** `ctx.timestamp == custom_ts`.
  - **Priority:** P1

- [COMPLETED] [TEST004-03] [Type: Unit] **test_session_context_immutability**
  - **Target:** `tests/unit/test_session_context.py` → `test_session_context_immutability()`
  - **Scenario:** Garantir imutabilidade (`frozen=True`) para proteger o contexto de mutações colaterais de estado no heap.
  - **Arrange:** Instanciar `SessionContext(session_id="session-immutable")`.
  - **Act:** Tentar alterar `ctx.session_id = "new-id"`.
  - **Assert:** Lança `dataclasses.FrozenInstanceError`.
  - **Priority:** P1

- [COMPLETED] [TEST004-04] [Type: Unit] **test_session_context_validation_empty**
  - **Target:** `tests/unit/test_session_context.py` → `test_session_context_validation_empty()`
  - **Scenario:** Validar que `session_id` vazio é rejeitado pelo domínio.
  - **Arrange:** Definir `session_id = ""`.
  - **Act:** Tentar instanciar `SessionContext(session_id="")`.
  - **Assert:** Lança `InvalidSessionIdError`.
  - **Priority:** P0

- [COMPLETED] [TEST004-05] [Type: Unit] **test_session_context_validation_invalid_characters**
  - **Target:** `tests/unit/test_session_context.py` → `test_session_context_validation_invalid_characters()`
  - **Scenario:** Proteger contra injeção de comandos e caracteres ilegais usando validação estrita por regex (`^[a-zA-Z0-9_-]+$`).
  - **Arrange:** Preparar strings maliciosas como `"session;DROP TABLE sales;--"` e strings com espaços `"session with spaces"`.
  - **Act:** Tentar validar e instanciar `SessionContext` com cada entrada.
  - **Assert:** Lança `InvalidSessionIdError` em ambos os casos.
  - **Priority:** P0

- [COMPLETED] [TEST004-06] [Type: Unit] **test_session_context_validation_too_long**
  - **Target:** `tests/unit/test_session_context.py` → `test_session_context_validation_too_long()`
  - **Scenario:** Prevenir ataques de exaustão de memória limitando o comprimento máximo de `session_id` a 128 caracteres.
  - **Arrange:** Gerar string com 129 caracteres (`"a" * 129`).
  - **Act:** Tentar instanciar `SessionContext`.
  - **Assert:** Lança `InvalidSessionIdError`.
  - **Priority:** P1

- [COMPLETED] [TEST004-07] [Type: Unit] **test_format_redis_key**
  - **Target:** `tests/unit/test_session_context.py` → `test_format_redis_key()`
  - **Scenario:** Validar método estático de formatação e namespacing de chave Redis.
  - **Arrange:** Definir `session_id = "sess_999"`.
  - **Act:** Executar `SessionContext.format_redis_key(session_id)`.
  - **Assert:** Retorna `"sales_agent:session:sess_999"`.
  - **Priority:** P0

---

### Task 002 — [Domain-Exception]: Criar Exceções de Domínio de Sessão

- [COMPLETED] [TEST004-08] [Type: Unit] **test_session_domain_error_hierarchy**
  - **Target:** `tests/unit/test_session_exceptions.py` → `test_session_domain_error_hierarchy()`
  - **Scenario:** Validar que todas as exceções de sessão herdam da raiz `SessionDomainError`.
  - **Arrange:** Carregar classes `InvalidSessionIdError`, `SessionStorageError` e `SessionConnectionError`.
  - **Act:** Verificar herança via `issubclass`.
  - **Assert:** `InvalidSessionIdError` e `SessionStorageError` herdam de `SessionDomainError`; `SessionConnectionError` herda de `SessionStorageError`.
  - **Priority:** P0

- [COMPLETED] [TEST004-09] [Type: Unit] **test_invalid_session_id_error_message**
  - **Target:** `tests/unit/test_session_exceptions.py` → `test_invalid_session_id_error_message()`
  - **Scenario:** Garantir que `InvalidSessionIdError` formata mensagem detalhando o ID rejeitado e a causa.
  - **Arrange:** Instanciar `InvalidSessionIdError("bad session id!", "Contains spaces")`.
  - **Act:** Inspecionar `str(err)`, `err.session_id` e `err.reason`.
  - **Assert:** Mensagem contém o identificador e a razão informados.
  - **Priority:** P1

- [COMPLETED] [TEST004-10] [Type: Unit] **test_session_connection_error_instantiation**
  - **Target:** `tests/unit/test_session_exceptions.py` → `test_session_connection_error_instantiation()`
  - **Scenario:** Validar instanciação de erro de conexão com mensagem descritiva.
  - **Arrange:** Instanciar `SessionConnectionError("Redis host unreachable on port 6379")`.
  - **Act:** Inspecionar mensagem e tipo de erro.
  - **Assert:** `isinstance(err, SessionStorageError)` e mensagem preservada.
  - **Priority:** P1

---

### Task 003 — [Port-Out]: Definir Interface SessionStorePort

- [COMPLETED] [TEST004-11] [Type: Unit] **test_session_store_port_contract**
  - **Target:** `src/application/port/outbound/session_store_port.py` → `SessionStorePort`
  - **Scenario:** Validar que a porta define a assinatura abstrata obrigatória para persistência de sessões sem vazamento de infraestrutura.
  - **Arrange:** Inspecionar métodos abstratos de `SessionStorePort`.
  - **Act:** Verificar declaração de `get_history(session_id: str) -> BaseChatMessageHistory`, `save_history(session_id: str, history: BaseChatMessageHistory) -> None`, `clear_history(session_id: str) -> None` e `exists(session_id: str) -> bool`.
  - **Assert:** Métodos são abstratos (`@abstractmethod`) exigindo implementação pelos adaptadores.
  - **Priority:** P0

---

### Task 004 — [UseCase]: Refatorar WebChatApplicationService para Ser Stateless

- [COMPLETED] [TEST004-12] [Type: Unit] **test_process_chat_message_with_session_store**
  - **Target:** `tests/unit/test_web_chat_application_service.py` → `test_process_chat_message_with_session_store()`
  - **Scenario:** Validar fluxo completo: busca histórico na porta de sessão, repassa ao SalesAgent, anexa resposta e persiste histórico atualizado.
  - **Arrange:** Configurar mocks de `SalesAgent` e `SessionStorePort` com `InMemoryChatMessageHistory`.
  - **Act:** Executar `WebChatApplicationService.process_chat_message(ChatRequestDTO(message="Hello", session_id="session-1"))`.
  - **Assert:** `mock_session_store.get_history.assert_called_once_with("session-1")`, `mock_agent.ask.assert_called_once()`, `mock_session_store.save_history.assert_called_once()`, e histórico contém 2 mensagens (`HumanMessage` e `AIMessage`).
  - **Priority:** P0

- [COMPLETED] [TEST004-13] [Type: Unit] **test_process_chat_message_multi_turn_stateless**
  - **Target:** `tests/unit/test_web_chat_application_service.py` → `test_process_chat_message_multi_turn_stateless()`
  - **Scenario:** Validar continuidade conversacional em múltiplos turnos utilizando instâncias de agente independentes.
  - **Arrange:** Inicializar `mock_history` com mensagens de turnos anteriores e mock de agente.
  - **Act:** Executar `process_chat_message` para a pergunta de acompanhamento.
  - **Assert:** `mock_agent.ask` recebe o histórico prévio completo no parâmetro `chat_history`, e o histórico salvo acumula todas as mensagens.
  - **Priority:** P0

- [COMPLETED] [TEST004-14] [Type: Unit] **test_process_chat_message_error_handling**
  - **Target:** `tests/unit/test_web_chat_application_service.py` → `test_process_chat_message_error_handling()`
  - **Scenario:** Garantir que exceções internas durante o processamento são sanitizadas para não expor stack traces ou dados sensíveis ao usuário.
  - **Arrange:** Configurar mock do agente para lançar `Exception("Internal database crash: connection pool exhausted")`.
  - **Act:** Executar `process_chat_message`.
  - **Assert:** `response.status == "error"` e `response.response` contém mensagem amigável sanitizada sem referências a detalhes internos.
  - **Priority:** P0

- [COMPLETED] [TEST004-15] [Type: Unit] **test_process_chat_message_invalid_session_id**
  - **Target:** `tests/unit/test_web_chat_application_service.py` → `test_process_chat_message_invalid_session_id()`
  - **Scenario:** Validar rejeição imediata com resposta amigável de erro quando `session_id` violar regras de formato.
  - **Arrange:** Instanciar serviço com mock de agent factory.
  - **Act:** Submeter requisição com `session_id` inválido.
  - **Assert:** Retorna `ChatResponseDTO(status="error")` e nenhuma instância de agente ou consulta a banco é executada.
  - **Priority:** P0

---

### Task 005 — [Adapter-Persistence]: Refatorar SessionMemoryAdapter

- [COMPLETED] [TEST004-16] [Type: Unit] **test_memory_adapter_get_and_save_history**
  - **Target:** `tests/unit/adapter/test_session_memory_adapter.py` → `test_memory_adapter_get_and_save_history()`
  - **Scenario:** Validar operações de leitura, escrita e verificação de existência em memória.
  - **Arrange:** Instanciar `SessionMemoryAdapter(max_sessions=10)`.
  - **Act:** Chamar `get_history("test-session-mem")`, adicionar mensagens de usuário e IA, salvar com `save_history()` e consultar `exists()`.
  - **Assert:** `exists()` retorna `True` e `get_history()` retorna exatamente as mensagens salvas.
  - **Priority:** P0

- [COMPLETED] [TEST004-17] [Type: Unit] **test_memory_adapter_clear_history**
  - **Target:** `tests/unit/adapter/test_session_memory_adapter.py` → `test_memory_adapter_clear_history()`
  - **Scenario:** Validar remoção explícita de sessão do cache em memória.
  - **Arrange:** Salvar histórico para `"to-be-deleted"`.
  - **Act:** Executar `adapter.clear_history("to-be-deleted")`.
  - **Assert:** `adapter.exists("to-be-deleted") is False`.
  - **Priority:** P1

- [COMPLETED] [TEST004-18] [Type: Unit] **test_memory_adapter_lru_eviction**
  - **Target:** `tests/unit/adapter/test_session_memory_adapter.py` → `test_memory_adapter_lru_eviction()`
  - **Scenario:** Validar política de despejo LRU (Least Recently Used) quando a capacidade limite é atingida.
  - **Arrange:** Instanciar `SessionMemoryAdapter(max_sessions=2)` e adicionar `s1` e `s2`.
  - **Act:** Acessar `s1` (tornando `s2` o mais antigo) e adicionar `s3`.
  - **Assert:** `s1` e `s3` permanecem no cache; `s2` é removido por despejo LRU.
  - **Priority:** P0

---

### Task 006 — [Adapter-Persistence]: Implementar RedisSessionAdapter

- [COMPLETED] [TEST004-19] [Type: Unit] **test_redis_session_adapter_get_history_empty**
  - **Target:** `tests/unit/adapter/test_redis_session_adapter.py` → `test_redis_session_adapter_get_history_empty()`
  - **Scenario:** Validar que ao consultar sessão inexistente no Redis é retornado histórico vazio sem exceções.
  - **Arrange:** Mockar `redis_client.get` retornando `None`.
  - **Act:** Executar `adapter.get_history("session_1")`.
  - **Assert:** Retorna `InMemoryChatMessageHistory` com 0 mensagens e busca chave com namespace `"sales_agent:session:session_1"`.
  - **Priority:** P0

- [COMPLETED] [TEST004-20] [Type: Unit] **test_redis_session_adapter_save_and_get_history**
  - **Target:** `tests/unit/adapter/test_redis_session_adapter.py` → `test_redis_session_adapter_save_and_get_history()`
  - **Scenario:** Validar serialização JSON de mensagens, armazenamento com parâmetro `ex` (TTL em segundos), e desserialização correta de `HumanMessage` e `AIMessage`.
  - **Arrange:** Configurar `mock_client` gravando payloads em dicionário em memória com `ttl_seconds=3600`.
  - **Act:** Salvar histórico com mensagem de usuário e resposta de IA via `save_history()`, em seguida executar `get_history()`.
  - **Assert:** `mock_client.set` chamado com chave namespaced e `ex=3600`; mensagens recuperadas preservam conteúdo e tipos intactos.
  - **Priority:** P0

- [COMPLETED] [TEST004-21] [Type: Unit] **test_redis_session_adapter_clear_and_exists**
  - **Target:** `tests/unit/adapter/test_redis_session_adapter.py` → `test_redis_session_adapter_clear_and_exists()`
  - **Scenario:** Validar métodos `exists()` e `clear_history()` direcionados à chave namespaced do Redis.
  - **Arrange:** Configurar mock de `redis_client.exists` e `redis_client.delete`.
  - **Act:** Invocar `exists("sess_exists")` e `clear_history("sess_exists")`.
  - **Assert:** `mock_client.exists` e `mock_client.delete` chamados com `"sales_agent:session:sess_exists"`.
  - **Priority:** P1

- [COMPLETED] [TEST004-22] [Type: Unit] **test_redis_session_adapter_connection_error_handling**
  - **Target:** `tests/unit/adapter/test_redis_session_adapter.py` → `test_redis_session_adapter_connection_error_handling()`
  - **Scenario:** Validar conversão de erros de rede nativos do Redis (`redis.ConnectionError`, `redis.TimeoutError`) para `SessionConnectionError` do domínio.
  - **Arrange:** Configurar `mock_client.get` lançando `redis.ConnectionError("Connection refused")`.
  - **Act:** Executar `adapter.get_history("sess_err")`.
  - **Assert:** Lança `SessionConnectionError`.
  - **Priority:** P0

- [COMPLETED] [TEST004-23] [Type: Unit] **test_redis_session_adapter_corrupt_json_storage_error**
  - **Target:** `tests/unit/adapter/test_redis_session_adapter.py` → `test_redis_session_adapter_corrupt_json_storage_error()`
  - **Scenario:** Validar resiliência e lançamento de `SessionStorageError` quando payload retornado do Redis for JSON inválido ou corrompido.
  - **Arrange:** Configurar `mock_client.get` retornando string inválida `"invalid-non-json-data"`.
  - **Act:** Executar `adapter.get_history("sess_corrupt")`.
  - **Assert:** Lança `SessionStorageError`.
  - **Priority:** P1

---

### Task 007 — [Adapter-Infra]: Implementar SessionFactory

- [COMPLETED] [TEST004-24] [Type: Unit] **test_session_factory_default_memory**
  - **Target:** `tests/unit/adapter/test_session_factory.py` → `test_session_factory_default_memory()`
  - **Scenario:** Validar fallback para `SessionMemoryAdapter` quando a variável de ambiente `SESSION_STORE` não estiver definida ou for `"memory"`.
  - **Arrange:** Resetar singleton e limpar variáveis de ambiente via `patch.dict`.
  - **Act:** Executar `SessionFactory.get_session_store(force_refresh=True)`.
  - **Assert:** Retorna instância de `SessionMemoryAdapter`.
  - **Priority:** P0

- [COMPLETED] [TEST004-25] [Type: Unit] **test_session_factory_redis_provider**
  - **Target:** `tests/unit/adapter/test_session_factory.py` → `test_session_factory_redis_provider()`
  - **Scenario:** Validar instanciação de `RedisSessionAdapter` quando `SESSION_STORE=redis`, parseando `REDIS_URL` e `SESSION_TTL_SECONDS`.
  - **Arrange:** Definir ambiente com `SESSION_STORE=redis`, `REDIS_URL=redis://custom-host:6379/1` e `SESSION_TTL_SECONDS=7200`. Mockar `redis.from_url`.
  - **Act:** Executar `SessionFactory.get_session_store(force_refresh=True)`.
  - **Assert:** Retorna `RedisSessionAdapter` com `_ttl_seconds == 7200` e `_redis_url == "redis://custom-host:6379/1"`.
  - **Priority:** P0

---

### Task 008 — [Adapter-Web]: Atualizar chat_controller e Injeção de Dependência

- [COMPLETED] [TEST004-26] [Type: Unit] **test_process_chat_controller_endpoint**
  - **Target:** `tests/unit/adapter/inbound/web/test_chat_controller.py` → `test_process_chat()`
  - **Scenario:** Validar que endpoint HTTP POST `/chat` recebe requisição com `session_id`, orquestra via caso de uso e retorna HTTP 200 com payload estruturado.
  - **Arrange:** Configurar FastAPI TestClient com override de `get_web_chat_use_case_singleton`.
  - **Act:** Postar payload `{"message": "hello", "session_id": "1234"}` em `/chat`.
  - **Assert:** Status HTTP 200 e resposta JSON com `status == "success"`.
  - **Priority:** P0

- [COMPLETED] [TEST004-27] [Type: Unit] **test_process_chat_endpoint_validation_error**
  - **Target:** `tests/unit/adapter/inbound/web/test_chat_controller.py` → `test_process_chat_endpoint_validation_error()`
  - **Scenario:** Validar resposta HTTP 422 Unprocessable Entity quando payload enviado não contiver os campos obrigatórios.
  - **Arrange:** Criar payload com campo inválido `{"invalid_field": 123}`.
  - **Act:** Postar payload em `/chat`.
  - **Assert:** Status HTTP 422 e detalhamento do erro de validação retornado pelo FastAPI.
  - **Priority:** P1

- [COMPLETED] [TEST004-28] [Type: Unit] **test_get_web_chat_use_case_singleton_lifecycle**
  - **Target:** `tests/unit/adapter/inbound/web/test_chat_controller.py` → `test_get_web_chat_use_case_singleton_lifecycle()`
  - **Scenario:** Validar ciclo de vida singleton do caso de uso injetado no controller.
  - **Arrange:** Resetar `chat_controller._app_service_instance = None`.
  - **Act:** Invocar `get_web_chat_use_case_singleton()` consecutivamente.
  - **Assert:** Ambas as invocações retornam a mesma referência de `WebChatApplicationService`.
  - **Priority:** P1

---

### Task 009 — [Adapter-Infra]: Atualizar requirements.txt com Dependência Redis

- [COMPLETED] [TEST004-29] [Type: Unit] **test_requirements_redis_dependency**
  - **Target:** `requirements.txt`
  - **Scenario:** Garantir que o driver oficial `redis>=5.0.0` está declarado no arquivo de dependências do projeto.
  - **Arrange:** Ler `requirements.txt`.
  - **Act:** Buscar declaração do pacote `redis`.
  - **Assert:** `redis>=5.0.0` está presente e instalado no ambiente virtual.
  - **Priority:** P0

---

### Task 010 — [Adapter-Infra]: Criar Manifestos Declarativos K3s

- [COMPLETED] [TEST004-30] [Type: Integration] **test_k8s_manifests_declarative_syntax**
  - **Target:** `k8s/redis-deployment.yaml`, `k8s/redis-service.yaml`, `k8s/app-deployment.yaml`, `k8s/app-service.yaml`
  - **Scenario:** Validar sintaxe YAML, schemas Kubernetes v1 e configuração de multi-réplicas (`replicas: 2`), `livenessProbe`, `readinessProbe` e variáveis de ambiente (`SESSION_STORE=redis`, `REDIS_URL=redis://redis-service:6379/0`).
  - **Arrange:** Analisar arquivos declarativos do diretório `k8s/`.
  - **Act:** Validar definições de Pods, Deployments, ClusterIP Services e portas de comunicação (6379 para Redis e 8000 para Web Chat).
  - **Assert:** Manifestos conformes com o padrão Kubernetes, sem portas ou nomes conflitantes, e apontamento correto do service DNS interno.
  - **Priority:** P0

---

### Task 011 — [Test-Integration]: Testes de Integração Multi-Réplica Distribuída

- [COMPLETED] [TEST004-31] [Type: Integration] **test_distributed_multi_replica_session_continuity**
  - **Target:** `tests/integration/test_distributed_session_integration.py` → `test_distributed_multi_replica_session_continuity()`
  - **Scenario:** Simular arquitetura multi-pod em K3s onde o Turno 1 é atendido pela Réplica A e o Turno 2 é atendido pela Réplica B sob o mesmo `session_id`, garantindo 100% de paridade e continuidade de contexto conversacional via Redis Store.
  - **Arrange:** Configurar repositório simulado compartilhado no `RedisSessionAdapter` com `ttl_seconds=86400`. Instanciar dois nós de aplicação independentes (`app_service_pod_a` e `app_service_pod_b`).
  - **Act:**
    1. Enviar mensagem de Turno 1 ao Pod A ("Quais os produtos mais vendidos?").
    2. Enviar mensagem de Turno 2 ao Pod B ("E qual foi a receita somada deles?").
  - **Assert:**
    - Turno 1 persiste mensagem de usuário e IA na chave `sales_agent:session:<session_id>`.
    - Pod B recupera perfeitamente o histórico acumulado do Pod A via Redis e injeta no agente.
    - Histórico final consolidado no Redis contém as 4 mensagens dos dois turnos sem perda de contexto.
  - **Priority:** P0
