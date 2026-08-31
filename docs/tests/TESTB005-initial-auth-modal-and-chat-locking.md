# TESTB005-initial-auth-modal-and-chat-locking — Especificação de Cobertura de Testes

> **Tarefa de Origem:** [B005-initial-auth-modal-and-chat-locking.md](../incidents/B005-initial-auth-modal-and-chat-locking.md)

## Visão Geral de Cobertura

Esta especificação de testes valida a implementação das correções do incidente B005. Ela assegura que a aplicação web do Sales Agent implemente proteção inicial contra acessos não autenticados, prevenindo envio de mensagens no chat antes da obtenção do token JWT, exibindo a modal de autenticação automaticamente na inicialização desautenticada, ocultando campos sensíveis ou desnecessários da UI e mantendo consistência de estado durante renovação e logout.

## Checklist de Testes

### Task 001 - Implementar o script de reprodução em tests/integration/test_auth_modal_ui_incident_b005.py

- [COMPLETED] [TESTB005-01] [Integration] **Validação de Ausência de Usuário Pré-preenchido e Presença de Placeholder**
  - **Target:** `tests/integration/test_auth_modal_ui_incident_b005.py` → `test_auth_username_field_is_empty_with_placeholder()`
  - **Scenario:** O campo de usuário no formulário de login não deve conter o atributo estático `value="admin"` e deve conter placeholder explicativo.
  - **Arrange:** Ler o arquivo estático `src/adapter/inbound/web/static/index.html`.
  - **Act:** Validar a ausência da string `value="admin"` e a presença de atributo `placeholder`.
  - **Assert:** O campo `#auth-username` existe com placeholder e sem valor pré-preenchido.
  - **Priority:** P0 (Critical)

- [COMPLETED] [TESTB005-02] [Integration] **Validação de Remoção da URL do Auth Service na Interface**
  - **Target:** `tests/integration/test_auth_modal_ui_incident_b005.py` → `test_auth_url_field_not_visible_in_login_modal()`
  - **Scenario:** O formulário da modal de autenticação não deve expor campos de URL do Auth Service ao usuário.
  - **Arrange:** Ler o arquivo estático `src/adapter/inbound/web/static/index.html`.
  - **Act:** Verificar ausência de `<label for="auth-url">` e `<input id="auth-url">`.
  - **Assert:** Elementos de configuração de URL não são exibidos no HTML.
  - **Priority:** P1 (High)

- [COMPLETED] [TESTB005-03] [Integration] **Validação de Bloqueio Inicial do Chat e Status Não Autenticado**
  - **Target:** `tests/integration/test_auth_modal_ui_incident_b005.py` → `test_initial_state_requires_auth_and_disables_chat()`
  - **Scenario:** No carregamento inicial sem autenticação, o chat deve iniciar bloqueado e o status deve ser "Não autenticado".
  - **Arrange:** Ler os arquivos `index.html` e `app.js`.
  - **Act:** Verificar se os inputs iniciam desabilitados e se o JS verifica `getJwtToken()` no startup para acionar `openModal()`.
  - **Assert:** `chatInput.disabled`, `sendBtn.disabled`, texto "Não autenticado" e chamada de `openModal()` estão devidamente configurados.
  - **Priority:** P0 (Critical)

### Task 002 - Ajustar src/adapter/inbound/web/static/index.html

- [COMPLETED] [TESTB005-04] [Unit] **Validação de Atributos de Segurança e Acessibilidade no Formulário de Login**
  - **Target:** `tests/integration/test_auth_modal_ui_incident_b005.py` → `test_auth_modal_form_attributes_and_security()`
  - **Scenario:** Os campos de senha e usuário devem conter atributos semânticos corretos (`type="password"`, `autocomplete`) e nenhuma credencial default embutida no HTML.
  - **Arrange:** Carregar o conteúdo de `src/adapter/inbound/web/static/index.html`.
  - **Act:** Inspecionar os atributos de `<input id="auth-password">` e `<input id="auth-username">`.
  - **Assert:** Atributos `type="password"`, `autocomplete="username"`, `autocomplete="current-password"` presentes e ausência de `value="changeme"`.
  - **Priority:** P1 (High)

### Task 003 - Ajustar src/adapter/inbound/web/static/app.js

- [COMPLETED] [TESTB005-05] [Unit] **Validação de Fluxo de Desautenticação e Bloqueio Reativo de UI**
  - **Target:** `tests/integration/test_auth_modal_ui_incident_b005.py` → `test_logout_and_unauthenticated_flow_disables_chat_and_resets_status()`
  - **Scenario:** Ao desautenticar ou clicar em logout, a sessão é limpa no storage e o chat é bloqueado imediatamente.
  - **Arrange:** Inspecionar a lógica de `setJwtToken(null)` e o listener do botão `logoutBtn` em `app.js`.
  - **Act:** Verificar as operações de remoção no `sessionStorage` e atualização textual de status.
  - **Assert:** `sessionStorage.removeItem` é executado, inputs de chat são desabilitados e o status passa a ser "Não autenticado".
  - **Priority:** P0 (Critical)

### Task 004 - Validar que o fluxo de renovação/logout reabilita o bloqueio da interface

- [COMPLETED] [TESTB005-06] [Integration] **Validação de Interceptação de HTTP 401 e Reabertura Automática da Modal**
  - **Target:** `tests/integration/test_auth_modal_ui_incident_b005.py` → `test_auth_401_interception_and_pending_message_handling()`
  - **Scenario:** Quando o backend retorna 401 Unauthorized para uma requisição de chat, o token expirado é invalidado, a mensagem digitada é retida e a modal de login é aberta.
  - **Arrange:** Inspecionar o bloco de tratamento de status HTTP em `sendMessage()` em `app.js`.
  - **Act:** Verificar o tratamento para `response.status === 401`.
  - **Assert:** `setJwtToken(null)` é invocado, `pendingMessage` armazena a mensagem e `openModal()` é acionado com aviso de autenticação necessária.
  - **Priority:** P0 (Critical)
