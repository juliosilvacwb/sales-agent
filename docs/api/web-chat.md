# Referência da API: Interface de Web Chat

Este documento especifica os contratos da API REST para a interface de Web Chat do Agente de Análise de Dados de Vendas.

## URL Base

`/chat`

## `GET /`

Redireciona o usuário para a página da interface de Web Chat.

- **Código de Status:** `307 Temporary Redirect`
- **Location:** `/static/index.html`

## `POST /chat`

Processa a mensagem em linguagem natural enviada pelo usuário, mantém o contexto da sessão e retorna a resposta gerada pelo agente.

### Corpo da Requisição (JSON)

**Objeto de Transferência de Dados:** `ChatRequestDTO`

| Campo | Tipo | Obrigatório | Restrições | Descrição |
| --- | --- | --- | --- | --- |
| `message` | string | **Sim** | `min_length: 1`, `max_length: 4000` | A mensagem ou pergunta do usuário. |
| `session_id` | string | **Sim** | `min_length: 1`, `max_length: 128`, regex: `^[a-zA-Z0-9_\-]+$` | O identificador único de sessão usado para manter o histórico conversacional. |

**Exemplo de Requisição:**

```json
{
  "message": "Quais são os 3 produtos mais vendidos?",
  "session_id": "893c5922-4933-40f4-8a58-693df92d47d4"
}
```

### Corpo da Resposta (JSON)

**Objeto de Transferência de Dados:** `ChatResponseDTO`

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `response` | string | A resposta em texto do agente, podendo incluir formatação Markdown. |
| `status` | string | Status da resposta (`"success"` ou `"error"`). |

**Exemplo de Resposta (Sucesso - 200 OK):**

```json
{
  "response": "Os 3 produtos mais vendidos são:\n\n1. Produto A\n2. Produto B\n3. Produto C",
  "status": "success"
}
```

**Exemplo de Resposta (Erro Interno - 200 OK):**

*Nota: Erros internos retornam uma mensagem higienizada e segura em vez de uma stack trace bruta para prevenir o vazamento de informações.*

```json
{
  "response": "An unexpected error occurred while processing your request. Please try again later.",
  "status": "error"
}
```

**Exemplo de Resposta (Erro de Validação - 422 Unprocessable Entity):**

```json
{
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "ensure this value has at most 4000 characters",
      "type": "value_error.any_str.max_length"
    }
  ]
}
```

### Cabeçalhos & Segurança

- **CORS:** Controlado via variável de ambiente `ALLOWED_ORIGINS`.
- **Cabeçalhos de Segurança:** As respostas incluem `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` e `Referrer-Policy: strict-origin-when-cross-origin`.

---

## Gerenciamento de Sessão Distribuída (Stateless Architecture)

A persistência do histórico conversacional é desacoplada da camada de computação através da porta `SessionStorePort`, suportando dois provedores configuráveis via ambiente:

1. **Redis Distribuído (`SESSION_STORE=redis`):** Armazena as mensagens em um cluster Redis centralizado com namespacing (`sales_agent:session:<session_id>`) e renovação automática de TTL a cada interação (`SESSION_TTL_SECONDS=86400`). Permite escalabilidade horizontal multi-pod com 100% de paridade conversacional entre réplicas.
2. **Memória Local (`SESSION_STORE=memory`):** Fallback thread-safe com descarte LRU (capacidade padrão de 500 sessões) para desenvolvimento local offline e testes unitários.

