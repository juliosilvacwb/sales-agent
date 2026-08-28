"""Unit tests for project scaffolding verification."""
from pathlib import Path


def test_project_structure_directories():
    """Verify that all required hexagonal architecture directories exist."""
    base_dir = Path(__file__).resolve().parent.parent.parent

    expected_dirs = [
        base_dir / "src",
        base_dir / "src" / "domain",
        base_dir / "src" / "domain" / "model",
        base_dir / "src" / "domain" / "service",
        base_dir / "src" / "application",
        base_dir / "src" / "application" / "port",
        base_dir / "src" / "application" / "port" / "in",
        base_dir / "src" / "application" / "port" / "out",
        base_dir / "src" / "application" / "service",
        base_dir / "src" / "adapter",
        base_dir / "src" / "adapter" / "in",
        base_dir / "src" / "adapter" / "in" / "cli",
        base_dir / "src" / "adapter" / "in" / "llm",
        base_dir / "src" / "adapter" / "out",
        base_dir / "src" / "adapter" / "out" / "persistence",
        base_dir / "src" / "adapter" / "out" / "llm",
        base_dir / "dataset",
        base_dir / "tests",
        base_dir / "tests" / "unit",
        base_dir / "tests" / "integration",
    ]

    for directory in expected_dirs:
        assert directory.exists(), f"Directory does not exist: {directory}"
        assert directory.is_dir(), f"Path is not a directory: {directory}"


def test_required_configuration_files():
    """Verify that configuration and documentation files exist."""
    base_dir = Path(__file__).resolve().parent.parent.parent

    expected_files = [
        base_dir / "requirements.txt",
        base_dir / ".env.example",
        base_dir / ".gitignore",
        base_dir / "dataset" / "sales.csv",
    ]

    for file_path in expected_files:
        assert file_path.exists(), f"Required file does not exist: {file_path}"
        assert file_path.is_file(), f"Path is not a file: {file_path}"


def test_env_example_contains_essential_keys():
    """Verify that .env.example contains the essential environment variables."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    env_example = base_dir / ".env.example"
    content = env_example.read_text(encoding="utf-8")

    expected_keys = [
        "LLM_PROVIDER",
        "MODEL_NAME",
        "DATASET_PATH",
    ]

    for key in expected_keys:
        assert key in content, f"Key '{key}' missing from .env.example"


def test_package_imports():
    """Verify that all created packages can be imported successfully."""
    import src
    import src.domain
    import src.domain.model
    import src.domain.service
    import src.application
    import src.application.port
    import src.application.port.in
    import src.application.port.out
    import src.application.service
    import src.adapter
    import src.adapter.in
    import src.adapter.in.cli
    import src.adapter.in.llm
    import src.adapter.out
    import src.adapter.out.persistence
    import src.adapter.out.llm

    assert src is not None
