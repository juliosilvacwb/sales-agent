# Resumo do Incidente: B005 - Initial Auth Modal e Chat Locking

- **Cobertura de Testes:** [TESTB005-initial-auth-modal-and-chat-locking.md](../tests/TESTB005-initial-auth-modal-and-chat-locking.md)
- **Auditoria de Segurança:** [SB005-initial-auth-modal-and-chat-locking.md](../security/SB005-initial-auth-modal-and-chat-locking.md)

Ao inicializar a interface web da aplicação, o sistema exibe o status como "Online" e mantém o campo de chat e botão de envio ativos para interação, mesmo quando o usuário não possui token JWT autenticado. Além disso, a modal de autenticação permanece oculta no carregamento inicial, o campo de usuário está pré-preenchido com "admin" em vez de vazio com placeholder, e a URL da API de autenticação é exibida desnecessariamente na tela de login.

**Análise Técnica da Causa Raiz:**

1. **Estado Inicial e Bloqueio de Chat:** Em `src/adapter/inbound/web/static/index.html` e `src/adapter/inbound/web/static/app.js`, o indicador de status é renderizado estaticamente como "Online", a modal `#auth-modal` inicia com `style="display: none;"` e a função de inicialização `updateAuthUI()` não verifica a ausência do token JWT (`getJwtToken()`) para abrir a modal de autenticação automaticamente nem desabilita os controles de entrada do chat (`#chat-input`, `#send-btn`).
2. **Campo de Usuário Pré-preenchido:** Em `src/adapter/inbound/web/static/index.html`, o elemento `<input id="auth-username">` possui o atributo `value="admin"` definido de forma estática no HTML em vez de apresentar um `placeholder` descritivo com valor inicial vazio.
3. **Exposição da URL do Auth Service:** O formulário de login contém um grupo de campos visível (`<label for="auth-url">` e `<input id="auth-url">`) expondo a rota interna do microsserviço de autenticação na UI em vez de encapsular o endpoint no client JavaScript de forma transparente ou configurável.

## Script de Reprodução (OBRIGATÓRIO)

```python
"""Automated reproduction tests for Incident B005: Initial Auth Modal and UI Cleanup."""
import os
import re
import pytest

STATIC_DIR = os.path.join(
    os.path.dirname(__file__),
    "../../src/adapter/inbound/web/static"
)


def test_auth_username_field_is_empty_with_placeholder():
    """
    Reproduction test for Incident B005:
    The username field must NOT be pre-filled with value="admin",
    and must contain a placeholder.
    """
    index_path = os.path.join(STATIC_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The username field must not be pre-filled with admin
    assert 'id="auth-username" value="admin"' not in content, (
        "Username field is pre-filled with value='admin' instead of being empty with a placeholder."
    )
    assert 'id="auth-username"' in content
    has_placeholder = (
        re.search(r'id="auth-username"[^>]*placeholder=', content)
        or re.search(r'placeholder=[^>]*id="auth-username"', content)
    )
    assert has_placeholder, "Username field must have a placeholder attribute."


def test_auth_url_field_not_visible_in_login_modal():
    """
    Reproduction test for Incident B005:
    The login modal must not display the Auth Service URL field.
    """
    index_path = os.path.join(STATIC_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert '<label for="auth-url">Auth Service URL</label>' not in content, (
        "Auth Service URL label is visible on the login screen."
    )
    assert '<input type="text" id="auth-url"' not in content, (
        "Auth Service URL input is visible on the login screen."
    )


def test_initial_state_requires_auth_and_disables_chat():
    """
    Reproduction test for Incident B005:
    The application must not show 'Online' unconditionally when unauthenticated,
    and app.js must handle automatic modal opening and chat locking when unauthenticated.
    """
    app_js_path = os.path.join(STATIC_DIR, "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        app_js = f.read()

    # app.js must check getJwtToken() on initialization to open modal and lock chat
    assert "chatInput.disabled" in app_js, (
        "app.js must control chat input disabled state based on authentication."
    )
    assert "agent-status-text" in app_js or "agentStatusText" in app_js, (
        "app.js must dynamically update agent status text based on authentication."
    )
```

## Checklist de Correção (Tarefas Atômicas)

- [COMPLETED] Task 001 - [Test] Implementar o script de reprodução em `tests/integration/test_auth_modal_ui_incident_b005.py` e confirmar a falha (Red).
- [COMPLETED] Task 002 - [Logic] Ajustar `src/adapter/inbound/web/static/index.html` para remover `value="admin"`, adicionar `placeholder="Digite seu usuário..."`, remover a exibição do campo `#auth-url` e definir o estado visual inicial como não autenticado.
- [COMPLETED] Task 003 - [Logic] Ajustar `src/adapter/inbound/web/static/app.js` para abrir a modal automaticamente no carregamento quando não autenticado, bloquear o chat (`chatInput.disabled = true`, `sendBtn.disabled = true`) até a autenticação ser concluída, gerenciar a URL padrão do auth service internamente e atualizar dinamicamente o status no header ("Não autenticado" vs "Online").
- [COMPLETED] Task 004 - [Security/Perf] Validar que o fluxo de renovação/logout reabilita o bloqueio da interface e executar a suíte completa de testes para garantir ausência de regressões.
