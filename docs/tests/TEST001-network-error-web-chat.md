# TEST001-network-error-web-chat — Especificação de Cobertura de Testes

> **Tarefa de Origem:** [B001-network-error-web-chat.md](../incidents/B001-network-error-web-chat.md)

## Visão Geral de Cobertura

Esta especificação de testes aborda os lacunas de cobertura identificadas durante a resolução do incidente de erro de rede B001. Ela garante que as dependências sejam devidamente injetadas no `SalesAgent` e que quaisquer exceções durante o processo de inicialização do agente sejam capturadas adequadamente pela camada de serviço da aplicação, evitando erros 500 não tratados no servidor.

## Checklist de Testes

### Task 001 - Implementar o script de reprodução em tests/integration/test_web_chat_incident_b001.py

- [COMPLETED] [TEST001-01] [Integration] **Teste de Reprodução do Erro de Rede no Web Chat**
  - **Alvo:** `tests/integration/test_web_chat_incident_b001.py` → `test_web_chat_network_error_reproduction()`
  - **Cenário:** A requisição de chat para uma nova sessão executa sem lançar HTTP 500.
  - **Arrange:** Inicializar o `TestClient` do FastAPI com a instância da aplicação.
  - **Act:** Enviar requisição POST `{"message": "hello", "session_id": "test-session-123"}` para `/chat`.
  - **Assert:** O código de status da resposta é `200 OK` e o campo `status` retornado é `success` ou `error`.
  - **Prioridade:** P0 (Crítica)

### Task 002 - Corrigir agent_factory em src/adapter/inbound/web/chat_controller.py

- [COMPLETED] [TEST001-02] [Unit] **Teste se Agent Factory Inicializa SalesAgent com Injeção de Dependências Adequada**
  - **Alvo:** `src/adapter/inbound/web/chat_controller.py` → `get_web_chat_use_case_singleton()`
  - **Cenário:** O `agent_factory` passado ao singleton `WebChatApplicationService` instancia corretamente uma instância válida de `SalesAgent`.
  - **Arrange:** Chamar `get_web_chat_use_case_singleton()` para obter a instância do serviço.
  - **Act:** Invocar o método protegido `_agent_factory()` a partir da instância obtida.
  - **Assert:** O objeto retornado é uma instância de `SalesAgent` e possui atributos `_llm` e `_tools` válidos inicializados.
  - **Prioridade:** P1 (Alta)

### Task 003 - Mover instanciação do agente para bloco try...except em WebChatApplicationService

- [COMPLETED] [TEST001-03] [Unit] **Teste se WebChatApplicationService Trata Erros da Fábrica de Agentes Adequadamente**
  - **Alvo:** `src/application/service/web_chat_application_service.py` → `process_chat_message()`
  - **Cenário:** Quando o `agent_factory` lança uma exceção durante a inicialização do agente, o serviço a captura e retorna uma resposta de erro estruturada em vez de lançar exceção.
  - **Arrange:** Criar um `agent_factory` mock que sempre lança uma `Exception("Mock factory failure")`. Instanciar `WebChatApplicationService(agent_factory=mock_factory)`. Criar payload `ChatRequestDTO`.
  - **Act:** Chamar `process_chat_message(request)`.
  - **Assert:** O método retorna um `ChatResponseDTO` com `status="error"` e `response="An unexpected error occurred while processing your request. Please try again later."`.
  - **Prioridade:** P0 (Crítica)
