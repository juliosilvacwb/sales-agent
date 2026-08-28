# API Reference: Web Chat Interface

This document specifies the REST API contracts for the Sales Data Analysis Agent Web Chat interface.

## Base URL

`/chat`

## `GET /`

Redirects the user to the Web Chat interface page.

- **Status Code:** `307 Temporary Redirect`
- **Location:** `/static/index.html`

## `POST /chat`

Processes a user's natural language chat message, maintains session context, and returns the agent's generated response.

### Request Body (JSON)

**Data Transfer Object:** `ChatRequestDTO`

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `message` | string | **Yes** | `min_length: 1`, `max_length: 4000` | The user's chat message or question. |
| `session_id` | string | **Yes** | `min_length: 1`, `max_length: 128`, regex: `^[a-zA-Z0-9_\-]+$` | The unique session identifier used to maintain conversational history. |

**Example Request:**

```json
{
  "message": "Quais são os 3 produtos mais vendidos?",
  "session_id": "893c5922-4933-40f4-8a58-693df92d47d4"
}
```

### Response Body (JSON)

**Data Transfer Object:** `ChatResponseDTO`

| Field | Type | Description |
| --- | --- | --- |
| `response` | string | The agent's text response, which may include Markdown formatting. |
| `status` | string | Status of the response (`"success"` or `"error"`). |

**Example Response (Success - 200 OK):**

```json
{
  "response": "Os 3 produtos mais vendidos são:\n\n1. Produto A\n2. Produto B\n3. Produto C",
  "status": "success"
}
```

**Example Response (Internal Error - 200 OK):**

*Note: Internal errors return a safe sanitized message instead of a raw stack trace to prevent information disclosure.*

```json
{
  "response": "An unexpected error occurred while processing your request. Please try again later.",
  "status": "error"
}
```

**Example Response (Validation Error - 422 Unprocessable Entity):**

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

### Headers & Security

- **CORS:** Controlled via the `ALLOWED_ORIGINS` environment variable.
- **Security Headers:** Responses include `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: strict-origin-when-cross-origin`.
