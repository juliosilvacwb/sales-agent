"""Outbound persistence adapter for DuckDB."""
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import duckdb

from src.application.port.outbound.sales_data_port import SalesDataPort
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
from src.domain.model.sale_record import SaleRecord

logger = logging.getLogger(__name__)


class DuckDbSalesAdapter(SalesDataPort):
    """DuckDB implementation of SalesDataPort for in-process high performance analytical queries."""

    def __init__(
        self,
        db_path: str = ":memory:",
        dataset_path: Optional[str] = None,
    ) -> None:
        """Initializes the DuckDB connection and loads sales dataset into memory."""
        self._db_path = db_path
        self._dataset_path = dataset_path or os.getenv("DATASET_PATH", "dataset/sales.csv")
        self._connection = duckdb.connect(database=self._db_path)
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        """Loads sales dataset into DuckDB in-memory table 'sales_data' if file exists."""
        csv_file = Path(self._dataset_path)
        if not csv_file.exists():
            logger.warning("Dataset file not found at %s. Creating empty sales_data schema.", self._dataset_path)
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sales_data (
                    product_id VARCHAR,
                    local VARCHAR,
                    date DATE,
                    planned_quantity DOUBLE,
                    actual_quantity DOUBLE,
                    planned_price DOUBLE,
                    actual_price DOUBLE,
                    service_level DOUBLE,
                    promotion_type VARCHAR
                )
                """
            )
            return

        logger.info("Loading sales dataset from %s into DuckDB...", self._dataset_path)
        normalized_path = str(csv_file.resolve()).replace("\\", "/")
        escaped_path = normalized_path.replace("'", "''")

        # Load CSV using read_csv_auto with semicolon delimiter and robust date parsing
        query = f"""
        CREATE TABLE IF NOT EXISTS sales_data AS
        SELECT
            CAST(product_id AS VARCHAR) AS product_id,
            CAST(local AS VARCHAR) AS local,
            COALESCE(TRY_STRPTIME(CAST(date AS VARCHAR), '%d/%m/%Y')::DATE, TRY_CAST(date AS DATE)) AS date,
            CAST(planned_quantity AS DOUBLE) AS planned_quantity,
            CAST(actual_quantity AS DOUBLE) AS actual_quantity,
            CAST(planned_price AS DOUBLE) AS planned_price,
            CAST(actual_price AS DOUBLE) AS actual_price,
            CAST(service_level AS DOUBLE) AS service_level,
            NULLIF(NULLIF(TRIM(CAST(promotion_type AS VARCHAR)), 'None'), '') AS promotion_type
        FROM read_csv_auto('{escaped_path}', delim=';', header=True)
        """
        self._connection.execute(query)
        # Harden DuckDB against arbitrary file reads/network access post-ingestion
        try:
            self._connection.execute("SET enable_external_access = false;")
        except Exception as e:
            logger.warning("Could not set enable_external_access=false: %s", e)
        logger.info("DuckDB table 'sales_data' initialized successfully.")

    def aggregate_top_selling_product(self) -> Optional[ProductAggregation]:
        """Aggregates product sales and returns the top selling product."""
        query = """
        SELECT
            product_id,
            SUM(actual_quantity) AS total_quantity,
            SUM(actual_quantity * actual_price) AS total_revenue,
            COUNT(*) AS total_records
        FROM sales_data
        GROUP BY product_id
        ORDER BY total_quantity DESC
        LIMIT 1
        """
        cursor = self._connection.execute(query)
        row = cursor.fetchone()
        if not row or row[0] is None:
            return None
        return ProductAggregation(
            product_id=str(row[0]),
            total_quantity=float(row[1]),
            total_revenue=float(row[2]),
            total_records=int(row[3]),
        )

    def aggregate_top_locations(self, limit: int = 5) -> Sequence[LocationSalesAggregation]:
        """Aggregates sales by location ordered by highest volume."""
        query = """
        SELECT
            local,
            SUM(actual_quantity) AS total_quantity,
            SUM(actual_quantity * actual_price) AS total_revenue
        FROM sales_data
        GROUP BY local
        ORDER BY total_quantity DESC
        LIMIT ?
        """
        cursor = self._connection.execute(query, [limit])
        rows = cursor.fetchall()
        return [
            LocationSalesAggregation(
                local=str(row[0]),
                total_quantity=float(row[1]),
                total_revenue=float(row[2]),
            )
            for row in rows
        ]

    def aggregate_total_sales(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> TotalSalesAggregation:
        """Aggregates total volume and revenue, optionally filtered by period."""
        conditions = ["1=1"]
        params: List[Any] = []

        if start_date:
            conditions.append("date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("date <= ?")
            params.append(end_date)

        query = f"""
        SELECT
            COALESCE(SUM(actual_quantity), 0.0) AS total_quantity,
            COALESCE(SUM(actual_quantity * actual_price), 0.0) AS total_revenue,
            COUNT(*) AS total_records
        FROM sales_data
        WHERE {" AND ".join(conditions)}
        """
        cursor = self._connection.execute(query, params)
        row = cursor.fetchone()
        if not row:
            return TotalSalesAggregation(total_quantity=0.0, total_revenue=0.0, total_records=0)
        return TotalSalesAggregation(
            total_quantity=float(row[0]),
            total_revenue=float(row[1]),
            total_records=int(row[2]),
        )

    def aggregate_planned_vs_actual(self) -> PlannedVsActualAggregation:
        """Aggregates planned vs actual sales quantities."""
        query = """
        SELECT
            COALESCE(SUM(planned_quantity), 0.0) AS total_planned_quantity,
            COALESCE(SUM(actual_quantity), 0.0) AS total_actual_quantity,
            COUNT(*) AS total_records
        FROM sales_data
        """
        cursor = self._connection.execute(query)
        row = cursor.fetchone()
        if not row:
            return PlannedVsActualAggregation(
                total_planned_quantity=0.0, total_actual_quantity=0.0, total_records=0
            )
        return PlannedVsActualAggregation(
            total_planned_quantity=float(row[0]),
            total_actual_quantity=float(row[1]),
            total_records=int(row[2]),
        )

    def aggregate_promotion_impact(self) -> PromotionImpactAggregation:
        """Aggregates sales metrics comparing promotional vs non-promotional transactions."""
        promo_cond = "promotion_type IS NOT NULL AND TRIM(promotion_type) != '' AND LOWER(TRIM(promotion_type)) != 'none'"
        query = f"""
        SELECT
            COUNT(*) FILTER (WHERE {promo_cond}) AS promoted_sales_count,
            COUNT(*) FILTER (WHERE NOT ({promo_cond})) AS non_promoted_sales_count,
            COALESCE(SUM(actual_quantity) FILTER (WHERE {promo_cond}), 0.0) AS promoted_total_quantity,
            COALESCE(SUM(actual_quantity) FILTER (WHERE NOT ({promo_cond})), 0.0) AS non_promoted_total_quantity,
            COALESCE(AVG(actual_price) FILTER (WHERE {promo_cond}), 0.0) AS promoted_avg_actual_price,
            COALESCE(AVG(actual_price) FILTER (WHERE NOT ({promo_cond})), 0.0) AS non_promoted_avg_actual_price,
            COALESCE(AVG(CASE WHEN planned_price > 0 AND actual_price < planned_price THEN (planned_price - actual_price) / planned_price ELSE 0.0 END) FILTER (WHERE {promo_cond}) * 100.0, 0.0) AS average_discount_in_promotion,
            COUNT(*) AS total_records
        FROM sales_data
        """
        cursor = self._connection.execute(query)
        row = cursor.fetchone()
        if not row:
            return PromotionImpactAggregation(
                promoted_sales_count=0,
                non_promoted_sales_count=0,
                promoted_total_quantity=0.0,
                non_promoted_total_quantity=0.0,
                promoted_avg_actual_price=0.0,
                non_promoted_avg_actual_price=0.0,
                average_discount_in_promotion=0.0,
                total_records=0,
            )
        return PromotionImpactAggregation(
            promoted_sales_count=int(row[0]),
            non_promoted_sales_count=int(row[1]),
            promoted_total_quantity=float(row[2]),
            non_promoted_total_quantity=float(row[3]),
            promoted_avg_actual_price=float(row[4]),
            non_promoted_avg_actual_price=float(row[5]),
            average_discount_in_promotion=float(row[6]),
            total_records=int(row[7]),
        )

    def aggregate_service_level_bottlenecks(self) -> ServiceLevelBottleneckAggregation:
        """Aggregates average SLA across locations and fleet total."""
        loc_query = """
        SELECT
            local,
            AVG(service_level) AS avg_sla
        FROM sales_data
        GROUP BY local
        """
        cursor = self._connection.execute(loc_query)
        loc_rows = cursor.fetchall()
        loc_averages: Dict[str, float] = {str(row[0]): float(row[1]) for row in loc_rows}

        overall_query = """
        SELECT
            COALESCE(AVG(service_level), 0.0) AS overall_avg_sla,
            COUNT(*) AS total_records
        FROM sales_data
        """
        cursor = self._connection.execute(overall_query)
        overall_row = cursor.fetchone()
        overall_avg = float(overall_row[0]) if overall_row else 0.0
        total_records = int(overall_row[1]) if overall_row else 0

        return ServiceLevelBottleneckAggregation(
            location_averages=loc_averages,
            overall_average_service_level=overall_avg,
            total_records=total_records,
        )

    def aggregate_revenue_deficit(self) -> RevenueDeficitAggregation:
        """Aggregates planned vs actual revenues to compute potential deficits."""
        query = """
        SELECT
            COALESCE(SUM(planned_quantity * planned_price), 0.0) AS total_planned_revenue,
            COALESCE(SUM(actual_quantity * actual_price), 0.0) AS total_actual_revenue,
            COUNT(*) AS total_records
        FROM sales_data
        """
        cursor = self._connection.execute(query)
        row = cursor.fetchone()
        if not row:
            return RevenueDeficitAggregation(
                total_planned_revenue=0.0, total_actual_revenue=0.0, total_records=0
            )
        return RevenueDeficitAggregation(
            total_planned_revenue=float(row[0]),
            total_actual_revenue=float(row[1]),
            total_records=int(row[2]),
        )

    def aggregate_average_discount(self) -> AverageDiscountAggregation:
        """Aggregates average discount percentages and breakdown by promotion."""
        totals_query = """
        SELECT
            COALESCE(SUM(planned_quantity * planned_price), 0.0) AS total_planned_revenue,
            COALESCE(SUM(actual_quantity * actual_price), 0.0) AS total_actual_revenue,
            COALESCE(SUM(CASE WHEN planned_price > actual_price THEN actual_quantity * (planned_price - actual_price) ELSE 0.0 END), 0.0) AS total_discount_value,
            COALESCE(AVG((planned_price - actual_price) / planned_price) FILTER (WHERE planned_price > 0 AND actual_price < planned_price) * 100.0, 0.0) AS overall_avg_discount,
            COUNT(*) AS total_records
        FROM sales_data
        """
        cursor = self._connection.execute(totals_query)
        tot_row = cursor.fetchone()
        if not tot_row:
            return AverageDiscountAggregation(
                total_planned_revenue=0.0,
                total_actual_revenue=0.0,
                total_discount_value=0.0,
                overall_average_discount_percentage=0.0,
                discount_by_promotion={},
                total_records=0,
            )

        promo_query = """
        SELECT
            COALESCE(NULLIF(TRIM(promotion_type), ''), 'None') AS promo,
            AVG((planned_price - actual_price) / planned_price) * 100.0 AS avg_disc
        FROM sales_data
        WHERE planned_price > 0 AND actual_price < planned_price
        GROUP BY promo
        """
        cursor = self._connection.execute(promo_query)
        promo_rows = cursor.fetchall()
        promo_dict: Dict[str, float] = {str(row[0]): float(row[1]) for row in promo_rows}

        return AverageDiscountAggregation(
            total_planned_revenue=float(tot_row[0]),
            total_actual_revenue=float(tot_row[1]),
            total_discount_value=float(tot_row[2]),
            overall_average_discount_percentage=float(tot_row[3]),
            discount_by_promotion=promo_dict,
            total_records=int(tot_row[4]),
        )

    def aggregate_seasonality(self) -> SeasonalityAggregation:
        """Aggregates sales volumes by month."""
        query = """
        SELECT
            STRFTIME(date, '%Y-%m') AS month_key,
            SUM(actual_quantity) AS total_qty
        FROM sales_data
        WHERE date IS NOT NULL
        GROUP BY month_key
        ORDER BY month_key
        """
        cursor = self._connection.execute(query)
        rows = cursor.fetchall()
        monthly_volumes: Dict[str, float] = {
            str(row[0]): float(row[1]) for row in rows if row[0] is not None
        }

        count_cursor = self._connection.execute("SELECT COUNT(*) FROM sales_data")
        count_row = count_cursor.fetchone()
        total_records = int(count_row[0]) if count_row else 0

        return SeasonalityAggregation(
            monthly_volumes=monthly_volumes,
            total_records=total_records,
        )

    def aggregate_price_elasticity(
        self, product_id: Optional[str] = None
    ) -> List[PriceElasticityAggregation]:
        """Aggregates promotional and baseline prices and quantities for price elasticity per product segment."""
        # Check if explicit promotion_type exists
        check_query = """
        SELECT
            COUNT(*) FILTER (WHERE promotion_type IS NOT NULL AND TRIM(promotion_type) != '' AND LOWER(TRIM(promotion_type)) != 'none') AS promo_cnt,
            COUNT(*) FILTER (WHERE promotion_type IS NULL OR TRIM(promotion_type) = '' OR LOWER(TRIM(promotion_type)) = 'none') AS non_promo_cnt
        FROM sales_data
        """
        cursor = self._connection.execute(check_query)
        check_row = cursor.fetchone()
        has_promo_types = check_row and check_row[0] > 0 and check_row[1] > 0

        if has_promo_types:
            promo_cond = "promotion_type IS NOT NULL AND TRIM(promotion_type) != '' AND LOWER(TRIM(promotion_type)) != 'none'"
        else:
            # Fallback to discount rate
            promo_cond = "planned_price > 0 AND actual_price < planned_price"

        where_clause = ""
        params: List[Any] = []
        if product_id is not None and product_id.strip() != "":
            where_clause = "WHERE product_id = ?"
            params.append(product_id.strip())

        query = f"""
        SELECT
            product_id,
            COALESCE(AVG(actual_price) FILTER (WHERE {promo_cond}), 0.0) AS promo_avg_p,
            COALESCE(AVG(actual_price) FILTER (WHERE NOT ({promo_cond})), 0.0) AS non_promo_avg_p,
            COALESCE(AVG(actual_quantity) FILTER (WHERE {promo_cond}), 0.0) AS promo_avg_q,
            COALESCE(AVG(actual_quantity) FILTER (WHERE NOT ({promo_cond})), 0.0) AS non_promo_avg_q,
            COUNT(*) FILTER (WHERE {promo_cond}) AS promo_count,
            COUNT(*) FILTER (WHERE NOT ({promo_cond})) AS non_promo_count,
            COUNT(*) AS total_records
        FROM sales_data
        {where_clause}
        GROUP BY product_id
        ORDER BY product_id
        """
        cursor = self._connection.execute(query, params)
        rows = cursor.fetchall()
        if not rows:
            return []

        return [
            PriceElasticityAggregation(
                product_id=str(row[0]),
                promoted_avg_price=float(row[1]),
                non_promoted_avg_price=float(row[2]),
                promoted_avg_qty=float(row[3]),
                non_promoted_avg_qty=float(row[4]),
                promoted_count=int(row[5]),
                non_promoted_count=int(row[6]),
                total_records=int(row[7]),
            )
            for row in rows
        ]


    def get_sales_by_filter(
        self,
        product_id: Optional[str] = None,
        local: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Sequence[SaleRecord]:
        """Retrieves sales records matching the given criteria."""
        conditions = ["1=1"]
        params: List[Any] = []

        if product_id:
            conditions.append("product_id = ?")
            params.append(product_id)
        if local:
            conditions.append("local = ?")
            params.append(local)
        if start_date:
            conditions.append("date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("date <= ?")
            params.append(end_date)

        sql = f"""
        SELECT
            product_id,
            local,
            date,
            planned_quantity,
            actual_quantity,
            planned_price,
            actual_price,
            service_level,
            promotion_type
        FROM sales_data
        WHERE {" AND ".join(conditions)}
        """
        cursor = self._connection.execute(sql, params)
        rows = cursor.fetchall()
        return [self._map_row_to_entity(row) for row in rows]

    def execute_read_only_query(self, query: str) -> List[Dict[str, Any]]:
        """Executes a read-only analytical SQL query against DuckDB and returns list of dictionaries."""
        logger.debug("Executing DuckDB query: %s", query)
        cursor = self._connection.execute(query)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    @staticmethod
    def _map_row_to_entity(row: Sequence[Any]) -> SaleRecord:
        """Maps a database row tuple to a pure domain SaleRecord."""
        raw_date = row[2]
        if isinstance(raw_date, datetime):
            parsed_date = raw_date.date()
        elif isinstance(raw_date, date):
            parsed_date = raw_date
        elif isinstance(raw_date, str):
            cleaned_date = raw_date.strip()
            try:
                parsed_date = datetime.strptime(cleaned_date, "%d/%m/%Y").date()
            except ValueError:
                parsed_date = date.fromisoformat(cleaned_date)
        else:
            parsed_date = date.today()

        raw_promo = row[8]
        promo_type = (
            str(raw_promo).strip()
            if raw_promo and str(raw_promo).strip().lower() not in ("none", "null", "")
            else None
        )

        return SaleRecord(
            product_id=str(row[0]),
            local=str(row[1]),
            date=parsed_date,
            planned_quantity=float(row[3]) if row[3] is not None else 0.0,
            actual_quantity=float(row[4]) if row[4] is not None else 0.0,
            planned_price=float(row[5]) if row[5] is not None else 0.0,
            actual_price=float(row[6]) if row[6] is not None else 0.0,
            service_level=float(row[7]) if row[7] is not None else 0.0,
            promotion_type=promo_type,
        )
