<!-- markdownlint-disable MD013 -->
# TEST012-type-safety-and-code-quality — Test Coverage Specification

> **Source Task:** [T012-type-safety-and-code-quality.md](../architecture/T012-type-safety-and-code-quality.md)  
> **PRD Reference:** [R012-type-safety-and-code-quality.md](../business-requirements/R012-type-safety-and-code-quality.md)

## Coverage Overview

Esta especificação estabelece o plano forense e a matriz de cobertura de testes para a implementação de **Tipagem Estática Estrita e Qualidade de Código** (`T012-type-safety-and-code-quality.md` / `R012-type-safety-and-code-quality.md`). O objetivo central é assegurar a eliminação de defeitos em tempo de execução (`TypeError`, `AttributeError` e `NoneType` dereferences) através da padronização e validação contínua com MyPy (modo estrito) e Ruff (linter e formatador de alta performance), configurados de forma unificada no `pyproject.toml` e protegidos pelo portão de qualidade no pipeline CI/CD (`.github/workflows/ci-cd.yml`).

- **Status Geral de Cobertura:** 100% de conformidade com as regras de tipagem estrita, configurações de linting/formatação, anotações de camadas (Domínio, Aplicação, Adaptadores) e pipeline de integração contínua para todas as 6 tarefas da especificação T012.
- **Pirâmide de Testes:**
  - **Unitários (Configurações e Dependências):** Verificação de integridade do `requirements.txt` (pinagem de versões `mypy`, `ruff`, stubs de tipos `types-redis`, `types-requests`) e validação estrutural do `pyproject.toml` (parâmetros de `[tool.mypy]`, `[[tool.mypy.overrides]]`, `[tool.ruff]`, `[tool.ruff.lint]` e `[tool.ruff.format]`, garantindo a remoção de legados como `pyright`).
  - **Unitários (Tipagem Estática na Camada de Domínio):** Inspeção de anotações estritas de tipos em entidades, value objects, dataclasses imutáveis, enums e exceções em `src/domain/`.
  - **Unitários (Tipagem Estática na Camada de Aplicação):** Validação de assinaturas estritas em interfaces abstratas de portas (inbound/outbound), contratos de DTOs e injeção de dependências em serviços de aplicação em `src/application/`.
  - **Unitários (Tipagem Estática e Tratamento de Nullability na Camada de Adaptadores):** Validação de salvaguardas contra `NoneType`, anotações de `Optional[T]` / `T | None`, decorators de rotas FastAPI e stubs para bibliotecas de terceiros em `src/adapter/`.
  - **Integração / CI-CD (Pipeline Quality Gates):** Validação estrutural do fluxo GitHub Actions (`.github/workflows/ci-cd.yml`), dependência entre jobs (`needs: [lint-and-typecheck]`) e garantia de bloqueio de testes subsequentes caso ocorram falhas de lint ou tipagem.

---

## Test Checklist

### Task 001 — [Config]: Update requirements.txt with development dependencies

- [COMPLETED] [TEST012-01] [Type: Unit] **test_requirements_contains_mypy_and_ruff_tooling**
  - **Target:** `requirements.txt`
  - **Scenario:** Validar que o arquivo `requirements.txt` declara dependências explícitas para as ferramentas de análise estática `mypy>=1.10.0` e `ruff>=0.5.0`.
  - **Arrange:** Carregar o conteúdo do arquivo `requirements.txt`.
  - **Act:** Analisar as linhas do arquivo e verificar a presença dos pacotes `mypy` e `ruff`.
  - **Assert:** Ambos os pacotes estão presentes e possuem restrições de versão mínima atendendo aos requisitos de arquitetura.
  - **Priority:** P1

- [COMPLETED] [TEST012-02] [Type: Unit] **test_requirements_contains_type_stubs**
  - **Target:** `requirements.txt`
  - **Scenario:** Validar que pacotes de stubs de tipos (`types-redis`, `types-requests`) estão devidamente registrados em `requirements.txt` para bibliotecas externas.
  - **Arrange:** Carregar as linhas de `requirements.txt`.
  - **Act:** Buscar declarações de stubs de tipos para pacotes externos.
  - **Assert:** Os pacotes `types-redis>=4.6.0` e `types-requests>=2.31.0` estão presentes no arquivo.
  - **Priority:** P1

---

### Task 002 — [Config]: Configure pyproject.toml

- [COMPLETED] [TEST012-03] [Type: Unit] **test_pyproject_mypy_strict_mode_configuration**
  - **Target:** `pyproject.toml` → `[tool.mypy]`
  - **Scenario:** Validar que `pyproject.toml` define `strict = true`, `disallow_untyped_defs = true`, `no_implicit_optional = true` e `warn_return_any = true` na seção do MyPy.
  - **Arrange:** Carregar e decodificar `pyproject.toml` utilizando analisador TOML.
  - **Act:** Obter a tabela `tool.mypy`.
  - **Assert:** As chaves `strict`, `disallow_untyped_defs`, `no_implicit_optional` e `warn_return_any` são `True`, e `python_version` está fixada em `"3.11"`.
  - **Priority:** P0

- [COMPLETED] [TEST012-04] [Type: Unit] **test_pyproject_mypy_third_party_overrides**
  - **Target:** `pyproject.toml` → `[[tool.mypy.overrides]]`
  - **Scenario:** Validar que bibliotecas externas sem tipagem completa (`duckdb`, `langchain`, `langgraph`, `sqlglot`, `jwt`, `cryptography`, `uvicorn`) possuem overrides configurados com `ignore_missing_imports = true`.
  - **Arrange:** Carregar `pyproject.toml`.
  - **Act:** Obter a lista de tabelas `tool.mypy.overrides`.
  - **Assert:** A lista de módulos contém os pacotes externos e a flag `ignore_missing_imports` está ativa.
  - **Priority:** P1

- [COMPLETED] [TEST012-05] [Type: Unit] **test_pyproject_ruff_linter_and_formatter_configuration**
  - **Target:** `pyproject.toml` → `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.format]`
  - **Scenario:** Validar que a configuração do Ruff habilita as categorias de regras `E`, `W`, `F`, `I` (Isort), `B` (Bugbear), `UP` (Pyupgrade), define `line-length = 100` e aspas duplas no formatador.
  - **Arrange:** Carregar `pyproject.toml`.
  - **Act:** Inspecionar `tool.ruff`, `tool.ruff.lint.select` e `tool.ruff.format`.
  - **Assert:** `line-length` é igual a 100, `select` contém `["E", "W", "F", "I", "B", "UP"]` e `quote-style` é `"double"`.
  - **Priority:** P0

- [COMPLETED] [TEST012-06] [Type: Unit] **test_pyproject_excludes_legacy_pyright_configuration**
  - **Target:** `pyproject.toml`
  - **Scenario:** Validar que configurações obsoletas do `pyright` (`[tool.pyright]`) foram integralmente removidas para evitar conflitos de diretivas.
  - **Arrange:** Carregar `pyproject.toml`.
  - **Act:** Verificar a existência da chave `tool.pyright`.
  - **Assert:** A chave `tool.pyright` não existe no documento.
  - **Priority:** P1

---

### Task 003 — [Domain-Model]: Type hint and format Domain Layer

- [COMPLETED] [TEST012-07] [Type: Unit] **test_domain_models_strict_type_annotations**
  - **Target:** `src/domain/model/`
  - **Scenario:** Validar que todas as classes e dataclasses de domínio (`aggregation_models.py`, `dataset_profile.py`, `sales_metrics.py`, `sql_validation.py`) possuem anotações explícitas de tipo em atributos, construtores e métodos públicos.
  - **Arrange:** Inspecionar os módulos de domínio via introspecção de AST ou `typing.get_type_hints`.
  - **Act:** Avaliar as assinaturas de construtores, métodos de fábrica e propriedades.
  - **Assert:** Todos os parâmetros e retornos possuem type hints definidos, sem nenhum parâmetro omitido ou com tipo dinâmico implícito.
  - **Priority:** P0

- [COMPLETED] [TEST012-08] [Type: Unit] **test_domain_exceptions_and_enums_type_safety**
  - **Target:** `src/domain/exception/`, `src/domain/model/`
  - **Scenario:** Validar que a hierarquia de exceções de domínio e enums mantém assinaturas de tipo estritas em seus inicializadores e propriedades.
  - **Arrange:** Instanciar exceções de domínio (`SalesValidationError`, `SqlValidationError`, `SessionError`) e membros de enums (`SqlViolationType`).
  - **Act:** Inspecionar atributos tipados e métodos utilitários.
  - **Assert:** Atributos transportam valores com os tipos corretos e não ocorrem erros de coerção em tempo de execução.
  - **Priority:** P1

---

### Task 004 — [UseCase]: Type hint and format Application Layer

- [COMPLETED] [TEST012-09] [Type: Unit] **test_application_ports_abstract_method_type_signatures**
  - **Target:** `src/application/port/inbound/`, `src/application/port/outbound/`
  - **Scenario:** Validar que todas as interfaces abstratas de portas de entrada e saída (`SalesDataPort`, `SessionRepositoryPort`, `SqlParserPort`, `WebChatUseCase`) declaram assinaturas completas de tipos para parâmetros e retornos.
  - **Arrange:** Carregar as classes abstratas de porta em `src/application/port/`.
  - **Act:** Obter anotações de tipos via `typing.get_type_hints` para todos os métodos abstratos.
  - **Assert:** Todas as funções abstratas possuem anotação explícita de retorno (ex: `-> DatasetProfile`, `-> ParsedSqlStatement`, `-> ChatResponseDTO`) e de argumentos.
  - **Priority:** P0

- [COMPLETED] [TEST012-10] [Type: Unit] **test_application_services_dependency_injection_typing**
  - **Target:** `src/application/service/`
  - **Scenario:** Validar que os serviços da camada de aplicação (`web_chat_application_service.py`, `sales_metrics_service.py`) utilizam tipagem estrita nos construtores para injeção de dependências e nos DTOs trafegados.
  - **Arrange:** Inspecionar `__init__` e métodos de execução dos serviços de aplicação.
  - **Act:** Verificar as anotações dos parâmetros de injeção de portas e contratos de entrada/saída (`ChatRequestDTO` -> `ChatResponseDTO`).
  - **Assert:** Todas as dependências injetadas são tipadas pelas interfaces abstratas e métodos de execução possuem contratos formais de DTO.
  - **Priority:** P0

---

### Task 005 — [Adapter-Web]: Type hint and format Adapter Layer

- [COMPLETED] [TEST012-11] [Type: Unit] **test_adapter_layer_optional_and_null_handling_type_safety**
  - **Target:** `src/adapter/` → `chat_controller.py`, `sql_fallback_tool.py`, `redis_session_adapter.py`
  - **Scenario:** Validar que adaptadores externos e controladores web tipam explicitamente retornos anuláveis com `Optional[T]` / `T | None` e realizam guard clauses (`if obj is not None:`) antes de acessar atributos.
  - **Arrange:** Inspecionar métodos de consulta em adaptadores de persistência e repositórios.
  - **Act:** Validar tipagem de retornos que podem resultar em ausência de registro/sessão.
  - **Assert:** Funções que retornam valores nulos utilizam `Optional[...]` e seus consumidores aplicam validação defensiva contra `NoneType`.
  - **Priority:** P0

- [COMPLETED] [TEST012-12] [Type: Unit] **test_adapter_fastapi_controllers_pydantic_payload_typing**
  - **Target:** `src/adapter/inbound/web/` → `chat_controller.py`, `main.py`
  - **Scenario:** Validar que os endpoints FastAPI possuem anotações estritas de payload (`BaseModel`), modelos de resposta, parâmetros de rota e injeção de dependência com `Depends(...)`.
  - **Arrange:** Inspecionar decorators `@router.post`, `@router.get` e assinaturas das funções de rota em `chat_controller.py` e `main.py`.
  - **Act:** Obter anotações de parâmetros e tipos de retorno das rotas FastAPI.
  - **Assert:** Todas as rotas declaram `response_model`, `status_code` e parâmetros com tipos explícitos.
  - **Priority:** P0

---

### Task 006 — [Adapter-Infra]: Implement lint-and-typecheck quality gate in CI

- [COMPLETED] [TEST012-13] [Type: Unit] **test_ci_workflow_lint_and_typecheck_job_structure**
  - **Target:** `.github/workflows/ci-cd.yml`
  - **Scenario:** Validar que o fluxo de trabalho do GitHub Actions contém o job obrigatório `lint-and-typecheck` executando os passos `ruff check .`, `ruff format --check .` e `mypy src/`.
  - **Arrange:** Carregar e decodificar o arquivo `.github/workflows/ci-cd.yml`.
  - **Act:** Inspecionar a seção `jobs.lint-and-typecheck.steps`.
  - **Assert:** O job existe com `timeout-minutes: 5`, executa os comandos do Ruff e MyPy com flags apropriadas e valida todo o diretório `src/`.
  - **Priority:** P0

- [COMPLETED] [TEST012-14] [Type: Unit] **test_ci_workflow_gating_halts_on_failure**
  - **Target:** `.github/workflows/ci-cd.yml`
  - **Scenario:** Validar que o job de suíte de testes (`test-suite`) depende explicitamente do job de static analysis através de `needs: [ lint-and-typecheck ]`, impedindo a execução de testes em caso de falha de lint/tipagem.
  - **Arrange:** Carregar o arquivo de workflow do CI/CD.
  - **Act:** Inspecionar as dependências do job `test-suite`.
  - **Assert:** `jobs.test-suite.needs` contém `lint-and-typecheck` sem cláusulas de bypass (`continue-on-error` ou `if: always()`).
  - **Priority:** P0
