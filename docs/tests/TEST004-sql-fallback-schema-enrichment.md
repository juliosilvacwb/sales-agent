# TEST004-sql-fallback-schema-enrichment — Especificação de Cobertura de Testes

> **Tarefa de Origem:** [B004-sql-fallback-schema-enrichment.md](../incidents/B004-sql-fallback-schema-enrichment.md)

## Visão Geral de Cobertura

Suíte de validação para o Incidente B004 cobrindo enriquecimento de esquema, orientação semântica de domínio (`promotion_type IS NULL`, metas de receita) e tratamento de payload estruturado de resultado vazio na `SecuredSQLQueryTool`.

## Checklist de Testes

### Task 001 — Implementar script de reprodução para o B004

- [COMPLETED] [TEST004-01] [Type: Unit] **test_sql_fallback_schema_enrichment_and_validation_reproduction**
  - **Alvo:** `tests/unit/test_sql_fallback_incident_b004.py` → `test_sql_fallback_schema_enrichment_and_validation_reproduction()`
  - **Cenário:** Valida enriquecimento da descrição do esquema, enriquecimento da descrição da ferramenta e payload estruturado de aviso em conjuntos de resultados vazios.
  - **Arrange:** Instanciar o esquema `SQLQueryInput` e a `SecuredSQLQueryTool` com `SalesAnalysisUseCase` mockado.
  - **Act:** Extrair esquema JSON de `SQLQueryInput`, ler `SecuredSQLQueryTool.description` e invocar a ferramenta com consulta que retorne `[]`.
  - **Assert:** Verificar que `promotion_type`, `is null` / `having count` e orientações de cálculo de receita existem nas descrições da ferramenta e esquema, e que a resposta contém `EMPTY_RESULT_SET` e `self_correction_guidance`.
  - **Prioridade:** P0

### Task 002 — Enriquecer descrições de esquema do SQLQueryInput e SecuredSQLQueryTool

- [COMPLETED] [TEST004-02] [Type: Unit] **test_sql_query_input_schema_has_full_domain_context**
  - **Alvo:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SQLQueryInput`
  - **Cenário:** Verificar se a descrição do campo `SQLQueryInput.query` contém todas as definições de colunas e regras de domínio.
  - **Arrange:** Acessar `SQLQueryInput.model_json_schema()` (ou `.schema()`).
  - **Act:** Ler a string de `description` da propriedade `query`.
  - **Assert:** Garantir que a descrição contém `product_id`, `local`, `date`, `planned_quantity`, `actual_quantity`, `planned_price`, `actual_price`, `service_level`, `promotion_type`, `HAVING COUNT(promotion_type) = 0` e `SUM(actual_quantity * actual_price)`.
  - **Prioridade:** P0

- [COMPLETED] [TEST004-03] [Type: Unit] **test_secured_sql_tool_description_has_table_and_revenue_semantics**
  - **Alvo:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SecuredSQLQueryTool`
  - **Cenário:** Verificar se a descrição da ferramenta expõe lista de colunas e regras de cálculo de meta de receita sem promoção para o agente LLM.
  - **Arrange:** Instanciar `SecuredSQLQueryTool` via fábrica `create_sql_fallback_tool`.
  - **Act:** Ler `tool.description`.
  - **Assert:** Garantir que a descrição inclui o esquema de colunas, orientação de `promotion_type IS NULL` e `SUM(actual_quantity * actual_price) >= SUM(planned_quantity * planned_price)`.
  - **Prioridade:** P1

### Task 003 — Payload de aviso estruturado para conjuntos de resultados vazios

- [COMPLETED] [TEST004-04] [Type: Unit] **test_secured_sql_tool_returns_structured_warning_on_empty_results**
  - **Alvo:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SecuredSQLQueryTool._run()`
  - **Cenário:** Quando a consulta DuckDB retorna lista vazia `[]`, a ferramenta retorna payload JSON com `status: EMPTY_RESULT_SET` e orientações de auto-correção.
  - **Arrange:** Mockar `use_case.execute_custom_query` para retornar `[]`.
  - **Act:** Invocar `tool.invoke({"query": "SELECT * FROM sales_data WHERE product_id = 'UNKNOWN'"})`.
  - **Assert:** Parsear resposta JSON, verificar `status == 'EMPTY_RESULT_SET'`, `count == 0` e presença de `self_correction_guidance` no payload.
  - **Prioridade:** P0

- [COMPLETED] [TEST004-05] [Type: Unit] **test_secured_sql_tool_handles_exceptions_gracefully**
  - **Alvo:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SecuredSQLQueryTool._run()`
  - **Cenário:** Quando a consulta DuckDB lança uma Exception, verificar se a string da exceção é retornada sem derrubar a ferramenta.
  - **Arrange:** Mockar `use_case.execute_custom_query` para lançar `RuntimeError("Table not found")`.
  - **Act:** Invocar `tool.invoke({"query": "SELECT * FROM non_existent_table"})`.
  - **Assert:** Garantir que a string retornada começa com `Erro ao executar a consulta SQL: Table not found`.
  - **Prioridade:** P1
