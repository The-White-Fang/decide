"""Integrated contract test suite for Task 1: Configuration & Cryptographic Utilities."""

from decide.config import Settings
from decide.crypto import (
    generate_admin_password,
    hash_password,
    verify_password,
    generate_api_key,
    extract_key_prefix,
    hash_api_key,
    constant_time_compare,
)


def test_admin_credential_bootstrap_pipeline():
    """
    Validates the end-to-end credential creation pipeline:
    If admin_password is unset in Settings, generate secure 24-character password,
    hash it with bcrypt, and verify authentication succeeds.
    """
    settings = Settings()
    assert settings.admin_password is None

    # Auto-generation flow
    generated_pwd = generate_admin_password(24)
    assert len(generated_pwd) == 24

    hashed = hash_password(generated_pwd)
    assert verify_password(generated_pwd, hashed) is True
    assert verify_password("incorrect_admin_pass", hashed) is False


def test_api_key_lifecycle_contract():
    """
    Validates complete API key generation, prefix slicing, hashing,
    and constant-time validation flow.
    """
    # 1. Generate key
    raw_key = generate_api_key()
    assert raw_key.startswith("dec_")
    assert len(raw_key) == 36

    # 2. Extract prefix for dashboard
    prefix = extract_key_prefix(raw_key)
    assert len(prefix) == 10
    assert prefix == raw_key[:10]

    # 3. Hash for database storage
    stored_hash = hash_api_key(raw_key)
    assert len(stored_hash) == 64

    # 4. Incoming client request verification
    incoming_key = str(raw_key)
    incoming_hash = hash_api_key(incoming_key)
    assert constant_time_compare(incoming_hash, stored_hash) is True

    # 5. Tampered request rejection
    tampered_key = raw_key[:-1] + ("A" if raw_key[-1] != "A" else "B")
    tampered_hash = hash_api_key(tampered_key)
    assert constant_time_compare(tampered_hash, stored_hash) is False
