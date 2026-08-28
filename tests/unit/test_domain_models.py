"""Unit tests for domain models and value objects."""
from datetime import date
from src.domain.model.sale_record import SaleRecord
from src.domain.model.metric_result import (
    TopSellingProductResult,
    TopLocationResult,
    TotalSalesResult,
    PlannedVsActualResult,
    PromotionImpactResult,
    ServiceLevelBottleneckResult,
    RevenueDeficitResult,
    AverageDiscountResult,
    SeasonalityResult,
    PriceElasticityResult,
)


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

    top_l = TopLocationResult(top_locations=[{"local": "W1", "total_quantity": 100.0}], primary_location="W1", primary_quantity=100.0)
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
