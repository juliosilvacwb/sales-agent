# TEST006-microservice-jwt-authentication — Test Coverage Specification

> **Source Task:** [T006-microservice-jwt-authentication.md](../architecture/T006-microservice-jwt-authentication.md)  
> **PRD Reference:** [R006-microservice-jwt-authentication.md](../business-requirements/R006-microservice-jwt-authentication.md)  
> **Product Strategy:** [PS006-microservice-jwt-authentication.md](../product-strategy/PS006-microservice-jwt-authentication.md)

## Coverage Overview

Esta especificação define a matriz forense de cobertura de testes unitários e de integração para a arquitetura de autenticação Zero Trust baseada no microsserviço de autenticação assimétrica com tokens JWT RS256 (`T006-microservice-jwt-authentication.md` / `R006-microservice-jwt-authentication.md`).

A arquitetura estabelece segregação criptográfica estrita: a chave privada RSA permanece restrita e exclusiva ao microsserviço de autenticação (`auth-service/`), enquanto o `sales-agent` atua exclusivamente como consumidor verificador da chave pública com cache local resiliente em memória.

- **Status Geral de Cobertura:** 100% de cobertura lógica mapeada cobrindo as 24 tasks do checklist técnico, incluindo testes unitários de domínio puro, testes de abstração de portas, adaptadores de criptografia RS256, guard de segurança FastAPI, e testes ponta a ponta (E2E) entre os serviços.
- **Pirâmide de Testes:**
  - **Unitários (Domínio Puro):** Validação da hierarquia de exceções de autenticação, imutabilidade dos value objects (`TokenClaims`, `AuthCredentials`, `TokenResponse`), lógica de expiração temporal e mitigação de timing attack no `CredentialValidator` via `hmac.compare_digest`.
  - **Unitários (Portas & Casos de Uso):** Verificação de contratos abstratos (`TokenSignerPort`, `TokenVerifierPort`, `PublicKeyProviderPort`, `AuthenticateUserUseCase`) e orquestração de autenticação no `AuthenticationApplicationService`.
  - **Unitários (Adaptadores Criptográficos e Infra):** Testes de geração, exportação PEM e persistência de pares de chaves RSA-2048 no `RsaKeyManager`; assinatura e verificação RS256 com PyJWT no `JwtRs256TokenAdapter`; e cliente HTTP resiliente com cache em memória no `HttpPublicKeyProvider`.
  - **Unitários (Adaptador Inbound / Web Guard):** Testes do FastAPI dependency guard `verify_jwt_token` validando cabeçalho `Authorization`, extração de Bearer token, bypass condicional de desenvolvimento (`AUTH_ENABLED=false`), tratamento de tokens expirados/adulterados e headers `WWW-Authenticate: Bearer`.
  - **Integração (Pipeline E2E Multi-Container):** Testes ponta a ponta exercitando o fluxo completo: login no Auth Microservice (`POST /auth/login`), recuperação de chave pública (`GET /auth/public-key`), verificação de healthcheck (`GET /health`), e consumo de rotas analíticas protegidas no Sales Agent (`POST /chat`) com assertividade de rejeição (401) e autorização (200).

---

## Test Checklist

### Task 001 — [Domain-Exception]: AuthenticationError Hierarchy

- [COMPLETED] [TEST006-01] [Type: Unit] **test_auth_exception_inheritance_hierarchy**
  - **Target:** `src/domain/exception/auth_exceptions.py` → `AuthenticationError`
  - **Scenario:** Validar que todas as exceções de domínio de autenticação herdam corretamente de `AuthenticationError`.
  - **Arrange:** Importar `AuthenticationError`, `InvalidCredentialsError`, `InvalidTokenError`, `ExpiredTokenError` e `MissingTokenError`.
  - **Act:** Verificar as relações de herança de classes.
  - **Assert:** `issubclass(InvalidCredentialsError, AuthenticationError)` é `True`, `issubclass(InvalidTokenError, AuthenticationError)` é `True`, `issubclass(ExpiredTokenError, InvalidTokenError)` é `True`, e `issubclass(MissingTokenError, AuthenticationError)` é `True`.
  - **Priority:** P0

- [COMPLETED] [TEST006-02] [Type: Unit] **test_auth_exceptions_custom_attributes_and_messages**
  - **Target:** `src/domain/exception/auth_exceptions.py` → `InvalidTokenError`, `MissingTokenError`
  - **Scenario:** Validar que exceções com atributos específicos (`reason`) populam as mensagens de erro adequadamente sem vazar detalhes sensíveis.
  - **Arrange:** Instanciar `InvalidTokenError(reason="Signature tampered")` e `MissingTokenError(reason="Header absent")`.
  - **Act:** Inspecionar os atributos `reason` e a representação string das instâncias.
  - **Assert:** `err.reason` armazena o motivo especificado e a conversão em string contém a mensagem formatada.
  - **Priority:** P1

---

### Task 002 — [Domain-Model]: TokenClaims Value Object

- [COMPLETED] [TEST006-03] [Type: Unit] **test_token_claims_instantiation_and_expiration_property**
  - **Target:** `src/domain/model/auth_models.py` → `TokenClaims`
  - **Scenario:** Validar cálculo da propriedade `is_expired` para timestamps passados e futuros em relação ao UTC atual.
  - **Arrange:** Criar um objeto `TokenClaims` com `exp` no futuro (`now + 3600`) e outro com `exp` no passado (`now - 100`).
  - **Act:** Avaliar a propriedade `claims.is_expired` para ambas as instâncias.
  - **Assert:** Retorna `False` para token vigente e `True` para token cujo timestamp de expiração já foi ultrapassado.
  - **Priority:** P0

- [COMPLETED] [TEST006-04] [Type: Unit] **test_token_claims_immutability**
  - **Target:** `src/domain/model/auth_models.py` → `TokenClaims`
  - **Scenario:** Garantir que a estrutura de claims é imutável (`frozen=True`) para prevenir mutações colaterais em memória.
  - **Arrange:** Instanciar `claims = TokenClaims(sub="user", iss="iss", iat=100, exp=200)`.
  - **Act:** Tentar reatribuir `claims.sub = "attacker"`.
  - **Assert:** Lança `dataclasses.FrozenInstanceError`.
  - **Priority:** P1

---

### Task 003 — [Domain-Model]: AuthCredentials Value Object

- [COMPLETED] [TEST006-05] [Type: Unit] **test_auth_credentials_instantiation_and_immutability**
  - **Target:** `src/domain/model/auth_models.py` → `AuthCredentials`
  - **Scenario:** Validar a integridade e imutabilidade dos dados de credenciais fornecidos pelo usuário.
  - **Arrange:** Instanciar `creds = AuthCredentials(username="admin", password="password123")`.
  - **Act:** Tentar alterar `creds.password = "new_pass"`.
  - **Assert:** Atributos `username` e `password` refletem os valores informados e a tentativa de mutação dispara `dataclasses.FrozenInstanceError`.
  - **Priority:** P0

---

### Task 004 — [Domain-Model]: TokenResponse Value Object

- [COMPLETED] [TEST006-06] [Type: Unit] **test_token_response_defaults_and_immutability**
  - **Target:** `src/domain/model/auth_models.py` → `TokenResponse`
  - **Scenario:** Validar valores padrão de resposta de token (`token_type="Bearer"`, `expires_in=3600`) e imutabilidade.
  - **Arrange:** Instanciar `resp = TokenResponse(access_token="sample.jwt.token")`.
  - **Act:** Verificar atributos padrão e tentar modificar `resp.access_token`.
  - **Assert:** `resp.token_type == "Bearer"`, `resp.expires_in == 3600`, e qualquer alteração de campo dispara `dataclasses.FrozenInstanceError`.
  - **Priority:** P0

---

### Task 005 — [Domain-Service]: CredentialValidator Domain Service

- [COMPLETED] [TEST006-07] [Type: Unit] **test_credential_validator_success**
  - **Target:** `src/domain/service/credential_validator.py` → `CredentialValidator.validate()`
  - **Scenario:** Validar que credenciais idênticas às configuradas retornam `True`.
  - **Arrange:** Instanciar `CredentialValidator` e `AuthCredentials(username="admin", password="secure_pass")`.
  - **Act:** Executar `validator.validate(creds, expected_username="admin", expected_password="secure_pass")`.
  - **Assert:** Retorna `True`.
  - **Priority:** P0

- [COMPLETED] [TEST006-08] [Type: Unit] **test_credential_validator_timing_safe_failure**
  - **Target:** `src/domain/service/credential_validator.py` → `CredentialValidator.validate()`
  - **Scenario:** Garantir que credenciais com username ou password incorretos disparam `InvalidCredentialsError` com mensagem padronizada.
  - **Arrange:** Instanciar credenciais com usuário incorreto (`wrong_admin`) e com senha incorreta (`wrong_pass`).
  - **Act:** Executar `validate()` contra os valores esperados.
  - **Assert:** Dispara `InvalidCredentialsError` com a mensagem `"Credenciais inválidas"` para ambos os casos de divergência.
  - **Priority:** P0

---

### Task 006 & Task 007 — [Port-Out]: TokenSignerPort and TokenVerifierPort Interfaces

- [COMPLETED] [TEST006-09] [Type: Unit] **test_token_ports_abstract_contract**
  - **Target:** `src/application/port/outbound/token_port.py` → `TokenSignerPort`, `TokenVerifierPort`
  - **Scenario:** Garantir que as interfaces de porta de saída para assinatura e verificação de tokens não podem ser instanciadas diretamente.
  - **Arrange:** Tentar instanciar diretamente `TokenSignerPort()` e `TokenVerifierPort()`.
  - **Act:** Avaliar a instanciação das classes abstratas.
  - **Assert:** Disparam `TypeError` indicando métodos abstratos pendentes (`sign` e `verify`).
  - **Priority:** P1

---

### Task 008 — [Port-Out]: PublicKeyProviderPort Interface

- [COMPLETED] [TEST006-10] [Type: Unit] **test_public_key_provider_port_abstract_contract**
  - **Target:** `src/application/port/outbound/public_key_provider_port.py` → `PublicKeyProviderPort`
  - **Scenario:** Validar que a porta de fornecimento de chave pública exige a implementação do método `get_public_key()`.
  - **Arrange:** Tentar instanciar `PublicKeyProviderPort()`.
  - **Act:** Avaliar a criação da instância.
  - **Assert:** Dispara `TypeError` devido ao método abstrato `get_public_key`.
  - **Priority:** P1

---

### Task 009 — [Port-In]: AuthenticateUserUseCase Interface

- [COMPLETED] [TEST006-11] [Type: Unit] **test_authenticate_user_use_case_abstract_contract**
  - **Target:** `src/application/port/inbound/authenticate_user_use_case.py` → `AuthenticateUserUseCase`
  - **Scenario:** Validar que o contrato de caso de uso de autenticação exige a implementação do método `authenticate()`.
  - **Arrange:** Tentar instanciar `AuthenticateUserUseCase()`.
  - **Act:** Avaliar a criação da instância.
  - **Assert:** Dispara `TypeError` devido ao método abstrato `authenticate`.
  - **Priority:** P1

---

### Task 010 — [UseCase]: AuthenticationApplicationService Implementation

- [COMPLETED] [TEST006-12] [Type: Unit] **test_auth_application_service_successful_authentication**
  - **Target:** `src/application/service/authentication_service.py` → `AuthenticationApplicationService.authenticate()`
  - **Scenario:** Validar o fluxo completo de autenticação da aplicação: validação de credenciais, geração de `TokenClaims` e chamada à porta `TokenSignerPort`.
  - **Arrange:** Mockar `TokenSignerPort` retornando `TokenResponse("mock.jwt", "Bearer", 3600)`. Configurar serviço com usuário `"admin"` e senha `"secret"`.
  - **Act:** Chamar `service.authenticate(AuthCredentials(username="admin", password="secret"))`.
  - **Assert:** Retorna o `TokenResponse` esperado e repassa `TokenClaims` com `sub="admin"`, `iss="sales-auth-service"` e `roles=("user",)` para o assinador.
  - **Priority:** P0

- [COMPLETED] [TEST006-13] [Type: Unit] **test_auth_application_service_invalid_credentials_blocks_signing**
  - **Target:** `src/application/service/authentication_service.py` → `AuthenticationApplicationService.authenticate()`
  - **Scenario:** Garantir que credenciais incorretas impedem a invocação do `TokenSignerPort` e propagam `InvalidCredentialsError`.
  - **Arrange:** Mockar `TokenSignerPort`. Instanciar serviço com credenciais esperadas.
  - **Act:** Tentar autenticar com credenciais inválidas.
  - **Assert:** Dispara `InvalidCredentialsError` e `mock_signer.sign.assert_not_called()`.
  - **Priority:** P0

---

### Task 012 — [Adapter-External]: JwtRs256TokenAdapter (Sign and Verify)

- [COMPLETED] [TEST006-14] [Type: Unit] **test_jwt_rs256_adapter_sign_and_verify_roundtrip**
  - **Target:** `src/adapter/outbound/auth/jwt_token_adapter.py` → `JwtRs256TokenAdapter`
  - **Scenario:** Executar ciclo completo de assinatura de `TokenClaims` com chave privada RSA e decodificação/verificação com chave pública RSA correspondente.
  - **Arrange:** Gerar par de chaves RSA-2048 de teste. Instanciar adapter com a chave privada.
  - **Act:** Assinar `TokenClaims` estruturados e em seguida decodificar o token gerado com a chave pública.
  - **Assert:** O token decodificado reproduz com exatidão os campos `sub`, `iss`, `iat`, `exp` e `roles`.
  - **Priority:** P0

- [COMPLETED] [TEST006-15] [Type: Unit] **test_jwt_rs256_adapter_signing_without_private_key_fails**
  - **Target:** `src/adapter/outbound/auth/jwt_token_adapter.py` → `JwtRs256TokenAdapter.sign()`
  - **Scenario:** Validar que instâncias do adaptador sem chave privada configurada (ex: pods do Sales Agent) rejeitam tentativas de assinatura.
  - **Arrange:** Instanciar `JwtRs256TokenAdapter(private_key_pem=None)`.
  - **Act:** Tentar executar `sign(claims)`.
  - **Assert:** Dispara `AuthenticationError` indicando ausência de chave privada para emissão de tokens.
  - **Priority:** P0

- [COMPLETED] [TEST006-16] [Type: Unit] **test_jwt_rs256_adapter_expired_token_rejection**
  - **Target:** `src/adapter/outbound/auth/jwt_token_adapter.py` → `JwtRs256TokenAdapter.verify()`
  - **Scenario:** Garantir que tokens com claim `exp` ultrapassado disparam `ExpiredTokenError`.
  - **Arrange:** Assinar token com timestamps de expiração retroativos (`exp = now - 3600`).
  - **Act:** Executar `verify(token, public_key_pem)`.
  - **Assert:** Dispara `ExpiredTokenError`.
  - **Priority:** P0

- [COMPLETED] [TEST006-17] [Type: Unit] **test_jwt_rs256_adapter_tampered_payload_rejection**
  - **Target:** `src/adapter/outbound/auth/jwt_token_adapter.py` → `JwtRs256TokenAdapter.verify()`
  - **Scenario:** Garantir que tokens com payload adulterado são rejeitados matematicamente pela verificação de assinatura RS256.
  - **Arrange:** Assinar token legítimo e alterar os bytes da seção de payload mantendo o cabeçalho e assinatura originais.
  - **Act:** Executar `verify(tampered_token, public_key_pem)`.
  - **Assert:** Dispara `InvalidTokenError`.
  - **Priority:** P0

- [COMPLETED] [TEST006-18] [Type: Unit] **test_jwt_rs256_adapter_foreign_key_signature_rejection**
  - **Target:** `src/adapter/outbound/auth/jwt_token_adapter.py` → `JwtRs256TokenAdapter.verify()`
  - **Scenario:** Garantir que tokens assinados por uma chave privada diferente são rejeitados ao verificar com a chave pública do sistema.
  - **Arrange:** Gerar dois pares distintos de chaves RSA. Assinar com o par A e verificar com a chave pública do par B.
  - **Act:** Executar `verify(token_a, public_key_b)`.
  - **Assert:** Dispara `InvalidTokenError`.
  - **Priority:** P0

---

### Task 013 — [Adapter-External]: RsaKeyManager Key Lifecycle

- [COMPLETED] [TEST006-19] [Type: Unit] **test_rsa_key_manager_generate_key_pair_pem_structure**
  - **Target:** `src/adapter/outbound/auth/rsa_key_manager.py` → `RsaKeyManager.generate_key_pair()`
  - **Scenario:** Validar que o gerador de chaves RSA emite blocos válidos nos formatos PKCS#8 (chave privada) e SubjectPublicKeyInfo (chave pública).
  - **Arrange:** Chamar `RsaKeyManager.generate_key_pair(key_size=2048)`.
  - **Act:** Inspecionar os cabeçalhos e rodapés dos blocos PEM retornados.
  - **Assert:** Chave privada contém `-----BEGIN PRIVATE KEY-----` e chave pública contém `-----BEGIN PUBLIC KEY-----`.
  - **Priority:** P0

- [COMPLETED] [TEST006-20] [Type: Unit] **test_rsa_key_manager_load_from_environment_variables**
  - **Target:** `src/adapter/outbound/auth/rsa_key_manager.py` → `RsaKeyManager.load_or_generate()`
  - **Scenario:** Validar carregamento prioritário de chaves injetadas via variáveis de ambiente (`RSA_PRIVATE_KEY_PEM` e `RSA_PUBLIC_KEY_PEM`).
  - **Arrange:** Definir as variáveis de ambiente com pares PEM válidos.
  - **Act:** Chamar `RsaKeyManager.load_or_generate()`.
  - **Assert:** Retorna com exatidão os valores das variáveis de ambiente sem acessar o disco nem gerar novas chaves.
  - **Priority:** P0

- [COMPLETED] [TEST006-21] [Type: Unit] **test_rsa_key_manager_filesystem_persistence_and_reloading**
  - **Target:** `src/adapter/outbound/auth/rsa_key_manager.py` → `RsaKeyManager.load_or_generate()`
  - **Scenario:** Validar que chaves geradas dinamicamente são salvas nos caminhos configurados e reutilizadas em inicializações subsequentes.
  - **Arrange:** Fornecer caminhos temporários para `private_key_path` e `public_key_path`.
  - **Act:** Chamar `load_or_generate()` na primeira execução (geração + gravação) e numa segunda execução (leitura do arquivo).
  - **Assert:** Os arquivos existem no disco e o conteúdo lido na segunda invocação é idêntico ao gerado na primeira.
  - **Priority:** P1

---

### Task 015 — [Adapter-Outbound]: HttpPublicKeyProvider Resilience & Caching

- [COMPLETED] [TEST006-22] [Type: Unit] **test_http_public_key_provider_caching_behavior**
  - **Target:** `src/adapter/outbound/auth/http_public_key_provider.py` → `HttpPublicKeyProvider.get_public_key()`
  - **Scenario:** Validar que a chave pública obtida via HTTP é mantida em cache em memória, evitando requisições de rede redundantes.
  - **Arrange:** Mockar `urllib.request.urlopen` retornando JSON com `public_key`.
  - **Act:** Chamar `get_public_key()` duas vezes consecutivas.
  - **Assert:** A chave é retornada corretamente em ambas as chamadas e `urlopen` é invocado exatamente 1 vez.
  - **Priority:** P0

- [COMPLETED] [TEST006-23] [Type: Unit] **test_http_public_key_provider_network_error_handling**
  - **Target:** `src/adapter/outbound/auth/http_public_key_provider.py` → `HttpPublicKeyProvider.get_public_key()`
  - **Scenario:** Validar que falhas de conexão ou timeouts ao contactar o Auth Microservice são encapsuladas em `AuthenticationError`.
  - **Arrange:** Mockar `urllib.request.urlopen` disparando erro de rede (`URLError`).
  - **Act:** Chamar `get_public_key()`.
  - **Assert:** Dispara `AuthenticationError` com detalhes informativos sobre a URL de destino.
  - **Priority:** P0

---

### Task 016 — [Adapter-Inbound / Web]: JwtSecurityGuard (FastAPI Dependency)

- [COMPLETED] [TEST006-24] [Type: Unit] **test_jwt_security_guard_bypass_when_auth_disabled**
  - **Target:** `src/adapter/inbound/web/jwt_security_guard.py` → `verify_jwt_token()`
  - **Scenario:** Validar que quando `AUTH_ENABLED=false`, requisições sem token são liberadas retornando claims de desenvolvimento.
  - **Arrange:** Definir `AUTH_ENABLED=false`.
  - **Act:** Executar `verify_jwt_token(authorization=None)`.
  - **Assert:** Retorna `TokenClaims` padrão com `sub="anonymous_dev"`.
  - **Priority:** P0

- [COMPLETED] [TEST006-25] [Type: Unit] **test_jwt_security_guard_missing_header_raises_401**
  - **Target:** `src/adapter/inbound/web/jwt_security_guard.py` → `verify_jwt_token()`
  - **Scenario:** Validar que requisições sem cabeçalho `Authorization` quando `AUTH_ENABLED=true` são rejeitadas com 401 e header `WWW-Authenticate: Bearer`.
  - **Arrange:** Definir `AUTH_ENABLED=true`.
  - **Act:** Executar `verify_jwt_token(authorization=None)`.
  - **Assert:** Dispara `HTTPException(401)` contendo `WWW-Authenticate: Bearer`.
  - **Priority:** P0

- [COMPLETED] [TEST006-26] [Type: Unit] **test_jwt_security_guard_malformed_scheme_raises_401**
  - **Target:** `src/adapter/inbound/web/jwt_security_guard.py` → `verify_jwt_token()`
  - **Scenario:** Rejeitar esquemas de autenticação não suportados (ex: `Basic <token>` ou token sem prefixo).
  - **Arrange:** Definir `AUTH_ENABLED=true` e `authorization="Basic dXNlcjpwYXNz"`.
  - **Act:** Executar `verify_jwt_token()`.
  - **Assert:** Dispara `HTTPException(401)` com mensagem informando necessidade do formato `'Bearer <token>'`.
  - **Priority:** P0

- [COMPLETED] [TEST006-27] [Type: Unit] **test_jwt_security_guard_valid_token_returns_claims**
  - **Target:** `src/adapter/inbound/web/jwt_security_guard.py` → `verify_jwt_token()`
  - **Scenario:** Validar que token Bearer válido extrai e retorna o objeto `TokenClaims` correspondente.
  - **Arrange:** Mockar `PublicKeyProviderPort` e `TokenVerifierPort` configurado para retornar `TokenClaims(sub="analyst")`.
  - **Act:** Executar `verify_jwt_token(authorization="Bearer valid.jwt.token")`.
  - **Assert:** Retorna o objeto `TokenClaims` esperado.
  - **Priority:** P0

- [COMPLETED] [TEST006-28] [Type: Unit] **test_jwt_security_guard_expired_and_invalid_token_returns_401_sanitized**
  - **Target:** `src/adapter/inbound/web/jwt_security_guard.py` → `verify_jwt_token()`
  - **Scenario:** Validar que tokens expirados ou com assinatura corrompida retornam HTTP 401 com detalhe sanitizado `"Token inválido ou expirado"`.
  - **Arrange:** Configurar mock de `TokenVerifierPort` para disparar `ExpiredTokenError` e `InvalidTokenError`.
  - **Act:** Executar `verify_jwt_token()` com tokens inválidos.
  - **Assert:** Dispara `HTTPException(401)` com `detail="Token inválido ou expirado"`.
  - **Priority:** P0

---

### Task 014, 017 & 024 — [Integration / E2E]: Full End-to-End Authentication & Chat Protection

- [COMPLETED] [TEST006-29] [Type: Integration] **test_auth_service_health_and_public_key_endpoints**
  - **Target:** `auth-service/app.py` → `GET /health`, `GET /auth/public-key`
  - **Scenario:** Validar a disponibilidade operacional e distribuição correta de chave pública do microsserviço de autenticação.
  - **Arrange:** Instanciar `TestClient` apontando para o app do `auth-service`.
  - **Act:** Executar requisições GET para `/health` e `/auth/public-key`.
  - **Assert:** `/health` responde HTTP 200 com `{"status": "ok"}` e `/auth/public-key` responde HTTP 200 com bloco PEM válido.
  - **Priority:** P0

- [COMPLETED] [TEST006-30] [Type: Integration] **test_auth_service_login_happy_and_unhappy_path**
  - **Target:** `auth-service/app.py` → `POST /auth/login`
  - **Scenario:** Validar login bem-sucedido com emissão de token JWT RS256 e rejeição com 401 sanitizado em caso de senha inválida.
  - **Arrange:** Cliente de teste do Auth Microservice.
  - **Act:** Submeter credenciais válidas (`admin`/`changeme`) e credenciais inválidas (`admin`/`wrong_password`).
  - **Assert:** Credenciais válidas retornam HTTP 200 com `access_token`, `token_type: "Bearer"` e `expires_in: 3600`. Senha inválida retorna HTTP 401 com `{"detail": "Credenciais inválidas"}`.
  - **Priority:** P0

- [COMPLETED] [TEST006-31] [Type: Integration] **test_sales_agent_chat_endpoint_protection_and_authorization**
  - **Target:** `src/adapter/inbound/web/main.py` → `POST /chat`
  - **Scenario:** Validar que rotas públicas (`/health`) funcionam sem autenticação e que rotas analíticas protegidas (`POST /chat`) exigem Bearer token válido emitido pelo Auth Service.
  - **Arrange:** Obter token válido via `POST /auth/login`. Instanciar `TestClient` do Sales Agent com `AUTH_ENABLED=true`.
  - **Act:** (1) Acessar `GET /health` sem token; (2) Chamar `POST /chat` sem token; (3) Chamar `POST /chat` com o token emitido; (4) Chamar `POST /chat` com token adulterado.
  - **Assert:** (1) `/health` retorna HTTP 200; (2) `/chat` sem token retorna HTTP 401; (3) `/chat` com token válido retorna HTTP 200 com resposta analítica; (4) `/chat` com token adulterado retorna HTTP 401.
  - **Priority:** P0
