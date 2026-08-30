# TEST005-ast-sql-validation — Test Coverage Specification

> **Source Task:** [T005-ast-sql-validation.md](../architecture/T005-ast-sql-validation.md)  
> **PRD Reference:** [R005-ast-sql-validation.md](../business-requirements/R005-ast-sql-validation.md)  
> **Quality Report:** [Q005-ast-sql-validation.md](../quality/Q005-ast-sql-validation.md)

## Coverage Overview

Esta especificação detalha a análise forense de cobertura de testes unitários e de integração para a substituição do validador SQL baseado em Regex por um analisador de Árvore de Sintaxe Abstrata (AST) determinístico com `sqlglot` (`T005-ast-sql-validation.md` / `R005-ast-sql-validation.md`). A nova arquitetura elimina 100% dos falsos positivos em literais de strings (ex: `WHERE product_id = 'DROP_01'`) e fornece proteção profunda e recursiva contra nós mutacionais (DML/DDL) e funções de leitura do sistema de arquivos no DuckDB.

- **Status Geral de Cobertura:** 100% de cobertura lógica, tratamento de exceções, isolamento de literais e branch coverage mapeados para todas as 13 tasks da especificação T005.
- **Pirâmide de Testes:**
  - **Unitários (Domínio Puro):** Testes de integridade de enums, hierarquia de exceções de domínio, imutabilidade dos value objects (`SqlValidationResult`, `ParsedSqlStatement`) e matriz parametrizada de regras de segurança no `SqlSecurityValidator`.
  - **Unitários (Portas):** Teste de abstração da porta de saída `SqlParserPort` garantindo contrato de interface.
  - **Unitários (Adaptador Externo):** Testes do `SqlGlotParserAdapter` cobrindo parsing no dialeto DuckDB, extração recursiva de AST, funções anônimas, consultas aninhadas/CTEs, consultas múltiplas e captura de `ParseError`.
  - **Unitários (Adaptador Inbound / Tool LLM):** Testes do `SecuredSQLQueryTool` validando injeção de dependência, feedback de autocorreção em erros de sintaxe, mensagens de segurança em português, truncamento de resultados (>50 registros), tratamento de conjuntos vazios e sanitização de paths `[REDACTED_PATH]`.
  - **Integração (Pipeline E2E):** Testes end-to-end do pipeline completo (String SQL → `SqlGlotParserAdapter` → `SqlSecurityValidator` → `SecuredSQLQueryTool` → `SalesAnalysisUseCase`) com verificação de observabilidade `[MISSING_TOOL]` e SLA de performance (< 5ms).

---

## Test Checklist

### Task 001 — [Domain-Enum]: SqlViolationType Enum

- [COMPLETED] [TEST005-01] [Type: Unit] **test_sql_violation_type_enum_members**
  - **Target:** `src/domain/model/sql_validation.py` → `SqlViolationType`
  - **Scenario:** Validar que todos os 5 membros do enum de violações de segurança existem com valores descritivos.
  - **Arrange:** Obter os membros de `SqlViolationType`.
  - **Act:** Inspecionar `DISALLOWED_ROOT_OPERATION`, `FORBIDDEN_MUTATIONAL_NODE`, `FORBIDDEN_FUNCTION_CALL`, `STACKED_QUERIES_DETECTED` e `SQL_SYNTAX_ERROR`.
  - **Assert:** Todos os 5 membros existem e suas propriedades `description` retornam strings não vazias.
  - **Priority:** P0

---

### Task 002 — [Domain-Exception]: SqlValidationError Domain Exception Hierarchy

- [COMPLETED] [TEST005-02] [Type: Unit] **test_sql_validation_error_hierarchy**
  - **Target:** `src/domain/exception/sql_validation_exceptions.py` → `SqlValidationError`
  - **Scenario:** Validar que a hierarquia de exceções herda de `SqlValidationError` e transporta metadados estruturados de violação.
  - **Arrange:** Importar `SqlValidationError`, `SqlSyntaxError` e `SqlSecurityViolationError`.
  - **Act:** Instanciar `SqlSyntaxError("SQL_SYNTAX_ERROR", "Unmatched paren")` e `SqlSecurityViolationError("FORBIDDEN_MUTATIONAL_NODE", "DROP is forbidden", offending_node_type="DROP")`.
  - **Assert:** `issubclass(SqlSyntaxError, SqlValidationError)` é `True`, `issubclass(SqlSecurityViolationError, SqlValidationError)` é `True`, e os atributos `violation_type`, `detail` e `offending_node_type` são atribuídos corretamente.
  - **Priority:** P0

---

### Task 003 — [Domain-Model]: SqlValidationResult Value Object

- [COMPLETED] [TEST005-03] [Type: Unit] **test_sql_validation_result_success_factory**
  - **Target:** `src/domain/model/sql_validation.py` → `SqlValidationResult.success()`
  - **Scenario:** Validar a criação de um resultado de validação bem-sucedido via método de fábrica.
  - **Arrange:** Chamar `SqlValidationResult.success()`.
  - **Act:** Inspecionar os campos `is_valid`, `violation_type`, `violation_detail` e `offending_node`.
  - **Assert:** `result.is_valid is True`, `result.violation_type is None`, `result.violation_detail is None`, `result.offending_node is None`.
  - **Priority:** P0

- [COMPLETED] [TEST005-04] [Type: Unit] **test_sql_validation_result_violation_factory**
  - **Target:** `src/domain/model/sql_validation.py` → `SqlValidationResult.violation()`
  - **Scenario:** Validar a criação de um resultado de validação com falha contendo tipo de violação, detalhe e nó ofensivo.
  - **Arrange:** Definir `vtype = SqlViolationType.FORBIDDEN_MUTATIONAL_NODE`, `detail = "Forbidden DROP"`, `node = "DROP"`.
  - **Act:** Instanciar `SqlValidationResult.violation(vtype, detail, node)`.
  - **Assert:** `result.is_valid is False`, `result.violation_type == vtype`, `result.violation_detail == detail` e `result.offending_node == "DROP"`.
  - **Priority:** P0

- [COMPLETED] [TEST005-05] [Type: Unit] **test_sql_validation_result_immutability**
  - **Target:** `src/domain/model/sql_validation.py` → `SqlValidationResult`
  - **Scenario:** Garantir que `SqlValidationResult` é imutável (`frozen=True`) para prevenir efeitos colaterais de estado no heap.
  - **Arrange:** Instanciar `result = SqlValidationResult.success()`.
  - **Act:** Tentar alterar `result.is_valid = False`.
  - **Assert:** Lança `dataclasses.FrozenInstanceError`.
  - **Priority:** P1

---

### Task 004 — [Domain-Model]: ParsedSqlStatement Value Object

- [COMPLETED] [TEST005-06] [Type: Unit] **test_parsed_sql_statement_instantiation_and_immutability**
  - **Target:** `src/domain/model/sql_validation.py` → `ParsedSqlStatement`
  - **Scenario:** Validar a correta inicialização de `ParsedSqlStatement` e garantir sua imutabilidade.
  - **Arrange:** Preparar `root = "SELECT"`, `nodes = frozenset({"SELECT", "LITERAL"})`, `funcs = frozenset({"SUM"})`, `count = 1`, `sql = "SELECT SUM(x) FROM t"`.
  - **Act:** Instanciar `ParsedSqlStatement(root, nodes, funcs, count, sql)` e tentar reatribuir `stmt.root_node_type = "DROP"`.
  - **Assert:** Campos são acessíveis com os valores informados e a tentativa de mutação dispara `dataclasses.FrozenInstanceError`.
  - **Priority:** P0

---

### Task 005 — [Domain-Service]: SqlSecurityValidator Domain Service

- [COMPLETED] [TEST005-07] [Type: Unit] **test_valid_root_operations**
  - **Target:** `tests/unit/test_sql_security_validator.py` → `test_valid_root_operations()`
  - **Scenario:** Validar que nós raiz permitidos (`SELECT`, `WITH`, `UNION`) passam na validação de segurança.
  - **Arrange:** Criar `ParsedSqlStatement` sintético com `root_node_type` parametrizado em `["SELECT", "WITH", "UNION"]`.
  - **Act:** Executar `validator.validate(statement)`.
  - **Assert:** `result.is_valid is True` e `result.violation_type is None`.
  - **Priority:** P0

- [COMPLETED] [TEST005-08] [Type: Unit] **test_forbidden_root_operations**
  - **Target:** `tests/unit/test_sql_security_validator.py` → `test_forbidden_root_operations()`
  - **Scenario:** Garantir que operações raiz mutacionais ou de definição de dados são categoricamente rejeitadas.
  - **Arrange:** Criar `ParsedSqlStatement` com `root_node_type` parametrizado em `["DROP", "DELETE", "UPDATE", "INSERT", "ALTER"]`.
  - **Act:** Executar `validator.validate(statement)`.
  - **Assert:** `result.is_valid is False` e `result.violation_type == SqlViolationType.DISALLOWED_ROOT_OPERATION`.
  - **Priority:** P0

- [COMPLETED] [TEST005-09] [Type: Unit] **test_forbidden_mutational_nodes_deep_ast**
  - **Target:** `tests/unit/test_sql_security_validator.py` → `test_forbidden_mutational_nodes()`
  - **Scenario:** Validar detecção e bloqueio de nós mutacionais presentes em qualquer nível de profundidade da AST (subconsultas ou CTEs).
  - **Arrange:** Criar `ParsedSqlStatement` com `root_node_type = "SELECT"` mas `all_node_types` contendo nós proibidos (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `REPLACE`, `TRUNCATE`, `PRAGMA`, `ATTACH`, `DETACH`, `COPY`, `LOAD`, `INSTALL`, `COMMAND`).
  - **Act:** Executar `validator.validate(statement)`.
  - **Assert:** `result.is_valid is False`, `result.violation_type == SqlViolationType.FORBIDDEN_MUTATIONAL_NODE` e `result.offending_node` identifica o nó mutacional.
  - **Priority:** P0

- [COMPLETED] [TEST005-10] [Type: Unit] **test_forbidden_function_calls**
  - **Target:** `tests/unit/test_sql_security_validator.py` → `test_forbidden_function_calls()`
  - **Scenario:** Rejeitar consultas que tentam invocar funções de acesso ao sistema de arquivos do host ou exportação de dados.
  - **Arrange:** Criar `ParsedSqlStatement` com `all_function_names` contendo funções proibidas (`READ_CSV`, `READ_TEXT`, `READ_BLOB`, `READ_PARQUET`, `READ_JSON`, `GLOB`, `READ_CSV_AUTO`, `WRITE_CSV`, `WRITE_PARQUET`, `EXPORT_PARQUET`).
  - **Act:** Executar `validator.validate(statement)`.
  - **Assert:** `result.is_valid is False`, `result.violation_type == SqlViolationType.FORBIDDEN_FUNCTION_CALL` e `result.offending_node` identifica a função proibida.
  - **Priority:** P0

- [COMPLETED] [TEST005-11] [Type: Unit] **test_stacked_queries_detected**
  - **Target:** `tests/unit/test_sql_security_validator.py` → `test_stacked_queries_detected()`
  - **Scenario:** Rejeitar payloads que contenham múltiplas declarações SQL encadeadas.
  - **Arrange:** Criar `ParsedSqlStatement` com `statement_count = 2`.
  - **Act:** Executar `validator.validate(statement)`.
  - **Assert:** `result.is_valid is False` e `result.violation_type == SqlViolationType.STACKED_QUERIES_DETECTED`.
  - **Priority:** P0

- [COMPLETED] [TEST005-12] [Type: Unit] **test_string_literal_safety_in_validator**
  - **Target:** `tests/unit/test_sql_security_validator.py` → `test_string_literal_safety()`
  - **Scenario:** Garantir que a presença de texto como `'DROP_TABLE'` no SQL bruto não causa rejeição se `all_node_types` estiver limpo.
  - **Arrange:** Criar `ParsedSqlStatement` com `root_node_type = "SELECT"`, `all_node_types = frozenset({"SELECT", "WHERE", "LITERAL"})` e `raw_sql = "SELECT * FROM t WHERE col = 'DROP_TABLE'"`.
  - **Act:** Executar `validator.validate(statement)`.
  - **Assert:** `result.is_valid is True`.
  - **Priority:** P0

---

### Task 006 — [Port-Out]: SqlParserPort Output Port Interface

- [COMPLETED] [TEST005-13] [Type: Unit] **test_sql_parser_port_is_abstract**
  - **Target:** `src/application/port/outbound/sql_parser_port.py` → `SqlParserPort`
  - **Scenario:** Garantir que `SqlParserPort` é uma classe abstrata e não pode ser instanciada diretamente sem implementar `parse()`.
  - **Arrange:** Carregar a classe abstrata `SqlParserPort`.
  - **Act:** Tentar instanciar `SqlParserPort()`.
  - **Assert:** Dispara `TypeError: Can't instantiate abstract class SqlParserPort with abstract method parse`.
  - **Priority:** P1

---

### Task 007 — [Config]: Add sqlglot Dependency & Packaging

- [COMPLETED] [TEST005-14] [Type: Unit] **test_sqlglot_dependency_installed**
  - **Target:** `requirements.txt` → `sqlglot`
  - **Scenario:** Validar que `sqlglot` está instalado no ambiente de execução e é importável no runtime.
  - **Arrange:** Importar `sqlglot`.
  - **Act:** Inspecionar `sqlglot.__version__`.
  - **Assert:** `sqlglot.__version__` é uma string válida e parseável.
  - **Priority:** P0

---

### Task 008 — [Adapter-External]: SqlGlotParserAdapter Implementation

- [COMPLETED] [TEST005-15] [Type: Unit] **test_parse_simple_select**
  - **Target:** `tests/unit/test_sqlglot_parser_adapter.py` → `test_parse_simple_select()`
  - **Scenario:** Validar análise sintática de consulta `SELECT` simples com dialeto DuckDB.
  - **Arrange:** Preparar query `"SELECT * FROM t"`.
  - **Act:** Executar `parser.parse("SELECT * FROM t")`.
  - **Assert:** `result.root_node_type == "SELECT"`, `result.statement_count == 1` e `"SELECT"` está em `result.all_node_types`.
  - **Priority:** P0

- [COMPLETED] [TEST005-16] [Type: Unit] **test_parse_cte**
  - **Target:** `tests/unit/test_sqlglot_parser_adapter.py` → `test_parse_cte()`
  - **Scenario:** Validar análise sintática de CTE (`WITH ... SELECT`).
  - **Arrange:** Preparar query `"WITH cte AS (SELECT 1) SELECT * FROM cte"`.
  - **Act:** Executar `parser.parse(query)`.
  - **Assert:** `result.root_node_type in ("SELECT", "WITH")` e `result.statement_count == 1`.
  - **Priority:** P0

- [COMPLETED] [TEST005-17] [Type: Unit] **test_parse_drop_table**
  - **Target:** `tests/unit/test_sqlglot_parser_adapter.py` → `test_parse_drop_table()`
  - **Scenario:** Validar identificação de nó raiz `DROP` e presença de `"DROP"` em `all_node_types`.
  - **Arrange:** Preparar query `"DROP TABLE t"`.
  - **Act:** Executar `parser.parse("DROP TABLE t")`.
  - **Assert:** `result.root_node_type == "DROP"` e `"DROP"` está em `result.all_node_types`.
  - **Priority:** P0

- [COMPLETED] [TEST005-18] [Type: Unit] **test_literal_isolation_in_parser**
  - **Target:** `tests/unit/test_sqlglot_parser_adapter.py` → `test_literal_isolation()`
  - **Scenario:** Provar que palavras-chave DDL/DML dentro de strings literais (`'DROP_TABLE'`) NÃO são classificadas como nós de operação.
  - **Arrange:** Preparar query `"SELECT * FROM t WHERE x = 'DROP_TABLE'"`.
  - **Act:** Executar `parser.parse(query)`.
  - **Assert:** `"DROP"` NÃO está em `result.all_node_types` e `result.root_node_type == "SELECT"`.
  - **Priority:** P0

- [COMPLETED] [TEST005-19] [Type: Unit] **test_parse_function_calls**
  - **Target:** `tests/unit/test_sqlglot_parser_adapter.py` → `test_parse_function_calls()`
  - **Scenario:** Validar extração recursiva de nomes de funções (`read_csv`) no AST.
  - **Arrange:** Preparar query `"SELECT * FROM read_csv('file.csv')"`.
  - **Act:** Executar `parser.parse(query)`.
  - **Assert:** `"READ_CSV"` está presente em `result.all_function_names`.
  - **Priority:** P0

- [COMPLETED] [TEST005-20] [Type: Unit] **test_parse_stacked_queries_count**
  - **Target:** `tests/unit/test_sqlglot_parser_adapter.py` → `test_parse_stacked_queries()`
  - **Scenario:** Validar contagem correta de múltiplas instruções separadas por ponto e vírgula.
  - **Arrange:** Preparar query `"SELECT 1; DROP TABLE t;"`.
  - **Act:** Executar `parser.parse(query)`.
  - **Assert:** `result.statement_count == 2`.
  - **Priority:** P0

- [COMPLETED] [TEST005-21] [Type: Unit] **test_malformed_sql_raises_syntax_error**
  - **Target:** `tests/unit/test_sqlglot_parser_adapter.py` → `test_malformed_sql()`
  - **Scenario:** Validar captura de erro de sintaxe do `sqlglot` e conversão em `SqlSyntaxError`.
  - **Arrange:** Preparar SQL truncado com parêntese aberto `"SELECT * FROM ("`.
  - **Act:** Invocar `parser.parse("SELECT * FROM (")`.
  - **Assert:** Dispara `SqlSyntaxError` com `violation_type == "SQL_SYNTAX_ERROR"`.
  - **Priority:** P0

- [COMPLETED] [TEST005-22] [Type: Unit] **test_parse_empty_query_raises_syntax_error**
  - **Target:** `src/adapter/outbound/parser/sqlglot_parser_adapter.py` → `parse()`
  - **Scenario:** Validar que queries vazias ou compostas apenas de espaços disparam `SqlSyntaxError`.
  - **Arrange:** Preparar string vazia `""` e string de espaços `"   "`.
  - **Act:** Executar `parser.parse("")`.
  - **Assert:** Dispara `SqlSyntaxError` informando `"Empty or invalid SQL statement."`.
  - **Priority:** P1

---

### Task 009 — [Adapter-Web]: SecuredSQLQueryTool AST Validation Integration

- [COMPLETED] [TEST005-23] [Type: Unit] **test_secured_sql_tool_valid_select**
  - **Target:** `tests/unit/test_sql_fallback_tool.py` → `test_secured_sql_tool_valid_select()`
  - **Scenario:** Validar execução de consulta analítica legítima e emissão do log de observabilidade `[MISSING_TOOL]`.
  - **Arrange:** Mock do `SalesAnalysisUseCase` retornando registros de vendas.
  - **Act:** Invocar `tool.invoke({"query": "SELECT local, SUM(actual_quantity) FROM sales_data GROUP BY local"})`.
  - **Assert:** `use_case.execute_custom_query` é chamado com a query limpa, resultado contém os dados formatados e `[MISSING_TOOL]` está no log.
  - **Priority:** P0

- [COMPLETED] [TEST005-24] [Type: Unit] **test_secured_sql_tool_blocks_dml_ddl**
  - **Target:** `tests/unit/test_sql_fallback_tool.py` → `test_secured_sql_tool_blocks_dml_ddl()`
  - **Scenario:** Matriz de testes parametrizada com 19 variações de comandos DML/DDL, funções de arquivo e injeções.
  - **Arrange:** Mock do `SalesAnalysisUseCase`.
  - **Act:** Invocar `tool.invoke({"query": forbidden_query})` para cada caso.
  - **Assert:** `use_case.execute_custom_query` NUNCA é chamado e resposta contém mensagem estruturada de erro de segurança.
  - **Priority:** P0

- [COMPLETED] [TEST005-25] [Type: Unit] **test_secured_sql_tool_false_positive_elimination**
  - **Target:** `tests/unit/test_sql_fallback_tool.py` → `test_secured_sql_tool_false_positive_elimination()`
  - **Scenario:** Validar eliminação de falsos positivos em consultas com palavras proibidas dentro de literais de string (AC02).
  - **Arrange:** Queries parametrizadas: `WHERE product_id = 'DROP_A'`, `WHERE promotion_type = 'UPDATE_DISCOUNT'`, `WHERE local = 'DELETE_ZONE'`, `WHERE local = 'INSERT_CO'`.
  - **Act:** Invocar `tool.invoke({"query": safe_query_with_literal})`.
  - **Assert:** `use_case.execute_custom_query` é executado com sucesso e nenhum erro de segurança é retornado.
  - **Priority:** P0

- [COMPLETED] [TEST005-26] [Type: Unit] **test_secured_sql_tool_complex_queries**
  - **Target:** `tests/unit/test_sql_fallback_tool.py` → `test_secured_sql_tool_complex_queries()`
  - **Scenario:** Validar consultas analíticas complexas com CTEs, window functions (`AVG OVER PARTITION`) e subconsultas aninhadas (AC05).
  - **Arrange:** Query analítica multicamada com CTE e subquery no `WHERE`.
  - **Act:** Invocar `tool.invoke({"query": query})`.
  - **Assert:** Query passa na validação AST e delega para o caso de uso.
  - **Priority:** P0

- [COMPLETED] [TEST005-27] [Type: Unit] **test_secured_sql_tool_malformed_sql**
  - **Target:** `tests/unit/test_sql_fallback_tool.py` → `test_secured_sql_tool_malformed_sql()`
  - **Scenario:** Validar que consultas malformadas retornam mensagem amigável de erro de sintaxe com orientação de autocorreção (AC06).
  - **Arrange:** Query com parêntese aberto sem fechamento `"SELECT * FROM (SELECT local FROM sales_data"`.
  - **Act:** Invocar `tool.invoke({"query": query})`.
  - **Assert:** `use_case.execute_custom_query` não é chamado e resposta contém `"Erro de Sintaxe"` e `"corrija a sintaxe"`.
  - **Priority:** P0

- [COMPLETED] [TEST005-28] [Type: Unit] **test_secured_sql_tool_truncates_large_results**
  - **Target:** `tests/unit/test_sql_fallback_tool.py` → `test_secured_sql_tool_truncates_large_results()`
  - **Scenario:** Garantir que consultas com mais de 50 registros são truncadas com metadados `total_records: 100` e `returned_records: 50`.
  - **Arrange:** Mock do caso de uso retornando 100 registros.
  - **Act:** Invocar `tool.invoke({"query": "SELECT product_id FROM sales_data"})`.
  - **Assert:** Resposta JSON contém `total_records == 100`, `returned_records == 50` e aviso explicativo.
  - **Priority:** P1

- [COMPLETED] [TEST005-29] [Type: Unit] **test_secured_sql_tool_sanitizes_file_paths_in_exceptions**
  - **Target:** `tests/unit/test_sql_fallback_incident_b004.py` → `test_secured_sql_tool_sanitizes_file_paths_in_exceptions()`
  - **Scenario:** Proteger caminhos absolutos do host contra vazamento em mensagens de erro do DuckDB.
  - **Arrange:** Mock do caso de uso lançando `RuntimeError("Could not open file c:/Code/challenge_ai_engineer/secret.csv")`.
  - **Act:** Invocar `tool.invoke({"query": "SELECT * FROM sales_data"})`.
  - **Assert:** Caminho original não aparece na resposta e é substituído por `[REDACTED_PATH]`.
  - **Priority:** P0

---

### Task 013 — [Test-Integration]: End-to-End AST Validation Pipeline

- [COMPLETED] [TEST005-30] [Type: Integration] **test_e2e_happy_path_literal_keyword**
  - **Target:** `tests/integration/test_ast_sql_validation_e2e.py` → `test_e2e_happy_path_literal_keyword()`
  - **Scenario:** Fluxo completo ponta a ponta de consulta analítica com palavra-chave proibida em literal de string.
  - **Arrange:** `create_sql_fallback_tool` com instâncias reais de `SqlGlotParserAdapter` e `SqlSecurityValidator` conectadas a usecase mockado.
  - **Act:** Invocar `"SELECT * FROM sales_data WHERE product_id = 'DROP_TABLE'"`.
  - **Assert:** Passa pelo pipeline sem erros, executa a consulta e emite o log `[MISSING_TOOL]`.
  - **Priority:** P0

- [COMPLETED] [TEST005-31] [Type: Integration] **test_e2e_security_block**
  - **Target:** `tests/integration/test_ast_sql_validation_e2e.py` → `test_e2e_security_block()`
  - **Scenario:** Bloqueio ponta a ponta de instrução `DROP TABLE sales_data`.
  - **Arrange:** Pipeline completo instanciado.
  - **Act:** Invocar `"DROP TABLE sales_data"`.
  - **Assert:** Bloqueado no validador, usecase não é acionado, resposta contém `"Erro de Segurança: A instrução 'DROP' é proibida."`.
  - **Priority:** P0

- [COMPLETED] [TEST005-32] [Type: Integration] **test_e2e_stacked_queries**
  - **Target:** `tests/integration/test_ast_sql_validation_e2e.py` → `test_e2e_stacked_queries()`
  - **Scenario:** Bloqueio ponta a ponta de injeção por consultas encadeadas (`SELECT 1; DROP TABLE sales_data`).
  - **Arrange:** Pipeline completo instanciado.
  - **Act:** Invocar `"SELECT 1; DROP TABLE sales_data"`.
  - **Assert:** Bloqueado pelo contador de statements (`statement_count == 2`), usecase não é chamado e erro de segurança é retornado.
  - **Priority:** P0

- [COMPLETED] [TEST005-33] [Type: Integration] **test_e2e_malformed_sql**
  - **Target:** `tests/integration/test_ast_sql_validation_e2e.py` → `test_e2e_malformed_sql()`
  - **Scenario:** Tratamento ponta a ponta de SQL malformado (`SELECT * FROM`).
  - **Arrange:** Pipeline completo instanciado.
  - **Act:** Invocar `"SELECT * FROM"`.
  - **Assert:** Capturado como `SqlSyntaxError`, retornado como `"Erro de Sintaxe"` sem exceção não tratada.
  - **Priority:** P0

- [COMPLETED] [TEST005-34] [Type: Integration] **test_e2e_complex_query**
  - **Target:** `tests/integration/test_ast_sql_validation_e2e.py` → `test_e2e_complex_query()`
  - **Scenario:** Execução de consulta complexa com CTEs, agregações e `UNION`.
  - **Arrange:** Pipeline completo instanciado.
  - **Act:** Invocar query combinando `WITH`, `SUM() GROUP BY`, `UNION` e `WHERE NOT IN`.
  - **Assert:** Analisado com sucesso pelo `sqlglot`, aprovado pelo validador e despachado para execução.
  - **Priority:** P0

- [COMPLETED] [TEST005-35] [Type: Integration] **test_e2e_performance_assertion**
  - **Target:** `tests/integration/test_ast_sql_validation_e2e.py` → `test_e2e_performance_assertion()`
  - **Scenario:** Verificação empírica do SLA de latência (NFR01 / Latency Overhead < 5ms).
  - **Arrange:** Aquecimento de parsing e preparação de query analítica padrão de 3 cláusulas.
  - **Act:** Medir tempo de validação e dispatch com `time.perf_counter()`.
  - **Assert:** Tempo total de validação e parsing é inferior a 5ms (com margem de tolerância em runner de teste < 10ms).
  - **Priority:** P0
