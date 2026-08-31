<!-- markdownlint-disable MD013 -->
# TEST010-golden-evals-deterministic — Test Coverage Specification

> **Source Task:** [T010-golden-evals-deterministic.md](../architecture/T010-golden-evals-deterministic.md)  
> **PRD Reference:** [R010-golden-evals-deterministic.md](../business-requirements/R010-golden-evals-deterministic.md)

## Coverage Overview

Esta especificação estabelece o plano forense e a matriz de cobertura de testes para o framework de **Avaliação Determinística com Golden Evals** (`T010-golden-evals-deterministic.md` / `R010-golden-evals-deterministic.md`). O objetivo principal é prevenir alucinações matemáticas e desvios de roteamento (*Prompt Drift*) no Agente de Análise de Vendas, interceptando os payloads estruturados intermediários retornados pelas ferramentas (`domain_tools` e `SecuredSQLQueryTool`) e aplicando asserções exatas com tolerâncias de ponto flutuante configuradas (`abs_tol=0.01` para valores monetários/quantitativos e `rel_tol=1e-3` para coeficientes/percentuais).

- **Status Geral de Cobertura:** 100% de cobertura lógica, esquemas de validação, ciclo de vida do interceptor, tolerâncias do motor de asserções, runner parametrizado e integração CI/CD mapeados para as 6 tasks da especificação T010.
- **Pirâmide de Testes:**
  - **Unitários (Dataset & Esquema Pydantic):** Validação estrita do `golden_dataset.json`, modelos `GoldenEvalRecord`, enum `GoldenEvalCategory`, validação de `expected_metrics` não vazios, whitelist `KNOWN_TOOLS` e tratamento de erros do parser `load_golden_dataset` (arquivo ausente, JSON malformado, root não-lista).
  - **Unitários (Interceptor LangChain Callback):** Validação do `ToolInterceptionCallbackHandler` nos estágios `on_tool_start`, `on_tool_end` e `on_tool_error`, suporte a payloads string/JSON, extração de conteúdo encapsulado em `ToolMessage`, rastreamento de múltiplas invocações e limpeza de estado (`clear`).
  - **Unitários (Motor de Asserções Determinísticas):** Validação exata e tolerante via `assert_metrics_match` e `compare_metric_value` cobrindo números escalares, float com tolerância absoluta/relativa, detecção de regressão fora de tolerância, estrita diferenciação de booleanos (`True != 1`), estruturas aninhadas (`dict`/`list`), campos ausentes no payload e geração de relatório diagnóstico detalhado (`format_diagnostic_report`).
  - **Integração / Harness (Pytest Runner):** Validação do ciclo completo de avaliação utilizando mock/fake LLM determinístico (`FakeToolCallingChatModel`), assertividade de roteamento de ferramentas, detecção e falha em desvio de rota (*Prompt Drift*), detecção e falha em regressão métrica, e resiliência com retry exponencial (`execute_with_retry`) contra erros transitórios de API (429, 500, 503, timeouts).
  - **Automação CI/CD (Pipeline GitHub Actions):** Validação do arquivo de workflow `.github/workflows/evals.yml`, triggers de PR/push, injeção segura de segredos de API e bloqueio de merge em caso de falha de regressão matemática.

---

## Test Checklist

### Task 001 — [Config]: Create the golden_dataset.json benchmark dataset

- [COMPLETED] [TEST010-01] [Type: Unit] **test_golden_dataset_structure_and_completeness**
  - **Target:** `tests/evals/golden_dataset.json`
  - **Scenario:** Validar que o dataset benchmark existe, contém no mínimo 10 casos de teste canônicos cobrindo todas as categorias analíticas fundamentais (REVENUE, LOGISTICS, PROMOTION, SEASONALITY, ELASTICITY).
  - **Arrange:** Localizar e carregar o arquivo `tests/evals/golden_dataset.json`.
  - **Act:** Parsear o JSON e inspecionar a quantidade de registros e presença dos campos obrigatórios (`eval_id`, `category`, `question`, `expected_tool`, `expected_metrics`).
  - **Assert:** O JSON é uma lista com $\ge 10$ registros válidos, sem campos nulos ou strings vazias, contemplando todas as categorias analíticas.
  - **Priority:** P0

---

### Task 002 — [Domain-Model]: Create GoldenEvalRecord validation models

- [COMPLETED] [TEST010-02] [Type: Unit] **test_golden_eval_record_valid_instantiation**
  - **Target:** `tests/evals/eval_models.py` → `GoldenEvalRecord`
  - **Scenario:** Validar que uma instância de `GoldenEvalRecord` é criada com sucesso quando todos os dados atendem ao contrato e schema definidos.
  - **Arrange:** Preparar dados válidos contendo `eval_id="EVAL_001_TEST"`, `category=GoldenEvalCategory.REVENUE`, `question="Qual o produto mais vendido?"`, `expected_tool="get_top_selling_product"`, `expected_metrics={"total_quantity": 280.0}`.
  - **Act:** Instanciar `GoldenEvalRecord(**valid_data)`.
  - **Assert:** Instância é criada com atributos populados corretamente e sem lançar exceção de validação Pydantic.
  - **Priority:** P0

- [COMPLETED] [TEST010-03] [Type: Unit] **test_golden_eval_record_field_validation_failures**
  - **Target:** `tests/evals/eval_models.py` → `GoldenEvalRecord` validators
  - **Scenario:** Validar que o schema rejeita campos vazios (`eval_id`, `question`), dicionário `expected_metrics` vazio ou ferramenta não cadastrada na whitelist `KNOWN_TOOLS`.
  - **Arrange:** Preparar payloads com (1) `eval_id=""`; (2) `question="   "`; (3) `expected_metrics={}`; (4) `expected_tool="unregistered_tool"`.
  - **Act:** Instanciar `GoldenEvalRecord` com cada payload defeituoso.
  - **Assert:** Cada tentativa dispara `ValueError` com mensagem indicando o campo inválido correspondente.
  - **Priority:** P0

- [COMPLETED] [TEST010-04] [Type: Unit] **test_load_golden_dataset_success_and_error_handling**
  - **Target:** `tests/evals/eval_models.py` → `load_golden_dataset()`
  - **Scenario:** Validar o carregamento do arquivo real `golden_dataset.json` e o tratamento de exceções para arquivo inexistente, JSON corrompido ou raiz não-lista.
  - **Arrange:** Preparar caminhos para: (1) arquivo canônico; (2) caminho inexistente; (3) arquivo temporário com sintaxe JSON inválida; (4) arquivo temporário com objeto dict na raiz.
  - **Act:** Invocar `load_golden_dataset()` para cada cenário.
  - **Assert:** O arquivo canônico carrega lista de registros válidos ($\ge 10$ records); caminho inexistente lança `FileNotFoundError`; JSON corrompido e raiz inválida lançam `ValueError`.
  - **Priority:** P0

---

### Task 003 — [Test-Integration]: Implement Agent Interceptor to capture tool calls

- [COMPLETED] [TEST010-05] [Type: Unit] **test_interceptor_initial_state_and_lifecycle_capture**
  - **Target:** `tests/evals/interceptor.py` → `ToolInterceptionCallbackHandler`
  - **Scenario:** Validar o estado inicial do interceptor e a captura precisa do início e término da execução da ferramenta com payload JSON serializado.
  - **Arrange:** Instanciar `ToolInterceptionCallbackHandler()`, gerar UUID de execução e preparar payload JSON `{"product_id": "Prod_B", "total_revenue": 26200.0}`.
  - **Act:** Verificar estado inicial, invocar `on_tool_start` e em seguida `on_tool_end`.
  - **Assert:** `has_invocations` torna-se `True`, `invocation_count == 1`, `actual_tool_name == "get_top_selling_product"`, e `parsed_tool_output` contém o dicionário decodificado.
  - **Priority:** P0

- [COMPLETED] [TEST010-06] [Type: Unit] **test_interceptor_tool_message_and_non_json_fallback**
  - **Target:** `tests/evals/interceptor.py` → `ToolInterceptionCallbackHandler.on_tool_end()`
  - **Scenario:** Validar que saídas encapsuladas em objetos LangChain `ToolMessage` têm seu conteúdo de texto extraído e que saídas de texto plano não-JSON não quebram o parsing.
  - **Arrange:** Instanciar handler; criar `ToolMessage(content='{"lift": 20.0}')` para o caso ToolMessage; e string pura `"Plain text result"` para o caso não-JSON.
  - **Act:** Invocar `on_tool_end` para ambos os casos.
  - **Assert:** Para `ToolMessage`, extrai `{"lift": 20.0}`; para texto puro, `parsed_tool_output` e `raw_tool_output` preservam a string original sem lançar exceção.
  - **Priority:** P1

- [COMPLETED] [TEST010-07] [Type: Unit] **test_interceptor_tool_error_and_state_reset**
  - **Target:** `tests/evals/interceptor.py` → `ToolInterceptionCallbackHandler`
  - **Scenario:** Validar captura de erros de ferramentas via `on_tool_error`, registro ordenado de múltiplas invocações e limpeza completa do estado via `clear()`.
  - **Arrange:** Instanciar handler; simular invocação 1 com erro `ValueError("Syntax Error")` e invocação 2 com sucesso.
  - **Act:** Invocar ciclo completo e em seguida chamar `handler.clear()`.
  - **Assert:** `all_invocations[0].error` armazena a mensagem de erro; antes do clear `invocation_count == 2`; após `clear()`, `has_invocations is False` e contadores zerados.
  - **Priority:** P1

---

### Task 004 — [Test-Integration]: Implement Deterministic Assertion Engine

- [COMPLETED] [TEST010-08] [Type: Unit] **test_assert_metrics_match_scalar_and_boolean_strictness**
  - **Target:** `tests/evals/assertions.py` → `assert_metrics_match()`
  - **Scenario:** Validar asserção de igualdade exata para strings, inteiros e estrita checagem booleana (garantindo que `True` não case com `1` ou `"True"`).
  - **Arrange:** Preparar pares esperados e reais para tipos escalares e booleanos.
  - **Act:** Executar `assert_metrics_match` para cenários coincidentes e divergentes.
  - **Assert:** Casos idênticos passam; booleano divergente (`has_deficit: True` vs `has_deficit: False`) ou booleano vs inteiro dispara `AssertionError`.
  - **Priority:** P0

- [COMPLETED] [TEST010-09] [Type: Unit] **test_assert_metrics_match_float_tolerances**
  - **Target:** `tests/evals/assertions.py` → `assert_metrics_match()`, `compare_metric_value()`
  - **Scenario:** Validar que divergências numéricas de float dentro das tolerâncias (`abs_tol=0.01`, `rel_tol=1e-3`) passam, enquanto desvios acima das tolerâncias disparam `AssertionError`.
  - **Arrange:** Preparar caso válido com micro-diferença (`total_revenue: 37300.0` vs `37300.005`) e caso inválido com desvio expressivo (`total_revenue: 37300.0` vs `37400.0`, delta > 37.3 sob rel_tol=1e-3).
  - **Act:** Executar asserções determinísticas.
  - **Assert:** Micro-diferença passa com sucesso; desvio fora da tolerância levanta `AssertionError` com detalhes do delta.
  - **Priority:** P0

- [COMPLETED] [TEST010-10] [Type: Unit] **test_assert_metrics_match_nested_structures_and_missing_keys**
  - **Target:** `tests/evals/assertions.py` → `assert_metrics_match()`
  - **Scenario:** Validar asserção recursiva em dicionários e listas aninhadas, além de capturar chaves ausentes no payload real.
  - **Arrange:** Preparar (1) estruturas aninhadas com métricas de localização; (2) dicionário real omitindo chave obrigatória `total_quantity`.
  - **Act:** Executar `assert_metrics_match`.
  - **Assert:** Estruturas aninhadas corretas passam; payload com chave ausente levanta `AssertionError` indicando `"Missing expected metric key 'total_quantity'"`.
  - **Priority:** P0

- [COMPLETED] [TEST010-11] [Type: Unit] **test_format_diagnostic_report_output**
  - **Target:** `tests/evals/assertions.py` → `format_diagnostic_report()`
  - **Scenario:** Validar a formatação do relatório visual de falha de avaliação diagnóstica contendo ID do teste, ferramenta esperada/executada, divergências e deltas.
  - **Arrange:** Definir `eval_id="EVAL_001"`, `expected_tool="get_top_selling_product"`, `actual_tool="get_top_selling_product"`, `mismatches=[("total_revenue", 26200.0, 25000.0, -1200.0)]`.
  - **Act:** Invocar `format_diagnostic_report()`.
  - **Assert:** String retornada contém `❌ GOLDEN EVALUATION FAILURE: EVAL_001`, seções de ferramentas, chave `total_revenue`, valores esperados/obtidos e o delta formatado.
  - **Priority:** P1

---

### Task 005 — [Test-Integration]: Implement test_golden_evals.py test runner

- [COMPLETED] [TEST010-12] [Type: Integration] **test_golden_eval_runner_canonical_flow_with_fake_llm**
  - **Target:** `tests/unit/test_golden_evals_runner.py` → `test_golden_eval_runner_passes_canonical_case`
  - **Scenario:** Validar a integração do runner determinístico simulando o agente com `FakeToolCallingChatModel` executando uma ferramenta de domínio sobre a base DuckDB hermética (`eval_dataset.csv`).
  - **Arrange:** Instanciar stack analítica (`DuckDbSalesAdapter(dataset_path=...)`, `SalesMetricsApplicationService`), configurar `FakeToolCallingChatModel` roteando para `get_top_selling_product`, e instanciar `ToolInterceptionCallbackHandler`.
  - **Act:** Invocar `agent.ask("Qual o produto mais vendido?", callbacks=[interceptor])` e aplicar asserções.
  - **Assert:** Interceptor captura execução de `get_top_selling_product`, payload retornado contém métricas reais da base fixture (`Prod_B`, `total_quantity=280.0`, `total_revenue=26200.0`), e asserção passa.
  - **Priority:** P0

- [COMPLETED] [TEST010-13] [Type: Integration] **test_golden_eval_runner_detects_prompt_drift_and_routing_mismatch**
  - **Target:** `tests/unit/test_golden_evals_runner.py` → `test_golden_eval_runner_catches_routing_mismatch`
  - **Scenario:** Validar que o framework de avaliação detecta e falha imediatamente quando o agente desvia da ferramenta esperada (*Prompt Drift*), chamando por exemplo `secured_sql_query` em vez de `get_top_selling_product`.
  - **Arrange:** Configurar `FakeToolCallingChatModel` para rotear incorretamente para `secured_sql_query`.
  - **Act:** Executar pergunta do benchmark contra o agente e inspecionar ferramenta interceptada.
  - **Assert:** `interceptor.actual_tool_name != record.expected_tool`, comprovando a detecção do desvio de rota agêntico.
  - **Priority:** P0

- [COMPLETED] [TEST010-14] [Type: Integration] **test_golden_eval_runner_detects_metric_regression**
  - **Target:** `tests/unit/test_golden_evals_runner.py` → `test_golden_eval_runner_catches_metric_regression`
  - **Scenario:** Validar que o framework dispara falha estruturada com relatório diagnóstico quando o valor retornado pela ferramenta diverge do gabarito matemático.
  - **Arrange:** Configurar registro com expectativa divergente (`total_revenue: 99999.0` quando o real é `26200.0`).
  - **Act:** Executar fluxo do agente e submeter payload ao motor de asserções.
  - **Assert:** Dispara `AssertionError` contendo `GOLDEN EVALUATION FAILURE` e detalhes do delta entre o valor esperado e o calculado pelo DuckDB.
  - **Priority:** P0

- [COMPLETED] [TEST010-15] [Type: Unit] **test_golden_eval_retry_mechanism_on_transient_errors**
  - **Target:** `tests/evals/test_golden_evals.py` → `execute_with_retry()`
  - **Scenario:** Validar que o wrapper de retry recupera chamadas que sofrem com erros transitórios de API (429 Rate Limit, 500, 503, connection timeouts) com backoff exponencial e re-lança exceções persistentes após esgotar tentativas.
  - **Arrange:** Criar mock de função que (1) falha 2 vezes com `Exception("429 Too Many Requests")` e tem sucesso na 3ª; (2) falha constantemente com erro 429; (3) falha imediatamente com erro não-transitório `ValueError("Permanent error")`.
  - **Act:** Executar `execute_with_retry(fn, max_retries=3, base_delay=0.01)` para os 3 cenários.
  - **Assert:** Cenário (1) completa com sucesso na 3ª tentativa; Cenário (2) esgota retries e lança a exceção 429; Cenário (3) lança `ValueError` imediatamente sem retentativas desnecessárias.
  - **Priority:** P1

---

### Task 006 — [Adapter-Infra]: Integrate Golden Evals into GitHub Actions workflow

- [COMPLETED] [TEST010-16] [Type: Integration] **test_github_actions_workflow_specification**
  - **Target:** `.github/workflows/evals.yml`
  - **Scenario:** Validar que a especificação de CI/CD para Golden Evals existe, possui sintaxe YAML válida, configura os triggers adequados (`push`, `pull_request`), define timeout de segurança e executa a suíte de avaliação com injeção de credenciais seguras.
  - **Arrange:** Ler o arquivo `.github/workflows/evals.yml`.
  - **Act:** Validar a estrutura YAML e inspecionar steps de instalação e execução (`pytest tests/evals/test_golden_evals.py`).
  - **Assert:** O workflow define job com `timeout-minutes: 10`, configura Python 3.11 com cache de pip, e injeta `OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}` no step de execução.
  - **Priority:** P0
