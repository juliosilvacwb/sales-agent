# T001: Sales Data Analysis Agent Architecture

## PRD Reference

- **PRD:** [R001-sales-agent.md](../business-requirements/R001-sales-agent.md)
- **Product Strategy:** [PS001-sales-agent.md](../product-strategy/PS001-sales-agent.md)

## Technical Goal

Desenvolver um Agente de IA em Python que atue como uma interface conversacional para análise de dados de vendas tabulares (`sales.csv`). O sistema utilizará uma arquitetura Híbrida (Domain Tools + Secured SQL Fallback) e será estruturado sob os princípios da Arquitetura Hexagonal (Ports & Adapters) para garantir altíssimo isolamento do core business, previsibilidade (zero-shot LLM para as métricas mapeadas) e máxima paralelização no desenvolvimento. O motor de dados será o DuckDB in-process e o LLM será agnóstico (OpenAI/Anthropic/Gemini) configurado via `.env`.

## Architecture Decisions

1. **Linguagem & Framework:** Python 3.x com `langchain` e `pytest`.
2. **Arquitetura Hexagonal:** Separação estrita em 3 fases (Domain, Ports, Adapters). O domínio (lógica de cálculo de métricas) não terá qualquer conhecimento sobre LangChain ou DuckDB.
3. **Persistência (OLAP):** `duckdb` (In-process, Colunar) carregando dados via `read_csv_auto` na inicialização para consultas analíticas submilisegundo.
4. **LLM Factory:** Fábrica abstrata usando `init_chat_model` do LangChain para permitir troca de provedor LLM via variáveis de ambiente sem refatoração de código.
5. **Ferramentas (Tools):**
   - *Domain Tools:* Encapsulam Use Cases determinísticos.
   - *Secured SQL Query Tool:* Middleware restritivo que bloqueia injeção DDL/DML.

## Security & Reliability

- **Segurança da Informação:** A `SecuredSQLQueryTool` intercepta e rejeita comandos DML/DDL (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ATTACH`, `COPY`) garantindo que as tabelas do DuckDB não sofram mutação via IA.
- **Prevenção de Alucinação:** O System Prompt injetará o Dicionário de Dados exato para a ferramenta de Fallback, reduzindo alucinação de *schema*.
- **Desacoplamento LLM:** As regras de negócio (KPIs, Elasticidade, SLA) são 100% Python, imunes a flutuações de precisão matemática dos modelos generativos.
- **Observabilidade Analítica:** Injeção de logs granulares com a tag `[MISSING_TOOL]` no acionamento da Fallback Tool para identificação manual de gaps funcionais.

## Technical Checklist (Atomic Tasks)

### [Scaffolding] (Day Zero Preparation)

- [x] Task 001 - [Scaffolding]: Inicializar estrutura do projeto Python (`src`, `tests`, `data`), `requirements.txt` e `.env.example`. (Depends On: —)

### 🔵 Phase 1 — Domain Core (Zero framework dependencies)

- [ ] Task 002 - [Domain-Model]: Criar entidades e *Value Objects* para Vendas e Métricas (`SaleRecord`, `MetricResult`). (Depends On: Task 001)
- [ ] Task 003 - [Domain-Service]: Implementar lógicas puras de métricas básicas (Top Produto, Top Local, Total Vendas, Planned vs Actual, Promoção). (Depends On: Task 002)
- [ ] Task 004 - [Domain-Service]: Implementar lógicas puras de métricas complexas (SLA, Deficit, Desconto, Sazonalidade, Elasticidade). (Depends On: Task 002)

### 🟡 Phase 2 — Ports & Use Cases (All tasks parallel-safe | Depends on Phase 1)

- [ ] Task 005 - [Port-Out]: Definir `SalesDataPort` interface para acesso aos dados analíticos. (Depends On: Task 002)
- [ ] Task 006 - [Port-In]: Definir `SalesAnalysisUseCase` interface para requisições de análise. (Depends On: Task 002)
- [ ] Task 007 - [UseCase]: Implementar `SalesMetricsApplicationService` orquestrando o cálculo das métricas usando o `SalesDataPort`. (Depends On: Task 003, Task 004, Task 005, Task 006)

### 🟢 Phase 3 — Adapters (All tasks parallel-safe | Depends on Phase 2)

- [ ] Task 008 - [Adapter-Persistence]: Implementar `DuckDbSalesAdapter` implementando `SalesDataPort` com carregamento do `sales.csv`. (Depends On: Task 005)
- [ ] Task 009 - [Adapter-LLM]: Implementar as 10 LangChain Tools (`@tool`) encapsulando os UseCases definidos em Phase 2. (Depends On: Task 007)
- [ ] Task 010 - [Adapter-LLM]: Implementar `SecuredSQLQueryTool` para Fallback com bloqueios DML/DDL estritos. (Depends On: Task 008)
- [ ] Task 011 - [Adapter-External]: Configurar fábrica LLM Agnóstica carregando de variáveis `.env`. (Depends On: Task 001)
- [ ] Task 012 - [Adapter-Web/CLI]: Implementar o Agente LangChain (Orquestrador) e o CLI (Chat loop). (Depends On: Task 009, Task 010, Task 011)

### 🏁 Final Phase (Validation & Packaging)

- [ ] Task 013 - [Test-Integration]: Implementar testes de integração (End-to-End Happy Path) garantindo acionamento das tools corretas. (Depends On: Task 012)
- [ ] Task 014 - [Config]: Elaborar `Dockerfile` limpo e finalizar `README.md` com arquitetura e guias de uso. (Depends On: Task 012)

## Task Detailing (Summary Tasks)

### Task 001 - [Scaffolding]: Inicializar estrutura do projeto Python

- **Phase:** —
- **Depends On:** —
- **Parallel With:** —
- **Objective:** Estruturar o projeto com pastas `/src` (arquitetura hexagonal), `/tests` e `/dataset`, configurando `.env.example` e `requirements.txt` (`duckdb`, `langchain`, `python-dotenv`, `pytest`).
- **Files/Path:** `requirements.txt`, `src/`, `tests/`
- **Technical Acceptance Criteria:** `pip install -r requirements.txt` roda com sucesso; pastas padrão criadas.

### Task 002 - [Domain-Model]: Criar entidades e Value Objects

- **Phase:** 1
- **Depends On:** Task 001
- **Parallel With:** —
- **Objective:** Definir os objetos e DTOs de negócio independentes de framework (ex: `SaleRecord`, tipos de métricas).
- **Files/Path:** `src/domain/model/`
- **Technical Acceptance Criteria:** Classes puras Python criadas sem nenhuma dependência externa, passando em testes unitários simples.

### Task 003 - [Domain-Service]: Lógicas puras de métricas básicas

- **Phase:** 1
- **Depends On:** Task 002
- **Parallel With:** Task 004
- **Objective:** Implementar regras matemáticas puras para: Top Produto, Top Local, Total Vendas, Real vs Planejado e Impacto de Promoções.
- **Files/Path:** `src/domain/service/basic_metrics_service.py`
- **Technical Acceptance Criteria:** Funções retornam resultados corretos injetando listas de `SaleRecord`, sem acessar bancos.

### Task 004 - [Domain-Service]: Lógicas puras de métricas complexas

- **Phase:** 1
- **Depends On:** Task 002
- **Parallel With:** Task 003
- **Objective:** Implementar regras matemáticas puras para: SLA Logístico, Deficit Receita, Desconto Médio, Sazonalidade, Elasticidade.
- **Files/Path:** `src/domain/service/advanced_metrics_service.py`
- **Technical Acceptance Criteria:** Cálculos complexos resolvidos com lógica determinística em Python.

### Task 005 - [Port-Out]: Definir SalesDataPort

- **Phase:** 2
- **Depends On:** Task 002
- **Parallel With:** Task 006
- **Objective:** Criar a interface de saída (contrato) estipulando os métodos que a infraestrutura deve prover (ex: `get_sales()`, `execute_query()`).
- **Files/Path:** `src/application/port/out/sales_data_port.py`
- **Technical Acceptance Criteria:** Apenas classes/interfaces abstratas sem implementação de SQL.

### Task 006 - [Port-In]: Definir SalesAnalysisUseCase

- **Phase:** 2
- **Depends On:** Task 002
- **Parallel With:** Task 005
- **Objective:** Criar as interfaces de entrada (comandos de análise) que a camada de agentes irá consumir.
- **Files/Path:** `src/application/port/in/sales_analysis_usecase.py`
- **Technical Acceptance Criteria:** Apenas definição de assinaturas de métodos.

### Task 007 - [UseCase]: Implementar SalesMetricsApplicationService

- **Phase:** 2
- **Depends On:** Task 003, Task 004, Task 005, Task 006
- **Parallel With:** —
- **Objective:** Implementar o UseCase injetando o `SalesDataPort` e chamando os Domain Services para calcular métricas com base nos dados.
- **Files/Path:** `src/application/service/sales_metrics_service.py`
- **Technical Acceptance Criteria:** Passa em testes unitários usando um mock do `SalesDataPort`.

### Task 008 - [Adapter-Persistence]: Implementar DuckDbSalesAdapter

- **Phase:** 3
- **Depends On:** Task 005
- **Parallel With:** Task 009, Task 010, Task 011, Task 012
- **Objective:** Implementar `SalesDataPort` conectando-se ao DuckDB e fazendo `read_csv_auto` do `sales.csv` em memória, retornando objetos do domínio.
- **Files/Path:** `src/adapter/out/persistence/duckdb_sales_adapter.py`
- **Technical Acceptance Criteria:** Integração com DuckDB retorna os dados reais mapeados para os modelos de domínio.

### Task 009 - [Adapter-LLM]: Implementar LangChain Domain Tools

- **Phase:** 3
- **Depends On:** Task 007
- **Parallel With:** Task 008, Task 010, Task 011, Task 012
- **Objective:** Envelopar as chamadas aos métodos de Use Case com o decorador `@tool` do LangChain, definindo os docstrings estritos para roteamento.
- **Files/Path:** `src/adapter/in/llm/domain_tools.py`
- **Technical Acceptance Criteria:** As 10 tools são reconhecidas pelo LangChain e executam as lógicas de domínio.

### Task 010 - [Adapter-LLM]: Implementar SecuredSQLQueryTool e Logs de Observabilidade

- **Phase:** 3
- **Depends On:** Task 008
- **Parallel With:** Task 008, Task 009, Task 011, Task 012
- **Objective:** Ferramenta de Fallback que intercepta SQL, varre comandos proibidos (`DROP`, `DELETE`, `UPDATE` etc.) e repassa ao `DuckDbSalesAdapter`. Deve obrigatoriamente registrar um log com a tag `[MISSING_TOOL]` e a pergunta original.
- **Files/Path:** `src/adapter/in/llm/sql_fallback_tool.py`
- **Technical Acceptance Criteria:** Testes bloqueiam injeções, permitem apenas `SELECT`, e verificam a emissão do log `[MISSING_TOOL]` contendo o input do usuário.

### Task 011 - [Adapter-External]: Configurar LLM Factory

- **Phase:** 3
- **Depends On:** Task 001
- **Parallel With:** Task 008, Task 009, Task 010, Task 012
- **Objective:** Criar a factory que retorna uma instância de chat model (`init_chat_model`) lendo `LLM_PROVIDER` do `.env`.
- **Files/Path:** `src/adapter/out/llm/llm_factory.py`
- **Technical Acceptance Criteria:** Alternância de modelos funciona sem alterar código fonte.

### Task 012 - [Adapter-Web/CLI]: Agente LangChain e CLI

- **Phase:** 3
- **Depends On:** Task 009, Task 010, Task 011
- **Parallel With:** Task 008, Task 009, Task 010, Task 011
- **Objective:** Configurar o agente orquestrador unindo o modelo (Task 011), as Tools (Task 009 e 010) e injetar o Dicionário de Dados no System Prompt. Criar o loop de interação no terminal (main.py).
- **Files/Path:** `src/adapter/in/cli/main.py`, `src/adapter/in/llm/sales_agent.py`
- **Technical Acceptance Criteria:** Chatbot responde no terminal e roteia perguntas simples para Tools e complexas para Fallback SQL.

### Task 013 - [Test-Integration]: Testes End-to-End

- **Phase:** —
- **Depends On:** Task 012
- **Parallel With:** Task 014
- **Objective:** Testar o "Happy Path" injetando um conjunto de dados pequeno no DB e enviando uma intenção para o agente confirmar se a resposta corresponde.
- **Files/Path:** `tests/test_agent_integration.py`
- **Technical Acceptance Criteria:** Teste automatizado do fluxo completo executado com sucesso.

### Task 014 - [Config]: Empacotamento Docker e Documentação

- **Phase:** —
- **Depends On:** Task 012
- **Parallel With:** Task 013
- **Objective:** Criar `Dockerfile` de aplicação estática (copiando dataset/src e executando python app) e finalizar as instruções técnicas no `README.md`.
- **Files/Path:** `Dockerfile`, `README.md`
- **Technical Acceptance Criteria:** Contêiner inicia o bot, README possui todas as etapas documentadas.
