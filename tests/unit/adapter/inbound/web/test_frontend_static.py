"""Unit tests for Frontend static assets, sanitization, and client script integrity."""
from pathlib import Path


def test_frontend_html_structure_and_assets():
    """Verify presence and key structure of index.html and styles.css including DOMPurify and crossorigin."""
    base_dir = Path(__file__).resolve().parents[5] / "src" / "adapter" / "inbound" / "web" / "static"
    index_html = base_dir / "index.html"
    styles_css = base_dir / "styles.css"

    assert index_html.exists(), "index.html must exist in static directory"
    assert styles_css.exists(), "styles.css must exist in static directory"

    html_content = index_html.read_text(encoding="utf-8")
    
    # Required element IDs
    assert 'id="chat-form"' in html_content
    assert 'id="chat-input"' in html_content
    assert 'id="chat-messages"' in html_content
    assert 'id="typing-indicator"' in html_content
    assert 'id="error-banner"' in html_content
    
    # External libraries with security attributes
    assert "marked.min.js" in html_content
    assert "purify.min.js" in html_content
    assert 'crossorigin="anonymous"' in html_content

    # CSS tokens and component styles
    css_content = styles_css.read_text(encoding="utf-8")
    assert "--bg-primary" in css_content
    assert ".chat-container" in css_content
    assert ".message" in css_content


def test_frontend_app_js_logic_integrity():
    """Verify client-side logic integrity, DOMPurify sanitization, and resilience in app.js."""
    base_dir = Path(__file__).resolve().parents[5] / "src" / "adapter" / "inbound" / "web" / "static"
    app_js = base_dir / "app.js"

    assert app_js.exists(), "app.js must exist in static directory"

    js_content = app_js.read_text(encoding="utf-8")

    # Session ID generation
    assert "crypto.randomUUID" in js_content or "randomUUID" in js_content
    assert "sessionStorage" in js_content

    # XSS Protection: textContent for user input and DOMPurify for bot responses
    assert "textContent" in js_content
    assert "DOMPurify.sanitize" in js_content
    assert "marked.parse" in js_content

    # Resilience: AbortController and timeout handling
    assert "AbortController" in js_content
    assert "signal" in js_content
    assert "error-banner" in js_content or "errorBanner" in js_content
