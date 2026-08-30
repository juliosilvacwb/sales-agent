"""Unit tests for domain models and value objects."""
from dataclasses import FrozenInstanceError
from datetime import date
import pytest

from src.domain.model.aggregation_models import (
    AverageDiscountAggregation,
    LocationSalesAggregation,
    PlannedVsActualAggregation,
    PriceElasticityAggregation,
    ProductAggregation,
    PromotionImpactAggregation,
    RevenueDeficitAggregation,
    SeasonalityAggregation,
    ServiceLevelBottleneckAggregation,
    TotalSalesAggregation,
)
from src.domain.model.metric_result import (
    AverageDiscountResult,
    PlannedVsActualResult,
    PriceElasticityResult,
    PromotionImpactResult,
    RevenueDeficitResult,
    SeasonalityResult,
    ServiceLevelBottleneckResult,
    TopLocationResult,
    TopSellingProductResult,
    TotalSalesResult,
)
from src.domain.model.sale_record import SaleRecord


def test_sale_record_properties():
    """Verify calculated properties on SaleRecord."""
    record = SaleRecord(
        product_id="Prod_01",
        local="Whse_A",
        date=date(2023, 3, 15),
        planned_quantity=100.0,
        actual_quantity=120.0,
        planned_price=50.0,
        actual_price=45.0,
        service_level=0.95,
        promotion_type="Discount_10",
    )

    assert record.date == date(2023, 3, 15)
    assert record.planned_revenue == 5000.0
    assert record.actual_revenue == 5400.0
    assert record.quantity_difference == 20.0
    assert record.revenue_difference == 400.0
    assert record.is_promoted is True
    assert record.discount_rate == 0.10


def test_sale_record_unpromoted():
    """Verify unpromoted records."""
    record = SaleRecord(
        product_id="Prod_02",
        local="Whse_B",
        date=date(2023, 5, 20),
        planned_quantity=50.0,
        actual_quantity=40.0,
        planned_price=10.0,
        actual_price=10.0,
        service_level=1.0,
        promotion_type="None",
    )

    assert record.date == date(2023, 5, 20)
    assert record.is_promoted is False
    assert record.discount_rate == 0.0
    assert record.quantity_difference == -10.0


def test_metric_results_instantiation():
    """Verify all metric result value objects can be created."""
    top_p = TopSellingProductResult("P1", 500.0, 25000.0, 10)
    assert top_p.product_id == "P1"

    top_l = TopLocationResult(
        top_locations=[{"local": "W1", "total_quantity": 100.0}],
        primary_location="W1",
        primary_quantity=100.0,
    )
    assert top_l.primary_location == "W1"

    tot = TotalSalesResult(1000.0, 50000.0, 25, "01/01/2023", "31/12/2023", 50.0)
    assert tot.total_quantity == 1000.0

    pva = PlannedVsActualResult(100.0, 120.0, 20.0, 120.0, "Exceeded")
    assert pva.achievement_percentage == 120.0

    promo = PromotionImpactResult(10, 20, 500.0, 800.0, 45.0, 50.0, 25.0, 10.0, "Lift")
    assert promo.volume_lift_percentage == 25.0

    sla = ServiceLevelBottleneckResult("W2", 0.85, 0.95, {"W2": 0.85}, "Bottleneck")
    assert sla.worst_location == "W2"

    rev_def = RevenueDeficitResult(10000.0, 8000.0, 2000.0, 20.0, True, "Deficit")
    assert rev_def.has_deficit is True

    disc = AverageDiscountResult(10.0, 10000.0, 9000.0, 1000.0, {"Promo": 10.0})
    assert disc.total_discount_value == 1000.0

    seas = SeasonalityResult({"2023-01": 100.0}, "2023-01", 100.0, "2023-01", 100.0, "Pattern")
    assert seas.peak_month == "2023-01"

    elas = PriceElasticityResult(-1.5, -10.0, 15.0, "Elastic", "Summary")
    assert elas.elasticity_coefficient == -1.5


def test_aggregation_models_instantiation():
    """Verify instantiation of all 10 domain aggregation models (TEST003-01)."""
    p_agg = ProductAggregation("Prod_1", 100.0, 1000.0, 5)
    assert p_agg.product_id == "Prod_1"
    assert p_agg.total_quantity == 100.0
    assert p_agg.total_revenue == 1000.0
    assert p_agg.total_records == 5

    loc_agg = LocationSalesAggregation("Whse_A", 200.0, 4000.0)
    assert loc_agg.local == "Whse_A"
    assert loc_agg.total_quantity == 200.0
    assert loc_agg.total_revenue == 4000.0

    tot_agg = TotalSalesAggregation(300.0, 6000.0, 10)
    assert tot_agg.total_quantity == 300.0
    assert tot_agg.total_revenue == 6000.0
    assert tot_agg.total_records == 10

    pva_agg = PlannedVsActualAggregation(500.0, 450.0, 8)
    assert pva_agg.total_planned_quantity == 500.0
    assert pva_agg.total_actual_quantity == 450.0

    promo_agg = PromotionImpactAggregation(2, 4, 150.0, 300.0, 45.0, 50.0, 10.0, 6)
    assert promo_agg.promoted_sales_count == 2
    assert promo_agg.non_promoted_sales_count == 4

    sla_agg = ServiceLevelBottleneckAggregation({"Whse_A": 0.95}, 0.95, 5)
    assert sla_agg.location_averages["Whse_A"] == 0.95

    rev_agg = RevenueDeficitAggregation(10000.0, 9000.0, 10)
    assert rev_agg.total_planned_revenue == 10000.0
    assert rev_agg.total_actual_revenue == 9000.0

    disc_agg = AverageDiscountAggregation(10000.0, 9000.0, 1000.0, 10.0, {"PromoA": 10.0}, 10)
    assert disc_agg.overall_average_discount_percentage == 10.0
    assert disc_agg.total_discount_value == 1000.0

    seas_agg = SeasonalityAggregation({"2023-01": 200.0}, 5)
    assert seas_agg.monthly_volumes["2023-01"] == 200.0

    elas_agg = PriceElasticityAggregation(45.0, 50.0, 150.0, 100.0, 5, 5, 10)
    assert elas_agg.promoted_avg_price == 45.0
    assert elas_agg.non_promoted_avg_price == 50.0


def test_aggregation_models_immutability():
    """Verify strict immutability of aggregation models (TEST003-02)."""
    p_agg = ProductAggregation("P1", 100.0, 500.0, 1)
    with pytest.raises((FrozenInstanceError, TypeError)):
        p_agg.total_quantity = 200.0  # type: ignore
