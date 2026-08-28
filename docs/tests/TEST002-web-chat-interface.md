# TEST002-web-chat-interface — Test Coverage Specification

> **Source Task:** [T002-web-chat-interface.md](../architecture/T002-web-chat-interface.md)  
> **Security Audit:** [S002-web-chat-interface.md](../security/S002-web-chat-interface.md)

## Coverage Overview

Esta especificação detalha a avaliação e o plano forense de cobertura de testes unitários e de integração para a interface web de chat do Sales Agent (`T002-web-chat-interface.md` / `R002-web-chat-interface.md`). A suíte valida a integridade da Arquitetura Hexagonal, abrangendo o modelo de contexto de sessão, DTOs de transporte, contratos de portas de entrada, serviço de aplicação orquestrador, adaptadores FastAPI (rotas, CORS, static files), adaptadores de memória conversacional, contratos frontend e cenários de integração End-to-End.

- **Status Geral de Execução:** Avaliação de cobertura realizada sobre as 10 tasks da especificação T002.
- **Pirâmide de Testes:** Cobertura balanceada entre Unitária (isolamento de domínio, serialização Pydantic, ciclo de vida de sessões, mocks de portas e adaptadores) e Integração (FastAPI TestClient, persistência de memória conversacional e tratamento de exceções).

---

## Test Checklist

### Task 001 — [Domain-Model]: Criar Value Object SessionContext

- [COMPLETED] [TEST002-01] [Type: Unit] **test_session_context_instantiation**
  - **Target:** `tests/unit/test_session_context.py` → `test_session_context_instantiation()`
  - **Scenario:** Validar instanciação básica do Value Object `SessionContext` com geração automática de timestamp UTC.
  - **Arrange:** Definir `session_id = "test-session-123"`.
  - **Act:** Instanciar `SessionContext(session_id=session_id)`.
  - **Assert:** `ctx.session_id == "test-session-123"` e `isinstance(ctx.timestamp, datetime)` é `True`.
  - **Priority:** P0

- [COMPLETED] [TEST002-02] [Type: Unit] **test_session_context_custom_timestamp**
  - **Target:** `tests/unit/test_session_context.py` → `test_session_context_custom_timestamp()`
  - **Scenario:** Validar instanciação do `SessionContext` aceitando timestamp customizado explícito.
  - **Arrange:** Definir `custom_ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)` e `session_id = "test-session-456"`.
  - **Act:** Instanciar `SessionContext(session_id=session_id, timestamp=custom_ts)`.
  - **Assert:** `ctx.timestamp == custom_ts` e `ctx.session_id == session_id`.
  - **Priority:** P1

- [COMPLETED] [TEST002-03] [Type: Unit] **test_session_context_immutability**
  - **Target:** `tests/unit/test_session_context.py` → `test_session_context_immutability()`
  - **Scenario:** Garantir imutabilidade estrita do Value Object (`frozen=True`) impedindo mutações de atributos após criação.
  - **Arrange:** Instanciar `ctx = SessionContext(session_id="session-immutable")`.
  - **Act:** Tentar alterar `ctx.session_id = "new-id"` dentro de bloco de captura de exceção.
  - **Assert:** Lança `FrozenInstanceError` (ou `dataclasses.FrozenInstanceError`).
  - **Priority:** P1

---

### Task 002 — [DTO]: Definir ChatRequestDTO e ChatResponseDTO

- [COMPLETED] [TEST002-04] [Type: Unit] **test_chat_request_dto_valid**
  - **Target:** `tests/unit/test_chat_dto.py` → `test_chat_request_dto_valid()`
  - **Scenario:** Validar criação e serialização do `ChatRequestDTO` com payload completo e válido.
  - **Arrange:** Definir dicionário com `{"message": "Hello", "session_id": "123"}`.
  - **Act:** Instanciar `ChatRequestDTO(**data)`.
  - **Assert:** `req.message == "Hello"` e `req.session_id == "123"`.
  - **Priority:** P0

- [COMPLETED] [TEST002-05] [Type: Unit] **test_chat_response_dto_valid**
  - **Target:** `tests/unit/test_chat_dto.py` → `test_chat_response_dto_valid()`
  - **Scenario:** Validar criação do `ChatResponseDTO` verificando o valor default do campo `status`.
  - **Arrange:** Definir payload `{"response": "Hi there"}`.
  - **Act:** Instanciar `ChatResponseDTO(**data)`.
  - **Assert:** `res.response == "Hi there"` e `res.status == "success"`.
  - **Priority:** P0

- [COMPLETED] [TEST002-06] [Type: Unit] **test_chat_request_dto_missing_fields_validation**
  - **Target:** `tests/unit/test_chat_dto.py` → `test_chat_request_dto_missing_fields_validation()`
  - **Scenario:** Validar que `ChatRequestDTO` rejeita payloads sem `message` ou sem `session_id`.
  - **Arrange:** Criar payloads parciais: `{"message": "Only message"}` e `{"session_id": "Only session"}`.
  - **Act:** Tentar instanciar `ChatRequestDTO` para cada payload.
  - **Assert:** Ambas as chamadas disparam `pydantic.ValidationError`.
  - **Priority:** P1

- [COMPLETED] [TEST002-07] [Type: Unit] **test_chat_response_dto_custom_status_and_missing_response**
  - **Target:** `tests/unit/test_chat_dto.py` → `test_chat_response_dto_custom_status_and_missing_response()`
  - **Scenario:** Validar `ChatResponseDTO` aceitando status de erro customizado e rejeitando payload sem campo `response`.
  - **Arrange:** Definir payload de erro `{"response": "Failure detail", "status": "error"}` e payload vazio `{}`.
  - **Act:** Instanciar DTO com status de erro e tentar instanciar DTO vazio.
  - **Assert:** Instância de erro possui `status == "error"` e tentativa vazia lança `ValidationError`.
  - **Priority:** P1

---

### Task 003 — [Port-In]: Definir WebChatUseCase Interface

- [COMPLETED] [TEST002-08] [Type: Unit] **test_web_chat_use_case_abstract_contract**
  - **Target:** `tests/unit/test_web_chat_use_case.py` → `test_web_chat_use_case_abstract_contract()`
  - **Scenario:** Garantir que `WebChatUseCase` é uma interface abstrata pura e não pode ser instanciada diretamente sem implementar `process_chat_message`.
  - **Arrange:** Importar `WebChatUseCase`.
  - **Act:** Tentar instanciar `WebChatUseCase()` diretamente e instanciar subclasse incompleta.
  - **Assert:** Ambas as tentativas disparam `TypeError: Can't instantiate abstract class`.
  - **Priority:** P1

---

### Task 004 — [UseCase]: Implementar WebChatApplicationService

- [COMPLETED] [TEST002-09] [Type: Unit] **test_process_chat_message_new_session**
  - **Target:** `tests/unit/test_web_chat_application_service.py` → `test_process_chat_message_new_session()`
  - **Scenario:** Processar primeira mensagem de uma sessão nova, invocando a factory do agente e delegando ao método `ask`.
  - **Arrange:** Mock do agente com `ask.return_value = "Agent response"`, mock de factory.
  - **Act:** Executar `service.process_chat_message(ChatRequestDTO(message="Hello", session_id="session-1"))`.
  - **Assert:** Factory chamada uma vez, `ask("Hello")` invocado, retorno com `status="success"` e resposta correta.
  - **Priority:** P0

- [COMPLETED] [TEST002-10] [Type: Unit] **test_process_chat_message_existing_session**
  - **Target:** `tests/unit/test_web_chat_application_service.py` → `test_process_chat_message_existing_session()`
  - **Scenario:** Garantir reuso da instância de agente para múltiplos turnos da mesma sessão sem re-instanciação.
  - **Arrange:** Service instanciado com mock factory e mock agent.
  - **Act:** Enviar requisição 1 e requisição 2 consecutivas com o mesmo `session_id="session-1"`.
  - **Assert:** `mock_factory` chamado exatamente 1 vez e `mock_agent.ask` chamado 2 vezes mantendo a mesma instância.
  - **Priority:** P0

- [COMPLETED] [TEST002-11] [Type: Unit] **test_process_chat_message_error_handling**
  - **Target:** `tests/unit/test_web_chat_application_service.py` → `test_process_chat_message_error_handling()`
  - **Scenario:** Capturar exceção do agente durante `ask` e retornar `ChatResponseDTO` com status de erro e mensagem descritiva.
  - **Arrange:** `mock_agent.ask.side_effect = Exception("Agent internal error")`.
  - **Act:** Executar `service.process_chat_message(ChatRequestDTO(message="Crash", session_id="session-2"))`.
  - **Assert:** Retorno é `ChatResponseDTO(response="Agent internal error", status="error")` sem quebrar o fluxo.
  - **Priority:** P0

- [COMPLETED] [TEST002-12] [Type: Unit] **test_process_chat_message_multiple_independent_sessions**
  - **Target:** `tests/unit/test_web_chat_application_service.py` → `test_process_chat_message_multiple_independent_sessions()`
  - **Scenario:** Validar isolamento estrito de instâncias de agentes entre múltiplos `session_id` concorrentes.
  - **Arrange:** Configurar factory para produzir agentes mock distintos para cada invocação.
  - **Act:** Enviar requisição com `session_id="session-A"` e depois com `session_id="session-B"`.
  - **Assert:** `mock_factory` é chamado 2 vezes, instâncias em `_active_sessions` são distintas e cada agente recebe apenas sua respectiva mensagem.
  - **Priority:** P1

---

### Task 005 — [Config]: Configurar Aplicação FastAPI Base

- [COMPLETED] [TEST002-13] [Type: Unit] **test_health_check**
  - **Target:** `tests/unit/adapter/inbound/web/test_main.py` → `test_health_check()`
  - **Scenario:** Validar endpoint de integridade operacional do servidor FastAPI (`GET /health`).
  - **Arrange:** Instanciar `TestClient(app)`.
  - **Act:** Executar `client.get("/health")`.
  - **Assert:** `status_code == 200` e payload `{"status": "ok"}`.
  - **Priority:** P0

- [COMPLETED] [TEST002-14] [Type: Unit] **test_static_files_and_cors_mount_configuration**
  - **Target:** `tests/unit/adapter/inbound/web/test_main.py` → `test_static_files_and_cors_mount_configuration()`
  - **Scenario:** Validar montagem correta da rota de arquivos estáticos `/static` e configuração dos headers de CORS.
  - **Arrange:** Instanciar `TestClient(app)`.
  - **Act:** Executar `client.options("/chat", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})` e checar rotas registradas no `app.routes`.
  - **Assert:** Rota montada com `name="static"` existe em `app.routes` e resposta OPTIONS retorna headers CORS permitidos.
  - **Priority:** P0

- [COMPLETED] [TEST002-15] [Type: Unit] **test_openapi_schema_endpoint**
  - **Target:** `tests/unit/adapter/inbound/web/test_main.py` → `test_openapi_schema_endpoint()`
  - **Scenario:** Validar geração de documentação OpenAPI/Swagger pelo FastAPI.
  - **Arrange:** Instanciar `TestClient(app)`.
  - **Act:** Executar `client.get("/openapi.json")`.
  - **Assert:** `status_code == 200`, JSON contém `title == "Sales Data Analysis API"` e rota `/chat` documentada.
  - **Priority:** P2

---

### Task 006 — [Adapter-Web]: Implementar ChatRestController

- [COMPLETED] [TEST002-16] [Type: Unit] **test_process_chat_endpoint_success**
  - **Target:** `tests/unit/adapter/inbound/web/test_chat_controller.py` → `test_process_chat()`
  - **Scenario:** Validar chamada HTTP `POST /chat` com resposta de sucesso via injeção de dependência mockada.
  - **Arrange:** `app.dependency_overrides` com mock de `WebChatUseCase` retornando `"echo: hello"`.
  - **Act:** Executar `client.post("/chat", json={"message": "hello", "session_id": "1234"})`.
  - **Assert:** `status_code == 200`, `response.json()["response"] == "echo: hello"` e `status == "success"`.
  - **Priority:** P0

- [COMPLETED] [TEST002-17] [Type: Unit] **test_process_chat_endpoint_validation_error**
  - **Target:** `tests/unit/adapter/inbound/web/test_chat_controller.py` → `test_process_chat_endpoint_validation_error()`
  - **Scenario:** Validar rejeição automática com HTTP 422 ao enviar payload inválido ou sem campos obrigatórios.
  - **Arrange:** Instanciar `TestClient(app)` sem overrides.
  - **Act:** Executar `client.post("/chat", json={"invalid_field": 123})`.
  - **Assert:** `status_code == 422` e detalhes de erro no payload JSON do FastAPI.
  - **Priority:** P1

- [COMPLETED] [TEST002-18] [Type: Unit] **test_get_web_chat_use_case_singleton_lifecycle**
  - **Target:** `tests/unit/adapter/inbound/web/test_chat_controller.py` → `test_get_web_chat_use_case_singleton_lifecycle()`
  - **Scenario:** Validar ciclo de vida e lazy initialization do singleton `get_web_chat_use_case_singleton`.
  - **Arrange:** Resetar `chat_controller._app_service_instance = None`.
  - **Act:** Chamar `get_web_chat_use_case_singleton()` duas vezes.
  - **Assert:** Retorna instância de `WebChatApplicationService` e a segunda chamada retorna exatamente o mesmo objeto (`inst1 is inst2`).
  - **Priority:** P1

---

### Task 007 — [Adapter-Persistence]: Persistência de Memória de Sessão

- [COMPLETED] [TEST002-19] [Type: Unit] **test_get_session_history**
  - **Target:** `tests/unit/adapter/outbound/memory/test_session_memory_adapter.py` → `test_get_session_history()`
  - **Scenario:** Validar recuperação e instanciação de `InMemoryChatMessageHistory` por `session_id`.
  - **Arrange:** Instanciar `SessionMemoryAdapter()`.
  - **Act:** Obter histórico para `session_1` e `session_2`.
  - **Assert:** `history1 is adapter.get_session_history("session_1")` e `history1 is not history2`.
  - **Priority:** P0

- [COMPLETED] [TEST002-20] [Type: Unit] **test_session_memory_adapter_message_persistence_and_isolation**
  - **Target:** `tests/unit/adapter/outbound/memory/test_session_memory_adapter.py` → `test_session_memory_adapter_message_persistence_and_isolation()`
  - **Scenario:** Garantir que mensagens adicionadas ao histórico de uma sessão persistem e não vazam para outras sessões.
  - **Arrange:** Instanciar `SessionMemoryAdapter()`, obter histórias de `sessA` e `sessB`.
  - **Act:** Adicionar `HumanMessage(content="Pergunta A")` e `AIMessage(content="Resposta A")` em `sessA`.
  - **Assert:** Histórico de `sessA` possui 2 mensagens com os conteúdos corretos e histórico de `sessB` permanece vazio com 0 mensagens.
  - **Priority:** P1

---

### Task 008 — [Adapter-Web-Frontend]: Desenvolver index.html e styles.css

- [APPROVED] [TEST002-21] [Type: Unit] **test_frontend_html_structure_and_assets**
  - **Target:** `tests/unit/adapter/inbound/web/test_frontend_static.py` → `test_frontend_html_structure_and_assets()`
  - **Scenario:** Validar presença e estrutura dos arquivos estáticos HTML e CSS no pacote web.
  - **Arrange:** Localizar caminhos de `src/adapter/inbound/web/static/index.html` e `styles.css`.
  - **Act:** Ler conteúdo dos arquivos estáticos.
  - **Assert:** `index.html` contém IDs obrigatórios (`chat-form`, `chat-input`, `chat-messages`, `typing-indicator`, `error-banner`) e CDN do `marked.js`. `styles.css` contém tokens de tema dark e seletores dos componentes.
  - **Priority:** P1

---

### Task 009 — [Adapter-Web-Frontend]: Desenvolver app.js

- [APPROVED] [TEST002-22] [Type: Unit] **test_frontend_app_js_logic_integrity**
  - **Target:** `tests/unit/adapter/inbound/web/test_frontend_static.py` → `test_frontend_app_js_logic_integrity()`
  - **Scenario:** Validar que o script cliente `app.js` implementa os requisitos de segurança e resiliência (XSS protection, crypto session, timeout de 60s).
  - **Arrange:** Ler `src/adapter/inbound/web/static/app.js`.
  - **Act:** Inspecionar padrões de código estático (regex/AST).
  - **Assert:** Script contém lógica de `crypto.randomUUID` (ou fallback), uso de `textContent` para sanitização de input do usuário, `marked.parse` para respostas do bot, `AbortController` e tratamento de erros do Exception Path 1.
  - **Priority:** P1

---

### Task 010 — [Test-Integration]: Implementar End-to-End Test

- [APPROVED] [TEST002-23] [Type: Integration] **test_web_chat_multi_turn_and_session_isolation**
  - **Target:** `tests/integration/test_web_chat.py` → `test_web_chat_flow()`
  - **Scenario:** Validar fluxo completo de chat via FastAPI com retenção de memória conversacional multi-turno e isolamento de sessão.
  - **Arrange:** Mock do agente com retenção de histórico em memória e `TestClient(app)`.
  - **Act:** Enviar turno 1 e turno 2 com `session_id="test-integration-session"`, e turno 3 com `session_id="other-session"`.
  - **Assert:** Turno 1 retorna sucesso; Turno 2 responde acumulando contexto do Turno 1; Turno 3 não possui o contexto da sessão anterior.
  - **Priority:** P0

- [APPROVED] [TEST002-24] [Type: Integration] **test_web_chat_integration_error_response**
  - **Target:** `tests/integration/test_web_chat.py` → `test_web_chat_integration_error_response()`
  - **Scenario:** Validar comportamento da API em cenário de falha operacional do agente durante o fluxo web.
  - **Arrange:** Configurar factory para retornar agente simulado que lança exceção em tempo de execução.
  - **Act:** Enviar requisição `POST /chat` com `{"message": "fail", "session_id": "err-session"}`.
  - **Assert:** Resposta HTTP 200 com payload `{"response": "...", "status": "error"}` e sem quebra da aplicação.
  - **Priority:** P1

---

## Sugestão de Mensagem de Commit

```text
docs(tests): create test coverage specification for T002 web chat interface

- Add TEST002-web-chat-interface.md mapping all 10 tasks from T002 architecture
- Define AAA test checklist covering domain, DTOs, use cases, FastAPI adapters, and E2E integration
- Add back-reference link in T002-web-chat-interface.md
```
