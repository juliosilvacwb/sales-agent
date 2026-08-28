# T002: Web Chat Interface

## PRD Reference

- **PRD:** [R002-web-chat-interface.md](../business-requirements/R002-web-chat-interface.md)
- **Test Coverage:** [TEST002-web-chat-interface.md](../tests/TEST002-web-chat-interface.md)
- **Security Audit:** [S002-web-chat-interface.md](../security/S002-web-chat-interface.md)

## Technical Goal

Criar uma interface web leve e interativa para o Sales Data Analysis Agent, democratizando o acesso aos dados. A solução consistirá em um backend API-First utilizando FastAPI e um frontend estático e responsivo utilizando exclusivamente Vanilla JS, HTML e CSS (com estética premium e suporte a Markdown). O sistema deve gerenciar sessões (`session_id`) para manter o contexto conversacional.

## Architecture Decisions

- **Inbound Web Adapter (FastAPI):** Adoção do FastAPI para expor o endpoint `POST /chat` e servir os arquivos estáticos do frontend. Essa camada atuará como um novo Inbound Adapter na Arquitetura Hexagonal.
- **Frontend Vanilla (Sem Build Step):** O frontend não utilizará Node/React/Vue. Será servido diretamente via arquivos estáticos, consumindo a API assincronamente (Fetch API). A renderização de Markdown será feita via biblioteca externa importada via CDN (ex: `marked.js`).
- **Gerenciamento de Sessão:** A API receberá um `session_id` em cada requisição. O histórico da conversa será mantido na camada de orquestração (via adaptadores de memória do LangChain) vinculado a este ID, mantendo a API REST stateless.
- **Hexagonal Integrity:** O FastAPI e o Frontend estão confinados à camada Adapter (Phase 3). Eles interagem com o Core através da interface (Port) de Use Case definida na Phase 2. As Domain Tools de análise e proteção SQL (R001) permanecem intactas e agnósticas à web.

## Security & Reliability

- **Validação de Entrada:** O FastAPI utilizará Pydantic nos DTOs para validar o payload (`message`, `session_id`).
- **Timeouts e UX:** O frontend implementará timeouts na requisição `fetch` e exibirá feedback visual apropriado em caso de falha de rede ou lentidão do LLM (Exception Path 1 do PRD).
- **Proteção SQL:** Nenhuma mudança necessária; a ferramenta `secured_sql_query` já implementa bloqueios DML/DDL.

## Technical Checklist (Atomic Tasks)

### 🔵 Phase 1 — Domain Core (Zero framework dependencies)

- [COMPLETED] Task 001 - [Domain-Model]: Criar Value Object `SessionContext` para encapsular metadados da sessão (ex: `session_id`, `timestamp`). (Depends On: —)

### 🟡 Phase 2 — Ports & Use Cases (All tasks parallel-safe | Depends on Phase 1)

- [COMPLETED] Task 002 - [DTO]: Definir `ChatRequestDTO` (mensagem, session_id) e `ChatResponseDTO` (texto de resposta, status). (Depends On: Task 001)
- [COMPLETED] Task 003 - [Port-In]: Definir `WebChatUseCase` interface com método `process_chat_message(request: ChatRequestDTO) -> ChatResponseDTO`. (Depends On: Task 002)
- [COMPLETED] Task 004 - [UseCase]: Implementar `WebChatApplicationService` que orquestra a chamada ao agente LangChain, injetando o histórico de conversa com base no `session_id`. (Depends On: Task 003)

### 🟢 Phase 3 — Adapters (All tasks parallel-safe | Depends on Phase 2)

- [COMPLETED] Task 005 - [Config]: Configurar aplicação FastAPI base (roteador, middlewares CORS, montagem do diretório de arquivos estáticos). (Depends On: Task 004)
- [COMPLETED] Task 006 - [Adapter-Web]: Implementar `ChatRestController` que expõe `POST /chat` e invoca o `WebChatUseCase`. (Depends On: Task 004)
- [COMPLETED] Task 007 - [Adapter-Persistence]: Implementar mecanismo de persistência de memória (ex: `InMemorySessionHistoryAdapter` compatível com o BaseChatMessageHistory do LangChain) para o `session_id`. (Depends On: Task 004)
- [COMPLETED] Task 008 - [Adapter-Web-Frontend]: Desenvolver `index.html` e `styles.css` (Dark Mode, layout responsivo de chat, balões de mensagem, micro-animações). (Depends On: —)
- [COMPLETED] Task 009 - [Adapter-Web-Frontend]: Desenvolver `app.js` (geração de `session_id` no client-side, requisição `fetch` assíncrona, renderização de Markdown, controle do loading state). (Depends On: Task 006, Task 008)
- [COMPLETED] Task 010 - [Test-Integration]: Implementar teste End-to-End validando o fluxo de chat via FastAPI (múltiplos turnos para garantir retenção de memória da sessão). (Depends On: Task 005, Task 006, Task 007)

## Task Detailing (Summary Tasks)

### Task 001 - [Domain-Model]: Criar Value Object SessionContext

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** —
- **Objective:** Encapsular os dados da sessão (ID).
- **Files/Path:** `src/domain/model/session_context.py`
- **Technical Acceptance Criteria:** POJO (dataclass em Python) simples, sem frameworks.

### Task 002 - [DTO]: Definir ChatRequestDTO e ChatResponseDTO

- **Phase:** 2
- **Depends On:** Task 001
- **Parallel With:** —
- **Objective:** Definir o formato de transporte de dados para as chamadas web.
- **Files/Path:** `src/application/dto/chat_dto.py`
- **Technical Acceptance Criteria:** Classes Pydantic (ou dataclasses) válidas.

### Task 003 - [Port-In]: Definir WebChatUseCase interface

- **Phase:** 2
- **Depends On:** Task 002
- **Parallel With:** —
- **Objective:** Definir o contrato de entrada para o caso de uso de chat.
- **Files/Path:** `src/application/port/inbound/web_chat_use_case.py`
- **Technical Acceptance Criteria:** Classe abstrata com o método `process_chat_message`.

### Task 004 - [UseCase]: Implementar WebChatApplicationService

- **Phase:** 2
- **Depends On:** Task 003
- **Parallel With:** —
- **Objective:** Orquestrar o LangChain agent utilizando a memória de contexto para o `session_id`.
- **Files/Path:** `src/application/service/web_chat_application_service.py`
- **Reuse:** Instância existente do Agent orquestrador do R001.
- **Technical Acceptance Criteria:** Injeta memória baseada no `session_id` e retorna o resultado formatado.

### Task 005 - [Config]: Configurar aplicação FastAPI

- **Phase:** 3
- **Depends On:** Task 004
- **Parallel With:** Task 006, Task 007, Task 008
- **Objective:** Setup inicial do servidor FastAPI e arquivos estáticos.
- **Files/Path:** `src/adapter/inbound/web/main.py`
- **Technical Acceptance Criteria:** FastAPI roda corretamente e serve pasta estática `/static`.

### Task 006 - [Adapter-Web]: Implementar ChatRestController

- **Phase:** 3
- **Depends On:** Task 004
- **Parallel With:** Task 005, Task 007, Task 008
- **Objective:** Rota da API.
- **Files/Path:** `src/adapter/inbound/web/chat_controller.py`
- **Technical Acceptance Criteria:** Endpoint `POST /chat` recebe e retorna os DTOs corretamente delegando ao port.

### Task 007 - [Adapter-Persistence]: Implementar persistência de memória da sessão

- **Phase:** 3
- **Depends On:** Task 004
- **Parallel With:** Task 005, Task 006, Task 008
- **Objective:** Guardar histórico da conversa por `session_id`.
- **Files/Path:** `src/adapter/outbound/memory/session_memory_adapter.py`
- **Technical Acceptance Criteria:** Implementa store (ex: In-Memory dict) para LangChain `ChatMessageHistory`.

### Task 008 - [Adapter-Web-Frontend]: Desenvolver index.html e styles.css

- **Phase:** 3
- **Depends On:** —
- **Parallel With:** Todos
- **Objective:** Criar a estrutura base visual com estética premium requerida pelo PRD04 e NFRs.
- **Files/Path:** `src/adapter/inbound/web/static/index.html`, `src/adapter/inbound/web/static/styles.css`
- **Technical Acceptance Criteria:** UI pronta, Dark Mode, visual premium e animações.

### Task 009 - [Adapter-Web-Frontend]: Desenvolver app.js

- **Phase:** 3
- **Depends On:** Task 006, Task 008
- **Parallel With:** Task 007, Task 010
- **Objective:** Lógica do cliente web, requests à API e renderização Markdown.
- **Files/Path:** `src/adapter/inbound/web/static/app.js`
- **Technical Acceptance Criteria:** Fetch funcionando, sessões gerenciadas localmente (`crypto.randomUUID()`), Markdown parseado e inserido no DOM com segurança. Tratamento do Exception Path 1.

### Task 010 - [Test-Integration]: Implementar End-to-End test

- **Phase:** 3
- **Depends On:** Task 005, Task 006, Task 007
- **Parallel With:** Task 008, Task 009
- **Objective:** Teste do fluxo completo via FastAPI.
- **Files/Path:** `tests/integration/test_web_chat.py`
- **Technical Acceptance Criteria:** Acessar a API com um `session_id`, enviar perguntas encadeadas e confirmar que o modelo "lembra" do contexto (TestClient do FastAPI).
