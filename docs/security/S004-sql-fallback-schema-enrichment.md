# S004-sql-fallback-schema-enrichment — Auditoria de Segurança

> **Tarefa de Origem:** [B004-sql-fallback-schema-enrichment.md](../incidents/B004-sql-fallback-schema-enrichment.md)

## Visão Geral de Segurança

Análise de segurança do enriquecimento de esquema da `SecuredSQLQueryTool`, mecanismos de proteção contra DML/DDL, resiliência a injeção de prompt e tratamento de payload estruturado de resultado vazio.

## Registro de Vulnerabilidades

| ID | Vulnerabilidade | Severidade | Risco | Impacto |
| :--- | :--- | :--- | :--- | :--- |
| S004-01 | Vazamento de Caminho Interno / Erro de Sistema no Tratamento de Exceções | Baixo | Baixo x Baixo | Divulgação menor de informações sobre caminhos do ambiente local em strings de exceção brutas do DuckDB. |
| S004-02 | Risco de Burlar com Consultas Empilhadas Usando Ponto e Vírgula | Baixo | Baixo x Baixo | Potencial execução de múltiplas consultas se pontos e vírgulas internos não forem tratados. |

## Tarefas de Refinamento

### Task 002 — Enriquecer descrições de esquema do SQLQueryInput e SecuredSQLQueryTool

- [COMPLETED] [S004-01] [Baixo] **Sanitização de Caminho de Erro Interno**
  - **Localização:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SecuredSQLQueryTool._run()`
  - **Risco:** Mensagens de exceção brutas do DuckDB no bloco catch `return f"Erro ao executar a consulta SQL: {str(e)}"` poderiam divulgar caminhos de arquivos do sistema.
  - **Correção:** Higienizar a mensagem de exceção para remover detalhes de caminhos do sistema de arquivos antes de retornar ao agente LLM.
  - **Validação:** Teste unitário verificando que a mensagem de exceção não divulga a string completa do caminho do diretório local.

### Task 003 — Payload de aviso estruturado para conjuntos de resultados vazios

- [COMPLETED] [S004-02] [Baixo] **Verificação de Ponto e Vírgula em Consultas Empilhadas**
  - **Localização:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SecuredSQLQueryTool._run()`
  - **Risco:** Pontos e vírgulas (`;`) intermediários em consultas personalizadas poderiam permitir tentativas de execução de consultas empilhadas.
  - **Correção:** Rejeitar consultas contendo pontos e vírgulas internos (`;`) após remover espaços em branco e ponto e vírgula finais.
  - **Validação:** Teste unitário tentando `SELECT 1; SELECT 2` verificando a rejeição da requisição.
