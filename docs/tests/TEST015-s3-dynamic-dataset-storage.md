<!-- markdownlint-disable MD013 -->
# TEST015-s3-dynamic-dataset-storage — Test Coverage Specification

> **Source Task:** [T015-s3-dynamic-dataset-storage.md](../architecture/T015-s3-dynamic-dataset-storage.md)  
> **PRD Reference:** [R015-s3-dynamic-dataset-storage.md](../business-requirements/R015-s3-dynamic-dataset-storage.md)  
> **Product Strategy:** [PS015-s3-dynamic-dataset-storage.md](../product-strategy/PS015-s3-dynamic-dataset-storage.md)

## Coverage Overview

Esta especificação estabelece o plano forense e a matriz de cobertura de testes para a funcionalidade de **Armazenamento Dinâmico e Consulta Remota Direta S3 com Zero-Copy** (`T015-s3-dynamic-dataset-storage.md` / `R015-s3-dynamic-dataset-storage.md`). O objetivo central é assegurar que o adaptador de persistência `DuckDbSalesAdapter` suporte streaming analítico via extensão nativa `httpfs` contra URIs `s3://` com consumo de memória bounded (sub-512MB), preservando 100% de retrocompatibilidade com arquivos CSV locais, injeção segura de credenciais AWS (12-Factor / K8s Secrets), fallback resiliente com schema canônico em caso de indisponibilidade ou falha de autenticação (HTTP 403/404/Timeout), e conformidade estrita com a Arquitetura Hexagonal.

- **Status Geral de Cobertura:** 100% de cobertura lógica, contratos de domínio, extensão DuckDB `httpfs`, injeção de credenciais, degradação graciosa, controle condicional de acesso externo, testes de regressão local e suítes de integração E2E para todas as 16 tarefas da especificação T015.
- **Pirâmide de Testes:**
  - **Unitários (Exceções de Domínio - Fase 1):** Validação da exceção pura `S3ConnectionError` em `src/domain/exception/s3_exceptions.py`, testando instanciação com mensagem, código de status HTTP opcional (ex: 403, 404), herança de `Exception` e desacoplamento total de frameworks ou SDKs externos (Task 001).
  - **Unitários (Contrato de Porta - Fase 2):** Verificação de compatibilidade da interface abstrata `SalesDataPort` em `src/application/port/outbound/sales_data_port.py`, assegurando que nenhuma assinatura de método foi alterada e que `DuckDbSalesAdapter` implementa fielmente todos os métodos abstratos (Task 002).
  - **Unitários (Autodetecção de Esquema URI e Extensão httpfs - Fase 3):** Validação de detecção de esquemas `s3://` (case-insensitive) vs caminhos locais absolutos/relativos, invocação das instruções SQL `INSTALL httpfs;` e `LOAD httpfs;` no DuckDB apenas em modo S3 (Task 003).
  - **Unitários (Configuração Segura de Credenciais AWS - Fase 3):** Validação do método `_configure_s3_credentials()`, verificando comandos `SET s3_region`, `SET s3_access_key_id`, `SET s3_secret_access_key`, `SET s3_session_token`, `SET s3_endpoint`, `SET s3_use_ssl`, fallback para `AWS_DEFAULT_REGION`, lançamento de `S3ConnectionError` (403) quando chaves obrigatórias estão ausentes e não-exposição de segredos em logs (Task 004).
  - **Unitários (Criação de VIEW S3 e Degradação Graciosa - Fase 3):** Validação da query `CREATE VIEW IF NOT EXISTS sales_data AS SELECT ... FROM read_csv_auto('s3://...')`, casting de tipos canônicos, escape de aspas simples em URIs, e captura resiliente de erros DuckDB (403 Forbidden, 404 Not Found, Timeout) com fallback para schema vazio sem crash da aplicação (Task 005).
  - **Unitários (Controle Condicional de Acesso Externo - Fase 3):** Validação de segurança verificando que `SET enable_external_access = false;` é executado exclusivamente em modo local, enquanto no modo S3 o acesso externo permanece ativo para permitir queries de streaming (Task 006).
  - **Unitários (Validação de Configuração e Infraestrutura - Fase 3):** Inspeção estática e estrutural de `.env.example`, manifestos K8s (`k8s/configmap.yaml`, `k8s/secrets.example.yaml`, `k8s/app-deployment.yaml`) e `Dockerfile` para suporte S3 sem obrigatoriedade de arquivo local (Tasks 007, 008, 009).
  - **Unitários (Suítes de Testes Dedicadas - Fase 4):** Validação das suítes de teste unitárias `test_s3_uri_detection.py`, `test_s3_credential_config.py`, `test_s3_graceful_degradation.py`, `test_s3_external_access.py` e `test_s3_backward_compatibility.py` (Tasks 010, 011, 012, 013, 014).
  - **Integração / E2E (Consultas e Profiling Remoto S3 - Fase 4):** Validação de execução de ponta a ponta de todas as 10 agregações analíticas, queries SQL read-only e profiling dinâmico de dataset contra S3 com skip condicional gracioso em ambientes sem credenciais AWS (Tasks 015, 016).

---

## Test Checklist

### Task 001 — [Domain-Exception]: Create S3ConnectionError domain exception

- [COMPLETED] [TEST015-01] [Type: Unit] **test_s3_connection_error_instantiation_default_status_code**
  - **Target:** `src/domain/exception/s3_exceptions.py` → `S3ConnectionError`
  - **Scenario:** Validar que `S3ConnectionError` pode ser instanciada apenas com mensagem descritiva, mantendo `status_code` padrão como `None`.
  - **Arrange:** Definir mensagem de erro `"Failed to connect to S3 endpoint"`.
  - **Act:** Instanciar `exc = S3ConnectionError(message="Failed to connect to S3 endpoint")`.
  - **Assert:** `exc.message == "Failed to connect to S3 endpoint"`, `exc.status_code is None`, e `str(exc) == "Failed to connect to S3 endpoint"`.
  - **Priority:** P0

- [COMPLETED] [TEST015-02] [Type: Unit] **test_s3_connection_error_with_custom_status_code**
  - **Target:** `src/domain/exception/s3_exceptions.py` → `S3ConnectionError`
  - **Scenario:** Validar que `S3ConnectionError` aceita códigos de status HTTP explícitos (ex: 403 Forbidden, 404 Not Found).
  - **Arrange:** Definir mensagem `"Access Denied"` e status code `403`.
  - **Act:** Instanciar `exc = S3ConnectionError(message="Access Denied", status_code=403)`.
  - **Assert:** `exc.message == "Access Denied"` e `exc.status_code == 403`.
  - **Priority:** P0

- [COMPLETED] [TEST015-03] [Type: Unit] **test_s3_connection_error_is_exception_subclass**
  - **Target:** `src/domain/exception/s3_exceptions.py` → `S3ConnectionError`
  - **Scenario:** Validar que `S3ConnectionError` herda diretamente da classe base `Exception` do Python sem dependência de bibliotecas externas.
  - **Arrange:** Obter classe `S3ConnectionError`.
  - **Act:** Inspecionar `issubclass(S3ConnectionError, Exception)`.
  - **Assert:** Retorna `True` e módulo não contém imports de frameworks externos.
  - **Priority:** P1

---

### Task 002 — [Port-Out]: Verify SalesDataPort interface compatibility

- [COMPLETED] [TEST015-04] [Type: Unit] **test_sales_data_port_interface_signatures_unchanged**
  - **Target:** `src/application/port/outbound/sales_data_port.py` → `SalesDataPort`
  - **Scenario:** Validar que a interface abstrata `SalesDataPort` preserva todas as assinaturas de métodos (10 agregações, `execute_read_only_query`, `get_sales_by_filter`, `profile_dataset`) sem acoplamento a S3 ou DuckDB.
  - **Arrange:** Inspecionar métodos abstratos de `SalesDataPort`.
  - **Act:** Verificar assinaturas de `profile_dataset`, `aggregate_top_selling_product`, `aggregate_total_sales`, etc.
  - **Assert:** Todas as assinaturas utilizam exclusivamente tipos de domínio e tipos primitivos padrão do Python.
  - **Priority:** P0

- [COMPLETED] [TEST015-05] [Type: Unit] **test_sales_data_port_duckdb_adapter_subclass_compliance**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter`
  - **Scenario:** Validar que `DuckDbSalesAdapter` implementa fielmente todos os métodos abstratos exigidos por `SalesDataPort`.
  - **Arrange:** Inspecionar hierarquia de classes.
  - **Act:** Verificar `issubclass(DuckDbSalesAdapter, SalesDataPort)`.
  - **Assert:** Retorna `True` e `DuckDbSalesAdapter` pode ser instanciada sem `TypeError` de métodos abstratos pendentes.
  - **Priority:** P0

---

### Task 003 — [Adapter-Persistence]: Implement S3 URI detection and httpfs extension management

- [COMPLETED] [TEST015-06] [Type: Unit] **test_s3_uri_detection_schemes_case_insensitivity**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter.__init__()`
  - **Scenario:** Validar que URIs iniciadas por `s3://`, `S3://`, `s3://bucket/path/data.csv` e `S3://BUCKET/KEY.CSV` ativam `_is_s3 = True`.
  - **Arrange:** Testar variações de URIs remotas.
  - **Act:** Avaliar expressão de verificação de prefixo S3.
  - **Assert:** Todas as variantes S3 resultam em `_is_s3 == True`.
  - **Priority:** P0

- [COMPLETED] [TEST015-07] [Type: Unit] **test_local_paths_absolute_and_relative_not_s3**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter.__init__()`
  - **Scenario:** Validar que caminhos locais como `/app/dataset/sales.csv`, `dataset/sales.csv`, `C:/data/sales.csv` e `file:///data.csv` resultam em `_is_s3 == False`.
  - **Arrange:** Definir lista de caminhos locais variados.
  - **Act:** Instanciar/avaliar `_is_s3` no adaptador para cada caminho.
  - **Assert:** Todos os caminhos retornam `_is_s3 == False`.
  - **Priority:** P0

- [COMPLETED] [TEST015-08] [Type: Unit] **test_httpfs_extension_install_and_load_invoked_in_s3_mode**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._initialize_s3_schema()`
  - **Scenario:** Validar que em modo S3 as instruções `INSTALL httpfs;` e `LOAD httpfs;` são executadas no DuckDB antes de qualquer consulta.
  - **Arrange:** Mockar conexão DuckDB e configurar `dataset_path="s3://bucket/sales.csv"` com credenciais válidas.
  - **Act:** Executar `_initialize_schema()`.
  - **Assert:** Lista de comandos executados contém `"INSTALL httpfs;"` e `"LOAD httpfs;"`.
  - **Priority:** P0

- [COMPLETED] [TEST015-09] [Type: Unit] **test_httpfs_extension_not_invoked_in_local_mode**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._initialize_local_schema()`
  - **Scenario:** Validar que em modo local a extensão `httpfs` não é instalada nem carregada, preservando a inicialização rápida offline.
  - **Arrange:** Mockar conexão DuckDB com caminho de arquivo CSV local temporário.
  - **Act:** Executar `_initialize_schema()`.
  - **Assert:** Comandos executados não contêm `"INSTALL httpfs"` nem `"LOAD httpfs"`.
  - **Priority:** P1

---

### Task 004 — [Adapter-Persistence]: Implement AWS credential configuration

- [COMPLETED] [TEST015-10] [Type: Unit] **test_aws_credentials_mandatory_keys_injected**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._configure_s3_credentials()`
  - **Scenario:** Validar que `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` e `AWS_REGION` do ambiente são injetados no DuckDB via `SET s3_...`.
  - **Arrange:** Mockar conexão DuckDB e definir variáveis de ambiente `AWS_ACCESS_KEY_ID="AKIA_TEST"`, `AWS_SECRET_ACCESS_KEY="SECRET_TEST"`, `AWS_REGION="sa-east-1"`.
  - **Act:** Invocar `_configure_s3_credentials()`.
  - **Assert:** Comandos `SET s3_region = 'sa-east-1';`, `SET s3_access_key_id = 'AKIA_TEST';` e `SET s3_secret_access_key = 'SECRET_TEST';` são executados.
  - **Priority:** P0

- [COMPLETED] [TEST015-11] [Type: Unit] **test_aws_credentials_missing_access_key_raises_s3_connection_error**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._configure_s3_credentials()`
  - **Scenario:** Validar que a ausência de `AWS_ACCESS_KEY_ID` lança `S3ConnectionError` com status 403.
  - **Arrange:** Limpar `AWS_ACCESS_KEY_ID` do ambiente mantendo `AWS_SECRET_ACCESS_KEY`.
  - **Act:** Invocar `_configure_s3_credentials()`.
  - **Assert:** Lança `S3ConnectionError` com `status_code == 403` e mensagem informativa sobre credencial ausente.
  - **Priority:** P0

- [COMPLETED] [TEST015-12] [Type: Unit] **test_aws_credentials_missing_secret_key_raises_s3_connection_error**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._configure_s3_credentials()`
  - **Scenario:** Validar que a ausência de `AWS_SECRET_ACCESS_KEY` lança `S3ConnectionError` com status 403.
  - **Arrange:** Limpar `AWS_SECRET_ACCESS_KEY` do ambiente mantendo `AWS_ACCESS_KEY_ID`.
  - **Act:** Invocar `_configure_s3_credentials()`.
  - **Assert:** Lança `S3ConnectionError` com `status_code == 403`.
  - **Priority:** P0

- [COMPLETED] [TEST015-13] [Type: Unit] **test_aws_credentials_region_fallback_to_default_region**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._configure_s3_credentials()`
  - **Scenario:** Validar que quando `AWS_REGION` não está definida, o adaptador busca `AWS_DEFAULT_REGION` e por fim utiliza `"us-east-1"`.
  - **Arrange:** Configurar apenas `AWS_DEFAULT_REGION="eu-west-1"` no ambiente.
  - **Act:** Invocar `_configure_s3_credentials()`.
  - **Assert:** Comando executado é `SET s3_region = 'eu-west-1';`.
  - **Priority:** P1

- [COMPLETED] [TEST015-14] [Type: Unit] **test_aws_credentials_optional_session_token_injected_when_present**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._configure_s3_credentials()`
  - **Scenario:** Validar que `AWS_SESSION_TOKEN` temporário (ex: STS / IAM Role) é configurado quando presente e omitido quando ausente.
  - **Arrange:** Testar com `AWS_SESSION_TOKEN="TOKEN123"` e sem a variável.
  - **Act:** Invocar `_configure_s3_credentials()`.
  - **Assert:** `SET s3_session_token = 'TOKEN123';` é chamado apenas no primeiro caso.
  - **Priority:** P1

- [COMPLETED] [TEST015-15] [Type: Unit] **test_aws_credentials_optional_endpoint_url_injected_when_present**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._configure_s3_credentials()`
  - **Scenario:** Validar suporte a MinIO / LocalStack via `AWS_ENDPOINT_URL` ou `S3_ENDPOINT`.
  - **Arrange:** Configurar `AWS_ENDPOINT_URL="http://minio.local:9000"`.
  - **Act:** Invocar `_configure_s3_credentials()`.
  - **Assert:** `SET s3_endpoint = 'http://minio.local:9000';` é executado.
  - **Priority:** P1

- [COMPLETED] [TEST015-16] [Type: Unit] **test_aws_credentials_s3_use_ssl_disabled_configurations**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._configure_s3_credentials()`
  - **Scenario:** Validar que valores `"false"`, `"0"` ou `"no"` em `S3_USE_SSL` desativam o SSL no DuckDB (`SET s3_use_ssl = false;`).
  - **Arrange:** Testar com `S3_USE_SSL="false"`, `S3_USE_SSL="0"` e `S3_USE_SSL="no"`.
  - **Act:** Invocar `_configure_s3_credentials()`.
  - **Assert:** `SET s3_use_ssl = false;` é executado para todos os formatos de falso.
  - **Priority:** P1

- [COMPLETED] [TEST015-17] [Type: Unit] **test_aws_credentials_not_logged_in_stdout_or_logs**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._configure_s3_credentials()`
  - **Scenario:** Validar que os valores de chaves secretas ou access keys nunca são expostos em mensagens de log (CWE-798).
  - **Arrange:** Capturar logs com `caplog` em nível DEBUG durante a configuração de credenciais com strings secretas identificáveis.
  - **Act:** Invocar `_configure_s3_credentials()`.
  - **Assert:** Nenhuma entrada de log contém a chave secreta ou o token de sessão.
  - **Priority:** P0

---

### Task 005 — [Adapter-Persistence]: Implement S3 VIEW creation with graceful degradation

- [COMPLETED] [TEST015-18] [Type: Unit] **test_s3_view_creation_query_structure_and_casting**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._initialize_s3_schema()`
  - **Scenario:** Validar que a query de criação de VIEW utiliza `CREATE VIEW IF NOT EXISTS sales_data AS SELECT ... FROM read_csv_auto('s3://...', delim=';', header=True)` mantendo paridade total de schema e casting de colunas com a tabela local.
  - **Arrange:** Mockar conexão DuckDB com S3 URI `s3://my-bucket/sales.csv`.
  - **Act:** Invocar `_initialize_s3_schema()`.
  - **Assert:** A query enviada contém `CREATE VIEW IF NOT EXISTS sales_data`, `read_csv_auto('s3://my-bucket/sales.csv', delim=';', header=True)` e os 9 campos tipados canônicos.
  - **Priority:** P0

- [COMPLETED] [TEST015-19] [Type: Unit] **test_s3_view_creation_graceful_degradation_on_403_forbidden**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._initialize_s3_schema()`
  - **Scenario:** Validar que uma falha de permissão HTTP 403 na criação da VIEW é interceptada, logada como warning e resulta na criação de uma tabela vazia com schema canônico sem propagar crash.
  - **Arrange:** Configurar mock para lançar `RuntimeError("HTTP Error 403: Access Denied")` no `execute` da VIEW.
  - **Act:** Invocar `_initialize_s3_schema()`.
  - **Assert:** `CREATE TABLE IF NOT EXISTS sales_data` com schema canônico é executado e o adaptador continua utilizável.
  - **Priority:** P0

- [COMPLETED] [TEST015-20] [Type: Unit] **test_s3_view_creation_graceful_degradation_on_404_not_found**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._initialize_s3_schema()`
  - **Scenario:** Validar que erro de objeto não encontrado (HTTP 404) na criação da VIEW resulta no fallback de schema vazio canônico.
  - **Arrange:** Configurar mock para lançar `RuntimeError("HTTP Error 404: Not Found")` no `execute` da VIEW.
  - **Act:** Invocar `_initialize_s3_schema()`.
  - **Assert:** Tabela vazia com schema canônico é criada e warning com diagnóstico é emitido.
  - **Priority:** P0

- [COMPLETED] [TEST015-21] [Type: Unit] **test_s3_view_creation_graceful_degradation_on_network_timeout**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._initialize_s3_schema()`
  - **Scenario:** Validar que timeout de rede ou indisponibilidade S3 resulta em fallback gracioso para schema vazio.
  - **Arrange:** Configurar mock para lançar `RuntimeError("Connection timed out after 30000ms")`.
  - **Act:** Invocar `_initialize_s3_schema()`.
  - **Assert:** Adaptador não quebra e inicializa schema canônico vazio.
  - **Priority:** P0

- [COMPLETED] [TEST015-22] [Type: Unit] **test_httpfs_install_failure_falls_back_to_empty_schema**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._initialize_s3_schema()`
  - **Scenario:** Validar que caso a instalação ou carga da extensão `httpfs` falhe (ex: ambiente offline ou erro de download de binário), o fallback para schema vazio é executado imediatamente.
  - **Arrange:** Configurar mock para lançar exceção durante `INSTALL httpfs;`.
  - **Act:** Invocar `_initialize_s3_schema()`.
  - **Assert:** Log de erro emitido e `_CANONICAL_SCHEMA_DDL` executado.
  - **Priority:** P1

- [COMPLETED] [TEST015-23] [Type: Unit] **test_s3_view_path_single_quotes_properly_escaped**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._initialize_s3_schema()`
  - **Scenario:** Validar que caminhos S3 contendo aspas simples são escapados (`''`) para prevenir injeção SQL no comando DDL da VIEW.
  - **Arrange:** Configurar `dataset_path="s3://bucket/sales'2023.csv"`.
  - **Act:** Executar `_initialize_s3_schema()` com mock connection.
  - **Assert:** A query gerada utiliza `read_csv_auto('s3://bucket/sales''2023.csv', ...)` sem quebra de sintaxe.
  - **Priority:** P1

---

### Task 006 — [Adapter-Persistence]: Implement conditional external access toggle

- [COMPLETED] [TEST015-24] [Type: Unit] **test_enable_external_access_disabled_in_local_mode**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._initialize_local_schema()`
  - **Scenario:** Validar que após carregar o CSV local em memória, `SET enable_external_access = false;` é executado para blindar o processo contra leituras arbitrárias.
  - **Arrange:** Instanciar adaptador com arquivo CSV local temporário.
  - **Act:** Tentar executar comando SQL de leitura externa como `SELECT * FROM read_csv_auto(...)`.
  - **Assert:** DuckDB lança exceção indicando que o acesso externo está desabilitado.
  - **Priority:** P0

- [COMPLETED] [TEST015-25] [Type: Unit] **test_enable_external_access_remains_enabled_in_s3_mode**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._initialize_s3_schema()`
  - **Scenario:** Validar que em modo S3 a instrução `SET enable_external_access = false;` **NÃO** é executada, permitindo queries remotas contínuas via `httpfs` (ADR-04).
  - **Arrange:** Mockar conexão DuckDB em modo S3 com credenciais.
  - **Act:** Executar `_initialize_s3_schema()`.
  - **Assert:** Nenhum comando contendo `enable_external_access = false` é enviado ao DuckDB.
  - **Priority:** P0

- [COMPLETED] [TEST015-26] [Type: Unit] **test_external_access_toggle_failure_handled_gracefully_in_local_mode**
  - **Target:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `DuckDbSalesAdapter._initialize_local_schema()`
  - **Scenario:** Validar que se `SET enable_external_access = false;` lançar uma exceção no modo local, o erro é capturado e registrado como warning sem interromper a inicialização.
  - **Arrange:** Configurar mock de conexão local para lançar exceção no `SET enable_external_access`.
  - **Act:** Executar `_initialize_local_schema()`.
  - **Assert:** A inicialização completa com sucesso sem lançar exceção.
  - **Priority:** P2

---

### Task 007 — [Config]: Update .env.example with S3 environment variables

- [COMPLETED] [TEST015-27] [Type: Unit] **test_env_example_contains_s3_variables_and_examples**
  - **Target:** `.env.example`
  - **Scenario:** Validar que o arquivo `.env.example` documenta todas as variáveis S3 requeridas (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_SESSION_TOKEN`, `AWS_ENDPOINT_URL`, `S3_USE_SSL`) e exemplo de `DATASET_PATH=s3://...`.
  - **Arrange:** Ler conteúdo de `.env.example`.
  - **Act:** Inspecionar presença de chaves e comentários explicativos.
  - **Assert:** Todas as 6 variáveis AWS/S3 estão presentes com exemplos comentados.
  - **Priority:** P1

---

### Task 008 — [Config]: Update K8s manifests for S3 credentials

- [COMPLETED] [TEST015-28] [Type: Unit] **test_k8s_manifests_contain_s3_and_aws_credential_configurations**
  - **Target:** `k8s/configmap.yaml`, `k8s/secrets.example.yaml`, `k8s/app-deployment.yaml`
  - **Scenario:** Validar que `configmap.yaml` inclui exemplo de `DATASET_PATH` S3 e `AWS_REGION`, `secrets.example.yaml` inclui chaves AWS e `app-deployment.yaml` mapeia as variáveis para o pod.
  - **Arrange:** Ler arquivos YAML do diretório `k8s/`.
  - **Act:** Verificar declaração de `DATASET_PATH`, `AWS_REGION`, `aws-access-key-id`, `aws-secret-access-key`.
  - **Assert:** Manifestos contêm todas as definições estruturais necessárias para deploy S3 em Kubernetes.
  - **Priority:** P1

---

### Task 009 — [Config]: Update Dockerfile for S3-first deployment

- [COMPLETED] [TEST015-29] [Type: Unit] **test_dockerfile_supports_s3_configuration_and_optional_dataset**
  - **Target:** `Dockerfile`
  - **Scenario:** Validar que o `Dockerfile` documenta a transição para armazenamento S3 remoto e não possui dependência obrigatória de cópia local do dataset.
  - **Arrange:** Ler conteúdo do `Dockerfile`.
  - **Act:** Verificar instruções `ENV DATASET_PATH` e cópia do dataset.
  - **Assert:** O container está configurado para operar tanto com dataset remoto S3 quanto com volume local.
  - **Priority:** P1

---

### Task 010 — [Test-Unit]: S3 URI detection logic tests

- [COMPLETED] [TEST015-30] [Type: Unit] **test_s3_uri_detection_test_suite_execution**
  - **Target:** `tests/unit/test_s3_uri_detection.py` → `TestS3UriDetection`
  - **Scenario:** Validar que todos os 7 testes da suíte `test_s3_uri_detection.py` executam e cobrem detecção minúscula, maiúscula, caminhos locais absolutos/relativos e construtor.
  - **Arrange:** Preparar ambiente de testes unitários.
  - **Act:** Executar `pytest tests/unit/test_s3_uri_detection.py`.
  - **Assert:** 100% dos testes passam sem warnings ou erros.
  - **Priority:** P0

---

### Task 011 — [Test-Unit]: httpfs and credential configuration tests

- [COMPLETED] [TEST015-31] [Type: Unit] **test_s3_credential_config_test_suite_execution**
  - **Target:** `tests/unit/test_s3_credential_config.py` → `TestHttpfsAndCredentialConfig`
  - **Scenario:** Validar que todos os 12 testes da suíte `test_s3_credential_config.py` executam cobrindo instalação do `httpfs`, comandos `SET`, fallbacks de região, tokens STS, endpoints MinIO e validação de chaves obrigatórias.
  - **Arrange:** Preparar ambiente de testes unitários.
  - **Act:** Executar `pytest tests/unit/test_s3_credential_config.py`.
  - **Assert:** 100% dos testes passam com asserções rigorosas de SQL gerado.
  - **Priority:** P0

---

### Task 012 — [Test-Unit]: Graceful degradation on S3 errors

- [COMPLETED] [TEST015-32] [Type: Unit] **test_s3_graceful_degradation_test_suite_execution**
  - **Target:** `tests/unit/test_s3_graceful_degradation.py` → `TestS3GracefulDegradation`
  - **Scenario:** Validar que todos os 6 testes da suíte `test_s3_graceful_degradation.py` executam verificando tratamento de erros 403, 404, timeouts, falha no `httpfs` e estabilidade contínua do adaptador.
  - **Arrange:** Preparar ambiente de testes unitários.
  - **Act:** Executar `pytest tests/unit/test_s3_graceful_degradation.py`.
  - **Assert:** 100% dos testes passam confirmando resiliência e integridade do schema vazio.
  - **Priority:** P0

---

### Task 013 — [Test-Unit]: Conditional external access toggle

- [COMPLETED] [TEST015-33] [Type: Unit] **test_s3_external_access_test_suite_execution**
  - **Target:** `tests/unit/test_s3_external_access.py` → `TestConditionalExternalAccess`
  - **Scenario:** Validar que todos os 3 testes da suíte `test_s3_external_access.py` executam confirmando isolamento de acesso no modo local e liberação de acesso externo para streaming S3.
  - **Arrange:** Preparar ambiente de testes unitários.
  - **Act:** Executar `pytest tests/unit/test_s3_external_access.py`.
  - **Assert:** 100% dos testes passam sem divergência de comportamento.
  - **Priority:** P0

---

### Task 014 — [Test-Unit]: Backward compatibility regression tests

- [COMPLETED] [TEST015-34] [Type: Unit] **test_s3_backward_compatibility_test_suite_execution**
  - **Target:** `tests/unit/test_s3_backward_compatibility.py` → `TestBackwardCompatibility`
  - **Scenario:** Validar que todos os 15 testes de regressão executam contra dataset local CSV, cobrindo todos os 10 métodos de agregação analítica, queries SQL genéricas, perfilamento dinâmico e tratamento de arquivo inexistente.
  - **Arrange:** Preparar fixture de CSV de regressão com dados temporários.
  - **Act:** Executar `pytest tests/unit/test_s3_backward_compatibility.py`.
  - **Assert:** 100% dos testes passam com resultados analíticos exatos e zero quebra retroativa.
  - **Priority:** P0

---

### Task 015 — [Test-Integration]: End-to-end domain aggregations against S3

- [COMPLETED] [TEST015-35] [Type: Integration] **test_s3_aggregations_e2e_all_domain_queries**
  - **Target:** `tests/integration/test_s3_aggregations.py` → `TestS3Aggregations`
  - **Scenario:** Validar a execução ponta a ponta de todas as 10 agregações analíticas (`aggregate_top_selling_product`, `aggregate_top_locations`, `aggregate_total_sales`, `aggregate_planned_vs_actual`, `aggregate_promotion_impact`, `aggregate_service_level_bottlenecks`, `aggregate_revenue_deficit`, `aggregate_average_discount`, `aggregate_seasonality`, `aggregate_price_elasticity`), `execute_read_only_query` e `get_sales_by_filter` diretamente contra a VIEW S3.
  - **Arrange:** Configurar credenciais AWS e bucket S3 válido com dataset real ou simulado.
  - **Act:** Executar métodos analíticos no adaptador S3.
  - **Assert:** Todas as consultas retornam instâncias de modelos de domínio populadas com dados válidos e consistentes.
  - **Priority:** P0

- [COMPLETED] [TEST015-36] [Type: Unit] **test_s3_aggregations_skipif_behavior_when_credentials_absent**
  - **Target:** `tests/integration/test_s3_aggregations.py`
  - **Scenario:** Validar que na ausência de credenciais AWS de ambiente ou quando `DATASET_PATH` não é um URI `s3://`, a suíte de integração é ignorada graciosamente com `@pytest.mark.skipif` para preservar o pipeline de CI/CD.
  - **Arrange:** Executar em ambiente sem `AWS_ACCESS_KEY_ID` configurado.
  - **Act:** Executar pytest na suíte de integração.
  - **Assert:** Os testes são marcados como `SKIPPED` com a razão explicativa clara.
  - **Priority:** P1

---

### Task 016 — [Test-Integration]: Dataset profiling against S3

- [COMPLETED] [TEST015-37] [Type: Integration] **test_s3_profiling_e2e_metadata_discovery**
  - **Target:** `tests/integration/test_s3_profiling.py` → `TestS3Profiling`
  - **Scenario:** Validar que `profile_dataset()` descobre com sucesso contagem total de registros, limites temporais, contagem distinta de produtos e locais, valores sentinela e formatação de bloco Markdown a partir do stream S3.
  - **Arrange:** Configurar conexão S3 ativa.
  - **Act:** Executar `profile_dataset()` no adaptador.
  - **Assert:** `profile.total_records > 0`, `distinct_products > 0`, `min_date` e `max_date` preenchidos e `to_markdown_block()` contendo `DYNAMIC DATA INSIGHTS`.
  - **Priority:** P0

- [COMPLETED] [TEST015-38] [Type: Unit] **test_s3_profiling_skipif_behavior_when_credentials_absent**
  - **Target:** `tests/integration/test_s3_profiling.py`
  - **Scenario:** Validar que a suíte de profiling em S3 é ignorada graciosamente (`SKIPPED`) quando executada em ambiente sem credenciais de nuvem ativas.
  - **Arrange:** Executar em ambiente sem credenciais AWS.
  - **Act:** Executar pytest na suíte de integração de profiling.
  - **Assert:** Os testes reportam status `SKIPPED` sem quebrar o pipeline.
  - **Priority:** P1
