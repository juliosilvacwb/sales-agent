# Product Strategy: Sales Data Analysis Agent

## Strategic Context

**Executive Summary:** Esta iniciativa estratégica foi solicitada com o objetivo de construir um Agente de Inteligência Artificial capaz de democratizar o acesso aos dados de vendas da companhia (atualmente exportados no formato `sales.csv`). O sistema deve permitir que usuários de negócios façam perguntas analíticas em linguagem natural. A diretriz técnica principal é não focar apenas em um MVP funcional, mas garantir uma arquitetura *Enterprise-grade* que priorize a segurança da informação, modularização de código, e baixa alucinação (determinismo), preparando o terreno para futura escalabilidade do produto.

## Market & Competitor Analysis

Avaliando as abordagens atuais de mercado (SaaS e ferramentas internas) para aplicações de IA sobre dados tabulares, identificamos três padrões arquiteturais:

1. **Code Execution Agent (Abordagem Pandas/Python Dinâmico):**
Rápido para prototipagem. O LLM gera e executa código nativo sob demanda para processar o arquivo.
   - *Desvantagens:* Inviável para ambientes corporativos rígidos devido ao altíssimo risco de segurança (execução arbitrária de código dinâmico) e instabilidade em regras de negócio complexas.
2. **Semantic Layer / SQL Agent Puro:** Os dados são ingeridos em um banco relacional ou OLAP. O LLM atua estritamente como um tradutor de Linguagem Natural para SQL.
   - *Desvantagens:* Pode alucinar tabelas se o contexto não for perfeitamente provido. Frequentemente ignora lógicas de negócio já homologadas pela engenharia, forçando o LLM a "redescobrir" cálculos complexos via SQL.
3. **Tool-calling Customizado (Domain Driven):** O LLM é acoplado a um SDK interno. Ele recebe ferramentas (Tools) que encapsulam as regras de negócio exatas da empresa.
   - *Desvantagens:* Rigidez. O usuário só consegue respostas para perguntas que os engenheiros previram e programaram.

## Ideation Results: A Evolução Híbrida (Domain Tools + Secured SQL Fallback)

Para atender à demanda garantindo segurança e flexibilidade, a arquitetura ideal não é nenhuma das três isoladamente. Propomos uma orquestração híbrida de **Múltiplas Ferramentas de Domínio** complementada por um **Mecanismo de SQL Seguro** (apenas como *fallback*).

**1. O Leque de "Domain Tools" (Primeira Linha de Defesa):**
Vamos prever as métricas mais críticas e perguntas frequentes do negócio, expondo-as como ferramentas determinísticas para o agente. Isso garante 100% de precisão para as consultas vitais.

- *Perguntas Comuns (Mapeadas para Tools):*
  - **"Qual produto foi mais vendido?"** -> `Tool: get_top_selling_product(limit)`
  - **"Qual local teve maior volume de vendas?"** -> `Tool: get_top_locations_by_volume()`
  - **"Qual foi o total de vendas em determinado período?"** -> `Tool: get_total_sales_in_period(start_date, end_date)`
  - **"Qual a diferença entre quantidade planejada e realizada?"** -> `Tool: compare_planned_vs_actual_quantity()`
  - **"Qual o impacto das promoções no preço e volume vendido?"** -> `Tool: analyze_promotion_impact()`
  - *(Nova)* **"Qual local apresenta o pior nível de serviço (SLA logístico) médio?"** -> `Tool: analyze_service_level_bottlenecks()`
  - *(Nova)* **"Qual a perda financeira estimada por não atingir a quantidade planejada de vendas?"** -> `Tool: calculate_revenue_deficit()`
  - *(Nova)* **"Qual a margem de desconto médio aplicado frente ao preço planejado?"** -> `Tool: calculate_average_discount()`
  - *(Nova)* **"Quais são os padrões de sazonalidade (dias da semana ou meses com picos históricos de venda)?"** -> `Tool: identify_sales_seasonality()`
  - *(Nova)* **"Existe correlação (elasticidade) entre a agressividade do desconto e o aumento real no volume vendido?"** -> `Tool: calculate_price_elasticity()`

**2. A "Skill" de Conhecimento do Banco de Dados (Dicionário de Dados):**
Para viabilizar consultas *ad-hoc* não previstas nas ferramentas acima, o agente receberá em seu `System Prompt` a topologia exata e a semântica da tabela de vendas (`sales_data`). O dicionário de dados injetado será:

- `product_id`: Identificador único do produto
- `local`: Local onde a venda foi realizada
- `date`: Data da venda
- `planned_quantity`: Quantidade planejada para venda
- `actual_quantity`: Quantidade realmente vendida
- `planned_price`: Preço planejado do produto
- `promotion_type`: Tipo de promoção aplicada (se houver)
- `actual_price`: Preço real praticado na venda
- `service_level`: Nível de serviço associado à venda
- *Vantagem:* Zera a alucinação estrutural. O LLM mapeia a intenção do usuário contra as colunas reais antes de montar a consulta SQL.

**3. O SQL Fallback Tool Sanitizado (Segurança Corporativa):**
**Regra de Roteamento Estrita:** O *System Prompt* instruirá a IA com clareza absoluta: *"Sempre priorize responder usando as Domain Tools. Utilize a ferramenta SQL como fallback APENAS caso nenhuma Domain Tool seja capaz de responder à pergunta."*
Quando este fallback for acionado para uma pergunta ad-hoc, o LLM utilizará o `SecuredSQLQueryTool`.

- *Como funciona:* Esta tool atua como um *middleware* defensivo. Ela intercepta a query SQL gerada pelo LLM e aplica regras restritivas (bloqueando instruções DML/DDL como `DROP`, `DELETE`, `UPDATE`, `INSERT`). A execução ocorre em um banco de dados temporário configurado em modo estrito de Leitura (`Read-Only`).
- *Vantagem:* Previne incidentes de "SQL Injection por IA" e garante aderência às políticas de governança da informação.

## Prioritization Matrix

| Dimension / Solução | Pandas Agent | SQL Agent Puro | **Híbrido Refinado (Tools + Secured SQL)** |
| :--- | :--- | :--- | :--- |
| **Business Value (KPIs exatos)** | 2 | 3 | **5** |
| **User Impact (Flexibilidade)** | 3 | 4 | **5** |
| **Strategic Alignment (Governança)** | 1 | 3 | **5** |
| **Effort Estimate (1=Difícil, 5=Fácil)** | 5 | 4 | **2** (Exige pipeline customizado) |
| **Risk (Segurança da Informação)** | 1 | 2 | **5** (Blindagem robusta) |
| **TOTAL (Ponderado)** | 12 | 16 | **22** |

## Recommendations

A aprovação deve seguir para a arquitetura **Híbrida Refinada (Domain Tools + Secured SQL Fallback)**. Ela maximiza a flexibilidade para os usuários de negócios ao mesmo tempo que mantém a governança e a segurança técnica exigidas pela engenharia.

### Justificativa de Engenharia & Decisões Arquiteturais Fechadas

1. **Decisão do Banco de Dados Analítico (DuckDB):**
   - **Engine OLAP Colunar e Vetorizada:** Diferente de bancos relacionais OLTP (como SQLite ou MySQL) que processam linha a linha, o DuckDB armazena e lê colunas em blocos de memória com execução vetorizada. Isso garante performance submilisegunda em cálculos agregados analíticos (`SUM`, `AVG`, `GROUP BY`, time-series).
   - **Ingestão Nativa e Instantânea de CSV:** Através do `read_csv_auto`, os dados do `sales.csv` são carregados diretamente sem sobrecarga de infraestrutura ou pipelines ETL complexos.
   - **In-Process & Serverless:** Opera embutido diretamente no runtime Python, sem necessidade de servidores externos ou portas de rede, facilitando a portabilidade, testes locais e empacotamento em Docker.
2. **Provedor de LLM Agnóstico (Multi-Model & Zero Vendor Lock-in):**
   - A camada de inferência não deve ficar acoplada a um único provedor proprietário. Deve utilizar uma fábrica (*LLM Factory* / `init_chat_model`) orquestrada via variáveis no `.env` (ex: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_TEMPERATURE`).
   - O usuário pode alternar transparentemente entre OpenAI (GPT-4o, GPT-4o-mini), Anthropic (Claude 3.5 Sonnet), Google Gemini, Groq ou modelos locais via Ollama.
3. **Isolamento de Domínio (Clean Architecture):** Todo o núcleo de negócios e cálculos analíticos deve ser construído utilizando uma arquitetura Orientada a Objetos e princípios *Clean Architecture* antes de ser exposto como *Tools*. Se uma regra de cálculo mudar, altera-se apenas a classe correspondente no backend Python, isolando completamente o LLM das regras de negócio. O agente foca apenas no roteamento da intenção.
4. **Segurança em Camadas (Defense in Depth):** A arquitetura defende o sistema em múltiplos pontos: nas ferramentas tipadas, no *middleware* de sanitização de consultas, e na configuração Read-Only da infraestrutura de dados.
5. **Observabilidade Orientada a Produto:** Implementação de logs sinalizados com a tag `[MISSING_TOOL]` sempre que o fallback SQL for acionado. Isso permite que Product Managers e Engenheiros analisem manualmente as perguntas não mapeadas mais frequentes e priorizem a criação de novas Domain Tools.
6. **Preparação para o Futuro:** O padrão de ingestão do CSV para DuckDB reflete um pipeline analítico moderno. Se o dataset for migrado para um Data Warehouse corporativo (Snowflake, BigQuery) no futuro, a interface de domínio do Agente permanece intacta.

### Sequenciamento de Implementação (Roadmap)

1. **Pipeline ETL & Data Store (Fase 1):** Ingestão do `sales.csv` diretamente no **DuckDB** (*in-process* / em memória), garantindo schema tipado e consultas colunares otimizadas.
2. **Domain Tools e Core OOP (Fase 2):** Desenvolver o núcleo de negócio em classes e módulos Python elegantes e altamente testáveis. Em seguida, encapsular essas lógicas em ferramentas tipadas para o Agente e homologá-las separadamente.
3. **Governança SQL (Fase 3):** Construir a `SecuredSQLQueryTool` conectada ao DuckDB com bloqueio estrito de instruções DML/DDL (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ATTACH`, `COPY`) e execução somente-leitura.
4. **Orquestração e Interface (Fase 4):** Unificar as *Tools* no LLM Agent usando LangChain com suporte a **LLM Agnóstico** (configurável via `.env`), configurando o System Prompt com o Dicionário de Dados. Desenvolver um *loop* interativo (CLI Chat).
5. **Documentação e Empacotamento (Fase 5):** Redigir a documentação técnica principal (`README.md`) detalhando a arquitetura escolhida, instruções de uso, troca de provedores LLM e dependências. Finalizar com empacotamento em `Dockerfile`.

### Dependencies e Stack

- `langchain`, `langchain-core` e provedores de chat (ex: `langchain-openai`, `langchain-anthropic`, `langchain-google-genai` ou inicialização dinâmica via `init_chat_model`).
- `duckdb`: Banco de dados analítico (OLAP) in-process, colunar e vetorizado.
- `python-dotenv`: Para gerenciamento flexível e seguro de variáveis de ambiente (`LLM_PROVIDER`, `LLM_MODEL`, `API_KEY`, etc.), desacoplando o código de qualquer credencial ou modelo fixo.
