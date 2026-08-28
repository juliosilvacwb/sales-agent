# 🚀 Sales Data Analysis Agent

> **Agente de Inteligência Artificial para Análise Conversacional de Dados de Vendas com Arquitetura Hexagonal, DuckDB e LangChain.**

[![GitHub Repo](https://img.shields.io/badge/GitHub-juliosilvacwb%2Fsales--agent-blue?logo=github)](https://github.com/juliosilvacwb/sales-agent)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-juliosilvacwb%2Fsales--agent-blue?logo=docker)](https://hub.docker.com/r/juliosilvacwb/sales-agent)

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

### Clonar o Repositório

```bash
git clone https://github.com/juliosilvacwb/sales-agent.git
cd sales-agent
```

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

### 🐳 Execução via Docker & Docker Hub

A imagem pré-construída da aplicação está disponível publicamente no Docker Hub em:
👉 **[juliosilvacwb/sales-agent no Docker Hub](https://hub.docker.com/r/juliosilvacwb/sales-agent)**

#### 1. Executar Imagem Pública (Recomendado)

##### 🌐 Modo Web API (Padrão - FastAPI na porta 8000)

```bash
# Executa a aplicação Web em background mapeando a porta 8000
docker run -d \
  --name sales-agent-web \
  -p 8000:8000 \
  --env-file .env \
  juliosilvacwb/sales-agent:latest
```

> Acesse a interface web em `http://localhost:8000/` e a documentação Swagger em `http://localhost:8000/docs`.

##### 💻 Modo CLI (Terminal Interativo)

```bash
# Executa a interface de linha de comando no terminal
docker run -it --rm \
  --env-file .env \
  --entrypoint python \
  juliosilvacwb/sales-agent:latest -m src.adapter.inbound.cli.main
```

---

#### 2. Passando Variáveis de Ambiente Diretas no Comando (sem arquivo .env)

##### 🌐 Modo Web API via Variáveis Diretas (FastAPI + Porta 8000)

```bash
docker run -d \
  --name sales-agent-web \
  -p 8000:8000 \
  -e LLM_PROVIDER=openai \
  -e MODEL_NAME=gpt-4o-mini \
  -e TEMPERATURE=0.0 \
  -e OPENAI_API_KEY="sk-proj-sua-chave-api-aqui" \
  -e DATASET_PATH=/app/dataset/sales.csv \
  -e LOG_LEVEL=INFO \
  juliosilvacwb/sales-agent:latest
```

##### 💻 Modo CLI via Variáveis Diretas (Terminal Interativo)

```bash
docker run -it --rm \
  -e LLM_PROVIDER=openai \
  -e MODEL_NAME=gpt-4o-mini \
  -e TEMPERATURE=0.0 \
  -e OPENAI_API_KEY="sk-proj-sua-chave-api-aqui" \
  -e DATASET_PATH=/app/dataset/sales.csv \
  -e LOG_LEVEL=INFO \
  --entrypoint python \
  juliosilvacwb/sales-agent:latest -m src.adapter.inbound.cli.main
```

---

#### 3. Build, Tag e Push Local (Para Desenvolvedores)

Caso queira construir e publicar sua própria versão:

```bash
# 1. Construir a imagem Docker localmente
docker build -t sales-agent:latest .

# 2. Marcar a imagem com seu usuário no Docker Hub
docker tag sales-agent:latest juliosilvacwb/sales-agent:latest

# 3. Publicar a imagem no Docker Hub
docker push juliosilvacwb/sales-agent:latest
```

---

## 🧪 Executando os Testes

O projeto possui uma suíte completa de testes automatizados unitários e de integração:

### Executar Todos os Testes

```bash
python -m pytest
```

### Executar Apenas os Testes Unitários

```bash
python -m pytest tests/unit
```

### Executar Apenas os Testes de Integração End-to-End

```bash
python -m pytest tests/integration
```

---

## 🔒 Segurança e Observabilidade

- **Prevenção de Injeção SQL:** A ferramenta `secured_sql_query` analisa consultas e bloqueia sumariamente quaisquer instruções que não sejam de leitura (`SELECT` ou CTEs `WITH`). Comandos como `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ATTACH`, `COPY` ou múltiplos statements com `;` são rejeitados antes de atingir o banco.
- **Auditoria de Consultas Ad-hoc:** O uso do fallback gera logs com `[MISSING_TOOL]`, permitindo que o time de engenharia analise as perguntas mais frequentes não cobertas e evolua o catálogo de Domain Tools com novas regras determinísticas.
