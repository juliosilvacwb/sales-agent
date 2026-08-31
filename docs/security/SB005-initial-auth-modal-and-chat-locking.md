# SB005-initial-auth-modal-and-chat-locking — Auditoria de Segurança

> **Tarefa de Origem:** [B005-initial-auth-modal-and-chat-locking.md](../incidents/B005-initial-auth-modal-and-chat-locking.md)

## Visão Geral de Segurança

A implementação da especificação [B005-initial-auth-modal-and-chat-locking.md](../incidents/B005-initial-auth-modal-and-chat-locking.md) foi auditada sob os pilares de Application Security (AppSec), OWASP Top 10 e arquitetura Zero Trust para interfaces cliente.

As alterações eliminam riscos de exposição estática de credenciais (CWE-798), ocultam a topologia interna de microsserviços do formulário de login (CWE-200) e implementam uma postura de segurança **Fail-Closed** no frontend, bloqueando a interface de chat por padrão e forçando a autenticação imediata via modal interativa.

### Achados Positivos de Segurança

1. **Eliminação de Hardcoded Credentials (CWE-798):** Remoção do atributo estático `value="admin"` no formulário de login de `index.html`, substituindo-o por `placeholder` e atributos semânticos (`autocomplete="username"`, `autocomplete="current-password"`).
2. **Encapsulamento de Infraestrutura (CWE-200):** Ocultação da rota interna do Auth Service da interface visual, prevenindo manipulação arbitrária de endpoints no formulário de login e encapsulando o fallback (`window.AUTH_SERVICE_URL || "http://localhost:8001"`) de forma segura no script cliente.
3. **Fail-Closed Client UI:** A interface inicia com `#chat-input` e `#send-btn` com o atributo `disabled` diretamente no HTML estático e aciona a modal de autenticação automaticamente na ausência de token JWT válido em `sessionStorage`.
4. **Tratamento de Sessão Expirada / 401 Unauthorized:** Interceptação reativa do status HTTP 401 que purga o token comprometido/expirado, bloqueia os controles de chat e reabre a modal solicitando reautenticação.
5. **Mitigação de DOM XSS (CWE-79):** Preservação do pipeline de higienização com `DOMPurify` e `marked` com remoção de badges forjadas e escape de entradas de usuário via `textContent`.

## Registro de Vulnerabilidades

| ID | Vulnerabilidade | Severidade | Risco | Impacto |
| :--- | :--- | :--- | :--- | :--- |
| SB005-01 | Credenciais Padrão Pré-preenchidas no HTML | Média | Médio x Médio | Risco de login acidental com credenciais default (CWE-798). Mitigado. |
| SB005-02 | Exposição de Endpoint do Microsserviço na UI | Baixa | Baixo x Médio | Divulgação desnecessária de rota interna e risco de desvio de endpoint (CWE-200). Mitigado. |
| SB005-03 | Falta de Bloqueio Inicial de Chat (Fail-Open) | Média | Médio x Alto | Envio de mensagens não autenticadas resultando em rejeição ou erro 401 não tratado (CWE-285). Mitigado. |

## Tarefas de Refinamento

### Task 001 - Auditoria de Credenciais e Campos do Formulário de Login

- [COMPLETED] [SB005-01] [Medium] **Remoção de Credenciais Hardcoded e Validação de Atributos de Formulário**
  - **Localização:** `src/adapter/inbound/web/static/index.html` → `<form id="login-form">`
  - **Risco:** Valores pré-preenchidos como `admin` ou senhas padrão expostas no HTML facilitam acessos não autorizados e confusão de privilégios.
  - **Correção:** Garantir que todos os campos de entrada de credenciais iniciem vazios com placeholders claros e tipos semânticos (`type="password"`).
  - **Validação:** Verificar via teste automatizado que `value="admin"` e `value="changeme"` não estão presentes no DOM inicial.

### Task 002 - Encapsulamento da Configuração do Auth Service

- [COMPLETED] [SB005-02] [Low] **Ocultação e Encapsulamento da URL de Autenticação**
  - **Localização:** `src/adapter/inbound/web/static/app.js` → `AUTH_SERVICE_URL`
  - **Risco:** Campos de input para URL do serviço de autenticação permitem que usuários finais alterem acidentalmente ou maliciosamente o destino de autenticação (SSRF/Credential Harvesting).
  - **Correção:** Remover campos visíveis do formulário HTML e gerenciar o endpoint via constante configurável no script cliente.
  - **Validação:** Confirmar que elementos `<label for="auth-url">` e `<input id="auth-url">` foram removidos e que a constante interna gerencia o endpoint.

### Task 003 - Implementação de Postura Fail-Closed e Gestão de Sessão

- [COMPLETED] [SB005-03] [Medium] **Bloqueio de Chat Inicial e Invalidação Reativa no Erro 401**
  - **Localização:** `src/adapter/inbound/web/static/app.js` → `updateAuthUI()`, `sendMessage()`, `logoutBtn`
  - **Risco:** Interfaces que permanecem abertas sem token JWT induzem falhas de autorização e degradação de experiência ao enviar requisições não autenticadas.
  - **Correção:** Definir estado inicial bloqueado (`disabled`) no HTML/JS, disparar modal automaticamente na ausência de token e purgar sessão no recebimento de 401 Unauthorized ou acionamento de logout.
  - **Validação:** Executar suite `tests/integration/test_auth_modal_ui_incident_b005.py` garantindo que todos os fluxos de bloqueio e desautenticação estão validados.
