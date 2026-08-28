# 🚀 Sales Data Analysis Agent

> **Agente de Inteligência Artificial para Análise Conversacional de Dados de Vendas com Arquitetura Hexagonal, DuckDB e LangChain.**

---

## 📌 Visão Geral

O **Sales Data Analysis Agent** é uma solução de engenharia de IA projetada para democratizar o acesso e a análise de dados tabulares de vendas (`sales.csv`). Usuários e executivos podem realizar consultas analíticas e estratégicas em linguagem natural através de uma interface interativa no terminal (CLI) ou contêiner Docker.

### 🌟 Diferenciais de Arquitetura & Engenharia

1. **Abordagem Híbrida Inteligente:**
   - **10 Domain Tools Determinísticas:** Métricas críticas de negócio (ex: produto mais vendido, SLA logístico, impacto de promoções, déficit de receita, elasticidade) são calculadas em código puro Python, imunes a alucinações matemáticas de LLMs.
   - **Secured SQL Fallback Tool:** Perguntas analíticas *ad-hoc* não previstas no catálogo de domínio são roteadas para uma ferramenta de consulta SQL com proteção rigorosa.
2. **Interface Web Premium (FastAPI + Vanilla JS):** Acesso democratizado aos dados de vendas através de um frontend moderno (Dark Mode, layout responsivo) comunicando-se com a API REST de forma assíncrona, eliminando a dependência da CLI.
3. **DuckDB In-Process (OLAP):** Mecanismo colunar vetorizado para processamento analítico submilisegundo em memória, sem custos ou complexidade de servidores de banco externos.
4. **Arquitetura Hexagonal (Ports & Adapters):** O núcleo de domínio (regras matemáticas e modelos de dados) possui zero acoplamento com LangChain, DuckDB ou bibliotecas web.
5. **LLM Agnóstico:** Suporte plug-and-play para múltiplos provedores (OpenAI, Anthropic, Google Gemini) via variáveis de ambiente (`.env`).
6. **Observabilidade & Descoberta:** Emissão automática de logs com a tag `[MISSING_TOOL]` quando o fallback SQL é acionado, facilitando a identificação contínua de novas métricas a serem promovidas a Domain Tools.
7. **Segurança Corporativa:** Bloqueio estrito de comandos DML/DDL (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ATTACH`, `COPY`, etc.), e sanitização contra injeção de HTML/JS no frontend (`DOMPurify`), garantindo imutabilidade e integridade.

---

## 🏛️ Arquitetura do Sistema

O projeto adota o padrão **Hexagonal (Ports & Adapters)** para garantir testabilidade máxima, desacoplamento e facilidade de manutenção:

```mermaid
graph TB
    subgraph Inbound Adapters [Adapters - Entrada]
        WebClient[Web Frontend / Browser]
        FastAPI[FastAPI / REST Controller]
        CLI[CLI Main / Terminal Loop]
        Agent[SalesAgent Orchestrator]
        DomainTools[10x LangChain Domain Tools]
        FallbackTool[Secured SQL Fallback Tool]
    end

    subgraph Inbound Ports [Ports - Entrada]
        UseCasePort[SalesAnalysisUseCase Port]
        WebChatPort[WebChatUseCase Port]
    end

    subgraph Application Core [Aplicação]
        AppService[SalesMetricsApplicationService]
        WebChatAppService[WebChatApplicationService]
    end

    subgraph Domain Core [Domínio Puro]
        Models[Domain Models: SaleRecord, MetricResult, SessionContext]
        BasicMetrics[BasicMetricsService]
        AdvancedMetrics[AdvancedMetricsService]
    end

    subgraph Outbound Ports [Ports - Saída]
        DataPort[SalesDataPort Port]
    end

    subgraph Outbound Adapters [Adapters - Saída]
        DuckDBAdapter[DuckDbSalesAdapter - In-Memory OLAP]
        LLMFactory[LLMFactory - LangChain Provider]
        SessionMemory[InMemorySessionHistoryAdapter]
    end

    WebClient -->|POST /chat| FastAPI
    FastAPI --> WebChatPort
    WebChatPort --> WebChatAppService
    WebChatAppService --> Agent
    WebChatAppService --> SessionMemory
    CLI --> Agent
    Agent --> DomainTools
    Agent --> FallbackTool
    DomainTools --> UseCasePort
    FallbackTool --> UseCasePort
    UseCasePort --> AppService
    AppService --> BasicMetrics
    AppService --> AdvancedMetrics
    BasicMetrics --> Models
    AdvancedMetrics --> Models
    AppService --> DataPort
    DataPort --> DuckDBAdapter
    Agent --> LLMFactory
```

---

## 🛠️ Catálogo de Ferramentas de Domínio (Domain Tools)

| Ferramenta | Identificador | Descrição de Negócio |
| --- | --- | --- |
| **Top Produto** | `get_top_selling_product` | Identifica o produto líder em volume e receita gerada. |
| **Top Localidades** | `get_top_locations_by_volume` | Lista as localidades/armazéns com maior volume expedido. |
| **Total de Vendas** | `get_total_sales_in_period` | Calcula quantidade total, receita e ticket médio no período. |
| **Realizado vs Planejado** | `compare_planned_vs_actual_quantity` | Compara volume orçado vs executado e percentual de atingimento. |
| **Impacto de Promoções** | `analyze_promotion_impact` | Mensura lift de volume e desconto médio concedido em campanhas. |
| **Gargalos de SLA** | `analyze_service_level_bottlenecks` | Detecta a localidade com pior nível de serviço logístico. |
| **Déficit de Receita** | `calculate_revenue_deficit` | Calcula a perda financeira estimada por desvios de meta. |
| **Desconto Médio** | `calculate_average_discount` | Avalia a margem de desconto médio aplicado frente ao planejado. |
| **Sazonalidade de Vendas** | `identify_sales_seasonality` | Aponta meses de pico, vale e curva de sazonalidade temporal. |
| **Elasticidade de Preço** | `calculate_price_elasticity` | Calcula o coeficiente de elasticidade-preço da demanda. |
| **Fallback SQL Seguro** | `secured_sql_query` | Executa consultas analíticas `SELECT` ad-hoc com log `[MISSING_TOOL]`. |

---

## 📁 Estrutura de Pastas

```text
challenge_ai_engineer/
├── dataset/
│   └── sales.csv                  # Dataset analítico tabular
├── docs/
│   ├── business-requirements/     # PRD e requisitos funcionais (R001)
│   ├── product-strategy/          # Estratégia de produto (PS001)
│   └── architecture/              # Especificação técnica e tasks (T001)
├── src/
│   ├── domain/                    # DOMÍNIO PURO (Zero frameworks)
│   │   ├── model/                 # SaleRecord, MetricResult
│   │   └── service/               # BasicMetricsService, AdvancedMetricsService
│   ├── application/               # CASOS DE USO E CONTRATOS
│   │   ├── port/
│   │   │   ├── inbound/           # SalesAnalysisUseCase
│   │   │   └── outbound/          # SalesDataPort
│   │   └── service/               # SalesMetricsApplicationService
│   └── adapter/                   # ADAPTERS (Tecnologias externas)
│       ├── inbound/
│       │   ├── cli/               # main.py (Interface do usuário)
│       │   └── llm/               # sales_agent.py, domain_tools.py, sql_fallback_tool.py
│       └── outbound/
│           ├── llm/               # llm_factory.py (OpenAI / Anthropic / Gemini)
│           └── persistence/       # duckdb_sales_adapter.py (DuckDB OLAP)
├── tests/
│   ├── unit/                      # Testes unitários com mocks (100% isolamento)
│   └── integration/               # Testes End-to-End e Happy Path integrados
├── .env.example                   # Modelo de variáveis de ambiente
├── Dockerfile                     # Empacotamento Docker da aplicação
├── pyproject.toml                 # Configurações do Pytest e Linters
└── requirements.txt               # Dependências do projeto
```

---

## 🚀 Como Executar

### Pré-requisitos

- Python 3.10+ instalado
- Chave de API de um provedor de IA (OpenAI, Anthropic ou Google Gemini)

### Configuração do Ambiente (.env)

Copie o arquivo de exemplo e defina suas credenciais:

```bash
cp .env.example .env
```

Edite o `.env` conforme o provedor desejado:

```env
# Exemplo com OpenAI
LLM_PROVIDER=openai
MODEL_NAME=gpt-4o-mini
OPENAI_API_KEY=sk-...

# Exemplo com Anthropic
# LLM_PROVIDER=anthropic
# MODEL_NAME=claude-3-5-sonnet-20241022
# ANTHROPIC_API_KEY=sk-ant-...

# Exemplo com Google Gemini
# LLM_PROVIDER=google
# MODEL_NAME=gemini-1.5-pro
# GOOGLE_API_KEY=AIzaSy...

DATASET_PATH=dataset/sales.csv
LOG_LEVEL=INFO
```

---

### Execução Local (CLI)

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

Inicie o agente interativo:

```bash
python -m src.adapter.inbound.cli.main
```

---

### Execução Local (Web Interface)

Inicie o servidor FastAPI:

```bash
python -m uvicorn src.adapter.inbound.web.main:app --reload
```

Acesse a interface web abrindo o navegador em: `http://localhost:8000/`

A documentação da API (Swagger UI) está disponível em: `http://localhost:8000/docs`

---

### Execução via Docker

Construa a imagem Docker:

```bash
docker build -t sales-agent .
```

Execute o contêiner interativamente passando as variáveis de ambiente:

```bash
docker run -it --rm --env-file .env sales-agent
```

---

## 🧪 Executando os Testes

O projeto possui uma suíte completa de testes automatizados unitários e de integração:

### Executar Todos os Testes

```bash
pytest
```

### Executar Apenas os Testes Unitários

```bash
pytest tests/unit
```

### Executar Apenas os Testes de Integração End-to-End

```bash
pytest tests/integration
```

---

## 🔒 Segurança e Observabilidade

- **Prevenção de Injeção SQL:** A ferramenta `secured_sql_query` analisa consultas e bloqueia sumariamente quaisquer instruções que não sejam de leitura (`SELECT` ou CTEs `WITH`). Comandos como `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ATTACH`, `COPY` ou múltiplos statements com `;` são rejeitados antes de atingir o banco.
- **Auditoria de Consultas Ad-hoc:** O uso do fallback gera logs com `[MISSING_TOOL]`, permitindo que o time de engenharia analise as perguntas mais frequentes não cobertas e evolua o catálogo de Domain Tools com novas regras determinísticas.
