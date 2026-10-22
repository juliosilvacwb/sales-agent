# Product Strategy: Database Query MCP Tool

## Strategic Context

O **Sales Data Analysis Agent** (repositório atual) já produz, em produção, uma capacidade de alto valor e baixa dependência de domínio: a ferramenta `secured_sql_query`. Ela permite que uma LLM escreva e execute consultas SQL *ad-hoc* em uma base de dados com três garantias críticas:

1. **Validação estrutural determinística via AST** (`SqlSecurityValidator` + `SqlGlotParserAdapter`): somente operações de leitura (`SELECT`/`WITH`/`UNION`) são aceitas, com bloqueio de nós mutacionais em qualquer profundidade, bloqueio de funções de I/O de arquivos (`read_csv`, `glob` etc.) e rejeição de *stacked queries* (R005, PRD01–PRD07).
2. **Execução estritamente read-only** (`execute_read_only_query`) com `enable_external_access = false` após a ingestão, sanitização de erros (`[REDACTED_PATH]`) e truncamento controlado de resultados.
3. **Contrato de erro pensado para autocorreção do agente**: mensagens estruturadas que re-injetam contexto de *self-correction* no LLM (T009/R009), com resultado vazio guiado e sem exposição de stack traces.

A estratégia deste PS é **extrair exclusivamente essa capacidade** e transformá-la em um produto autônomo e reutilizável: um **servidor MCP (Model Context Protocol) de consulta a banco de dados**, protegido por **chave de API**, configurado via **variáveis de ambiente** para **múltiplos bancos**, e empacotado em **imagem Docker**.

O produto deve suportar **quatro bancos relacionais de mercado**: **Oracle DB**, **SQL Server**, **PostgreSQL** e **MySQL**. O suporte é por conexão individual — cada banco registrado declara seu **tipo** e sua **versão**, e o pipeline (validação AST por dialeto, execução read-only, descoberta de schema) adapta-se ao dialeto e às convenções nativas de cada um. A declaração da versão é obrigatória porque famílias como Oracle podem exigir **conectores/drivers distintos conforme a versão do servidor** (ex.: Oracle 11g, 12c, 19c, 21c e 23ai nem sempre são alcançáveis pelo mesmo driver/modo de conexão). Todos os quatro operam estritamente em modo de leitura.

Além da segurança estrutural (AST) e de execução read-only, o produto deve tratar **dados sensíveis como cidadãos de primeira classe**: senhas, tokens e API keys armazenados em tabelas podem ser retornados por um `SELECT` legítimo e injetados no contexto de um LLM (ou vazados em logs e evals). O servidor deve **sanitizar dados sensíveis na resposta**, usando o schema conhecido e heurísticas de coluna/valor, com política configurável por banco — herança direta dos padrões de redação já comprovados no Sales Agent (`_sanitize_s3_error` mascarando credenciais/signatures AWS e `_sanitize_path_details` redigindo caminhos).

**Decisão de estrutura: extração para repositório independente.** Esta capacidade não será uma pasta ou módulo dentro do `sales-agent`: será uma **nova aplicação em um repositório próprio**, com código auto-contido (domínio de validação, parser, catálogo de conexões, servidor MCP, imagem Docker), versionamento semântico próprio, pipeline de CI/CD independente e zero dependência do monólito de vendas. O repositório atual do `sales-agent` permanece intocado (PS001–PS015 imutáveis); o novo projeto nasce da **cópia controlada das peças relevantes** (`SqlSecurityValidator`, `ParsedSqlStatement`, `SqlSyntaxError`, padrões de sanitização e contrato de erro), generalizadas para os quatro dialetos.

**Decisão de responsabilidade: quem gera, quem valida, quem executa.** O servidor MCP **não possui LLM embutido** e não gera consultas. O modelo de responsabilidade é explícito:

1. **O agente cliente (host MCP) é o único que gera SQL**, pois detém o contexto do bug/incidente em investigação.
2. **O MCP valida** a query de forma **determinística** (parse AST + guardrail read-only por dialeto), **executa** de forma read-only e **responde** com dados estruturados ou erros categorizados.
3. **A autocorreção acontece no agente cliente**: ao receber um erro estruturado (sintaxe, violação, resultado vazio), o agente regenera a query no turno seguinte — o MCP não "pensa", não sugere SQL e não interpreta intenção.

Isso segue o mesmo princípio já provado no `sales-agent` (R009/T009): o guardrail de segurança é **estrutural e determinístico**, e a criatividade de geração fica com a LLM do cliente. Colocar LLM dentro do MCP traria custo de dupla invocação, latência extra, quebra de determinismo do guardrail e risco de vazamento de contexto entre agentes — portanto está fora de escopo.

**Catálogo de bancos na conexão.** Ao conectar ou inicializar a sessão MCP, o agente cliente deve receber o **catálogo de bancos disponíveis** — cada entrada com **nome lógico**, **descrição** (para que serve, o que contém, quando usar), **tipo** (`oracle`, `mssql`, `postgres`, `mysql`) e **versão** — para que a LLM saiba **como e o que** consultar antes de gerar qualquer SQL.

O público-alvo primário são **agentes de IA que investigam bugs** — agentes de suporte, *debugger agents*, engenheiros de plataforma e pipelines de observabilidade que precisam interrogar bancos (produção, staging, réplicas analíticas) de forma segura, iterativa e sem risco de mutação. O consumidor da ferramenta não é um usuário final conversando com um chat, mas sim outro agente (MCP host), o que altera o contrato de produto: respostas estruturadas, descoberta de schema sob demanda e erros auto-corrigíveis.

### O que está dentro do escopo

- Extrair a lógica de validação AST, execução read-only e contrato de erro do Sales Agent.
- Criar a nova aplicação em **repositório próprio**, auto-contido e desacoplado do `sales-agent`.
- Reexpô-la como ferramentas MCP (`execute_query`, descoberta de schema, validação de consulta).
- Autenticação por chave de API no transporte MCP.
- Registro de múltiplos bancos via variáveis de ambiente, com suporte nativo a Oracle DB, SQL Server, PostgreSQL e MySQL.
- Declaração de **tipo** e **versão** por banco registrado, com **seleção de conector/driver compatível com a versão** do servidor (ex.: Oracle 11g/12c/19c/21c/23ai) e falha rápida no startup quando a combinação não for suportada.
- **Sanitização de dados sensíveis** nas respostas: máscara de senhas, tokens e API keys retornados por consultas, baseada em schema conhecido e heurísticas de coluna/valor, com política configurável por banco (allowlist/denylist de colunas).
- Validação de consultas por dialeto do banco de destino (Oracle, T-SQL, PostgreSQL, MySQL).
- Empacotamento Docker com healthcheck e postura de segurança não-root.

### O que está fora do escopo

- Refatorar ou modificar estratégias já aprovadas do Sales Agent (PS001–PS015 permanecem imutáveis; o Sales Agent continua consumindo suas próprias ferramentas).
- Manter a orquestração conversacional (LangGraph, sessões, frontend) — o MCP entrega ferramentas, não um chat.
- Suportar operações de escrita/DDL em qualquer banco — o produto é estritamente read-only.
- Substituir as 10 Domain Tools do Sales Agent — este PS extrai somente o *fallback* SQL.
- Colocar a nova aplicação dentro do repositório atual do `sales-agent` — ela vive em repositório separado.
- Embutir LLM no servidor MCP — o MCP é determinístico (valida, executa e responde); a geração e a correção de SQL pertencem ao agente cliente.

## Market & Competitor Analysis

O **Model Context Protocol (MCP)** consolidou-se como o padrão aberto para conectar LLMs a ferramentas e dados. Lançado como padrão aberto no final de 2024 e posteriormente adotado por grandes provedores de plataformas de IA, o protocolo define como um *host* (cliente) descobre e invoca ferramentas de um *servidor*. Servidores MCP públicos para bancos de dados (mais notavelmente para `SQLite` e `PostgreSQL`) já existem no ecossistema, seguindo a especificação aberta disponível em `https://modelcontextprotocol.io`.

Fatos verificáveis que sustentam a estratégia:

- **Padrão aberto e crescente:** o MCP especifica ferramentas com *JSON Schema* e transporte entre host e servidor, o que torna um servidor de banco consumível por múltiplos hosts (IDE, CLI de agente, plataformas de orquestração) sem reimplementação por cliente.
- **Referência funcional interna (evidência empírica):** o Sales Agent já valida e executa consultas SQL dirigidas por LLM com guardrails AST em produção (R005/T005), autocorreção comprovada (R009/T009) e perfilamento de schema (R011/T011). Não se trata de uma aposta: é uma extração de capacidade validada.
- **Tendência de agentes de bug-hunting:** há movimento de mercado em ferramentas de *agentic observability* e agentes de investigação de incidentes que consultam bancos e logs iterativamente. Este produto se posiciona nessa categoria.
- **Demanda por SGBDs relacionais de mercado:** Oracle DB, SQL Server, PostgreSQL e MySQL estão entre os bancos relacionais mais presentes em estoques corporativos, em especial em ambientes de produção legados. Para um agente de investigação de bugs ser útil em stacks heterogêneos, a cobertura desses quatro dialetos é requisito de adoção, não um recurso opcional.

Hipóteses (a validar com usuários-alvo, sem dados de mercado verificados neste momento):

- **H1:** agentes que investigam bugs preferem contratos de erro estruturados e auto-corrigíveis a respostas textuais de erro de banco.
- **H2:** a descoberta de schema sob demanda (`list_tables`, `get_table_schema`) reduz significativamente consultas inválidas geradas por alucinação de colunas.
- **H3:** a ausência de autenticação é o principal bloqueador para adoção de servidores MCP de banco em ambientes corporativos.
- **H4:** a cobertura de Oracle DB e SQL Server é decisiva para adoção em stacks corporativos, mesmo que PostgreSQL e MySQL sejam usados com mais frequência em inovações em greenfield.
- **H5:** a ausência de sanitização de dados sensíveis (senhas, tokens, API keys) é um bloqueador de adoção tão relevante quanto a ausência de autenticação, pois governança de dados corporativos proíbe segredos em contexto de LLM e logs.
- **H6:** a diversidade de versões dentro de uma mesma família (ex.: Oracle 11g a 23ai) é a norma em estoques corporativos legados, tornando a compatibilidade por versão do conector um critério real de fechamento de adoção, não um requisito teórico.

## Ideation Results

### Categoria A — Núcleo extraído e contrato com o agente

#### Ideia 1: Servidor MCP de consulta somente-leitura (`execute_query`)

- **Problem Statement:** agentes que investigam bugs precisam interrogar bancos de forma iterativa, mas não podem ter risco de mutação, e a LLM não pode receber erros cruéis ou dados fora de contexto.
- **Proposed Solution:** expor a ferramenta `execute_query(database, query)` que aplica o pipeline herdado adaptado ao dialeto do banco de destino: parse AST, validação determinística read-only por dialeto (Oracle, T-SQL, PostgreSQL, MySQL), execução read-only, serialização JSON, truncamento de resultados e sanitização de caminhos/credenciais. O servidor é **puramente determinístico e sem LLM**: a query chega pronta do agente cliente, e o MCP apenas valida, executa e devolve o resultado ou o erro estruturado.
- **Inspiration/Evidence:** ferramenta `secured_sql_query` do Sales Agent (R005; `src/adapter/inbound/llm/sql_fallback_tool.py`; `src/domain/service/sql_security_validator.py`).

#### Ideia 2: Contrato de erro auto-corrigível para o agente cliente

- **Problem Statement:** uma consulta rejeitada ou com falha (coluna inexistente, sintaxe, resultado vazio) interrompe a investigação se o erro for opaco ao LLM.
- **Proposed Solution:** manter e generalizar o contrato atual: erros categorizados (`SQL_SYNTAX_ERROR`, `DISALLOWED_ROOT_OPERATION`, `FORBIDDEN_MUTATIONAL_NODE`, `STACKED_QUERIES_DETECTED`, `EMPTY_RESULT_SET`), com orientação explícita de correção, sanitização de detalhes e zero stack traces. O agente cliente usará essas mensagens para autocorrigir no próximo turno.
- **Inspiration/Evidence:** `ToolException` + `_handle_tool_error` + `self_correction_guidance` (R009/T009; `sales_agent.py`).

#### Ideia 3: Observabilidade e trilha de auditoria

- **Problem Statement:** ao expor acesso a bancos para agentes autônomos, é impossível investigar abusos ou falhas sem registrar o que foi executado.
- **Proposed Solution:** emitir log estruturado a cada chamada (agente/chave, banco, query, duração, status, linhas retornadas), com redação obrigatória de credenciais e paths (`[REDACTED_PATH]`), e marcador de telemetria para consultas fallback (reutilizar o conceito `[MISSING_TOOL]`).
- **Inspiration/Evidence:** logs `[MISSING_TOOL]` e funções `_sanitize_s3_error`/`_sanitize_path_details` do projeto atual.

### Categoria B — Segurança e governança de acesso

#### Ideia 4: Autenticação por chave de API no transporte MCP

- **Problem Statement:** sem autenticação, qualquer host MCP que alcance o servidor poderia consultar bancos produtivos — inaceitável para o uso de investigação de bugs.
- **Proposed Solution:** exigir chave de API (configurada via variável de ambiente, ex.: `MCP_API_KEYS`) em todas as chamadas; rejeitar requisições sem chave ou com chave inválida com resposta padronizada; suportar múltiplas chaves para revogação individual.
- **Inspiration/Evidence:** requisito explícito do solicitante; padrão 12-factor já usado no projeto (`AUTH_ENABLED`, `AUTH_PASSWORD`).

#### Ideia 5: Registro de múltiplos bancos via variáveis de ambiente

- **Problem Statement:** agentes de bug-hunting precisam consultar mais de um banco (e.g., produção, staging, réplica analítica) sem mudança de código ou rebuild.
- **Proposed Solution:** cada banco declarado por um bloco de variáveis de ambiente com alias lógico (ex.: prefixo `DB_<ALIAS>_`), incluindo **tipo de banco** (`oracle`, `mssql`, `postgres`, `mysql`), parâmetros de conexão, credenciais e limites próprios. O servidor valida as conexões no startup, falha rápido com diagnóstico claro, e disponibiliza o catálogo de aliases (com seus tipos) na ferramenta de descoberta.
- **Inspiration/Evidence:** requisito explícito do solicitante; padrão de configuração por env do projeto (`DATASET_PATH`, credenciais AWS em `.env.example`).

#### Ideia 6: Princípio do menor privilégio e validação read-only no runtime

- **Problem Statement:** a validação AST bloqueia mutações sintáticas, mas não protege contra um usuário de banco com permissões amplas caso o guardrail falhe.
- **Proposed Solution:** documentar e validar, no startup, que cada conexão registrada opera em modo read-only da perspectiva do próprio banco (mecanismo nativo de leitura somente, específico por tipo de banco — Oracle, SQL Server, PostgreSQL e MySQL), além de manter o guardrail AST como primeira linha de defesa.
- **Inspiration/Evidence:** postura de segurança em camadas do projeto (`SET enable_external_access = false;`, fail-closed).

#### Ideia 7: Proteção de recursos (linhas, tempo, varredura)

- **Problem Statement:** agentes autônomos podem gerar consultas caras (full scan sem limite) que degradam o banco ou estouram a resposta do MCP.
- **Proposed Solution:** impor limites configuráveis por banco: teto de linhas retornadas, timeout de execução, rejeição ou aviso para consultas sem restrição de volume, e limite por requisição/agente.
- **Inspiration/Evidence:** truncamento `MAX_RESULTS = 50` e guia `COUNT(*)` do `sql_fallback_tool.py`.

#### Ideia 16: Sanitização de dados sensíveis na resposta (senhas, tokens, API keys)

- **Problem Statement:** um banco legítimo pode conter colunas com senhas (hasheadas ou em claro), tokens de autenticação e API keys. Uma consulta ad-hoc `SELECT *` executada por um agente de investigação pode retornar essas colunas, que então fluem para o contexto do LLM, logs, evals e trilhas de auditoria — vazando segredos (CWE-200/532) sem qualquer violação do guardrail read-only.
- **Proposed Solution:** camada de sanitização na serialização da resposta, em duas frentes complementares: (1) **por esquema** — colunas declaradas sensíveis no catálogo do banco (allowlist/denylist configurável por banco, ex.: `password`, `token`, `api_key`, `secret`) têm valores mascarados; (2) **por heurística de valor** — regex/julgamento de padrões típicos (`Authorization:`, `Bearer `, JWT, chaves prefixadas tipo `AKIA`/`sk-`, strings de conexão) redigem valores mesmo quando a coluna não estava catalogada. O resultado mantém a estrutura (nomes de coluna e contagem) mas substitui o valor sensível por `[REDACTED]`, e o contrato de resposta sinaliza explicitamente quando houve redação. A mesma camada sanitiza logs e mensagens de erro para nunca vazar credenciais de conexão (senha do usuário do banco, `CONNECT_STRING`, tokens de sessão).
- **Inspiration/Evidence:** `_sanitize_s3_error` do `duckdb_sales_adapter.py` (máscara de credenciais AWS, signatures e session tokens via regex — CWE-209/532), `_sanitize_path_details` do `sql_fallback_tool.py` e testes correspondentes em `tests/unit/test_sql_fallback_tool.py` (S009-02) e `tests/unit/test_eval_assertions.py`.

### Categoria C — Ferramentas complementares de investigação

#### Ideia 8: Descoberta de schema sob demanda

- **Problem Statement:** o agente que investiga um bug não conhece o schema de bancos desconhecidos; sem ele, gera SQL inválido e desperdiça tentativas.
- **Proposed Solution:** expor ferramentas `list_databases`, `list_tables(database)` e `get_table_schema(database, table)` que retornam metadados read-only por banco, adaptadas ao catálogo nativo de metadados de cada tipo (Oracle, SQL Server, PostgreSQL, MySQL), permitindo ao agente planejar a consulta antes de executar.
- **Inspiration/Evidence:** perfilamento dinâmico de dados do Sales Agent (R011/T011) demonstrou a redução de alucinação quando o modelo conhece o schema.

#### Ideia 9: Modo de validação sem execução (`validate_only`)

- **Problem Statement:** o agente frequentemente quer confirmar se uma consulta é válida e segura antes de executá-la contra produção.
- **Proposed Solution:** parâmetro `validate_only` na ferramenta `execute_query` que executa apenas parse + validação AST (+ plano de execução quando suportado pelo banco), retornando um veredito sem tocar nos dados.
- **Inspiration/Evidence:** separação parse/validação/execução já existente no pipeline atual (`SqlParserPort` → `SqlSecurityValidator` → `execute_custom_query`).

#### Ideia 15: Catálogo de bancos informado na conexão

- **Problem Statement:** o agente cliente, ao conectar no MCP, não sabe quais bancos existem, o que cada um contém e para que serve; sem esse contexto, ele gera SQL às cegas (banco errado, schema errado, semântica errada).
- **Proposed Solution:** no momento da conexão/inicialização da sessão MCP (mecanismo de descoberta do protocolo), o servidor entrega o **catálogo de bancos disponíveis**, onde cada banco expõe: `nome` (alias lógico usado em `execute_query`), `descrição` (contexto de negócio: o que contém, quando usar, exemplos de tabelas), `tipo` (`oracle`/`mssql`/`postgres`/`mysql`), `modo_acesso` (sempre read-only), `limites` (máximo de linhas, timeout) e, opcionalmente, `schemas` disponíveis. O catálogo também é consultável sob demanda via ferramenta `list_databases`, e o `description` da ferramenta `execute_query` referencia o catálogo para reforçar a orientação da LLM.
- **Inspiration/Evidence:** requisito explícito do solicitante; o perfilamento dinâmico do Sales Agent (R011/T011) provou que injetar contexto estruturado reduz alucinação de nomes e filtros; o MCP oferece mecanismo nativo de descoberta de ferramentas na inicialização, que permite carregar esse catálogo sem chamada extra.

### Categoria D — Compatibilidade nativa com bancos relacionais

#### Ideia 13: Suporte nativo a Oracle DB, SQL Server, PostgreSQL e MySQL

- **Problem Statement:** agentes de bug-hunting operam em ambientes heterogêneos com bancos de dialetos e convenções distintos; um MCP que fala apenas "um SQL genérico" falha em validação e execução nos bancos reais.
- **Proposed Solution:** cada conexão registrada declara seu tipo (`oracle`, `mssql`, `postgres`, `mysql`). A validação AST e a execução usam o dialeto correspondente de cada banco, o contrato de erro respeita as mensagens nativas no formato de cada um, e a descoberta de schema consulta o catálogo de metadados nativo. Todos os quatro são tratados estritamente como leitura (somente `SELECT`/CTEs, sem DDL/DML).
- **Inspiration/Evidence:** requisito explícito do solicitante; o projeto atual já parametriza o dialeto no parser (`dialect="duckdb"`), demonstrando que a validação estrutural por AST é portável entre dialetos e não atende somente a um SGBD.

#### Ideia 17: Matriz de compatibilidade por versão do banco (conectores e drivers)

- **Problem Statement:** uma mesma família de SGBD (ex.: Oracle) possui muitas versões de servidor — 11g, 12c, 19c, 21c e 23ai — que podem exigir **conectores, drivers ou modos de conexão diferentes** (ex.: cliente fino vs. thick, versões de driver JDBC/ODBC com suporte a protocolo distinto, diferenças no TLS e em tipos nativos). Se o produto assumir "um conector por família", conexões reais em servidores legados falham sem diagnóstico, e o agente não consegue distinguir "banco fora do ar" de "conector incompatível".
- **Proposed Solution:** todo banco registrado declara **tipo + versão** (ex.: `oracle_19c`, `mssql_2019`, `postgres_15`, `mysql_8.0`), e o servidor mantém uma **matriz de compatibilidade conector↔versão**: no startup, valida se a combinação declarada é suportada pelo driver disponível, falha rápido com diagnóstico claro quando não for, e documenta versões testadas por família. A configuração permite fixar a versão do driver/protocolo quando necessário (sem sugerir tecnologia específica; a decisão de qual driver pertence ao Architect). A validação AST também incorpora `read_version` do dialeto quando o parser suportar (ex.: Oracle SQL com sintaxe 19c vs. 11g), evitando falso negativo em consultas válidas de versões mais novas.
- **Inspiration/Evidence:** requisito explícito do solicitante (diferentes versões da família Oracle podem exigir conectores diferentes); o mesmo princípio de seleção por configuração já usado no projeto (`dialect="duckdb"`); postura fail-fast do startup de conexões prevista na Ideia 5.

### Categoria E — Entrega, operação e qualidade

#### Ideia 10: Imagem Docker oficial com healthcheck e postura não-root

- **Problem Statement:** o produto precisa subir em qualquer ambiente de agentes sem fricção de instalação.
- **Proposed Solution:** imagem Docker env-driven com usuário não-root, `PYTHONDONTWRITEBYTECODE`, healthcheck de prontidão e EXPOSE documentado; a imagem inclui os conectores dos quatro bancos suportados (Oracle DB, SQL Server, PostgreSQL e MySQL) e credenciais nunca embutidas na imagem.
- **Inspiration/Evidence:** `Dockerfile` atual do projeto (usuário `appuser` UID 1000, sem cache de bytecode).

#### Ideia 11: Golden evals para o guardrail SQL

- **Problem Statement:** qualquer regressão no guardrail AST (falso positivo em literal, falso negativo em mutação) quebra a confiança do produto.
- **Proposed Solution:** suite automatizada de casos canônicos herdados e expandidos para **cada dialeto suportado** (Oracle, T-SQL, PostgreSQL e MySQL): consultas válidas com palavras proibidas em literais (`'DROP_ITEM'`), mutações em qualquer profundidade, stacked queries, sintaxe inválida, I/O de arquivos. Quality gate bloqueante no CI antes de publicar a imagem.
- **Inspiration/Evidence:** framework de Golden Evals determinísticos (R010/T010) e testes existentes `tests/unit/test_sql_fallback_tool.py` e `tests/integration/test_ast_sql_validation_e2e.py`.

#### Ideia 12: Guia de onboarding para hosts MCP

- **Problem Statement:** adoção rápida exige que o operador saiba configurar variáveis de ambiente e apontar seu host MCP para o servidor.
- **Proposed Solution:** documentação prática (exemplos completos de configuração de múltiplos bancos, chaves de API, transporte e troubleshooting) publicada junto ao repositório da imagem.
- **Inspiration/Evidence:** padrão de documentação operacional do projeto (`.env.example`, `k8s/secrets.example.yaml`, README com passos de deploy).

#### Ideia 14: Repositório independente e pipeline de release próprio

- **Problem Statement:** sem desacoplamento físico, a capacidade ficaria presa ao ciclo de release e às dependências do `sales-agent`, limitando a adoção por outras equipes e outros hosts MCP.
- **Proposed Solution:** fundar um **repositório novo e auto-contido** para a aplicação, contendo apenas as peças extraídas (domínio de validação, parser por dialeto, catálogo de conexões, servidor MCP, golden evals e Dockerfile), com versionamento semântico próprio, CI/CD independente e documentação própria. A extração é feita por cópia controlada das peças do `sales-agent` e generalização para os quatro dialetos, sem alterar a fonte.
- **Inspiration/Evidence:** requisito explícito do solicitante; o `auth-service/` do próprio `sales-agent` demonstra o padrão de componente desacoplado com ciclo de vida próprio dentro do ecossistema.

## Prioritization Matrix

Pontuação de 1 a 5 em todas as dimensões (quanto maior, melhor). `Effort` é invertido (5 = menor esforço; 1 = maior esforço). `Risk` é invertido (5 = menor risco; 1 = maior risco). Total = soma simples das cinco dimensões.

| Ideia | Business Value | User Impact | Strategic Alignment | Effort (5=menor esforço) | Risk (5=menor risco) | Total |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Ideia 15 - Catálogo de bancos informado na conexão | 5 | 5 | 5 | 5 | 5 | 25 |
| Ideia 2 - Contrato de erro auto-corrigível | 4 | 5 | 5 | 5 | 4 | 23 |
| Ideia 4 - Autenticação por chave de API | 5 | 4 | 5 | 4 | 5 | 23 |
| Ideia 16 - Sanitização de dados sensíveis na resposta | 5 | 5 | 5 | 3 | 4 | 22 |
| Ideia 1 - Servidor MCP de consulta read-only | 5 | 5 | 5 | 3 | 4 | 22 |
| Ideia 6 - Menor privilégio e read-only runtime | 4 | 4 | 5 | 5 | 4 | 22 |
| Ideia 3 - Observabilidade e auditoria | 4 | 4 | 5 | 4 | 4 | 21 |
| Ideia 5 - Multi-banco via variáveis de ambiente | 5 | 5 | 5 | 3 | 3 | 21 |
| Ideia 7 - Proteção de recursos | 4 | 4 | 5 | 4 | 4 | 21 |
| Ideia 10 - Imagem Docker com healthcheck | 4 | 4 | 5 | 4 | 4 | 21 |
| Ideia 11 - Golden evals para o guardrail | 4 | 3 | 5 | 4 | 5 | 21 |
| Ideia 13 - Suporte a Oracle, SQL Server, PostgreSQL e MySQL | 5 | 5 | 5 | 2 | 3 | 20 |
| Ideia 14 - Repositório independente e pipeline de release próprio | 4 | 4 | 5 | 3 | 4 | 20 |
| Ideia 8 - Descoberta de schema | 4 | 5 | 4 | 4 | 3 | 20 |
| Ideia 12 - Guia de onboarding | 3 | 4 | 4 | 5 | 5 | 21 |
| Ideia 9 - Modo validate-only | 3 | 4 | 4 | 4 | 4 | 19 |
| Ideia 17 - Matriz de compatibilidade por versão do banco | 4 | 4 | 5 | 2 | 3 | 18 |

Observação: Ideias 3, 5, 7, 10, 11 e 12 empatam em 21. A ordem de recomendação abaixo prioriza o encadeamento de valor da featureIdea (extração → autenticação → multi-banco → operação segura), não apenas o placar isolado.

A **Ideia 15** lidera a matriz (25 pontos) por ser barata, de baixo risco e determinante para o comportamento correto da LLM: sem o catálogo de bancos (nome, descrição, tipo), o agente cliente não sabe o que consultar. Ela integra o Pacote 1 e é entregue junto com a primeira ferramenta.

A **Ideia 16** pontua alto (22) e é tratada como **requisito de segurança de primeira classe do Pacote 1** (junto com o contrato de erro): sem ela, qualquer banco com colunas de segredos vazaria credenciais para o contexto do LLM e para logs — o que inviabilizaria a adoção corporativa (CWE-200/532), mesmo com todos os demais guardrails funcionando.

A **Ideia 13** pontua abaixo na dimensão Esforço (4 dialetos + conectores + testes por banco representam esforço alto e algumas incertezas de integração), mas é **requisito explícito e inegociável do solicitante**: a entrega do produto só é considerada completa quando os quatro bancos relacionais forem operáveis. Por isso ela é tratada como parte do núcleo do produto no Pacote 1, mesmo com placar de 20.

A **Ideia 17** pontua no fim (18) por combinar esforço alto (matriz conector↔versão + testes por versão) e risco médio de integração; contudo, é **requisito explícito do solicitante** e condiciona a operabilidade real em ambientes legados (ex.: Oracle 11g vs. 23ai). Ela não bloqueia o Pacote 1 para um caso feliz de versões modernas, mas deve constar no Pacote 3 e ser validada desde a Fase 3 do sequenciamento.

A **Ideia 14** (repositório independente) também é requisito estrutural do solicitante: a extração para repositório próprio não é opcional e antecede todo o trabalho de implementação — ela define a fundação do novo projeto (Fase 0 do sequenciamento).

## Recommendations

### Pacote 0 — Fundação do novo repositório (Ideia 14)

Antes de qualquer implementação, fundar o **repositório independente** da nova aplicação e executar a **extração controlada** das peças do `sales-agent` (domínio de validação SQL, modelos de validação, exceções, padrões de sanitização e contrato de erro), generalizadas para os quatro dialetos. Definir versionamento semântico próprio, pipeline de CI/CD independente e estrutura de pastas inicial.

- **Justificativa:** requisito estrutural do solicitante — a capacidade será uma aplicação autônoma. Desacoplar cedo evita que o novo projeto herde dívidas de dependências do monólito de vendas.
- **Dependências:** nenhuma (é a fundação); todos os demais pacotes dependem dela.
- **Validação sugerida:** o repositório novo compila, roda os testes de guardrail extraídos (portados) e não importa nenhum módulo do `sales-agent`.

### Pacote 1 — Núcleo extraído (Ideias 1, 2, 8, 13, 15 e 16)

Entregar o servidor MCP com as ferramentas `execute_query`, `list_databases`, `list_tables` e `get_table_schema`, reutilizando o domínio puro existente (`SqlSecurityValidator`, `ParsedSqlStatement`, `SqlSyntaxError`) e o parser AST como biblioteca de referência. O contrato de erro auto-corrigível (Ideia 2) deve ser tratado como requisito de primeira classe do contrato público, pois é o que torna o agente cliente eficaz em investigação iterativa de bugs.

O **catálogo de bancos** (Ideia 15) deve estar presente desde a primeira conexão: na inicialização da sessão MCP, o agente cliente recebe nome, descrição, tipo, versão, modo de acesso e limites de cada banco disponível — e a LLM usa essa informação para decidir **o que** consultar e **em qual** banco. O servidor permanece **sem LLM embutido**: a query chega pronta do cliente, e o MCP valida, executa e responde de forma 100% determinística.

A **sanitização de dados sensíveis** (Ideia 16) é requisito de segurança de primeira classe do contrato público, na mesma altura do contrato de erro: toda resposta percorre a camada de redação (por schema conhecido e por heurística de valor), logs e erros nunca expõem credenciais de conexão, e a resposta sinaliza quando houve redação (`[REDACTED]`). Sem ela, um `SELECT *` sobre uma tabela com tokens vazaria segredos para o contexto do LLM e para a trilha de auditoria — anulando na prática os demais guardrails.

O núcleo deve já nascer **multi-dialeto** (Ideia 13): para cada conexão registrada (Oracle DB, SQL Server, PostgreSQL ou MySQL), o pipeline roda a validação AST no dialeto correspondente, executa de forma read-only e adapta o contrato de erro às mensagens nativas do banco. A ordem de incorporação dos quatro bancos pode ser incremental — PostgreSQL e MySQL primeiro (ciclo de validação mais rápido), seguidos de SQL Server e Oracle — mas todos fazem parte do escopo de entrega do produto.

- **Justificativa:** é a extração mínima viável da capacidade comprovada; sem ela, nenhuma outra ideia faz sentido. O suporte aos quatro SGBDs relacionais é requisito explícito do solicitante e irrevogável. A sanitização de dados sensíveis é a garantia que torna o produto aceitável para operar sobre bancos corporativos reais.
- **Dependências:** depende do Pacote 0 (repositório novo e extração controlada). As ferramentas de descoberta de schema dependem do catálogo de conexões (Pacote 3) — na Fase 1, podem operar com um único banco padrão. A Ideia 16 depende do formato do registro de conexões (para o allowlist/denylist de colunas por banco), definido no Pacote 3 — na Fase 1, deve nascer com heurísticas de valor e um denylist global padrão.

### Pacote 2 — Autenticação (Ideia 4)

Proteger o transporte MCP com chave de API desde a primeira versão pública. A ausência de autenticação é um bloqueador de adoção corporativa (H3).

- **Justificativa:** alto valor de negócio e baixo risco/esforço (23 pontos). Sem isso, a ferramenta não pode ser operada contra bancos reais.
- **Validação sugerida:** teste de admissão com host MCP sem chave (rejeição) e com chave válida/inválida (aceitação e rejeição).

### Pacote 3 — Multi-banco e governança operacional (Ideias 5, 6, 7 e 17)

Registrar múltiplos bancos por variáveis de ambiente — incluindo todos os quatro tipos suportados (`oracle`, `mssql`, `postgres`, `mysql`) —, impor menor privilégio read-only no startup, e aplicar proteção de recursos (limite de linhas, timeout, aviso de full scan). O registro de conexões passa a exigir **tipo + versão** e o servidor valida a **matriz de compatibilidade conector↔versão** (Ideia 17): falha rápida com diagnóstico claro quando a versão declarada não é suportada, e documentação das versões testadas por família (ex.: Oracle 11g/12c/19c/21c/23ai). A camada de sanitização por banco (allowlist/denylist de colunas) também é configurada neste pacote, completando a Ideia 16.

- **Justificativa:** multi-banco é requisito explícito do solicitante e habilita o caso de uso real (produção + staging + réplica, e múltiplos SGBDs distintos na mesma instância do MCP); as proteções evitam incidentes quando agentes autônomos erram. A compatibilidade por versão é requisito explícito e condiciona a operabilidade real em ambientes legados da família Oracle.
- **Dependências:** o formato do registro de conexões (env, com campo `type` e `version` obrigatórios) deve ser definido antes das ferramentas de descoberta, de `execute_query` e da sanitização por banco.
- **Validação sugerida:** dois bancos de teste com aliases diferentes (ou tipos diferentes), uma consulta sem `LIMIT` (verificação do aviso/proteção) e um teste de conexão inválida (falha rápida com diagnóstico). Para a Ideia 17: um teste com versão declarada suportada (conexão OK) e outro com versão não suportada (falha rápida com mensagem apontando a matriz), além de pelo menos duas versões reais da mesma família (ex.: Oracle 11g e 19c) no pipeline de validação.

### Pacote 4 — Entrega e qualidade (Ideias 10 e 11)

Empacotar a imagem Docker com healthcheck e usuário não-root, e instalar a suite de golden evals do guardrail como quality gate de CI.

- **Justificativa:** viabiliza o deploy imediato e protege as regras de segurança contra regressão — pré-requisito para publicar qualquer imagem.
- **Dependências:** evals dependem do núcleo (Pacote 1); a imagem depende dos Pacotes 1 a 3.

### Sequenciamento recomendado

1. **Fase 0:** Pacote 0 (fundação do novo repositório, extração controlada e CI/CD próprio).
2. **Fase 1:** Pacote 1 (núcleo + contrato de erro + **catálogo de bancos na conexão** + **sanitização de dados sensíveis** + schema discovery básico), iniciando por um primeiro dialeto para validar o pipeline.
3. **Fase 2:** Pacote 2 (autenticação) e definição do formato multi-banco (com campos `type` e `version`).
4. **Fase 3:** Pacote 3 (multi-banco completo para os quatro SGBDs, **matriz de compatibilidade por versão**, menor privilégio, proteção de recursos e política de sanitização por banco).
5. **Fase 4:** Pacote 4 (Docker + golden evals por dialeto + documentação mínima).
6. Observabilidade (Ideia 3) entra transversalmente desde a Fase 1 (logs estruturados) e é completada na Fase 3 (auditoria de acesso por chave).

### Validação antes da especificação completa

- **Prova de conceito MCP:** conectar um host MCP real ao servidor local e executar uma consulta em um banco de teste, verificar o contrato de erro auto-corrigível com uma consulta inválida e confirmar que o agente cliente corrige no turno seguinte.
- **Teste do catálogo na conexão:** ao inicializar a sessão, verificar que o agente recebe a lista de bancos com `nome`, `descrição`, `tipo`, `modo_acesso` e `limites`, e que uma LLM de teste usa essas descrições para escolher o banco e gerar uma query coerente.
- **Matriz de dialetos:** validar a mesma query canônica e o mesmo caso adversarial nos quatro SGBDs (Oracle, SQL Server, PostgreSQL, MySQL), confirmando que validação, execução read-only e contrato de erro se comportam de forma consistente.
- **Sanitização adversarial:** executar `SELECT *` sobre tabelas de teste com colunas de senha/token/API key (nomeadas de formas óbvias e não óbvias), confirmar máscara por schema e por heurística de valor, ausência de segredos em logs, e resposta sinalizando redação. Incluir padrões reais (JWT, `Bearer`, `Authorization:`, chaves prefixadas) e valores embutidos em colunas de texto livre (ex.: logs de aplicação com tokens).
- **Matriz de versões:** conectar o mesmo MCP a duas versões da mesma família (ex.: Oracle 11g e 19c) confirmando seleção de conector, comportamento consistente do guardrail AST e mensagem de falha rápida para combinação não suportada.
- **Suite adversarial:** rodar as golden evals do guardrail contra a nova superfície (não apenas contra o código interno), para cada dialeto suportado.
- **Questionário com agentes de investigação:** confirmar H1, H2 e H4 (contrato de erro, schema discovery e a prioridade da cobertura Oracle/SQL Server) com usuários-alvo antes de investir em ferramentas avançadas (Ideia 9).

## Parking Lot

Ideias com potencial, mas não recomendadas para ação imediata — preservadas para futuras sessões de estratégia:

- **PUB-X: Publicação em diretório público de servidores MCP:** aumentar a descoberta do produto fora do time, depois de estabilizar o núcleo e a segurança.
- **AUTH-X: Autorização granular por banco por chave:** chaves com escopo (ex.: chave da equipe de billing acessa apenas o banco de billing). Pode ser adicionada sem quebrar o modelo de chaves único inicial.
- **WRITE-X: Suporte a write-path controlado:** útil apenas para bancos de staging/desenvolvimento; contraria o posicionamento read-only e deve ser avaliado separadamente.
- **ADMIN-X: Interface de administração de conexões:** em vez de env vars, um painel de gestão; aumenta a superfície de segurança e o escopo — avaliar somente quando houver demanda explícita.
- **COST-X: Estimativa de custo/volume antes da execução (modo `validate_only` avançado):** útil, porém menor prioridade que as proteções de recursos básicas do Pacote 3.
- **DOC-X: Guia de onboarding completo e multilíngue:** o mínimo documental deve acompanhar a entrega; a versão completa pode ser tratada como item de documentação posterior, fora da estratégia de produto.
- **DB-X: Suporte a outros SGBDs fora do escopo core (ex.: SQLite, bancos NoSQL/documento):** não faz parte do requisito; avaliar somente após a estabilização dos quatro bancos relacionais alvo.
- **REDACT-X: Detecção automática de dados sensíveis por amostragem de dados (sem catalogação explícita):** a Ideia 16 já prevê heurísticas de valor; uma camada de *data profiling* sensível (amostrar valores para descobrir colunas secretas não declaradas) amplia a superfície de processamento e deve ser avaliada separadamente, com cuidado de privacidade.
- **VER-X: Matriz de compatibilidade expandida para todas as versões históricas de cada família:** a Ideia 17 foca nas versões em uso corporativo (ex.: Oracle 11g+); cobrir versões descontinuadas exige manutenção contínua de conectores e deve ser decidido por demanda, não por padrão.

## Finalization

- **Status:** proposta de estratégia criada (aguardando refinamento do PO e validação da Quality Agent).
- **Local de entrega:** a implementação ocorrerá em **novo repositório independente** (a extrair do `sales-agent`), não neste repositório.
- **Commit Message:** `docs(strategy): extend PS016 with sensitive data sanitization and per-version database connector compatibility for Oracle/SQL Server/PostgreSQL/MySQL MCP tool`
- **Handoff:** prontas para refinamento do PO Agent:
  - `/po-agent create a PRD for bootstrapping the independent repository and controlled extraction of the SQL validation core (Ideia 14) based on PS016-database-query-mcp-tool.md`
  - `/po-agent create a PRD for the database query MCP server core covering Oracle DB, SQL Server, PostgreSQL and MySQL (execute_query + database catalog on connection + self-correctable error contract + sensitive data sanitization for passwords, tokens and API keys + LLM-free deterministic validation) based on PS016-database-query-mcp-tool.md`
  - `/po-agent create a PRD for MCP API key authentication and multi-database environment configuration (oracle, mssql, postgres, mysql) including the version compatibility matrix for database connectors and per-database sensitive column policy based on PS016-database-query-mcp-tool.md`