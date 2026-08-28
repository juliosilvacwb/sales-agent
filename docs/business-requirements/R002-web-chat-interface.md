# R002: Web Chat Interface para o Sales Agent

## Summary

**Origin:** [PS002-web-chat-interface.md](../product-strategy/PS002-web-chat-interface.md), Recommendation: Idea 2 (Arquitetura Desacoplada Leve - FastAPI + Vanilla JS/HTML/CSS)

Este documento especifica a construção de uma interface web interativa para o Sales Data Analysis Agent (R001). O objetivo central é superar a barreira de adoção da interface de Linha de Comando (CLI) atual, democratizando o acesso aos dados para usuários de negócios, gerentes e executivos por meio de uma aplicação web acessível diretamente pelo navegador.

A solução entregará valor através de uma arquitetura desacoplada e leve (API First), expondo o agente LangChain já existente via FastAPI e consumindo-o através de um frontend estático e premium feito com Vanilla JS, HTML e CSS. Essa abordagem garante alta flexibilidade e escalabilidade sem a complexidade excessiva de frameworks pesados de frontend.

## Functional Requirements

- **PRD01** - O sistema deve expor as capacidades do agente de vendas através de uma API REST (ou WebSockets) desenvolvida em FastAPI.
- **PRD02** - A API deve prover no mínimo um endpoint dedicado ao chat (ex: `POST /chat`), que receberá as mensagens do usuário e retornará a resposta gerada pelo LLM/Agente.
- **PRD03** - A API deve implementar um mecanismo de gerenciamento de sessão (`session_id`) para garantir a manutenção do contexto e do histórico conversacional (Context Memory) entre as chamadas do cliente web.
- **PRD04** - O sistema deve incluir uma interface de usuário (Frontend) desenvolvida exclusivamente com HTML, CSS Vanilla e Javascript (sem a obrigatoriedade de Node/npm ou React/Vue para a página principal do chat).
- **PRD05** - O frontend deve suportar a renderização de Markdown na tela do chat, permitindo a exibição adequada de tabelas, listas e formatações de texto retornadas pelo agente.
- **PRD06** - O frontend deve possuir um layout responsivo que se adapte corretamente a diferentes tamanhos de tela (desktop e mobile).
- **PRD07** - O frontend deve apresentar a exibição clara e separada das mensagens enviadas pelo usuário e das respostas enviadas pelo agente (estilo balões de chat ou fluxo similar).

## Non-Functional Requirements

- **Estética Premium (Aesthetics):** A interface deve obrigatoriamente prover uma experiência de usuário (UX) moderna, contendo Dark Mode, paleta de cores harmoniosa e animações fluidas (micro-animações, hover effects, transições de mensagens), superando uma aparência simples de MVP.
- **Performance Front-End:** A aplicação web deve ser altamente responsiva e rápida ao carregar, alavancando a leveza do Vanilla JS.
- **Percepção de Latência:** O frontend deve exibir indicadores visuais claros de processamento (ex: "Digitando...", loading spinners) enquanto aguarda a resposta assíncrona da API, mitigando a ansiedade do usuário. (Opcional, porém desejável: suporte futuro a Streaming de Respostas).
- **Desacoplamento e Independência (Clean Architecture):** O frontend deve atuar unicamente como camada de apresentação, sem conter regras de negócio complexas de orquestração de IA. Toda a lógica conversacional e analítica deve estar confinada no backend e em sua orquestração (LangChain).

## Business Rules

- **BR01 (Retrocompatibilidade):** A nova interface web e a integração com FastAPI não devem comprometer a lógica pré-existente de *Domain Tools* nem as medidas de segurança (*Secured SQL*) estabelecidas no R001. Ambas as interfaces (nova Web e antiga CLI) podem coexistir e consumir o mesmo *Core* do agente.
- **BR02 (Acesso e Distribuição):** No atual escopo inicial, a autenticação sofisticada de usuários e controle minucioso de acessos estão fora do MVP e enviados para o "Parking Lot", assumindo-se o uso do frontend em rede segura ou para uso interno.

## User Flow

### Happy Path (Interação Contínua)

1. O usuário acessa a URL web do Sales Agent a partir do seu navegador, visualizando uma interface limpa, premium (Dark Mode) e convidativa.
2. O usuário digita uma pergunta analítica ("Quais os 3 produtos mais vendidos no mês passado?") na barra de envio e pressiona Enter (ou clica no botão Enviar).
3. O frontend exibe a mensagem do usuário no painel de chat e aciona imediatamente um indicador de carregamento (ex: animação "Agent is thinking...").
4. O cliente Vanilla JS faz uma requisição assíncrona (Fetch/AJAX) para o endpoint `POST /chat` do FastAPI, passando a mensagem e seu `session_id`.
5. O FastAPI orquestra a chamada com o LangChain/DuckDB e aguarda a geração da resposta.
6. A resposta do agente, contendo formatação (ex: uma tabela em Markdown), é devolvida como JSON para o frontend.
7. O frontend interpreta o Markdown, renderiza a tabela elegantemente formatada no fluxo da conversa e oculta o indicador de carregamento.
8. O usuário continua o diálogo no mesmo contexto e envia uma segunda pergunta. A sessão é mantida com sucesso pelo FastAPI.

### Exception Path 1 (Erro de Conexão ou Timeout)

1. O usuário submete uma pergunta complexa e a comunicação de rede falha (ou o tempo de processamento do LLM excede o timeout do navegador).
2. O frontend captura a falha da requisição.
3. O frontend informa o usuário de maneira não intrusiva com uma mensagem estilizada na própria interface de chat (ex: "Desculpe, ocorreu uma falha de conexão temporária. Tente novamente."), removendo o loading e restaurando o campo de envio.

## Acceptance Criteria

- [ ] A aplicação backend (FastAPI) expõe com sucesso um endpoint que recebe e responde requisições oriundas da interface de chat.
- [ ] O contexto conversacional (memória do histórico de chat) funciona adequadamente em testes de múltiplos turnos de interação através da interface web.
- [ ] O código frontend é entregue em tecnologias puras (HTML, CSS e JS Vanilla) sem a dependência de um processo de build complexo (Node/React).
- [ ] O frontend é responsivo e renderiza visualmente de forma esteticamente impecável (incluindo renderização de sintaxe Markdown nas respostas da IA).
- [ ] Micro-animações e feedback visual de carregamento são visíveis para o usuário enquanto o agente processa a solicitação.
- [ ] É possível testar a aplicação de ponta-a-ponta (do browser até as agregações no DuckDB e retorno ao navegador).
