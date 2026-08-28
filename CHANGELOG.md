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
