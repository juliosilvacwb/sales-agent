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
    index_path = os.path.join(STATIC_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        index_html = f.read()

    assert "Não autenticado" in index_html, "index.html initial rendered status must be unauthenticated."
    assert 'id="chat-input"' in index_html and "disabled" in index_html, (
        "index.html chat input must be initially disabled."
    )
    assert 'id="send-btn"' in index_html and "disabled" in index_html, (
        "index.html send button must be initially disabled."
    )

    app_js_path = os.path.join(STATIC_DIR, "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        app_js = f.read()

    # app.js must check getJwtToken() on initialization to open modal and lock chat
    assert "chatInput.disabled" in app_js, (
        "app.js must control chat input disabled state based on authentication."
    )
    assert "sendBtn.disabled" in app_js, (
        "app.js must control send button disabled state based on authentication."
    )
    assert "agent-status-text" in app_js or "agentStatusText" in app_js, (
        "app.js must dynamically update agent status text based on authentication."
    )
    assert "openModal" in app_js and "!getJwtToken()" in app_js, (
        "app.js must automatically open modal if no JWT token exists on startup."
    )
    assert "AUTH_SERVICE_URL" in app_js, (
        "app.js must encapsulate the Auth Service URL internally."
    )


def test_auth_modal_form_attributes_and_security():
    """
    Test that login modal form elements are properly configured without hardcoded passwords
    and with required security/accessibility attributes.
    """
    index_path = os.path.join(STATIC_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'id="auth-password"' in content, "Password field must exist."
    assert 'type="password"' in content, "Password input must have type='password'."
    assert 'value="changeme"' not in content, "Password must not have hardcoded value."
    assert 'autocomplete="username"' in content, "Username field should have autocomplete."
    assert 'autocomplete="current-password"' in content, "Password field should have autocomplete."


def test_logout_and_unauthenticated_flow_disables_chat_and_resets_status():
    """
    Test that app.js handles logout, resetting JWT token, locking chat, and resetting status.
    """
    app_js_path = os.path.join(STATIC_DIR, "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        app_js = f.read()

    assert "logoutBtn.addEventListener" in app_js, "Logout button must have an event listener registered."
    assert "setJwtToken(null)" in app_js, "Logout must invoke setJwtToken(null)."
    assert 'sessionStorage.removeItem("jwt_access_token")' in app_js, "setJwtToken(null) must clear session storage."
    assert 'agentStatusText.textContent = "Não autenticado"' in app_js, (
        "updateAuthUI must set status to 'Não autenticado' when unauthenticated."
    )


def test_auth_401_interception_and_pending_message_handling():
    """
    Test that app.js handles 401 Unauthorized API responses by triggering re-authentication
    and retaining pending messages.
    """
    app_js_path = os.path.join(STATIC_DIR, "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        app_js = f.read()

    assert "response.status === 401" in app_js, "app.js must intercept 401 HTTP response status."
    assert "pendingMessage = message" in app_js, "app.js must store pending message on 401."
    assert "openModal(" in app_js, "app.js must display modal on 401 with appropriate message."

