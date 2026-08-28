"""Domain Service for Basic Sales Metrics.

Zero framework dependencies - pure business logic calculations.
"""
from collections import defaultdict
from datetime import date
from typing import List, Optional, Sequence

from src.domain.model.metric_result import (
    PlannedVsActualResult,
    PromotionImpactResult,
    TopLocationResult,
    TopSellingProductResult,
    TotalSalesResult,
)
from src.domain.model.sale_record import SaleRecord


class BasicMetricsService:
    """Calculates deterministic basic sales metrics."""

    def get_top_selling_product(
        self, records: Sequence[SaleRecord]
    ) -> TopSellingProductResult:
        """Identifies the product with the highest total actual sales volume."""
        if not records:
            return TopSellingProductResult(
                product_id="N/A",
                total_quantity=0.0,
                total_revenue=0.0,
                total_records=0,
            )

        product_quantities = defaultdict(float)
        product_revenues = defaultdict(float)
        product_counts = defaultdict(int)

        for r in records:
            product_quantities[r.product_id] += r.actual_quantity
            product_revenues[r.product_id] += r.actual_revenue
            product_counts[r.product_id] += 1

        top_product = max(product_quantities.items(), key=lambda x: x[1])[0]

        return TopSellingProductResult(
            product_id=top_product,
            total_quantity=round(product_quantities[top_product], 2),
            total_revenue=round(product_revenues[top_product], 2),
            total_records=product_counts[top_product],
        )

    def get_top_locations_by_volume(
        self, records: Sequence[SaleRecord], limit: int = 5
    ) -> TopLocationResult:
        """Identifies locations sorted by highest sales volume."""
        if not records:
            return TopLocationResult(top_locations=[], primary_location=None, primary_quantity=0.0)

        loc_quantities = defaultdict(float)
        loc_revenues = defaultdict(float)

        for r in records:
            loc_quantities[r.local] += r.actual_quantity
            loc_revenues[r.local] += r.actual_revenue

        sorted_locs = sorted(loc_quantities.items(), key=lambda x: x[1], reverse=True)
        top_list = [
            {
                "local": loc,
                "total_quantity": round(qty, 2),
                "total_revenue": round(loc_revenues[loc], 2),
            }
            for loc, qty in sorted_locs[:limit]
        ]

        primary = sorted_locs[0] if sorted_locs else ("N/A", 0.0)

        return TopLocationResult(
            top_locations=top_list,
            primary_location=primary[0],
            primary_quantity=round(primary[1], 2),
        )

    def get_total_sales_in_period(
        self,
        records: Sequence[SaleRecord],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> TotalSalesResult:
        """Calculates total sales (quantity and revenue), optionally filtered by period."""
        filtered: List[SaleRecord] = []
        for r in records:
            if start_date and r.date < start_date:
                continue
            if end_date and r.date > end_date:
                continue
            filtered.append(r)

        total_qty = sum(r.actual_quantity for r in filtered)
        total_rev = sum(r.actual_revenue for r in filtered)
        total_recs = len(filtered)
        avg_ticket = (total_rev / total_qty) if total_qty > 0 else 0.0

        return TotalSalesResult(
            total_quantity=round(total_qty, 2),
            total_revenue=round(total_rev, 2),
            total_records=total_recs,
            period_start=start_date.strftime("%d/%m/%Y") if start_date else None,
            period_end=end_date.strftime("%d/%m/%Y") if end_date else None,
            average_ticket=round(avg_ticket, 2),
        )

    def compare_planned_vs_actual_quantity(
        self, records: Sequence[SaleRecord]
    ) -> PlannedVsActualResult:
        """Compares total planned quantity against realized quantity."""
        if not records:
            return PlannedVsActualResult(
                total_planned_quantity=0.0,
                total_actual_quantity=0.0,
                difference_quantity=0.0,
                achievement_percentage=0.0,
                evaluation="No sales records available",
            )

        total_planned = sum(r.planned_quantity for r in records)
        total_actual = sum(r.actual_quantity for r in records)
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
        self, records: Sequence[SaleRecord]
    ) -> PromotionImpactResult:
        """Evaluates the impact of promotions on actual prices and sales volumes."""
        if not records:
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

        promoted = [r for r in records if r.is_promoted]
        non_promoted = [r for r in records if not r.is_promoted]

        promoted_qty = sum(r.actual_quantity for r in promoted)
        non_promoted_qty = sum(r.actual_quantity for r in non_promoted)

        promoted_avg_price = (
            sum(r.actual_price for r in promoted) / len(promoted) if promoted else 0.0
        )
        non_promoted_avg_price = (
            sum(r.actual_price for r in non_promoted) / len(non_promoted)
            if non_promoted
            else 0.0
        )

        promoted_avg_discount = (
            sum(r.discount_rate for r in promoted) / len(promoted) * 100.0
            if promoted
            else 0.0
        )

        # Calculate average quantity per transaction to assess lift
        promoted_avg_qty = (promoted_qty / len(promoted)) if promoted else 0.0
        non_promoted_avg_qty = (non_promoted_qty / len(non_promoted)) if non_promoted else 0.0

        if non_promoted_avg_qty > 0:
            volume_lift = ((promoted_avg_qty - non_promoted_avg_qty) / non_promoted_avg_qty) * 100.0
        else:
            volume_lift = 100.0 if promoted_avg_qty > 0 else 0.0

        summary = (
            f"Promotions generated {promoted_qty:,.2f} units across {len(promoted)} transactions "
            f"(Avg Price: ${promoted_avg_price:.2f}, Avg Discount: {promoted_avg_discount:.1f}%), "
            f"with a volume lift of {volume_lift:+.1f}% per transaction vs non-promoted."
        )

        return PromotionImpactResult(
            promoted_sales_count=len(promoted),
            non_promoted_sales_count=len(non_promoted),
            promoted_total_quantity=round(promoted_qty, 2),
            non_promoted_total_quantity=round(non_promoted_qty, 2),
            promoted_avg_actual_price=round(promoted_avg_price, 2),
            non_promoted_avg_actual_price=round(non_promoted_avg_price, 2),
            volume_lift_percentage=round(volume_lift, 2),
            average_discount_in_promotion=round(promoted_avg_discount, 2),
            summary=summary,
        )
