# S010-golden-evals-deterministic — Security Audit

> **Source Task:** [T010-golden-evals-deterministic.md](../architecture/T010-golden-evals-deterministic.md)  
> **PRD Reference:** [R010-golden-evals-deterministic.md](../business-requirements/R010-golden-evals-deterministic.md)  
> **Test Coverage:** [TEST010-golden-evals-deterministic.md](../tests/TEST010-golden-evals-deterministic.md)

## Security Overview

A auditoria de segurança da especificação técnica de **Avaliação Determinística com Golden Evals** (`T010-golden-evals-deterministic.md` / `R010-golden-evals-deterministic.md`) avaliou a postura de segurança e resiliência da suíte de benchmarking automatizado do Agente de Análise de Vendas. A análise foi conduzida sob as diretrizes do **OWASP Top 10 for LLM Applications (LLM01: Prompt Injection, LLM04: Model Denial of Service, LLM06: Sensitive Information Disclosure, LLM10: Unbounded Consumption)**, **OWASP ASVS V5 (Validation and Sanitization)**, **CWE-522 (Insufficiently Protected Credentials)**, **CWE-400 (Uncontrolled Resource Consumption)** e **CWE-209 (Generation of Error Message Containing Sensitive Information)**.

O framework de Golden Evals atua interceptando payloads estruturados de ferramentas intermediárias antes da síntese em linguagem natural, garantindo 100% de determinismo matemático e eliminando alucinações e *Prompt Drift*. Os seguintes pilares de segurança foram auditados:

1. **Gestão Segura de Credenciais e Segredos de CI/CD (CWE-522 / OWASP LLM06):** Injeção controlada de chaves de API (`OPENAI_API_KEY`) no pipeline GitHub Actions (`.github/workflows/evals.yml`) exclusivamente via `secrets.OPENAI_API_KEY`, com isolamento de contexto e skip limpo em ambientes de desenvolvimento sem chaves configuradas.
2. **Isolamento Hermético de Dados e Prevenção de Vazamento de Produção (CWE-200 / OWASP LLM06):** Execução estrita contra dataset fixo e versionado em `tests/fixtures/eval_dataset.csv` sobre DuckDB em memória (`:memory:`), garantindo que as rotinas de avaliação nunca interajam com bancos de dados produtivos ou persistam dados voláteis.
3. **Prevenção de Negação de Serviço e Exaustão de Orçamento de Tokens (OWASP LLM04 / OWASP LLM10 / CWE-400):** Implementação de limites estritos de retentativa (`max_retries=3`) com backoff exponencial contra códigos transitórios de erro (429, 500, 503, timeouts), timeout estrito de 10 minutos no job de CI e limitação do tamanho do dataset para execução rápida (< 60s).
4. **Validação Defensiva e Integridade do Dataset Benchmark (CWE-20 / CWE-1287 / OWASP LLM01):** Modelagem rigorosa via Pydantic (`GoldenEvalRecord`) com whitelist estrita de ferramentas (`KNOWN_TOOLS`), rejeição de strings vazias, tipagem estrita de categorias e validação de schema antes da execução agêntica.
5. **Sanitização de Relatórios Diagnósticos e Prevenção de Log Forging (CWE-209 / CWE-117):** Formatação segura de relatórios de falha (`format_diagnostic_report`), assegurando que variáveis de ambiente, caminhos absolutos locais ou credenciais nunca sejam impressos em logs de CI.

---

## Vulnerability Log

| ID | Vulnerability / Security Control | Severity | Risk | Impact |
| :--- | :--- | :--- | :--- | :--- |
| S010-01 | Unbounded API Retries & CI Token Budget Exhaustion (DoS) | Medium | Medium x High | Loop de retentativas descontrolado consumindo tokens de API e excedendo limites de faturamento no provedor LLM. |
| S010-02 | Unsanitized Diagnostic Failure Reports & Secret Disclosure in CI Logs | Medium | Medium x Medium | Exposição de credenciais, tokens de autenticação ou variáveis de ambiente em logs públicos do GitHub Actions após falhas de asserção. |
| S010-03 | Production Data Pollution via Unrestricted Dataset Path Binding | High | Low x High | Execução acidental da suíte de avaliação contra bases de dados transacionais ou arquivos de dados reais de clientes. |
| S010-04 | Malicious Tool Name Injection & Schema Tampering in Golden Dataset | Low | Low x Medium | Inclusão de nomes de ferramentas não registradas ou estruturas JSON malformadas causando falhas silenciosas ou comportamentos inesperados. |

---

## Refinement Tasks

### Task 001 — Create the golden_dataset.json benchmark dataset

- [COMPLETED] [S010-04] [Low] **Validação Defensiva de Integridade e Whitelist de Ferramentas no Dataset**
  - **Location:** `tests/evals/golden_dataset.json` / `tests/evals/eval_models.py` → `GoldenEvalRecord`
  - **Risk:** Alterações não auditadas no arquivo JSON podem introduzir casos de teste com nomes de ferramentas inválidas ou payloads manipulados, resultando em falsos positivos ou mascaramento de falhas de segurança.
  - **Fix:** Validar no modelo `GoldenEvalRecord` que todas as entradas pertencem ao conjunto estrito `KNOWN_TOOLS` e que nenhuma chave de métrica esperada possui valores nulos ou indeterminados.
  - **Validation:** Executar `test_golden_eval_record_field_validation_failures` garantindo a rejeição imediata de ferramentas desconhecidas.

---

### Task 004 — Implement Deterministic Assertion Engine

- [COMPLETED] [S010-02] [Medium] **Sanitização de Relatórios Diagnósticos e Prevenção de Log Forging**
  - **Location:** `tests/evals/assertions.py` → `format_diagnostic_report()`
  - **Risk:** Na ocorrência de discrepâncias de valores ou erros nas ferramentas, o relatório impresso pode conter strings brutas com caracteres de controle CRLF ou mensagens de erro do sistema de arquivos local contendo caminhos sensíveis.
  - **Fix:** Assegurar que `format_diagnostic_report` sanitiza strings e payloads brutos, suprimindo caminhos absolutos locais (`[REDACTED_PATH]`) e limitando o tamanho máximo de exibição de payloads textuais nos logs de CI.
  - **Validation:** Executar asserções com payloads simulando mensagens de erro com paths locais e verificar que a saída impressa no relatório não expõe o caminho do host.

---

### Task 005 — Implement test_golden_evals.py test runner

- [COMPLETED] [S010-01] [Medium] **Mitigação de Exaustão de Recursos com Limites Rígidos de Retentativa e Timeout**
  - **Location:** `tests/evals/test_golden_evals.py` → `execute_with_retry()`
  - **Risk:** Erros persistentes de concorrência ou 429 Rate Limits podem travar o pipeline ou esgotar a cota de tokens da organização caso não haja um limite superior de tentativas e um backoff delimitado.
  - **Fix:** Fixar `max_retries=3` com atraso máximo delimitado (`base_delay=2.0`), filtrando estritamente exceções identificadas como transitórias e abortando imediatamente em exceções permanentes (ex: 401 Unauthorized, 403 Forbidden).
  - **Validation:** Executar `test_golden_eval_retry_mechanism_on_transient_errors` e validar recuperação em 3 tentativas e falha rápida em erros permanentes.

- [COMPLETED] [S010-03] [High] **Garantia de Isolamento Hermético do Dataset de Avaliação**
  - **Location:** `tests/evals/test_golden_evals.py` → `eval_agent` fixture
  - **Risk:** Se o caminho do dataset não for explicitamente fixado no arquivo fixture isolado (`tests/fixtures/eval_dataset.csv`), a suíte pode acidentalmente ler ou modificar dados de produção ou de staging.
  - **Fix:** Configurar a fixture `eval_agent` para validar a existência de `tests/fixtures/eval_dataset.csv` e instanciar o `DuckDbSalesAdapter` com banco de dados em memória `:memory:`, impedindo qualquer persistência em disco.
  - **Validation:** Inspecionar a fixture de testes para certificar que o adapter utiliza conexão in-memory e dataset isolado.

---

### Task 006 — Integrate Golden Evals into GitHub Actions workflow

- [COMPLETED] [S010-05] [Low] **Proteção de Segredos e Isolamento de Execução no Pipeline CI/CD**
  - **Location:** `.github/workflows/evals.yml`
  - **Risk:** Execução de pull requests públicos (forks) com segredos de API expostos pode levar a vazamento de credenciais do provedor LLM.
  - **Fix:** Garantir que o workflow defina `timeout-minutes: 10` e que a injeção do segredo `OPENAI_API_KEY` ocorra estritamente no step de execução dos testes de avaliação, sem expor chaves em variáveis de ambiente globais de steps de build/setup.
  - **Validation:** Auditar a sintaxe e a hierarquia do arquivo `.github/workflows/evals.yml`.
