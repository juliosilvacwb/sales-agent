# S012-type-safety-and-code-quality — Security Audit

> **Source Task:** [T012-type-safety-and-code-quality.md](../architecture/T012-type-safety-and-code-quality.md)  
> **PRD Reference:** [R012-type-safety-and-code-quality.md](../business-requirements/R012-type-safety-and-code-quality.md)  
> **Test Coverage:** [TEST012-type-safety-and-code-quality.md](../tests/TEST012-type-safety-and-code-quality.md)

## Security Overview

A auditoria de segurança da especificação técnica de **Strict Type Safety and Code Quality** (`T012-type-safety-and-code-quality.md` / `R012-type-safety-and-code-quality.md`) avaliou a infraestrutura de tipagem estática, linting determinístico e gates de integração contínua (CI/CD) implementados no Sales Data Analysis Agent. A avaliação foi conduzida com base nos padrões do **OWASP Top 10 for LLM Applications (LLM04: Model Denial of Service)**, **OWASP ASVS V5 (Validation and Sanitization)**, **OWASP Top 10 CI/CD Security (CICD-SEC-01: Insufficient Pipeline Gates, CICD-SEC-03: Dependency Chain Abuse, CICD-SEC-05: Pipeline Misconfigurations)** e **CWE-704 (Incorrect Type Conversion or Cast) / CWE-252 (Unchecked Return Value)**.

A transição de tipagem dinâmica para MyPy em modo estrito (`strict = true`) e a consolidação de regras de linting via Ruff trazem ganhos significativos na prevenção de falhas de desreferenciação em tempo de execução (`TypeError`, `NoneType` attribute dereferencing). A análise de segurança identificou e estruturou os seguintes vetores de risco e mitigação:

1. **Segregação de Dependências e Segurança da Cadeia de Suprimentos (SCA / CWE-1104 / CICD-SEC-03):** Avaliação da inclusão de pacotes de desenvolvimento e stubs de tipagem (`mypy`, `ruff`, `types-redis`, `types-requests`) diretamente no arquivo `requirements.txt` de produção, mitigando o risco de expansão desnecessária da superfície de ataque em containers de produção.
2. **Prevenção de Type Confusion em Módulos Críticos de Autenticação e Criptografia (CWE-704 / ASVS V5):** Análise dos overrides globais no `pyproject.toml` (`ignore_missing_imports = true`) para assegurar que bibliotecas sensíveis como `jwt` e `cryptography` não sofram bypass de checagem estática nas fronteiras de verificação de tokens e controle de acesso.
3. **Robustez de Tipagem em Fronteiras de Adaptadores e Tratamento de Nullability (CWE-252 / CWE-754):** Garantia de que retornos `Optional` de repositórios, parsers e caches em memória/Redis possuam guards explícitos de nullability antes de invocações de métodos, evitando interrupções em fluxos orquestrados por LLM.
4. **Hardening de Permissões e Imutabilidade de Pipeline de CI/CD (CICD-SEC-01 / CICD-SEC-05):** Validação da configuração do workflow GitHub Actions (`.github/workflows/ci-cd.yml`) para impor execução de gates com princípio do menor privilégio (`permissions: contents: read`) e dependência estrita (`needs: [ lint-and-typecheck ]`).

---

## Vulnerability Log

| ID | Vulnerability / Security Control | Severity | Risk | Impact |
| :--- | :--- | :--- | :--- | :--- |
| S012-01 | Supply Chain Attack Surface & Dev Dependency Pollution in Production | Medium | Low x Medium | Inclusão de compiladores/linters em containers de produção aumentando vetor de exploração e footprint da imagem. |
| S012-02 | Broad Wildcard Type-Check Overrides on Security/Crypto Libraries | Medium | Low x High | Supressão inadvertida de tipagem em módulos de JWT/Crypto mascarando erros de validação de assinatura e claims. |
| S012-03 | Missing Defensive Type Narrowing on External Adapter Boundaries | Low | Low x Medium | Falhas de runtime `TypeError` decorrentes de retornos inesperados de bibliotecas externas sem type guard explícito. |
| S012-04 | Missing Explicit Pipeline Permissions in CI/CD Workflow | Low | Low x Low | Execução de jobs de CI com privilégios de escrita desnecessários no repositório padrão em caso de compromised actions. |

---

## Refinement Tasks

### Task 001 — [Config]: Update requirements.txt with development dependencies

- [COMPLETED] [S012-01] [Medium] **Segregação de Dependências de Desenvolvimento e Supply Chain Hardening**
  - **Location:** `requirements.txt` → `mypy`, `ruff`, `types-redis`, `types-requests`
  - **Risk:** Declarar ferramentas de análise estática e stubs de tipagem diretamente no `requirements.txt` principal faz com que ambientes de produção instalem compiladores e bibliotecas desnecessárias, ampliando a superfície de ataque da cadeia de suprimentos e aumentando o tamanho de containers Docker.
  - **Fix:** Isolar dependências de desenvolvimento em um arquivo dedicado `requirements-dev.txt` (ou seção de dependências opcionais/grupos de build) ou garantir que builds de contêiner utilizem multi-stage builds instalando estritamente os pacotes de runtime.
  - **Validation:** Verificar a separação das dependências e testar se `pip install -r requirements.txt` em container de produção não instala linters ou ferramentas de desenvolvimento.

---

### Task 002 — [Config]: Configure pyproject.toml

- [COMPLETED] [S012-02] [Medium] **Restrição de Overrides de Type Checking em Módulos de Autenticação e Criptografia**
  - **Location:** `pyproject.toml` → `[[tool.mypy.overrides]]`
  - **Risk:** A regra `ignore_missing_imports = true` aplicada indistintamente a `jwt.*` e `cryptography.*` desativa verificações essenciais de tipo nas chamadas de decodificação e validação de tokens JWT (`PyJwtAdapter`), podendo ocultar erros silenciosos de parâmetros e assinaturas criptográficas.
  - **Fix:** Remover bibliotecas de segurança (`jwt.*`, `cryptography.*`) dos blocos genéricos de `ignore_missing_imports`, instalando os stubs oficiais correspondentes ou criando interfaces tipadas rigorosas na camada de domínio/portas para encapsular os tipos externos sem bypass global.
  - **Validation:** Executar `mypy src/adapter/outbound/token/` e `mypy src/domain/model/auth_models.py` assegurando zero erros de tipagem sem depender de wildcards permissivos.

---

### Task 005 — [Adapter-Web]: Type hint and format Adapter Layer

- [COMPLETED] [S012-03] [Low] **Defesa em Profundidade e Type Narrowing em Adaptadores de Borda**
  - **Location:** `src/adapter/inbound/llm/sql_fallback_tool.py` e `src/adapter/outbound/redis/redis_session_adapter.py`
  - **Risk:** Conversões implícitas ou casts forçados de tipos retornados por drivers externos (como DuckDB, Redis ou LangChain) sem type guard explícito (`if value is not None:`) podem resultar em falhas de desreferenciação em tempo de execução e negação de serviço da sessão do agente.
  - **Fix:** Aplicar validações defensivas de tipo (`isinstance`, verificação explícita de `is not None` e Pydantic validation) em todas as fronteiras de entrada de dados externos antes de processar ou delegar para o use case.
  - **Validation:** Executar testes unitários cobrindo cenários com payloads nulos, malformados ou tipos divergentes em todos os métodos de adaptadores externos.

---

### Task 006 — [Adapter-Infra]: Implement lint-and-typecheck quality gate in CI

- [COMPLETED] [S012-04] [Low] **Hardening de Permissões e Imutabilidade de Actions no Pipeline CI/CD**
  - **Location:** `.github/workflows/ci-cd.yml`
  - **Risk:** Workflows de CI sem definição explícita do bloco `permissions` herdam permissões amplas (leitura/escrita) por padrão no GitHub Actions, violando o princípio do menor privilégio (OWASP CICD-SEC-05).
  - **Fix:** Adicionar o bloco explícito `permissions: contents: read` no topo do workflow ou no escopo de cada job (`lint-and-typecheck` e `test-suite`) para garantir que os executores operem em modo estritamente read-only.
  - **Validation:** Inspecionar o workflow `.github/workflows/ci-cd.yml` e verificar que nenhum job possui privilégios desnecessários de escrita ou acesso a secrets sem escopo.
