<!-- markdownlint-disable MD013 -->
# TEST011-dynamic-data-profiling — Test Coverage Specification

> **Source Task:** [T011-dynamic-data-profiling.md](../architecture/T011-dynamic-data-profiling.md)  
> **PRD Reference:** [R011-dynamic-data-profiling.md](../business-requirements/R011-dynamic-data-profiling.md)

## Coverage Overview

Esta especificação estabelece o plano forense e a matriz de cobertura de testes para a funcionalidade de **Perfilamento Dinâmico de Dados e Injeção de Contexto** (`T011-dynamic-data-profiling.md` / `R011-dynamic-data-profiling.md`). O objetivo central é assegurar que o Agente de Análise de Vendas descubra metadados empíricos em tempo de inicialização (limites temporais, contagem distinta de entidades, representações literais de pseudo-nulos como `'None'` e colunas invariantes), sintetizando essas descobertas em um bloco `### DYNAMIC DATA INSIGHTS:` injetado no `SYSTEM_PROMPT` sem violar a imutabilidade dos dados brutos (BR01).

- **Status Geral de Cobertura:** 100% de cobertura lógica, contratos de portas, adaptadores de persistência, ciclo de vida do agente e cenários de integração mapeados para todas as 5 tasks da especificação T011.
- **Pirâmide de Testes:**
  - **Unitários (Modelos de Domínio):** Validação dos Value Objects `DatasetProfile` e `DataInsights`, teste de imutabilidade (`frozen=True`), serialização determinística do bloco Markdown, formatação de limites de data (`DD/MM/YYYY`), ordenação estável de dicionários e tratamento de múltiplos valores sentinela.
  - **Unitários (Contrato de Porta):** Verificação da interface abstrata `SalesDataPort.profile_dataset() -> DatasetProfile`.
  - **Unitários (Adaptador DuckDB):** Validação da execução de consultas analíticas `SELECT`, profiling de agregados temporais e cardinalidade, detecção de sentinelas em colunas de texto (`promotion_type`), detecção de colunas constantes (`service_level`), validação do cache em memória e tratamento resiliente de falhas/exceções sem interrupção do boot.
  - **Unitários (Orquestração do Agente):** Verificação do utilitário `build_system_prompt`, injeção do bloco de insights no construtor do `SalesAgent`, exposição da propriedade `system_prompt` e orquestração do `bootstrap_agent`.
  - **Integração / E2E:** Validação de ponta a ponta com simulação de LLM (`FakeProfilingChatModel`), verificação de geração de consultas SQL com igualdade estrita (`WHERE promotion_type = 'None'`) para evitar alucinações de 0 vendas, e resiliência de boot em caso de banco de dados ausente ou indisponível.

---

## Test Checklist

### Task 001 — [Domain-Model]: Create DatasetProfile and DataInsights models

- [COMPLETED] [TEST011-01] [Type: Unit] **test_dataset_profile_empty_markdown_generation**
  - **Target:** `src/domain/model/dataset_profile.py` → `DatasetProfile.to_markdown_block()`
  - **Scenario:** Validar que um perfil recém-instanciado ou com `total_records == 0` gera uma string vazia, evitando injeção de bloco inútil no prompt.
  - **Arrange:** Instanciar `DatasetProfile()` com valores padrão.
  - **Act:** Invocar `profile.to_markdown_block()`.
  - **Assert:** O retorno é exatamente uma string vazia `""`.
  - **Priority:** P0

- [COMPLETED] [TEST011-02] [Type: Unit] **test_dataset_profile_full_markdown_generation**
  - **Target:** `src/domain/model/dataset_profile.py` → `DatasetProfile.to_markdown_block()`
  - **Scenario:** Validar a formatação completa do bloco Markdown com contagem formatada, período temporal, cardinalidade de produtos/locais, representação sentinela de nulos e colunas constantes.
  - **Arrange:** Instanciar `DatasetProfile(total_records=1000, min_date="01/01/2024", max_date="31/12/2024", distinct_products=50, distinct_locations=5, null_representations={"promotion_type": "None"}, constant_columns={"service_level": 0.95})`.
  - **Act:** Invocar `profile.to_markdown_block()`.
  - **Assert:** O texto gerado contém o cabeçalho `### DYNAMIC DATA INSIGHTS:`, `Total de registros no dataset: 1,000`, período temporal, produtos catalogados, `WHERE promotion_type = 'None'` e indicação da coluna constante `service_level`.
  - **Priority:** P0

- [COMPLETED] [TEST011-03] [Type: Unit] **test_dataset_profile_multiple_sentinels_formatting**
  - **Target:** `src/domain/model/dataset_profile.py` → `DatasetProfile.to_markdown_block()`
  - **Scenario:** Validar que uma lista de múltiplos valores sentinela (ex: `["None", "N/A"]`) é formatada corretamente entre aspas e separada por vírgulas.
  - **Arrange:** Instanciar `DatasetProfile(total_records=500, null_representations={"promotion_type": ["None", "N/A"]})`.
  - **Act:** Invocar `profile.to_markdown_block()`.
  - **Assert:** O bloco gerado contém `"'None', 'N/A'"`.
  - **Priority:** P1

- [COMPLETED] [TEST011-04] [Type: Unit] **test_data_insights_and_dataset_profile_immutability**
  - **Target:** `src/domain/model/dataset_profile.py` → `DataInsights` e `DatasetProfile`
  - **Scenario:** Validar que os modelos de perfilamento são Value Objects imutáveis (`frozen=True`).
  - **Arrange:** Instanciar `profile = DatasetProfile(total_records=100)` e `insights = DataInsights(constant_columns={"k": 1})`.
  - **Act:** Tentar alterar atributos em tempo de execução (ex: `profile.total_records = 200`).
  - **Assert:** Lança `FrozenInstanceError` (ou `dataclasses.FrozenInstanceError`).
  - **Priority:** P1

---

### Task 002 — [Port-Out]: Update SalesDataPort with profile_dataset interface

- [COMPLETED] [TEST011-05] [Type: Unit] **test_sales_data_port_profile_dataset_abstract_method**
  - **Target:** `src/application/port/outbound/sales_data_port.py` → `SalesDataPort.profile_dataset`
  - **Scenario:** Validar que `profile_dataset` é um método abstrato obrigatório na interface `SalesDataPort`.
  - **Arrange:** Definir classe de teste derivada de `SalesDataPort` sem implementar `profile_dataset`.
  - **Act:** Tentar instanciar a classe incompleta.
  - **Assert:** Lança `TypeError` indicando que o método abstrato `profile_dataset` não foi implementado.
  - **Priority:** P0

---

### Task 003 — [Adapter-Persistence]: Implement DuckDB DatasetProfiler logic

- [COMPLETED] [TEST011-06] [Type: Unit] **test_duckdb_sales_adapter_profile_dataset_extraction**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter.profile_dataset()`
  - **Scenario:** Validar que a consulta de profiling extrai estatísticas globais, limites de data em formato brasileiro, contagens distintas, valores sentinela e colunas invariantes a partir do CSV.
  - **Arrange:** Criar arquivo CSV temporário com 3 registros contendo datas, sentinela `'None'` em `promotion_type` e armazéns variados. Instanciar `DuckDbSalesAdapter`.
  - **Act:** Executar `adapter.profile_dataset()`.
  - **Assert:** `total_records == 3`, `distinct_products == 2`, `distinct_locations == 2`, `min_date == "03/01/2023"`, `max_date == "20/03/2023"`.
  - **Priority:** P0

- [COMPLETED] [TEST011-07] [Type: Unit] **test_duckdb_sales_adapter_profile_dataset_caching**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter.profile_dataset()`
  - **Scenario:** Validar que chamadas subsequentes a `profile_dataset()` retornam a mesma instância em cache sem re-executar queries no DuckDB.
  - **Arrange:** Instanciar `DuckDbSalesAdapter` com CSV de teste.
  - **Act:** Executar `profile1 = adapter.profile_dataset()` e `profile2 = adapter.profile_dataset()`.
  - **Assert:** `profile1 is profile2` (mesma referência em memória).
  - **Priority:** P1

- [COMPLETED] [TEST011-08] [Type: Unit] **test_duckdb_sales_adapter_profile_dataset_missing_csv_fallback**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter.profile_dataset()`
  - **Scenario:** Validar que se o arquivo CSV não existir e o esquema estiver vazio, o adaptador retorna um `DatasetProfile` vazio com `total_records == 0`.
  - **Arrange:** Instanciar `DuckDbSalesAdapter(dataset_path="non_existent.csv")`.
  - **Act:** Executar `adapter.profile_dataset()`.
  - **Assert:** `profile.total_records == 0` e `profile.to_markdown_block() == ""`.
  - **Priority:** P1

- [COMPLETED] [TEST011-09] [Type: Unit] **test_duckdb_sales_adapter_profile_dataset_exception_graceful_handling**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter.profile_dataset()`
  - **Scenario:** Validar que falhas inesperadas na execução SQL do profiling são capturadas graciosamente, emitindo log de warning e retornando `DatasetProfile()` vazio para evitar crash no boot.
  - **Arrange:** Instanciar `DuckDbSalesAdapter` e simular falha na conexão DuckDB via monkeypatch no método `execute`.
  - **Act:** Executar `adapter.profile_dataset()`.
  - **Assert:** Nenhuma exceção é propagada e `profile.total_records == 0`.
  - **Priority:** P0

- [COMPLETED] [TEST011-10] [Type: Unit] **test_duckdb_sales_adapter_profile_dataset_immutability**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter.profile_dataset()`
  - **Scenario:** Validar que a rotina de profiling é estritamente read-only (BR01 / ADR-01) e não altera os registros da tabela `sales_data`.
  - **Arrange:** Instanciar `DuckDbSalesAdapter` com CSV de teste e verificar a quantidade e conteúdo inicial dos registros.
  - **Act:** Executar `adapter.profile_dataset()`.
  - **Assert:** `adapter.get_sales_by_filter()` retorna exatamente os mesmos registros sem modificações de esquema ou mutações DML.
  - **Priority:** P0

---

### Task 004 — [Adapter-Web]: Update Agent Factory to inject Dynamic Insights block

- [COMPLETED] [TEST011-11] [Type: Unit] **test_build_system_prompt_without_profile_or_empty**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `build_system_prompt()`
  - **Scenario:** Validar que `build_system_prompt` preserva o prompt base sem alterações quando o perfil for `None` ou vazio (`DatasetProfile()`).
  - **Arrange:** Preparar string base de prompt.
  - **Act:** Invocar `build_system_prompt("BASE")` e `build_system_prompt("BASE", DatasetProfile())`.
  - **Assert:** Em ambos os casos, o retorno é idêntico a `"BASE"`.
  - **Priority:** P0

- [COMPLETED] [TEST011-12] [Type: Unit] **test_build_system_prompt_with_valid_profile**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `build_system_prompt()`
  - **Scenario:** Validar que `build_system_prompt` anexa o bloco Markdown de profiling ao final do prompt base com separação de quebra de linha.
  - **Arrange:** Preparar prompt base e `DatasetProfile(total_records=5000, null_representations={"promotion_type": "None"}, constant_columns={"service_level": 0.99})`.
  - **Act:** Invocar `build_system_prompt("BASE PROMPT", profile)`.
  - **Assert:** O prompt resultante contém `"BASE PROMPT"`, `"### DYNAMIC DATA INSIGHTS:"`, `"5,000"` e `"WHERE promotion_type = 'None'"`.
  - **Priority:** P0

- [COMPLETED] [TEST011-13] [Type: Unit] **test_sales_agent_initialization_with_dataset_profile**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.__init__`
  - **Scenario:** Validar que ao instanciar o `SalesAgent` com um `dataset_profile`, o executor LangChain recebe o prompt enriquecido com os insights dinâmicos.
  - **Arrange:** Preparar mock de LLM, lista vazia de ferramentas e `DatasetProfile(total_records=100, null_representations={"promotion_type": "None"})`.
  - **Act:** Instanciar `SalesAgent(llm=mock_llm, tools=[], dataset_profile=profile)`.
  - **Assert:** `agent.system_prompt` contém `"### DYNAMIC DATA INSIGHTS:"` e `create_agent` foi invocado com `system_prompt == agent.system_prompt`.
  - **Priority:** P0

- [COMPLETED] [TEST011-14] [Type: Unit] **test_bootstrap_agent_executes_profiling_and_configures_agent**
  - **Target:** `src/adapter/inbound/cli/main.py` → `bootstrap_agent()`
  - **Scenario:** Validar que o orquestrador `bootstrap_agent` executa o profiling no adaptador de persistência e repassa o perfil ao instanciar o `SalesAgent`.
  - **Arrange:** Criar CSV de teste temporário.
  - **Act:** Executar `agent = bootstrap_agent(dataset_path=temp_csv)`.
  - **Assert:** `agent` é instanciado com sucesso e `agent.system_prompt` contém as diretrizes dinâmicas do dataset fornecido.
  - **Priority:** P0

---

### Task 005 — [Test-Integration]: Implement E2E tests for dynamic prompt adaptation

- [COMPLETED] [TEST011-15] [Type: Integration] **test_dynamic_data_profiling_prompt_injection_e2e**
  - **Target:** `tests/integration/test_dynamic_profiling.py` → `test_dynamic_data_profiling_prompt_injection`
  - **Scenario:** Validar a cadeia completa de boot através do `bootstrap_agent`, verificando que o perfil de metadados é extraído do DuckDB e refletido no `SalesAgent.system_prompt`.
  - **Arrange:** Gerar CSV de teste com `promotion_type='None'`, `service_level=0.99` e período de janeiro/2024.
  - **Act:** Invocar `bootstrap_agent(dataset_path=csv_path)`.
  - **Assert:** O prompt do agente contém `### DYNAMIC DATA INSIGHTS:`, total de registros, limites temporais e a regra `WHERE promotion_type = 'None'`.
  - **Priority:** P0

- [COMPLETED] [TEST011-16] [Type: Integration] **test_dynamic_profiling_sql_generation_with_sentinel_none**
  - **Target:** `tests/integration/test_dynamic_profiling.py` → `test_dynamic_profiling_sql_generation_e2e`
  - **Scenario:** Validar que o LLM recebe o prompt com os insights dinâmicos e gera a consulta SQL ad-hoc utilizando `WHERE promotion_type = 'None'` em vez de `IS NULL`, eliminando a alucinação de 0 vendas sem promoção.
  - **Arrange:** Configurar DuckDB e `FakeProfilingChatModel` simulando chamada para `secured_sql_query` com query contendo `promotion_type = 'None'`.
  - **Act:** Executar `agent.ask("Quantas vendas não tiveram promoção?")`.
  - **Assert:** O modelo recebeu o prompt dinâmico (`received_system_prompt`), a ferramenta SQL foi executada contra a base DuckDB retornando as 2 vendas e o agente entregou a resposta final esperada.
  - **Priority:** P0

- [COMPLETED] [TEST011-17] [Type: Integration] **test_dynamic_profiling_safe_fallback_on_corrupted_dataset**
  - **Target:** `tests/integration/test_dynamic_profiling.py` → `test_dynamic_profiling_safe_fallback_on_error`
  - **Scenario:** Validar que se o arquivo de dataset for inexistente ou estiver corrompido no momento da inicialização, o `bootstrap_agent` inicializa sem exceções e utiliza o `SYSTEM_PROMPT` padrão estático.
  - **Arrange:** Passar caminho de dataset inválido para `bootstrap_agent`.
  - **Act:** Executar `agent = bootstrap_agent(dataset_path="non_existent.csv")`.
  - **Assert:** `agent` é inicializado, `agent.system_prompt == SYSTEM_PROMPT` e nenhuma seção `### DYNAMIC DATA INSIGHTS:` é inserida.
  - **Priority:** P0

