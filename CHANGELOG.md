# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
