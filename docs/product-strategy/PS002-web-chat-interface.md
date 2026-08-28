# Product Strategy: Web Chat Interface para o Sales Agent

## Strategic Context

**Executive Summary:** O Sales Data Analysis Agent foi originalmente desenhado com uma interface interativa de Linha de Comando (CLI). Embora funcional para desenvolvedores, essa interface representa uma barreira de adoção significativa para o público-alvo real: usuários de negócios, gerentes de vendas e executivos. Para democratizar verdadeiramente o acesso aos dados, precisamos evoluir a interface do agente para uma aplicação web acessível via navegador, mantendo a arquitetura robusta de backend (DuckDB + LangChain + Domain Tools) já definida.

## Market & Competitor Analysis

Aplicações analíticas baseadas em IA no mercado corporativo (como ChatGPT Enterprise, Microsoft Copilot e dashboards de BI modernos) compartilham padrões comuns de interface:

1. **Acessibilidade Universal:** Nenhuma instalação necessária; acesso instantâneo via browser.
2. **Experiência Conversacional Fluida:** Streaming de respostas em tempo real para reduzir a percepção de latência, suporte a markdown (para tabelas e listas) e histórico de contexto claro.
3. **Desacoplamento Front/Back:** Separação clara entre a lógica de IA (pesada) e a interface do usuário (leve), permitindo escalar cada camada independentemente.

## Ideation Results

Para transformar o chat CLI em uma experiência web, divergimos nas abordagens técnicas focadas em diferentes níveis de esforço e escalabilidade:

1. **Idea 1: Data-App Rápido (Streamlit / Gradio / Chainlit)**
   - **Problem Statement:** Construir do zero um frontend web exige conhecimentos de React/JS e roteamento de APIs, aumentando o tempo de entrega.
   - **Proposed Solution:** Utilizar frameworks Python nativos para aplicações de dados (ex: Chainlit ou Streamlit). O código UI e backend ficam no mesmo repositório e linguagem, acelerando absurdamente o MVP.
   - **Inspiration/Evidence:** Padrão ouro atual na comunidade de AI Engineering para testes rápidos e MVPs internos.

2. **Idea 2: Arquitetura Desacoplada Leve (FastAPI + Vanilla JS/HTML/CSS)**
   - **Problem Statement:** Frameworks como Streamlit podem ser engessados para customizações avançadas de UI/UX e consumo por outros sistemas no futuro.
   - **Proposed Solution:** Expor o agente via API REST ou WebSockets usando **FastAPI**. O frontend seria uma página HTML/CSS/JS simples (Vanilla) servida estaticamente, mantendo o estilo premium mas sem a complexidade de um framework moderno pesadíssimo.
   - **Inspiration/Evidence:** Microserviços tradicionais e a necessidade de "Aesthetics" (interfaces bonitas e responsivas) sem a sobrecarga de ferramentas como Node/npm apenas para uma página de chat.

3. **Idea 3: Arquitetura Desacoplada Enterprise (FastAPI + Next.js/React)**
   - **Problem Statement:** No futuro, a ferramenta de IA pode se tornar um portal complexo com múltiplos dashboards e autenticação sofisticada.
   - **Proposed Solution:** Backend em FastAPI e um frontend rico em React (Next.js ou Vite).
   - **Inspiration/Evidence:** Padrão da indústria para SaaS em larga escala.

4. **Idea 4: Embed Widget (Integração em Intranet Existente)**
   - **Problem Statement:** Usuários não querem abrir "mais um site", querem a resposta onde já trabalham (ex: ERP ou Salesforce).
   - **Proposed Solution:** O agente é envelopado como um widget injetável (Iframe ou Web Component) para rodar dentro de plataformas que a empresa já usa.
   - **Inspiration/Evidence:** Zendesk, Intercom.

## Prioritization Matrix

| Dimension / Solução | Idea 1 (Streamlit/Chainlit) | **Idea 2 (FastAPI + Vanilla UI)** | Idea 3 (FastAPI + React) | Idea 4 (Embed Widget) |
| :--- | :--- | :--- | :--- | :--- |
| **Business Value** (Adoção, TTM) | 5 | 5 | 5 | 4 |
| **User Impact** (UX e Estética) | 3 | **5** (Design customizável) | 5 | 4 |
| **Strategic Alignment** (Flexibilidade) | 2 | **5** (API pronta para o futuro) | 5 | 3 |
| **Effort Estimate** (1=Difícil, 5=Fácil) | 5 | **4** (Requer HTML/CSS) | 2 | 1 |
| **Risk** (Manutenção, Lock-in) | 3 (Lock-in de UI) | **5** (Nenhum lock-in) | 3 (Overengineering) | 2 (Dependências externas) |
| **TOTAL (Ponderado)** | 18 | **24** | 20 | 14 |

## Recommendations

A recomendação principal é avançar com a **Idea 2: Arquitetura Desacoplada Leve (FastAPI + Vanilla JS/HTML/CSS)**.

### Justificativa

- **Separação de Responsabilidades (API First):** Ao encapsular o agente LangChain dentro do FastAPI, criamos um serviço robusto que pode ser consumido por qualquer cliente no futuro.
- **Estética Premium (Aesthetics):** Podemos criar uma interface linda, responsiva e dinâmica (Dark Mode, animações) usando HTML e CSS Vanilla, garantindo que os usuários de negócios fiquem maravilhados sem a complexidade de um build React.
- **Velocidade (Effort vs Reward):** Evita o *overengineering* do Next.js, mas não sofre das limitações visuais rígidas do Streamlit.

### Recommended Sequencing

1. **API Layer (Backend):** Envolver a lógica atual de inicialização do agente e o *loop* de conversa em endpoints do FastAPI (ex: `POST /chat`).
2. **Frontend Service:** Criar a estrutura estática (HTML/CSS) com foco forte em UI/UX, utilizando Fetch API ou WebSocket (Vanilla JS) para conversar com a API.
3. **Integração:** Conectar as peças, garantindo renderização de histórico de conversa e Markdown de forma fluida.

### Validation Suggestions

- Garantir que a API consiga manter o histórico da sessão (Context Memory) entre as chamadas RESTful, dado que HTTP é *stateless* (pode exigir identificadores de sessão (`session_id`) simples).

## Parking Lot

- **Autenticação:** Deixado para fase posterior. Assumimos rede segura ou acesso interno por enquanto.
- **Streaming de Tokens:** Para dar a sensação do ChatGPT (palavra por palavra). Se for muito complexo no início via WebSockets/SSE, entregar a mensagem inteira primeiro, e evoluir para Streaming depois.
