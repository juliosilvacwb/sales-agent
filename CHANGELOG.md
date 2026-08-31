# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.0] - 2026-08-30

### Added

- **Elasticidade-Preço da Demanda Baseada em Segmentos (T008 / R008):** Transição do cálculo global para modelo segmentado por `product_id`, eliminando distorções estatísticas decorrentes do Paradoxo de Simpson ao isolar variações de preço e volume em coortes homogêneas.
- **Modelos e Value Objects de Domínio (`src/domain/model/metric_result.py` e `aggregation_models.py`):**
  - Criação do Value Object imutável `CatalogPriceElasticityOverview` com campos `total_products_evaluated`, `inconclusive_products_count`, `most_elastic_products`, `most_inelastic_products` e `summary`.
  - Atualização de `PriceElasticityAggregation` adicionando o campo `product_id: str`.
  - Atualização de `PriceElasticityResult` adicionando o campo `product_id: Optional[str] = None`.
- **Serviço de Domínio `AdvancedMetricsService` (`src/domain/service/advanced_metrics_service.py`):**
  - Refatoração do método `calculate_price_elasticity` para suportar tanto consultas individuais de produtos quanto ranqueamento macro de todo o catálogo.
  - Implementação do cálculo determinístico de PED per segment ($\frac{\% \Delta Q}{\% \Delta P}$).
  - Proteção estrita contra divisão por zero (`Unitary / Zero price change`) quando a variação de preço for nula ($\% \Delta P = 0.0$).
  - Isolamento de coortes esparsas (`Inconclusive`) para produtos sem registros promocionais ou basais, excluindo-os dos rankings sem interromper o processamento dos demais itens.
- **Portas de Saída e Entrada (`src/application/port/`):**
  - Atualização de `SalesDataPort.aggregate_price_elasticity(product_id: Optional[str] = None) -> List[PriceElasticityAggregation]`.
  - Atualização de `SalesAnalysisUseCase.calculate_price_elasticity(product_id: Optional[str] = None) -> Union[PriceElasticityResult, CatalogPriceElasticityOverview]`.
- **Serviço de Aplicação `SalesMetricsApplicationService` (`src/application/service/sales_metrics_service.py`):**
  - Orquestração do caso de uso com repasse transparente do parâmetro `product_id` para o adaptador de banco e o serviço de domínio.
- **Pushdown de Agregação SQL no Adaptador DuckDB (`src/adapter/outbound/persistence/duckdb_sales_adapter.py`):**
  - Agrupamento nativo via SQL `GROUP BY product_id` com funções de agregação condicionais (`AVG() FILTER (...)`, `COUNT() FILTER (...)`).
  - Filtragem parametrizada segura contra SQL Injection via `WHERE product_id = ?`.
- **Ferramenta LLM Atualizada (`src/adapter/inbound/llm/domain_tools.py`):**
  - Assinatura da tool `calculate_price_elasticity(product_id: Optional[str] = None) -> str` com docstring contextualizada para consultas pontuais ou rankings de catálogo.
- **Suíte Completa de Testes Automatizados:**
  - Criação de `tests/integration/test_price_elasticity.py` validando cenários elásticos, inelásticos, variação zero, produtos inexistentes e visão macro do catálogo.
  - Testes unitários expandidos em `test_advanced_metrics_service.py`, `test_duckdb_sales_adapter.py`, `test_domain_tools.py` e `test_domain_models.py`.
- **Artefatos de Governança ADD:** Inclusão das especificações `R008-segment-based-price-elasticity.md`, `T008-segment-based-price-elasticity.md`, `TEST008-segment-based-price-elasticity.md`, `S008-segment-based-price-elasticity.md`, `Q008-segment-based-price-elasticity.md` e `PS008-segment-based-price-elasticity.md`.

### Changed

- **Eliminação do Paradoxo de Simpson em Análise de Elasticidade:** Superação do modelo legado que misturava preços de itens heterogêneos em médias globais antes de computar elasticidade.

### Security & Reliability

- **Prevenção de Injeção de SQL (OWASP A03 / ASVS V5):** Parametrização estrita de consultas SQL DuckDB na cláusula `WHERE product_id = ?`.
- **Prevenção de Negação de Serviço por Divisão por Zero (CWE-369):** Tratamento matemático de $\Delta P = 0.0$ e preços/quantidades base zeradas retornando classificações seguras (`Unitary / Zero price change` e `Undefined`).
- **Resiliência e Isolamento de Falhas (BR04):** Dados incompletos em um produto não contaminam nem invalidam o processamento do catálogo como um todo.
- **Sanitização e Normalização de Entradas (CWE-20):** Remoção de espaços em branco (`.strip()`) nos identificadores de produtos.

## [1.5.0] - 2026-08-30

### Added

- **Microsserviço de Autenticação Assimétrica JWT RS256 (T006 / R006):** Criação de arquitetura Zero Trust baseada em microsserviço independente (`auth-service/`) como detentor exclusivo da chave privada RSA-2048, emitindo tokens de acesso assinados (`RS256`).
- **Endpoint de Autenticação e Login (`POST /auth/login`):** Validação de credenciais administrativas em tempo constante (`hmac.compare_digest`) e emissão de tokens JWT com expiração temporal (`JWT_EXPIRATION_MINUTES`).
- **Endpoint de Distribuição de Chave Pública (`GET /auth/public-key`):** Distribuição da chave pública RSA em formato PEM para consumo e validação offline por microsserviços analíticos.
- **Modelos e Value Objects de Domínio (`src/domain/model/auth_models.py`):** Criação de `TokenClaims`, `AuthCredentials` e `TokenResponse` como estruturas de dados imutáveis (`frozen=True`).
- **Hierarquia de Exceções de Domínio (`src/domain/exception/auth_exceptions.py`):** Exceções `AuthenticationError`, `InvalidCredentialsError`, `InvalidTokenError`, `ExpiredTokenError` e `MissingTokenError`.
- **Serviço de Domínio `CredentialValidator` (`src/domain/service/credential_validator.py`):** Validador puro com mitigação de ataques de canal lateral/timing attack.
- **Portas de Saída e Entrada (`src/application/port/`):** Contratos de abstração `TokenSignerPort`, `TokenVerifierPort`, `PublicKeyProviderPort` e caso de uso `AuthenticateUserUseCase`.
- **Serviço de Aplicação `AuthenticationApplicationService` (`src/application/service/authentication_service.py`):** Orquestrador de autenticação e construção de claims.
- **Adaptador Criptográfico `JwtRs256TokenAdapter` (`src/adapter/outbound/auth/jwt_token_adapter.py`):** Assinatura e verificação de tokens RS256 via PyJWT e cryptography com whitelist estrita de algoritmos.
- **Gerenciador de Chaves `RsaKeyManager` (`src/adapter/outbound/auth/rsa_key_manager.py`):** Geração, persistência em disco e carregamento via variáveis de ambiente/Secrets de pares de chaves RSA-2048.
- **Provedor HTTP de Chave Pública `HttpPublicKeyProvider` (`src/adapter/outbound/auth/http_public_key_provider.py`):** Cliente com cache em memória e lazy loading para verificação offline sub-milissegundo (< 0.5ms).
- **Inbound Security Guard `JwtSecurityGuard` (`src/adapter/inbound/web/jwt_security_guard.py`):** Injeção de dependência FastAPI `verify_jwt_token` validando cabeçalho `Authorization: Bearer <token>` em rotas protegidas.
- **Docker Compose Multi-Container (`docker-compose.yml`):** Orquestração completa de 3 serviços (`auth-service:8001`, `sales-agent:8000`, `redis:6379`).
- **Manifestos Declarativos K3s/Kubernetes:** Manifestos `k8s/auth-deployment.yaml`, `k8s/auth-service.yaml` e atualização de `k8s/configmap.yaml` para orquestração em cluster.
- **Documentação de API Atualizada:** Criação de `docs/api/auth-service.md` e atualização de `docs/api/web-chat.md`.
- **Artefatos de Governança ADD:** Inclusão das especificações `R006-microservice-jwt-authentication.md`, `T006-microservice-jwt-authentication.md`, `TEST006-microservice-jwt-authentication.md`, `S006-microservice-jwt-authentication.md`, `Q006-microservice-jwt-authentication.md` e `docs/api/auth-service.md`.

### Changed

- **Proteção do Endpoint Analítico (`src/adapter/inbound/web/chat_controller.py`):** Rota `POST /chat` atualizada com `Depends(verify_jwt_token)` para impor validação Bearer e registrar log de auditoria com o `sub` do usuário.
- **Dependências do Projeto (`requirements.txt` e `auth-service/requirements.txt`):** Adicionadas as bibliotecas `PyJWT>=2.8.0` e `cryptography>=42.0.0`.
- **Configuração de Ambiente (`.env.example`):** Novas variáveis `AUTH_ENABLED`, `AUTH_SERVICE_URL`, `AUTH_USER`, `AUTH_PASSWORD`, `JWT_EXPIRATION_MINUTES`, `RSA_PRIVATE_KEY_PATH`, `RSA_PUBLIC_KEY_PATH`.

### Security & Reliability

- **Segregação Criptográfica Zero Trust (BR01 / NIST SP 800-207):** Chave privada isolada exclusivamente no processo do Auth Service; o pod do Sales Agent nunca recebe nem manipula a chave privada, impedindo forja de tokens.
- **Prevenção de Confusão de Algoritmo (CWE-347):** Decodificação restrita a `RS256`, bloqueando ataques de algoritmo `none` ou transmutação de chave pública para HMAC simétrico.
- **Mitigação de Timing Attack (CWE-208):** Comparação em tempo constante de usuário e senha via `hmac.compare_digest()`.
- **Sanitização de Mensagens e Prevenção de Enumeração (CWE-209):** Respostas de erro uniformes (`{"detail": "Credenciais inválidas"}` / `{"detail": "Token inválido ou expirado"}`).
- **Resiliência e Alta Disponibilidade:** O Sales Agent continua validando tokens vigentes com a chave pública em cache mesmo durante reinicializações da Auth Service.

## [1.4.0] - 2026-08-30

### Added

- **Validação SQL Robusta via AST Parsing (T005 / R005):** Substituição completa do validador baseado em Regex pelo analisador de Árvore de Sintaxe Abstrata (AST) determinístico com `sqlglot` configurado para o dialeto DuckDB.
- **Modelos e Enums de Domínio (`src/domain/model/sql_validation.py`):** Criação do enum `SqlViolationType` e dos value objects imutáveis `SqlValidationResult` e `ParsedSqlStatement` (`frozen=True`).
- **Hierarquia de Exceções de Domínio (`src/domain/exception/sql_validation_exceptions.py`):** Exceções tipadas `SqlValidationError`, `SqlSyntaxError` e `SqlSecurityViolationError` para transporte de metadados de violação estruturada.
- **Serviço de Domínio de Segurança (`src/domain/service/sql_security_validator.py`):** Serviço puro `SqlSecurityValidator` com regras determinísticas para validação de nós raiz (`SELECT`, `WITH`, `UNION`), bloqueio recursivo de 15 operações mutacionais e 10 funções de acesso a arquivos.
- **Porta de Saída `SqlParserPort` (`src/application/port/outbound/sql_parser_port.py`):** Interface abstrata desacoplando a camada de aplicação/domínio do motor de parsing de infraestrutura.
- **Adaptador de Parsing `SqlGlotParserAdapter` (`src/adapter/outbound/parser/sqlglot_parser_adapter.py`):** Implementação concreta de `SqlParserPort` utilizando `sqlglot` com suporte a DuckDB, extração recursiva de funções e isolamento estrito de literais.
- **Suíte de Testes Automatizados de Validação AST:** Novos testes em `tests/unit/test_sql_security_validator.py`, `tests/unit/test_sqlglot_parser_adapter.py` e `tests/integration/test_ast_sql_validation_e2e.py` validando SLA de latência (< 5ms), eliminação de falsos positivos e bloqueio de DDL/DML.
- **Artefatos de Governança ADD:** Inclusão das especificações `R005-ast-sql-validation.md`, `T005-ast-sql-validation.md`, `TEST005-ast-sql-validation.md`, `S005-ast-sql-validation.md` e `Q005-ast-sql-validation.md`.

### Changed

- **Refatoração de `SecuredSQLQueryTool` (`src/adapter/inbound/llm/sql_fallback_tool.py`):** Removidos regexes e heurísticas textuais; a ferramenta agora delega a análise estrutural para o `SqlParserPort` e as regras de segurança para o `SqlSecurityValidator` via injeção de dependência.
- **Fábrica `create_sql_fallback_tool`:** Atualizada para instanciar e injetar automaticamente o `SqlGlotParserAdapter` e o `SqlSecurityValidator`.
- **Dependências do Projeto (`requirements.txt`):** Adicionada a biblioteca `sqlglot>=26.0.0`.

### Security & Reliability

- **Eliminação de Falsos Positivos em Literais (AC02 / BR02):** Consultas contendo palavras-chave reservadas dentro de constantes de texto (ex: `WHERE product_id = 'DROP_01'`) executam com segurança sem serem rejeitadas indevidamente.
- **Defesa em Profundidade contra SQLi e Prompt Injection (OWASP LLM01 / A03):** Bloqueio garantido de operações mutacionais (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, etc.) em qualquer profundidade da árvore sintática (subselects, CTEs e UNIONs).
- **Proteção contra Stacked Queries e Acesso a Arquivos:** Bloqueio de declarações encadeadas (`statement_count > 1`) e de funções de leitura/escrita no disco do host (`read_csv`, `read_text`, `read_blob`, `read_parquet`, `read_json`, `glob`).
- **Sanitização de Respostas e Observabilidade:** Redação de paths internos do servidor (`[REDACTED_PATH]`), orientação amigável de autocorreção em erros de sintaxe e preservação do log `[MISSING_TOOL]`.

## [1.3.0] - 2026-08-30

### Added

- **Escalabilidade de Sessão Distribuída (T004):** Transição da camada de computação do Sales Agent para uma arquitetura completamente stateless baseada em 12-Factor App, desacoplando a persistência do histórico conversacional para o Redis.
- **Porta de Saída `SessionStorePort`:** Definição do contrato de persistência desacoplada em `src/application/port/outbound/session_store_port.py` com suporte a `get_history`, `save_history`, `clear_history` e `exists`.
- **Adaptador de Persistência `RedisSessionAdapter`:** Implementação em `src/adapter/outbound/redis/redis_session_adapter.py` com serialização/desserialização JSON de mensagens LangChain (`messages_to_dict` / `messages_from_dict`), renovação automática de TTL a cada interação (`SESSION_TTL_SECONDS`), e timeouts defensivos de socket (3s).
- **Provedor Plugável `SessionFactory`:** Fábrica centralizada em `src/adapter/outbound/session_factory.py` que resolve dinamicamente entre `RedisSessionAdapter` (`SESSION_STORE=redis`) e `SessionMemoryAdapter` (`SESSION_STORE=memory` / fallback padrão).
- **Modelos e Exceções de Domínio de Sessão:** Entidade imutável `SessionContext` com validação de identificador por regex (`^[a-zA-Z0-9_-]+$`, max 128 chars), prefixo namespaced isolado (`sales_agent:session:<session_id>`), e exceções de domínio em `src/domain/exception/session_exceptions.py` (`SessionDomainError`, `InvalidSessionIdError`, `SessionStorageError`, `SessionConnectionError`).
- **Manifestos Declarativos K3s/Kubernetes:** Criação da pasta `k8s/` contendo `redis-deployment.yaml`, `redis-service.yaml`, `app-deployment.yaml` (multi-réplica, probes de liveness/readiness, resource limits), `app-service.yaml` e `configmap.yaml`.
- **Suíte de Testes de Integração Multi-Réplica:** Criação de `tests/integration/test_distributed_session_integration.py` validando continuidade de contexto conversacional e paridade em múltiplos turnos entre réplicas independentes (Pod A e Pod B) compartilhando o Redis Store.
- **Artefatos de Governança ADD:** Inclusão das especificações `R004-distributed-session-scalability.md`, `T004-distributed-session-scalability.md`, `TEST004-distributed-session-scalability.md`, `S004-distributed-session-scalability.md` e `Q004-distributed-session-scalability.md`.

### Changed

- **Stateless Web Chat Application Service:** `WebChatApplicationService` refatorado para eliminar o armazenamento em heap `_active_sessions`, injetando dinamicamente o histórico a partir do `SessionStorePort` por requisição e persistindo o turno atualizado.
- **Injeção de Dependências no `chat_controller`:** Atualização do provider singleton para instanciar o serviço com o `SessionStorePort` resolvido via `SessionFactory`.
- **Dependências do Projeto (`requirements.txt`):** Adicionado pacote oficial `redis>=5.0.0`.

### Security & Reliability

- **Prevenção de Injeção de Chaves (OWASP A03):** Validação estrita do `session_id` e namespacing de chaves impedem poluição de cache ou colisão acidental entre instâncias de aplicação.
- **Proteção contra Esgotamento de Memória (OWASP API4):** Expiração automática por TTL configurável (padrão 86.400s / 24h) no Redis e capacidade limitada com política LRU (500 sessões) no adaptador em memória.
- **Sanitização de Erros e Prevenção de Vazamento (OWASP A05):** Mascaramento de erros de conexão e timeouts internos em mensagens neutras para o usuário final, com rastreabilidade estruturada nos logs do servidor.
- **Hardening de Infraestrutura:** Serviço Redis operando estritamente em rede interna ClusterIP, credenciais sensíveis gerenciadas via Kubernetes Secrets (`SecretKeyRef`), e limites de CPU/RAM declarados contra DoS.

## [1.2.0] - 2026-08-30

### Added

- **OLAP Pushdown Aggregations (T003):** Migração completa dos cálculos matemáticos de métricas básicas e avançadas para o motor SQL nativo do DuckDB, garantindo latência de sub-segundo e escalabilidade para 50M+ registros.
- **Domain Value Objects de Agregação:** Criação de 10 novos modelos imutáveis em `src/domain/model/aggregation_models.py` (`ProductAggregation`, `LocationSalesAggregation`, `TotalSalesAggregation`, `PlannedVsActualAggregation`, `PromotionImpactAggregation`, `ServiceLevelBottleneckAggregation`, `RevenueDeficitAggregation`, `AverageDiscountAggregation`, `SeasonalityAggregation`, `PriceElasticityAggregation`).
- **Contratos de Agregação em `SalesDataPort`:** Definição de métodos analíticos explícitos na porta de saída (`aggregate_top_selling_product`, `aggregate_top_locations`, `aggregate_total_sales`, etc.).
- **Queries SQL Vetorizadas no `DuckDbSalesAdapter`:** Implementação de consultas otimizadas utilizando `SUM`, `AVG`, `FILTER (WHERE ...)`, `GROUP BY` e `ORDER BY` diretamente no banco colunar em memória.
- **Suíte de Testes de Paridade e Integração:** Criação de `tests/integration/test_sales_metrics_integration.py` validando 100% de paridade matemática e funcional entre o pushdown SQL e as regras de negócio.
- **Artefatos de Governança ADD:** Inclusão das especificações `R003-analytical-engine-scalability.md`, `T003-analytical-engine-scalability.md`, `TEST003-analytical-engine-scalability.md`, `S003-analytical-engine-scalability.md` e `Q003-analytical-engine-scalability.md`.

### Changed

- **Refatoração de `BasicMetricsService` e `AdvancedMetricsService`:** Os serviços de domínio agora recebem DTOs pré-agregados compactos em vez de sequências de registros brutos (`Sequence[SaleRecord]`), mantendo o domínio puro e as regras de negócio isoladas.
- **Orquestração em `SalesMetricsApplicationService`:** Atualizado para delegar a recuperação de agregações para a `SalesDataPort` e repassar os resultados aos serviços de domínio.

### Removed

- **Eliminação de `get_all_sales()`:** O método `get_all_sales()` foi completamente removido de `SalesDataPort` e `DuckDbSalesAdapter` para mitigar definitivamente riscos de exaustão de memória (OOM). Para consultas filtradas de registros, utiliza-se `get_sales_by_filter()`.

### Performance & Security

- **Consumo de Memória O(1):** A aplicação Python não transfere mais datasets brutos sobre o barramento de memória, mantendo a pegada de memória constante mesmo sob cargas analíticas de dezenas de milhões de linhas.
- **Hardening DuckDB:** Parametrização integral das consultas de agregação e manutenção do bloqueio de acesso a arquivos externos (`enable_external_access = false`).

## [1.1.0] - 2026-08-28


### Added

- **Web Chat Interface:** Nova aplicação web (FastAPI + Vanilla JS) que expõe o Sales Data Analysis Agent via API REST (`POST /chat`), eliminando a dependência do terminal CLI.
- **Frontend Responsivo Premium:** UI com Dark Mode, micro-animações, suporte a Markdown nas respostas do bot e integração sem dependência de build (Node/npm).
- **Domain Value Object `SessionContext`:** Para rastrear as sessões via `session_id`.
- **DTOs de Entrada e Saída:** `ChatRequestDTO` e `ChatResponseDTO` definidos via Pydantic para comunicação tipada com a interface web.
- **API `WebChatUseCase` e Orquestração:** Implementação do `WebChatApplicationService` integrando as sessões da interface web diretamente ao agente LangChain de análise de vendas.
- **Armazenamento de Sessões e Descarte:** Implementação de `InMemorySessionHistoryAdapter` garantindo a persistência do histórico conversacional na memória, acoplado com uma estratégia de descarte LRU (Least Recently Used) com capacidade padrão de 500 sessões ativas para mitigar esgotamento de recursos.
- **Proteção XSS Frontend:** Sanitização via `DOMPurify` implantada globalmente antes da conversão e inserção do Markdown.
- **Proteções Headers HTTP e CORS:** Configuração aprimorada de middleware FastAPI com origens restritas explicitamente, além dos cabeçalhos anti-sniff e clickjacking.
- **Redirecionamento de Raiz:** Adicionado redirecionamento (`307 Temporary Redirect`) de `GET /` para a página inicial da interface em `/static/index.html`.
- **Integração End-to-End:** Novos testes de integração simulando múltiplos turnos e checando resiliência.
- **Documentação de API Atualizada:** Inclusão do documento `docs/api/web-chat.md`.

### Fixed

- **Web Chat Network Error (B001):** Corrigido o erro 500 ao iniciar sessões no chat web. A falha ocorria por falta de injeção de dependências do `SalesAgent` e ausência das chaves de API. A correção incluiu a restauração da inicialização via `bootstrap_agent()` no `chat_controller`, a inclusão do carregamento correto das variáveis de ambiente (`load_dotenv()`) no serviço web, e a implementação de uma barreira segura (`try...except`) que evita crashs da aplicação, retornando erros encapsulados e seguros para o frontend.
- **Desconto Médio e Análise de Promoções (B002):** Corrigida a falha no cálculo do valor total de desconto e da margem de desconto médio em promoções no `AdvancedMetricsService`. O cálculo anterior subtraía a receita real total da receita planejada globalmente, fazendo com que itens vendidos acima do valor planejado anulassem os descontos aplicados. A nova lógica acumula separadamente apenas transações com desconto efetivo (`actual_price < planned_price`), preservando a precisão analítica do agente nas estatísticas de vendas promocionais.
- **Gargalos de Nível de Serviço Logístico / SLA (B003):** Corrigido o resultado falso-positivo na identificação de gargalo de SLA em `AdvancedMetricsService.analyze_service_level_bottlenecks`. A verificação de desempate foi refinada para comparar a igualdade exata dos valores arredondados de 4 casas decimais (`min_sla == max_sla`), evitando que imprecisões de ponto flutuante em Python (ex: `0.9800 - 0.9799 < 1e-4`) considerassem erradamente médias distintas como empates. Quando todas as localidades possuem médias idênticas, retorna `worst_location="N/A"`; quando uma localidade apresenta média inferior (ex: `Whse_A` a 97,99%), ela é identificada corretamente como gargalo crítico.
- **Enriquecimento de Esquema do Fallback SQL (B004):** Corrigida a geração de consultas SQL incorretas no `SecuredSQLQueryTool` quando exposto a perguntas ad-hoc sem promoção. O esquema do campo `query` em `SQLQueryInput` e a descrição da ferramenta foram enriquecidos com definições completas de colunas, semântica de `promotion_type IS NULL` / `HAVING COUNT(promotion_type) = 0` e fórmulas de receita (`SUM(actual_quantity * actual_price)`). Adicionado payload de aviso estruturado (`EMPTY_RESULT_SET`) com orientações de auto-correção (`self_correction_guidance`) quando a consulta DuckDB retorna zero registros, prevenindo alucinações inversas do agente LLM.

### Security

- **Proteção e Sanitização do Fallback SQL (S004):** Adicionado bloqueio de ponto e vírgula intermediário (`;`) em consultas personalizadas no `SecuredSQLQueryTool` para mitigar tentativas de execução de instruções múltiplas empilhadas (*stacked queries*). Implantada sanitização automática por regex em mensagens de exceção para prevenir vazamento de caminhos locais do sistema de arquivos (`[REDACTED_PATH]`).

## [1.0.0] - 2026-08-27

### Added

- Arquitetura Hexagonal (Ports & Adapters) inicializada.
- Entidades de domínio e Value Objects (`SaleRecord`, `MetricResult`).
- Serviços de domínio para métricas básicas e complexas (10 regras determinísticas).
- Portas de entrada (`SalesAnalysisUseCase`) e saída (`SalesDataPort`).
- `SalesMetricsApplicationService` orquestrando casos de uso.
- `DuckDbSalesAdapter` implementando motor OLAP in-memory para ingestão de `sales.csv`.
- 10 ferramentas de domínio acopladas ao LangChain (`@tool`).
- `SecuredSQLQueryTool` atuando como fallback para consultas ad-hoc seguras (bloqueando DML/DDL).
- Configuração de LLM Agnóstico (OpenAI, Anthropic, Gemini) via `LLMFactory`.
- Interface interativa no terminal (CLI) usando agente orquestrador do LangChain.
- Cobertura abrangente de testes unitários e de integração (84 testes totais).
- Empacotamento em contêiner via `Dockerfile`.
- Documentação técnica, arquitetônica e guia de uso atualizados (`README.md`).

### Security

- Acesso à leitura arbitrária de arquivos pelo DuckDB foi bloqueado (`enable_external_access: false`).
- Parsing resiliente implementado para formatos de data brasileiros e ISO.
- Janela de memória conversacional implementada para prevenir exaustão de token/custo.
