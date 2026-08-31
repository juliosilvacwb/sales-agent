# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.14.0] - 2026-08-31

### Fixed

- **Bloqueio de Chat e Abertura Automática da Modal de Autenticação (B005):**
  - Correção da inicialização da interface web (`src/adapter/inbound/web/static/app.js` e `src/adapter/inbound/web/static/index.html`) para disparar a modal de login automaticamente no carregamento quando não há token JWT em `sessionStorage`.
  - Imposição de postura *Fail-Closed* no frontend, iniciando os elementos `#chat-input` e `#send-btn` com o atributo `disabled` diretamente no HTML estático e mantendo-os bloqueados até a autenticação com sucesso.
  - Atualização dinâmica do status visual no header da aplicação (`"Não autenticado"` vs `"Online"`).
- **Remoção de Credenciais Hardcoded e Prevenção de Autofill Inseguro (SB005 / CWE-798):**
  - Remoção do atributo estático `value="admin"` do campo `<input id="auth-username">`, substituindo-o por `placeholder="Digite seu usuário..."` e atributo semântico de acessibilidade `autocomplete="username"`.
  - Garantia de que o campo `<input id="auth-password">` permaneça vazio com `placeholder="Digite sua senha..."` e `autocomplete="current-password"`.
- **Encapsulamento da Topologia do Auth Microservice (SB005 / CWE-200):**
  - Remoção dos campos visíveis de configuração de URL (`<label for="auth-url">` e `<input id="auth-url">`) do formulário de login no modal HTML.
  - Encapsulamento da rota interna do microsserviço de autenticação via constante JavaScript configurável `AUTH_SERVICE_URL` com fallback seguro para `window.AUTH_SERVICE_URL || "http://localhost:8001"`.
- **Tratamento de Sessão Expirada e Erro HTTP 401:**
  - Interceptação de respostas HTTP 401 Unauthorized nas requisições do chat, invalidando a sessão (`setJwtToken(null)`), retendo a mensagem pendente (`pendingMessage`) e reabrindo a modal interativa para reautenticação imediata sem perda do fluxo do usuário.

### Security

- **Fail-Closed Client Security (SB005-03 / CWE-285):** Interface protegida contra disparos acidentais ou não autorizados de requisições de chat sem credenciais válidas.
- **Mitigação de Exposição de Infraestrutura (SB005-02 / CWE-200):** Eliminação da manipulação manual de endpoints de autenticação no cliente visual.
- **Eliminação de Credenciais Embutidas (SB005-01 / CWE-798):** Erradicação de valores padrão embutidos no DOM inicial.

### Added

- **Suíte de Testes Automatizados de UI e Segurança (TESTB005):**
  - Criação do arquivo de testes de integração e reprodução `tests/integration/test_auth_modal_ui_incident_b005.py` com 6 testes automatizados cobrindo ausência de credenciais default, ocultação de URL, bloqueio inicial, logout reativo e contingência para 401 Unauthorized.
- **Artefatos de Governança ADD:** Inclusão das especificações `B005-initial-auth-modal-and-chat-locking.md`, `SB005-initial-auth-modal-and-chat-locking.md`, `TESTB005-initial-auth-modal-and-chat-locking.md` e `QB005-initial-auth-modal-and-chat-locking.md`.

## [1.13.0] - 2026-08-31

### Removed

- **Docker Compose (`docker-compose.yml`):**
  - Remoção do arquivo `docker-compose.yml` e descontinuação da orquestração local via Docker Compose em favor da orquestração declarativa padronizada via Kubernetes / K3s.

### Changed

- **Padronização de Deploy em Kubernetes (`kubectl`):**
  - Consolidação do pipeline de implantação em 4 etapas canônicas: Build das Imagens Docker -> Push para o Container Registry (Docker Hub) -> Criação de Secrets no Kubernetes -> Deploy declarativo com `kubectl apply -f k8s/`.
- **Manifestos Kubernetes e Probes (`k8s/`):**
  - Atualização do `k8s/configmap.yaml` com mapeamento explícito de `DATASET_PATH`, `LLM_PROVIDER`, `MODEL_NAME` e `LOG_LEVEL`.
  - Atualização do `k8s/app-deployment.yaml` com suporte a injeção opcional de chaves de múltiplos provedores (OpenAI, Anthropic, Google Gemini) e probes de liveness/readiness apontando para `/health`.
- **Documentação de Implantação e Guia de Execução (`README.md`):**
  - Atualização completa do `README.md` com os comandos exatos de build, push, criação de segredos (`kubectl create secret generic sales-agent-secrets --from-literal=...`), deploy, port-forwarding, testes de API com cURL e comandos de teardown.

### Added

- **Template de Segredos Kubernetes (`k8s/secrets.example.yaml`):**
  - Inclusão de modelo declarativo de segredos (`sales-agent-secrets`) com documentação de campos para credenciais de API de LLM e senhas do Auth Microservice.

## [1.12.0] - 2026-08-31

### Added

- **Orquestração de Agente com LangGraph StateGraph (T014 / R014):**
  - Transição arquitetural do orquestrador cognitivo do Sales Data Analysis Agent para uma máquina de estados direcionada determinística baseada em `langgraph.graph.StateGraph` e `langgraph.graph.MessagesState`.
- **Topologia de Grafo e Nós Desacoplados (`src/adapter/inbound/llm/sales_agent.py`):**
  - Implementação de `create_sales_graph` compilando nós discretos: nó `call_model` (execução do LLM com bind de ferramentas e injeção do prompt de sistema enriquecido) e nó `tools` (`ToolNode` nativo para execução das 10 Domain Tools determinísticas e do Fallback SQL seguro).
- **Roteamento Condicional e Aresta Cíclica:**
  - Implementação da função de transição `should_continue` que roteia para `"tools"` quando há `tool_calls` pendentes ou para `END` na presença de resposta final/diálogo casual, com aresta cíclica incondicional `"tools" -> "agent"` garantindo suporte nativo ao loop de autorrecuperação autônoma (R009).
- **Tratamento de Exceções de Grafo e Contingência:**
  - Captura robusta de `GraphRecursionError` e exceções genéricas durante a invocação do grafo, retornando a mensagem de fallback padronizada `FALLBACK_ERROR_MESSAGE` com `data_queried = False`.
- **Suíte de Testes Automatizados de Grafo:**
  - Criação de 23 cenários de testes unitários e de integração em `tests/unit/test_sales_agent.py` e `tests/integration/test_sales_agent.py` cobrindo compilação de nós, roteamento de borda, autorrecuperação cíclica, teto de recursão e retrocompatibilidade de turnos conversacionais.
- **Artefatos de Governança ADD:** Inclusão das especificações `R014-langgraph-orchestration.md`, `T014-langgraph-orchestration.md`, `TEST014-langgraph-orchestration.md`, `S014-langgraph-orchestration.md`, `Q014-langgraph-orchestration.md` e `PS014-langgraph-orchestration.md`.

### Changed

- **Eliminação de Dependência de `AgentExecutor` Legado:**
  - Substituição da compilação legada `AgentExecutor(agent=agent, tools=tools)` pela execução de `StateGraph(MessagesState).compile()`.
- **Isolamento de Memória Conversacional em Grafo:**
  - O método `SalesAgent.ask` agora monta o `MessagesState` com lista ordenada (`SystemMessage`, histórico anterior, `HumanMessage`) e propaga o `RunnableConfig` com `recursion_limit: 10` e callbacks para o executor compilado.
- **Compatibilidade Retroativa:**
  - Manutenção da assinatura pública de `SalesAgent.ask()`, retorno do tipo estruturado `AgentResult` e alias funcional `create_agent` para continuidade de patches e testes existentes.

### Security & Reliability

- **Prevenção de Negação de Serviço e Loop Infinito (OWASP LLM04 / S014-01 / CWE-400 / CWE-835):** Imposição imutável de `recursion_limit: 10` na execução do grafo e interceptação graciosa de `GraphRecursionError`.
- **Validação de Grounding e Whitelist Estrita (S014-02 / CWE-1188):** Extração de instâncias `ToolMessage` do estado inspecionando conformidade contra a constante `DATA_QUERY_TOOLS`.
- **Sanitização de Caminhos e Prevenção de Log Forging (S014-03 / CWE-209 / CWE-117):** Redação de diretórios locais (`[PATH_REDACTED]`) e remoção de quebras de linha em mensagens de erro interceptadas pelo `_handle_tool_error`.
- **Sanitização de Mensagens Externas de Histórico (S014-04 / CWE-20):** Validação defensiva de instâncias `BaseMessage` recebidas em `chat_history`, ignorando tipos inválidos sem quebrar a execução.
- **Encapsulamento Hexagonal Estrito (S014-05 / BR01):** Primitivas e estados do LangGraph restritos ao adaptador de entrada `sales_agent.py`, sem vazamento para serviços de aplicação, controladores ou domínio.

## [1.11.0] - 2026-08-31

### Added

- **Rastreamento de Grounding e Flag de Consulta a Dados (T013 / R013):**
  - Implementação de interceptação de ferramentas em tempo real para grounding factual de respostas analíticas no Sales Data Analysis Agent.
- **Interceptador de Callbacks LangChain (`ToolTrackingCallbackHandler`):**
  - Criação de `ToolTrackingCallbackHandler` derivado de `BaseCallbackHandler` em `src/adapter/inbound/llm/sales_agent.py`, interceptando eventos `on_tool_start` e `on_tool_end` com validação estrita fail-closed contra a whitelist `DATA_QUERY_TOOLS` e overhead sub-milissegundo (< 0.1ms).
- **Contrato de Resultado Agêntico (`AgentResult`):**
  - Criação da classe `AgentResult` em `src/adapter/inbound/llm/sales_agent.py`, fornecendo propriedades estruturadas `response: str` e `data_queried: bool`, desempacotamento de tupla `(response, data_queried)`, e paridade com operações de string para retrocompatibilidade total.
- **Enriquecimento do DTO de Resposta (`ChatResponseDTO`):**
  - Adição do atributo tipado `data_queried: bool = False` em `src/application/dto/chat_dto.py`, transportando o sinal determinístico de grounding pela fronteira da API REST (`POST /chat`).
- **Selo Acessível no Web Chat Frontend (`src/adapter/inbound/web/static/app.js`):**
  - Renderização dinâmica do badge `.verified-data-badge` ("Dados Verificados") com ícone SVG estático, semântica ARIA (`role="status"`, `aria-label="Dados verificados no banco de dados"`), e omissão limpa em diálogos casuais ou mensagens de erro.
- **Suíte de Testes Automatizados de Isolamento por Turno:**
  - Criação de `tests/integration/test_data_queried_flag.py` com 5 cenários completos validando chamadas de Domain Tools (`data_queried=True`), diálogos casuais (`data_queried=False`), isolamento estrito multi-turnos sem contaminação histórica (PRD04), contingência em falhas e teste de estresse de latência.
- **Artefatos de Governança ADD:** Inclusão das especificações `R013-data-queried-flag.md`, `T013-data-queried-flag.md`, `TEST013-data-queried-flag.md`, `S013-data-queried-flag.md`, `Q013-data-queried-flag.md` e `PS013-data-queried-flag.md`.

### Changed

- **Assinatura e Orquestração de `SalesAgent.ask` (`src/adapter/inbound/llm/sales_agent.py`):**
  - Atualizado para retornar `AgentResult` em vez de string pura, instanciando `ToolTrackingCallbackHandler` por requisição (`request-scoped`) no `RunnableConfig` para isolamento hermético entre turnos (ADR-02).
- **Mapeamento no Serviço de Aplicação (`src/application/service/web_chat_application_service.py`):**
  - Adicionado helper `_extract_response_and_flag` para extrair de forma resiliente a resposta e a flag `data_queried` do retorno do agente e mapeá-las para `ChatResponseDTO`.

### Security & Reliability

- **Mitigação de Overreliance e Alucinações (OWASP LLM09 / T013):** Desacoplamento entre a resposta textual gerada pelo LLM e o indicador estruturado de grounding emitido pelo orquestrador.
- **Política Estritamente Fail-Closed no Callback (S013-01 / CWE-1188):** A flag `has_queried_data` só é ativada se `tool_name` for resolvido e constar expressamente no conjunto `data_tools`, mantendo-se `False` caso o nome seja nulo ou indefinido.
- **Whitelist Não-Vazia Obrigatória (S013-02 / CWE-184):** Exigência de `self.data_tools and tool_name in self.data_tools`, impedindo que conjuntos vazios funcionem inadvertidamente como curingas (wildcards).
- **Defesa em Profundidade contra UI Badge Spoofing (S013-03 / CWE-79 / ASVS V5):** Remoção explícita de elementos `.verified-data-badge` inseridos no Markdown gerado pelo modelo via `DOMPurify` e `querySelectorAll.remove()`, garantindo que o selo seja renderizado unicamente via controle programático JavaScript baseado no DTO verificado.
- **Isolamento de Estado por Turno (ADR-02 / CWE-662 / PRD04):** Ciclo de vida request-scoped do handler impede vazamento de estado de consultas de banco para turnos casuais subsequentes na mesma sessão.

## [1.10.0] - 2026-08-31

### Added

- **Tipagem Estática Estrita e Qualidade de Código (T012 / R012):**
  - Implementação de tipagem estática rigorosa com MyPy em modo estrito (`strict = true`) em 100% da base de código (`src/`), eliminando erros de runtime como `TypeError` e `NoneType` attribute dereferences.
- **Consolidação de Tooling no `pyproject.toml`:**
  - Configurações centralizadas para MyPy (`strict = true`, `disallow_untyped_defs = true`, `no_implicit_optional = true`, `warn_return_any = true`) e Ruff (linter e formatador determinístico de alta performance, regras `E`, `W`, `F`, `I`, `B`, `UP`, com `line-length = 100` e aspas duplas).
- **Segregação de Dependências de Desenvolvimento (`requirements-dev.txt`):**
  - Criação do arquivo dedicado `requirements-dev.txt` isolando ferramentas de teste, linter e stubs de tipagem (`pytest`, `pytest-mock`, `mypy`, `ruff`, `types-redis`, `types-requests`) das dependências de runtime de produção (`requirements.txt`).
- **Quality Gate de CI/CD no GitHub Actions (`.github/workflows/ci-cd.yml`):**
  - Adição do job bloqueante `lint-and-typecheck` executando `ruff check .`, `ruff format --check .` e `mypy src/` com timeout de 5 minutos, exigido como pré-requisito estrito antes da execução de testes unitários (`test-suite`).
- **Suíte de Testes Automatizados de Tipagem e Qualidade (`tests/unit/test_type_safety_and_code_quality.py`):**
  - 14 cenários de testes unitários cobrindo integridade de configurações, assinaturas de portas e modelos de domínio, injeção de dependências em serviços, anotações de controllers FastAPI e barreiras de CI/CD.
- **Artefatos de Governança ADD:** Inclusão das especificações `R012-type-safety-and-code-quality.md`, `T012-type-safety-and-code-quality.md`, `TEST012-type-safety-and-code-quality.md`, `S012-type-safety-and-code-quality.md`, `Q012-type-safety-and-code-quality.md` e `PS012-type-safety-and-code-quality.md`.

### Changed

- **Isolamento de Imagem de Produção (`requirements.txt` / `Dockerfile`):**
  - Remoção de dependências de compilação, testes e linters do `requirements.txt` principal, reduzindo o footprint e a superfície de ataque dos contêineres Docker.
- **Remoção de Configurações Obsoletas:**
  - Exclusão de configurações legadas do Pyright (`[tool.pyright]`).

### Security & Reliability

- **Supply Chain Security & Hardening de Containers (S012-01 / CWE-1104 / CICD-SEC-03):** Isolamento de dependências de desenvolvimento prevenindo instalação de ferramentas desnecessárias em containers de produção.
- **Restrição de Overrides em Módulos de Autenticação e Criptografia (S012-02 / CWE-704 / ASVS V5):** Erradicação de supressões `ignore_missing_imports = true` para `jwt.*` e `cryptography.*`, garantindo integridade de verificação de tokens e manipulação de chaves RSA.
- **Defesa em Profundidade e Type Narrowing em Adaptadores de Borda (S012-03 / CWE-252 / CWE-754):** Validações defensivas contra queries vazias/nulas e fábrica nula em `sql_fallback_tool.py`, e salvaguardas de nullability em leituras/escritas do Redis em `redis_session_adapter.py`.
- **Princípio do Menor Privilégio no Pipeline CI/CD (S012-04 / CICD-SEC-01 / CICD-SEC-05):** Imposição explícita de `permissions: contents: read` nos jobs do GitHub Actions.

## [1.9.0] - 2026-08-30

### Added

- **Perfilamento Dinâmico de Dados e Injeção de Contexto (T011 / R011):**
  - Implementação de inspeção de metadados read-only em tempo de inicialização (`profile_dataset`), adaptando o prompt do Sales Agent à realidade empírica do banco de dados DuckDB sem mutação dos dados brutos (BR01).
- **Modelos de Domínio de Perfilamento (`src/domain/model/dataset_profile.py`):**
  - Criação dos Value Objects `DatasetProfile` e `DataInsights`, incluindo gerador de blocos Markdown estruturados `### DYNAMIC DATA INSIGHTS:` com sanitização linear de metadados.
- **Extensão da Porta de Saída (`src/application/port/outbound/sales_data_port.py`):**
  - Adição do método abstrato `profile_dataset() -> DatasetProfile`.
- **Adaptador de Persistência DuckDB (`src/adapter/outbound/persistence/duckdb_sales_adapter.py`):**
  - Implementação de profiling analítico veloz (< 100ms) com detecção de valores sentinela (ex: `'None'`, `'N/A'`) em colunas de texto como `promotion_type`, identificação de colunas invariantes (`service_level`) e limites temporais/cardinalidade. Cache in-memory e fallback gracioso em caso de erro na consulta exploratória.
- **Injeção de Contexto Dinâmico no Agente (`src/adapter/inbound/llm/sales_agent.py`, `src/adapter/inbound/cli/main.py`):**
  - Integração do `build_system_prompt` e instanciação do agente injetando os insights empíricos no `system_prompt` do LangChain.
- **Suíte de Testes Automatizados:**
  - Testes unitários em `tests/unit/test_dataset_profile.py`, `tests/unit/test_duckdb_sales_adapter.py` e `tests/unit/test_sales_agent.py`.
  - Testes de integração End-to-End em `tests/integration/test_dynamic_profiling.py`.
- **Artefatos de Governança ADD:** Inclusão das especificações `R011-dynamic-data-profiling.md`, `T011-dynamic-data-profiling.md`, `TEST011-dynamic-data-profiling.md`, `S011-dynamic-data-profiling.md`, `Q011-dynamic-data-profiling.md` e `PS011-dynamic-data-profiling.md`.

### Security & Reliability

- **Defesa contra Indirect Prompt Injection em Metadados (S011-01 / OWASP LLM01 / CWE-20):** Sanitização linear rigorosa de quebras de linha (`\r`, `\n`, `\t`), neutralização de marcadores de cabeçalho Markdown (`###`) e imposição de limite de tamanho em metadados extraídos da base.
- **Otimização de Escopo e Proteção de Recursos no Boot (S011-02 / CWE-400 / OWASP LLM04):** Whitelist tipada de colunas inspecionadas e persistência em cache de instância (`_cached_profile`) O(1).
- **Imutabilidade de Dados Brutos (S011-03 / BR01 / ADR-01 / CWE-284):** Perfilamento restrito a consultas analíticas `SELECT` sobre `information_schema` e `sales_data`, sem mutações DDL/DML.
- **Isolamento de Falhas e Mascaramento de Logs no Profiling (S011-04 / CWE-209 / NFR Reliability):** Profiling encapsulado em `try/except Exception` com sanitização defensiva de mensagens de log e fallback para `DatasetProfile()` vazio sem interromper o boot.
- **Validação Defensiva de Composição do Prompt (S011-05):** Preservação do prompt base sem quebras de layout na ausência de metadados ou tabelas vazias.

## [1.8.0] - 2026-08-30

### Added

- **Avaliações Determinísticas Golden (Golden Evals) para IA Analítica (T010 / R010):**
  - Implementação de framework automatizado de avaliação determinística para prevenção de alucinações matemáticas e *Prompt Drift* no Sales Data Analysis Agent.
- **Dataset Canônico de Benchmark (`tests/evals/golden_dataset.json`):**
  - Criação de suíte declarativa de benchmark com consultas analíticas canônicas cobrindo todas as 10 ferramentas de domínio e casos de uso ad-hoc.
- **Modelos de Domínio e Validação de Evals (`tests/evals/eval_models.py`):**
  - Schemas Pydantic `GoldenEvalRecord`, enumeração `GoldenEvalCategory` e função utilitária `load_golden_dataset`.
- **Interceptador de Ferramentas LangChain (`tests/evals/interceptor.py`):**
  - Callback handler `ToolInterceptionCallbackHandler` que captura metadados, payload JSON bruto e estruturado retornado pelas ferramentas antes da síntese do LLM.
- **Motor de Asserção Determinística com Tolerância de Float (`tests/evals/assertions.py`):**
  - Comparador recursivo com tolerâncias estritas (`abs_tol=0.01` e `rel_tol=1e-3`) e gerador de relatórios diagnósticos de erro formatados e sanitizados.
- **Runner de Testes Pytest Parametrizado (`tests/evals/test_golden_evals.py`):**
  - Runner automatizado com retry exponencial para erros transitórios de API do provedor LLM.
- **Quality Gate de CI/CD no GitHub Actions (`.github/workflows/evals.yml`):**
  - Pipeline de validação bloqueante executando `pytest tests/evals/test_golden_evals.py -v`.
- **Testes Unitários da Suíte de Evals:**
  - `tests/unit/test_eval_models.py`, `tests/unit/test_eval_interceptor.py`, `tests/unit/test_eval_assertions.py` e `tests/unit/test_golden_evals_runner.py`.
- **Artefatos de Governança ADD:** Inclusão das especificações `R010-golden-evals-deterministic.md`, `T010-golden-evals-deterministic.md`, `TEST010-golden-evals-deterministic.md`, `S010-golden-evals-deterministic.md`, `Q010-golden-evals-deterministic.md` e `PS010-golden-evals-deterministic.md`.

### Security & Reliability

- **Isolamento Hermético de Dados (S010-03 / CWE-200 / OWASP LLM06):** Execução estrita contra dataset fixo `tests/fixtures/eval_dataset.csv` sobre DuckDB em memória (`:memory:`), impedindo acesso a dados transacionais ou persistência em disco.
- **Mitigação de Negação de Serviço e Esgotamento de Tokens (S010-01 / OWASP LLM04 / CWE-400):** Limite de retentativas (`max_retries=3`), backoff exponencial delimitado a 10s e fail-fast imediato em erros de autenticação (401, 403).
- **Sanitização de Logs e Prevenção de Log Forging (S010-02 / CWE-209 / CWE-117):** Ofuscação de caminhos absolutos do host (`[REDACTED_PATH]`), supressão de CRLF e truncamento de payloads extensos em relatórios diagnósticos.
- **Proteção de Segredos no Pipeline CI/CD (S010-05 / CWE-522):** Injeção de `OPENAI_API_KEY` restrita ao step de avaliação no GitHub Actions com timeout de 10 minutos.

## [1.7.0] - 2026-08-30

### Added

- **Autocorreção Agêntica e Resiliência a Erros (T009 / R009):** Implementação de mecanismo de autocorreção em tempo real utilizando exceções nativas `ToolException` do LangChain no Inbound LLM Adapter.
- **Sinalização de Erro com `ToolException` (`src/adapter/inbound/llm/`):**
  - Refatoração da `SecuredSQLQueryTool` para lançar `ToolException` estruturado em erros de sintaxe SQL, violações de segurança e falhas de execução no DuckDB (ex: colunas inexistentes ou alucinadas).
  - Refatoração das 10 ferramentas de domínio em `domain_tools.py` (`@tool(handle_tool_error=True)`) com lançamento de `ToolException` em erros de validação e formatação de datas.
- **Handler de Telemetria e Observabilidade (`src/adapter/inbound/llm/sales_agent.py`):**
  - Implementação do handler `_handle_tool_error(error: ToolException) -> str` que intercepta falhas de execução, emite logs de warning com o marcador de telemetria `[AGENT_SELF_CORRECTION]` e formata o feedback de diagnóstico para re-injeção no contexto do LLM.
- **Suíte de Testes Automatizados de Autocorreção:**
  - Criação de `tests/integration/test_agent_self_correction.py` com simulador determinístico `FakeToolCallingChatModel` validando: (1) reparo de coluna SQL alucinada no mesmo turno; (2) autocorreção de formato de data; (3) esgotamento de retries com entrega de fallback executivo; (4) emissão de logs `[AGENT_SELF_CORRECTION]`.
  - Novos testes unitários em `tests/unit/test_sales_agent.py`, `tests/unit/test_sql_fallback_tool.py` e `tests/unit/test_domain_tools.py`.
- **Artefatos de Governança ADD:** Inclusão das especificações `R009-agentic-self-correction.md`, `T009-agentic-self-correction.md`, `TEST009-agentic-self-correction.md`, `S009-agentic-self-correction.md`, `Q009-agentic-self-correction.md` e `PS009-agentic-self-correction.md`.

### Changed

- **Diretrizes de Autocorreção no `SYSTEM_PROMPT` (`src/adapter/inbound/llm/sales_agent.py`):**
  - Inclusão da seção `DIRETRIZES DE AUTOCORREÇÃO E RECUPERAÇÃO DE ERROS`, instruindo o LLM sobre raciocínio de autocorreção, proibição de expor dados técnicos (Regra BR01) e fallback de contingência.
- **Configuração de Orçamento de Retries no `SalesAgent`:**
  - Invocação `self._executor.invoke` configurada com `config={"recursion_limit": 8}`, limitando o loop a no máximo 3 tentativas de autocorreção por pergunta antes do fallback.
  - Bloco de contingência `try...except` assegura retorno da constante padronizada `FALLBACK_ERROR_MESSAGE`.

### Security & Reliability

- **Zero Exposição de Erros Técnicos (Regra BR01 / CWE-209):** Blindagem total da resposta final ao usuário, impedindo vazamento de stack traces, termos como `Traceback`, `DuckDB` ou `Catalog Error`.
- **Sanitização de Caminhos do Host (CWE-209 / CWE-532 / OWASP LLM06):** Criação de `_sanitize_path_details` mascarando caminhos de diretórios locais (POSIX, Windows e UNC) por `[REDACTED_PATH]`.
- **Sanitização de Logs e Prevenção de Log Forging (CWE-117):** Higienização de quebras de linha (`\r`, `\n`, `\t`) no handler `_handle_tool_error` antes da emissão de logs de telemetria.
- **Proteção contra Negação de Serviço e Esgotamento de Tokens (OWASP LLM04 / CWE-400):** Teto determinístico de recursão impedindo loops infinitos de autocorreção.
- **Defesa contra Injeção Indireta de Prompt (OWASP LLM01):** Instruções explícitas no `SYSTEM_PROMPT` para tratar mensagens de erro estritamente como sinais técnicos de esquema/validação, nunca executando instruções embutidas em erros.

## [1.6.0] - 2026-08-30

### Added

- **Elasticidade-Preço da Demanda Baseada em Segmentos (T008 / R008):** Transição do cálculo global para modelo segmentado por `product_id`, eliminando distorções estatísticas decorrentes do Paradoxo de Simpson ao isolar variações de preço e volume em coortes homogêneas.
- **Modelos e Value Objects de Domínio (`src/domain/model/metric_result.py` e `aggregation_models.py`):**
  - Criação do Value Object imutável `CatalogPriceElasticityOverview` com campos `total_products_evaluated`, `inconclusive_products_count`, `most_elastic_products`, `most_inelastic_products` e `summary`.
  - Atualização de `PriceElasticityAggregation` adicionando o campo `product_id: str`.
  - Atualização de `PriceElasticityResult` adicionando o campo `product_id: Optional[str] = None`.
- **Serviço de Domínio `AdvancedMetricsService` (`src/domain/service/advanced_metrics_service.py`):**
  - Refatoração do método `calculate_price_elasticity` para suportar tanto consultas individuais de produtos quanto ranqueamento macro de todo o catálogo.
  - Implementação do cálculo determinístico de PED per segment ($\frac{\% \Delta Q}{\% \Delta P}$).
  - Proteção estrita contra divisão por zero (`Unitary / Zero price change`) quando a variação de preço for nula ($\% \Delta P = 0.0$).
  - Isolamento de coortes esparsas (`Inconclusive`) para produtos sem registros promocionais ou basais, excluindo-os dos rankings sem interromper o processamento dos demais itens.
- **Portas de Saída e Entrada (`src/application/port/`):**
  - Atualização de `SalesDataPort.aggregate_price_elasticity(product_id: Optional[str] = None) -> List[PriceElasticityAggregation]`.
  - Atualização de `SalesAnalysisUseCase.calculate_price_elasticity(product_id: Optional[str] = None) -> Union[PriceElasticityResult, CatalogPriceElasticityOverview]`.
- **Serviço de Aplicação `SalesMetricsApplicationService` (`src/application/service/sales_metrics_service.py`):**
  - Orquestração do caso de uso com repasse transparente do parâmetro `product_id` para o adaptador de banco e o serviço de domínio.
- **Pushdown de Agregação SQL no Adaptador DuckDB (`src/adapter/outbound/persistence/duckdb_sales_adapter.py`):**
  - Agrupamento nativo via SQL `GROUP BY product_id` com funções de agregação condicionais (`AVG() FILTER (...)`, `COUNT() FILTER (...)`).
  - Filtragem parametrizada segura contra SQL Injection via `WHERE product_id = ?`.
- **Ferramenta LLM Atualizada (`src/adapter/inbound/llm/domain_tools.py`):**
  - Assinatura da tool `calculate_price_elasticity(product_id: Optional[str] = None) -> str` com docstring contextualizada para consultas pontuais ou rankings de catálogo.
- **Suíte Completa de Testes Automatizados:**
  - Criação de `tests/integration/test_price_elasticity.py` validando cenários elásticos, inelásticos, variação zero, produtos inexistentes e visão macro do catálogo.
  - Testes unitários expandidos em `test_advanced_metrics_service.py`, `test_duckdb_sales_adapter.py`, `test_domain_tools.py` e `test_domain_models.py`.
- **Artefatos de Governança ADD:** Inclusão das especificações `R008-segment-based-price-elasticity.md`, `T008-segment-based-price-elasticity.md`, `TEST008-segment-based-price-elasticity.md`, `S008-segment-based-price-elasticity.md`, `Q008-segment-based-price-elasticity.md` e `PS008-segment-based-price-elasticity.md`.

### Changed

- **Eliminação do Paradoxo de Simpson em Análise de Elasticidade:** Superação do modelo legado que misturava preços de itens heterogêneos em médias globais antes de computar elasticidade.

### Security & Reliability

- **Prevenção de Injeção de SQL (OWASP A03 / ASVS V5):** Parametrização estrita de consultas SQL DuckDB na cláusula `WHERE product_id = ?`.
- **Prevenção de Negação de Serviço por Divisão por Zero (CWE-369):** Tratamento matemático de $\Delta P = 0.0$ e preços/quantidades base zeradas retornando classificações seguras (`Unitary / Zero price change` e `Undefined`).
- **Resiliência e Isolamento de Falhas (BR04):** Dados incompletos em um produto não contaminam nem invalidam o processamento do catálogo como um todo.
- **Sanitização e Normalização de Entradas (CWE-20):** Remoção de espaços em branco (`.strip()`) nos identificadores de produtos.

## [1.5.0] - 2026-08-30

### Added

- **Microsserviço de Autenticação Assimétrica JWT RS256 (T006 / R006):** Criação de arquitetura Zero Trust baseada em microsserviço independente (`auth-service/`) como detentor exclusivo da chave privada RSA-2048, emitindo tokens de acesso assinados (`RS256`).
- **Endpoint de Autenticação e Login (`POST /auth/login`):** Validação de credenciais administrativas em tempo constante (`hmac.compare_digest`) e emissão de tokens JWT com expiração temporal (`JWT_EXPIRATION_MINUTES`).
- **Endpoint de Distribuição de Chave Pública (`GET /auth/public-key`):** Distribuição da chave pública RSA em formato PEM para consumo e validação offline por microsserviços analíticos.
- **Modelos e Value Objects de Domínio (`src/domain/model/auth_models.py`):** Criação de `TokenClaims`, `AuthCredentials` e `TokenResponse` como estruturas de dados imutáveis (`frozen=True`).
- **Hierarquia de Exceções de Domínio (`src/domain/exception/auth_exceptions.py`):** Exceções `AuthenticationError`, `InvalidCredentialsError`, `InvalidTokenError`, `ExpiredTokenError` e `MissingTokenError`.
- **Serviço de Domínio `CredentialValidator` (`src/domain/service/credential_validator.py`):** Validador puro com mitigação de ataques de canal lateral/timing attack.
- **Portas de Saída e Entrada (`src/application/port/`):** Contratos de abstração `TokenSignerPort`, `TokenVerifierPort`, `PublicKeyProviderPort` e caso de uso `AuthenticateUserUseCase`.
- **Serviço de Aplicação `AuthenticationApplicationService` (`src/application/service/authentication_service.py`):** Orquestrador de autenticação e construção de claims.
- **Adaptador Criptográfico `JwtRs256TokenAdapter` (`src/adapter/outbound/auth/jwt_token_adapter.py`):** Assinatura e verificação de tokens RS256 via PyJWT e cryptography com whitelist estrita de algoritmos.
- **Gerenciador de Chaves `RsaKeyManager` (`src/adapter/outbound/auth/rsa_key_manager.py`):** Geração, persistência em disco e carregamento via variáveis de ambiente/Secrets de pares de chaves RSA-2048.
- **Provedor HTTP de Chave Pública `HttpPublicKeyProvider` (`src/adapter/outbound/auth/http_public_key_provider.py`):** Cliente com cache em memória e lazy loading para verificação offline sub-milissegundo (< 0.5ms).
- **Inbound Security Guard `JwtSecurityGuard` (`src/adapter/inbound/web/jwt_security_guard.py`):** Injeção de dependência FastAPI `verify_jwt_token` validando cabeçalho `Authorization: Bearer <token>` em rotas protegidas.
- **Docker Compose Multi-Container (`docker-compose.yml`):** Orquestração completa de 3 serviços (`auth-service:8001`, `sales-agent:8000`, `redis:6379`).
- **Manifestos Declarativos K3s/Kubernetes:** Manifestos `k8s/auth-deployment.yaml`, `k8s/auth-service.yaml` e atualização de `k8s/configmap.yaml` para orquestração em cluster.
- **Documentação de API Atualizada:** Criação de `docs/api/auth-service.md` e atualização de `docs/api/web-chat.md`.
- **Artefatos de Governança ADD:** Inclusão das especificações `R006-microservice-jwt-authentication.md`, `T006-microservice-jwt-authentication.md`, `TEST006-microservice-jwt-authentication.md`, `S006-microservice-jwt-authentication.md`, `Q006-microservice-jwt-authentication.md` e `docs/api/auth-service.md`.

### Changed

- **Proteção do Endpoint Analítico (`src/adapter/inbound/web/chat_controller.py`):** Rota `POST /chat` atualizada com `Depends(verify_jwt_token)` para impor validação Bearer e registrar log de auditoria com o `sub` do usuário.
- **Dependências do Projeto (`requirements.txt` e `auth-service/requirements.txt`):** Adicionadas as bibliotecas `PyJWT>=2.8.0` e `cryptography>=42.0.0`.
- **Configuração de Ambiente (`.env.example`):** Novas variáveis `AUTH_ENABLED`, `AUTH_SERVICE_URL`, `AUTH_USER`, `AUTH_PASSWORD`, `JWT_EXPIRATION_MINUTES`, `RSA_PRIVATE_KEY_PATH`, `RSA_PUBLIC_KEY_PATH`.

### Security & Reliability

- **Segregação Criptográfica Zero Trust (BR01 / NIST SP 800-207):** Chave privada isolada exclusivamente no processo do Auth Service; o pod do Sales Agent nunca recebe nem manipula a chave privada, impedindo forja de tokens.
- **Prevenção de Confusão de Algoritmo (CWE-347):** Decodificação restrita a `RS256`, bloqueando ataques de algoritmo `none` ou transmutação de chave pública para HMAC simétrico.
- **Mitigação de Timing Attack (CWE-208):** Comparação em tempo constante de usuário e senha via `hmac.compare_digest()`.
- **Sanitização de Mensagens e Prevenção de Enumeração (CWE-209):** Respostas de erro uniformes (`{"detail": "Credenciais inválidas"}` / `{"detail": "Token inválido ou expirado"}`).
- **Resiliência e Alta Disponibilidade:** O Sales Agent continua validando tokens vigentes com a chave pública em cache mesmo durante reinicializações da Auth Service.

## [1.4.0] - 2026-08-30

### Added

- **Validação SQL Robusta via AST Parsing (T005 / R005):** Substituição completa do validador baseado em Regex pelo analisador de Árvore de Sintaxe Abstrata (AST) determinístico com `sqlglot` configurado para o dialeto DuckDB.
- **Modelos e Enums de Domínio (`src/domain/model/sql_validation.py`):** Criação do enum `SqlViolationType` e dos value objects imutáveis `SqlValidationResult` e `ParsedSqlStatement` (`frozen=True`).
- **Hierarquia de Exceções de Domínio (`src/domain/exception/sql_validation_exceptions.py`):** Exceções tipadas `SqlValidationError`, `SqlSyntaxError` e `SqlSecurityViolationError` para transporte de metadados de violação estruturada.
- **Serviço de Domínio de Segurança (`src/domain/service/sql_security_validator.py`):** Serviço puro `SqlSecurityValidator` com regras determinísticas para validação de nós raiz (`SELECT`, `WITH`, `UNION`), bloqueio recursivo de 15 operações mutacionais e 10 funções de acesso a arquivos.
- **Porta de Saída `SqlParserPort` (`src/application/port/outbound/sql_parser_port.py`):** Interface abstrata desacoplando a camada de aplicação/domínio do motor de parsing de infraestrutura.
- **Adaptador de Parsing `SqlGlotParserAdapter` (`src/adapter/outbound/parser/sqlglot_parser_adapter.py`):** Implementação concreta de `SqlParserPort` utilizando `sqlglot` com suporte a DuckDB, extração recursiva de funções e isolamento estrito de literais.
- **Suíte de Testes Automatizados de Validação AST:** Novos testes em `tests/unit/test_sql_security_validator.py`, `tests/unit/test_sqlglot_parser_adapter.py` e `tests/integration/test_ast_sql_validation_e2e.py` validando SLA de latência (< 5ms), eliminação de falsos positivos e bloqueio de DDL/DML.
- **Artefatos de Governança ADD:** Inclusão das especificações `R005-ast-sql-validation.md`, `T005-ast-sql-validation.md`, `TEST005-ast-sql-validation.md`, `S005-ast-sql-validation.md` e `Q005-ast-sql-validation.md`.

### Changed

- **Refatoração de `SecuredSQLQueryTool` (`src/adapter/inbound/llm/sql_fallback_tool.py`):** Removidos regexes e heurísticas textuais; a ferramenta agora delega a análise estrutural para o `SqlParserPort` e as regras de segurança para o `SqlSecurityValidator` via injeção de dependência.
- **Fábrica `create_sql_fallback_tool`:** Atualizada para instanciar e injetar automaticamente o `SqlGlotParserAdapter` e o `SqlSecurityValidator`.
- **Dependências do Projeto (`requirements.txt`):** Adicionada a biblioteca `sqlglot>=26.0.0`.

### Security & Reliability

- **Eliminação de Falsos Positivos em Literais (AC02 / BR02):** Consultas contendo palavras-chave reservadas dentro de constantes de texto (ex: `WHERE product_id = 'DROP_01'`) executam com segurança sem serem rejeitadas indevidamente.
- **Defesa em Profundidade contra SQLi e Prompt Injection (OWASP LLM01 / A03):** Bloqueio garantido de operações mutacionais (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, etc.) em qualquer profundidade da árvore sintática (subselects, CTEs e UNIONs).
- **Proteção contra Stacked Queries e Acesso a Arquivos:** Bloqueio de declarações encadeadas (`statement_count > 1`) e de funções de leitura/escrita no disco do host (`read_csv`, `read_text`, `read_blob`, `read_parquet`, `read_json`, `glob`).
- **Sanitização de Respostas e Observabilidade:** Redação de paths internos do servidor (`[REDACTED_PATH]`), orientação amigável de autocorreção em erros de sintaxe e preservação do log `[MISSING_TOOL]`.

## [1.3.0] - 2026-08-30

### Added

- **Escalabilidade de Sessão Distribuída (T004):** Transição da camada de computação do Sales Agent para uma arquitetura completamente stateless baseada em 12-Factor App, desacoplando a persistência do histórico conversacional para o Redis.
- **Porta de Saída `SessionStorePort`:** Definição do contrato de persistência desacoplada em `src/application/port/outbound/session_store_port.py` com suporte a `get_history`, `save_history`, `clear_history` e `exists`.
- **Adaptador de Persistência `RedisSessionAdapter`:** Implementação em `src/adapter/outbound/redis/redis_session_adapter.py` com serialização/desserialização JSON de mensagens LangChain (`messages_to_dict` / `messages_from_dict`), renovação automática de TTL a cada interação (`SESSION_TTL_SECONDS`), e timeouts defensivos de socket (3s).
- **Provedor Plugável `SessionFactory`:** Fábrica centralizada em `src/adapter/outbound/session_factory.py` que resolve dinamicamente entre `RedisSessionAdapter` (`SESSION_STORE=redis`) e `SessionMemoryAdapter` (`SESSION_STORE=memory` / fallback padrão).
- **Modelos e Exceções de Domínio de Sessão:** Entidade imutável `SessionContext` com validação de identificador por regex (`^[a-zA-Z0-9_-]+$`, max 128 chars), prefixo namespaced isolado (`sales_agent:session:<session_id>`), e exceções de domínio em `src/domain/exception/session_exceptions.py` (`SessionDomainError`, `InvalidSessionIdError`, `SessionStorageError`, `SessionConnectionError`).
- **Manifestos Declarativos K3s/Kubernetes:** Criação da pasta `k8s/` contendo `redis-deployment.yaml`, `redis-service.yaml`, `app-deployment.yaml` (multi-réplica, probes de liveness/readiness, resource limits), `app-service.yaml` e `configmap.yaml`.
- **Suíte de Testes de Integração Multi-Réplica:** Criação de `tests/integration/test_distributed_session_integration.py` validando continuidade de contexto conversacional e paridade em múltiplos turnos entre réplicas independentes (Pod A e Pod B) compartilhando o Redis Store.
- **Artefatos de Governança ADD:** Inclusão das especificações `R004-distributed-session-scalability.md`, `T004-distributed-session-scalability.md`, `TEST004-distributed-session-scalability.md`, `S004-distributed-session-scalability.md` e `Q004-distributed-session-scalability.md`.

### Changed

- **Stateless Web Chat Application Service:** `WebChatApplicationService` refatorado para eliminar o armazenamento em heap `_active_sessions`, injetando dinamicamente o histórico a partir do `SessionStorePort` por requisição e persistindo o turno atualizado.
- **Injeção de Dependências no `chat_controller`:** Atualização do provider singleton para instanciar o serviço com o `SessionStorePort` resolvido via `SessionFactory`.
- **Dependências do Projeto (`requirements.txt`):** Adicionado pacote oficial `redis>=5.0.0`.

### Security & Reliability

- **Prevenção de Injeção de Chaves (OWASP A03):** Validação estrita do `session_id` e namespacing de chaves impedem poluição de cache ou colisão acidental entre instâncias de aplicação.
- **Proteção contra Esgotamento de Memória (OWASP API4):** Expiração automática por TTL configurável (padrão 86.400s / 24h) no Redis e capacidade limitada com política LRU (500 sessões) no adaptador em memória.
- **Sanitização de Erros e Prevenção de Vazamento (OWASP A05):** Mascaramento de erros de conexão e timeouts internos em mensagens neutras para o usuário final, com rastreabilidade estruturada nos logs do servidor.
- **Hardening de Infraestrutura:** Serviço Redis operando estritamente em rede interna ClusterIP, credenciais sensíveis gerenciadas via Kubernetes Secrets (`SecretKeyRef`), e limites de CPU/RAM declarados contra DoS.

## [1.2.0] - 2026-08-30

### Added

- **OLAP Pushdown Aggregations (T003):** Migração completa dos cálculos matemáticos de métricas básicas e avançadas para o motor SQL nativo do DuckDB, garantindo latência de sub-segundo e escalabilidade para 50M+ registros.
- **Domain Value Objects de Agregação:** Criação de 10 novos modelos imutáveis em `src/domain/model/aggregation_models.py` (`ProductAggregation`, `LocationSalesAggregation`, `TotalSalesAggregation`, `PlannedVsActualAggregation`, `PromotionImpactAggregation`, `ServiceLevelBottleneckAggregation`, `RevenueDeficitAggregation`, `AverageDiscountAggregation`, `SeasonalityAggregation`, `PriceElasticityAggregation`).
- **Contratos de Agregação em `SalesDataPort`:** Definição de métodos analíticos explícitos na porta de saída (`aggregate_top_selling_product`, `aggregate_top_locations`, `aggregate_total_sales`, etc.).
- **Queries SQL Vetorizadas no `DuckDbSalesAdapter`:** Implementação de consultas otimizadas utilizando `SUM`, `AVG`, `FILTER (WHERE ...)`, `GROUP BY` e `ORDER BY` diretamente no banco colunar em memória.
- **Suíte de Testes de Paridade e Integração:** Criação de `tests/integration/test_sales_metrics_integration.py` validando 100% de paridade matemática e funcional entre o pushdown SQL e as regras de negócio.
- **Artefatos de Governança ADD:** Inclusão das especificações `R003-analytical-engine-scalability.md`, `T003-analytical-engine-scalability.md`, `TEST003-analytical-engine-scalability.md`, `S003-analytical-engine-scalability.md` e `Q003-analytical-engine-scalability.md`.

### Changed

- **Refatoração de `BasicMetricsService` e `AdvancedMetricsService`:** Os serviços de domínio agora recebem DTOs pré-agregados compactos em vez de sequências de registros brutos (`Sequence[SaleRecord]`), mantendo o domínio puro e as regras de negócio isoladas.
- **Orquestração em `SalesMetricsApplicationService`:** Atualizado para delegar a recuperação de agregações para a `SalesDataPort` e repassar os resultados aos serviços de domínio.

### Removed

- **Eliminação de `get_all_sales()`:** O método `get_all_sales()` foi completamente removido de `SalesDataPort` e `DuckDbSalesAdapter` para mitigar definitivamente riscos de exaustão de memória (OOM). Para consultas filtradas de registros, utiliza-se `get_sales_by_filter()`.

### Performance & Security

- **Consumo de Memória O(1):** A aplicação Python não transfere mais datasets brutos sobre o barramento de memória, mantendo a pegada de memória constante mesmo sob cargas analíticas de dezenas de milhões de linhas.
- **Hardening DuckDB:** Parametrização integral das consultas de agregação e manutenção do bloqueio de acesso a arquivos externos (`enable_external_access = false`).

## [1.1.0] - 2026-08-28


### Added

- **Web Chat Interface:** Nova aplicação web (FastAPI + Vanilla JS) que expõe o Sales Data Analysis Agent via API REST (`POST /chat`), eliminando a dependência do terminal CLI.
- **Frontend Responsivo Premium:** UI com Dark Mode, micro-animações, suporte a Markdown nas respostas do bot e integração sem dependência de build (Node/npm).
- **Domain Value Object `SessionContext`:** Para rastrear as sessões via `session_id`.
- **DTOs de Entrada e Saída:** `ChatRequestDTO` e `ChatResponseDTO` definidos via Pydantic para comunicação tipada com a interface web.
- **API `WebChatUseCase` e Orquestração:** Implementação do `WebChatApplicationService` integrando as sessões da interface web diretamente ao agente LangChain de análise de vendas.
- **Armazenamento de Sessões e Descarte:** Implementação de `InMemorySessionHistoryAdapter` garantindo a persistência do histórico conversacional na memória, acoplado com uma estratégia de descarte LRU (Least Recently Used) com capacidade padrão de 500 sessões ativas para mitigar esgotamento de recursos.
- **Proteção XSS Frontend:** Sanitização via `DOMPurify` implantada globalmente antes da conversão e inserção do Markdown.
- **Proteções Headers HTTP e CORS:** Configuração aprimorada de middleware FastAPI com origens restritas explicitamente, além dos cabeçalhos anti-sniff e clickjacking.
- **Redirecionamento de Raiz:** Adicionado redirecionamento (`307 Temporary Redirect`) de `GET /` para a página inicial da interface em `/static/index.html`.
- **Integração End-to-End:** Novos testes de integração simulando múltiplos turnos e checando resiliência.
- **Documentação de API Atualizada:** Inclusão do documento `docs/api/web-chat.md`.

### Fixed

- **Web Chat Network Error (B001):** Corrigido o erro 500 ao iniciar sessões no chat web. A falha ocorria por falta de injeção de dependências do `SalesAgent` e ausência das chaves de API. A correção incluiu a restauração da inicialização via `bootstrap_agent()` no `chat_controller`, a inclusão do carregamento correto das variáveis de ambiente (`load_dotenv()`) no serviço web, e a implementação de uma barreira segura (`try...except`) que evita crashs da aplicação, retornando erros encapsulados e seguros para o frontend.
- **Desconto Médio e Análise de Promoções (B002):** Corrigida a falha no cálculo do valor total de desconto e da margem de desconto médio em promoções no `AdvancedMetricsService`. O cálculo anterior subtraía a receita real total da receita planejada globalmente, fazendo com que itens vendidos acima do valor planejado anulassem os descontos aplicados. A nova lógica acumula separadamente apenas transações com desconto efetivo (`actual_price < planned_price`), preservando a precisão analítica do agente nas estatísticas de vendas promocionais.
- **Gargalos de Nível de Serviço Logístico / SLA (B003):** Corrigido o resultado falso-positivo na identificação de gargalo de SLA em `AdvancedMetricsService.analyze_service_level_bottlenecks`. A verificação de desempate foi refinada para comparar a igualdade exata dos valores arredondados de 4 casas decimais (`min_sla == max_sla`), evitando que imprecisões de ponto flutuante em Python (ex: `0.9800 - 0.9799 < 1e-4`) considerassem erradamente médias distintas como empates. Quando todas as localidades possuem médias idênticas, retorna `worst_location="N/A"`; quando uma localidade apresenta média inferior (ex: `Whse_A` a 97,99%), ela é identificada corretamente como gargalo crítico.
- **Enriquecimento de Esquema do Fallback SQL (B004):** Corrigida a geração de consultas SQL incorretas no `SecuredSQLQueryTool` quando exposto a perguntas ad-hoc sem promoção. O esquema do campo `query` em `SQLQueryInput` e a descrição da ferramenta foram enriquecidos com definições completas de colunas, semântica de `promotion_type IS NULL` / `HAVING COUNT(promotion_type) = 0` e fórmulas de receita (`SUM(actual_quantity * actual_price)`). Adicionado payload de aviso estruturado (`EMPTY_RESULT_SET`) com orientações de auto-correção (`self_correction_guidance`) quando a consulta DuckDB retorna zero registros, prevenindo alucinações inversas do agente LLM.

### Security

- **Proteção e Sanitização do Fallback SQL (S004):** Adicionado bloqueio de ponto e vírgula intermediário (`;`) em consultas personalizadas no `SecuredSQLQueryTool` para mitigar tentativas de execução de instruções múltiplas empilhadas (*stacked queries*). Implantada sanitização automática por regex em mensagens de exceção para prevenir vazamento de caminhos locais do sistema de arquivos (`[REDACTED_PATH]`).

## [1.0.0] - 2026-08-27

### Added

- Arquitetura Hexagonal (Ports & Adapters) inicializada.
- Entidades de domínio e Value Objects (`SaleRecord`, `MetricResult`).
- Serviços de domínio para métricas básicas e complexas (10 regras determinísticas).
- Portas de entrada (`SalesAnalysisUseCase`) e saída (`SalesDataPort`).
- `SalesMetricsApplicationService` orquestrando casos de uso.
- `DuckDbSalesAdapter` implementando motor OLAP in-memory para ingestão de `sales.csv`.
- 10 ferramentas de domínio acopladas ao LangChain (`@tool`).
- `SecuredSQLQueryTool` atuando como fallback para consultas ad-hoc seguras (bloqueando DML/DDL).
- Configuração de LLM Agnóstico (OpenAI, Anthropic, Gemini) via `LLMFactory`.
- Interface interativa no terminal (CLI) usando agente orquestrador do LangChain.
- Cobertura abrangente de testes unitários e de integração (84 testes totais).
- Empacotamento em contêiner via `Dockerfile`.
- Documentação técnica, arquitetônica e guia de uso atualizados (`README.md`).

### Security

- Acesso à leitura arbitrária de arquivos pelo DuckDB foi bloqueado (`enable_external_access: false`).
- Parsing resiliente implementado para formatos de data brasileiros e ISO.
- Janela de memória conversacional implementada para prevenir exaustão de token/custo.
