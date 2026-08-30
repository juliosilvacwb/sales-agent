# TEST003-analytical-engine-scalability — Test Coverage Specification

> **Source Task:** [T003-analytical-engine-scalability.md](../architecture/T003-analytical-engine-scalability.md)  
> **PRD Reference:** [R003-analytical-engine-scalability.md](../business-requirements/R003-analytical-engine-scalability.md)

## Coverage Overview

Esta especificação detalha a análise forense de cobertura de testes unitários e de integração para a migração de escalabilidade do motor analítico (`T003-analytical-engine-scalability.md` / `R003-analytical-engine-scalability.md`). A arquitetura migrou cálculos em memória Python para pushdown analítico OLAP nativo no DuckDB via SQL, eliminando o risco de Out-of-Memory (OOM) em datasets com 50M+ registros.

- **Status Geral de Cobertura:** 100% de cobertura lógica e branch coverage mapeada para todas as 8 tasks da especificação T003.
- **Pirâmide de Testes:**
  - **Unitários (Domínio Puro):** Testes dos modelos de agregação e serviços de métricas básicas/avançadas desacoplados de infraestrutura.
  - **Unitários (Portas e Casos de Uso):** Testes de orquestração do `SalesMetricsApplicationService` com mocks isolados da `SalesDataPort`.
  - **Unitários (Persistência DuckDB):** Testes de execução das 10 queries SQL de pushdown no `DuckDbSalesAdapter` com tratamento de edge cases (ausência de dados, paths especiais, restrição de acesso externo).
  - **Integração (End-to-End):** Testes de paridade matemática e funcional garantindo que o pushdown SQL produza resultados 100% equivalentes às regras de negócio originais.

---

## Test Checklist

### Task 001 — [Domain-Model]: Criar estruturas de dados agregadas

- [COMPLETED] [TEST003-01] [Type: Unit] **test_aggregation_models_instantiation**
  - **Target:** `tests/unit/test_domain_models.py` → `test_aggregation_models_instantiation()`
  - **Scenario:** Validar a instanciação e integridade de todos os 10 Value Objects de agregação em `src/domain/model/aggregation_models.py`.
  - **Arrange:** Preparar instâncias de `ProductAggregation`, `LocationSalesAggregation`, `TotalSalesAggregation`, `PlannedVsActualAggregation`, `PromotionImpactAggregation`, `ServiceLevelBottleneckAggregation`, `RevenueDeficitAggregation`, `AverageDiscountAggregation`, `SeasonalityAggregation` e `PriceElasticityAggregation`.
  - **Act:** Acessar os atributos de cada modelo instanciado.
  - **Assert:** Todos os campos preservam os tipos e valores informados sem dependências de framework.
  - **Priority:** P0

- [COMPLETED] [TEST003-02] [Type: Unit] **test_aggregation_models_immutability**
  - **Target:** `tests/unit/test_domain_models.py` → `test_aggregation_models_immutability()`
  - **Scenario:** Garantir imutabilidade (`frozen=True`) dos modelos de agregação para evitar mutações acidentais de estado no heap.
  - **Arrange:** Instanciar `ProductAggregation(product_id="P1", total_quantity=100.0, total_revenue=500.0, total_records=1)`.
  - **Act:** Tentar alterar `product.total_quantity = 200.0`.
  - **Assert:** Lança `dataclasses.FrozenInstanceError`.
  - **Priority:** P1

---

### Task 002 — [Domain-Service]: Refatorar BasicMetricsService

- [COMPLETED] [TEST003-03] [Type: Unit] **test_basic_metrics_top_selling_product**
  - **Target:** `tests/unit/test_basic_metrics_service.py` → `test_get_top_selling_product()`
  - **Scenario:** Validar cálculo do produto mais vendido a partir de `ProductAggregation`.
  - **Arrange:** Instanciar `ProductAggregation(product_id="Product_01", total_quantity=400.0, total_revenue=3500.0, total_records=2)`.
  - **Act:** Executar `BasicMetricsService.get_top_selling_product(agg)`.
  - **Assert:** Retorna `TopSellingProductResult` com `product_id == "Product_01"`, `total_quantity == 400.0` e `total_revenue == 3500.0`.
  - **Priority:** P0

- [COMPLETED] [TEST003-04] [Type: Unit] **test_basic_metrics_top_selling_product_empty**
  - **Target:** `tests/unit/test_basic_metrics_service.py` → `test_get_top_selling_product_empty()`
  - **Scenario:** Validar comportamento quando agregação for `None` ou possuir `total_records == 0`.
  - **Arrange:** Definir payload de entrada como `None`.
  - **Act:** Executar `BasicMetricsService.get_top_selling_product(None)`.
  - **Assert:** Retorna `TopSellingProductResult` com `product_id == "N/A"`, `total_quantity == 0.0` e `total_records == 0`.
  - **Priority:** P1

- [COMPLETED] [TEST003-05] [Type: Unit] **test_basic_metrics_top_locations_by_volume**
  - **Target:** `tests/unit/test_basic_metrics_service.py` → `test_get_top_locations_by_volume()`
  - **Scenario:** Validar ordenação e identificação da localização primária a partir de sequência de `LocationSalesAggregation`.
  - **Arrange:** Criar lista com agregações de `Whse_A` (250 un) e `Whse_B` (250 un).
  - **Act:** Executar `BasicMetricsService.get_top_locations_by_volume(aggregations, limit=2)`.
  - **Assert:** `len(result.top_locations) == 2`, `primary_location == "Whse_A"` e `primary_quantity == 250.0`.
  - **Priority:** P0

- [COMPLETED] [TEST003-06] [Type: Unit] **test_basic_metrics_total_sales_in_period**
  - **Target:** `tests/unit/test_basic_metrics_service.py` → `test_get_total_sales_in_period()`
  - **Scenario:** Validar totalização de volume, receita e ticket médio a partir de `TotalSalesAggregation`.
  - **Arrange:** Criar `TotalSalesAggregation(total_quantity=500.0, total_revenue=5500.0, total_records=3)`.
  - **Act:** Executar `BasicMetricsService.get_total_sales_in_period(agg)`.
  - **Assert:** `total_quantity == 500.0`, `total_revenue == 5500.0` e `average_ticket == 11.0`.
  - **Priority:** P0

- [COMPLETED] [TEST003-07] [Type: Unit] **test_basic_metrics_compare_planned_vs_actual_quantity**
  - **Target:** `tests/unit/test_basic_metrics_service.py` → `test_compare_planned_vs_actual_quantity()`
  - **Scenario:** Validar cálculo de atingimento percentual e mensagem de avaliação de metas.
  - **Arrange:** Criar `PlannedVsActualAggregation(total_planned_quantity=600.0, total_actual_quantity=500.0, total_records=3)`.
  - **Act:** Executar `BasicMetricsService.compare_planned_vs_actual_quantity(agg)`.
  - **Assert:** `difference_quantity == -100.0`, `achievement_percentage == 83.33` e `evaluation` contém "missed".
  - **Priority:** P0

- [COMPLETED] [TEST003-08] [Type: Unit] **test_basic_metrics_analyze_promotion_impact**
  - **Target:** `tests/unit/test_basic_metrics_service.py` → `test_analyze_promotion_impact()`
  - **Scenario:** Validar cálculo de volume lift e resumo de promoções a partir de `PromotionImpactAggregation`.
  - **Arrange:** Criar agregação com 1 venda promovida (250 un) e 2 não-promovidas (250 un).
  - **Act:** Executar `BasicMetricsService.analyze_promotion_impact(agg)`.
  - **Assert:** `volume_lift_percentage == 100.0`, `promoted_avg_actual_price == 8.0` e `average_discount_in_promotion == 20.0`.
  - **Priority:** P0

---

### Task 003 — [Domain-Service]: Refatorar AdvancedMetricsService

- [COMPLETED] [TEST003-09] [Type: Unit] **test_advanced_metrics_service_level_bottlenecks**
  - **Target:** `tests/unit/test_advanced_metrics_service.py` → `test_analyze_service_level_bottlenecks()`
  - **Scenario:** Identificar gargalo crítico de SLA a partir de `ServiceLevelBottleneckAggregation`.
  - **Arrange:** Criar agregação com `Whse_A: 0.985` e `Whse_B: 0.825`.
  - **Act:** Executar `AdvancedMetricsService.analyze_service_level_bottlenecks(agg)`.
  - **Assert:** `worst_location == "Whse_B"`, `worst_service_level == 0.825` e `summary` cita `Whse_B`.
  - **Priority:** P0

- [COMPLETED] [TEST003-10] [Type: Unit] **test_advanced_metrics_service_level_bottlenecks_equal_sla**
  - **Target:** `tests/unit/test_advanced_metrics_service.py` → `test_analyze_service_level_bottlenecks_equal_sla()`
  - **Scenario:** Validar cenário onde todas as localidades possuem o mesmo nível de serviço.
  - **Arrange:** Criar agregação com `Whse_A: 0.98`, `Whse_B: 0.98` e `Whse_C: 0.98`.
  - **Act:** Executar `AdvancedMetricsService.analyze_service_level_bottlenecks(agg)`.
  - **Assert:** `worst_location == "N/A"` e `summary` contém "No logistics SLA bottleneck identified".
  - **Priority:** P1

- [COMPLETED] [TEST003-11] [Type: Unit] **test_advanced_metrics_calculate_revenue_deficit**
  - **Target:** `tests/unit/test_advanced_metrics_service.py` → `test_calculate_revenue_deficit()`
  - **Scenario:** Validar detecção de déficit financeiro a partir de `RevenueDeficitAggregation`.
  - **Arrange:** Criar `RevenueDeficitAggregation(total_planned_revenue=70000.0, total_actual_revenue=55600.0, total_records=4)`.
  - **Act:** Executar `AdvancedMetricsService.calculate_revenue_deficit(agg)`.
  - **Assert:** `total_revenue_deficit == 14400.0`, `has_deficit is True` e `deficit_percentage == 20.57`.
  - **Priority:** P0

- [COMPLETED] [TEST003-12] [Type: Unit] **test_advanced_metrics_calculate_average_discount**
  - **Target:** `tests/unit/test_advanced_metrics_service.py` → `test_calculate_average_discount()`
  - **Scenario:** Validar margem média de desconto e breakdown por promoção.
  - **Arrange:** Criar `AverageDiscountAggregation` com desconto de 15.0% e detalhamento de `Promo_Flash` (20.0%) e `Promo_B2B` (10.0%).
  - **Act:** Executar `AdvancedMetricsService.calculate_average_discount(agg)`.
  - **Assert:** `overall_average_discount_percentage == 15.0`, `total_discount_value == 14400.0` e mapa de promoções preenchido.
  - **Priority:** P0

- [COMPLETED] [TEST003-13] [Type: Unit] **test_advanced_metrics_identify_sales_seasonality**
  - **Target:** `tests/unit/test_advanced_metrics_service.py` → `test_identify_sales_seasonality()`
  - **Scenario:** Validar identificação de mês de pico e mês de vale a partir de `SeasonalityAggregation`.
  - **Arrange:** Criar agregação com volumes mensais para `2023-01` (300 un), `2023-02` (100 un) e `2023-03` (60 un).
  - **Act:** Executar `AdvancedMetricsService.identify_sales_seasonality(agg)`.
  - **Assert:** `peak_month == "2023-01"`, `peak_volume == 300.0`, `lowest_month == "2023-03"` e `lowest_volume == 60.0`.
  - **Priority:** P0

- [COMPLETED] [TEST003-14] [Type: Unit] **test_advanced_metrics_calculate_price_elasticity**
  - **Target:** `tests/unit/test_advanced_metrics_service.py` → `test_calculate_price_elasticity()`
  - **Scenario:** Validar cálculo do coeficiente de elasticidade-preço da demanda (PED).
  - **Arrange:** Criar `PriceElasticityAggregation(promoted_avg_price=80.0, non_promoted_avg_price=100.0, promoted_avg_qty=220.0, non_promoted_avg_qty=80.0, promoted_count=2, non_promoted_count=2, total_records=4)`.
  - **Act:** Executar `AdvancedMetricsService.calculate_price_elasticity(agg)`.
  - **Assert:** `elasticity_coefficient == -8.75`, `percentage_change_in_price == -20.0`, `percentage_change_in_quantity == 175.0` e `demand_classification` contém "Elastic".
  - **Priority:** P0

---

### Task 004 & Task 005 — [Port-Out & UseCase]: SalesDataPort & SalesMetricsApplicationService

- [COMPLETED] [TEST003-15] [Type: Unit] **test_usecase_orchestration_top_selling_product**
  - **Target:** `tests/unit/test_sales_metrics_service.py` → `test_get_top_selling_product()`
  - **Scenario:** Garantir que o caso de uso invoca `aggregate_top_selling_product` da porta e repassa ao serviço de domínio.
  - **Arrange:** Mockar `SalesDataPort.aggregate_top_selling_product` retornando `ProductAggregation("Prod_B", 180.0, 18000.0, 1)`.
  - **Act:** Executar `SalesMetricsApplicationService.get_top_selling_product()`.
  - **Assert:** `mock_sales_port.aggregate_top_selling_product.assert_called_once()` e `result.product_id == "Prod_B"`.
  - **Priority:** P0

- [COMPLETED] [TEST003-16] [Type: Unit] **test_usecase_orchestration_all_analytical_methods**
  - **Target:** `tests/unit/test_sales_metrics_service.py` → `test_get_total_sales_in_period()`, `test_compare_planned_vs_actual_quantity()`, etc.
  - **Scenario:** Garantir que os 10 métodos de caso de uso não invocam `get_all_sales()` e utilizam exclusivamente métodos agregados da porta.
  - **Arrange:** Configurar `MagicMock(spec=SalesDataPort)` com retornos para todos os 10 métodos de agregação.
  - **Act:** Invocar sequencialmente cada método no `SalesMetricsApplicationService`.
  - **Assert:** Cada método correspondente na porta é acionado uma vez; nenhuma tentativa de carregar registros brutos ocorre.
  - **Priority:** P0

---

### Task 006 & Task 007 — [Adapter-Persistence]: DuckDbSalesAdapter SQL Pushdown & get_all_sales Removal

- [COMPLETED] [TEST003-17] [Type: Unit] **test_duckdb_adapter_sql_pushdown_aggregations**
  - **Target:** `tests/unit/test_duckdb_sales_adapter.py` → `test_duckdb_sales_adapter_aggregations()`
  - **Scenario:** Validar execução nativa das 10 queries SQL de agregação diretamente na tabela DuckDB in-memory.
  - **Arrange:** Inicializar `DuckDbSalesAdapter` com CSV temporário contendo vendas multi-armazém.
  - **Act:** Executar `aggregate_top_selling_product()`, `aggregate_top_locations()`, `aggregate_total_sales()`, `aggregate_planned_vs_actual()`, `aggregate_promotion_impact()`, `aggregate_service_level_bottlenecks()`, `aggregate_revenue_deficit()`, `aggregate_average_discount()`, `aggregate_seasonality()` e `aggregate_price_elasticity()`.
  - **Assert:** Todos os métodos retornam os DTOs de agregação com os cálculos SQL exatos (SUM, AVG, GROUP BY, FILTER).
  - **Priority:** P0

- [COMPLETED] [TEST003-18] [Type: Unit] **test_duckdb_adapter_missing_csv_resilience**
  - **Target:** `tests/unit/test_duckdb_sales_adapter.py` → `test_duckdb_sales_adapter_missing_csv()`
  - **Scenario:** Garantir resiliência ao inicializar com arquivo CSV inexistente.
  - **Arrange:** Instanciar adapter apontando para `"non_existent_file.csv"`.
  - **Act:** Executar `aggregate_top_selling_product()` e `get_sales_by_filter()`.
  - **Assert:** `aggregate_top_selling_product() is None` e `get_sales_by_filter() == []` sem lançar exceção fatal.
  - **Priority:** P1

- [COMPLETED] [TEST003-19] [Type: Unit] **test_duckdb_adapter_external_access_security**
  - **Target:** `tests/unit/test_duckdb_sales_adapter.py` → `test_duckdb_sales_adapter_external_access_disabled()`
  - **Scenario:** Garantir que tentativas de ler arquivos arbitrários pós-inicialização via `read_csv_auto` na query são bloqueadas.
  - **Arrange:** Instanciar `DuckDbSalesAdapter`.
  - **Act:** Tentar executar `execute_read_only_query("SELECT * FROM read_csv_auto('...')")`.
  - **Assert:** Lança exceção de segurança do DuckDB (`enable_external_access = false`).
  - **Priority:** P0

---

### Task 008 — [Test-Integration]: Paridade End-to-End do Pushdown Analítico

- [COMPLETED] [TEST003-20] [Type: Integration] **test_e2e_analytical_pushdown_parity**
  - **Target:** `tests/integration/test_sales_metrics_integration.py` → `test_integration_top_selling_product()`, `test_integration_revenue_deficit()`, etc.
  - **Scenario:** Validar a cadeia completa da Arquitetura Hexagonal (`DuckDbSalesAdapter` → `SalesMetricsApplicationService` → Domain Services) em dataset sintético.
  - **Arrange:** Carregar dataset com 6 transações com mix de produtos (Alpha, Beta, Gamma), promoções (Winter, Flash, B2B) e armazéns (North, South).
  - **Act:** Executar os 10 casos de uso analíticos através da aplicação.
  - **Assert:**
    - `Product_Beta` é o mais vendido (320 un, R$ 27.600 receita).
    - `Whse_North` lidera o ranking de volume (400 un).
    - Receita realizada é de R$ 55.800 vs R$ 65.000 planejada, apurando déficit de R$ 9.200.
    - `Whse_South` é identificado como pior SLA logístico (média 0.9033).
    - Desconto médio global é de 13.33% com breakdown correto por promoção.
  - **Priority:** P0
