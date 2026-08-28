# S002-web-chat-interface — Security Audit

> **Source Task:** [T002-web-chat-interface.md](../architecture/T002-web-chat-interface.md)  
> **Test Coverage:** [TEST002-web-chat-interface.md](../tests/TEST002-web-chat-interface.md)

## Security Overview

A interface web de chat do Sales Data Analysis Agent (`T002-web-chat-interface.md` / `R002-web-chat-interface.md` / `TEST002-web-chat-interface.md`) foi avaliada sob a perspectiva de Application Security (AppSec), SAST (Static Application Security Testing), DAST (Dynamic Application Security Testing), OWASP Top 10 Web Application Security Risks e OWASP Top 10 for LLM Applications.

### Pontos Positivos Identificados

- **Isolamento de Camadas (Arquitetura Hexagonal):** A integração web é estritamente restrita à camada de adaptadores (`adapter/inbound/web/`), garantindo que o núcleo de domínio e as ferramentas determinísticas permaneçam desacoplados da camada HTTP.
- **Prevenção Básica de XSS no Input do Usuário:** O client-side `app.js` utiliza `textContent` para renderizar as mensagens do usuário no DOM, evitando a injeção direta de scripts no envio.
- **Validação de Tipos com Pydantic:** Uso de `ChatRequestDTO` e `ChatResponseDTO` com Pydantic para tipagem estática de requisições e respostas no FastAPI.
- **Client-side AbortController:** O `app.js` implementa timeout de 60s com `AbortController` para mitigar bloqueios indefinidos na interface.

### Riscos Identificados e Oportunidades de Refinamento

1. **Renderização de Markdown sem Sanitização HTML (Indirect/DOM-based XSS via `marked.parse`):** A função `addMessage` em `app.js` injeta o HTML gerado por `marked.parse(content)` diretamente em `innerHTML` para mensagens do bot sem passar por uma biblioteca de higienização (ex: DOMPurify). Caso o LLM gere ou repita tags HTML maliciosas (`<img onerror=...>`, `<script>`, `<a href="javascript:...">`) via prompt injection indireto ou manipulação de dados, scripts arbitrários serão executados no navegador do cliente.
2. **Configuração Permissiva de CORS (`allow_origins=["*"]` com `allow_credentials=True`):** Configurar CORS com wildcard `*` e `allow_credentials=True` viola especificações modernas de segurança e possibilita explorações de Cross-Origin caso credenciais/cookies sejam introduzidos.
3. **Crescimento Irrestrito de Memória e DoS por Criação Infinita de Sessões (OWASP LLM04 / CWE-400):** O dicionário `_active_sessions` no `WebChatApplicationService` e `_store` no `SessionMemoryAdapter` não possuem política de expiração (TTL), limpeza ou limite máximo (LRU). Um invasor pode enviar milhares de `session_id` distintos causando esgotamento de memória no servidor.
4. **Ausência de Limites de Tamanho e Validação de Formato nos DTOs (CWE-20):** `ChatRequestDTO` não define `max_length` para o campo `message` nem restrições de formato/tamanho para `session_id`, permitindo envio de payloads gigantescos que acarretam custos e consumo excessivo de tokens LLM.
5. **Exposição de Detalhes Internos em Mensagens de Erro (CWE-209):** O `WebChatApplicationService` captura `Exception` e propaga `str(e)` diretamente no payload de resposta (`ChatResponseDTO`), podendo vazar dados sensíveis, credenciais ou stack traces do sistema em caso de falhas internas.
6. **Ausência de Headers de Segurança HTTP e Subresource Integrity (SRI) (CWE-693 / CWE-353):** A aplicação FastAPI não define headers como `X-Content-Type-Options: nosniff` e `X-Frame-Options: DENY`, e o script externo `marked.min.js` em `index.html` não utiliza hashes de integridade (SRI).

---

## Vulnerability Log

| ID | Vulnerability | Severity | Risk | Impact |
| :--- | :--- | :--- | :--- | :--- |
| S002-01 | DOM-based / Indirect XSS via Unsanitized Markdown (`marked.parse`) | High | Medium x High | Execução arbitrária de JavaScript no navegador do usuário via respostas do agente |
| S002-02 | Overly Permissive CORS Configuration (`allow_origins=["*"]` + `allow_credentials=True`) | Medium | Medium x Medium | Exposição indevida da API a requisições cross-origin maliciosas |
| S002-03 | Unbounded Session Memory Growth & DoS via Unrestricted `session_id` | Medium | High x Medium | Esgotamento de memória RAM do servidor por acúmulo de instâncias de agentes |
| S002-04 | Missing Message Length Boundaries and `session_id` Regex in DTO | Medium | Medium x Medium | Consumo excessivo de tokens de IA, estouro de contexto e DoS de recursos |
| S002-05 | Information Disclosure via Raw Exception Message in Response DTO | Low | Low x Medium | Vazamento de detalhes de infraestrutura ou stack trace para clientes HTTP |
| S002-06 | Missing HTTP Security Headers and Subresource Integrity (SRI) | Low | Low x Low | Vulnerabilidade a MIME sniffing, Clickjacking e adulteração de CDN |

---

## Refinement Tasks

### Task 009 — [Adapter-Web-Frontend] Client-side Markdown Sanitization (DOMPurify)

- [COMPLETED] [S002-01] [High] **DOM-based / Indirect XSS via Unsanitized Markdown (`marked.parse`)**
  - **Location:** `src/adapter/inbound/web/static/app.js` → `addMessage()` & `src/adapter/inbound/web/static/index.html`
  - **Risk:** O método `contentDiv.innerHTML = marked.parse(content)` renderiza qualquer elemento HTML retornado pelo bot. Injeções de prompt indiretas ou dados maliciosos no dataset podem instruir o modelo a gerar tags perigosas (`<img src=x onerror=...>`, `<svg onload=...>`, `<a href="javascript:...">`), executando JavaScript no contexto do cliente.
  - **Fix:**
    1. Incluir a biblioteca `DOMPurify` (versão 3.x) via CDN no `index.html`:
       `<script src="https://cdn.jsdelivr.net/npm/dompurify@3.1.6/dist/purify.min.js"></script>`.
    2. Em `app.js`, higienizar a saída do `marked.parse` antes de atribuir ao `innerHTML`:
       `contentDiv.innerHTML = DOMPurify.sanitize(marked.parse(content));`.
  - **Validation:** Criar teste unitário em `tests/unit/adapter/inbound/web/test_frontend_static.py` validando que `DOMPurify` está referenciado no `index.html` e invocado no `app.js`.

---

### Task 005 — [Config] FastAPI CORS and HTTP Security Headers Hardening

- [COMPLETED] [S002-02] [Medium] **Overly Permissive CORS Configuration**
  - **Location:** `src/adapter/inbound/web/main.py` → `CORSMiddleware`
  - **Risk:** Combinar `allow_origins=["*"]` com `allow_credentials=True` gera configurações inseguras e pode violar restrições de navegadores.
  - **Fix:** Configurar origens permitidas explícitas (ex: ler de variável de ambiente `ALLOWED_ORIGINS` com default restrito para desenvolvimento local `["http://localhost:8000", "http://127.0.0.1:8000"]`) ou desativar `allow_credentials=False` se for wildcard público.
  - **Validation:** Testar resposta OPTIONS no endpoint `/chat` em `test_main.py` garantindo que os headers CORS respeitam as origens válidas.

- [COMPLETED] [S002-06] [Low] **Missing HTTP Security Headers and Subresource Integrity (SRI)**
  - **Location:** `src/adapter/inbound/web/main.py` & `src/adapter/inbound/web/static/index.html`
  - **Risk:** Ausência de cabeçalhos de defesa em profundidade (`X-Frame-Options`, `X-Content-Type-Options`) e dependências CDN sem verificação de hash SRI.
  - **Fix:**
    1. Adicionar middleware no FastAPI inserindo os headers de segurança: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`.
    2. Adicionar atributo `integrity` e `crossorigin="anonymous"` nas tags `<script>` e `<link>` do `index.html`.
  - **Validation:** Verificar presença dos headers em testes do `TestClient` no `test_main.py`.

---

### Task 004 & Task 007 — [UseCase / Adapter-Persistence] Session Memory Bounding & Eviction

- [COMPLETED] [S002-03] [Medium] **Unbounded Session Memory Growth & DoS via Unrestricted `session_id`**
  - **Location:** `src/application/service/web_chat_application_service.py` → `_active_sessions` & `src/adapter/outbound/memory/session_memory_adapter.py` → `_store`
  - **Risk:** Cada novo `session_id` aloca um novo objeto `SalesAgent` e histórico em memória sem expiração ou limite, possibilitando ataque de negação de serviço por exaustão de memória (OOM).
  - **Fix:**
    1. Definir limite máximo de sessões ativas (ex: `MAX_ACTIVE_SESSIONS = 500`) com política de descarte LRU (Least Recently Used) ou `OrderedDict` no `WebChatApplicationService` e no `SessionMemoryAdapter`.
    2. Ao atingir o limite, remover as sessões mais antigas para liberar recursos.
  - **Validation:** Teste unitário adicionando `MAX_ACTIVE_SESSIONS + 10` sessões e verificando que o tamanho da coleção respeita o limite estipulado.

---

### Task 002 — [DTO] Input Validation, Length Limits & Pattern Enforcement

- [COMPLETED] [S002-04] [Medium] **Missing Message Length Boundaries and `session_id` Regex in DTO**
  - **Location:** `src/application/dto/chat_dto.py` → `ChatRequestDTO`
  - **Risk:** Payloads com mensagens descomunais (megabytes) ou caracteres de controle em `session_id` provocam estouro de tokens LLM e vulnerabilidades de injeção/recursos.
  - **Fix:** Adicionar validações Pydantic em `ChatRequestDTO`:
    ```python
    message: str = Field(..., min_length=1, max_length=4000, description="The user's chat message")
    session_id: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_\-]+$", description="The unique session identifier")
    ```
  - **Validation:** Testes unitários em `test_chat_dto.py` confirmando rejeição (HTTP 422 / `ValidationError`) para mensagens vazias, mensagens > 4000 caracteres ou `session_id` com caracteres inválidos.

---

### Task 004 — [UseCase] Error Sanitization & Information Leak Prevention

- [COMPLETED] [S002-05] [Low] **Information Disclosure via Raw Exception Message in Response DTO**
  - **Location:** `src/application/service/web_chat_application_service.py` → `process_chat_message()`
  - **Risk:** Retornar `str(e)` expõe detalhes internos de implementação, caminhos do servidor ou mensagens de erro de drivers SQL/LLM diretamente para o cliente.
  - **Fix:** Registrar a exceção com stack trace usando `logger.exception(...)` e retornar mensagem amigável e sanitizada no `ChatResponseDTO`, como: `"An unexpected error occurred while processing your request. Please try again later."`.
  - **Validation:** Teste unitário em `test_web_chat_application_service.py` simulando exceção interna e verificando que a mensagem retornada é genérica e segura.
