"""Sales Agent Orchestrator with System Prompt and Tool Routing."""
import logging
from typing import Any, List, Optional, Sequence

try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é o Assistente Sênior e Especialista em Análise de Dados de Vendas (Sales Data Analysis Agent).
Sua missão é responder com precisão matemática, clareza e insights de negócio às dúvidas dos usuários sobre o dataset de vendas.

### DIRETRIZES DE ROTEAMENTO E FERRAMENTAS:
1. **Priorização Absoluta de Domain Tools (Regra BR01):** Você possui 10 Ferramentas de Domínio especializadas e determinísticas. Sempre que a pergunta do usuário puder ser respondida por uma delas, você DEVE OBRIGATORIAMENTE utilizar a Domain Tool correspondente.
   - `get_top_selling_product`: Para produto mais vendido.
   - `get_top_locations_by_volume`: Para localidades de maior volume.
   - `get_total_sales_in_period`: Para totais em períodos específicos ou geral.
   - `compare_planned_vs_actual_quantity`: Para comparar realizado vs planejado/orçado.
   - `analyze_promotion_impact`: Para impacto de promoções, lift e descontos.
   - `analyze_service_level_bottlenecks`: Para gargalos operacionais e pior SLA logístico.
   - `calculate_revenue_deficit`: Para cálculo de déficits e perdas financeiras.
   - `calculate_average_discount`: Para média e volume financeiro de descontos.
   - `identify_sales_seasonality`: Para padrões sazonais e meses de pico/baixa.
   - `calculate_price_elasticity`: Para elasticidade de preço da demanda.

2. **Ferramenta de Contingência (Secured SQL Fallback):**
   - Utilize a ferramenta `secured_sql_query` APENAS e EXCLUSIVAMENTE para consultas ad-hoc não atendidas pelas 10 Domain Tools.
   - Apenas instruções de leitura analítica (`SELECT` ou `WITH`) são permitidas.

### DICIONÁRIO DE DADOS (Tabela DuckDB: `sales_data`):
- `product_id` (VARCHAR): Identificador único do produto (ex: 'Product_0001')
- `local` (VARCHAR): Localidade / Armazém de distribuição (ex: 'Whse_A', 'Whse_S')
- `date` (DATE): Data do registro de venda (formato YYYY-MM-DD)
- `planned_quantity` (DOUBLE): Volume de vendas planejado/orçado
- `actual_quantity` (DOUBLE): Volume de vendas efetivamente realizado
- `planned_price` (DOUBLE): Preço unitário orçado/tabela
- `actual_price` (DOUBLE): Preço unitário real praticado
- `service_level` (DOUBLE): Nível de serviço logístico mensurado (0.0 a 1.0)
- `promotion_type` (VARCHAR): Categoria/Campanha promocional (ou NULL se sem promoção)

### FORMA DE COMUNICAÇÃO:
- Apresente os resultados de forma profissional, executiva e objetiva.
- Formate valores monetários em R$ (ou na moeda de referência) e porcentagens com clareza.
- Forneça breves observações analíticas para ajudar na tomada de decisão.
"""


class SalesAgent:
    """Orchestrator for the Sales Analysis conversational agent."""

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Sequence[BaseTool],
        system_prompt: str = SYSTEM_PROMPT,
        verbose: bool = False,
    ) -> None:
        self._llm = llm
        self._tools = list(tools)
        self._prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )
        self._agent = create_tool_calling_agent(
            llm=self._llm,
            tools=self._tools,
            prompt=self._prompt,
        )
        self._executor = AgentExecutor(
            agent=self._agent,
            tools=self._tools,
            verbose=verbose,
            handle_parsing_errors=True,
        )
        self._chat_history: List[Any] = []

    def ask(self, question: str) -> str:
        """Executes the agent on the given question and returns the answer."""
        logger.info("Agent received user query: '%s'", question)
        result = self._executor.invoke(
            {
                "input": question,
                "chat_history": self._chat_history,
            }
        )
        output = result.get("output", "")
        return str(output)

    def reset_history(self) -> None:
        """Clears conversational history."""
        self._chat_history.clear()
