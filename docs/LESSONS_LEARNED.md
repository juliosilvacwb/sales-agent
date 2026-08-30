# Lições Aprendidas & Retrospectiva do Projeto (Lessons Learned)

## Visão Geral da Jornada

A construção do **Sales Data Analysis Agent** foi desenhada para ir além de um simples "chatbot de IA". O objetivo inicial era provar que é possível aplicar **Engenharia de Software Clássica** (Arquitetura Hexagonal, SOLID, TDD) ao emergente ecossistema de Inteligência Artificial Generativa. 

A primeira versão (MVP) focou na entrega de valor e no desacoplamento. No entanto, o verdadeiro aprendizado surgiu após a fase de *Code Review* e avaliação técnica, onde métricas de escalabilidade e resiliência foram postas à prova, exigindo uma evolução de arquitetura de software para **Arquitetura de Sistemas de IA em Escala Enterprise**.

Este documento sumariza as decisões técnicas, os *trade-offs* e os intensos aprendizados colhidos ao longo dessa jornada.

---

## Fase 1: As Decisões Fundacionais (O que deu certo)

1. **Arquitetura Hexagonal (Ports & Adapters):**
   * **A Decisão:** Isolar a lógica de negócio e as agregações de vendas no *Domain Layer*, tratando o LLM (LangChain) e o Banco de Dados (DuckDB) apenas como adaptadores de entrada (*Inbound*) e saída (*Outbound*).
   * **O Aprendizado:** Essa foi a decisão mais valiosa do projeto. Ela permitiu que o sistema fosse testado em menos de 3 segundos (via mocks) e garantiu que pudéssemos trocar de LLM ou de Banco de Dados sem reescrever as regras de negócio.

2. **DuckDB como Motor OLAP (vs. Pandas):**
   * **A Decisão:** Usar DuckDB em memória para habilitar consultas SQL complexas.
   * **O Aprendizado:** Extremamente eficaz para *Text-to-SQL*. O LLM tem muito mais facilidade em gerar consultas SQL ANSI do que manipulações complexas de dataframes Pandas.

---

## Fase 2: Evolução Arquitetural e "Choque de Realidade" (Os Feedbacks e Correções)

A evolução do MVP gerou um *roadmap* de 14 estratégias de produto (Product Strategies - PS). Abaixo listamos as lições mais valiosas de Engenharia de Dados e IA extraídas desse processo:

### 1. Data Gravity e OOM (Out Of Memory)

* **O Erro Inicial:** Trazer todos os dados do banco para a memória da aplicação (`get_all_sales`) para realizar agregações no Python.
* **A Lição:** *Pushdown Aggregation*. Em arquiteturas de dados modernas, você leva a computação até o dado (via SQL), e não o dado até a computação. O Python deve apenas receber o resultado final consolidado para evitar OOM Crushes em datasets bilionários. *(PS003)*

### 2. Escalabilidade Sem Estado (Stateless)

* **O Erro Inicial:** Armazenar o histórico de mensagens da IA em memória local (dicionários do Python).
* **A Lição:** Sistemas web *precisam* ser Stateless. Para escalar com Kubernetes e múltiplas réplicas, a sessão (Chat History) deve obrigatoriamente residir em um cache externo e distribuído (Redis). *(PS004)*

### 3. A Ilusão da Segurança por Regex (SQL Guard)

* **O Erro Inicial:** Usar Expressões Regulares (`re`) para tentar bloquear comandos destrutivos (DROP, DELETE, INSERT) gerados pela IA.
* **A Lição:** Regex valida "Texto", não "Estrutura". Para garantir segurança 100% contra injeções SQL ofuscadas em um ambiente *Text-to-SQL*, a única abordagem segura é usar **AST (Abstract Syntax Tree) Parsing**, como a biblioteca SQLGlot, para verificar a árvore sintática do comando antes da execução. *(PS005)*

### 4. Rigor Matemático e Falhas Metodológicas (Elasticidade)

* **O Erro Inicial:** Calcular a "Elasticidade de Preço" somando a receita global e ignorando as variações entre categorias e produtos.
* **A Lição:** Cuidado com o Paradoxo de Simpson. Agregações macro (misturando itens de baixo e alto valor) destroem a validade matemática de métricas de dados. Agentes analíticos devem, por padrão, quebrar cálculos avançados em Segmentos (Agrupamento por Produto/Categoria). *(PS008)*

### 5. O Paradigma do *Agentic Self-Correction* (Tratamento de Erros)

* **O Erro Inicial:** Quando o banco de dados retornava um erro no SQL, a aplicação capturava a exceção e enviava a string de erro disfarçada de "sucesso" para a IA, que por sua vez repassava o erro nu e cru para o usuário final.
* **A Lição:** Frameworks de agentes precisam raciocinar sobre as próprias falhas. Levantando exceções específicas (`ToolException`), a IA entra em um "Self-Correction Loop", lendo a mensagem de erro, ajustando a query e tentando novamente, de forma transparente para o usuário final. *(PS009)*

### 6. A Batalha contra o *Prompt Drift* (Golden Evals)

* **O Erro Inicial:** Depender apenas de testes unitários (`pytest`) para validar a arquitetura, sem testar a inteligência do LLM.
* **A Lição:** Como o LLM é não-determinístico, qualquer mudança mínima no prompt pode "quebrar" a IA e fazê-la responder com o cálculo errado amanhã. A adoção de **Deterministic Golden Evals** em CI/CD é a única forma de garantir a confiabilidade matemática a longo prazo em operações *Text-to-SQL*. *(PS010)*

### 7. O Perigo de Suposições no Prompt (Dynamic Data Profiling)

* **O Erro Inicial:** "Chumbar" o Dicionário de Dados no System Prompt da IA (Ex: *"Valores nulos usam NULL"*), sem considerar que o dado real carregado poderia ter formatos diferentes (Ex: string `"None"`).
* **A Lição:** *Garbage In, Garbage Out*. Ao invés de fazer hardcode de esquemas, a aplicação deve possuir um script de *Data Profiling* rodando na inicialização. Ele varre o banco, verifica anomalias estatísticas do dado real, e **injeta esse contexto dinamicamente no prompt** para a IA não alucinar nas respostas. *(PS011)*

### 8. Transparência para Executivos (Data Queried Flag)

* **O Erro Inicial:** Devolver apenas a resposta em texto da IA, sem atestar de onde a informação veio.
* **A Lição:** Em ambientes Enterprise, a interface precisa exibir *Trust & Safety*. Criar uma flag (`data_queried: True/False`) e exibi-la como um "Selo de Garantia (Grounding)" no frontend tranquiliza o executivo de que a IA de fato utilizou o banco de dados, em vez de recorrer à sua própria memória. *(PS013)*

### 9. A Evolução Suprema da Orquestração (Migração para LangGraph)

* **O Erro Inicial:** Usar o `AgentExecutor` legado do LangChain, um "loop fechado (black-box)" engessado e difícil de debugar.
* **A Lição:** Para implementar os conceitos de Self-Correction (PS009) e Grounding (PS013) com excelência, e para manter total observabilidade do estado da aplicação, arquiteturas baseadas em **Máquinas de Estado e Grafos Ciclicos (LangGraph)** não são mais apenas opções, são o Estado da Arte exigido pelo mercado. *(PS014)*

### 10. Qualidade e Rigor (MyPy Strict e Ruff)

* **A Lição:** Um projeto maduro em Python que lida com inteligência estocástica precisa do máximo de garantias determinísticas na esteira de CI/CD. A adoção de checagem estática de tipos (`MyPy Strict`) aliada à linting e formatação veloz (`Ruff`) são diferenciais inegociáveis. *(PS012)*

---

## Conclusão e Filosofia do Projeto

A grande revelação deste projeto é que construir um Agente de IA não se resume a "fazer chamadas para a API da OpenAI".

O verdadeiro desafio de um Engenheiro de IA (AI Engineer) é dominar a fusão de três disciplinas brutalmente distintas: **Engenharia de Dados (OLAP, Pushdown, Profiling)**, **Engenharia de Software (SOLID, CI/CD, Hexagonal, Type Safety)** e **Pesquisa de IA (Prompt Engineering, Evals, Self-Correction Loops)**.

Os aprendizados deste ciclo transformaram um produto que era puramente um *MVP de demonstração* em um documento vivo sobre como as arquiteturas de ponta a ponta (E2E) operam hoje nos gigantes tecnológicos. O resultado não é apenas um código funcional, é um manifesto sobre escalabilidade, resiliência e foco no usuário.
