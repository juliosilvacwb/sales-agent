# TEST003-service-level-bottlenecks — Especificação de Cobertura de Testes

> **Incidente de Origem:** [B003-service-level-bottlenecks.md](../incidents/B003-service-level-bottlenecks.md)

## Visão Geral de Cobertura

Esta especificação detalha os requisitos de cobertura de testes para a resolução do **Incidente B003: Falso Positivo de Gargalo de SLA**. O serviço de domínio subjacente `AdvancedMetricsService.analyze_service_level_bottlenecks` escolhia anteriormente um armazém arbitrário como "gargalo crítico de SLA" quando todos os armazéns no conjunto de dados possuíam níveis médios de serviço idênticos (98,00%).

A suíte de testes valida:

1. Comportamento ponta a ponta sobre os dados analíticos de vendas no DuckDB.
2. Tratamento de SLA igual/empatado entre múltiplas localidades.
3. Segurança contra imprecisão no acúmulo de ponto flutuante.
4. Casos de borda (conjunto de dados vazio, armazém único).
5. Prevenção de regressão na identificação de gargalo de SLA distinto.

## Checklist de Testes

### Task 001 — Teste de Reprodução e Integração

- [COMPLETED] [TEST003-01] [Integration] **`test_service_level_bottlenecks_equal_sla_reproduction`**
  - **Alvo:** `tests/integration/test_service_level_incident_b003.py` → `test_service_level_bottlenecks_equal_sla_reproduction()`
  - **Cenário:** Valida a análise de gargalo de SLA quando todos os armazéns em `dataset/sales.csv` possuem nível médio de serviço de 98,00%.
  - **Arrange:** Instanciar `DuckDbSalesAdapter` com `dataset/sales.csv` e inicializar `SalesMetricsApplicationService`.
  - **Act:** Executar `service.analyze_service_level_bottlenecks()`.
  - **Assert:** Verificar que `worst_location` é `"N/A"` (não `'Whse_A'`) e o `summary` não contém `"critical SLA bottleneck"`.
  - **Prioridade:** P0

### Task 002 — Lógica de Domínio e Detecção de SLA Igual

- [COMPLETED] [TEST003-02] [Unit] **`test_analyze_service_level_bottlenecks_equal_sla`**
  - **Alvo:** `src/domain/service/advanced_metrics_service.py` → `analyze_service_level_bottlenecks()`
  - **Cenário:** Avalia o cálculo de SLA quando registros sintéticos de entrada em 3 armazéns (Whse_A, Whse_B, Whse_C) possuem SLA igual de 0.98.
  - **Arrange:** Construir sequência de instâncias de `SaleRecord` para Whse_A, Whse_B e Whse_C com `service_level=0.98`.
  - **Act:** Chamar `AdvancedMetricsService().analyze_service_level_bottlenecks(records)`.
  - **Assert:** Garantir `worst_location == "N/A"`, `worst_service_level == 0.98`, `overall_average_service_level == 0.98` e `summary` contendo `"No logistics SLA bottleneck identified"`.
  - **Prioridade:** P0

- [COMPLETED] [TEST003-03] [Unit] **`test_analyze_service_level_bottlenecks_empty_records`**
  - **Alvo:** `src/domain/service/advanced_metrics_service.py` → `analyze_service_level_bottlenecks()`
  - **Cenário:** Avalia a análise de gargalo de SLA quando um conjunto de dados vazio é fornecido.
  - **Arrange:** Definir `records = []`.
  - **Act:** Chamar `AdvancedMetricsService().analyze_service_level_bottlenecks(records)`.
  - **Assert:** Garantir `worst_location == "N/A"`, `worst_service_level == 0.0`, `overall_average_service_level == 0.0` e `summary == "No records to analyze for SLA bottlenecks"`.
  - **Prioridade:** P1

- [COMPLETED] [TEST003-04] [Unit] **`test_analyze_service_level_bottlenecks_distinct_sla`**
  - **Alvo:** `src/domain/service/advanced_metrics_service.py` → `analyze_service_level_bottlenecks()`
  - **Cenário:** Proteção contra regressão confirmando que um gargalo autêntico é identificado corretamente quando as localidades possuem SLAs distintos.
  - **Arrange:** Construir instâncias de `SaleRecord` onde Whse_A possui SLA médio 0.985 e Whse_B possui SLA médio 0.825.
  - **Act:** Chamar `AdvancedMetricsService().analyze_service_level_bottlenecks(records)`.
  - **Assert:** Garantir `worst_location == "Whse_B"`, `worst_service_level == 0.825` e `summary` contendo `"The critical SLA bottleneck is at location 'Whse_B'"`.
  - **Prioridade:** P0

### Task 003 — Segurança, Precisão e Casos de Borda

- [COMPLETED] [TEST003-05] [Unit] **`test_analyze_service_level_bottlenecks_floating_imprecision`**
  - **Alvo:** `src/domain/service/advanced_metrics_service.py` → `analyze_service_level_bottlenecks()`
  - **Cenário:** Verifica se discrepâncias mínimas de acúmulo em ponto flutuante (`0.9799999999996978` vs `0.9800000000003375`) não acionam relatórios de falso positivo.
  - **Arrange:** Construir `SaleRecord` para Whse_A com `0.9799999999996978` e Whse_B com `0.9800000000003375`.
  - **Act:** Chamar `AdvancedMetricsService().analyze_service_level_bottlenecks(records)`.
  - **Assert:** Garantir `worst_location == "N/A"`, `worst_service_level == 0.98` e `summary` contendo `"No logistics SLA bottleneck identified"`.
  - **Prioridade:** P0

- [COMPLETED] [TEST003-06] [Unit] **`test_analyze_service_level_bottlenecks_single_location`**
  - **Alvo:** `src/domain/service/advanced_metrics_service.py` → `analyze_service_level_bottlenecks()`
  - **Cenário:** Verifica o comportamento quando o conjunto de dados contém registros de apenas um único armazém.
  - **Arrange:** Construir instâncias de `SaleRecord` pertencentes exclusivamente a `Whse_A` (ex: SLA 0.95).
  - **Act:** Chamar `AdvancedMetricsService().analyze_service_level_bottlenecks(records)`.
  - **Assert:** Garantir `worst_location == "N/A"` (visto que não existem outras localidades para comparar), `overall_average_service_level == 0.95`.
  - **Prioridade:** P2
