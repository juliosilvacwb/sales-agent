# Resumo do Incidente: B001 - Network Error Web Chat

- **Cobertura de Testes:** [TEST001-network-error-web-chat.md](../tests/TEST001-network-error-web-chat.md)
- **Auditoria de Segurança:** [S001-network-error-web-chat.md](../security/S001-network-error-web-chat.md)

A interface de chat web exibe a mensagem "Network error. Please try again." quando os usuários tentam enviar uma requisição de chat.

**Análise Técnica da Causa Raiz:**
A requisição `fetch` do frontend recebe um erro HTTP 500 Internal Server Error, o qual é capturado de forma genérica como erro de rede. No backend, esse erro 500 é causado por um `TypeError: SalesAgent.__init__() missing 2 required positional arguments: 'llm' and 'tools'`.

Em `src/adapter/inbound/web/chat_controller.py`, o `agent_factory` instancia `SalesAgent()` sem fornecer as dependências obrigatórias (`llm` e `tools`). Quando uma nova sessão de chat é inicializada em `WebChatApplicationService.process_chat_message()`, essa fábrica com falha é acionada. Além disso, a invocação da fábrica (`self._active_sessions[request.session_id] = self._agent_factory()`) estava localizada *fora* do bloco `try...except` no serviço. Como resultado, a exceção se propaga até o FastAPI, resultando em um erro HTTP 500 não tratado em vez de um payload de erro JSON amigável.

## Script de Reprodução (OBRIGATÓRIO)

```python
import pytest
from fastapi.testclient import TestClient
from src.adapter.inbound.web.main import app

client = TestClient(app)

def test_web_chat_network_error_reproduction():
    """
    Automated Reproduction Test for the Web Chat Network Error.
    When sending a chat request to a new session, the API crashes with HTTP 500
    because of a TypeError during SalesAgent initialization.
    """
    response = client.post(
        "/chat",
        json={"message": "hello", "session_id": "test-session-123"}
    )

    # We expect the test to FAIL here right now because response.status_code is 500
    # instead of the expected 200 OK.
    # The Engineer Agent will make this test pass by fixing the DI configuration
    # and ensuring the exception handling wraps the agent factory properly.
    assert response.status_code == 200, f"Expected 200 OK but got {response.status_code}"

    data = response.json()
    assert data["status"] in ("success", "error")
```

## Checklist de Correção (Tarefas Atômicas)

- [COMPLETED] Task 001 - [Test] Implementar o script de reprodução em `tests/integration/test_web_chat_incident_b001.py` e confirmar a falha (Red).
- [COMPLETED] Task 002 - [Logic] Corrigir `agent_factory` em `src/adapter/inbound/web/chat_controller.py` para injetar corretamente as instâncias de `llm` e `tools` ao instanciar `SalesAgent`.
- [COMPLETED] Task 003 - [Security/Perf] Mover `self._active_sessions[request.session_id] = self._agent_factory()` para dentro do bloco `try...except` em `src/application/service/web_chat_application_service.py` para garantir que qualquer falha de inicialização retorne uma resposta de erro estruturada em vez de derrubar o servidor.
