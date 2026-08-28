# Resumo do Incidente: B003 - Gargalos no Nível de Serviço

- **Cobertura de Testes:** [TEST003-service-level-bottlenecks.md](../tests/TEST003-service-level-bottlenecks.md)
- **Auditoria de Segurança:** [S003-service-level-bottlenecks.md](../security/S003-service-level-bottlenecks.md)

O assistente de IA alucina um falso positivo indicando gargalo de SLA em `Whse_A` ao ser questionado sobre qual localidade apresenta o pior nível de serviço logístico. Embora todas as localidades no conjunto de dados (Whse_A, Whse_J, Whse_C, Whse_S) possuam níveis médios de serviço idênticos (98,00%), o sistema identificava `Whse_A` como o "gargalo crítico de SLA", causando contradições ao ser questionado pelo usuário.

## Análise Técnica da Causa Raiz

O problema estava localizado em `AdvancedMetricsService.analyze_service_level_bottlenecks` em `src/domain/service/advanced_metrics_service.py`.

1. **Seleção Arbitrária com Valores Iguais:**
   A função calcula as médias de SLA arredondadas por localidade `loc_averages` (onde todos os armazéns resultavam em `0.98`) e anteriormente determinava a pior localidade usando `worst_loc, worst_sla = min(loc_averages.items(), key=lambda item: item[1])`. Quando todos os valores em `loc_averages` eram iguais (`0.98`), a função `min()` do Python escolhia arbitrariamente o primeiro item da iteração do dicionário (`Whse_A`).

2. **Imprecisão de Ponto Flutuante vs. Igualdade Exata (`min_sla == max_sla`):**
   Usar uma verificação por delta em ponto flutuante como `abs(max_sla - min_sla) < 1e-4` mostrou-se propenso a erros em casos de borda devido à representação de float IEEE-754 (por exemplo, `0.9800 - 0.9799` avaliando para `0.00009999999999998899 < 0.0001`). Isso fazia com que pequenas diferenças legítimas (como `Whse_A` caindo para 97,99% enquanto outros permaneciam em 98,00%) fossem incorretamente tratadas como empates iguais, projetando `min_sla` (97,99%) para todos os armazéns na string de resumo.

3. **Correção Definitiva:**
   A condição foi refinada para comparar a igualdade exata entre as médias arredondadas em 4 casas decimais:

   ```python
   if min_sla == max_sla:
       summary = (
           f"All locations present an equal average service level of {min_sla * 100:.2f}% "
           f"(overall fleet average: {overall_avg * 100:.2f}%). No logistics SLA bottleneck identified."
       )
       return ServiceLevelBottleneckResult(
           worst_location="N/A",
           worst_service_level=min_sla,
           overall_average_service_level=overall_avg,
           location_averages=loc_averages,
           summary=summary,
       )
   ```

   Quando as médias diferem (ex: `0.9799` vs `0.9800`), `min_sla == max_sla` resulta em `False`, permitindo que o sistema identifique com precisão `worst_location="Whse_A"` com `worst_service_level=0.9799`.

## Script de Reprodução (OBRIGATÓRIO)

```python
import pytest
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.domain.service.advanced_metrics_service import AdvancedMetricsService
from src.domain.service.basic_metrics_service import BasicMetricsService
from src.application.service.sales_metrics_service import SalesMetricsApplicationService


def test_service_level_bottlenecks_equal_sla_reproduction():
    """
    Automated Reproduction Test for SLA Bottlenecks when service levels are identical.
    Validates that when all locations present equal service levels (98.00%),
    the metric does not arbitrarily highlight one warehouse as a bottleneck.
    """
    adapter = DuckDbSalesAdapter(dataset_path="dataset/sales.csv")
    service = SalesMetricsApplicationService(
        sales_data_port=adapter,
        basic_metrics_service=BasicMetricsService(),
        advanced_metrics_service=AdvancedMetricsService(),
    )

    result = service.analyze_service_level_bottlenecks()

    # In dataset/sales.csv, all warehouses have an average SLA of 98.00%.
    # Currently, result.worst_location returns 'Whse_A' and summary claims Whse_A is a bottleneck.
    # Expected behavior when all SLAs are equal:
    # 1. worst_location should return "N/A" or "None" (or indicate no bottleneck).
    # 2. summary should state that all locations operate at equal service levels with no bottleneck.
    assert result.worst_location in ("N/A", "None", "TIE", "Nenhum"), (
        f"Expected no specific location as bottleneck when all SLAs are equal, got '{result.worst_location}'"
    )
    assert "critical sla bottleneck" not in result.summary.lower(), (
        f"Summary incorrectly reports a critical bottleneck: '{result.summary}'"
    )
```

## Checklist de Correção (Tarefas Atômicas)

- [COMPLETED] Task 001 - [Test] Implementar o script de reprodução em `tests/integration/test_service_level_incident_b003.py` e confirmar a falha (Red).
- [COMPLETED] Task 002 - [Logic] Corrigir `analyze_service_level_bottlenecks` em `src/domain/service/advanced_metrics_service.py` para verificar médias de SLA uniformes/empatadas entre localidades, definindo `worst_location` como `"N/A"` (ou `"None"`) e gerando um resumo indicando que não existe gargalo de localidade quando todos os SLAs forem iguais.
- [COMPLETED] Task 003 - [Security/Perf] Adicionar testes unitários em `tests/unit/test_advanced_metrics_service.py` verificando o tratamento de SLAs empatados, tolerância de ponto flutuante e cálculos com gargalos distintos por localidade.
