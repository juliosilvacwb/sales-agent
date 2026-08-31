"""Unit tests for conditional enable_external_access toggle per storage mode."""
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter


class TestConditionalExternalAccess:
    """Verify enable_external_access behavior per mode (local vs S3)."""

    def test_local_mode_disables_external_access(self) -> None:
        """In local mode: SET enable_external_access = false is executed."""
        content = (
            "product_id;local;date;planned_quantity;actual_quantity;"
            "planned_price;actual_price;service_level;promotion_type\n"
            "P1;L1;01/01/2023;10;10;1.0;1.0;0.9;None\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=temp_path)
            # After local initialization, external access should be disabled.
            # Verify by trying to use read_csv_auto - should raise an error
            with pytest.raises(Exception):
                adapter._connection.execute(
                    f"SELECT * FROM read_csv_auto('{temp_path}')"
                )
        finally:
            os.remove(temp_path)

    def test_s3_mode_does_not_disable_external_access(self) -> None:
        """In S3 mode: SET enable_external_access = false is NOT executed."""
        env = {
            "AWS_ACCESS_KEY_ID": "key",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_REGION": "us-east-1",
        }
        mock_conn = MagicMock()

        adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
        adapter._db_path = ":memory:"
        adapter._dataset_path = "s3://bucket/data.csv"
        adapter._is_s3 = True
        adapter._cached_profile = None
        adapter._connection = mock_conn

        with patch.dict(os.environ, env, clear=False):
            adapter._initialize_schema()

        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        # Should NOT contain "enable_external_access = false" in S3 mode
        assert not any(
            "enable_external_access" in s and "false" in s for s in executed_sqls
        ), "S3 mode should not disable external access"

    def test_local_mode_contains_external_access_disable(self) -> None:
        """Verify local mode initialization SQL includes the external access disable statement."""
        content = (
            "product_id;local;date;planned_quantity;actual_quantity;"
            "planned_price;actual_price;service_level;promotion_type\n"
            "P1;L1;01/01/2023;10;10;1.0;1.0;0.9;None\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            mock_conn = MagicMock()
            adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
            adapter._db_path = ":memory:"
            adapter._dataset_path = temp_path
            adapter._is_s3 = False
            adapter._cached_profile = None
            adapter._connection = mock_conn

            adapter._initialize_local_schema()

            executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
            assert any(
                "enable_external_access" in s and "false" in s for s in executed_sqls
            ), "Local mode must disable external access"
        finally:
            os.remove(temp_path)

    def test_external_access_toggle_failure_handled_gracefully_in_local_mode(self) -> None:
        """[TEST015-26] Verify that if SET enable_external_access fails in local mode, error is caught."""
        content = (
            "product_id;local;date;planned_quantity;actual_quantity;"
            "planned_price;actual_price;service_level;promotion_type\n"
            "P1;L1;01/01/2023;10;10;1.0;1.0;0.9;None\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            mock_conn = MagicMock()

            def execute_side_effect(sql: str, *args: object, **kwargs: object) -> MagicMock:
                if "enable_external_access" in sql:
                    raise RuntimeError("External access disable failed")
                return MagicMock()

            mock_conn.execute.side_effect = execute_side_effect

            adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
            adapter._db_path = ":memory:"
            adapter._dataset_path = temp_path
            adapter._is_s3 = False
            adapter._cached_profile = None
            adapter._connection = mock_conn

            # Should complete gracefully without raising exception
            adapter._initialize_local_schema()
            assert adapter._connection is not None
        finally:
            os.remove(temp_path)

    @pytest.mark.parametrize(
        "forbidden_sql",
        [
            "SELECT * FROM read_csv('http://malicious.ssrf.internal/data.csv')",
            "SELECT * FROM read_parquet('s3://exfiltrate-bucket/out.parquet')",
            "INSTALL httpfs;",
            "ATTACH 'evil.db' AS evil;",
            "SELECT * FROM read_json('http://169.254.169.254/latest/meta-data/')",
        ],
    )
    def test_s3_mode_ast_defense_in_depth_blocks_arbitrary_io_functions(self, forbidden_sql: str) -> None:
        """[S015-03] Assert that SqlSecurityValidator blocks SSRF / remote I/O function calls even when external access is active."""
        from src.adapter.outbound.parser.sqlglot_parser_adapter import SqlGlotParserAdapter
        from src.domain.service.sql_security_validator import SqlSecurityValidator

        parser = SqlGlotParserAdapter()
        validator = SqlSecurityValidator()

        parsed = parser.parse(forbidden_sql)
        result = validator.validate(parsed)

        assert not result.is_valid
        assert result.violation_type is not None

