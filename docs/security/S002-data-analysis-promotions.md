# S002-data-analysis-promotions — Auditoria de Segurança

> **Tarefa de Origem:** [B002-data-analysis-promotions.md](../incidents/B002-data-analysis-promotions.md)

## Visão Geral de Segurança

Uma auditoria de segurança direcionada foi realizada na implementação de `AdvancedMetricsService.calculate_average_discount` e no código de análise de promoções. A auditoria avaliou a higienização de entradas, segurança numérica (propagação de NaN/Inf), eficiência de memória e segurança do contexto do prompt do LLM.

## Registro de Vulnerabilidades

| ID | Vulnerabilidade | Severidade | Risco | Impacto |
| :--- | :--- | :--- | :--- | :--- |
| S002-01 | String de Chave de Promoção Não Higienizada | Baixo | Baixo x Baixo | Potencial poluição no contexto do prompt do LLM caso o dataset contenha caracteres de controle brutos em `promotion_type`. |
| S002-02 | Estabilidade Numérica (Defesa NaN / Inf) | Baixo | Baixo x Baixo | Registros de dataset corrompidos com floats não finitos poderiam propagar NaN para a serialização JSON. |

## Tarefas de Refinamento

### Task 002 - Corrigir a lógica de calculate_average_discount

- [COMPLETED] [S002-01] [Baixo] **String de Chave de Promoção Não Higienizada**
  - **Localização:** `src/domain/service/advanced_metrics_service.py` -> `calculate_average_discount()`
  - **Risco:** Valores de dataset não confiáveis em `promotion_type` poderiam conter caracteres de controle ou sintaxe de formatação que poluem as saídas JSON enviadas para os prompts do LLM.
  - **Correção:** Higienizar `promo_key` usando `.strip()` e tratamento de fallback para strings vazias ou None.
  - **Validação:** Testado com registros de entidades mapeados pelo DuckDbSalesAdapter garantindo serialização JSON limpa.

- [COMPLETED] [S002-02] [Baixo] **Estabilidade Numérica (Defesa NaN / Inf)**
  - **Localização:** `src/domain/service/advanced_metrics_service.py` -> `calculate_average_discount()`
  - **Risco:** Registros de dataset corrompidos com floats não finitos poderiam propagar NaN para a serialização JSON.
  - **Correção:** Proteção dos cálculos da taxa de desconto com `planned_price > 0` e verificações de divisão por zero.
  - **Validação:** Verificados os limites de cálculo em listas vazias, registros únicos e datasets com mais de 200k registros.
