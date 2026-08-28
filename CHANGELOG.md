# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **Gargalos de Nível de Serviço Logístico / SLA (B003):** Corrigido o resultado falso-positivo na identificação de gargalo de SLA em `AdvancedMetricsService.analyze_service_level_bottlenecks`. Quando todas as localidades possuem médias de SLA idênticas (ex: 98,00%), o sistema não mais seleciona arbitrariamente um armazém (ex: `Whse_A`), retornando `worst_location="N/A"` e summary claro com a identificação de equivalência de SLA entre todas as localidades.

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
