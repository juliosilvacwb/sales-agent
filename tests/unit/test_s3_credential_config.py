"""Unit tests for httpfs extension installation and AWS credential SET commands."""
import logging
import os
from unittest.mock import MagicMock, call, patch

import pytest

from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.domain.exception.s3_exceptions import S3ConnectionError


class TestHttpfsAndCredentialConfig:
    """Verify httpfs installation and AWS credential SET commands are emitted correctly."""

    def _build_adapter_with_mock_connection(
        self, dataset_path: str = "s3://bucket/data.csv", env_overrides: dict | None = None
    ) -> tuple[DuckDbSalesAdapter, MagicMock]:
        """Helper to create an adapter with a mocked DuckDB connection for S3 mode."""
        env = {
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "AWS_REGION": "us-east-1",
        }
        if env_overrides:
            env.update(env_overrides)

        mock_conn = MagicMock()
        adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
        adapter._db_path = ":memory:"
        adapter._dataset_path = dataset_path
        adapter._is_s3 = dataset_path.lower().startswith("s3://")
        adapter._cached_profile = None
        adapter._connection = mock_conn

        with patch.dict(os.environ, env, clear=False):
            adapter._initialize_schema()

        return adapter, mock_conn

    def test_httpfs_install_and_load_called(self) -> None:
        """Verify INSTALL httpfs and LOAD httpfs are called during S3 initialization."""
        _, mock_conn = self._build_adapter_with_mock_connection()
        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("INSTALL httpfs" in s for s in executed_sqls)
        assert any("LOAD httpfs" in s for s in executed_sqls)

    def test_s3_region_set_from_env(self) -> None:
        """Verify SET s3_region is called with value from AWS_REGION env var."""
        _, mock_conn = self._build_adapter_with_mock_connection()
        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("s3_region" in s and "us-east-1" in s for s in executed_sqls)

    def test_s3_access_key_id_set_from_env(self) -> None:
        """Verify SET s3_access_key_id is called with AWS_ACCESS_KEY_ID value."""
        _, mock_conn = self._build_adapter_with_mock_connection()
        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("s3_access_key_id" in s and "AKIAIOSFODNN7EXAMPLE" in s for s in executed_sqls)

    def test_s3_secret_access_key_set_from_env(self) -> None:
        """Verify SET s3_secret_access_key is called with AWS_SECRET_ACCESS_KEY value."""
        _, mock_conn = self._build_adapter_with_mock_connection()
        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("s3_secret_access_key" in s and "wJalrXUtnFEMI" in s for s in executed_sqls)

    def test_s3_session_token_set_when_present(self) -> None:
        """Verify SET s3_session_token is called only when AWS_SESSION_TOKEN is set."""
        _, mock_conn = self._build_adapter_with_mock_connection(
            env_overrides={"AWS_SESSION_TOKEN": "FwoGZXIvYXdzE"}
        )
        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("s3_session_token" in s and "FwoGZXIvYXdzE" in s for s in executed_sqls)

    def test_s3_session_token_not_set_when_absent(self) -> None:
        """Verify SET s3_session_token is NOT called when AWS_SESSION_TOKEN is not set."""
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

        # Ensure AWS_SESSION_TOKEN is not in the environment
        cleaned_env = {k: v for k, v in os.environ.items() if k != "AWS_SESSION_TOKEN"}
        cleaned_env.update(env)

        with patch.dict(os.environ, cleaned_env, clear=True):
            adapter._initialize_schema()

        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        assert not any("s3_session_token" in s for s in executed_sqls)

    def test_s3_endpoint_set_when_present(self) -> None:
        """Verify SET s3_endpoint is called when AWS_ENDPOINT_URL is set (for MinIO/LocalStack)."""
        _, mock_conn = self._build_adapter_with_mock_connection(
            env_overrides={"AWS_ENDPOINT_URL": "http://localhost:9000"}
        )
        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("s3_endpoint" in s and "localhost:9000" in s for s in executed_sqls)

    @pytest.mark.parametrize("false_val", ["false", "0", "no", "False", "NO"])
    def test_s3_use_ssl_disabled_configurations(self, false_val: str) -> None:
        """[TEST015-16] Verify SET s3_use_ssl = false is called for all falsy values in S3_USE_SSL."""
        _, mock_conn = self._build_adapter_with_mock_connection(
            env_overrides={"S3_USE_SSL": false_val}
        )
        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("s3_use_ssl" in s and "false" in s for s in executed_sqls)

    def test_aws_credentials_not_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """[TEST015-17] Verify secret keys and access keys are not logged (CWE-798)."""
        secret_value = "SUPER_SECRET_AWS_KEY_12345"
        with caplog.at_level(logging.DEBUG):
            self._build_adapter_with_mock_connection(
                env_overrides={"AWS_SECRET_ACCESS_KEY": secret_value}
            )

        for record in caplog.records:
            assert secret_value not in record.message

    def test_s3_connection_error_raised_when_missing_access_key(self) -> None:
        """Verify S3ConnectionError is raised when AWS_ACCESS_KEY_ID is missing."""
        mock_conn = MagicMock()
        adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
        adapter._db_path = ":memory:"
        adapter._dataset_path = "s3://bucket/data.csv"
        adapter._is_s3 = True
        adapter._cached_profile = None
        adapter._connection = mock_conn

        env = {"AWS_SECRET_ACCESS_KEY": "secret", "AWS_REGION": "us-east-1"}
        cleaned_env = {k: v for k, v in os.environ.items() if k != "AWS_ACCESS_KEY_ID"}
        cleaned_env.update(env)

        with patch.dict(os.environ, cleaned_env, clear=True):
            with pytest.raises(S3ConnectionError) as exc_info:
                adapter._initialize_schema()

        assert exc_info.value.status_code == 403
        assert "AWS_ACCESS_KEY_ID" in exc_info.value.message

    def test_s3_connection_error_raised_when_missing_secret_key(self) -> None:
        """Verify S3ConnectionError is raised when AWS_SECRET_ACCESS_KEY is missing."""
        mock_conn = MagicMock()
        adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
        adapter._db_path = ":memory:"
        adapter._dataset_path = "s3://bucket/data.csv"
        adapter._is_s3 = True
        adapter._cached_profile = None
        adapter._connection = mock_conn

        env = {"AWS_ACCESS_KEY_ID": "key", "AWS_REGION": "us-east-1"}
        cleaned_env = {k: v for k, v in os.environ.items() if k != "AWS_SECRET_ACCESS_KEY"}
        cleaned_env.update(env)

        with patch.dict(os.environ, cleaned_env, clear=True):
            with pytest.raises(S3ConnectionError) as exc_info:
                adapter._initialize_schema()

        assert exc_info.value.status_code == 403

    def test_aws_default_region_fallback(self) -> None:
        """Verify AWS_DEFAULT_REGION is used when AWS_REGION is not set."""
        env = {
            "AWS_ACCESS_KEY_ID": "key",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_DEFAULT_REGION": "eu-west-1",
        }
        mock_conn = MagicMock()
        adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
        adapter._db_path = ":memory:"
        adapter._dataset_path = "s3://bucket/data.csv"
        adapter._is_s3 = True
        adapter._cached_profile = None
        adapter._connection = mock_conn

        cleaned_env = {k: v for k, v in os.environ.items() if k not in ("AWS_REGION", "AWS_DEFAULT_REGION")}
        cleaned_env.update(env)

        with patch.dict(os.environ, cleaned_env, clear=True):
            adapter._initialize_schema()

        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("s3_region" in s and "eu-west-1" in s for s in executed_sqls)

    def test_view_creation_sql_contains_s3_path(self) -> None:
        """Verify the VIEW creation SQL references the S3 URI."""
        s3_path = "s3://my-bucket/my-data.csv"
        _, mock_conn = self._build_adapter_with_mock_connection(dataset_path=s3_path)
        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("CREATE VIEW" in s and s3_path in s for s in executed_sqls)

    def test_s3_credentials_single_quotes_escaped(self) -> None:
        """[S015-01] Verify single quotes in AWS credentials and config values are escaped with double single-quotes."""
        env_with_quotes = {
            "AWS_ACCESS_KEY_ID": "AKIA'INJECTION_TEST",
            "AWS_SECRET_ACCESS_KEY": "SECRET'KEY'VALUE",
            "AWS_REGION": "us-east-1'--",
            "AWS_SESSION_TOKEN": "TOKEN'WITH'QUOTES",
            "AWS_ENDPOINT_URL": "http://minio'host:9000",
        }
        _, mock_conn = self._build_adapter_with_mock_connection(
            env_overrides=env_with_quotes
        )
        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("AKIA''INJECTION_TEST" in s for s in executed_sqls)
        assert any("SECRET''KEY''VALUE" in s for s in executed_sqls)
        assert any("us-east-1''--" in s for s in executed_sqls)
        assert any("TOKEN''WITH''QUOTES" in s for s in executed_sqls)
        assert any("http://minio''host:9000" in s for s in executed_sqls)

    def test_sanitize_s3_error_masks_credentials_and_signatures(self) -> None:
        """[S015-02] Verify _sanitize_s3_error masks signatures, authorization headers, tokens, and secret keys."""
        raw_error = (
            "HTTP 403 Forbidden: Authorization: AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20260831/us-east-1/s3/aws4_request, "
            "SignedHeaders=host;x-amz-date, Signature=d8a4f91b7c8932ef8a74e921e428 "
            "X-Amz-Security-Token=AQoDYXdzEJr12345 s3_secret_access_key = 'wJalrXUtnFEMI/K7MDENG' "
            "AWS_SECRET_ACCESS_KEY=SuperSecretVal123"
        )
        sanitized = DuckDbSalesAdapter._sanitize_s3_error(raw_error)

        assert "Signature=d8a4f91b" not in sanitized
        assert "Signature=[REDACTED]" in sanitized
        assert "AQoDYXdzEJr12345" not in sanitized
        assert "X-Amz-Security-Token=[REDACTED]" in sanitized
        assert "wJalrXUtnFEMI/K7MDENG" not in sanitized
        assert "s3_secret_access_key = '[REDACTED]'" in sanitized
        assert "SuperSecretVal123" not in sanitized
        assert "AWS_SECRET_ACCESS_KEY=[REDACTED]" in sanitized

