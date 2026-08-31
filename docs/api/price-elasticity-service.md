# Price Elasticity of Demand (PED) Service & Domain Tool Specification

> **Feature Reference:** [T008-segment-based-price-elasticity.md](../architecture/T008-segment-based-price-elasticity.md)  
> **PRD Reference:** [R008-segment-based-price-elasticity.md](../business-requirements/R008-segment-based-price-elasticity.md)  
> **Quality Validation:** [Q008-segment-based-price-elasticity.md](../quality/Q008-segment-based-price-elasticity.md)  

---

## 1. Visão Geral e Fundamentação Econômica

O serviço de **Elasticidade-Preço da Demanda Baseada em Segmentos** calcula a sensibilidade volumétrica de vendas frente a variações no preço praticado (baseline regular vs. promocional).

Diferente de agregações globais ingênuas que sofrem do **Paradoxo de Simpson** (ao misturar produtos de alto ticket com baixo ticket em uma média compartilhada), o motor analítico isola rigorosamente as coortes homogêneas por `product_id`.

A fórmula determinística aplicada é:

```text
PED = (% Delta Quantity) / (% Delta Price)

Onde:
% Delta Price    = ((promoted_avg_price - non_promoted_avg_price) / non_promoted_avg_price) * 100
% Delta Quantity = ((promoted_avg_qty - non_promoted_avg_qty) / non_promoted_avg_qty) * 100
```

---

## 2. Diagrama de Fluxo e Execução (Mermaid)

```mermaid
flowchart TD
    A[Invocação: calculate_price_elasticity] --> B{product_id informado?}
    
    B -->|Sim: product_id='PROD_01'| C[DuckDB Pushdown: WHERE product_id = ? GROUP BY product_id]
    B -->|Não: None| D[DuckDB Pushdown: GROUP BY product_id para todo o catálogo]
    
    C --> E[Mapeamento para List PriceElasticityAggregation]
    D --> E
    
    E --> F[AdvancedMetricsService: Avaliação de Coortes]
    
    F --> G{Possui Promoção e Base?}
    G -->|Não: promoted_count=0 ou non_promo=0| H[Classificação: Inconclusive]
    G -->|Sim: Ambas as coortes presentes| I{Delta Price == 0.0?}
    
    I -->|Sim: Preço idêntico| J[Classificação: Unitary / Zero price change Coef=0.0]
    I -->|Não: Preço variou| K[Cálculo: PED = Delta Q / Delta P]
    
    K --> L{Magnitude |PED|}
    L -->|> 1.0| M[Classificação: Elastic]
    L -->|< 1.0| N[Classificação: Inelastic]
    L -->|== 1.0| O[Classificação: Unit Elastic]
    
    H --> P{Modo de Retorno}
    J --> P
    M --> P
    N --> P
    O --> P
    
    P -->|Single Product| Q[Retorna PriceElasticityResult JSON]
    P -->|Catalog Overview| R[Filtra Inconclusivos e Ordena Rankings]
    R --> S[Retorna CatalogPriceElasticityOverview JSON]
```

---

## 3. Contratos de Dados e Modelos de Domínio

### 3.1 `PriceElasticityResult` (Consulta de Produto Individual)

Retornado quando um `product_id` específico é consultado ou quando o catálogo possui apenas um segmento avaliado.

#### Schema JSON

```json
{
  "product_id": "PROD_ELASTIC",
  "elasticity_coefficient": -5.0,
  "percentage_change_in_price": -20.0,
  "percentage_change_in_quantity": 100.0,
  "demand_classification": "Elastic (Quantity highly responsive to price change)",
  "summary": "Produto PROD_ELASTIC - Price Elasticity Coefficient: -5.00 (Elastic (Quantity highly responsive to price change)). A price variance of -20.0% resulted in a quantity variance of +100.0%."
}
```

#### Descrição dos Campos

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `product_id` | `string \| null` | Identificador do produto avaliado. |
| `elasticity_coefficient` | `float` | Coeficiente numérico PED arredondado para 2 casas decimais. |
| `percentage_change_in_price` | `float` | Variação percentual entre preço promocional e preço base. |
| `percentage_change_in_quantity` | `float` | Variação percentual entre volume promocional e volume base. |
| `demand_classification` | `string` | Categoria econômica (`Elastic`, `Inelastic`, `Unit Elastic`, `Unitary / Zero price change`, `Inconclusive`, `Undefined`). |
| `summary` | `string` | Sumário textual executivo formatado para consumo do agente LLM. |

---

### 3.2 `CatalogPriceElasticityOverview` (Visão Macro do Catálogo)

Retornado quando nenhum `product_id` é informado (`product_id=None`), agregando todo o dataset.

#### Schema JSON

```json
{
  "total_products_evaluated": 4,
  "inconclusive_products_count": 1,
  "most_elastic_products": [
    {
      "product_id": "PROD_ELASTIC",
      "elasticity_coefficient": -5.0,
      "percentage_change_in_price": -20.0,
      "percentage_change_in_quantity": 100.0,
      "demand_classification": "Elastic (Quantity highly responsive to price change)",
      "summary": "Produto PROD_ELASTIC - Price Elasticity Coefficient: -5.00..."
    }
  ],
  "most_inelastic_products": [
    {
      "product_id": "PROD_INELASTIC",
      "elasticity_coefficient": -0.5,
      "percentage_change_in_price": -20.0,
      "percentage_change_in_quantity": 10.0,
      "demand_classification": "Inconclusive (Quantity less responsive to price change)",
      "summary": "Produto PROD_INELASTIC - Price Elasticity Coefficient: -0.50..."
    }
  ],
  "summary": "Avaliação de elasticidade do catálogo: 4 produtos avaliados (3 válidos, 1 inconclusivos/indefinidos). Produto mais elástico: PROD_ELASTIC. Produto mais inelástico: PROD_INELASTIC."
}
```

---

## 4. Classificações Econômicas & Regras de Negócio

| Classificação | Condição Matemática | Interpretação de Negócio |
| --- | --- | --- |
| **Elastic** | `|PED| > 1.0` | Alta sensibilidade: reduções de preço geram aumentos desproporcionais de volume. |
| **Inelastic** | `|PED| < 1.0` | Baixa sensibilidade: a demanda varia pouco com alterações de preço. |
| **Unit Elastic** | `|PED| == 1.0` | Proporcionalidade estrita entre variação de preço e volume. |
| **Unitary / Zero price change** | `% Delta Price == 0.0` | Preço promocional idêntico ao preço regular (sem variação de preço observada). |
| **Inconclusive** | `promoted_count == 0` ou `non_promoted_count == 0` | Histórico insuficiente: produto nunca foi promovido ou só possui vendas em promoção. |
| **Undefined** | Produto ausente ou base zerada | Produto inexistente no dataset ou preço/quantidade base $\le 0$. |

---

## 5. Integração com a Camada LLM (LangChain Domain Tool)

A ferramenta é exposta no catálogo de ferramentas do Sales Agent (`src/adapter/inbound/llm/domain_tools.py`):

```python
@tool
def calculate_price_elasticity(product_id: Optional[str] = None) -> str:
    """Calcula o coeficiente de elasticidade-preço da demanda para um produto específico ou visão geral do catálogo.
    
    Args:
        product_id: Identificador do produto (ex: 'PROD_01'). Se omitido (None), calcula e ranqueia a elasticidade de todo o catálogo.
    """
    logger.info("Tool invoked: calculate_price_elasticity (product_id=%s)", product_id)
    result = sales_use_case.calculate_price_elasticity(product_id=product_id)
    return _to_json_str(result)
```

---

## 6. Segurança e Resiliência

1. **Prevenção de Injeção de SQL (OWASP A03):** Parâmetro `product_id` repassado unicamente através de consultas parametrizadas (`WHERE product_id = ?` com lista `params`).
2. **Proteção contra Divisão por Zero (CWE-369):** Guard clauses prevenindo exceções de ponto flutuante em `% Delta Price == 0.0` ou `base_price <= 0`.
3. **Isolamento de Cohort & Integridade Analítica:** Produtos inconclusivos são automaticamente excluídos dos rankings `most_elastic_products` e `most_inelastic_products`, evitando distorções operacionais.
