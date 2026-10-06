"""Unit tests for decide container appliance and deployment configurations (Task 07 / Module 07)."""

import os
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from decide.bootstrap import main as bootstrap_main
from scripts.bake_model import bake


def test_dockerfile_structure():
    """Verify Dockerfile contains required base image, volume, healthcheck, and entrypoint."""
    dockerfile_path = Path("Dockerfile")
    assert dockerfile_path.exists(), "Dockerfile must exist at repository root"

    content = dockerfile_path.read_text()
    assert "FROM python:3.11-slim" in content
    assert 'VOLUME ["/data"]' in content
    assert "EXPOSE 8000" in content
    assert 'ENTRYPOINT ["./entrypoint.sh"]' in content
    assert "HEALTHCHECK" in content
    assert "http://localhost:8000/health" in content
    assert "bake_model.py" in content


def test_entrypoint_script():
    """Verify entrypoint.sh is executable and configures volume directory and uvicorn."""
    entrypoint_path = Path("entrypoint.sh")
    assert entrypoint_path.exists(), "entrypoint.sh must exist at repository root"
    assert os.access(entrypoint_path, os.X_OK), "entrypoint.sh must be executable"

    content = entrypoint_path.read_text()
    assert "#!/usr/bin/env bash" in content
    assert "mkdir -p" in content
    assert "python -m decide.bootstrap" in content
    assert "exec uvicorn decide.main:app" in content
    assert "--workers" in content
    assert "--lifespan on" in content


def test_docker_compose_configuration():
    """Verify docker-compose.yml defines decide service, volume, and healthcheck."""
    compose_path = Path("docker-compose.yml")
    assert compose_path.exists(), "docker-compose.yml must exist at repository root"

    content = compose_path.read_text()
    assert "services:" in content
    assert "decide:" in content
    assert "8000:8000" in content
    assert "decide_data:/data" in content
    assert "healthcheck:" in content
    assert "volumes:" in content
    assert "decide_data:" in content


def test_dockerignore_configuration():
    """Verify .dockerignore excludes virtualenvs, caches, and test artifacts."""
    ignore_path = Path(".dockerignore")
    assert ignore_path.exists(), ".dockerignore must exist at repository root"

    content = ignore_path.read_text()
    assert ".venv" in content
    assert "__pycache__" in content
    assert ".git" in content
    assert "*.db" in content


def test_offline_verification_script():
    """Verify tests/test_offline_boot.sh exists and tests --network none execution."""
    script_path = Path("tests/test_offline_boot.sh")
    assert script_path.exists(), "tests/test_offline_boot.sh must exist"
    assert os.access(script_path, os.X_OK), "tests/test_offline_boot.sh must be executable"

    content = script_path.read_text()
    assert "--network none" in content
    assert "curl" in content
    assert "/health" in content


def test_bake_model_script_fallback(monkeypatch, tmp_path):
    """Verify scripts/bake_model.py handles exceptions gracefully during build."""
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "hf_cache"))
    monkeypatch.setenv("MODEL_CHECKPOINT", "test/mock-checkpoint")

    # Mock AutoExtractor failure path
    mock_extractor = MagicMock()
    mock_extractor.from_pretrained.side_effect = RuntimeError("Network unreachable")
    monkeypatch.setattr("gliner2.AutoExtractor", mock_extractor)

    # Should gracefully catch error, print warning, and return False (not crash or raise)
    result = bake()
    assert result is False

    # Test success path
    mock_extractor.from_pretrained.side_effect = None
    mock_extractor.from_pretrained.return_value = MagicMock()
    assert bake() is True



def test_bootstrap_main_execution(monkeypatch, tmp_path):
    """Verify decide.bootstrap main() executes without crashing."""
    test_db = tmp_path / "bootstrap_unit.db"
    monkeypatch.setenv("DATABASE_PATH", str(test_db))
    monkeypatch.setenv("ADMIN_PASSWORD", "UnitBootstrapPass123!")

    # Clear cached settings
    from decide.config import get_settings
    get_settings.cache_clear()

    bootstrap_main()
    assert test_db.exists(), "Bootstrap must provision database file"
