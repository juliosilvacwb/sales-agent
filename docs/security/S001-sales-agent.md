# S001-sales-agent — Security Audit

> **Source Task:** [T001-sales-agent.md](../architecture/T001-sales-agent.md)

## Security Overview

O Sales Data Analysis Agent foi avaliado sob a ótica de Segurança da Informação, SAST (Static Application Security Testing), DAST (Dynamic Application Security Testing), segurança de IA/LLM (OWASP Top 10 for LLMs) e arquitetura de dados (DuckDB).

### Pontos Positivos Identificados

- **Isolamento Hexagonal:** O núcleo de domínio (`domain/` e `application/`) é 100% determinístico e desacoplado de bibliotecas externas e agentes generativos, eliminando riscos de manipulação matemática por alucinações de IA.
- **Parametrização de Consultas:** As consultas no `DuckDbSalesAdapter` utilizam queries parametrizadas (`?`) para filtros dinâmicos.
- **Execução Containerizada não-root:** O `Dockerfile` define e executa a aplicação com usuário não-privilegiado `appuser` (UID 1000).
- **Gestão de Segredos:** O `.gitignore` ignora adequadamente arquivos `.env`, bancos de dados e caches locais.
- **Bloqueio DDL/DML Inicial:** A ferramenta `SecuredSQLQueryTool` intercepta e rejeita comandos de mutação como `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`.

### Riscos Identificados e Oportunidades de Refinamento

1. **Leitura Arbitrária de Arquivos via DuckDB (OWASP LLM02 / Insecure Output Handling & Indirect Prompt Injection):** Funções nativas de leitura do DuckDB (`read_csv`, `read_text`, `glob`) não estavam explicitamente na lista de palavras proibidas nem desabilitadas no nível do motor DuckDB, permitindo potencial exfiltração de arquivos locais através de instruções `SELECT` geradas via prompt injection.
2. **Resiliência e Suporte a Padrões de Data (Padrão Brasileiro DD/MM/YYYY e ISO YYYY-MM-DD):** Falta de suporte ou tratamento de exceções para conversão de datas nos formatos brasileiro (`DD/MM/YYYY`) e ISO (`YYYY-MM-DD`), além de ausência de limites numéricos para parâmetros como `limit`.
3. **Gerenciamento de Janela de Memória Conversacional:** Histórico de chat ilimitado no `SalesAgent`, que pode acarretar estouro de contexto e custos excessivos em sessões longas.

---

## Vulnerability Log

| ID | Vulnerability | Severity | Risk | Impact |
| :--- | :--- | :--- | :--- | :--- |
| S001-01 | Arbitrary File Read / Data Exfiltration via DuckDB Functions | High | Medium x High | Exfiltração de variáveis de ambiente, arquivos `.env` ou arquivos do sistema via `SELECT` |
| S001-02 | Unhandled Date Format Parsing & Brazilian Date Support (DD/MM/YYYY) | Medium | Medium x Medium | Quebra de execução do agente ao receber formatos de data brasileiros (`DD/MM/YYYY`) ou strings inválidas |
| S001-03 | Unbounded Parameter Limit (Resource Exhaustion / DoS) | Medium | Medium x Low | Consumo excessivo de memória ou respostas volumosas com `limit` arbitrário |
| S001-04 | Unbounded Chat History Growth (Context Window & Cost Exhaustion) | Low | Low x Medium | Degradação de latência, overflow de contexto de tokens e aumento de custo |
| S001-05 | Ingestion Path Special Character / Traversal Resilience | Low | Low x Low | Possíveis falhas na inicialização do schema com caracteres especiais no path |

---

## Refinement Tasks

### Task 010 - [Adapter-LLM] SecuredSQLQueryTool and Persistence Hardening

- [x] [S001-01] [High] **Arbitrary File Read / Data Exfiltration via DuckDB Functions**
  - **Location:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `FORBIDDEN_KEYWORDS` & `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `__init__()`
  - **Risk:** Instruções `SELECT` legítimas contendo funções nativas como `read_text('.env')`, `read_csv('/etc/passwd')` ou `glob('*')` poderiam contornar o filtro de comandos DML/DDL e expor arquivos confidenciais do servidor/container.
  - **Fix:**
    1. Adicionar à lista `FORBIDDEN_KEYWORDS` as funções de acesso ao sistema de arquivos e extensões: `READ_CSV`, `READ_TEXT`, `READ_BLOB`, `READ_PARQUET`, `READ_JSON`, `GLOB`, `INSTALL`, `LOAD`, `ATTACH`, `DETACH`, `COPY`, `EXPORT`, `IMPORT`, `SYSTEM`, `WRITE_PARQUET`, `WRITE_CSV`.
    2. Configurar o DuckDB no `DuckDbSalesAdapter` com `config={"enable_external_access": "false"}` (ou executar `SET enable_external_access=false;`) após o carregamento inicial do CSV, desabilitando o acesso externo no nível do engine.
  - **Validation:** Testar que consultas contendo `SELECT * FROM read_text('.env')` ou `SELECT * FROM glob('*')` são categoricamente rejeitadas pela ferramenta e/ou bloqueadas pelo DuckDB.

---

### Task 009 - [Adapter-LLM] LangChain Domain Tools Input Validation & Date Parsing

- [x] [S001-02] [Medium] **Unhandled Date Format Parsing & Brazilian Date Format Support**
  - **Location:** `src/adapter/inbound/llm/domain_tools.py` → `_parse_date()` & `get_total_sales_in_period()`
  - **Risk:** Usuários brasileiros e agentes LLM frequentemente utilizam datas no formato padrão brasileiro `DD/MM/YYYY` (ex: `01/01/2023`, `31/12/2023`) ou strings arbitrárias. Se a ferramenta utilizar apenas `date.fromisoformat` sem tratamento, datas em formato brasileiro causarão falhas e exceções `ValueError` não capturadas, interrompendo a interação do agente.
  - **Fix:**
    1. Implementar parser de datas resiliente que suporte explicitamente o formato brasileiro (`DD/MM/YYYY`, `DD-MM-YYYY`) com prioridade e o formato ISO (`YYYY-MM-DD`).
    2. Tratar `ValueError` capturando exceções de formatos não reconhecidos e retornar mensagem estruturada orientando os formatos aceitos (`DD/MM/YYYY` ou `YYYY-MM-DD`).
  - **Validation:** Testes unitários validando: (a) parsing correto de datas brasileiras `DD/MM/YYYY`, (b) parsing de datas ISO `YYYY-MM-DD`, e (c) resposta amigável com mensagem de erro sem lançar exceção não tratada ao receber entradas inválidas.

- [x] [S001-03] [Medium] **Unbounded Parameter Limit (Resource Exhaustion / DoS)**
  - **Location:** `src/adapter/inbound/llm/domain_tools.py` → `get_top_locations_by_volume()`
  - **Risk:** Parâmetros `limit` negativos ou excessivamente grandes (ex: `1000000`) podem causar respostas gigantescas ou comportamento imprevisto no slice de ordenação.
  - **Fix:** Normalizar o parâmetro `limit` com limites seguros, por exemplo: `max(1, min(int(limit), 100))`.
  - **Validation:** Teste unitário com `limit=-10` e `limit=99999` garante que a tool retorne dados limitados dentro da faixa válida.

---

### Task 012 - [Adapter-Web/CLI] Conversational Memory Management

- [x] [S001-04] [Low] **Unbounded Chat History Growth (Context Window & Cost Exhaustion)**
  - **Location:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent`
  - **Risk:** A lista `_chat_history` acumula todas as interações indefinidamente, o que pode esgotar a janela de contexto de tokens do LLM ou elevar exponencialmente o custo da API em conversas longas.
  - **Fix:** Implementar truncamento ou janela deslizante (ex: reter no máximo as últimas 10 ou 20 mensagens) ou encapsular em `ConversationBufferWindowMemory`.
  - **Validation:** Teste automatizado com múltiplas invocações consecutivas verifica que o histórico mantém apenas as mensagens mais recentes dentro do limite estipulado.

---

### Task 008 - [Adapter-Persistence] Ingestion Path Sanitization

- [x] [S001-05] [Low] **Dataset File Path Special Character Sanitization**
  - **Location:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `_initialize_schema()`
  - **Risk:** Interpolação direta do caminho do arquivo em string SQL `f"... '{normalized_path}' ..."` pode falhar caso o caminho do dataset contenha aspas simples ou caracteres especiais.
  - **Fix:** Escapar aspas simples no path ou validar a estrutura do arquivo antes da interpolação na query de inicialização.
  - **Validation:** Testar inicialização com paths contendo caracteres escapados e validar carregamento sem erros.
