"""Outbound persistence adapter for DuckDB."""
import os
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import duckdb

from src.application.port.outbound.sales_data_port import SalesDataPort
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
        FROM read_csv_auto('{normalized_path}', delim=';', header=True)
        """
        self._connection.execute(query)
        logger.info("DuckDB table 'sales_data' initialized successfully.")

    def get_all_sales(self) -> Sequence[SaleRecord]:
        """Retrieves all sales records mapped to domain SaleRecord entities."""
        cursor = self._connection.execute(
            """
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
            """
        )
        rows = cursor.fetchall()
        return [self._map_row_to_entity(row) for row in rows]

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
            parsed_date = date.fromisoformat(raw_date)
        else:
            parsed_date = date.today()

        raw_promo = row[8]
        promo_type = str(raw_promo).strip() if raw_promo and str(raw_promo).strip().lower() not in ("none", "null", "") else None

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
