# TEST008-segment-based-price-elasticity — Test Coverage Specification

> **Source Task:** [T008-segment-based-price-elasticity.md](../architecture/T008-segment-based-price-elasticity.md)  
> **PRD Reference:** [R008-segment-based-price-elasticity.md](../business-requirements/R008-segment-based-price-elasticity.md)  
> **Product Strategy:** [PS008-segment-based-price-elasticity.md](../product-strategy/PS008-segment-based-price-elasticity.md)

## Coverage Overview

Esta especificação define a matriz forense de cobertura de testes unitários e de integração para o cálculo de Elasticidade-Preço da Demanda baseado em segmentos de produtos (`T008-segment-based-price-elasticity.md` / `R008-segment-based-price-elasticity.md`).

A arquitetura elimina o Paradoxo de Simpson ao isolar variações de preço e volume por coorte homogênea de produto (`product_id`), suportando tanto consultas direcionadas para um único produto quanto rankings gerais de elasticidade de todo o catálogo.

- **Status Geral de Cobertura:** 100% de cobertura lógica mapeada cobrindo as 10 tasks do checklist técnico, abrangendo modelos de domínio puro, isolamento matemático em serviço de domínio, portas hexagonais, orquestração de aplicação, adapter DuckDB com pushdown SQL parametrizado, ferramentas LLM e testes de integração end-to-end.
- **Pirâmide de Testes:**
  - **Unitários (Domínio Puro):** Validação da estrutura imutável de `PriceElasticityAggregation`, `PriceElasticityResult` e `CatalogPriceElasticityOverview`.
  - **Unitários (Serviço de Domínio):** Validação do cálculo de PED (`AdvancedMetricsService`), classificações econômicas (`Elastic`, `Inelastic`, `Unit Elastic`), proteção contra divisão por zero (`Unitary / Zero price change`), dados esparsos/inconclusivos (`Inconclusive`), produtos não encontrados (`Undefined`), e ordenação por magnitude de sensibilidade a preço no catálogo.
  - **Unitários (Portas e Casos de Uso):** Verificação de contratos abstratos (`SalesDataPort`, `SalesAnalysisUseCase`) e orquestração de aplicação (`SalesMetricsApplicationService`).
  - **Unitários / Persistência (Adapter DuckDB):** Agrupamento `GROUP BY product_id` com pushdown SQL e filtragem segura contra SQL Injection via consultas parametrizadas (`WHERE product_id = ?`).
  - **Unitários / LLM (Domain Tools):** Invocação da ferramenta `calculate_price_elasticity` com e sem parâmetro `product_id`, validação de docstrings e serialização JSON.
  - **Integração (End-to-End):** Testes de integração cobrindo fluxos reais com dados sintéticos: produtos altamente elásticos, produtos inelásticos, variação nula de preço, produtos desconhecidos e ranqueamento macro do catálogo.

---

## Test Checklist

### Task 001 — [Domain-Model]: Update PriceElasticityAggregation

- [COMPLETED] [TEST008-01] [Type: Unit] **test_price_elasticity_aggregation_instantiation_with_product_id**
  - **Target:** `src/domain/model/aggregation_models.py` → `PriceElasticityAggregation`
  - **Scenario:** Validar instanciação do Value Object de agregação contendo o identificador do produto (`product_id`).
  - **Arrange:** Criar instância de `PriceElasticityAggregation(promoted_avg_price=45.0, non_promoted_avg_price=50.0, promoted_avg_qty=150.0, non_promoted_avg_qty=100.0, promoted_count=5, non_promoted_count=5, total_records=10, product_id="PROD_01")`.
  - **Act:** Acessar atributos da instância.
  - **Assert:** `agg.product_id == "PROD_01"`, `agg.promoted_avg_price == 45.0`, `agg.non_promoted_avg_price == 50.0`.
  - **Priority:** P0

- [COMPLETED] [TEST008-02] [Type: Unit] **test_price_elasticity_aggregation_immutability**
  - **Target:** `src/domain/model/aggregation_models.py` → `PriceElasticityAggregation`
  - **Scenario:** Garantir que o Value Object de agregação de elasticidade é estritamente imutável (`frozen=True`).
  - **Arrange:** Instanciar `agg = PriceElasticityAggregation(45.0, 50.0, 150.0, 100.0, 5, 5, 10, product_id="PROD_01")`.
  - **Act:** Tentar reatribuir `agg.product_id = "MUTATED"`.
  - **Assert:** Lança `FrozenInstanceError` ou `TypeError`.
  - **Priority:** P1

---

### Task 002 — [Domain-Model]: Update PriceElasticityResult

- [COMPLETED] [TEST008-03] [Type: Unit] **test_price_elasticity_result_with_product_id**
  - **Target:** `src/domain/model/metric_result.py` → `PriceElasticityResult`
  - **Scenario:** Validar criação do resultado de elasticidade com o campo `product_id` opcional e populado.
  - **Arrange:** Instanciar `PriceElasticityResult(elasticity_coefficient=-2.0, percentage_change_in_price=-10.0, percentage_change_in_quantity=20.0, demand_classification="Elastic", summary="Elastic demand", product_id="PROD_01")`.
  - **Act:** Avaliar propriedades do objeto.
  - **Assert:** `result.product_id == "PROD_01"`, `result.elasticity_coefficient == -2.0`, `result.demand_classification == "Elastic"`.
  - **Priority:** P0

- [COMPLETED] [TEST008-04] [Type: Unit] **test_price_elasticity_result_immutability**
  - **Target:** `src/domain/model/metric_result.py` → `PriceElasticityResult`
  - **Scenario:** Garantir imutabilidade do resultado de elasticidade por segmento.
  - **Arrange:** Instanciar `result = PriceElasticityResult(-2.0, -10.0, 20.0, "Elastic", "summary", "PROD_01")`.
  - **Act:** Tentar alterar `result.elasticity_coefficient = -1.0`.
  - **Assert:** Lança `FrozenInstanceError` ou `TypeError`.
  - **Priority:** P1

---

### Task 003 — [Domain-Model]: Create CatalogPriceElasticityOverview

- [COMPLETED] [TEST008-05] [Type: Unit] **test_catalog_price_elasticity_overview_instantiation**
  - **Target:** `src/domain/model/metric_result.py` → `CatalogPriceElasticityOverview`
  - **Scenario:** Validar instanciação do Value Object representando a visão macro do catálogo com listas ordenadas de produtos.
  - **Arrange:** Instanciar `elas_res = PriceElasticityResult(-2.0, -10.0, 20.0, "Elastic", "summary", "PROD_01")` e `overview = CatalogPriceElasticityOverview(total_products_evaluated=1, inconclusive_products_count=0, most_elastic_products=[elas_res], most_inelastic_products=[elas_res], summary="Overview summary")`.
  - **Act:** Inspecionar propriedades de `overview`.
  - **Assert:** `overview.total_products_evaluated == 1`, `overview.inconclusive_products_count == 0`, `len(overview.most_elastic_products) == 1`, `overview.most_elastic_products[0].product_id == "PROD_01"`.
  - **Priority:** P0

- [COMPLETED] [TEST008-06] [Type: Unit] **test_catalog_price_elasticity_overview_immutability**
  - **Target:** `src/domain/model/metric_result.py` → `CatalogPriceElasticityOverview`
  - **Scenario:** Garantir imutabilidade do overview do catálogo.
  - **Arrange:** Instanciar `overview = CatalogPriceElasticityOverview(0, 0, [], [], "empty")`.
  - **Act:** Tentar reatribuir `overview.total_products_evaluated = 5`.
  - **Assert:** Lança `FrozenInstanceError` ou `TypeError`.
  - **Priority:** P1

---

### Task 004 — [Domain-Service]: Update AdvancedMetricsService

- [COMPLETED] [TEST008-07] [Type: Unit] **test_advanced_metrics_calculate_price_elasticity_single_product_elastic**
  - **Target:** `src/domain/service/advanced_metrics_service.py` → `calculate_price_elasticity()`
  - **Scenario:** Calcular elasticidade para produto com alta resposta volumétrica a desconto (|PED| > 1.0).
  - **Arrange:** Criar `PriceElasticityAggregation(promoted_avg_price=80.0, non_promoted_avg_price=100.0, promoted_avg_qty=220.0, non_promoted_avg_qty=80.0, promoted_count=2, non_promoted_count=2, total_records=4, product_id="PROD_ELASTIC")`.
  - **Act:** Executar `service.calculate_price_elasticity([agg], target_product_id="PROD_ELASTIC")`.
  - **Assert:** `result.product_id == "PROD_ELASTIC"`, `result.elasticity_coefficient == -8.75`, `result.percentage_change_in_price == -20.0`, `result.percentage_change_in_quantity == 175.0`, `"Elastic" in result.demand_classification`.
  - **Priority:** P0

- [COMPLETED] [TEST008-08] [Type: Unit] **test_advanced_metrics_calculate_price_elasticity_single_product_inelastic**
  - **Target:** `src/domain/service/advanced_metrics_service.py` → `calculate_price_elasticity()`
  - **Scenario:** Calcular elasticidade para produto com baixa sensibilidade a preço (|PED| < 1.0).
  - **Arrange:** Criar `PriceElasticityAggregation(promoted_avg_price=90.0, non_promoted_avg_price=100.0, promoted_avg_qty=105.0, non_promoted_avg_qty=100.0, promoted_count=2, non_promoted_count=2, total_records=4, product_id="PROD_INELASTIC")`.
  - **Act:** Executar `service.calculate_price_elasticity([agg], target_product_id="PROD_INELASTIC")`.
  - **Assert:** `result.product_id == "PROD_INELASTIC"`, `result.elasticity_coefficient == -0.5`, `"Inelastic" in result.demand_classification`.
  - **Priority:** P0

- [COMPLETED] [TEST008-09] [Type: Unit] **test_advanced_metrics_calculate_price_elasticity_zero_price_delta**
  - **Target:** `src/domain/service/advanced_metrics_service.py` → `calculate_price_elasticity()`
  - **Scenario:** Garantir proteção contra divisão por zero quando o preço promocional for idêntico ao preço base (% Delta Price == 0.0).
  - **Arrange:** Criar `PriceElasticityAggregation(promoted_avg_price=100.0, non_promoted_avg_price=100.0, promoted_avg_qty=120.0, non_promoted_avg_qty=100.0, promoted_count=2, non_promoted_count=2, total_records=4, product_id="PROD_ZERO_DELTA")`.
  - **Act:** Executar `service.calculate_price_elasticity([agg], target_product_id="PROD_ZERO_DELTA")`.
  - **Assert:** `result.elasticity_coefficient == 0.0`, `result.demand_classification == "Unitary / Zero price change"`.
  - **Priority:** P0

- [COMPLETED] [TEST008-10] [Type: Unit] **test_advanced_metrics_calculate_price_elasticity_inconclusive_missing_promo**
  - **Target:** `src/domain/service/advanced_metrics_service.py` → `calculate_price_elasticity()`
  - **Scenario:** Classificar como Inconclusive quando produto não possuir coorte de vendas promocionais registradas.
  - **Arrange:** Criar `PriceElasticityAggregation(promoted_avg_price=0.0, non_promoted_avg_price=100.0, promoted_avg_qty=0.0, non_promoted_avg_qty=100.0, promoted_count=0, non_promoted_count=5, total_records=5, product_id="PROD_NO_PROMO")`.
  - **Act:** Executar `service.calculate_price_elasticity([agg], target_product_id="PROD_NO_PROMO")`.
  - **Assert:** `result.product_id == "PROD_NO_PROMO"`, `result.demand_classification == "Inconclusive"`, `"não possui histórico de promoções" in result.summary`.
  - **Priority:** P1

- [COMPLETED] [TEST008-11] [Type: Unit] **test_advanced_metrics_calculate_price_elasticity_unknown_product**
  - **Target:** `src/domain/service/advanced_metrics_service.py` → `calculate_price_elasticity()`
  - **Scenario:** Retornar classificação Undefined quando o identificador de produto solicitado não existir no conjunto de dados.
  - **Arrange:** Lista de agregações contendo `PROD_EXISTING`.
  - **Act:** Executar `service.calculate_price_elasticity(aggs, target_product_id="PROD_UNKNOWN")`.
  - **Assert:** `result.product_id == "PROD_UNKNOWN"`, `result.demand_classification == "Undefined"`, `"não encontrado" in result.summary`.
  - **Priority:** P1

- [COMPLETED] [TEST008-12] [Type: Unit] **test_advanced_metrics_calculate_price_elasticity_catalog_overview_ranking**
  - **Target:** `src/domain/service/advanced_metrics_service.py` → `calculate_price_elasticity()`
  - **Scenario:** Calcular elasticidade de múltiplos produtos do catálogo, ranquear por sensibilidade e filtrar inconclusivos do ranking.
  - **Arrange:** Lista de agregações com `PROD_HIGH_ELASTIC` (PED -8.75), `PROD_LOW_INELASTIC` (PED -0.5) e `PROD_INCONCLUSIVE` (promoted_count 0).
  - **Act:** Executar `service.calculate_price_elasticity(aggs, target_product_id=None)`.
  - **Assert:** `overview.total_products_evaluated == 3`, `overview.inconclusive_products_count == 1`, `len(overview.most_elastic_products) == 2`, `overview.most_elastic_products[0].product_id == "PROD_HIGH_ELASTIC"`, `overview.most_inelastic_products[0].product_id == "PROD_LOW_INELASTIC"`.
  - **Priority:** P0

- [COMPLETED] [TEST008-13] [Type: Unit] **test_advanced_metrics_calculate_price_elasticity_empty_catalog**
  - **Target:** `src/domain/service/advanced_metrics_service.py` → `calculate_price_elasticity()`
  - **Scenario:** Tratar entrada vazia (`None` ou lista vazia) retornando `CatalogPriceElasticityOverview` vazio sem exceções.
  - **Arrange:** Entrada `None`.
  - **Act:** Executar `service.calculate_price_elasticity(None)`.
  - **Assert:** `result.total_products_evaluated == 0`, `result.inconclusive_products_count == 0`, `result.most_elastic_products == []`.
  - **Priority:** P1

---

### Task 005 — [Port-Out]: Update SalesDataPort interface

- [COMPLETED] [TEST008-14] [Type: Unit] **test_sales_data_port_abstract_interface_contract**
  - **Target:** `src/application/port/outbound/sales_data_port.py` → `SalesDataPort.aggregate_price_elasticity`
  - **Scenario:** Validar que a interface abstrata define o método `aggregate_price_elasticity` com parâmetro `product_id: Optional[str] = None`.
  - **Arrange:** Inspecionar assinatura de método via `inspect.signature`.
  - **Act:** Obter parâmetros e tipo de retorno anotado.
  - **Assert:** Parâmetro `product_id` está presente com default `None` e retorno anotado é `List[PriceElasticityAggregation]`.
  - **Priority:** P1

---

### Task 006 — [Port-In]: Update SalesAnalysisUseCase interface

- [COMPLETED] [TEST008-15] [Type: Unit] **test_sales_analysis_usecase_abstract_interface_contract**
  - **Target:** `src/application/port/inbound/sales_analysis_usecase.py` → `SalesAnalysisUseCase.calculate_price_elasticity`
  - **Scenario:** Validar que o porto de entrada define `calculate_price_elasticity` aceitando `product_id: Optional[str] = None`.
  - **Arrange:** Inspecionar assinatura de método via `inspect.signature`.
  - **Act:** Obter parâmetros de `calculate_price_elasticity`.
  - **Assert:** Parâmetro `product_id` está presente com default `None`.
  - **Priority:** P1

---

### Task 007 — [UseCase]: Update SalesMetricsApplicationService

- [COMPLETED] [TEST008-16] [Type: Unit] **test_sales_metrics_service_calculate_price_elasticity_catalog**
  - **Target:** `src/application/service/sales_metrics_service.py` → `calculate_price_elasticity()`
  - **Scenario:** Validar orquestração de caso de uso sem `product_id` repassando `product_id=None` ao porto e serviço de domínio.
  - **Arrange:** Mock de `SalesDataPort` retornando lista com 1 agregação.
  - **Act:** Executar `application_service.calculate_price_elasticity()`.
  - **Assert:** `mock_sales_port.aggregate_price_elasticity.assert_called_with(product_id=None)` e `result.total_products_evaluated == 1`.
  - **Priority:** P0

- [COMPLETED] [TEST008-17] [Type: Unit] **test_sales_metrics_service_calculate_price_elasticity_single_product**
  - **Target:** `src/application/service/sales_metrics_service.py` → `calculate_price_elasticity()`
  - **Scenario:** Validar orquestração de caso de uso para produto específico (`product_id="PROD_01"`).
  - **Arrange:** Mock de `SalesDataPort` configurado para retornar agregação do produto `PROD_01`.
  - **Act:** Executar `application_service.calculate_price_elasticity(product_id="PROD_01")`.
  - **Assert:** `mock_sales_port.aggregate_price_elasticity.assert_called_with(product_id="PROD_01")`, `result.product_id == "PROD_01"`, `result.elasticity_coefficient != 0.0`.
  - **Priority:** P0

---

### Task 008 — [Adapter-Persistence]: Update SalesDataDuckDbAdapter query logic

- [COMPLETED] [TEST008-18] [Type: Unit] **test_duckdb_adapter_aggregate_price_elasticity_catalog_grouping**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter.aggregate_price_elasticity`
  - **Scenario:** Validar agrupamento SQL DuckDB `GROUP BY product_id` retornando uma agregação por produto no catálogo.
  - **Arrange:** Adaptador DuckDB carregado com dataset de teste sintético em memória contendo múltiplos produtos.
  - **Act:** Executar `adapter.aggregate_price_elasticity()`.
  - **Assert:** Retorna lista não vazia de `PriceElasticityAggregation`, e `any(e.product_id == "Prod_01" for e in elas_list) == True`.
  - **Priority:** P0

- [COMPLETED] [TEST008-19] [Type: Unit] **test_duckdb_adapter_aggregate_price_elasticity_parameterized_filter**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter.aggregate_price_elasticity`
  - **Scenario:** Validar filtragem parametrizada segura via `product_id="Prod_01"` sem injeção de SQL.
  - **Arrange:** Adaptador DuckDB com dataset em memória.
  - **Act:** Executar `adapter.aggregate_price_elasticity(product_id="Prod_01")`.
  - **Assert:** Retorna lista com exatamente 1 agregação correspondente ao produto `Prod_01`.
  - **Priority:** P0

---

### Task 009 — [Adapter-Web]: Update LLM domain_tools.py signature and docstrings

- [COMPLETED] [TEST008-20] [Type: Unit] **test_domain_tools_calculate_price_elasticity_catalog**
  - **Target:** `src/adapter/inbound/llm/domain_tools.py` → `calculate_price_elasticity` tool
  - **Scenario:** Invocação da ferramenta pelo agente sem parâmetros repassando `product_id=None` para o caso de uso.
  - **Arrange:** Mock do caso de uso de análise de vendas.
  - **Act:** Invocação `tools["calculate_price_elasticity"].invoke({})`.
  - **Assert:** `mock_sales_usecase.calculate_price_elasticity.assert_called_with(product_id=None)` e payload retornado contém JSON formatado.
  - **Priority:** P0

- [COMPLETED] [TEST008-21] [Type: Unit] **test_domain_tools_calculate_price_elasticity_with_product_id**
  - **Target:** `src/adapter/inbound/llm/domain_tools.py` → `calculate_price_elasticity` tool
  - **Scenario:** Invocação da ferramenta com argumento `product_id="PROD_01"` repassando o filtro para o caso de uso.
  - **Arrange:** Mock do caso de uso de análise de vendas.
  - **Act:** Invocação `tools["calculate_price_elasticity"].invoke({"product_id": "PROD_01"})`.
  - **Assert:** `mock_sales_usecase.calculate_price_elasticity.assert_called_with(product_id="PROD_01")`.
  - **Priority:** P0

---

### Task 010 — [Test-Integration]: E2E test for specific product and catalog overview

- [COMPLETED] [TEST008-22] [Type: Integration] **test_integration_specific_product_elastic**
  - **Target:** `tests/integration/test_price_elasticity.py` → `test_integration_specific_product_elastic`
  - **Scenario:** Validar pipeline integrado de cálculo de elasticidade para produto altamente elástico (`PROD_ELASTIC`).
  - **Arrange:** Dataset CSV sintético com `PROD_ELASTIC` (Preço base 100/qty 100, Preço promo 80/qty 200).
  - **Act:** Executar `sales_service.calculate_price_elasticity(product_id="PROD_ELASTIC")`.
  - **Assert:** `result.product_id == "PROD_ELASTIC"`, `result.elasticity_coefficient == -5.0`, `result.percentage_change_in_price == -20.0`, `result.percentage_change_in_quantity == 100.0`, `"Elastic" in result.demand_classification`.
  - **Priority:** P0

- [COMPLETED] [TEST008-23] [Type: Integration] **test_integration_specific_product_inelastic**
  - **Target:** `tests/integration/test_price_elasticity.py` → `test_integration_specific_product_inelastic`
  - **Scenario:** Validar pipeline integrado de cálculo de elasticidade para produto inelástico (`PROD_INELASTIC`).
  - **Arrange:** Dataset CSV sintético com `PROD_INELASTIC` (Preço base 50/qty 100, Preço promo 40/qty 110).
  - **Act:** Executar `sales_service.calculate_price_elasticity(product_id="PROD_INELASTIC")`.
  - **Assert:** `result.product_id == "PROD_INELASTIC"`, `result.elasticity_coefficient == -0.5`, `result.percentage_change_in_price == -20.0`, `result.percentage_change_in_quantity == 10.0`, `"Inelastic" in result.demand_classification`.
  - **Priority:** P0

- [COMPLETED] [TEST008-24] [Type: Integration] **test_integration_zero_price_variation**
  - **Target:** `tests/integration/test_price_elasticity.py` → `test_integration_zero_price_variation`
  - **Scenario:** Validar pipeline integrado para produto com variação zero de preço entre promoção e base (`PROD_ZERO_DELTA`).
  - **Arrange:** Dataset CSV sintético com `PROD_ZERO_DELTA` (Preço promo 60 == Preço base 60).
  - **Act:** Executar `sales_service.calculate_price_elasticity(product_id="PROD_ZERO_DELTA")`.
  - **Assert:** `result.product_id == "PROD_ZERO_DELTA"`, `result.elasticity_coefficient == 0.0`, `result.demand_classification == "Unitary / Zero price change"`.
  - **Priority:** P0

- [COMPLETED] [TEST008-25] [Type: Integration] **test_integration_unknown_product**
  - **Target:** `tests/integration/test_price_elasticity.py` → `test_integration_unknown_product`
  - **Scenario:** Validar pipeline integrado consultando produto inexistente no banco.
  - **Arrange:** Base sem o produto `PROD_UNKNOWN`.
  - **Act:** Executar `sales_service.calculate_price_elasticity(product_id="PROD_UNKNOWN")`.
  - **Assert:** `result.product_id == "PROD_UNKNOWN"`, `result.elasticity_coefficient == 0.0`, `result.demand_classification == "Undefined"`, `"não encontrado" in result.summary`.
  - **Priority:** P1

- [COMPLETED] [TEST008-26] [Type: Integration] **test_integration_catalog_overview_ranking**
  - **Target:** `tests/integration/test_price_elasticity.py` → `test_integration_catalog_overview_ranking`
  - **Scenario:** Validar visão geral macro do catálogo com múltiplos produtos, cálculo individual de PED e ranqueamento ordenado por sensibilidade.
  - **Arrange:** Dataset CSV sintético com 4 produtos (`PROD_ELASTIC`, `PROD_INELASTIC`, `PROD_ZERO_DELTA`, `PROD_NO_PROMO`).
  - **Act:** Executar `sales_service.calculate_price_elasticity()`.
  - **Assert:** `isinstance(result, CatalogPriceElasticityOverview)`, `result.total_products_evaluated == 4`, `result.inconclusive_products_count == 1`, `result.most_elastic_products[0].product_id == "PROD_ELASTIC"`.
  - **Priority:** P0
