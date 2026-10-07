"""Comprehensive unit tests for decide.config module."""

from pathlib import Path
import pytest
from pydantic import ValidationError
from decide.config import Settings, get_settings


def test_default_settings():
    """Verify default settings adhere strictly to PRD Section 8 and Section 10."""
    settings = Settings()

    assert settings.admin_username == "admin"
    assert settings.admin_password is None
    assert settings.force_admin_reset is False
    assert settings.database_path == Path("/data/decide.db")
    assert settings.secret_key is None
    assert settings.device == "auto"
    assert settings.port == 8000
    assert settings.workers == 1

    # Security limits
    assert settings.max_input_text_length == 8000
    assert settings.max_task_count == 20
    assert settings.max_labels_per_task == 50

    # Model defaults
    assert settings.model_checkpoint == "fastino/GLiNER2.5-Decide"
    assert settings.cache_dir == Path("/root/.cache/huggingface/")


def test_environment_variable_override(monkeypatch):
    """Verify settings can be customized via OS environment variables."""
    monkeypatch.setenv("ADMIN_USERNAME", "superadmin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret_pass_12345")
    monkeypatch.setenv("FORCE_ADMIN_RESET", "true")
    monkeypatch.setenv("DATABASE_PATH", "/custom/path/app.db")
    monkeypatch.setenv("SECRET_KEY", "custom_session_signing_secret")
    monkeypatch.setenv("DEVICE", "cuda")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("WORKERS", "2")

    settings = Settings()

    assert settings.admin_username == "superadmin"
    assert settings.admin_password == "secret_pass_12345"
    assert settings.force_admin_reset is True
    assert settings.database_path == Path("/custom/path/app.db")
    assert settings.secret_key == "custom_session_signing_secret"
    assert settings.device == "cuda"
    assert settings.port == 9000
    assert settings.workers == 2
    get_settings.cache_clear()


@pytest.mark.parametrize(
    "flag,expected",
    [
        ("true", True),
        ("True", True),
        ("1", True),
        ("false", False),
        ("False", False),
        ("0", False),
    ],
)
def test_boolean_flag_coercion(monkeypatch, flag, expected):
    """Verify boolean env flags parse correctly."""
    monkeypatch.setenv("FORCE_ADMIN_RESET", flag)
    settings = Settings()
    assert settings.force_admin_reset is expected


def test_device_validation_allowed_values():
    """Verify device accepts only auto, cpu, or cuda."""
    assert Settings(device="auto").device == "auto"
    assert Settings(device="cpu").device == "cpu"
    assert Settings(device="cuda").device == "cuda"

    with pytest.raises(ValidationError):
        Settings(device="tpu")

    with pytest.raises(ValidationError):
        Settings(device="invalid")

    with pytest.raises(ValidationError):
        Settings(device="CUDA")  # case sensitive check


def test_port_validation_range():
    """Verify port must be between 1 and 65535."""
    assert Settings(port=1).port == 1
    assert Settings(port=8080).port == 8080
    assert Settings(port=65535).port == 65535

    with pytest.raises(ValidationError):
        Settings(port=0)

    with pytest.raises(ValidationError):
        Settings(port=-1)

    with pytest.raises(ValidationError):
        Settings(port=65536)

    with pytest.raises(ValidationError):
        Settings(port=70000)


def test_workers_validation_range():
    """Verify worker bounds."""
    assert Settings(workers=1).workers == 1
    assert Settings(workers=4).workers == 4
    assert Settings(workers=32).workers == 32

    with pytest.raises(ValidationError):
        Settings(workers=0)

    with pytest.raises(ValidationError):
        Settings(workers=-1)

    with pytest.raises(ValidationError):
        Settings(workers=33)


def test_guardrails_validation_bounds():
    """Verify bounds on security guardrail settings."""
    with pytest.raises(ValidationError):
        Settings(max_input_text_length=0)

    with pytest.raises(ValidationError):
        Settings(max_task_count=0)

    with pytest.raises(ValidationError):
        Settings(max_labels_per_task=0)


def test_path_type_conversion():
    """Verify string paths are automatically converted to pathlib.Path instances."""
    s = Settings(
        database_path="/custom/dir/data.sqlite",  # type: ignore
        cache_dir="/custom/cache/dir",  # type: ignore
    )
    assert isinstance(s.database_path, Path)
    assert isinstance(s.cache_dir, Path)
    assert s.database_path == Path("/custom/dir/data.sqlite")
    assert s.cache_dir == Path("/custom/cache/dir")


def test_ignore_unknown_extra_env_vars(monkeypatch):
    """Verify extra/unknown environment variables are ignored without failing."""
    monkeypatch.setenv("RANDOM_UNDEFINED_VAR", "ignore_me")
    monkeypatch.setenv("ANOTHER_VAR_XYZ", "123")
    settings = Settings()
    assert not hasattr(settings, "RANDOM_UNDEFINED_VAR")


def test_ensure_db_dir(tmp_path):
    """Verify ensure_db_dir creates parent directory if it does not exist, idempotently."""
    nested_db = tmp_path / "deeply" / "nested" / "app.db"
    settings = Settings(database_path=nested_db)

    assert not nested_db.parent.exists()
    created_dir = settings.ensure_db_dir()

    assert created_dir.exists()
    assert created_dir == nested_db.parent

    # Calling again should be idempotent without error
    second_call = settings.ensure_db_dir()
    assert second_call.exists()


def test_dotenv_file_loading(tmp_path, monkeypatch):
    """Verify settings loads from .env file when present."""
    env_file = tmp_path / ".env"
    env_file.write_text("PORT=8888\nADMIN_USERNAME=env_admin\nDEVICE=cpu\n")

    monkeypatch.chdir(tmp_path)
    settings = Settings(_env_file=str(env_file))

    assert settings.port == 8888
    assert settings.admin_username == "env_admin"
    assert settings.device == "cpu"


def test_get_settings_caching():
    """Verify get_settings returns singleton cached instance and responds to cache_clear."""
    get_settings.cache_clear()
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
    get_settings.cache_clear()
