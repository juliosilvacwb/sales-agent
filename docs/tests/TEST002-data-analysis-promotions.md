# TEST002-data-analysis-promotions — Especificação de Cobertura de Testes

> **Tarefa de Origem:** [B002-data-analysis-promotions.md](../incidents/B002-data-analysis-promotions.md)

## Visão Geral de Cobertura

Esta especificação detalha os cenários de teste para validar a correção em `AdvancedMetricsService.calculate_average_discount`. Ela cobre os testes de reprodução de integração em relação ao conjunto de dados de vendas do DuckDB e testes unitários cobrindo filtragem de desconto positivo, aumentos de preços mistos e casos de borda.

## Checklist de Testes

### Task 001 - Implementar o script de reprodução

- [COMPLETED] [TEST002-01] [Type: Integration] **test_data_analysis_promotions_reproduction**
  - **Alvo:** `tests/integration/test_data_analysis_incident_b002.py` -> `test_data_analysis_promotions_reproduction()`
  - **Cenário:** Valida a leitura de ponta a ponta do conjunto de dados e verifica se valores de desconto positivo e percentuais de desconto são calculados em vez de retornar 0.0.
  - **Arrange:** Instanciar `DuckDbSalesAdapter` com `dataset/sales.csv` e `SalesMetricsApplicationService`.
  - **Act:** Chamar `service.calculate_average_discount()`.
  - **Assert:** Verificar `total_discount_value > 0.0` e `overall_average_discount_percentage > 0.0`.
  - **Prioridade:** P0

### Task 002 - Corrigir a lógica de calculate_average_discount

- [COMPLETED] [TEST002-02] [Type: Unit] **test_calculate_average_discount**
  - **Alvo:** `tests/unit/test_advanced_metrics_service.py` -> `test_calculate_average_discount()`
  - **Cenário:** Validar que o percentual de desconto médio e o valor total de desconto calculam descontos positivos corretamente em registros de amostra padrão.
  - **Arrange:** Configurar a fixture `sample_advanced_sales_records` contendo itens com descontos de 20% e 10%.
  - **Act:** Chamar `service.calculate_average_discount(sample_records)`.
  - **Assert:** Verificar `overall_average_discount_percentage == 15.0`, `total_discount_value == 6400.0` e `discount_by_promotion["Promo_Flash"] == 20.0`.
  - **Prioridade:** P0

### Task 003 - Adicionar testes unitários para aumentos de preço mistos e casos de borda

- [COMPLETED] [TEST002-03] [Type: Unit] **test_calculate_average_discount_mixed_price_increases**
  - **Alvo:** `tests/unit/test_advanced_metrics_service.py` -> `test_calculate_average_discount_mixed_price_increases()`
  - **Cenário:** Validar que registros com aumento de preço (actual_price > planned_price) não reduzem o valor total de desconto nem diluem o percentual de desconto positivo médio.
  - **Arrange:** Construir lista de SaleRecord com 1 item com desconto de 20% e 1 item com aumento de preço de 50%.
  - **Act:** Chamar `service.calculate_average_discount(records)`.
  - **Assert:** Verificar `total_discount_value == 2000.0`, `overall_average_discount_percentage == 20.0` e `discount_by_promotion == {"Flash": 20.0}`.
  - **Prioridade:** P0
