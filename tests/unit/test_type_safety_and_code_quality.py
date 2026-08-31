"""Unit tests for Strict Type Safety and Code Quality (TEST012 / S012)."""
import inspect
import os
import pathlib
import sys
from typing import Any, Callable, Optional, get_type_hints
from unittest.mock import MagicMock

import pytest

# Task 001: requirements.txt and requirements-dev.txt configuration (S012-01)
def test_requirements_contains_mypy_and_ruff_tooling() -> None:
    """[TEST012-01 / S012-01] Validates that requirements-dev.txt declares mypy and ruff dependencies."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    dev_req_file = repo_root / "requirements-dev.txt"
    prod_req_file = repo_root / "requirements.txt"
    assert dev_req_file.exists(), "requirements-dev.txt must exist at repo root"
    assert prod_req_file.exists(), "requirements.txt must exist at repo root"

    content_dev = dev_req_file.read_text(encoding="utf-8")
    lines_dev = [line.strip() for line in content_dev.splitlines() if line.strip() and not line.startswith("#")]

    has_mypy = any(line.startswith("mypy") and ">=1.10.0" in line for line in lines_dev)
    has_ruff = any(line.startswith("ruff") and ">=0.5.0" in line for line in lines_dev)

    assert has_mypy, "requirements-dev.txt must contain mypy>=1.10.0"
    assert has_ruff, "requirements-dev.txt must contain ruff>=0.5.0"

    content_prod = prod_req_file.read_text(encoding="utf-8")
    lines_prod = [line.strip() for line in content_prod.splitlines() if line.strip() and not line.startswith("#")]
    assert not any(line.startswith("mypy") for line in lines_prod), "Production requirements.txt must not contain mypy"
    assert not any(line.startswith("ruff") for line in lines_prod), "Production requirements.txt must not contain ruff"


def test_requirements_contains_type_stubs() -> None:
    """[TEST012-02 / S012-01] Validates that requirements-dev.txt declares types-redis and types-requests stubs."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    dev_req_file = repo_root / "requirements-dev.txt"
    assert dev_req_file.exists(), "requirements-dev.txt must exist at repo root"

    content = dev_req_file.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

    has_types_redis = any(line.startswith("types-redis") and ">=4.6.0" in line for line in lines)
    has_types_requests = any(line.startswith("types-requests") and ">=2.31.0" in line for line in lines)

    assert has_types_redis, "requirements-dev.txt must contain types-redis>=4.6.0"
    assert has_types_requests, "requirements-dev.txt must contain types-requests>=2.31.0"


# Task 002: pyproject.toml configuration (S012-02)
def _load_pyproject_toml() -> dict[str, Any]:
    """Helper to parse pyproject.toml using standard tomllib or fallback."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    pyproject_file = repo_root / "pyproject.toml"
    assert pyproject_file.exists(), "pyproject.toml must exist at repo root"

    if sys.version_info >= (3, 11):
        import tomllib
        with open(pyproject_file, "rb") as f:
            return tomllib.load(f)
    else:
        try:
            import tomli as tomllib  # type: ignore
            with open(pyproject_file, "rb") as f:
                return tomllib.load(f)
        except ImportError:
            content = pyproject_file.read_text(encoding="utf-8")
            return {"_raw": content}


def test_pyproject_mypy_strict_mode_configuration() -> None:
    """[TEST012-03] Validates that pyproject.toml defines strict mode settings in [tool.mypy]."""
    data = _load_pyproject_toml()
    if "_raw" in data:
        raw = data["_raw"]
        assert "[tool.mypy]" in raw
        assert "strict = true" in raw
        assert "disallow_untyped_defs = true" in raw
        assert "no_implicit_optional = true" in raw
        assert "warn_return_any = true" in raw
        assert 'python_version = "3.11"' in raw
    else:
        mypy_cfg = data.get("tool", {}).get("mypy", {})
        assert mypy_cfg.get("strict") is True
        assert mypy_cfg.get("disallow_untyped_defs") is True
        assert mypy_cfg.get("no_implicit_optional") is True
        assert mypy_cfg.get("warn_return_any") is True
        assert mypy_cfg.get("python_version") == "3.11"


def test_pyproject_mypy_third_party_overrides() -> None:
    """[TEST012-04 / S012-02] Validates third-party overrides and security modules exclusion (no jwt/crypto wildcard)."""
    data = _load_pyproject_toml()
    if "_raw" in data:
        raw = data["_raw"]
        assert "[[tool.mypy.overrides]]" in raw
        assert "ignore_missing_imports = true" in raw
        for pkg in ["duckdb", "langchain", "langgraph", "sqlglot", "uvicorn"]:
            assert pkg in raw
        assert "jwt" not in raw
        assert "cryptography" not in raw
    else:
        overrides = data.get("tool", {}).get("mypy", {}).get("overrides", [])
        assert len(overrides) > 0, "Expected at least one tool.mypy.overrides section"
        override = overrides[0]
        assert override.get("ignore_missing_imports") is True
        modules = override.get("module", [])
        modules_str = " ".join(modules)
        for pkg in ["duckdb", "langchain", "langgraph", "sqlglot", "uvicorn"]:
            assert any(pkg in mod for mod in modules), f"Expected package '{pkg}' in mypy overrides: {modules_str}"
        assert not any("jwt" in mod for mod in modules), "jwt.* must not be in ignore_missing_imports (S012-02)"
        assert not any("cryptography" in mod for mod in modules), "cryptography.* must not be in ignore_missing_imports (S012-02)"


def test_pyproject_ruff_linter_and_formatter_configuration() -> None:
    """[TEST012-05] Validates that pyproject.toml defines Ruff linter rules and formatter settings."""
    data = _load_pyproject_toml()
    if "_raw" in data:
        raw = data["_raw"]
        assert "[tool.ruff]" in raw
        assert "line-length = 100" in raw
        assert "[tool.ruff.lint]" in raw
        for rule in ["E", "W", "F", "I", "B", "UP"]:
            assert f'"{rule}"' in raw or f"'{rule}'" in raw
        assert "[tool.ruff.format]" in raw
        assert 'quote-style = "double"' in raw
    else:
        ruff = data.get("tool", {}).get("ruff", {})
        assert ruff.get("line-length") == 100
        lint_select = ruff.get("lint", {}).get("select", [])
        for rule in ["E", "W", "F", "I", "B", "UP"]:
            assert rule in lint_select, f"Expected rule '{rule}' in tool.ruff.lint.select: {lint_select}"
        quote_style = ruff.get("format", {}).get("quote-style")
        assert quote_style == "double"


def test_pyproject_excludes_legacy_pyright_configuration() -> None:
    """[TEST012-06] Validates that legacy pyright configuration is excluded from pyproject.toml."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    pyproject_file = repo_root / "pyproject.toml"
    content = pyproject_file.read_text(encoding="utf-8")
    assert "[tool.pyright]" not in content, "Legacy [tool.pyright] configuration must be removed"


# Task 003: Domain Layer Type Safety
def test_domain_models_strict_type_annotations() -> None:
    """[TEST012-07] Validates strict type annotations on domain model classes."""
    from src.domain.model.aggregation_models import TotalSalesAggregation, ProductAggregation
    from src.domain.model.dataset_profile import DatasetProfile
    from src.domain.model.sale_record import SaleRecord
    from src.domain.model.session_context import SessionContext
    from src.domain.model.sql_validation import SqlValidationResult

    # Check TotalSalesAggregation
    hints_agg = get_type_hints(TotalSalesAggregation)
    assert hints_agg.get("total_quantity") == float
    assert hints_agg.get("total_revenue") == float
    assert hints_agg.get("total_records") == int

    # Check DatasetProfile
    hints_profile = get_type_hints(DatasetProfile)
    assert hints_profile.get("total_records") == int
    assert "null_representations" in hints_profile
    assert "constant_columns" in hints_profile

    # Method type hints
    sig_markdown = inspect.signature(DatasetProfile.to_markdown_block)
    assert sig_markdown.return_annotation is str

    # Check SessionContext methods
    sig_validate = inspect.signature(SessionContext.validate_session_id)
    assert "session_id" in sig_validate.parameters
    assert sig_validate.parameters["session_id"].annotation is str


def test_domain_exceptions_and_enums_type_safety() -> None:
    """[TEST012-08] Validates type safety and signatures of domain exceptions and enums."""
    from src.domain.exception.auth_exceptions import AuthenticationError, InvalidCredentialsError
    from src.domain.exception.session_exceptions import SessionDomainError, SessionConnectionError
    from src.domain.exception.sql_validation_exceptions import SqlSyntaxError, SqlValidationError
    from src.domain.model.sql_validation import SqlViolationType

    # Exception instantiation with proper message types
    auth_err = InvalidCredentialsError("Invalid auth")
    assert isinstance(auth_err, AuthenticationError)
    assert str(auth_err) == "Invalid auth"

    sql_err = SqlSyntaxError("SYNTAX_ERROR", "Malformed SQL syntax")
    assert isinstance(sql_err, SqlValidationError)
    assert "Malformed SQL syntax" in str(sql_err)

    session_err = SessionConnectionError("Redis down")
    assert isinstance(session_err, SessionDomainError)
    assert str(session_err) == "Redis down"

    # Enums
    assert SqlViolationType.DISALLOWED_ROOT_OPERATION.name == "DISALLOWED_ROOT_OPERATION"
    assert SqlViolationType.FORBIDDEN_MUTATIONAL_NODE.name == "FORBIDDEN_MUTATIONAL_NODE"


# Task 004: Application Layer Type Safety
def test_application_ports_abstract_method_type_signatures() -> None:
    """[TEST012-09] Validates complete type annotations on abstract methods of inbound/outbound ports."""
    from src.application.port.inbound.authenticate_user_use_case import AuthenticateUserUseCase
    from src.application.port.inbound.web_chat_use_case import WebChatUseCase
    from src.application.port.outbound.sales_data_port import SalesDataPort
    from src.application.port.outbound.session_store_port import SessionStorePort
    from src.application.port.outbound.sql_parser_port import SqlParserPort

    # WebChatUseCase
    sig_web_chat = inspect.signature(WebChatUseCase.process_chat_message)
    assert sig_web_chat.return_annotation != inspect.Signature.empty
    assert "request" in sig_web_chat.parameters
    assert sig_web_chat.parameters["request"].annotation != inspect.Parameter.empty

    # AuthenticateUserUseCase
    sig_auth = inspect.signature(AuthenticateUserUseCase.authenticate)
    assert sig_auth.return_annotation != inspect.Signature.empty
    assert "credentials" in sig_auth.parameters

    # SalesDataPort
    sig_profile = inspect.signature(SalesDataPort.profile_dataset)
    assert sig_profile.return_annotation != inspect.Signature.empty

    # SessionStorePort
    sig_get_hist = inspect.signature(SessionStorePort.get_history)
    assert sig_get_hist.return_annotation != inspect.Signature.empty
    sig_save_hist = inspect.signature(SessionStorePort.save_history)
    assert sig_save_hist.return_annotation in (None, type(None), "None")
    sig_exists = inspect.signature(SessionStorePort.exists)
    assert sig_exists.return_annotation is bool

    # SqlParserPort
    sig_parse = inspect.signature(SqlParserPort.parse)
    assert sig_parse.return_annotation != inspect.Signature.empty


def test_application_services_dependency_injection_typing() -> None:
    """[TEST012-10] Validates constructor DI and method contracts in Application Services."""
    from src.application.service.authentication_service import AuthenticationApplicationService
    from src.application.service.sales_metrics_service import SalesMetricsApplicationService
    from src.application.service.web_chat_application_service import WebChatApplicationService

    # WebChatApplicationService __init__
    sig_web_init = inspect.signature(WebChatApplicationService.__init__)
    assert "agent_factory" in sig_web_init.parameters
    assert "session_store" in sig_web_init.parameters
    assert sig_web_init.parameters["session_store"].annotation != inspect.Parameter.empty

    # SalesMetricsApplicationService __init__
    sig_metrics_init = inspect.signature(SalesMetricsApplicationService.__init__)
    assert "sales_data_port" in sig_metrics_init.parameters
    assert sig_metrics_init.parameters["sales_data_port"].annotation != inspect.Parameter.empty

    # AuthenticationApplicationService __init__
    sig_auth_init = inspect.signature(AuthenticationApplicationService.__init__)
    assert "token_signer" in sig_auth_init.parameters
    assert "validator" in sig_auth_init.parameters


# Task 005: Adapter Layer Type Safety and Defensive Guards (S012-03)
def test_adapter_layer_optional_and_null_handling_type_safety() -> None:
    """[TEST012-11 / S012-03] Validates Optional annotations and nullability safeguards in adapters."""
    from src.adapter.inbound.llm.sql_fallback_tool import SecuredSQLQueryTool
    from src.adapter.outbound.redis.redis_session_adapter import RedisSessionAdapter

    # RedisSessionAdapter constructor Optional parameters
    sig_redis_init = inspect.signature(RedisSessionAdapter.__init__)
    assert "redis_url" in sig_redis_init.parameters
    assert "ttl_seconds" in sig_redis_init.parameters
    assert "redis_client" in sig_redis_init.parameters

    # SecuredSQLQueryTool attributes/fields
    hints_tool = get_type_hints(SecuredSQLQueryTool)
    assert "use_case" in hints_tool
    assert "sql_parser_port" in hints_tool
    assert "validator" in hints_tool


def test_sql_fallback_tool_defensive_type_guards() -> None:
    """[S012-03] Validates that SecuredSQLQueryTool rejects invalid/empty queries defensively."""
    from langchain_core.tools import ToolException
    from src.adapter.inbound.llm.sql_fallback_tool import create_sql_fallback_tool

    mock_use_case = MagicMock()
    tool = create_sql_fallback_tool(mock_use_case)

    # Empty string or non-string query raises ToolException
    with pytest.raises(ToolException, match="Consulta SQL inválida ou vazia"):
        tool._run("")

    with pytest.raises(ToolException, match="Consulta SQL inválida ou vazia"):
        tool._run("   ")

    # None use_case factory check
    with pytest.raises(ValueError, match="sales_use_case must not be None"):
        create_sql_fallback_tool(None)  # type: ignore


def test_redis_session_adapter_defensive_type_narrowing() -> None:
    """[S012-03] Validates RedisSessionAdapter defensive type narrowing on invalid Redis return payloads."""
    from src.adapter.outbound.redis.redis_session_adapter import RedisSessionAdapter
    from src.domain.exception.session_exceptions import SessionStorageError

    mock_redis = MagicMock()
    adapter = RedisSessionAdapter(redis_client=mock_redis)

    # Case 1: Redis returns None -> empty history
    mock_redis.get.return_value = None
    hist = adapter.get_history("valid-session-123")
    assert len(hist.messages) == 0

    # Case 2: Redis returns non-list JSON -> fallback to empty history
    mock_redis.get.return_value = '{"not": "a_list"}'
    hist_invalid = adapter.get_history("valid-session-123")
    assert len(hist_invalid.messages) == 0

    # Case 3: Save None history -> raises SessionStorageError
    with pytest.raises(SessionStorageError, match="Cannot save None history"):
        adapter.save_history("valid-session-123", None)  # type: ignore


def test_adapter_fastapi_controllers_pydantic_payload_typing() -> None:
    """[TEST012-12] Validates FastAPI route typing, response_model, and Depends annotations."""
    from src.adapter.inbound.web.chat_controller import process_chat, router
    from src.adapter.inbound.web.main import health_check
    from src.application.dto.chat_dto import ChatResponseDTO

    # chat_controller process_chat signature
    sig_process = inspect.signature(process_chat)
    assert sig_process.return_annotation is ChatResponseDTO
    assert "request" in sig_process.parameters
    assert "claims" in sig_process.parameters
    assert "use_case" in sig_process.parameters

    # Check router route definitions
    chat_route = next((r for r in router.routes if getattr(r, "path", None) == "/chat"), None)
    assert chat_route is not None, "Expected /chat route in chat_controller router"
    assert getattr(chat_route, "response_model", None) is ChatResponseDTO

    # Health check route typing
    sig_health = inspect.signature(health_check)
    assert sig_health.return_annotation != inspect.Signature.empty


# Task 006: CI/CD Quality Gate Workflow (S012-04)
def test_ci_workflow_lint_and_typecheck_job_structure() -> None:
    """[TEST012-13 / S012-04] Validates that GitHub Actions ci-cd.yml contains lint-and-typecheck with requirements-dev."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    ci_file = repo_root / ".github" / "workflows" / "ci-cd.yml"
    assert ci_file.exists(), ".github/workflows/ci-cd.yml must exist"

    content = ci_file.read_text(encoding="utf-8")
    assert "lint-and-typecheck:" in content
    assert "timeout-minutes: 5" in content
    assert "ruff check ." in content
    assert "ruff format --check ." in content
    assert "mypy src/" in content
    assert "pip install -r requirements-dev.txt" in content


def test_ci_workflow_gating_halts_on_failure() -> None:
    """[TEST012-14] Validates that test-suite job strictly depends on lint-and-typecheck with no bypass."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    ci_file = repo_root / ".github" / "workflows" / "ci-cd.yml"
    content = ci_file.read_text(encoding="utf-8")

    assert "needs: [ lint-and-typecheck ]" in content or "needs: [lint-and-typecheck]" in content
    assert "continue-on-error: true" not in content, "CI quality gates must not contain continue-on-error bypasses"


def test_ci_workflow_permissions_least_privilege() -> None:
    """[S012-04] Validates that GitHub Actions ci-cd.yml enforces principle of least privilege permissions."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    ci_file = repo_root / ".github" / "workflows" / "ci-cd.yml"
    content = ci_file.read_text(encoding="utf-8")

    assert "permissions:" in content
    assert "contents: read" in content
