# S009-agentic-self-correction — Security Audit

> **Source Task:** [T009-agentic-self-correction.md](../architecture/T009-agentic-self-correction.md)  
> **PRD Reference:** [R009-agentic-self-correction.md](../business-requirements/R009-agentic-self-correction.md)  
> **Product Strategy:** [PS009-agentic-self-correction.md](../product-strategy/PS009-agentic-self-correction.md)  
> **Test Coverage:** [TEST009-agentic-self-correction.md](../tests/TEST009-agentic-self-correction.md)

## Security Overview

A auditoria de segurança da especificação técnica de Autocorreção Agentica e Resiliência a Erros (`T009-agentic-self-correction.md` / `R009-agentic-self-correction.md`) avaliou a conformidade arquitetural e de implementação com os padrões **OWASP Top 10 for LLM Applications (LLM01: Prompt Injection, LLM04: Model Denial of Service, LLM06: Sensitive Information Disclosure)**, **OWASP ASVS V5 (Validation and Sanitization)**, e boas práticas de proteção contra vazamento de informações (CWE-209, CWE-532) e injeção de logs (CWE-117).

O mecanismo de autocorreção substitui retornos de erro como strings planas pelo lançamento de `ToolException` nativo da LangChain, ativando um loop de re-diagnóstico pelo modelo LLM. Os seguintes pilares de segurança foram auditados:

1. **Prevenção de Vazamento de Informações e Paths do Host (CWE-209 / CWE-532 / OWASP LLM06):** Sanitização estrita de mensagens de erro geradas por DuckDB e Python antes de serem encapsuladas em `ToolException`, expurgando caminhos absolutos de diretórios locais (`[REDACTED_PATH]`) e variáveis de ambiente.
2. **Mitigação de Negação de Serviço e Consumo Excessivo de Recursos (OWASP LLM04 / CWE-400):** Fixação de teto de recursão (`recursion_limit`) e orçamento estrito de no máximo 3 tentativas de autocorreção por turno do usuário, evitando loops infinitos e exaustão de orçamento de tokens.
3. **Isolamento de Erros e Defesa Contra Injeção Indireta de Prompt (OWASP LLM01 / CWE-77):** Blindagem do `SYSTEM_PROMPT` para que mensagens de erro das ferramentas sejam tratadas puramente como sinais diagnósticos estruturados, nunca executando instruções embutidas em dados ou queries SQL inválidas.
4. **Política de Zero Exposição de Erros Técnicos ao Usuário Final (Regra BR01 / CWE-209):** Fallback determinístico e padronizado (`FALLBACK_ERROR_MESSAGE`) para contingência corporativa, impedindo a exibição de stack traces, erros de banco de dados ou detalhes internos de infraestrutura ao usuário.
5. **Sanitização de Telemetria e Prevenção de Log Forging (CWE-117):** Higienização de quebras de linha e caracteres de controle no handler `_handle_tool_error` antes da emissão de logs com o marcador `[AGENT_SELF_CORRECTION]`.
6. **Validação Defensiva de Parâmetros nas Domain Tools (CWE-20 / CWE-1287):** Tratamento rigoroso de tipos, formatos de data (DD/MM/YYYY e ISO) e limites de paginação (`safe_limit`), garantindo que entradas inválidas disparem exceções tratadas de forma previsível.

---

## Vulnerability Log

| ID | Vulnerability / Security Control | Severity | Risk | Impact |
| :--- | :--- | :--- | :--- | :--- |
| S009-01 | Unbounded Agent Recursion & Token Budget Depletion (DoS) | High | High x High | Loop infinito de chamadas de ferramentas consumindo orçamento de tokens da API do modelo. |
| S009-02 | Sensitive Host Path & System Info Disclosure in Error Signals | High | Medium x High | Exposição de diretórios locais, estrutura de arquivos e ambiente do host no contexto do LLM. |
| S009-03 | Indirect Prompt Injection via Reflected Tool Error Payloads | Medium | High x Medium | Manipulação do fluxo de autocorreção por instruções maliciosas contidas em erros de consulta. |
| S009-04 | Log Injection & CRLF Forging in Observability Telemetry | Medium | Medium x Medium | Falsificação de logs ou corrupção de telemetria SIEM através de erros com quebra de linha. |
| S009-05 | Technical Stack Trace & Raw Database Error Exposure to User | Low | Medium x Low | Vazamento de detalhes internos do motor DuckDB ou falhas de runtime na resposta final ao usuário. |
| S009-06 | Denial of Service & Type Confusion via Unchecked Tool Arguments | Low | Medium x Low | Falhas não tratadas de parsing de datas ou estouro de limites de registros em domain tools. |

---

## Refinement Tasks

### Task 001 — Update SYSTEM_PROMPT with self-correction instructions

- [COMPLETED] [S009-03] [Medium] **Isolamento Contextual e Blindagem Contra Prompt Injection no Loop de Erro**
  - **Location:** `src/adapter/inbound/llm/sales_agent.py` → `SYSTEM_PROMPT`
  - **Risk:** Mensagens de erro contendo trechos de consultas enviadas pelo usuário podem conter instruções de prompt injection tentando induzir o LLM a ignorar restrições de segurança durante a fase de autocorreção.
  - **Fix:** Reforçar as diretrizes de autocorreção no `SYSTEM_PROMPT` para instruir o modelo a tratar erros de ferramentas estritamente como sinais técnicos de validação/esquema, mantendo fidelidade estrita às restrições de leitura analítica (SELECT/WITH) e nunca executando comandos embutidos nas mensagens de erro.
  - **Validation:** Testar cenários com injeção de prompt dentro de queries SQL com erro sintático proposital, assegurando que o agente apenas corrija a sintaxe sem violar as regras do sistema.

---

### Task 002 — Refactor SecuredSQLQueryTool to raise sanitized ToolException

- [COMPLETED] [S009-02] [High] **Sanitização Reforçada de Caminhos de Arquivos e Detalhes do Host em Exceções SQL**
  - **Location:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `_run()`
  - **Risk:** Exceções do DuckDB ou do parser de SQL podem conter caminhos absolutos do sistema de arquivos do servidor (ex: caminhos com espaços entre aspas ou variáveis de ambiente), expondo topologia de diretórios ao contexto do modelo.
  - **Fix:** Garantir que a regex de redação cubra caminhos POSIX, Windows e URIs com espaços ou delimitadores (`re.sub(r'([a-zA-Z]:[\\/][^\s:\'"]+|/[^\s:\'"]+|[A-Z]:\\[^\s:\'"]+)', '[REDACTED_PATH]', raw_err)`), substituindo qualquer caminho por `[REDACTED_PATH]` antes de instanciar `ToolException`.
  - **Validation:** Executar testes unitários com mensagens de erro simuladas contendo caminhos Windows e POSIX com e sem espaços, validando que todas as ocorrências são redigidas.

---

### Task 003 — Refactor domain_tools.py to raise ToolException

- [COMPLETED] [S009-06] [Low] **Limites Defensivos e Tratamento Resiliente de Parâmetros de Entrada**
  - **Location:** `src/adapter/inbound/llm/domain_tools.py` → `_parse_date()`, `get_top_locations_by_volume()`
  - **Risk:** Formatos de data inválidos ou valores extremos de paginação podem causar exceções de runtime não controladas ou sobrecarga de memória analítica.
  - **Fix:** Assegurar que `_parse_date` converta `ValueError` em `ToolException` com orientação em português dos formatos aceitos (DD/MM/YYYY ou YYYY-MM-DD), e manter `safe_limit = max(1, min(int(limit), 100))` para evitar consultas exorbitantes.
  - **Validation:** Validar via `test_domain_tool_date_validation_self_correction_e2e` e testes unitários de limites de parâmetros.

---

### Task 004 — Implement custom error handler for Telemetry

- [COMPLETED] [S009-04] [Medium] **Sanitização de Quebras de Linha e Prevenção de Log Injection em Telemetria**
  - **Location:** `src/adapter/inbound/llm/sales_agent.py` → `_handle_tool_error()`
  - **Risk:** Mensagens de erro de ferramentas contendo caracteres de quebra de linha (`\r`, `\n`) podem permitir Log Injection / Log Forging ao registrar logs com o prefixo `[AGENT_SELF_CORRECTION]`.
  - **Fix:** Normalizar a mensagem de erro no handler substituindo quebras de linha e caracteres de controle por espaços simples antes da chamada `logger.warning()`.
  - **Validation:** Testes unitários passando strings de erro com `\n` e `\r` para `_handle_tool_error()`, verificando emissão de log em linha única sanitizada.

---

### Task 005 — Configure SalesAgent executor with retry ceilings

- [COMPLETED] [S009-01] [High] **Imposição Rigorosa de Teto de Recursão e Orçamento de Tentativas**
  - **Location:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.ask()`
  - **Risk:** Se o modelo entrar em um loop de falhas contínuas com ferramentas sucessivas e o executor não possuir limite de recursão explícito, o agente continuará consumindo tokens indefinidamente (Denial of Service / Denial of Wallet).
  - **Fix:** Configurar explicitamente `config={"recursion_limit": 8}` na invocação `self._executor.invoke({"messages": messages}, config=...)` para garantir que após no máximo 3 iterações completas de ferramenta/pensamento o fluxo seja abortado para o bloco de fallback.
  - **Validation:** Validar via `test_retry_exhaustion_returns_polite_fallback_e2e` assegurando terminação graciosa e deterministicamente contida.

- [COMPLETED] [S009-05] [Low] **Garantia de Zero Vazamento de Stack Trace via Fallback Corporativo**
  - **Location:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.ask()`, `FALLBACK_ERROR_MESSAGE`
  - **Risk:** Falhas catastróficas ou esgotamento de tentativas podem expor exceções Python ou stack traces técnicos ao usuário final.
  - **Fix:** Manter o bloco protetor `try...except Exception` capturando qualquer falha no executor e retornando exclusivamente a constante `FALLBACK_ERROR_MESSAGE`.
  - **Validation:** Validar que testes de exaustão de retries (`test_retry_exhaustion_returns_polite_fallback_e2e`) não contêm termos como `Traceback`, `Catalog Error`, `DuckDB` ou `Exception`.
