"""Domain Service for Advanced / Complex Sales Metrics.

Zero framework dependencies - pure business logic and mathematical models.
"""
from collections import defaultdict
from typing import Dict, Optional, Sequence

from src.domain.model.metric_result import (
    AverageDiscountResult,
    PriceElasticityResult,
    RevenueDeficitResult,
    SeasonalityResult,
    ServiceLevelBottleneckResult,
)
from src.domain.model.sale_record import SaleRecord


class AdvancedMetricsService:
    """Calculates deterministic advanced sales metrics."""

    def analyze_service_level_bottlenecks(
        self, records: Sequence[SaleRecord]
    ) -> ServiceLevelBottleneckResult:
        """Identifies which location has the lowest average service level (logistics SLA bottleneck)."""
        if not records:
            return ServiceLevelBottleneckResult(
                worst_location="N/A",
                worst_service_level=0.0,
                overall_average_service_level=0.0,
                location_averages={},
                summary="No records to analyze for SLA bottlenecks",
            )

        loc_sla_totals = defaultdict(float)
        loc_counts = defaultdict(int)
        total_sla = 0.0

        for r in records:
            loc_sla_totals[r.local] += r.service_level
            loc_counts[r.local] += 1
            total_sla += r.service_level

        loc_averages: Dict[str, float] = {
            loc: round(loc_sla_totals[loc] / loc_counts[loc], 4)
            for loc in loc_sla_totals
        }

        min_sla = min(loc_averages.values())
        max_sla = max(loc_averages.values())
        overall_avg = round(total_sla / len(records), 4)

        if abs(max_sla - min_sla) < 1e-4:
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
        self, records: Sequence[SaleRecord]
    ) -> RevenueDeficitResult:
        """Calculates estimated financial loss/deficit due to planned vs actual variance."""
        if not records:
            return RevenueDeficitResult(
                total_planned_revenue=0.0,
                total_actual_revenue=0.0,
                total_revenue_deficit=0.0,
                deficit_percentage=0.0,
                has_deficit=False,
                summary="No records to calculate revenue deficit",
            )

        total_planned_rev = sum(r.planned_revenue for r in records)
        total_actual_rev = sum(r.actual_revenue for r in records)
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
        self, records: Sequence[SaleRecord]
    ) -> AverageDiscountResult:
        """Calculates average discount margin applied against planned price."""
        if not records:
            return AverageDiscountResult(
                overall_average_discount_percentage=0.0,
                total_planned_revenue=0.0,
                total_actual_revenue=0.0,
                total_discount_value=0.0,
                discount_by_promotion={},
            )

        total_planned_rev = sum(r.planned_revenue for r in records)
        total_actual_rev = sum(r.actual_revenue for r in records)
        total_discount_val = sum(
            max(0.0, r.planned_revenue - r.actual_revenue)
            for r in records
            if r.planned_price > r.actual_price
        )

        discount_rates = [
            r.discount_rate for r in records if r.planned_price > 0 and r.discount_rate > 0
        ]
        avg_discount_pct = (
            (sum(discount_rates) / len(discount_rates) * 100.0) if discount_rates else 0.0
        )

        # Discount breakdown by promotion type
        promo_totals = defaultdict(float)
        promo_counts = defaultdict(int)
        for r in records:
            if r.planned_price > 0 and r.discount_rate > 0:
                promo_key = str(r.promotion_type).strip() if r.promotion_type else "None"
                promo_totals[promo_key] += r.discount_rate * 100.0
                promo_counts[promo_key] += 1

        promo_breakdown = {
            k: round(promo_totals[k] / promo_counts[k], 2) for k in promo_totals
        }

        return AverageDiscountResult(
            overall_average_discount_percentage=round(avg_discount_pct, 2),
            total_planned_revenue=round(total_planned_rev, 2),
            total_actual_revenue=round(total_actual_rev, 2),
            total_discount_value=round(total_discount_val, 2),
            discount_by_promotion=promo_breakdown,
        )

    def identify_sales_seasonality(
        self, records: Sequence[SaleRecord]
    ) -> SeasonalityResult:
        """Analyzes monthly sales volume to identify peaks, troughs, and seasonality patterns."""
        if not records:
            return SeasonalityResult(
                monthly_volumes={},
                peak_month="N/A",
                peak_volume=0.0,
                lowest_month="N/A",
                lowest_volume=0.0,
                seasonality_pattern="No data to analyze",
            )

        monthly_vols = defaultdict(float)

        for r in records:
            month_key = r.date.strftime("%Y-%m") if r.date else "Unknown"
            monthly_vols[month_key] += r.actual_quantity

        if not monthly_vols:
            return SeasonalityResult()

        sorted_months = sorted(monthly_vols.keys())
        monthly_dict = {m: round(monthly_vols[m], 2) for m in sorted_months}

        peak_m, peak_v = max(monthly_vols.items(), key=lambda x: x[1])
        lowest_m, lowest_v = min(monthly_vols.items(), key=lambda x: x[1])

        pattern = (
            f"Peak sales volume occurred in {peak_m} ({peak_v:,.2f} units), while lowest volume "
            f"occurred in {lowest_m} ({lowest_v:,.2f} units). "
            f"Across {len(monthly_vols)} months recorded."
        )

        return SeasonalityResult(
            monthly_volumes=monthly_dict,
            peak_month=peak_m,
            peak_volume=round(peak_v, 2),
            lowest_month=lowest_m,
            lowest_volume=round(lowest_v, 2),
            seasonality_pattern=pattern,
        )

    def calculate_price_elasticity(
        self, records: Sequence[SaleRecord]
    ) -> PriceElasticityResult:
        """Calculates Price Elasticity of Demand comparing promotional vs baseline sales.
        
        Elasticity (PED) = (% Delta Quantity) / (% Delta Price)
        """
        if not records:
            return PriceElasticityResult(
                elasticity_coefficient=0.0,
                percentage_change_in_price=0.0,
                percentage_change_in_quantity=0.0,
                demand_classification="Undefined",
                summary="Insufficient data to compute elasticity",
            )

        promoted = [r for r in records if r.is_promoted]
        non_promoted = [r for r in records if not r.is_promoted]

        if not promoted or not non_promoted:
            # Fallback: compare transactions with discounts vs no discounts
            promoted = [r for r in records if r.discount_rate > 0.0]
            non_promoted = [r for r in records if r.discount_rate <= 0.0]

        if not promoted or not non_promoted:
            return PriceElasticityResult(
                elasticity_coefficient=0.0,
                percentage_change_in_price=0.0,
                percentage_change_in_quantity=0.0,
                demand_classification="Inconclusive",
                summary="Both promotional and regular baseline records are required to calculate price elasticity.",
            )

        base_avg_price = sum(r.actual_price for r in non_promoted) / len(non_promoted)
        promo_avg_price = sum(r.actual_price for r in promoted) / len(promoted)

        base_avg_qty = sum(r.actual_quantity for r in non_promoted) / len(non_promoted)
        promo_avg_qty = sum(r.actual_quantity for r in promoted) / len(promoted)

        if base_avg_price <= 0 or base_avg_qty <= 0:
            return PriceElasticityResult(
                elasticity_coefficient=0.0,
                percentage_change_in_price=0.0,
                percentage_change_in_quantity=0.0,
                demand_classification="Undefined",
                summary="Base price or quantity is zero; cannot compute elasticity.",
            )

        # % change in price = (Promo Price - Base Price) / Base Price
        pct_delta_p = ((promo_avg_price - base_avg_price) / base_avg_price) * 100.0
        # % change in quantity = (Promo Qty - Base Qty) / Base Qty
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

        summary = (
            f"Price Elasticity Coefficient: {elasticity:.2f} ({classification}). "
            f"A price variance of {pct_delta_p:+.1f}% resulted in a quantity variance of {pct_delta_q:+.1f}%."
        )

        return PriceElasticityResult(
            elasticity_coefficient=round(elasticity, 2),
            percentage_change_in_price=round(pct_delta_p, 2),
            percentage_change_in_quantity=round(pct_delta_q, 2),
            demand_classification=classification,
            summary=summary,
        )
