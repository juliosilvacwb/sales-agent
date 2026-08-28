# TEST001-sales-agent — Test Coverage Specification

> **Source Task:** [T001-sales-agent.md](../architecture/T001-sales-agent.md)

## Coverage Overview

Esta especificação detalha a cobertura de testes unitários e de integração para o Agente de Análise de Vendas (`T001-sales-agent.md`). A suíte valida a integridade da Arquitetura Hexagonal (Domínio Puro, Portas Inbound/Outbound, Adaptadores DuckDB, LangChain Tools, Fallback SQL Seguro, LLM Factory e CLI).

- **Status Geral de Execução:** 84/84 testes aprovados no `pytest`.
- **Pirâmide de Testes:** Cobertura abrangente em nível Unitário (isolamento de domínio, parsers, segurança SQL e mocks de portas) e nível de Integração (fluxos End-to-End com modelo simulado e persistência DuckDB real).

---

## Test Checklist

### Task 001 — [Scaffolding]: Estrutura do Projeto e Configurações

- [APPROVED] [TEST001-01] [Type: Unit] **test_project_structure_directories**
  - **Target:** `tests/unit/test_scaffolding.py` → `test_project_structure_directories()`
  - **Scenario:** Validar se toda a árvore de diretórios da arquitetura hexagonal e suporte existe.
  - **Arrange:** Obter caminho base do repositório (`Path(__file__)`).
  - **Act:** Checar existência dos diretórios `src/domain`, `src/application`, `src/adapter`, `dataset`, `tests`.
  - **Assert:** Todos os diretórios existem e são do tipo pasta (`is_dir() is True`).
  - **Priority:** P0

- [APPROVED] [TEST001-02] [Type: Unit] **test_required_configuration_files**
  - **Target:** `tests/unit/test_scaffolding.py` → `test_required_configuration_files()`
  - **Scenario:** Validar existência dos arquivos de configuração do ecossistema Python.
  - **Arrange:** Mapear arquivos esperados (`requirements.txt`, `.env.example`, `.gitignore`, `dataset/sales.csv`).
  - **Act:** Verificar a presença dos arquivos no disco.
  - **Assert:** Todos os arquivos essenciais estão presentes (`is_file() is True`).
  - **Priority:** P0

- [APPROVED] [TEST001-03] [Type: Unit] **test_env_example_contains_essential_keys**
  - **Target:** `tests/unit/test_scaffolding.py` → `test_env_example_contains_essential_keys()`
  - **Scenario:** Garantir que `.env.example` fornece as chaves necessárias para LLM e Dataset.
  - **Arrange:** Ler o arquivo `.env.example`.
  - **Act:** Verificar as chaves `LLM_PROVIDER`, `MODEL_NAME`, `DATASET_PATH`.
  - **Assert:** Todas as chaves estão declaradas no template.
  - **Priority:** P1

- [APPROVED] [TEST001-04] [Type: Unit] **test_package_imports**
  - **Target:** `tests/unit/test_scaffolding.py` → `test_package_imports()`
  - **Scenario:** Garantir que todos os pacotes do módulo `src` são importáveis.
  - **Arrange:** Identificar subpacotes de domínio, aplicação e adaptadores.
  - **Act:** Executar `import src.domain`, `import src.application`, `import src.adapter`.
  - **Assert:** Nenhuma exceção `ImportError` ou `ModuleNotFoundError` é lançada.
  - **Priority:** P0

---

### Task 002 — [Domain-Model]: Entidades e Value Objects

- [APPROVED] [TEST001-05] [Type: Unit] **test_sale_record_properties**
  - **Target:** `tests/unit/test_domain_models.py` → `test_sale_record_properties()`
  - **Scenario:** Validar cálculos em propriedades derivadas da entidade `SaleRecord` (receitas, deltas, descontos).
  - **Arrange:** Instanciar `SaleRecord` com valores planejados (100 un @ R$ 50) e realizados (120 un @ R$ 45, promo "Discount_10").
  - **Act:** Acessar `planned_revenue`, `actual_revenue`, `quantity_difference`, `revenue_difference`, `discount_rate`.
  - **Assert:** Receita planejada = 5000.0, realizada = 5400.0, delta volume = +20.0, desconto = 0.10, `is_promoted` = True.
  - **Priority:** P0

- [APPROVED] [TEST001-06] [Type: Unit] **test_sale_record_unpromoted**
  - **Target:** `tests/unit/test_domain_models.py` → `test_sale_record_unpromoted()`
  - **Scenario:** Validar comportamento de `SaleRecord` sem promoção ("None" / None).
  - **Arrange:** Instanciar `SaleRecord` com `promotion_type="None"`.
  - **Act:** Avaliar propriedades `is_promoted` e `discount_rate`.
  - **Assert:** `is_promoted` é False e `discount_rate` é 0.0.
  - **Priority:** P1

- [APPROVED] [TEST001-07] [Type: Unit] **test_metric_results_instantiation**
  - **Target:** `tests/unit/test_domain_models.py` → `test_metric_results_instantiation()`
  - **Scenario:** Garantir instanciabilidade e imutabilidade dos 10 DTOs/Value Objects de resposta.
  - **Arrange:** Importar todos os `MetricResult` (`TopSellingProductResult`, `PriceElasticityResult`, etc.).
  - **Act:** Instanciar cada classe com parâmetros de domínio representativos.
  - **Assert:** Atributos mantêm os valores passados no construtor.
  - **Priority:** P1

---

### Task 003 — [Domain-Service]: Lógicas Puras de Métricas Básicas

- [APPROVED] [TEST001-08] [Type: Unit] **test_get_top_selling_product**
  - **Target:** `tests/unit/test_basic_metrics_service.py` → `test_get_top_selling_product()`
  - **Scenario:** Agrupar e classificar produtos por volume total realizado.
  - **Arrange:** Injetar lista com 2 vendas de `Product_01` (150 + 250) e 1 de `Product_02` (100).
  - **Act:** Executar `BasicMetricsService.get_top_selling_product()`.
  - **Assert:** Produto retornado é `Product_01` com `total_quantity = 400.0` e receita correta.
  - **Priority:** P0

- [APPROVED] [TEST001-09] [Type: Unit] **test_get_top_selling_product_empty**
  - **Target:** `tests/unit/test_basic_metrics_service.py` → `test_get_top_selling_product_empty()`
  - **Scenario:** Tratar lista vazia de vendas sem disparar divisão por zero ou exceção.
  - **Arrange:** Lista vazia `[]`.
  - **Act:** Executar `BasicMetricsService.get_top_selling_product([])`.
  - **Assert:** Retorna `product_id="N/A"` e `total_quantity=0.0`.
  - **Priority:** P1

- [APPROVED] [TEST001-10] [Type: Unit] **test_get_top_locations_by_volume**
  - **Target:** `tests/unit/test_basic_metrics_service.py` → `test_get_top_locations_by_volume()`
  - **Scenario:** Ordenar armazéns/locais pelo volume total e respeitar limite especificado.
  - **Arrange:** Injetar dados com `Whse_A` (250 un) e `Whse_B` (250 un).
  - **Act:** Executar `BasicMetricsService.get_top_locations_by_volume(limit=2)`.
  - **Assert:** Retorna lista com 2 localidades e volume primário de 250.0.
  - **Priority:** P1

- [APPROVED] [TEST001-11] [Type: Unit] **test_get_total_sales_in_period**
  - **Target:** `tests/unit/test_basic_metrics_service.py` → `test_get_total_sales_in_period()`
  - **Scenario:** Consolidar totais gerais e aplicar filtros de intervalo temporal (`start_date`, `end_date`).
  - **Arrange:** Injetar registros em Janeiro e Fevereiro de 2023.
  - **Act:** Executar cálculo total e cálculo restrito a `2023-01-01` até `2023-01-31`.
  - **Assert:** Total geral = 500.0 un (R$ 5500.0); total Janeiro = 400.0 un (2 registros).
  - **Priority:** P0

- [APPROVED] [TEST001-12] [Type: Unit] **test_compare_planned_vs_actual_quantity**
  - **Target:** `tests/unit/test_basic_metrics_service.py` → `test_compare_planned_vs_actual_quantity()`
  - **Scenario:** Calcular percentual de atingimento de meta de volume e avaliar status.
  - **Arrange:** Planejado total = 600 un, Realizado total = 500 un.
  - **Act:** Executar `BasicMetricsService.compare_planned_vs_actual_quantity()`.
  - **Assert:** Diferença = -100 un, atingimento = 83.3%, status indica meta não atingida.
  - **Priority:** P0

- [APPROVED] [TEST001-13] [Type: Unit] **test_analyze_promotion_impact**
  - **Target:** `tests/unit/test_basic_metrics_service.py` → `test_analyze_promotion_impact()`
  - **Scenario:** Comparar desempenho de vendas promovidas vs não-promovidas.
  - **Arrange:** Registros contendo promoções com desconto e registros regulares a preço cheio.
  - **Act:** Executar `BasicMetricsService.analyze_promotion_impact()`.
  - **Assert:** Contagens corretas, preço médio com desconto = R$ 8.0, desconto médio = 20.0%.
  - **Priority:** P1

---

### Task 004 — [Domain-Service]: Lógicas Puras de Métricas Complexas

- [APPROVED] [TEST001-14] [Type: Unit] **test_analyze_service_level_bottlenecks**
  - **Target:** `tests/unit/test_advanced_metrics_service.py` → `test_analyze_service_level_bottlenecks()`
  - **Scenario:** Identificar a localidade com o menor SLA (Service Level) médio.
  - **Arrange:** Dados com `Whse_A` (médias 0.985) e `Whse_B` (médias 0.825).
  - **Act:** Executar `AdvancedMetricsService.analyze_service_level_bottlenecks()`.
  - **Assert:** Pior localidade identificada como `Whse_B` com SLA = 0.825.
  - **Priority:** P0

- [APPROVED] [TEST001-15] [Type: Unit] **test_calculate_revenue_deficit**
  - **Target:** `tests/unit/test_advanced_metrics_service.py` → `test_calculate_revenue_deficit()`
  - **Scenario:** Mensurar perda financeira entre faturamento planejado e faturamento real.
  - **Arrange:** Receita planejada = R$ 70.000,00 e receita realizada = R$ 55.600,00.
  - **Act:** Executar `AdvancedMetricsService.calculate_revenue_deficit()`.
  - **Assert:** Déficit apurado = R$ 14.400,00 e flag `has_deficit=True`.
  - **Priority:** P0

- [APPROVED] [TEST001-16] [Type: Unit] **test_calculate_average_discount**
  - **Target:** `tests/unit/test_advanced_metrics_service.py` → `test_calculate_average_discount()`
  - **Scenario:** Computar desconto percentual médio ponderado global e quebras por tipo de promoção.
  - **Arrange:** Registros com descontos pontuais ("Promo_Flash").
  - **Act:** Executar `AdvancedMetricsService.calculate_average_discount()`.
  - **Assert:** Média global calculada em 7.5% e presença de "Promo_Flash" no dicionário detalhado.
  - **Priority:** P1

- [APPROVED] [TEST001-17] [Type: Unit] **test_identify_sales_seasonality**
  - **Target:** `tests/unit/test_advanced_metrics_service.py` → `test_identify_sales_seasonality()`
  - **Scenario:** Agrupar volumes por mês (YYYY-MM) para detectar mês de pico e menor volume.
  - **Arrange:** Vendas distribuídas entre Janeiro (300 un), Fevereiro (100 un) e Março (60 un) de 2023.
  - **Act:** Executar `AdvancedMetricsService.identify_sales_seasonality()`.
  - **Assert:** Mês de pico = `2023-01` (300 un) e menor mês = `2023-03` (60 un).
  - **Priority:** P1

- [APPROVED] [TEST001-18] [Type: Unit] **test_calculate_price_elasticity**
  - **Target:** `tests/unit/test_advanced_metrics_service.py` → `test_calculate_price_elasticity()`
  - **Scenario:** Avaliar sensibilidade de demanda em relação a variações de preço planejado vs real.
  - **Arrange:** Vendas com redução de preço e aumento de volume.
  - **Act:** Executar `AdvancedMetricsService.calculate_price_elasticity()`.
  - **Assert:** Coeficiente elástico (< 0) e classificação "Elástica" ou "Inelástica".
  - **Priority:** P1

---

### Task 005, Task 006 & Task 007 — [Ports & UseCase]: Orquestração de Aplicação

- [APPROVED] [TEST001-19] [Type: Unit] **test_sales_metrics_service_delegation_to_ports**
  - **Target:** `tests/unit/test_sales_metrics_service.py` → `test_get_top_selling_product()`, `test_get_total_sales_in_period()`, etc.
  - **Scenario:** Garantir que o serviço de aplicação invoca o `SalesDataPort` e orquestra os cálculos de domínio.
  - **Arrange:** Mock do `SalesDataPort` retornando lista de `SaleRecord`.
  - **Act:** Chamar cada método do `SalesMetricsApplicationService`.
  - **Assert:** `mock_sales_port.get_all_sales` é acionado e os DTOs de resultado são retornados intactos.
  - **Priority:** P0

- [APPROVED] [TEST001-20] [Type: Unit] **test_execute_custom_query_port_delegation**
  - **Target:** `tests/unit/test_sales_metrics_service.py` → `test_execute_custom_query()`
  - **Scenario:** Verificar repasse de query raw segura para o método `execute_read_only_query` da porta.
  - **Arrange:** Mock do `SalesDataPort` configurado para retornar `[{"col1": "val1", "count": 42}]`.
  - **Act:** Executar `application_service.execute_custom_query(sql)`.
  - **Assert:** `mock_sales_port.execute_read_only_query.assert_called_once_with(sql)` e retorno idêntico.
  - **Priority:** P0

---

### Task 008 — [Adapter-Persistence]: DuckDB In-Memory & Leitura de CSV

- [APPROVED] [TEST001-21] [Type: Unit] **test_duckdb_sales_adapter_initialization**
  - **Target:** `tests/unit/test_duckdb_sales_adapter.py` → `test_duckdb_sales_adapter_initialization()`
  - **Scenario:** Carregar CSV delimitado por `;` com formato de data brasileiro (`DD/MM/YYYY`) para DuckDB.
  - **Arrange:** Criar CSV temporário com registros e instanciar `DuckDbSalesAdapter(db_path=":memory:")`.
  - **Act:** Executar `adapter.get_all_sales()`.
  - **Assert:** 3 registros convertidos para `SaleRecord`, com tipagem correta (`date(2023, 1, 3)`, float para preços/quantidades).
  - **Priority:** P0

- [APPROVED] [TEST001-22] [Type: Unit] **test_duckdb_sales_adapter_get_sales_by_filter**
  - **Target:** `tests/unit/test_duckdb_sales_adapter.py` → `test_duckdb_sales_adapter_get_sales_by_filter()`
  - **Scenario:** Filtragem dinâmica via SQL por produto, local e faixa temporal.
  - **Arrange:** Instância de `DuckDbSalesAdapter` com dados populados.
  - **Act:** Chamar `get_sales_by_filter` por `product_id`, por `local` e por intervalo `start_date`/`end_date`.
  - **Assert:** Registros retornados obedecem rigorosamente aos filtros aplicados.
  - **Priority:** P1

- [APPROVED] [TEST001-23] [Type: Unit] **test_duckdb_sales_adapter_execute_read_only_query**
  - **Target:** `tests/unit/test_duckdb_sales_adapter.py` → `test_duckdb_sales_adapter_execute_read_only_query()`
  - **Scenario:** Executar consultas analíticas customizadas agregadas sobre a tabela `sales_data`.
  - **Arrange:** Consulta `SELECT local, SUM(actual_quantity) AS total_qty FROM sales_data GROUP BY local`.
  - **Act:** Executar `adapter.execute_read_only_query(query)`.
  - **Assert:** Lista de dicionários com resultados esperados (`Whse_A: 120.0`, `Whse_B: 340.0`).
  - **Priority:** P0

- [APPROVED] [TEST001-24] [Type: Unit] **test_duckdb_sales_adapter_missing_csv**
  - **Target:** `tests/unit/test_duckdb_sales_adapter.py` → `test_duckdb_sales_adapter_missing_csv()`
  - **Scenario:** Tratamento de resiliência caso o caminho do arquivo CSV não seja encontrado.
  - **Arrange:** Instanciar adaptador com `dataset_path="non_existent_file.csv"`.
  - **Act:** Executar `adapter.get_all_sales()`.
  - **Assert:** Retorna lista vazia `[]` sem derrubar a aplicação.
  - **Priority:** P2

---

### Task 009 — [Adapter-LLM]: LangChain Domain Tools

- [APPROVED] [TEST001-25] [Type: Unit] **test_create_domain_tools_count**
  - **Target:** `tests/unit/test_domain_tools.py` → `test_create_domain_tools_count()`
  - **Scenario:** Validar registro das 10 ferramentas de domínio com o decorador `@tool`.
  - **Arrange:** Mock de `SalesAnalysisUseCase`.
  - **Act:** Executar `create_domain_tools(mock_sales_usecase)`.
  - **Assert:** Exatamente 10 ferramentas instanciadas com os nomes mapeados na especificação.
  - **Priority:** P0

- [APPROVED] [TEST001-26] [Type: Unit] **test_domain_tools_invocation_and_formatting**
  - **Target:** `tests/unit/test_domain_tools.py` → `test_tool_get_top_selling_product()`, etc.
  - **Scenario:** Validar invocação de cada tool, passagem de parâmetros e conversão do DTO para string legível.
  - **Arrange:** Tools instanciadas com mock de use case.
  - **Act:** Invocar `.invoke(args)` em cada uma das 10 ferramentas.
  - **Assert:** UseCase correspondente é chamado e o retorno contém os dados esperados em formato string.
  - **Priority:** P0

---

### Task 010 — [Adapter-LLM]: Secured SQL Query Fallback & Observabilidade

- [APPROVED] [TEST001-27] [Type: Unit] **test_secured_sql_tool_valid_select**
  - **Target:** `tests/unit/test_sql_fallback_tool.py` → `test_secured_sql_tool_valid_select()`
  - **Scenario:** Permitir consultas `SELECT` legítimas e registrar log de observabilidade `[MISSING_TOOL]`.
  - **Arrange:** Mock de `SalesAnalysisUseCase`, query `SELECT local, SUM(actual_quantity) FROM sales_data GROUP BY local`.
  - **Act:** Invocar ferramenta com captura de logs `caplog`.
  - **Assert:** UseCase executa consulta, dados retornam e `[MISSING_TOOL]` consta no log.
  - **Priority:** P0

- [APPROVED] [TEST001-28] [Type: Unit] **test_secured_sql_tool_blocks_dml_ddl**
  - **Target:** `tests/unit/test_sql_fallback_tool.py` → `test_secured_sql_tool_blocks_dml_ddl()`
  - **Scenario:** Bloquear estritamente comandos DML/DDL (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ATTACH`, `COPY`, `ALTER`, `CREATE`, `TRUNCATE`, multi-statements).
  - **Arrange:** Lista de queries proibidas parametrizadas.
  - **Act:** Invocar `sql_fallback_tool.invoke({"query": forbidden_query})`.
  - **Assert:** UseCase **não** é chamado (`execute_custom_query.assert_not_called()`) e mensagem de violação de segurança é retornada.
  - **Priority:** P0

---

### Task 011 — [Adapter-External]: LLM Factory Agnóstica

- [APPROVED] [TEST001-29] [Type: Unit] **test_llm_factory_default_environment**
  - **Target:** `tests/unit/test_llm_factory.py` → `test_llm_factory_default_environment()`
  - **Scenario:** Criar modelo de linguagem com base nas variáveis de ambiente (`LLM_PROVIDER`, `MODEL_NAME`, `TEMPERATURE`).
  - **Arrange:** Configurar variáveis de ambiente com `monkeypatch` e mockar `init_chat_model`.
  - **Act:** Executar `LLMFactory.create_llm()`.
  - **Assert:** `init_chat_model` chamado com os parâmetros do `.env`.
  - **Priority:** P0

- [APPROVED] [TEST001-30] [Type: Unit] **test_llm_factory_google_alias_normalization**
  - **Target:** `tests/unit/test_llm_factory.py` → `test_llm_factory_google_alias_normalization()`
  - **Scenario:** Normalizar aliases "google" ou "gemini" para o provedor oficial "google_genai".
  - **Arrange:** Mockar `init_chat_model`.
  - **Act:** Invocar `LLMFactory.create_llm(provider="google", model_name="gemini-1.5-flash")`.
  - **Assert:** `model_provider="google_genai"` é repassado ao inicializador do LangChain.
  - **Priority:** P1

---

### Task 012 — [Adapter-Web/CLI]: Orquestrador do Agente e Interface CLI

- [APPROVED] [TEST001-31] [Type: Unit] **test_system_prompt_contains_critical_sections**
  - **Target:** `tests/unit/test_sales_agent.py` → `test_system_prompt_contains_critical_sections()`
  - **Scenario:** Garantir que o System Prompt inclui o Dicionário de Dados exato do `sales_data` e regras de priorização de ferramentas.
  - **Arrange:** Carregar `SYSTEM_PROMPT`.
  - **Act:** Verificar a presença de campos como `product_id`, `service_level`, `sales_data`, `secured_sql_query`.
  - **Assert:** Todas as diretrizes críticas e metadados de colunas estão presentes.
  - **Priority:** P1

- [APPROVED] [TEST001-32] [Type: Unit] **test_sales_agent_ask_execution**
  - **Target:** `tests/unit/test_sales_agent.py` → `test_sales_agent_ask()`
  - **Scenario:** Executar método `.ask()` do `SalesAgent` e retornar a saída final gerada pelo `AgentExecutor`.
  - **Arrange:** Mock de `AgentExecutor` com resposta simulada.
  - **Act:** Invocar `agent.ask("Qual o produto mais vendido?")`.
  - **Assert:** Retorna a resposta esperada e invoca o executor uma vez.
  - **Priority:** P0

- [APPROVED] [TEST001-33] [Type: Unit] **test_cli_main_interaction_and_exit_flow**
  - **Target:** `tests/unit/test_cli_main.py` → `test_cli_main_exit_flow()`, `test_cli_main_interaction_flow()`
  - **Scenario:** Validar loop de chat do CLI tratando perguntas do usuário e comandos de encerramento ("sair", "exit").
  - **Arrange:** Mockar `bootstrap_agent` e simular entradas do usuário com `builtins.input`.
  - **Act:** Executar `main()`.
  - **Assert:** Respostas são impressas no console e o loop encerra graciosamente no comando de saída.
  - **Priority:** P1

---

### Task 013 — [Test-Integration]: Fluxos End-to-End e Fallback

- [APPROVED] [TEST001-34] [Type: Integration] **test_e2e_domain_tools_flows**
  - **Target:** `tests/integration/test_agent_integration.py` → `test_e2e_top_selling_product_flow()`, `test_e2e_top_locations_by_volume_flow()`, `test_e2e_planned_vs_actual_flow()`, `test_e2e_service_level_bottleneck_flow()`, `test_e2e_promotion_impact_flow()`, `test_e2e_revenue_deficit_flow()`
  - **Scenario:** Executar fluxo ponta a ponta: Pergunta do Usuário → FakeToolCallingChatModel aciona Tool de Domínio → DuckDB lê CSV real → Domain Service calcula métrica → Agente sintetiza resposta.
  - **Arrange:** Dataset CSV de teste integrado com 5 registros e stack hexagonal real instanciada.
  - **Act:** Executar `agent.ask(pergunta)` para cada fluxo de negócio.
  - **Assert:** A resposta final contém as métricas exatas apuradas pelo DuckDB e pelos Domain Services.
  - **Priority:** P0

- [APPROVED] [TEST001-35] [Type: Integration] **test_e2e_sql_fallback_and_missing_tool_log**
  - **Target:** `tests/integration/test_agent_integration.py` → `test_e2e_sql_fallback_flow_emits_missing_tool_log()`
  - **Scenario:** Validar acionamento da `secured_sql_query` para perguntas ad-hoc e emissão do log `[MISSING_TOOL]`.
  - **Arrange:** Pergunta complexa sobre média de SLA por armazém, modelo fake acionando tool SQL.
  - **Act:** Executar `agent.ask(...)` com captura de logs `caplog`.
  - **Assert:** Resposta sintetizada com sucesso e log `[MISSING_TOOL]` registrado na observabilidade.
  - **Priority:** P0

- [APPROVED] [TEST001-36] [Type: Integration] **test_e2e_sql_fallback_security_rejection**
  - **Target:** `tests/integration/test_agent_integration.py` → `test_e2e_sql_fallback_security_rejection()`
  - **Scenario:** Rejeição de tentativa de deleção de dados via query maliciosa no fluxo integrado, garantindo que o banco de dados DuckDB permaneça intacto.
  - **Arrange:** Modelo simulado tentando executar `DELETE FROM sales_data`.
  - **Act:** Executar `agent.ask("Remova as vendas...")` e consultar `duckdb_adapter.get_all_sales()`.
  - **Assert:** Resposta informa rejeição de segurança e contagem de registros no DuckDB permanece em 5 (sem mutação).
  - **Priority:** P0

- [APPROVED] [TEST001-37] [Type: Integration] **test_e2e_bootstrap_agent_flow**
  - **Target:** `tests/integration/test_agent_integration.py` → `test_e2e_bootstrap_agent_flow()`
  - **Scenario:** Validar inicialização completa do ecossistema a partir do método `bootstrap_agent()` com dataset de teste.
  - **Arrange:** Variáveis de ambiente configuradas e mock de `init_chat_model`.
  - **Act:** Chamar `bootstrap_agent(dataset_path=...)` e invocar pergunta.
  - **Assert:** Agente é instanciado como instância de `SalesAgent` e responde adequadamente.
  - **Priority:** P0

---

### Task 014 — [Config]: Empacotamento Docker e Documentação

- [APPROVED] [TEST001-38] [Type: Unit] **test_dockerfile_and_readme_readiness**
  - **Target:** `tests/unit/test_scaffolding.py` / Documentação
  - **Scenario:** Validar integridade dos artefatos de entrega e empacotamento.
  - **Arrange:** Verificar arquivos `Dockerfile` e `README.md`.
  - **Act:** Inspecionar presença de instruções de execução e configuração de contêiner.
  - **Assert:** Arquivos existem e contêm especificações válidas para montagem da imagem Docker e execução do CLI.
  - **Priority:** P2
