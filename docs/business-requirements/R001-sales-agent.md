# R001: Sales Data Analysis Agent

## Summary

**Origin:** [PS001-sales-agent.md](../product-strategy/PS001-sales-agent.md), Recommendation #1

Este documento especifica a construção de um Agente de Inteligência Artificial para a análise de dados de vendas (Sales Data Analysis Agent). O problema central a ser resolvido é democratizar o acesso aos dados tabulares (atualmente extraídos via `sales.csv`), permitindo que usuários de negócio sem habilidades técnicas de banco de dados façam perguntas analíticas em linguagem natural.

A solução proposta entregará valor ao adotar uma arquitetura Híbrida Refinada, onde as métricas mais comuns são atendidas com 100% de precisão por meio de ferramentas de domínio acopladas (Domain Tools), e consultas *ad-hoc* não previstas são atendidas através de um *SQL Fallback* com proteções rígidas (Secured SQL). O motor analítico será suportado por um banco de dados in-process otimizado para agregações (DuckDB).

## Functional Requirements

- **PRD01** - O sistema deve ingerir dados do arquivo `sales.csv` diretamente para um banco de dados analítico in-process (DuckDB).
- **PRD02** - O sistema deve prover uma interface de interação via chat (CLI ou API) onde o usuário consiga enviar perguntas analíticas em linguagem natural.
- **PRD03** - O sistema deve suportar um conjunto de ferramentas de domínio específicas (*Domain Tools*) para responder às perguntas de negócio mapeadas de forma exata e previsível, sem gerar dinamicamente cálculos ou SQLs para elas.
- **PRD04** - O sistema deve disponibilizar as seguintes ferramentas de domínio:
  - Identificar o produto mais vendido. (`get_top_selling_product`)
  - Identificar o local de maior volume de vendas. (`get_top_locations_by_volume`)
  - Calcular o total de vendas em um período. (`get_total_sales_in_period`)
  - Comparar a quantidade planejada vs. quantidade realizada. (`compare_planned_vs_actual_quantity`)
  - Analisar o impacto das promoções no preço e volume vendido. (`analyze_promotion_impact`)
  - Identificar qual local apresenta o pior SLA logístico (nível de serviço) médio. (`analyze_service_level_bottlenecks`)
  - Calcular a perda financeira estimada devido a déficits no planejado vs. realizado. (`calculate_revenue_deficit`)
  - Calcular a margem de desconto médio aplicado frente ao preço planejado. (`calculate_average_discount`)
  - Identificar padrões de sazonalidade de vendas. (`identify_sales_seasonality`)
  - Calcular a correlação/elasticidade entre o desconto e o aumento real do volume. (`calculate_price_elasticity`)
- **PRD05** - O sistema deve possuir uma ferramenta de contingência (Secured SQL Query Tool) capaz de traduzir perguntas não cobertas pelas Domain Tools para consultas SQL de leitura.
- **PRD06** - O sistema deve prover, via *System Prompt*, um Dicionário de Dados da tabela de vendas (`sales_data`) para orientar o LLM ao utilizar a Secured SQL Query Tool de fallback.
- **PRD07** - O sistema deve ser independente de provedor (*agnóstico a modelo*), permitindo a alternância de provedores (ex: OpenAI, Anthropic, Gemini, Ollama) exclusivamente via variáveis de ambiente, sem alterar o código principal.
- **PRD08** - O sistema deve registrar um log contendo a tag `[MISSING_TOOL]` acompanhado da pergunta original do usuário sempre que a ferramenta SQL Fallback for acionada, permitindo análise posterior para descoberta de novas Domain Tools.

## Non-Functional Requirements

- **Performance:** O processamento das consultas analíticas deve possuir latência submilisegunda para agregações usuais, alavancando a execução vetorizada e armazenamento colunar do DuckDB.
- **Segurança da Informação (SQL Injection Mitigation):** A Secured SQL Query Tool DEVE atuar como um *middleware* defensivo, utilizando uma conexão configurada estritamente para Leitura (Read-Only) junto ao banco de dados.
- **Segurança Corporativa (Bloqueio DML/DDL):** O sistema deve rejeitar categoricamente (através de regras a nível de aplicação ou a nível de SGBD) qualquer tentativa de executar instruções `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ATTACH` e `COPY`.
- **Manutenibilidade (Clean Architecture):** A lógica de negócio (como os cálculos matemáticos das Domain Tools) e a orquestração do Agente LLM devem estar claramente desacoplados em classes/módulos separados.
- **Portabilidade & Deploy:** A arquitetura deve ser autocontida, dispensando o gerenciamento de processos de servidores externos para o banco de dados (Serverless in-process via DuckDB). A aplicação deve ser entregue acompanhada de um `Dockerfile` funcional que empacote o sistema e permita sua execução isolada em contêineres.
- **Documentação Técnica:** O projeto deve conter um `README.md` detalhado, explicando a arquitetura adotada, instruções de uso, de execução (local e via Docker), forma de alternar os provedores de LLM e as dependências principais.

## Business Rules

- **BR01 (Priorização Estrita de Roteamento):** O fluxo de orquestração do LLM deve, obrigatoriamente, ser instruído de que o agente priorize ao máximo a utilização de Domain Tools, invocando a ferramenta SQL Fallback APENAS como última opção, quando a pergunta do usuário for ad-hoc.
- **BR02 (Desacoplamento de Conhecimento):** Qualquer alteração nos métodos de cálculo de indicadores do negócio deve ser feita diretamente no backend Python nas classes de domínio apropriadas, sem exigir ajustes no prompt da IA. A IA atua puramente como roteador semântico das intenções para as ferramentas.

## Critical Data (Conceptual)

Os indicadores baseiam-se diretamente na topologia de ingestão de dados em memória, necessitando reconhecer:

- `product_id`: Identificador único do produto
- `local`: Localização da venda
- `date`: Data da venda
- `planned_quantity`: Volume esperado (orçado)
- `actual_quantity`: Volume efetivado (realizado)
- `planned_price`: Preço original da mercadoria
- `actual_price`: Preço efetivo pago na ponta (com descontos/acréscimos)
- `promotion_type`: A categoria/tipo de promoção aplicada (se houver)
- `service_level`: SLA logístico e nível de serviço mensurado

## User Flow

### Happy Path (Consulta via Domain Tool)

1. O usuário acessa a interface de interação do Agente.
2. O usuário envia uma pergunta analítica mapeada (Ex: "Qual foi o impacto das promoções nas vendas?").
3. A IA identifica a intenção semântica e seleciona a Domain Tool correspondente (`analyze_promotion_impact`).
4. A ferramenta de negócio processa a requisição usando o repositório DuckDB e retorna dados exatos (determinísticos).
5. A IA sumariza e formula a resposta natural utilizando os dados obtidos e a entrega ao usuário.

### Exception Path 1 (Consulta Ad-Hoc - Fallback)

1. O usuário submete uma pergunta não prevista no conjunto das 10 ferramentas de domínio principais.
2. A IA avalia e reconhece que não possui uma Domain Tool apta.
3. A IA constrói uma query baseando-se no Dicionário de Dados contido no seu System Prompt, invocando a `SecuredSQLQueryTool`.
4. A infraestrutura assegura que a consulta é somente de leitura (Read-Only) e não agride as regras de segurança, executando no DuckDB e retornando as linhas pertinentes.
5. A IA formula a resposta final com base no resultado da query.

### Exception Path 2 (Tentativa de Violação de Sistema / DML)

1. O usuário maliciosamente tenta interagir solicitando a remoção ou modificação de dados (Ex: "Atualize a tabela e apague as vendas de ontem").
2. A IA, por meio da `SecuredSQLQueryTool`, tenta gerar e rodar comandos DML/DDL.
3. O bloqueio de sistema intercepta e nega a transação, rejeitando os comandos indesejados.
4. A IA retorna uma mensagem ao usuário indicando falha por políticas de segurança estritas.

## Acceptance Criteria

- [ ] A arquitetura consegue ingerir, sem esforço adicional, os dados contidos no arquivo `sales.csv` localmente em memória utilizando o DuckDB (processo isolado, sem necessidade de servidores externos).
- [ ] Há evidência técnica comprovando que todas as 10 funcionalidades descritas na PRD04 possuem uma *Domain Tool* independente, tipada e com classe correspondente que encapsula a regra de cálculo, livre de "geração dinâmica de IA".
- [ ] Em testes, uma solicitação ad-hoc resulta no uso correto da `SecuredSQLQueryTool` sem alucinações estruturais, pois a IA respeita o Dicionário de Dados fornecido.
- [ ] Qualquer tentativa de instrução DML/DDL submetida (ex: comando contendo `UPDATE`) através do Agente falha e não compromete a estrutura dos dados.
- [ ] É possível trocar a engine que roda a IA (por exemplo, de Anthropic para OpenAI) alterando unicamente um arquivo `.env` de configuração, com o sistema subindo com total sucesso.
- [ ] O repositório possui um `Dockerfile` válido e funcional que empacota toda a aplicação.
- [ ] Existe um `README.md` exaustivo contendo guia de uso, instruções de execução via Docker e local, e a documentação técnica da arquitetura.
- [ ] O sistema produz logs identificados com a tag `[MISSING_TOOL]` registrando a pergunta do usuário quando o Fallback (SecuredSQLQueryTool) é utilizado.
