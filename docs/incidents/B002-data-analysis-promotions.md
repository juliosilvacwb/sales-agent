# Resumo do Incidente: B002 - Análise de Dados de Promoções

- **Cobertura de Testes:** [TEST002-data-analysis-promotions.md](../tests/TEST002-data-analysis-promotions.md)
- **Auditoria de Segurança:** [S002-data-analysis-promotions.md](../security/S002-data-analysis-promotions.md)

O assistente de IA relata que o desconto médio geral é de 0% e que não houve vendas promocionais ou descontos aplicados, embora o conjunto de dados contenha claramente promoções do tipo "Flash" com vendas realizadas.

## Análise Técnica da Causa Raiz

O bug reside em `AdvancedMetricsService.calculate_average_discount` localizado em `src/domain/service/advanced_metrics_service.py`. Existem dois problemas principais:

1. **Cálculo do Desconto Total:** `total_discount_val` é calculated como `max(0.0, total_planned_rev - total_actual_rev)` sobre todos os registros globalmente. Como a receita realizada total é maior que a receita planejada total em todo o conjunto de dados (devido a alguns itens vendidos com ágio/premium), essa subtração global resulta em `< 0`, fazendo com que `max()` retorne `0.0`. O cálculo deve somar os descontos *apenas* para os registros onde `actual_price < planned_price`.
2. **Percentual de Desconto Médio:** `avg_discount_pct` é calculado tirando a média de `r.discount_rate` em todos os registros. Como `discount_rate` pode ser negativo (quando `actual_price > planned_price`), as taxas positivas e negativas se anulam ao longo de 200.000+ registros, resultando em ~0.001%, que é arredondado para `0.0%`.

Como consequência, `average_discount_in_promotion` pode exibir um desconto de 20% para "Flash", mas o valor global de desconto aparece como 0, o que confunde o LLM fazendo-o acreditar que nenhum desconto foi aplicado na prática.

## Script de Reprodução (OBRIGATÓRIO)

```python
import pytest
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.domain.service.advanced_metrics_service import AdvancedMetricsService
from src.domain.service.basic_metrics_service import BasicMetricsService
from src.application.service.sales_metrics_service import SalesMetricsApplicationService


def test_data_analysis_promotions_reproduction():
    """
    Automated Reproduction Test for the Data Analysis Promotions Error.
    Validates that the total discount value and overall discount percentage
    are calculated correctly instead of returning 0.0.
    """
    adapter = DuckDbSalesAdapter(dataset_path="dataset/sales.csv")
    service = SalesMetricsApplicationService(
        sales_data_port=adapter,
        basic_metrics_service=BasicMetricsService(),
        advanced_metrics_service=AdvancedMetricsService(),
    )

    result = service.calculate_average_discount()

    # We expect this test to FAIL currently because result.total_discount_value is 0.0
    # and result.overall_average_discount_percentage is 0.0.
    # The Engineer Agent will fix the logic in AdvancedMetricsService.
    assert result.total_discount_value > 0.0, (
        f"Expected positive discount value, got {result.total_discount_value}"
    )
    assert result.overall_average_discount_percentage > 0.0, (
        f"Expected positive discount percentage, got {result.overall_average_discount_percentage}"
    )
```

## Checklist de Correção (Tarefas Atômicas)

- [COMPLETED] Task 001 - [Test] Implementar o script de reprodução em `tests/integration/test_data_analysis_incident_b002.py` e confirmar a falha (Red).
- [COMPLETED] Task 002 - [Logic] Corrigir `calculate_average_discount` em `src/domain/service/advanced_metrics_service.py` para acumular apenas taxas de desconto positivas e somar adequadamente valores individuais de desconto positivo.
- [COMPLETED] Task 003 - [Security/Perf] Adicionar testes unitários em `tests/unit/test_advanced_metrics_service.py` para casos de borda onde há aumentos e reduções de preço misturados.
