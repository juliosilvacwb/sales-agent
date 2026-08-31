<!-- markdownlint-disable MD013 -->
# TEST013-data-queried-flag — Test Coverage Specification

> **Source Task:** [T013-data-queried-flag.md](../architecture/T013-data-queried-flag.md)  
> **PRD Reference:** [R013-data-queried-flag.md](../business-requirements/R013-data-queried-flag.md)  
> **Security Audit:** [S013-data-queried-flag.md](../security/S013-data-queried-flag.md)

## Coverage Overview

Esta especificação estabelece o plano forense e a matriz de cobertura de testes para a funcionalidade de **Data Queried Flag and Response Grounding** (`T013-data-queried-flag.md` / `R013-data-queried-flag.md`). O objetivo central é assegurar a rastreabilidade e a transparência executiva no Agente de Análise de Vendas, monitorando via LangChain `BaseCallbackHandler` em escopo por requisição (ADR-02) as execuções de ferramentas determinísticas de domínio ou fallback SQL (`DATA_QUERY_TOOLS`), enriquecendo o `ChatResponseDTO` com a flag booleana `data_queried` e renderizando o selo "Dados Verificados" na interface web com isolamento estrito entre turnos conversacionais.

- **Status Geral de Cobertura:** 100% de cobertura lógica, contratos de DTOs, manipuladores de callbacks, interoperabilidade de resultados, serviços de aplicação, adaptadores web e testes de integração de ponta a ponta para todas as 6 tarefas da especificação T013.
- **Pirâmide de Testes:**
  - **Unitários (Contrato de DTOs):** Validação de `ChatResponseDTO` em `src/application/dto/chat_dto.py`, garantindo o valor padrão `data_queried: bool = False`, validação de atribuição explícita `True`, imutabilidade de esquema e compatibilidade de serialização JSON.
  - **Unitários (Callback Interceptor):** Validação de `ToolTrackingCallbackHandler` em `src/adapter/inbound/llm/sales_agent.py`, verificação dos métodos `on_tool_start` e `on_tool_end` para `DATA_QUERY_TOOLS`, filtragem de ferramentas não catalogadas e aferição de overhead de latência estritamente sub-milissegundo (< 0.1ms) (NFR02).
  - **Unitários (Orquestração do Agente e Interoperabilidade):** Validação da classe `AgentResult` (compatibilidade com strings, tuplas e acesso por propriedade) e do método `SalesAgent.ask()`, assegurando instanciação de callback request-scoped e retorno determinístico do flag.
  - **Unitários (Serviço de Aplicação):** Validação de `WebChatApplicationService.process_chat_message()` em `src/application/service/web_chat_application_service.py`, mapeando o resultado do agente para `ChatResponseDTO` e tratando exceções com `data_queried=False`.
  - **Unitários / DOM (Adaptador Web e Acessibilidade):** Inspeção de regras do frontend `src/adapter/inbound/web/static/app.js`, verificando inserção do elemento `.verified-data-badge`, atributos `role="status"` e `aria-label`, e omissão segura em respostas casuais ou erros.
  - **Integração / E2E (Isolamento de Turnos):** Execução de fluxos encadeados em `tests/integration/test_data_queried_flag.py`, validando a alternância entre perguntas analíticas (`data_queried=True`) e cumprimentos casuais (`data_queried=False`) na mesma sessão sem contaminação de estado (PRD04).

---

## Test Checklist

### Task 001 — [Domain-Model]: Update ChatResponseDTO with data_queried

- [COMPLETED] [TEST013-01] [Type: Unit] **test_chat_response_dto_default_data_queried_false**
  - **Target:** `src/application/dto/chat_dto.py` → `ChatResponseDTO`
  - **Scenario:** Validar que uma instância de `ChatResponseDTO` inicializada apenas com a resposta textual assume por padrão `data_queried = False` e `status = "success"`.
  - **Arrange:** Definir payload com texto `"Olá! Como posso ajudar?"`.
  - **Act:** Instanciar `dto = ChatResponseDTO(response="Olá! Como posso ajudar?")`.
  - **Assert:** `dto.data_queried is False` e `dto.status == "success"`.
  - **Priority:** P0

- [COMPLETED] [TEST013-02] [Type: Unit] **test_chat_response_dto_with_data_queried_true**
  - **Target:** `src/application/dto/chat_dto.py` → `ChatResponseDTO`
  - **Scenario:** Validar que `ChatResponseDTO` aceita e armazena corretamente o valor `data_queried = True` vindo de consultas analíticas.
  - **Arrange:** Definir resposta com dados analíticos `"Produto líder: Prod_01"`.
  - **Act:** Instanciar `dto = ChatResponseDTO(response="Produto líder: Prod_01", data_queried=True)`.
  - **Assert:** `dto.data_queried is True` e `dto.response == "Produto líder: Prod_01"`.
  - **Priority:** P0

- [COMPLETED] [TEST013-03] [Type: Unit] **test_chat_response_dto_json_serialization**
  - **Target:** `src/application/dto/chat_dto.py` → `ChatResponseDTO.model_dump()`
  - **Scenario:** Validar que a serialização do DTO para dicionário e JSON transporta a chave `data_queried` com tipo booleano estrito.
  - **Arrange:** Instanciar `dto = ChatResponseDTO(response="OK", data_queried=True)`.
  - **Act:** Executar `data = dto.model_dump()`.
  - **Assert:** `"data_queried" in data` e `isinstance(data["data_queried"], bool)` e `data["data_queried"] is True`.
  - **Priority:** P1

---

### Task 002 — [UseCase]: Implement ToolTrackingCallbackHandler

- [COMPLETED] [TEST013-04] [Type: Unit] **test_tool_tracking_callback_handler_initial_state**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `ToolTrackingCallbackHandler`
  - **Scenario:** Validar que um handler recém-criado inicializa com `has_queried_data = False` e conjunto padrão de `DATA_QUERY_TOOLS`.
  - **Arrange:** Instanciar `handler = ToolTrackingCallbackHandler()`.
  - **Act:** Inspecionar `handler.has_queried_data` e `handler.data_tools`.
  - **Assert:** `handler.has_queried_data is False` e `handler.data_tools == DATA_QUERY_TOOLS`.
  - **Priority:** P0

- [COMPLETED] [TEST013-05] [Type: Unit] **test_tool_tracking_callback_handler_domain_tool_detection**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `ToolTrackingCallbackHandler.on_tool_start()`
  - **Scenario:** Validar que o disparo de `on_tool_start` com o nome de uma Domain Tool (ex: `get_top_selling_product`) altera `has_queried_data` para `True`.
  - **Arrange:** Instanciar `handler = ToolTrackingCallbackHandler()`.
  - **Act:** Invocar `handler.on_tool_start(serialized={"name": "get_top_selling_product"}, input_str="{}")`.
  - **Assert:** `handler.has_queried_data is True`.
  - **Priority:** P0

- [COMPLETED] [TEST013-06] [Type: Unit] **test_tool_tracking_callback_handler_sql_query_on_tool_end**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `ToolTrackingCallbackHandler.on_tool_end()`
  - **Scenario:** Validar que a finalização da ferramenta `secured_sql_query` via `on_tool_end` ativa a flag `has_queried_data = True`.
  - **Arrange:** Instanciar `handler = ToolTrackingCallbackHandler()`.
  - **Act:** Invocar `handler.on_tool_end(output="result", name="secured_sql_query")`.
  - **Assert:** `handler.has_queried_data is True`.
  - **Priority:** P0

- [COMPLETED] [TEST013-07] [Type: Unit] **test_tool_tracking_callback_handler_sub_millisecond_overhead**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `ToolTrackingCallbackHandler`
  - **Scenario:** Validar que a execução em memória do interceptor de callbacks opera com overhead sub-milissegundo (< 0.1ms por invocação) satisfazendo o NFR02.
  - **Arrange:** Instanciar `handler = ToolTrackingCallbackHandler()` e preparar loop de 1.000 iterações.
  - **Act:** Medir tempo total de execução via `time.perf_counter()`.
  - **Assert:** Latência média por chamada é estritamente inferior a 0.1ms.
  - **Priority:** P1

---

### Task 003 — [UseCase]: Update SalesAgent.ask to inject callback and return flag

- [COMPLETED] [TEST013-08] [Type: Unit] **test_agent_result_contracts_and_interoperability**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `AgentResult`
  - **Scenario:** Validar que `AgentResult` implementa paridade total com string (igualdade, substrings, `lower()`, `startswith()`) e desempacotamento de tupla `(response, data_queried)`.
  - **Arrange:** Instanciar `res = AgentResult(response="Produto A é o líder", data_queried=True)`.
  - **Act:** Testar operações `res == "Produto A é o líder"`, `text, flag = res` e `res.data_queried`.
  - **Assert:** Todas as asserções de compatibilidade comportamental retornam verdadeiro sem quebrar consumidores legados.
  - **Priority:** P0

- [COMPLETED] [TEST013-09] [Type: Unit] **test_sales_agent_ask_intercepts_callbacks_and_returns_flag**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.ask()`
  - **Scenario:** Validar que `SalesAgent.ask()` injeta uma nova instância de `ToolTrackingCallbackHandler` no `RunnableConfig` do executor e retorna `AgentResult` com `data_queried = True` quando a ferramenta é executada.
  - **Arrange:** Configurar mock de executor para simular disparo de evento no callback handler.
  - **Act:** Invocar `result = agent.ask("Qual o produto mais vendido?")`.
  - **Assert:** `result.response == "Produto mais vendido foi P1."` e `result.data_queried is True`.
  - **Priority:** P0

- [COMPLETED] [TEST013-10] [Type: Unit] **test_sales_agent_ask_exception_fallback_returns_flag_false**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.ask()`
  - **Scenario:** Validar que caso o executor lance uma exceção não tratada ou atinja o teto de recursão, a mensagem de fallback é retornada com `data_queried = False`.
  - **Arrange:** Configurar mock do executor com `side_effect = RuntimeError("Recursion limit exhausted")`.
  - **Act:** Invocar `result = agent.ask("Gere relatório com erro")`.
  - **Assert:** `result.data_queried is False` e `result.response == FALLBACK_ERROR_MESSAGE`.
  - **Priority:** P1

---

### Task 004 — [UseCase]: Update WebChatApplicationService to map flag

- [COMPLETED] [TEST013-11] [Type: Unit] **test_web_chat_service_maps_data_queried_flag_true**
  - **Target:** `src/application/service/web_chat_application_service.py` → `WebChatApplicationService.process_chat_message()`
  - **Scenario:** Validar que o serviço de aplicação extrai o flag `data_queried = True` do `AgentResult` e o injeta no `ChatResponseDTO`.
  - **Arrange:** Configurar mock do `SalesAgent.ask` retornando `AgentResult(response="Total: R$ 50.000", data_queried=True)`.
  - **Act:** Invocar `response = service.process_chat_message(ChatRequestDTO(message="Total?", session_id="sess-1"))`.
  - **Assert:** `response.data_queried is True`, `response.response == "Total: R$ 50.000"` e `response.status == "success"`.
  - **Priority:** P0

- [COMPLETED] [TEST013-12] [Type: Unit] **test_web_chat_service_maps_data_queried_flag_false_on_casual_chat**
  - **Target:** `src/application/service/web_chat_application_service.py` → `WebChatApplicationService.process_chat_message()`
  - **Scenario:** Validar que em interações sem uso de ferramentas o flag `data_queried = False` é propagado fielmente no DTO de resposta.
  - **Arrange:** Configurar mock de `SalesAgent.ask` retornando `AgentResult(response="Olá!", data_queried=False)`.
  - **Act:** Invocar `response = service.process_chat_message(ChatRequestDTO(message="Oi", session_id="sess-1"))`.
  - **Assert:** `response.data_queried is False` e `response.status == "success"`.
  - **Priority:** P0

- [COMPLETED] [TEST013-13] [Type: Unit] **test_web_chat_service_error_handling_sanitizes_and_sets_flag_false**
  - **Target:** `src/application/service/web_chat_application_service.py` → `WebChatApplicationService.process_chat_message()`
  - **Scenario:** Validar que falhas inesperadas na aplicação capturam a exceção, retornam mensagem sanitizada e garantem `data_queried = False` com `status = "error"`.
  - **Arrange:** Configurar mock de `agent.ask` lançando exceção fatal.
  - **Act:** Invocar `response = service.process_chat_message(ChatRequestDTO(message="Crash", session_id="sess-2"))`.
  - **Assert:** `response.data_queried is False`, `response.status == "error"` e mensagem de erro amigável ao usuário.
  - **Priority:** P1

---

### Task 005 — [Adapter-Web]: Update Frontend UI to render Verified Badge

- [COMPLETED] [TEST013-14] [Type: Unit] **test_frontend_verified_badge_dom_rendering_when_true**
  - **Target:** `src/adapter/inbound/web/static/app.js` → `addMessage()`
  - **Scenario:** Validar que quando o payload da API contém `data_queried: true`, a função `addMessage` insere o container `.verified-data-badge` com ícone SVG e o texto `"Dados Verificados"`.
  - **Arrange:** Carregar `app.js` e simular resposta `data.data_queried = true` para `bot-message`.
  - **Act:** Chamar `addMessage("Total calculado", "bot-message", true)`.
  - **Assert:** O elemento criado possui a classe `.verified-data-badge`, contém texto `"Dados Verificados"` e o ícone SVG correspondente.
  - **Priority:** P0

- [COMPLETED] [TEST013-15] [Type: Unit] **test_frontend_verified_badge_omitted_when_false**
  - **Target:** `src/adapter/inbound/web/static/app.js` → `addMessage()`
  - **Scenario:** Validar que mensagens casuais ou com `data_queried: false` não renderizam o elemento `.verified-data-badge` no DOM.
  - **Arrange:** Carregar `app.js` e simular resposta `data.data_queried = false`.
  - **Act:** Chamar `addMessage("Olá! Como posso ajudar?", "bot-message", false)`.
  - **Assert:** O elemento filho com a classe `.verified-data-badge` não existe dentro do container da mensagem.
  - **Priority:** P0

- [COMPLETED] [TEST013-16] [Type: Unit] **test_frontend_verified_badge_accessibility_attributes**
  - **Target:** `src/adapter/inbound/web/static/app.js` → `.verified-data-badge`
  - **Scenario:** Validar que o selo de verificação atende aos padrões de acessibilidade ARIA incluindo `role="status"` e `aria-label="Dados verificados no banco de dados"`.
  - **Arrange:** Inspecionar a criação do selo no `app.js`.
  - **Act:** Obter atributos ARIA do nó HTML construído.
  - **Assert:** `getAttribute("role") == "status"` e `getAttribute("aria-label") == "Dados verificados no banco de dados"`.
  - **Priority:** P1

---

### Task 006 — [Test-Integration]: Implement E2E tests for turn isolation and badge logic

- [COMPLETED] [TEST013-17] [Type: Integration] **test_analytical_turn_returns_data_queried_true**
  - **Target:** `tests/integration/test_data_queried_flag.py` → `test_analytical_turn_returns_data_queried_true`
  - **Scenario:** Validar que uma consulta analítica executando uma Domain Tool (`get_top_selling_product`) retorna `data_queried = True` no `AgentResult`.
  - **Arrange:** Configurar `DeterministicSequenceChatModel` simulando chamada de ferramenta e resposta.
  - **Act:** Invocar `agent.ask("Qual foi o produto mais vendido?")`.
  - **Assert:** `result.data_queried is True` e resposta contém dados do produto líder.
  - **Priority:** P0

- [COMPLETED] [TEST013-18] [Type: Integration] **test_casual_greeting_turn_returns_data_queried_false**
  - **Target:** `tests/integration/test_data_queried_flag.py` → `test_casual_greeting_turn_returns_data_queried_false`
  - **Scenario:** Validar que uma pergunta casual ("Olá! Tudo bem?") respondida diretamente pelo modelo sem acionar ferramentas retorna `data_queried = False`.
  - **Arrange:** Configurar `DeterministicSequenceChatModel` com resposta textual direta.
  - **Act:** Invocar `agent.ask("Olá! Tudo bem?")`.
  - **Assert:** `result.data_queried is False`.
  - **Priority:** P0

- [COMPLETED] [TEST013-19] [Type: Integration] **test_multi_turn_turn_isolation**
  - **Target:** `tests/integration/test_data_queried_flag.py` → `test_multi_turn_turn_isolation`
  - **Scenario:** Validar em sessão multi-turn encadeada que a execução de ferramenta no Turno 1 não contamina o Turno 2 (casual), e que o Turno 3 com SQL ad-hoc volta a sinalizar `data_queried = True` com isolamento estrito.
  - **Arrange:** Instanciar `WebChatApplicationService` com `SessionMemoryAdapter` e roteiro de 3 mensagens encadeadas.
  - **Act:** Processar Turno 1 (Analítico), Turno 2 (Casual) e Turno 3 (SQL Fallback).
  - **Assert:** Turno 1 retorna `data_queried = True`; Turno 2 retorna `data_queried = False`; Turno 3 retorna `data_queried = True`.
  - **Priority:** P0

- [COMPLETED] [TEST013-20] [Type: Integration] **test_exception_fallback_returns_data_queried_false**
  - **Target:** `tests/integration/test_data_queried_flag.py` → `test_exception_fallback_returns_data_queried_false`
  - **Scenario:** Validar que em caso de interrupção abrupta ou limite de recursão atingido no executor LangChain, a resposta de contingência mantém `data_queried = False`.
  - **Arrange:** Configurar mock de executor simulando `RuntimeError("Recursion limit exhausted")`.
  - **Act:** Invocar `agent.ask("Gere relatório de erro")`.
  - **Assert:** `result.data_queried is False` e texto contém mensagem padrão de indisponibilidade de dados.
  - **Priority:** P1

---

## Traceability Matrix

| Test ID | Task Reference | Component Under Test | Scope / Type | Status |
| :--- | :--- | :--- | :--- | :--- |
| **TEST013-01** | Task 001 | `src/application/dto/chat_dto.py` | Unit | `[COMPLETED]` |
| **TEST013-02** | Task 001 | `src/application/dto/chat_dto.py` | Unit | `[COMPLETED]` |
| **TEST013-03** | Task 001 | `src/application/dto/chat_dto.py` | Unit | `[COMPLETED]` |
| **TEST013-04** | Task 002 | `src/adapter/inbound/llm/sales_agent.py` | Unit | `[COMPLETED]` |
| **TEST013-05** | Task 002 | `src/adapter/inbound/llm/sales_agent.py` | Unit | `[COMPLETED]` |
| **TEST013-06** | Task 002 | `src/adapter/inbound/llm/sales_agent.py` | Unit | `[COMPLETED]` |
| **TEST013-07** | Task 002 | `src/adapter/inbound/llm/sales_agent.py` | Unit / Performance | `[COMPLETED]` |
| **TEST013-08** | Task 003 | `src/adapter/inbound/llm/sales_agent.py` | Unit | `[COMPLETED]` |
| **TEST013-09** | Task 003 | `src/adapter/inbound/llm/sales_agent.py` | Unit | `[COMPLETED]` |
| **TEST013-10** | Task 003 | `src/adapter/inbound/llm/sales_agent.py` | Unit | `[COMPLETED]` |
| **TEST013-11** | Task 004 | `src/application/service/web_chat_application_service.py` | Unit | `[COMPLETED]` |
| **TEST013-12** | Task 004 | `src/application/service/web_chat_application_service.py` | Unit | `[COMPLETED]` |
| **TEST013-13** | Task 004 | `src/application/service/web_chat_application_service.py` | Unit | `[COMPLETED]` |
| **TEST013-14** | Task 005 | `src/adapter/inbound/web/static/app.js` | UI / Unit | `[COMPLETED]` |
| **TEST013-15** | Task 005 | `src/adapter/inbound/web/static/app.js` | UI / Unit | `[COMPLETED]` |
| **TEST013-16** | Task 005 | `src/adapter/inbound/web/static/app.js` | UI / Accessibility | `[COMPLETED]` |
| **TEST013-17** | Task 006 | `tests/integration/test_data_queried_flag.py` | Integration | `[COMPLETED]` |
| **TEST013-18** | Task 006 | `tests/integration/test_data_queried_flag.py` | Integration | `[COMPLETED]` |
| **TEST013-19** | Task 006 | `tests/integration/test_data_queried_flag.py` | Integration | `[COMPLETED]` |
| **TEST013-20** | Task 006 | `tests/integration/test_data_queried_flag.py` | Integration | `[COMPLETED]` |
