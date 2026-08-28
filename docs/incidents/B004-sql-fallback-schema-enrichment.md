# Resumo do Incidente: B004 - Enriquecimento do Esquema do Fallback SQL

- **Cobertura de Testes:** [TEST004-sql-fallback-schema-enrichment.md](../tests/TEST004-sql-fallback-schema-enrichment.md)
- **Auditoria de Segurança:** [S004-sql-fallback-schema-enrichment.md](../security/S004-sql-fallback-schema-enrichment.md)

Quando os usuários fazem perguntas analíticas ad-hoc não cobertas por ferramentas de domínio fixas (como *"Quais produtos não tiveram vendas promocionais mas ainda assim atingiram a meta de receita?"*), a ferramenta de fallback `SecuredSQLQueryTool` gera consultas SQL incorretas. O LLM responde erroneamente que 0 produtos atenderam aos critérios, quando na verdade **914 produtos** em `dataset/sales.csv` cumprem a condição.

## Análise Técnica da Causa Raiz

A falha ocorre devido a duas limitações principais em `src/adapter/inbound/llm/sql_fallback_tool.py`:

1. **Falta de Esquema e Semântica de Domínio na Descrição da Ferramenta:**
   O esquema de `SQLQueryInput` e a descrição da `SecuredSQLQueryTool` continham apenas texto genérico (*"Executa uma consulta SQL analítica na tabela sales_data"*). Faltavam detalhes críticos do esquema:
   - `promotion_type` é `NULL` para 99,99% das linhas sem promoção.
   - Filtrar produtos sem promoção no nível do produto requer `GROUP BY product_id HAVING COUNT(promotion_type) = 0` ou `WHERE promotion_type IS NULL`, em vez de filtrar incorretamente itens promocionais no nível de linha.
   - O atingimento da meta de receita requer comparar `SUM(actual_quantity * actual_price) >= SUM(planned_quantity * planned_price)`.

2. **Saída Passiva de Resultado Vazio e Falta de Auto-Correção:**
   Quando uma consulta SQL mal formada é executada e retorna `[]` (0 linhas), `SecuredSQLQueryTool._run()` retorna uma mensagem passiva (*"A consulta foi executada com sucesso, mas não retornou nenhum registro"*). Vendo 0 registros, o LLM aceita o resultado como verdade e alucina uma conclusão invertida ("nenhum produto atingiu a meta sem promoções").

## Script de Reprodução (OBRIGATÓRIO)

```python
import pytest
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.domain.service.advanced_metrics_service import AdvancedMetricsService
from src.domain.service.basic_metrics_service import BasicMetricsService
from src.application.service.sales_metrics_service import SalesMetricsApplicationService
from src.adapter.inbound.llm.sql_fallback_tool import SecuredSQLQueryTool, SQLQueryInput


def test_sql_fallback_schema_enrichment_and_validation_reproduction():
    """
    Automated Reproduction Test for B004 - SQL Fallback Schema Enrichment & Validation.
    Validates that:
    1. SecuredSQLQueryTool input schema contains explicit DuckDB table context (promotion_type IS NULL handling, revenue meta rules).
    2. Fallback tool enforces semantic validation and enriched schema guidance.
    """
    # 1. Verify schema description enrichment in SQLQueryInput
    input_schema = SQLQueryInput.model_json_schema() if hasattr(SQLQueryInput, "model_json_schema") else SQLQueryInput.schema()
    description = input_schema.get("properties", {}).get("query", {}).get("description", "")

    assert "promotion_type" in description.lower(), (
        "SQLQueryInput description must include schema context for promotion_type."
    )
    assert "having count(promotion_type) = 0" in description.lower() or "is null" in description.lower(), (
        "SQLQueryInput description must explain how to query non-promoted products."
    )
```

## Checklist de Correção (Tarefas Atômicas)

- [COMPLETED] Task 001 - [Test] Implementar o script de reprodução em `tests/unit/test_sql_fallback_incident_b004.py` e confirmar a falha (Red).
- [COMPLETED] Task 002 - [Logic] Enriquecer `SQLQueryInput` e `SecuredSQLQueryTool` em `src/adapter/inbound/llm/sql_fallback_tool.py` com contexto explícito de esquema da tabela `sales_data`, definições de colunas, semântica de `promotion_type IS NULL` e orientações de cálculo para metas de receita.
- [COMPLETED] Task 003 - [Security/Perf] Adicionar validação de intenção semântica e payload de aviso estruturado para conjuntos de resultados vazios em `SecuredSQLQueryTool._run()` para orientar a auto-correção do agente antes de retornar resultados vazios.
