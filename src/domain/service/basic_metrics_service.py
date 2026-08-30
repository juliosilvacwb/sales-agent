"""Domain Service for Basic Sales Metrics.

Zero framework dependencies - pure business logic calculations over aggregated structures.
"""
from datetime import date
from typing import Optional, Sequence

from src.domain.model.aggregation_models import (
    LocationSalesAggregation,
    PlannedVsActualAggregation,
    ProductAggregation,
    PromotionImpactAggregation,
    TotalSalesAggregation,
)
from src.domain.model.metric_result import (
    PlannedVsActualResult,
    PromotionImpactResult,
    TopLocationResult,
    TopSellingProductResult,
    TotalSalesResult,
)


class BasicMetricsService:
    """Calculates deterministic basic sales metrics from aggregated database inputs."""

    def get_top_selling_product(
        self, aggregation: Optional[ProductAggregation]
    ) -> TopSellingProductResult:
        """Constructs TopSellingProductResult from pre-aggregated product data."""
        if not aggregation or aggregation.total_records == 0:
            return TopSellingProductResult(
                product_id="N/A",
                total_quantity=0.0,
                total_revenue=0.0,
                total_records=0,
            )

        return TopSellingProductResult(
            product_id=aggregation.product_id,
            total_quantity=round(aggregation.total_quantity, 2),
            total_revenue=round(aggregation.total_revenue, 2),
            total_records=aggregation.total_records,
        )

    def get_top_locations_by_volume(
        self,
        aggregations: Sequence[LocationSalesAggregation],
        limit: int = 5,
    ) -> TopLocationResult:
        """Constructs TopLocationResult from pre-aggregated location data."""
        if not aggregations:
            return TopLocationResult(top_locations=[], primary_location=None, primary_quantity=0.0)

        top_list = [
            {
                "local": agg.local,
                "total_quantity": round(agg.total_quantity, 2),
                "total_revenue": round(agg.total_revenue, 2),
            }
            for agg in aggregations[:limit]
        ]

        primary = aggregations[0]

        return TopLocationResult(
            top_locations=top_list,
            primary_location=primary.local,
            primary_quantity=round(primary.total_quantity, 2),
        )

    def get_total_sales_in_period(
        self,
        aggregation: Optional[TotalSalesAggregation],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> TotalSalesResult:
        """Constructs TotalSalesResult from pre-aggregated sales volume and revenue totals."""
        if not aggregation or aggregation.total_records == 0:
            return TotalSalesResult(
                total_quantity=0.0,
                total_revenue=0.0,
                total_records=0,
                period_start=start_date.strftime("%d/%m/%Y") if start_date else None,
                period_end=end_date.strftime("%d/%m/%Y") if end_date else None,
                average_ticket=0.0,
            )

        total_qty = aggregation.total_quantity
        total_rev = aggregation.total_revenue
        avg_ticket = (total_rev / total_qty) if total_qty > 0 else 0.0

        return TotalSalesResult(
            total_quantity=round(total_qty, 2),
            total_revenue=round(total_rev, 2),
            total_records=aggregation.total_records,
            period_start=start_date.strftime("%d/%m/%Y") if start_date else None,
            period_end=end_date.strftime("%d/%m/%Y") if end_date else None,
            average_ticket=round(avg_ticket, 2),
        )

    def compare_planned_vs_actual_quantity(
        self, aggregation: Optional[PlannedVsActualAggregation]
    ) -> PlannedVsActualResult:
        """Constructs PlannedVsActualResult comparing aggregated planned vs actual quantities."""
        if not aggregation or aggregation.total_records == 0:
            return PlannedVsActualResult(
                total_planned_quantity=0.0,
                total_actual_quantity=0.0,
                difference_quantity=0.0,
                achievement_percentage=0.0,
                evaluation="No sales records available",
            )

        total_planned = aggregation.total_planned_quantity
        total_actual = aggregation.total_actual_quantity
        diff = total_actual - total_planned
        pct = (total_actual / total_planned * 100.0) if total_planned > 0 else 0.0

        if pct >= 100.0:
            evaluation = f"Target exceeded by {diff:,.2f} units ({pct:.1f}% achievement)"
        else:
            deficit = total_planned - total_actual
            evaluation = f"Target missed by {deficit:,.2f} units ({pct:.1f}% achievement)"

        return PlannedVsActualResult(
            total_planned_quantity=round(total_planned, 2),
            total_actual_quantity=round(total_actual, 2),
            difference_quantity=round(diff, 2),
            achievement_percentage=round(pct, 2),
            evaluation=evaluation,
        )

    def analyze_promotion_impact(
        self, aggregation: Optional[PromotionImpactAggregation]
    ) -> PromotionImpactResult:
        """Constructs PromotionImpactResult from pre-aggregated promotional metrics."""
        if not aggregation or aggregation.total_records == 0:
            return PromotionImpactResult(
                promoted_sales_count=0,
                non_promoted_sales_count=0,
                promoted_total_quantity=0.0,
                non_promoted_total_quantity=0.0,
                promoted_avg_actual_price=0.0,
                non_promoted_avg_actual_price=0.0,
                volume_lift_percentage=0.0,
                average_discount_in_promotion=0.0,
                summary="No records to analyze",
            )

        promoted_qty = aggregation.promoted_total_quantity
        non_promoted_qty = aggregation.non_promoted_total_quantity
        promoted_count = aggregation.promoted_sales_count
        non_promoted_count = aggregation.non_promoted_sales_count

        promoted_avg_qty = (promoted_qty / promoted_count) if promoted_count > 0 else 0.0
        non_promoted_avg_qty = (non_promoted_qty / non_promoted_count) if non_promoted_count > 0 else 0.0

        if non_promoted_avg_qty > 0:
            volume_lift = ((promoted_avg_qty - non_promoted_avg_qty) / non_promoted_avg_qty) * 100.0
        else:
            volume_lift = 100.0 if promoted_avg_qty > 0 else 0.0

        summary = (
            f"Promotions generated {promoted_qty:,.2f} units across {promoted_count} transactions "
            f"(Avg Price: ${aggregation.promoted_avg_actual_price:.2f}, Avg Discount: {aggregation.average_discount_in_promotion:.1f}%), "
            f"with a volume lift of {volume_lift:+.1f}% per transaction vs non-promoted."
        )

        return PromotionImpactResult(
            promoted_sales_count=promoted_count,
            non_promoted_sales_count=non_promoted_count,
            promoted_total_quantity=round(promoted_qty, 2),
            non_promoted_total_quantity=round(non_promoted_qty, 2),
            promoted_avg_actual_price=round(aggregation.promoted_avg_actual_price, 2),
            non_promoted_avg_actual_price=round(aggregation.non_promoted_avg_actual_price, 2),
            volume_lift_percentage=round(volume_lift, 2),
            average_discount_in_promotion=round(aggregation.average_discount_in_promotion, 2),
            summary=summary,
        )
