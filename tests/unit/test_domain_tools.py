"""Unit tests for LangChain Domain Tools."""
from datetime import date
from unittest.mock import MagicMock
import pytest

from src.adapter.inbound.llm.domain_tools import create_domain_tools
from src.application.port.inbound.sales_analysis_usecase import SalesAnalysisUseCase
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


@pytest.fixture
def mock_sales_usecase():
    usecase = MagicMock(spec=SalesAnalysisUseCase)
    usecase.get_top_selling_product.return_value = TopSellingProductResult(
        product_id="Prod_01", total_quantity=1000.0, total_revenue=50000.0, total_records=10
    )
    usecase.get_top_locations_by_volume.return_value = TopLocationResult(
        top_locations=[{"local": "Whse_A", "total_quantity": 1000.0}],
        primary_location="Whse_A",
        primary_quantity=1000.0,
    )
    usecase.get_total_sales_in_period.return_value = TotalSalesResult(
        total_quantity=500.0, total_revenue=25000.0, total_records=5, period_start="01/01/2023", period_end="31/01/2023", average_ticket=5000.0
    )
    usecase.compare_planned_vs_actual_quantity.return_value = PlannedVsActualResult(
        total_planned_quantity=1000.0,
        total_actual_quantity=950.0,
        difference_quantity=-50.0,
        achievement_percentage=95.0,
        evaluation="Abaixo da Meta",
    )
    usecase.analyze_promotion_impact.return_value = PromotionImpactResult(
        promoted_sales_count=10,
        non_promoted_sales_count=20,
        promoted_total_quantity=500.0,
        non_promoted_total_quantity=400.0,
        promoted_avg_actual_price=45.0,
        non_promoted_avg_actual_price=50.0,
        volume_lift_percentage=25.0,
        average_discount_in_promotion=10.0,
        summary="Promoção aumentou volume em 25.0%.",
    )
    usecase.analyze_service_level_bottlenecks.return_value = ServiceLevelBottleneckResult(
        worst_location="Whse_B",
        worst_service_level=0.85,
        overall_average_service_level=0.92,
        location_averages={"Whse_A": 0.95, "Whse_B": 0.85},
        summary="Gargalo logístico em Whse_B",
    )
    usecase.calculate_revenue_deficit.return_value = RevenueDeficitResult(
        total_planned_revenue=100000.0,
        total_actual_revenue=90000.0,
        total_revenue_deficit=10000.0,
        deficit_percentage=10.0,
        has_deficit=True,
        summary="Déficit de R$ 10,000.00",
    )
    usecase.calculate_average_discount.return_value = AverageDiscountResult(
        overall_average_discount_percentage=7.5,
        total_planned_revenue=100000.0,
        total_actual_revenue=92500.0,
        total_discount_value=7500.0,
        discount_by_promotion={"Promo10": 10.0},
    )
    usecase.identify_sales_seasonality.return_value = SeasonalityResult(
        monthly_volumes={"2023-01": 100.0, "2023-02": 300.0},
        peak_month="2023-02",
        peak_volume=300.0,
        lowest_month="2023-01",
        lowest_volume=100.0,
        seasonality_pattern="Pico em Fevereiro",
    )
    usecase.calculate_price_elasticity.return_value = PriceElasticityResult(
        elasticity_coefficient=-1.5,
        percentage_change_in_price=-10.0,
        percentage_change_in_quantity=15.0,
        demand_classification="Elástica",
        summary="Demanda Elástica",
    )
    return usecase


def test_create_domain_tools_count(mock_sales_usecase):
    """Test that all 10 domain tools are created."""
    tools = create_domain_tools(mock_sales_usecase)
    assert len(tools) == 10
    tool_names = {t.name for t in tools}
    expected_names = {
        "get_top_selling_product",
        "get_top_locations_by_volume",
        "get_total_sales_in_period",
        "compare_planned_vs_actual_quantity",
        "analyze_promotion_impact",
        "analyze_service_level_bottlenecks",
        "calculate_revenue_deficit",
        "calculate_average_discount",
        "identify_sales_seasonality",
        "calculate_price_elasticity",
    }
    assert tool_names == expected_names


def test_tool_get_top_selling_product(mock_sales_usecase):
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}
    result = tools["get_top_selling_product"].invoke({})
    mock_sales_usecase.get_top_selling_product.assert_called_once()
    assert "Prod_01" in str(result)
    assert "1000.0" in str(result)


def test_tool_get_top_locations_by_volume(mock_sales_usecase):
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}
    result = tools["get_top_locations_by_volume"].invoke({"limit": 3})
    mock_sales_usecase.get_top_locations_by_volume.assert_called_once_with(limit=3)
    assert "Whse_A" in str(result)


def test_tool_get_top_locations_by_volume_limit_normalization(mock_sales_usecase):
    mock_sales_usecase.reset_mock()
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}

    # Negative limit should be clamped to 1
    tools["get_top_locations_by_volume"].invoke({"limit": -10})
    mock_sales_usecase.get_top_locations_by_volume.assert_called_with(limit=1)

    # Excessively large limit should be clamped to 100
    mock_sales_usecase.reset_mock()
    tools["get_top_locations_by_volume"].invoke({"limit": 99999})
    mock_sales_usecase.get_top_locations_by_volume.assert_called_with(limit=100)


def test_tool_get_total_sales_in_period(mock_sales_usecase):
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}
    result = tools["get_total_sales_in_period"].invoke(
        {"start_date": "2023-01-01", "end_date": "2023-01-31"}
    )
    mock_sales_usecase.get_total_sales_in_period.assert_called_once_with(
        start_date=date(2023, 1, 1), end_date=date(2023, 1, 31)
    )
    assert "500.0" in str(result)


def test_tool_get_total_sales_in_period_brazilian_format(mock_sales_usecase):
    mock_sales_usecase.reset_mock()
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}
    result = tools["get_total_sales_in_period"].invoke(
        {"start_date": "15/01/2023", "end_date": "31/12/2023"}
    )
    mock_sales_usecase.get_total_sales_in_period.assert_called_once_with(
        start_date=date(2023, 1, 15), end_date=date(2023, 12, 31)
    )
    assert "500.0" in str(result)


def test_tool_get_total_sales_in_period_brazilian_dotted_and_dashed_format(mock_sales_usecase):
    mock_sales_usecase.reset_mock()
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}
    result = tools["get_total_sales_in_period"].invoke(
        {"start_date": "01.05.2023", "end_date": "31-05-2023"}
    )
    mock_sales_usecase.get_total_sales_in_period.assert_called_once_with(
        start_date=date(2023, 5, 1), end_date=date(2023, 5, 31)
    )
    assert "500.0" in str(result)


def test_tool_get_total_sales_in_period_invalid_date(mock_sales_usecase):
    mock_sales_usecase.reset_mock()
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}
    result = tools["get_total_sales_in_period"].invoke(
        {"start_date": "invalid-date", "end_date": "2023-01-31"}
    )
    assert "Erro de validação de data" in str(result)
    mock_sales_usecase.get_total_sales_in_period.assert_not_called()


def test_tool_compare_planned_vs_actual_quantity(mock_sales_usecase):
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}
    result = tools["compare_planned_vs_actual_quantity"].invoke({})
    mock_sales_usecase.compare_planned_vs_actual_quantity.assert_called_once()
    assert "95.0" in str(result)


def test_tool_analyze_promotion_impact(mock_sales_usecase):
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}
    result = tools["analyze_promotion_impact"].invoke({})
    mock_sales_usecase.analyze_promotion_impact.assert_called_once()
    assert "25.0" in str(result)


def test_tool_analyze_service_level_bottlenecks(mock_sales_usecase):
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}
    result = tools["analyze_service_level_bottlenecks"].invoke({})
    mock_sales_usecase.analyze_service_level_bottlenecks.assert_called_once()
    assert "Whse_B" in str(result)


def test_tool_calculate_revenue_deficit(mock_sales_usecase):
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}
    result = tools["calculate_revenue_deficit"].invoke({})
    mock_sales_usecase.calculate_revenue_deficit.assert_called_once()
    assert "10000.0" in str(result)


def test_tool_calculate_average_discount(mock_sales_usecase):
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}
    result = tools["calculate_average_discount"].invoke({})
    mock_sales_usecase.calculate_average_discount.assert_called_once()
    assert "7.5" in str(result)


def test_tool_identify_sales_seasonality(mock_sales_usecase):
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}
    result = tools["identify_sales_seasonality"].invoke({})
    mock_sales_usecase.identify_sales_seasonality.assert_called_once()
    assert "2023-02" in str(result)


def test_tool_calculate_price_elasticity(mock_sales_usecase):
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}
    result = tools["calculate_price_elasticity"].invoke({})
    mock_sales_usecase.calculate_price_elasticity.assert_called_with(product_id=None)
    assert "-1.5" in str(result)

    result_prod = tools["calculate_price_elasticity"].invoke({"product_id": "PROD_01"})
    mock_sales_usecase.calculate_price_elasticity.assert_called_with(product_id="PROD_01")
    assert "-1.5" in str(result_prod)


def test_tool_get_total_sales_in_period_raises_tool_exception(mock_sales_usecase):
    """Test that domain tool raises ToolException when date format is invalid."""
    from langchain_core.tools import StructuredTool, ToolException
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}
    tool = tools["get_total_sales_in_period"]
    
    assert isinstance(tool, StructuredTool) and tool.func is not None
    with pytest.raises(ToolException) as exc_info:
        tool.func(start_date="invalid-date", end_date="2023-01-31")

    assert "Erro de validação de data" in str(exc_info.value)
    mock_sales_usecase.get_total_sales_in_period.assert_not_called()


def test_domain_tools_handle_tool_error_configured(mock_sales_usecase):
    """Test that all 10 domain tools created by factory have handle_tool_error = True (AC01)."""
    tools = create_domain_tools(mock_sales_usecase)
    assert len(tools) == 10
    for tool in tools:
        assert tool.handle_tool_error is not None
        assert tool.handle_tool_error is True or callable(tool.handle_tool_error)


def test_tool_get_total_sales_in_period_valid_date_formats(mock_sales_usecase):
    """Test that valid Brazilian (DD/MM/YYYY, DD.MM.YYYY, DD-MM-YYYY) and ISO formats parse correctly."""
    mock_sales_usecase.reset_mock()
    tools = {t.name: t for t in create_domain_tools(mock_sales_usecase)}

    # Test ISO format
    tools["get_total_sales_in_period"].invoke({"start_date": "2023-01-01", "end_date": "2023-01-31"})
    mock_sales_usecase.get_total_sales_in_period.assert_called_with(
        start_date=date(2023, 1, 1), end_date=date(2023, 1, 31)
    )

    # Test Brazilian slash format
    mock_sales_usecase.reset_mock()
    tools["get_total_sales_in_period"].invoke({"start_date": "15/01/2023", "end_date": "31/12/2023"})
    mock_sales_usecase.get_total_sales_in_period.assert_called_with(
        start_date=date(2023, 1, 15), end_date=date(2023, 12, 31)
    )

    # Test Brazilian dot and dash format
    mock_sales_usecase.reset_mock()
    tools["get_total_sales_in_period"].invoke({"start_date": "01.05.2023", "end_date": "31-05-2023"})
    mock_sales_usecase.get_total_sales_in_period.assert_called_with(
        start_date=date(2023, 5, 1), end_date=date(2023, 5, 31)
    )


