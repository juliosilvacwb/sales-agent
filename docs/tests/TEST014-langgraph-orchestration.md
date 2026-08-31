<!-- markdownlint-disable MD013 -->
# TEST014-langgraph-orchestration — Test Coverage Specification

> **Source Task:** [T014-langgraph-orchestration.md](../architecture/T014-langgraph-orchestration.md)  
> **PRD Reference:** [R014-langgraph-orchestration.md](../business-requirements/R014-langgraph-orchestration.md)

## Coverage Overview

Esta especificação estabelece o plano forense e a matriz de cobertura de testes para a migração do motor de orquestração do Agente de Análise de Vendas para uma **Máquina de Estados baseada em Grafo via LangGraph** (`T014-langgraph-orchestration.md` / `R014-langgraph-orchestration.md`). O objetivo central é substituir o executor linear legadado (`AgentExecutor`) por um `StateGraph(MessagesState)` determinístico com nós desacoplados (`call_model`, `tools`), controle de ciclo de autorrecuperação (Self-Correction Loop R009), teto estrito de recursão (`recursion_limit=10`) e inspeção de estado para Response Grounding (`data_queried: bool` R013), mantendo 100% de compatibilidade retroativa com a interface pública `SalesAgent.ask`.

- **Status Geral de Cobertura:** 100% de cobertura lógica, nós de execução, roteamento condicional, isolamento de camadas hexagonais, inspeção de estado e testes de integração cíclica para todas as 5 tarefas da especificação T014.
- **Pirâmide de Testes:**
  - **Unitários (Configuração e Dependências):** Verificação de dependências em `requirements.txt` e `pyproject.toml` (`langgraph>=0.2.0`, `langchain-core`), resolução de tipagem e integridade de importação de primitivas LangGraph (`StateGraph`, `MessagesState`, `ToolNode`, `START`, `END`, `GraphRecursionError`).
  - **Unitários (Nós de Execução do Grafo):** Validação dos nós `call_model` e `tools` (`ToolNode`), garantia de vinculação de ferramentas (`bind_tools`), fallback seguro para modelos sem suporte a tool binding e configuração de tratamento de erros com telemetria `_handle_tool_error`.
  - **Unitários (Roteamento Condicional e Topologia):** Validação da função de borda condicional `should_continue` (detecção de `tool_calls` vs `END`), tratamento de estados vazios, compilação da topologia cíclica e preservação do alias de compatibilidade `create_agent`.
  - **Unitários (Orquestração e Inspeção de Estado no SalesAgent):** Validação da montagem do `MessagesState` inicial com `SystemMessage` dinâmico, injeção de `recursion_limit` e callbacks no `RunnableConfig`, captura graciosa de `GraphRecursionError` com fallback executivo, e extração da flag `data_queried` inspecionando instâncias de `ToolMessage`.
  - **Unitários (Memória e Isolamento de Sessão):** Validação da janela deslizante (`max_history_messages`), reset de memória e preservação do isolamento stateless quando `chat_history` externo é fornecido.
  - **Integração (Ciclo de Execução e Autorrecuperação):** Execução ponta a ponta com `DuckDbSalesAdapter`, dataset DuckDB e `DeterministicFakeChatModel` em `tests/integration/test_sales_agent.py`, validando travessia cíclica (`call_model -> tools -> call_model -> END`), bypass de ferramentas em cumprimentos casuais, autorrecuperação autônoma de erros SQL e contenção de loops infinitos.

---

## Test Checklist

### Task 001 — [Config]: Ensure langgraph dependency exists

- [COMPLETED] [TEST014-01] [Type: Unit] **test_langgraph_dependency_declaration_and_imports**
  - **Target:** `requirements.txt`, `pyproject.toml`, `src/adapter/inbound/llm/sales_agent.py`
  - **Scenario:** Validar que a dependência `langgraph>=0.2.0` e `langchain-core` estão declaradas nos manifestos de dependências e que os símbolos essenciais do LangGraph são importáveis no runtime sem erros.
  - **Arrange:** Inspecionar os arquivos de configuração e importar `StateGraph`, `MessagesState`, `START`, `END`, `ToolNode` e `GraphRecursionError`.
  - **Act:** Verificar as entradas em `requirements.txt`, `pyproject.toml` (em `[tool.mypy.overrides]`) e validar a resolução dos símbolos importados.
  - **Assert:** As declarações de dependência contêm `langgraph>=0.2.0` e todos os símbolos do LangGraph são carregados com sucesso.
  - **Priority:** P0

---

### Task 002 — [Adapter-Web]: Implement discrete graph nodes

- [COMPLETED] [TEST014-02] [Type: Unit] **test_call_model_node_invokes_llm_with_bound_tools_and_returns_aimessage**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `create_sales_graph` / `call_model`
  - **Scenario:** Validar que o nó `call_model` extrai a lista `state["messages"]`, propaga o `RunnableConfig` com callbacks/limites, invoca o modelo vinculado às ferramentas e retorna o dicionário `{"messages": [response]}`.
  - **Arrange:** Criar mock de `BaseChatModel` com método `bind_tools` retornando mock invocável, e compilar grafo com ferramenta de teste.
  - **Act:** Invocar o nó `call_model` com estado `{"messages": [HumanMessage(content="Qual o produto mais vendido?")]}`.
  - **Assert:** O modelo é invocado com a sequência correta de mensagens e o retorno é um dicionário contendo a chave `"messages"` com a lista contendo o `AIMessage` gerado.
  - **Priority:** P0

- [COMPLETED] [TEST014-03] [Type: Unit] **test_call_model_node_preserves_model_without_bind_tools_capability**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `create_sales_graph`
  - **Scenario:** Validar que se um modelo customizado não implementar `bind_tools`, `create_sales_graph` utiliza o modelo original sem levantar `AttributeError`.
  - **Arrange:** Criar mock de `BaseChatModel` sem o atributo `bind_tools`.
  - **Act:** Invocar `create_sales_graph(model=mock_model, tools=[])`.
  - **Assert:** O grafo é compilado com sucesso e o nó `call_model` invoca o modelo diretamente.
  - **Priority:** P1

- [COMPLETED] [TEST014-04] [Type: Unit] **test_tool_node_instantiation_with_error_handling_enabled**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `ToolNode`
  - **Scenario:** Validar que o `ToolNode` é instanciado com `handle_tool_errors=True`, capturando exceções de ferramentas (`ToolException`) e gerando `ToolMessage` com flag de erro em vez de abortar o processo.
  - **Arrange:** Definir ferramenta que levanta `ToolException("Coluna inexistente")` e compilar o grafo.
  - **Act:** Executar o `ToolNode` com uma chamada para a ferramenta com erro.
  - **Assert:** O nó retorna `ToolMessage` contendo a mensagem de erro formatada, permitindo a continuidade do ciclo de autorrecuperação.
  - **Priority:** P0

---

### Task 003 — [Adapter-Web]: Implement conditional routing and compile StateGraph

- [COMPLETED] [TEST014-05] [Type: Unit] **test_should_continue_routes_to_tools_when_tool_calls_present**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `should_continue`
  - **Scenario:** Validar que a função de roteamento condicional `should_continue` inspeciona a última mensagem do estado e retorna `"tools"` quando há chamadas de ferramenta pendentes (`tool_calls`).
  - **Arrange:** Montar `MessagesState` com última mensagem sendo `AIMessage(content="", tool_calls=[{"name": "get_top_selling_product", "args": {}, "id": "1", "type": "tool_call"}])`.
  - **Act:** Executar a função de roteamento condicional com o estado preparado.
  - **Assert:** Retorna estritamente `"tools"`.
  - **Priority:** P0

- [COMPLETED] [TEST014-06] [Type: Unit] **test_should_continue_routes_to_end_when_no_tool_calls**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `should_continue`
  - **Scenario:** Validar que `should_continue` retorna `END` (`"__end__"`) quando a última mensagem do assistente não contém `tool_calls` (ex: resposta final ou saudação).
  - **Arrange:** Montar `MessagesState` com última mensagem sendo `AIMessage(content="O produto mais vendido foi Prod_01.")` sem `tool_calls`.
  - **Act:** Executar a função de roteamento condicional.
  - **Assert:** Retorna estritamente `END`.
  - **Priority:** P0

- [COMPLETED] [TEST014-07] [Type: Unit] **test_should_continue_handles_empty_messages_state_edge_case**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `should_continue`
  - **Scenario:** Validar o caso de borda onde a lista `messages` no estado está vazia (`[]`), assegurando que `should_continue` retorne `END` sem disparar `IndexError`.
  - **Arrange:** Montar estado `{"messages": []}`.
  - **Act:** Executar `should_continue(state)`.
  - **Assert:** Retorna `END` de forma segura.
  - **Priority:** P1

- [COMPLETED] [TEST014-08] [Type: Unit] **test_state_graph_compilation_and_topology_verification**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `create_sales_graph`
  - **Scenario:** Validar a topologia estrutural do grafo compilado: nós `"agent"` e `"tools"`, ponto de entrada `START -> agent`, aresta condicional em `"agent"` e retorno cíclico `"tools" -> agent`.
  - **Arrange:** Instanciar mock LLM e ferramentas, e compilar `graph = create_sales_graph(model=mock_llm, tools=mock_tools)`.
  - **Act:** Inspecionar o grafo compilado e seus nós / arestas registradas.
  - **Assert:** O grafo possui nó `"agent"`, nó `"tools"`, arestas configuradas e método `invoke` pronto para execução.
  - **Priority:** P0

- [COMPLETED] [TEST014-09] [Type: Unit] **test_create_agent_backward_compatibility_alias**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `create_agent`
  - **Scenario:** Validar que `create_agent` é mantido como um alias para `create_sales_graph`, assegurando que código legado ou patches de testes continuem operacionais.
  - **Arrange:** Importar `create_agent` e `create_sales_graph`.
  - **Act:** Verificar a identidade dos objetos.
  - **Assert:** `create_agent is create_sales_graph` e aceita os parâmetros `(model, tools, system_prompt)`.
  - **Priority:** P1

---

### Task 004 — [Adapter-Web]: Refactor SalesAgent orchestration and state extraction

- [COMPLETED] [TEST014-10] [Type: Unit] **test_sales_agent_initialization_with_langgraph_executor**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.__init__`
  - **Scenario:** Validar que a instanciação de `SalesAgent` configura o modelo, vincula os manipuladores `_handle_tool_error` nas ferramentas, monta o prompt do sistema com insights dinâmicos e compila o `_executor` via LangGraph.
  - **Arrange:** Criar mock de `BaseChatModel` e ferramentas com atributo `handle_tool_error`.
  - **Act:** Instanciar `agent = SalesAgent(llm=mock_llm, tools=mock_tools)`.
  - **Assert:** `agent._executor` não é nulo, `agent._tools[0].handle_tool_error` é configurado como função chamável e `agent._system_prompt` contém o prompt padrão.
  - **Priority:** P0

- [COMPLETED] [TEST014-11] [Type: Unit] **test_sales_agent_ask_constructs_messages_state_correctly**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.ask()`
  - **Scenario:** Validar que `SalesAgent.ask()` monta a sequência de mensagens do `MessagesState` iniciando com `SystemMessage(content=self._system_prompt)`, seguido pelo histórico e finalizando com `HumanMessage(content=question)`.
  - **Arrange:** Criar `SalesAgent` com mock de executor que captura os argumentos de entrada e retorna `{"messages": [AIMessage(content="OK")]}`.
  - **Act:** Executar `agent.ask("Qual o total vendido?", chat_history=[HumanMessage(content="H1"), AIMessage(content="A1")])`.
  - **Assert:** Os argumentos passados para `_executor.invoke` contêm uma lista de mensagens na ordem exata: `SystemMessage`, `HumanMessage("H1")`, `AIMessage("A1")` e `HumanMessage("Qual o total vendido?")`.
  - **Priority:** P0

- [COMPLETED] [TEST014-12] [Type: Unit] **test_sales_agent_ask_injects_recursion_limit_and_callbacks_config**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.ask()`
  - **Scenario:** Validar que `ask()` passa um dicionário `RunnableConfig` para o executor com `recursion_limit: 10` e a lista de callbacks contendo `ToolTrackingCallbackHandler` e callbacks externos fornecidos.
  - **Arrange:** Criar mock de callback externo e configurar spy no método `_executor.invoke`.
  - **Act:** Executar `agent.ask("Teste de configuração", callbacks=[mock_external_cb])`.
  - **Assert:** `_executor.invoke` é chamado com `config["recursion_limit"] == 10` e `config["callbacks"]` contendo a instância de `ToolTrackingCallbackHandler` e o callback externo.
  - **Priority:** P0

- [COMPLETED] [TEST014-13] [Type: Unit] **test_sales_agent_ask_detects_tool_messages_and_flags_data_queried**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.ask()`
  - **Scenario:** Validar que quando o resultado do grafo contém uma ou mais instâncias de `ToolMessage` em `result["messages"]`, `ask()` retorna um `AgentResult` com `data_queried = True`.
  - **Arrange:** Configurar mock de executor para retornar lista de mensagens contendo `ToolMessage(content='{"total": 100}', tool_call_id="call_1", name="get_total_sales_in_period")` e resposta final `AIMessage(content="Total: 100")`.
  - **Act:** Executar `result = agent.ask("Qual o total de vendas?")`.
  - **Assert:** `result.data_queried is True` e `result.response == "Total: 100"`.
  - **Priority:** P0

- [COMPLETED] [TEST014-14] [Type: Unit] **test_sales_agent_ask_flags_data_queried_false_when_no_tool_messages**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.ask()`
  - **Scenario:** Validar que para consultas casuais onde nenhuma `ToolMessage` foi emitida e o tracking handler permaneceu inativo, `ask()` retorna `data_queried = False`.
  - **Arrange:** Configurar mock de executor para retornar apenas `AIMessage(content="Olá! Tudo bem?")` sem `ToolMessage`.
  - **Act:** Executar `result = agent.ask("Olá!")`.
  - **Assert:** `result.data_queried is False` e `result.response == "Olá! Tudo bem?"`.
  - **Priority:** P0

- [COMPLETED] [TEST014-15] [Type: Unit] **test_sales_agent_catches_graph_recursion_error_and_returns_fallback**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.ask()`
  - **Scenario:** Validar que o disparo de `GraphRecursionError` pelo LangGraph (ao atingir o limite de 10 passos) é interceptado, emitindo log de erro e retornando a mensagem de fallback de negócio com `data_queried = False`.
  - **Arrange:** Configurar `_executor.invoke` para lançar `GraphRecursionError("Recursion limit of 10 reached")`.
  - **Act:** Executar `result = agent.ask("Gere consulta que entra em loop")`.
  - **Assert:** `result.response == FALLBACK_ERROR_MESSAGE` e `result.data_queried is False`.
  - **Priority:** P0

- [COMPLETED] [TEST014-16] [Type: Unit] **test_sales_agent_catches_generic_graph_execution_exception**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.ask()`
  - **Scenario:** Validar que qualquer exceção genérica inesperada lançada durante a invocação do grafo é capturada de forma segura, evitando quebra da API e retornando a mensagem de fallback com `data_queried = False`.
  - **Arrange:** Configurar `_executor.invoke` para lançar `RuntimeError("Erro de comunicação com o LLM")`.
  - **Act:** Executar `result = agent.ask("Consulta com falha inesperada")`.
  - **Assert:** `result.response == FALLBACK_ERROR_MESSAGE` e `result.data_queried is False`.
  - **Priority:** P0

- [COMPLETED] [TEST014-17] [Type: Unit] **test_sales_agent_sliding_window_memory_with_graph_orchestration**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.ask()` / `_chat_history`
  - **Scenario:** Validar que na ausência de histórico externo, cada chamada a `ask()` armazena o `HumanMessage` e o `AIMessage` no `_chat_history` interno, respeitando o limite deslizante `max_history_messages`.
  - **Arrange:** Instanciar `agent = SalesAgent(..., max_history_messages=4)` com mock de executor retornando mensagens de resposta.
  - **Act:** Executar 3 consultas sequenciais ("Pergunta 1", "Pergunta 2", "Pergunta 3") e em seguida `agent.reset_history()`.
  - **Assert:** O histórico retém exatamente 4 mensagens correspondentes aos dois últimos turnos ("Pergunta 2" e "Pergunta 3"), e após `reset_history()` o tamanho passa a ser 0.
  - **Priority:** P1

- [COMPLETED] [TEST014-18] [Type: Unit] **test_sales_agent_external_chat_history_isolation_no_leak**
  - **Target:** `src/adapter/inbound/llm/sales_agent.py` → `SalesAgent.ask()`
  - **Scenario:** Validar que ao passar uma sequência no parâmetro `chat_history`, o histórico interno da instância `_chat_history` permanece intacto e inalterado, garantindo isolamento thread-safe.
  - **Arrange:** Instanciar `agent` e definir histórico externo com `[HumanMessage(content="Msg antiga")]`.
  - **Act:** Executar `agent.ask("Pergunta nova", chat_history=external_history)`.
  - **Assert:** `len(agent.chat_history) == 0`.
  - **Priority:** P1

---

### Task 005 — [Test-Integration]: Validate cyclic execution and backwards compatibility

- [COMPLETED] [TEST014-19] [Type: Integration] **test_langgraph_cyclic_tool_execution_integration**
  - **Target:** `tests/integration/test_sales_agent.py` → `test_langgraph_cyclic_tool_execution`
  - **Scenario:** Validar em nível de integração que uma consulta analítica percorre o ciclo completo do grafo: `call_model` emite chamada para `get_top_selling_product` -> `ToolNode` executa consulta no DuckDB real -> `call_model` sintetiza a resposta final com os dados -> transiciona para `END`.
  - **Arrange:** Criar fixture com CSV temporário de vendas, instanciar `DuckDbSalesAdapter`, `SalesMetricsApplicationService`, `create_domain_tools` e `DeterministicFakeChatModel` configurado para emitir chamada de ferramenta seguida de resposta textual.
  - **Act:** Executar `result = agent.ask("Qual foi o produto mais vendido?")`.
  - **Assert:** `result.data_queried is True`, o texto da resposta contém o cálculo analítico real ("Product_0001", "210"), e o `chat_history` interno armazena o turno completo.
  - **Priority:** P0

- [COMPLETED] [TEST014-20] [Type: Integration] **test_langgraph_direct_conversational_turn_integration**
  - **Target:** `tests/integration/test_sales_agent.py` → `test_langgraph_direct_conversational_turn`
  - **Scenario:** Validar que uma mensagem de saudação casual sem necessidade de dados transiciona diretamente de `call_model` para `END` em um único passo de inferência, sem acionar o nó de ferramentas.
  - **Arrange:** Configurar `DeterministicFakeChatModel` retornando saudação executiva sem `tool_calls`.
  - **Act:** Executar `result = agent.ask("Olá, assistente!")`.
  - **Assert:** `result.data_queried is False`, o texto retornado corresponde à saudação e o `chat_history` contém o registro do turno.
  - **Priority:** P0

- [COMPLETED] [TEST014-21] [Type: Integration] **test_langgraph_agentic_self_correction_cyclic_recovery_integration**
  - **Target:** `tests/integration/test_sales_agent.py` → `test_langgraph_agentic_self_correction_cyclic_recovery`
  - **Scenario:** Validar o ciclo de autorrecuperação autônoma (R009): o modelo gera SQL com coluna inválida -> `ToolNode` captura `ToolException` e retorna mensagem de erro -> aresta cíclica devolve o estado para `call_model` -> modelo corrige a sintaxe SQL -> consulta executa com sucesso no DuckDB -> modelo sintetiza resposta final -> transiciona para `END`.
  - **Arrange:** Configurar `DeterministicFakeChatModel` com sequência de 3 respostas: (1) chamada `secured_sql_query` com coluna inexistente, (2) chamada `secured_sql_query` corrigida, (3) resposta final de síntese.
  - **Act:** Executar `result = agent.ask("Qual o volume total de unidades vendidas?")` capturando logs com `caplog.at_level(logging.WARNING)`.
  - **Assert:** `result.data_queried is True`, a resposta contém o valor computado ("390") e os logs contêm a telemetria `[AGENT_SELF_CORRECTION]`.
  - **Priority:** P0

- [COMPLETED] [TEST014-22] [Type: Integration] **test_langgraph_recursion_limit_protection_integration**
  - **Target:** `tests/integration/test_sales_agent.py` → `test_langgraph_recursion_limit_protection`
  - **Scenario:** Validar que um loop infinito simulado com mais de 10 chamadas contínuas de ferramentas atinge o limite `recursion_limit=10`, interrompe a execução com segurança e retorna a mensagem de contingência sem travar a aplicação.
  - **Arrange:** Configurar `DeterministicFakeChatModel` emitindo uma lista de 20 chamadas de ferramentas sucessivas sem resposta de texto.
  - **Act:** Executar `result = agent.ask("Gere loop infinito de ferramentas")`.
  - **Assert:** `result.response == FALLBACK_ERROR_MESSAGE` e `result.data_queried is False`.
  - **Priority:** P0

- [COMPLETED] [TEST014-23] [Type: Integration] **test_langgraph_full_stack_web_chat_backward_compatibility**
  - **Target:** `tests/integration/test_data_queried_flag.py`, `src/application/service/web_chat_application_service.py`
  - **Scenario:** Validar que a camada de aplicação `WebChatApplicationService` e os endpoints web operam perfeitamente com o `SalesAgent` baseado em LangGraph, garantindo interoperabilidade do `AgentResult` e isolamento de flag por turno.
  - **Arrange:** Instanciar stack completa com `WebChatApplicationService`, `SessionStorePort` em memória e `SalesAgent`.
  - **Act:** Enviar requisição de análise de vendas seguida de requisição de saudação para a mesma sessão.
  - **Assert:** A primeira resposta retorna `data_queried=True` com badge de dados verificados, e a segunda resposta retorna `data_queried=False`, confirmando compatibilidade retroativa e isolamento estrito de turnos.
  - **Priority:** P0
