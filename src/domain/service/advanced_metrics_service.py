"""Domain Service for Advanced / Complex Sales Metrics.

Zero framework dependencies - pure business logic and mathematical models over aggregated structures.
"""
from typing import Dict, List, Optional, Union

from src.domain.model.aggregation_models import (
    AverageDiscountAggregation,
    PriceElasticityAggregation,
    RevenueDeficitAggregation,
    SeasonalityAggregation,
    ServiceLevelBottleneckAggregation,
)
from src.domain.model.metric_result import (
    AverageDiscountResult,
    CatalogPriceElasticityOverview,
    PriceElasticityResult,
    RevenueDeficitResult,
    SeasonalityResult,
    ServiceLevelBottleneckResult,
)


class AdvancedMetricsService:
    """Calculates deterministic advanced sales metrics from aggregated database inputs."""

    def analyze_service_level_bottlenecks(
        self, aggregation: Optional[ServiceLevelBottleneckAggregation]
    ) -> ServiceLevelBottleneckResult:
        """Identifies which location has the lowest average service level (logistics SLA bottleneck)."""
        if not aggregation or aggregation.total_records == 0 or not aggregation.location_averages:
            return ServiceLevelBottleneckResult(
                worst_location="N/A",
                worst_service_level=0.0,
                overall_average_service_level=0.0,
                location_averages={},
                summary="No records to analyze for SLA bottlenecks",
            )

        loc_averages: Dict[str, float] = {
            loc: round(val, 4) for loc, val in aggregation.location_averages.items()
        }

        min_sla = min(loc_averages.values())
        max_sla = max(loc_averages.values())
        overall_avg = round(aggregation.overall_average_service_level, 4)

        if min_sla == max_sla:
            summary = (
                f"All locations present an equal average service level of {min_sla * 100:.2f}% "
                f"(overall fleet average: {overall_avg * 100:.2f}%). No logistics SLA bottleneck identified."
            )
            return ServiceLevelBottleneckResult(
                worst_location="N/A",
                worst_service_level=min_sla,
                overall_average_service_level=overall_avg,
                location_averages=loc_averages,
                summary=summary,
            )

        worst_loc, worst_sla = min(loc_averages.items(), key=lambda item: item[1])

        summary = (
            f"The critical SLA bottleneck is at location '{worst_loc}' with an average service level "
            f"of {worst_sla * 100:.2f}% (overall fleet average: {overall_avg * 100:.2f}%)."
        )

        return ServiceLevelBottleneckResult(
            worst_location=worst_loc,
            worst_service_level=worst_sla,
            overall_average_service_level=overall_avg,
            location_averages=loc_averages,
            summary=summary,
        )

    def calculate_revenue_deficit(
        self, aggregation: Optional[RevenueDeficitAggregation]
    ) -> RevenueDeficitResult:
        """Calculates estimated financial loss/deficit due to planned vs actual variance."""
        if not aggregation or aggregation.total_records == 0:
            return RevenueDeficitResult(
                total_planned_revenue=0.0,
                total_actual_revenue=0.0,
                total_revenue_deficit=0.0,
                deficit_percentage=0.0,
                has_deficit=False,
                summary="No records to calculate revenue deficit",
            )

        total_planned_rev = aggregation.total_planned_revenue
        total_actual_rev = aggregation.total_actual_revenue
        deficit = total_planned_rev - total_actual_rev
        pct = (deficit / total_planned_rev * 100.0) if total_planned_rev > 0 else 0.0
        has_deficit = deficit > 0

        if has_deficit:
            summary = (
                f"Revenue deficit identified: Total planned revenue was ${total_planned_rev:,.2f} "
                f"vs actual realized revenue of ${total_actual_rev:,.2f}, resulting in a loss of "
                f"${deficit:,.2f} ({pct:.2f}% below target)."
            )
        else:
            surplus = abs(deficit)
            summary = (
                f"No revenue deficit. Revenue exceeded budget plan by ${surplus:,.2f} "
                f"(Actual: ${total_actual_rev:,.2f} vs Planned: ${total_planned_rev:,.2f})."
            )

        return RevenueDeficitResult(
            total_planned_revenue=round(total_planned_rev, 2),
            total_actual_revenue=round(total_actual_rev, 2),
            total_revenue_deficit=round(deficit, 2),
            deficit_percentage=round(pct, 2),
            has_deficit=has_deficit,
            summary=summary,
        )

    def calculate_average_discount(
        self, aggregation: Optional[AverageDiscountAggregation]
    ) -> AverageDiscountResult:
        """Calculates average discount margin applied against planned price."""
        if not aggregation or aggregation.total_records == 0:
            return AverageDiscountResult(
                overall_average_discount_percentage=0.0,
                total_planned_revenue=0.0,
                total_actual_revenue=0.0,
                total_discount_value=0.0,
                discount_by_promotion={},
            )

        promo_breakdown = {
            k: round(v, 2) for k, v in aggregation.discount_by_promotion.items()
        }

        return AverageDiscountResult(
            overall_average_discount_percentage=round(aggregation.overall_average_discount_percentage, 2),
            total_planned_revenue=round(aggregation.total_planned_revenue, 2),
            total_actual_revenue=round(aggregation.total_actual_revenue, 2),
            total_discount_value=round(aggregation.total_discount_value, 2),
            discount_by_promotion=promo_breakdown,
        )

    def identify_sales_seasonality(
        self, aggregation: Optional[SeasonalityAggregation]
    ) -> SeasonalityResult:
        """Analyzes monthly sales volume to identify peaks, troughs, and seasonality patterns."""
        if not aggregation or aggregation.total_records == 0 or not aggregation.monthly_volumes:
            return SeasonalityResult(
                monthly_volumes={},
                peak_month="N/A",
                peak_volume=0.0,
                lowest_month="N/A",
                lowest_volume=0.0,
                seasonality_pattern="No data to analyze",
            )

        sorted_months = sorted(aggregation.monthly_volumes.keys())
        monthly_dict = {m: round(aggregation.monthly_volumes[m], 2) for m in sorted_months}

        peak_m, peak_v = max(aggregation.monthly_volumes.items(), key=lambda x: x[1])
        lowest_m, lowest_v = min(aggregation.monthly_volumes.items(), key=lambda x: x[1])

        pattern = (
            f"Peak sales volume occurred in {peak_m} ({peak_v:,.2f} units), while lowest volume "
            f"occurred in {lowest_m} ({lowest_v:,.2f} units). "
            f"Across {len(aggregation.monthly_volumes)} months recorded."
        )

        return SeasonalityResult(
            monthly_volumes=monthly_dict,
            peak_month=peak_m,
            peak_volume=round(peak_v, 2),
            lowest_month=lowest_m,
            lowest_volume=round(lowest_v, 2),
            seasonality_pattern=pattern,
        )

    def _calculate_single_elasticity(
        self,
        aggregation: Optional[PriceElasticityAggregation],
        product_id: Optional[str] = None,
    ) -> PriceElasticityResult:
        """Calculates Price Elasticity of Demand for a single product cohort."""
        effective_pid = product_id or (aggregation.product_id if aggregation and aggregation.product_id else None)

        if not aggregation or aggregation.total_records == 0:
            summary = (
                f"Produto '{effective_pid}' não encontrado no conjunto de dados."
                if effective_pid
                else "Insufficient data to compute elasticity"
            )
            return PriceElasticityResult(
                elasticity_coefficient=0.0,
                percentage_change_in_price=0.0,
                percentage_change_in_quantity=0.0,
                demand_classification="Undefined",
                summary=summary,
                product_id=effective_pid,
            )

        if aggregation.promoted_count == 0 or aggregation.non_promoted_count == 0:
            summary = (
                f"O produto {effective_pid} não possui histórico de promoções registrado; impossível calcular elasticidade."
                if effective_pid
                else "Both promotional and regular baseline records are required to calculate price elasticity."
            )
            return PriceElasticityResult(
                elasticity_coefficient=0.0,
                percentage_change_in_price=0.0,
                percentage_change_in_quantity=0.0,
                demand_classification="Inconclusive",
                summary=summary,
                product_id=effective_pid,
            )

        base_avg_price = aggregation.non_promoted_avg_price
        promo_avg_price = aggregation.promoted_avg_price

        base_avg_qty = aggregation.non_promoted_avg_qty
        promo_avg_qty = aggregation.promoted_avg_qty

        if base_avg_price <= 0 or base_avg_qty <= 0:
            return PriceElasticityResult(
                elasticity_coefficient=0.0,
                percentage_change_in_price=0.0,
                percentage_change_in_quantity=0.0,
                demand_classification="Undefined",
                summary="Base price or quantity is zero; cannot compute elasticity.",
                product_id=effective_pid,
            )

        pct_delta_p = ((promo_avg_price - base_avg_price) / base_avg_price) * 100.0
        pct_delta_q = ((promo_avg_qty - base_avg_qty) / base_avg_qty) * 100.0

        if pct_delta_p == 0.0:
            elasticity = 0.0
            classification = "Unitary / Zero price change"
        else:
            elasticity = pct_delta_q / pct_delta_p
            abs_e = abs(elasticity)
            if abs_e > 1.0:
                classification = "Elastic (Quantity highly responsive to price change)"
            elif abs_e < 1.0:
                classification = "Inelastic (Quantity less responsive to price change)"
            else:
                classification = "Unit Elastic"

        pid_prefix = f"Produto {effective_pid} - " if effective_pid else ""
        summary = (
            f"{pid_prefix}Price Elasticity Coefficient: {elasticity:.2f} ({classification}). "
            f"A price variance of {pct_delta_p:+.1f}% resulted in a quantity variance of {pct_delta_q:+.1f}%."
        )

        return PriceElasticityResult(
            elasticity_coefficient=round(elasticity, 2),
            percentage_change_in_price=round(pct_delta_p, 2),
            percentage_change_in_quantity=round(pct_delta_q, 2),
            demand_classification=classification,
            summary=summary,
            product_id=effective_pid,
        )

    def calculate_price_elasticity(
        self,
        aggregations: Union[List[PriceElasticityAggregation], PriceElasticityAggregation, None],
        target_product_id: Optional[str] = None,
    ) -> Union[PriceElasticityResult, CatalogPriceElasticityOverview]:
        """Calculates Price Elasticity of Demand comparing promotional vs baseline sales.

        Supports single product evaluation or catalog-wide overview and ranking.
        Elasticity (PED) = (% Delta Quantity) / (% Delta Price)
        """
        if aggregations is None:
            agg_list: List[PriceElasticityAggregation] = []
        elif isinstance(aggregations, list):
            agg_list = aggregations
        else:
            agg_list = [aggregations]

        if target_product_id is not None and target_product_id.strip() != "":
            clean_target = target_product_id.strip()
            matching_agg = None
            for agg in agg_list:
                if agg.product_id == clean_target or (len(agg_list) == 1 and not agg.product_id):
                    matching_agg = agg
                    break

            if matching_agg is not None:
                return self._calculate_single_elasticity(matching_agg, product_id=clean_target)

            return PriceElasticityResult(
                elasticity_coefficient=0.0,
                percentage_change_in_price=0.0,
                percentage_change_in_quantity=0.0,
                demand_classification="Undefined",
                summary=f"Produto '{clean_target}' não encontrado no conjunto de dados.",
                product_id=clean_target,
            )

        if not agg_list:
            return CatalogPriceElasticityOverview(
                total_products_evaluated=0,
                inconclusive_products_count=0,
                most_elastic_products=[],
                most_inelastic_products=[],
                summary="Nenhum produto encontrado para avaliação de elasticidade.",
            )

        if len(agg_list) == 1 and not agg_list[0].product_id:
            return self._calculate_single_elasticity(agg_list[0])

        results: List[PriceElasticityResult] = [
            self._calculate_single_elasticity(agg) for agg in agg_list
        ]
        inconclusive_products = [
            r for r in results if r.demand_classification in ("Inconclusive", "Undefined")
        ]
        valid_products = [
            r for r in results if r.demand_classification not in ("Inconclusive", "Undefined")
        ]

        most_elastic = sorted(
            valid_products,
            key=lambda r: abs(r.elasticity_coefficient),
            reverse=True,
        )
        most_inelastic = sorted(
            valid_products,
            key=lambda r: abs(r.elasticity_coefficient),
        )

        summary = (
            f"Avaliação de elasticidade do catálogo: {len(results)} produtos avaliados "
            f"({len(valid_products)} válidos, {len(inconclusive_products)} inconclusivos/indefinidos). "
            f"Produto mais elástico: {most_elastic[0].product_id if most_elastic else 'N/A'}. "
            f"Produto mais inelástico: {most_inelastic[0].product_id if most_inelastic else 'N/A'}."
        )

        return CatalogPriceElasticityOverview(
            total_products_evaluated=len(results),
            inconclusive_products_count=len(inconclusive_products),
            most_elastic_products=most_elastic,
            most_inelastic_products=most_inelastic,
            summary=summary,
        )

