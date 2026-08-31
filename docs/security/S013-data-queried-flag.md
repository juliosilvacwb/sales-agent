# S013-data-queried-flag — Security Audit

> **Source Task:** [T013-data-queried-flag.md](../architecture/T013-data-queried-flag.md)  
> **PRD Reference:** [R013-data-queried-flag.md](../business-requirements/R013-data-queried-flag.md)  
> **Test Coverage:** [TEST013-data-queried-flag.md](../tests/TEST013-data-queried-flag.md)

## Security Overview

A auditoria de segurança da especificação técnica de **Data Queried Flag and Response Grounding** (`T013-data-queried-flag.md` / `R013-data-queried-flag.md`) avaliou a integridade do mecanismo de rastreamento determinístico de ferramentas e mitigação de alucinações no Sales Data Analysis Agent. A análise foi fundamentada nos padrões **OWASP Top 10 for LLM Applications (LLM09: Misinformation & Overreliance, LLM01: Prompt Injection, LLM06: Sensitive Information Disclosure)**, **OWASP ASVS V5 (Validation, Sanitization and Output Encoding)**, **CWE-1188 (Insecure Default Initialization / Fail-Open Behavior)** e **CWE-79 (Cross-Site Scripting)**.

O objetivo do recurso T013 é fornecer um sinal determinístico (`data_queried: true`) via LangChain callback interception para que o frontend renderize o selo "Dados Verificados", diferenciando respostas baseadas em dados reais do DuckDB de conversas casuais baseadas no conhecimento probabilístico do modelo.

### Principais Pontos Auditados

1. **Mitigação de Overreliance e Alucinações (OWASP LLM09):** O desacoplamento entre a resposta textual do LLM e a flag booleana estruturada no DTO garante que o usuário final receba um indicador visual não-forjável pela saída gerada pelo modelo.
2. **Isolamento de Estado por Turno (CWE-662 / Session Bleeding):** A instanciação da classe `ToolTrackingCallbackHandler` com escopo estrito por requisição (`request-scoped`) dentro de `SalesAgent.ask()` impede que turnos anteriores vazem estado para novos turnos na mesma sessão de chat.
3. **Fail-Closed em Falhas e Exceções (CWE-754):** O tratamento de exceções em `SalesAgent.ask()` e `WebChatApplicationService.process_chat_message()` força `data_queried = False` e sanitiza mensagens de erro em caso de falha de execução ou estouro do limite de recursão.
4. **Proteção contra Injeção DOM no Frontend (CWE-79 / ASVS V5):** A renderização do selo utiliza `document.createElement()` e ícone SVG estático controlado pelo sistema, enquanto o conteúdo do LLM é higienizado via `DOMPurify.sanitize(marked.parse(content))`.
5. **Vulnerabilidades Identificadas de Fail-Open e Whitelist (CWE-1188 / CWE-184):** Identificou-se um comportamento de fail-open no método `on_tool_end` do callback handler caso o nome da ferramenta seja nulo ou indefinido, bem como fallback permissivo quando a lista de ferramentas monitoradas for vazia.

---

## Vulnerability Log

| ID | Vulnerability / Security Control | Severity | Risk | Impact |
| :--- | :--- | :--- | :--- | :--- |
| S013-01 | Fail-Open Fallback on Unresolved Tool Names in Callback Handler | Medium | Low x Medium | Falha ao resolver o nome da ferramenta em `on_tool_end` ativando indevidamente a flag de dados verificados (falso positivo de grounding). |
| S013-02 | Permissive Toolset Whitelist Fallback on Empty data_tools | Low | Low x Low | Configuração com `data_tools` vazia resultando no tratamento indiscriminado de qualquer ferramenta como consulta ao banco de dados. |
| S013-03 | Synthetic UI Badge Spoofing Defense in Depth | Low | Low x Low | Tentativa do LLM de simular o selo de verificação através de formatação Markdown/HTML no corpo da mensagem. |

---

## Refinement Tasks

### Task 002 — [UseCase]: Implement ToolTrackingCallbackHandler for LangChain

- [COMPLETED] [S013-01] [Medium] **Fail-Closed Refactoring for Unresolved Tool Names in ToolTrackingCallbackHandler**
  - **Location:** `src/adapter/inbound/llm/sales_agent.py` → `ToolTrackingCallbackHandler.on_tool_end()`
  - **Risk:** Nas linhas 147-148 de `sales_agent.py`, a cláusula `else: self.has_queried_data = True` faz com que qualquer evento `on_tool_end` sem o parâmetro `name` ou `serialized` explícito ative a flag de consulta de dados. Caso ferramentas utilitárias internas ou plugins futuros sem metadados disparem o callback, o sistema marcará a resposta como "Dados Verificados" indevidamente, quebrando o princípio do menor privilégio e o design fail-closed (CWE-1188 / OWASP LLM09).
  - **Fix:** Adotar política estritamente fail-closed em `on_tool_end()`. A flag `self.has_queried_data` só deve ser atribuída como `True` se `tool_name` for resolvido com sucesso e constar expressamente no conjunto `self.data_tools`. Se `tool_name` for `None` ou ausente, a flag não deve ser alterada.
  - **Validation:** Executar teste unitário disparando `handler.on_tool_end(output="result", name=None)` e validar que `handler.has_queried_data` permanece `False`.

- [COMPLETED] [S013-02] [Low] **Enforce Non-Empty Whitelist Check on data_tools Collection**
  - **Location:** `src/adapter/inbound/llm/sales_agent.py` → `ToolTrackingCallbackHandler.on_tool_start()` e `on_tool_end()`
  - **Risk:** A condição `if not self.data_tools or tool_name in self.data_tools:` interpreta um conjunto `self.data_tools` vazio como permissão total (wildcard), considerando qualquer ferramenta como ferramenta de dados.
  - **Fix:** Ajustar a verificação para exigir correspondência estrita na whitelist: `if self.data_tools and tool_name in self.data_tools:`. Caso `self.data_tools` seja um conjunto vazio, nenhuma ferramenta deve ser reconhecida como geradora de dados verificados.
  - **Validation:** Testar `ToolTrackingCallbackHandler(data_tools=set())` com ferramentas quaisquer e assegurar que `has_queried_data` permanece `False`.

---

### Task 005 — [Adapter-Web]: Update Frontend UI to render Verified Badge

- [COMPLETED] [S013-03] [Low] **DOM Sanitization and Synthetic Badge Spoofing Hardening**
  - **Location:** `src/adapter/inbound/web/static/app.js` → `addMessage()`
  - **Risk:** Respostas do LLM contendo tags HTML ou classes CSS personalizadas poderiam tentar mimetizar o elemento `.verified-data-badge` para induzir o usuário em erro quando a flag `data_queried` for `false`.
  - **Fix:** Garantir que o DOMPurify sanitize todas as tags no corpo da mensagem sem preservar classes reservadas do sistema (como `.verified-data-badge`), assegurando que apenas a lógica programática em JavaScript injete o badge autêntico baseado estritamente na propriedade `data.data_queried === true`.
  - **Validation:** Injetar respostas contendo `<div class="verified-data-badge">Falso Selo</div>` no bot message handler e verificar que o elemento injetado é neutralizado pelo sanitizer e não gera conflito com o selo oficial.
