# S015-s3-dynamic-dataset-storage — Security Audit

> **Source Task:** [T015-s3-dynamic-dataset-storage.md](../architecture/T015-s3-dynamic-dataset-storage.md)  
> **PRD Reference:** [R015-s3-dynamic-dataset-storage.md](../business-requirements/R015-s3-dynamic-dataset-storage.md)  
> **Test Coverage:** [TEST015-s3-dynamic-dataset-storage.md](../tests/TEST015-s3-dynamic-dataset-storage.md)

## Security Overview

A auditoria de segurança da especificação de **Zero-Copy Remote S3 Direct Querying for Big Data Scalability** (`T015-s3-dynamic-dataset-storage.md` / `R015-s3-dynamic-dataset-storage.md`) avaliou a robustez da integração de armazenamento em nuvem S3 via extensão `httpfs` do DuckDB, o gerenciamento de credenciais AWS em ambientes conteinerizados (Kubernetes/12-Factor), o controle de acesso externo (`enable_external_access`) e a proteção de limites de memória e observabilidade. A análise foi fundamentada nos padrões **OWASP Top 10 (A01: Broken Access Control, A03: Injection, A05: Security Misconfiguration, A09: Security Logging and Monitoring Failures)**, **CWE-89 (Improper Neutralization of Special Elements used in an SQL Command)**, **CWE-209 (Generation of Error Message Containing Sensitive Information)**, **CWE-532 (Insertion of Sensitive Information into Log File)**, **CWE-918 (Server-Side Request Forgery - SSRF)** e **CWE-798 (Use of Hard-coded Credentials)**.

A transição de arquivos CSV estáticos locais para streaming remoto via S3 introduz novos vetores de ataque cibernético relacionados a injeção em comandos de configuração `SET`, permissividade de acesso externo de rede (`enable_external_access = true`), vazamento de assinaturas/chaves de autenticação em mensagens de erro e riscos de escopo excessivo de permissões IAM.

### Principais Dimensões Auditadas

1. **Prevenção de Injeção em Comandos DuckDB SET (CWE-89 / CWE-20):** Avaliação da sanitização e escape de aspas simples (`'`) em variáveis de ambiente (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_SESSION_TOKEN`, `AWS_ENDPOINT_URL`) injetadas dinamicamente via comandos `SET` na sessão do DuckDB.
2. **Prevenção de Vazamento de Credenciais em Logs e Tratamento de Exceções (CWE-209 / CWE-532 / OWASP A09):** Validação da higienização de mensagens de erro emitidas durante falhas de carregamento da extensão `httpfs` ou criação da `VIEW` S3, garantindo a remoção de cabeçalhos de autorização AWS, assinaturas HMAC e tokens de sessão.
3. **Controle de Acesso Externo e Defesa em Profundidade contra SSRF (CWE-918 / OWASP A01 / A05):** Análise da coexistência entre a permissão de rede necessária pelo `httpfs` (`enable_external_access = true` no modo S3) e as travas determinísticas da AST de consultas SQL (`SecuredSQLQueryTool` / `SqlSecurityValidator`), garantindo que funções arbitrárias de leitura remota continuem bloqueadas.
4. **Gerenciamento Seguro de Credenciais e Princípio do Menor Privilégio IAM (CWE-798 / OWASP A05):** Auditoria dos manifestos Kubernetes (`k8s/secrets.example.yaml`, `k8s/app-deployment.yaml`) e diretrizes de políticas IAM para restringir o acesso apenas a operações de leitura (`s3:GetObject`, `s3:ListBucket`) limitadas ao bucket e prefixo específicos do dataset.
5. **Execução Segura em Contêineres e Bounded Resource Consumption (CWE-400):** Validação do Dockerfile com usuário não-root (`appuser`, UID 1000) e arquitetura baseada em `CREATE VIEW` para streaming sob demanda, prevenindo esgotamento de memória (OOM) e vetores de escalonamento de privilégios.

---

## Vulnerability Log

| ID | Vulnerability / Security Control | Severity | Risk | Impact |
| :--- | :--- | :--- | :--- | :--- |
| S015-01 | Unescaped String Interpolation in DuckDB SET Credentials Configuration | Medium | Low x Medium | Risco de erro de sintaxe SQL ou injeção de parâmetros em comandos DuckDB caso variáveis de credenciais contenham aspas simples. |
| S015-02 | Potential AWS Credential and Signature Leakage in S3 Error Logs | Medium | Low x Medium | Exposição de assinaturas de requisição AWS, tokens ou URIs sensíveis em logs operacionais durante falhas na criação da VIEW S3. |
| S015-03 | Permissive External Access Hardening and Defence-in-Depth against SSRF | High | Medium x High | Manutenção de travas estritas na AST para impedir que a ativação de rede do httpfs permita execução de funções de leitura arbitrária. |
| S015-04 | Least-Privilege IAM Policy and Secret Isolation Enforcement | Low | Low x Low | Risco de concessão excessiva de privilégios (s3:*) a credenciais injetadas na aplicação. |

---

## Refinement Tasks

### Task 004 — [Adapter-Persistence]: Implement AWS credential configuration

- [COMPLETED] [S015-01] [Medium] **Sanitize and Escape Single Quotes in DuckDB SET Statements**
  - **Location:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `_configure_s3_credentials()`
  - **Risk:** As variáveis de ambiente lidas (`region`, `access_key`, `secret_key`, `session_token`, `endpoint_url`) são interpoladas diretamente em comandos SQL `SET s3_... = '{val}';` sem escape prévio de aspas simples. Caso uma credencial ou endpoint contenha aspas simples ou caracteres de controle, isso pode causar falhas de parse SQL ou injeção de comandos na sessão do DuckDB (CWE-89 / CWE-20).
  - **Fix:** Implementar sanitização e escape de aspas simples (`val.replace("'", "''")`) em todas as variáveis de configuração antes da interpolação nas instruções `SET`, ou validar rigorosamente os formatos das credenciais antes da execução.
  - **Validation:** Criar teste unitário em `tests/unit/test_s3_credential_config.py` simulando variáveis de ambiente com aspas simples e caracteres especiais, verificando que o escape é aplicado corretamente sem quebrar a execução SQL.

---

### Task 005 — [Adapter-Persistence]: Implement S3 VIEW creation with graceful degradation

- [COMPLETED] [S015-02] [Medium] **Mask Sensitive AWS Credentials and Signatures in S3 Error Handlers**
  - **Location:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` → `_initialize_s3_schema()`
  - **Risk:** Durante falhas de conexão S3 (ex: HTTP 403 Forbidden, 400 Bad Request, DNS timeout), o DuckDB pode emitir exceções contendo cabeçalhos de autenticação (`Authorization: AWS4-HMAC-SHA256 ...`), assinaturas de query string (`X-Amz-Signature=...`) ou caminhos internos. O tratamento atual apenas normaliza espaços em branco (`re.sub(r"[\r\n\t]+", " ", str(e))[:200]`), podendo persistir fragmentos de credenciais em logs de produção (CWE-209 / CWE-532).
  - **Fix:** Enriquecer a sanitização de erros com regex para mascarar assinaturas AWS, tokens de sessão, credenciais (`AWS_SECRET_ACCESS_KEY`, `Signature=`, `Credential=`) e caminhos sensíveis de arquivos antes de registrar logs de aviso/erro ou retornar mensagens.
  - **Validation:** Criar teste unitário simulando mensagem de erro do DuckDB contendo strings simuladas de assinatura AWS e chaves secretas, verificando que o log gerado está devidamente ofuscado com tags `[REDACTED]`.

---

### Task 006 — [Adapter-Persistence]: Implement conditional external access toggle

- [COMPLETED] [S015-03] [High] **Enforce Strict AST Defence-in-Depth for S3 Streaming Mode**
  - **Location:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py` e `src/domain/service/sql_security_validator.py`
  - **Risk:** No modo S3, `enable_external_access` precisa permanecer `true` para permitir requisições de byte-range HTTP pelo `httpfs`. Caso uma consulta ad-hoc de usuário contorne as barreiras de validação, funções de rede do DuckDB poderiam ser invocadas para exfiltração de dados ou varredura de rede interna (SSRF / CWE-918).
  - **Fix:** Garantir que: (1) `SqlSecurityValidator` mantenha bloqueio determinístico a qualquer chamada de leitura ou carregamento remoto (`READ_CSV`, `READ_CSV_AUTO`, `READ_PARQUET`, `READ_JSON`, `READ_TEXT`, `READ_BLOB`, `GLOB`, `ATTACH`, `LOAD`, `INSTALL`), (2) a URI do dataset S3 seja validada na inicialização do adaptador exigindo formato estrito `s3://<bucket>/<key>` sem saltos de diretório (`..`), e (3) a conexão utilize SSL obrigatório (`S3_USE_SSL=true`) por padrão.
  - **Validation:** Executar testes unitários e de integração validando que tentativas de executar consultas SQL com funções de I/O externo via `SecuredSQLQueryTool` continuam sendo rejeitadas com erro de segurança, mesmo com `enable_external_access = true` ativo no banco.

---

### Task 008 — [Config]: Update K8s manifests for S3 credentials

- [COMPLETED] [S015-04] [Low] **Document and Enforce Least-Privilege IAM Policy for S3 Storage**
  - **Location:** `k8s/secrets.example.yaml` e documentação de infraestrutura
  - **Risk:** O uso de credenciais AWS com permissões amplas (`AdministratorAccess` ou `s3:*` irrestrito) nos Secrets do Kubernetes viola o princípio do menor privilégio (CWE-272 / OWASP A05).
  - **Fix:** Documentar a política IAM mínima necessária para o funcionamento do adapter, limitando ações exclusivamente a leitura (`s3:GetObject`, `s3:ListBucket`) com escopo restrito ao bucket e prefixo exatos do dataset:
    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": [
            "s3:GetObject",
            "s3:ListBucket"
          ],
          "Resource": [
            "arn:aws:s3:::juliosilvacwb-private",
            "arn:aws:s3:::juliosilvacwb-private/*"
          ]
        }
      ]
    }
    ```
  - **Validation:** Verificar a conformidade do arquivo `k8s/secrets.example.yaml` e dos comentários explicativos no `.env.example`.
