<!-- markdownlint-disable MD013 -->
# TEST009-agentic-self-correction — Test Coverage Specification

> **Source Task:** [T009-agentic-self-correction.md](../architecture/T009-agentic-self-correction.md)  
> **PRD Reference:** [R009-agentic-self-correction.md](../business-requirements/R009-agentic-self-correction.md)

## Coverage Overview

Esta especificação detalha a análise forense de cobertura de testes unitários e de integração para a funcionalidade de **Autocorreção Agêntica e Resiliência a Erros** (`T009-agentic-self-correction.md` / `R009-agentic-self-correction.md`). O objetivo central é assegurar que todas as ferramentas do agente (`domain_tools` e `SecuredSQLQueryTool`) lancem `ToolException` nativas com sanitização de caminhos locais (`[REDACTED_PATH]`), que o `SalesAgent` intercepte essas exceções emitindo telemetria (`[AGENT_SELF_CORRECTION]`) e re-injetando o sinal de erro no contexto do LLM para autocorreção autônoma (reparo de colunas SQL alucinadas e validação de datas), garantindo a regra de negócio de zero exposição de erros técnicos (BR01) e fallback gracioso mediante esgotamento do orçamento de 3 tentativas (BR03 / AC06).

- **Status Geral de Cobertura:** 100% de cobertura lógica, tratamento de exceções, sanitização de caminhos e validação E2E mapeados para todas as 6 tasks da especificação T009.
- **Pirâmide de Testes:**
  - **Unitários (Configuração & Prompts):** Validação estrita das diretrizes de autocorreção, regras BR01/BR02/BR03/BR04 e templates de resposta no `SYSTEM_PROMPT`.
  - **Unitários (Adaptador Inbound / SQL Fallback Tool):** Validação de lançamento de `ToolException` em erros de sintaxe SQL, violações de segurança DML/DDL, falhas de execução e sanitização de paths (`[REDACTED_PATH]`).
  - **Unitários (Adaptador Inbound / Domain Tools):** Validação de lançamento de `ToolException` em parsing e validação de formatos de datas no `get_total_sales_in_period` e configuração de `handle_tool_error=True`.
  - **Unitários (Telemetria & Observabilidade):** Validação do handler `_handle_tool_error`, formatação para o LLM e emissão de logs estruturados `[AGENT_SELF_CORRECTION]`.
  - **Unitários (Orquestrador SalesAgent):** Validação de acoplamento do handler de telemetria a todas as ferramentas injetadas e captura de exceções para entrega da mensagem de fallback.
  - **Integração / E2E (Autocorreção Agêntica):** Validação de fluxos conversacionais simulados com `FakeToolCallingChatModel` testando: (1) reparo autônomo de coluna alucinada em único turno; (2) autocorreção de formato de data inválido; (3) esgotamento de retries com entrega de pedido de desculpas executivo sem rastros de SQL/DuckDB.

---

## Test Checklist

### Task 001 — [Config]: Update SYSTEM_PROMPT with self-correction instructions

- [COMPLETED] [TEST009-01] [Type: Unit] **test_system_prompt_adheres_to_business_rules**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SYSTEM_PROMPT`
  - **Scenario:** Validar que o `SYSTEM_PROMPT` contém explicitamente todas as diretrizes de autocorreção de erros (BR01, BR02, BR03, BR04).
  - **Arrange:** Importar a constante `SYSTEM_PROMPT` e `FALLBACK_ERROR_MESSAGE` de `sales_agent.py`.
  - **Act:** Inspecionar a presença das seções e palavras-chave estruturantes no texto do prompt.
  - **Assert:** O prompt contém `"DIRETRIZES DE AUTOCORREÇÃO E RECUPERAÇÃO DE ERROS"`, `"Tratamento Autônomo de Erros"`, `"Zero Exposição de Erros Técnicos"`, `"Limite de Tentativas e Fallback Gracioso"` e a mensagem exata de contingência de `FALLBACK_ERROR_MESSAGE`.
  - **Priority:** P0

---

### Task 002 — [Adapter-Web]: Refactor SecuredSQLQueryTool to raise sanitized ToolException

- [COMPLETED] [TEST009-02] [Type: Unit] **test_secured_sql_tool_raises_tool_exception_on_syntax_error**
  - **Target:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SecuredSQLQueryTool._run()`
  - **Scenario:** Validar que consultas com sintaxe SQL malformada disparam `ToolException` com mensagem explicativa em português (AC01).
  - **Arrange:** Instanciar `SecuredSQLQueryTool` com mock de `SalesAnalysisUseCase`.
  - **Act:** Invocar `tool._run("SELECT * FROM (SELECT local FROM sales_data")` (parêntese não fechado).
  - **Assert:** Lança `ToolException` contendo `"Erro de Sintaxe"` e orientação para corrigir a consulta.
  - **Priority:** P0

- [COMPLETED] [TEST009-03] [Type: Unit] **test_secured_sql_tool_raises_tool_exception_on_security_violation**
  - **Target:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SecuredSQLQueryTool._run()`
  - **Scenario:** Validar que operações mutacionais proibidas (DML/DDL) disparam `ToolException` bloqueando a execução (AC01).
  - **Arrange:** Instanciar `SecuredSQLQueryTool` com mock de `SalesAnalysisUseCase`.
  - **Act:** Invocar `tool._run("DROP TABLE sales_data")`.
  - **Assert:** Lança `ToolException` contendo `"Erro de Segurança"` e indicação de instrução proibida.
  - **Priority:** P0

- [COMPLETED] [TEST009-04] [Type: Unit] **test_secured_sql_tool_raises_tool_exception_on_execution_error**
  - **Target:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SecuredSQLQueryTool._run()`
  - **Scenario:** Validar que erros de execução no banco de dados (ex: coluna inexistente) disparam `ToolException` com sanitização de caminhos locais (AC01, BR04).
  - **Arrange:** Configurar `usecase.execute_custom_query` para lançar `RuntimeError("Binder Error: Column 'total_revenue' does not exist in path c:/Code/challenge_ai_engineer/data.parquet")`.
  - **Act:** Invocar `tool._run("SELECT SUM(total_revenue) FROM sales_data")`.
  - **Assert:** Lança `ToolException` contendo `"Erro ao executar a consulta SQL"`, `"[REDACTED_PATH]"` e nenhum rastro de `"c:/Code/challenge_ai_engineer"`.
  - **Priority:** P0

- [COMPLETED] [TEST009-05] [Type: Unit] **test_secured_sql_tool_handle_tool_error_attribute**
  - **Target:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SecuredSQLQueryTool`
  - **Scenario:** Validar que a classe `SecuredSQLQueryTool` define `handle_tool_error = True` para permitir captura e feedback pelo LangChain AgentExecutor.
  - **Arrange:** Obter a classe `SecuredSQLQueryTool` ou uma instância via `create_sql_fallback_tool`.
  - **Act:** Inspecionar o atributo `handle_tool_error`.
  - **Assert:** `tool.handle_tool_error is not None` e é verdadeiro / configurável.
  - **Priority:** P1

---

### Task 003 — [Adapter-Web]: Refactor domain_tools.py to raise ToolException

- [COMPLETED] [TEST009-06] [Type: Unit] **test_domain_tools_handle_tool_error_configured**
  - **Target:** `src/adapter/inbound/llm/domain_tools.py` → `create_domain_tools()`
  - **Scenario:** Validar que todas as 10 ferramentas de domínio retornadas pela factory possuem `handle_tool_error = True`.
  - **Arrange:** Instanciar as ferramentas de domínio via `create_domain_tools(mock_usecase)`.
  - **Act:** Iterar sobre as 10 ferramentas e checar o atributo `handle_tool_error`.
  - **Assert:** Para todas as 10 ferramentas, `tool.handle_tool_error is True`.
  - **Priority:** P0

- [COMPLETED] [TEST009-07] [Type: Unit] **test_tool_get_total_sales_in_period_raises_tool_exception**
  - **Target:** `src/adapter/inbound/llm/domain_tools.py` → `get_total_sales_in_period()`
  - **Scenario:** Validar que formato de data inválido dispara `ToolException` explicativa em vez de retornar string de sucesso (AC01).
  - **Arrange:** Obter a ferramenta `get_total_sales_in_period` criada pela factory.
  - **Act:** Invocar a função subjacente com `start_date="invalid-date"`.
  - **Assert:** Lança `ToolException` com a mensagem `"Erro de validação de data: Formato de data inválido"`, e o use case não é chamado.
  - **Priority:** P0

- [COMPLETED] [TEST009-08] [Type: Unit] **test_tool_get_total_sales_in_period_valid_date_formats**
  - **Target:** `src/adapter/inbound/llm/domain_tools.py` → `_parse_date()`
  - **Scenario:** Validar que formatos válidos brasileiros (DD/MM/YYYY, DD.MM.YYYY, DD-MM-YYYY) e ISO (YYYY-MM-DD) são aceitos sem lançar exceções.
  - **Arrange:** Preparar datas válidas em múltiplos formatos.
  - **Act:** Invocar `get_total_sales_in_period` com datas brasileiras e ISO.
  - **Assert:** Execução ocorre com sucesso chamando `mock_usecase.get_total_sales_in_period` com instâncias corretas de `datetime.date`.
  - **Priority:** P1

---

### Task 004 — [Adapter-Web]: Implement custom error handler for Telemetry

- [COMPLETED] [TEST009-09] [Type: Unit] **test_handle_tool_error_formatting_and_logging**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `_handle_tool_error()`
  - **Scenario:** Validar que `_handle_tool_error` formata a mensagem para o LLM e emite log de aviso com o marcador de telemetria `[AGENT_SELF_CORRECTION]` (AC07).
  - **Arrange:** Criar instância de `ToolException("Coluna 'total_revenue' não existe.")`.
  - **Act:** Executar `_handle_tool_error(exc)` capturando logs no nível `WARNING`.
  - **Assert:** Retorna `"Coluna 'total_revenue' não existe."` e o log capturado contém `"[AGENT_SELF_CORRECTION]"` e a mensagem de erro.
  - **Priority:** P0

- [COMPLETED] [TEST009-10] [Type: Unit] **test_handle_tool_error_empty_args**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `_handle_tool_error()`
  - **Scenario:** Validar que `_handle_tool_error` não lança exceções quando `ToolException` é instanciada sem argumentos explícitos.
  - **Arrange:** Criar instância de `ToolException()`.
  - **Act:** Executar `_handle_tool_error(exc)`.
  - **Assert:** Retorna uma string não nula e nenhum erro é propagado.
  - **Priority:** P1

---

### Task 005 — [UseCase]: Configure SalesAgent executor with retry ceilings

- [COMPLETED] [TEST009-11] [Type: Unit] **test_sales_agent_attaches_telemetry_handler_to_all_tools**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.__init__()`
  - **Scenario:** Validar que ao inicializar o `SalesAgent`, o handler `_handle_tool_error` é anexado a todas as ferramentas fornecidas.
  - **Arrange:** Instanciar lista de ferramentas contendo domain tools e SQL fallback tool.
  - **Act:** Instanciar `SalesAgent(llm=mock_llm, tools=all_tools)` com mock de `create_agent`.
  - **Assert:** Para todas as ferramentas em `agent._tools`, `tool.handle_tool_error == _handle_tool_error`.
  - **Priority:** P0

- [COMPLETED] [TEST009-12] [Type: Unit] **test_sales_agent_returns_fallback_message_on_unhandled_exception**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.ask()`
  - **Scenario:** Validar que falhas catastróficas ou estouro de iterações no executor retornam a mensagem de contingência sem expor exceções brutas (BR01, BR03, AC06).
  - **Arrange:** Mockar `_executor.invoke` para lançar `RuntimeError("Max iterations reached")`.
  - **Act:** Invocar `agent.ask("Pergunta complexa")`.
  - **Assert:** Retorna `FALLBACK_ERROR_MESSAGE` e registra erro no log com traceback para auditoria interna.
  - **Priority:** P0

- [COMPLETED] [TEST009-13] [Type: Unit] **test_sales_agent_chat_history_preservation_and_reset**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.reset_history()`
  - **Scenario:** Validar que a memória conversacional interna mantém o histórico dentro dos limites configurados e é limpa via `reset_history()`.
  - **Arrange:** Instanciar `SalesAgent` com mock executor retornando resposta textual.
  - **Act:** Executar perguntas sequenciais e em seguida chamar `agent.reset_history()`.
  - **Assert:** O histórico armazena pares de mensagens `HumanMessage` / `AIMessage` até `max_history_messages`, e `reset_history()` limpa a lista.
  - **Priority:** P2

---

### Task 006 — [Test-Integration]: Implement self-correction E2E tests

- [COMPLETED] [TEST009-14] [Type: Integration] **test_sql_column_hallucination_self_correction_e2e**
  - **Target:** `tests/integration/test_agent_self_correction.py` → `test_sql_column_hallucination_self_correction_e2e()`
  - **Scenario:** Validar que quando o LLM gera uma coluna SQL inexistente (`total_price`), ele recebe feedback de erro via `ToolException`, emite log `[AGENT_SELF_CORRECTION]`, autocorrige a consulta para `SUM(actual_quantity * actual_price)` e responde com sucesso no mesmo turno (AC04, AC07).
  - **Arrange:** Configurar `FakeToolCallingChatModel` com sequência: (1) tool call com coluna errada; (2) tool call corrigida; (3) resposta executiva final.
  - **Act:** Executar `agent.ask("Qual é o faturamento total do produto Product_0001?")` com captura de logs.
  - **Assert:** A resposta final contém o valor correto, não contém menções a erro técnico, e o log contém o marcador `[AGENT_SELF_CORRECTION]`.
  - **Priority:** P0

- [COMPLETED] [TEST009-15] [Type: Integration] **test_domain_tool_date_validation_self_correction_e2e**
  - **Target:** `tests/integration/test_agent_self_correction.py` → `test_domain_tool_date_validation_self_correction_e2e()`
  - **Scenario:** Validar que quando o LLM invoca `get_total_sales_in_period` com formato de data inválido, ele recebe `ToolException`, reformata para `DD/MM/YYYY` e conclui a consulta com sucesso (AC01, AC04, AC07).
  - **Arrange:** Configurar `FakeToolCallingChatModel` com: (1) tool call com data inválida; (2) tool call com data corrigida; (3) resposta executiva.
  - **Act:** Executar `agent.ask("Qual o total de vendas em janeiro de 2023?")`.
  - **Assert:** Resposta contém os dados consolidados do período e o log registra o marcador `[AGENT_SELF_CORRECTION]`.
  - **Priority:** P0

- [COMPLETED] [TEST009-16] [Type: Integration] **test_retry_exhaustion_returns_polite_fallback_e2e**
  - **Target:** `tests/integration/test_agent_self_correction.py` → `test_retry_exhaustion_returns_polite_fallback_e2e()`
  - **Scenario:** Validar que ao atingir o teto de 3 tentativas consecutivas com falha (erro irrecuperável), o agente entrega a mensagem padronizada de desculpas de negócio sem expor stack traces ou erros de banco (AC05, AC06, BR01, BR03).
  - **Arrange:** Configurar `FakeToolCallingChatModel` com 3 chamadas consecutivas a tabelas inexistentes seguidas pela mensagem de fallback.
  - **Act:** Executar `agent.ask("Qual a margem dos produtos da tabela confidencial?")`.
  - **Assert:** A resposta contém o texto exato de `FALLBACK_ERROR_MESSAGE`, não contém `"Traceback"`, `"Catalog Error"` ou `"Table with name"`, e o log contém os marcadores `[AGENT_SELF_CORRECTION]`.
  - **Priority:** P0
