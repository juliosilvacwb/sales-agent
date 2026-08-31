# S014-langgraph-orchestration — Security Audit

> **Source Task:** [T014-langgraph-orchestration.md](../architecture/T014-langgraph-orchestration.md)  
> **PRD Reference:** [R014-langgraph-orchestration.md](../business-requirements/R014-langgraph-orchestration.md)  
> **Test Coverage:** [TEST014-langgraph-orchestration.md](../tests/TEST014-langgraph-orchestration.md)

## Security Overview

A auditoria de segurança da especificação de **Advanced AI Orchestration via LangGraph** (`T014-langgraph-orchestration.md` / `R014-langgraph-orchestration.md`) avaliou a robustez da máquina de estados (`StateGraph`), a segurança dos nós de execução (`call_model`, `ToolNode`), o roteamento condicional de ferramentas e a integridade da inspeção de estado para Response Grounding. A análise foi fundamentada nos padrões **OWASP Top 10 for LLM Applications (LLM01: Prompt Injection, LLM04: Model Denial of Service, LLM06: Sensitive Information Disclosure, LLM09: Misinformation & Overreliance)**, **OWASP ASVS V5 (Validation, Sanitization and Output Encoding)**, **CWE-400 (Uncontrolled Resource Consumption)**, **CWE-835 (Loop with Unreachable Exit Condition)** e **CWE-1188 (Insecure Default Initialization / Fail-Open Behavior)**.

A migração substitui o executor linear e opaco (`AgentExecutor`) por um grafo cíclico determinístico no LangGraph, introduzindo novos vetores de risco cibernético relacionados a consumo excessivo de tokens em laços de autorrecuperação, vazamento de detalhes estruturais em mensagens de ferramentas e potenciais inconsistências na detecção de resposta fundamentada (`data_queried`).

### Principais Dimensões Auditadas

1. **Prevenção de Denial of Service e Token Exhaustion (OWASP LLM04 / CWE-400 / CWE-835):** Avaliação do teto de recursão (`recursion_limit: 10`) e dos manipuladores de exceção para `GraphRecursionError`, prevenindo laços infinitos e exaustão orçamentária de inferência durante ciclos contínuos de autocorreção.
2. **Defesa contra Injeção Indireta via Tool Feedback (OWASP LLM01 / CWE-20):** Validação das diretrizes de isolamento entre mensagens de erro (`ToolMessage`) e comandos operacionais, assegurando que erros de validação SQL e esquema não induzam o modelo a ultrapassar restrições de leitura (`SELECT`/`WITH`).
3. **Higienização de Logs e Prevenção de Log Injection (CWE-117):** Verificação da higienização de quebras de linha (CRLF) na função `_handle_tool_error` antes da emissão de telemetria `[AGENT_SELF_CORRECTION]`.
4. **Inspeção Estrita de Estado e Prevenção de Spoofing de Grounding (OWASP LLM09 / CWE-1188 / CWE-345):** Identificação de vulnerabilidade na extração da flag `data_queried`, onde a checagem indiscriminada de instâncias `ToolMessage` sem validação da whitelist de ferramentas analíticas (`DATA_QUERY_TOOLS`) pode introduzir falsos positivos de verificação de dados.
5. **Isolamento de Memória e Sessão (CWE-662 / Session Bleeding):** Validação da preservação do histórico de mensagens e isolamento quando instâncias externas de `chat_history` são fornecidas, impedindo contaminação cruzada entre requisições concorrentes.

---

## Vulnerability Log

| ID | Vulnerability / Security Control | Severity | Risk | Impact |
| :--- | :--- | :--- | :--- | :--- |
| S014-01 | Permissive ToolMessage State Inspection for Data Queried Flag | Medium | Low x Medium | Marcação indevida de respostas como dados verificados quando ferramentas não-analíticas ou com erro geram ToolMessages. |
| S014-02 | Unhandled Schema & Path Information Disclosure in ToolNode Exceptions | Low | Low x Low | Exposição de caminhos de arquivos ou detalhes internos do DuckDB em ToolMessages durante falhas não tratadas. |
| S014-03 | Strict Recursion Ceiling Enforcement against Model DoS | High | Medium x High | Proteção contra laços infinitos e consumo descontrolado de tokens em grafos cíclicos via recursion_limit=10. |
| S014-04 | Chat History Input Type Validation and State Tampering Defense | Low | Low x Low | Risco de corrupção de estado ou injeção ao receber objetos inválidos no parâmetro chat_history. |

---

## Refinement Tasks

### Task 002 — [Adapter-Web]: Implement discrete graph nodes

- [COMPLETED] [S014-02] [Low] **Sanitize Internal Stack Traces and File System Paths in ToolNode Error Handlers**
  - **Location:** `src/adapter/inbound/llm/sales_agent.py` → `_handle_tool_error()` e `create_sales_graph()`
  - **Risk:** Caso uma exceção interna no `ToolNode` contenha caminhos absolutos do sistema operacional (ex: `C:\Code\...` ou `/tmp/...`) ou estruturas internas do DuckDB, o retorno direto do `str(error)` para a `ToolMessage` pode expor dados sensíveis de infraestrutura ao contexto do LLM (CWE-209 / OWASP LLM06).
  - **Fix:** Garantir que `_handle_tool_error` normalize e sanitize mensagens de erro antes de retorná-las, removendo referências a diretórios absolutos do sistema de arquivos e mantendo apenas a mensagem técnica essencial de validação de dados/esquema.
  - **Validation:** Executar teste unitário instanciando ferramenta com erro contendo caminhos de arquivo absolutos e validar que a mensagem retornada no `ToolMessage` foi devidamente higienizada.

---

### Task 003 — [Adapter-Web]: Implement conditional routing and compile StateGraph

- [COMPLETED] [S014-03] [High] **Enforce Strict Recursion Limit and Fallback Isolation in Cyclic Graph Compilation**
  - **Location:** `src/adapter/inbound/llm/sales_agent.py` → `create_sales_graph()` e `SalesAgent.ask()`
  - **Risk:** Grafos com arestas cíclicas (`tools -> agent`) apresentam risco intrínseco de loop infinito (CWE-835 / OWASP LLM04) caso o modelo entre em oscilação de chamadas de ferramentas. Sem uma trava rígida em tempo de execução, requisições maliciosas podem esgotar recursos de CPU e orçamento de API.
  - **Fix:** Assegurar que `SalesAgent.ask()` configure imutavelmente `recursion_limit: 10` em todas as invocações de `_executor.invoke()`, capturando explicitamente `GraphRecursionError` e retornando `FALLBACK_ERROR_MESSAGE` com `data_queried = False`, sem propagar exceções não tratadas para a camada HTTP.
  - **Validation:** Executar `test_langgraph_recursion_limit_protection` com 20 chamadas contínuas de ferramentas simuladas e verificar que a execução é interrompida no 10º passo retornando a mensagem de contingência.

---

### Task 004 — [Adapter-Web]: Refactor SalesAgent orchestration and state extraction

- [COMPLETED] [S014-01] [Medium] **Enforce Whitelist Validation on ToolMessage Inspection for Response Grounding**
  - **Location:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.ask()` (linhas 316-317)
  - **Risk:** A lógica atual avalia `has_tool_message = any(isinstance(m, ToolMessage) for m in result.get("messages", []))`. Se ferramentas utilitárias futuras ou mensagens de ferramentas com erro emitirem um `ToolMessage`, a flag `data_queried` será marcada como `True`, gerando falsos positivos no selo de "Dados Verificados" e induzindo o usuário a confiar em respostas não fundamentadas (CWE-1188 / OWASP LLM09).
  - **Fix:** Refatorar a verificação de `has_tool_message` para validar estritamente se o nome da ferramenta (`m.name`) pertence ao conjunto autorizado `DATA_QUERY_TOOLS` e se a mensagem não representa uma falha não recuperada, ou sincronizar a decisão exclusivamente com o `ToolTrackingCallbackHandler` que já possui a política de whitelist fail-closed implementada.
  - **Validation:** Executar teste unitário simulando retorno de `ToolMessage` com nome de ferramenta fora de `DATA_QUERY_TOOLS` e verificar que `data_queried` permanece `False`.

- [COMPLETED] [S014-04] [Low] **Input Type Sanitization and Validation for External Chat History**
  - **Location:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.ask()`
  - **Risk:** O recebimento de sequências não validadas no parâmetro `chat_history` pode levar à injeção de tipos arbitrários no `MessagesState`, causando comportamento indefinido na compilação do prompt do LangGraph ou exceções de serialização.
  - **Fix:** Validar no início do método `ask()` que todos os elementos da lista `chat_history` são instâncias válidas de `BaseMessage` (`HumanMessage`, `AIMessage`, `SystemMessage`), descartando ou convertendo entradas incompatíveis de forma segura.
  - **Validation:** Executar teste passando objetos inválidos na lista de histórico externo e garantir que o agente trata a anomalia sem falhas de execução.

---

### Task 005 — [Test-Integration]: Validate cyclic execution and backwards compatibility

- [COMPLETED] [S014-05] [Low] **Automated Security Regression Suite for LangGraph Cyclic Execution and Resilience**
  - **Location:** `tests/integration/test_sales_agent.py` → `test_langgraph_agentic_self_correction_cyclic_recovery`
  - **Risk:** Regressões futuras no motor de orquestração podem reintroduzir vulnerabilidades de vazamento de logs ou falha de interrupção em loops.
  - **Fix:** Formalizar testes de regressão de segurança que garantam: (1) sanitização de logs CRLF durante autorrecuperação cíclica, (2) ativação correta de `data_queried` apenas em consultas com ferramentas de dados, e (3) interrupção graciosa sem crash em estouro de limite de recursão.
  - **Validation:** Executar a suíte de testes de integração com `python -m pytest tests/integration/test_sales_agent.py` e validar 100% de aprovação.
