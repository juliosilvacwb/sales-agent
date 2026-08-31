# Referência da API: Microsserviço de Autenticação (Auth Service)

Este documento especifica os contratos da API REST do **Authentication Microservice** (`auth-service/`), responsável exclusivo pela gestão de credenciais, emissão de tokens JWT assinados com chave privada RSA-2048 (`RS256`) e distribuição da chave pública.

## URL Base

- **Desenvolvimento Local:** `http://localhost:8001`
- **Cluster Kubernetes / K3s:** `http://auth-service:8001`

---

## `POST /auth/login`

Autentica as credenciais do cliente (usuário e senha) em tempo constante (`hmac.compare_digest`) e emite um token de acesso JWT assimétrico assinado com a chave privada RSA-2048 (`RS256`).

### Corpo da Requisição (JSON)

**Modelo de Entrada:** `LoginRequest`

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `username` | string | **Sim** | Nome de usuário administrativo autorizado. |
| `password` | string | **Sim** | Senha do usuário. |

**Exemplo de Requisição:**

```json
{
  "username": "admin",
  "password": "changeme"
}
```

### Corpo da Resposta (JSON)

**Modelo de Saída:** `LoginResponse`

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `access_token` | string | Token JWT assinado com algoritmo assimétrico RS256. |
| `token_type` | string | Tipo do token de autorização (fixo em `"Bearer"`). |
| `expires_in` | integer | Tempo de validade do token em segundos (ex: `3600`). |

**Exemplo de Resposta de Sucesso (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImlzcyI6InNhbGVzLWF1dGgtc2VydmljZSIsImlhdCI6MTcyNTA1MjgwMCwiZXhwIjoxNzI1MDU2NDAwLCJyb2xlcyI6WyJ1c2VyIl19.c3lnNGZ4...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Respostas de Erro

**401 Unauthorized (Credenciais Inválidas):**

*Nota: Mensagem sanitizada e uniforme para prevenir colheita de credenciais e enumeração de usuários (BR05).*

```json
{
  "detail": "Credenciais inválidas"
}
```

**422 Unprocessable Entity (Erro de Validação de Schema):**

```json
{
  "detail": [
    {
      "loc": ["body", "username"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## `GET /auth/public-key`

Retorna a chave pública RSA em formato PEM padrão (`SubjectPublicKeyInfo`) para validação matemática de tokens por serviços consumidores (ex: Sales Agent).

### Resposta de Sucesso (200 OK)

**Modelo de Saída:** `PublicKeyResponse`

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `public_key` | string | Chave pública RSA-2048 codificada em bloco PEM padrão. |

**Exemplo de Resposta:**

```json
{
  "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2Qbw...IDAQAB\n-----END PUBLIC KEY-----\n"
}
```

---

## `GET /health`

Health check endpoint para sondas de liveness e readiness do Kubernetes e Docker Compose.

### Resposta de Sucesso (200 OK)

```json
{
  "status": "ok"
}
```

---

## Estrutura dos Claims JWT (RS256 Payload)

Todo token emitido pelo microsserviço de autenticação contém os seguintes claims obrigatórios:

| Claim | Tipo | Exemplo | Descrição |
| --- | --- | --- | --- |
| `sub` | string | `"admin"` | Identificador do sujeito autenticado (Subject). |
| `iss` | string | `"sales-auth-service"` | Identificador do emissor do token (Issuer). |
| `iat` | integer | `1725052800` | Timestamp UNIX de emissão do token (Issued At). |
| `exp` | integer | `1725056400` | Timestamp UNIX de expiração do token (Expiration). |
| `roles` | array[string] | `["user"]` | Papéis e permissões do usuário no sistema. |
