"""Comprehensive unit tests for decide.crypto module."""

import re
import string
import pytest
from decide.crypto import (
    hash_password,
    verify_password,
    generate_admin_password,
    generate_session_secret,
    generate_api_key,
    extract_key_prefix,
    hash_api_key,
    constant_time_compare,
)


def test_password_hashing_and_verification():
    """Verify password hashing with bcrypt and matching verification."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    # Positive verification
    assert verify_password(password, hashed) is True

    # Negative verification
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False


def test_password_unicode_characters():
    """Verify password hashing and verification support full Unicode charset."""
    unicode_passwords = [
        "パスワード12345",
        "Pässwörd!_€99",
        "🔐SecureKey_2026✨",
        "пароль_секрет_123",
    ]
    for pwd in unicode_passwords:
        hashed = hash_password(pwd)
        assert verify_password(pwd, hashed) is True
        assert verify_password(pwd + "x", hashed) is False


def test_password_different_salts():
    """Verify two hashes of the same password produce different bcrypt salts."""
    pwd = "SamePasswordEveryTime123"
    h1 = hash_password(pwd)
    h2 = hash_password(pwd)

    assert h1 != h2
    assert verify_password(pwd, h1) is True
    assert verify_password(pwd, h2) is True


def test_password_corrupted_hash():
    """Verify corrupt or truncated bcrypt hashes fail gracefully without crashing."""
    assert verify_password("test", "corrupted_non_bcrypt_string") is False
    assert verify_password("test", "$2b$12$short") is False
    assert verify_password("test", "") is False


def test_password_invalid_types():
    """Verify password hashing rejects non-strings and verification handles invalid types."""
    with pytest.raises(TypeError):
        hash_password(12345)  # type: ignore

    with pytest.raises(TypeError):
        hash_password(None)  # type: ignore

    assert verify_password(None, "hash") is False  # type: ignore
    assert verify_password("pass", None) is False  # type: ignore


def test_generate_admin_password():
    """Verify generated admin password meets complexity and length requirements."""
    pwd = generate_admin_password()
    assert len(pwd) == 24
    assert all(c in string.ascii_letters + string.digits for c in pwd)

    custom_pwd = generate_admin_password(32)
    assert len(custom_pwd) == 32

    # Multiple calls produce different passwords
    pwd2 = generate_admin_password()
    assert pwd != pwd2

    with pytest.raises(ValueError):
        generate_admin_password(7)


def test_generate_session_secret():
    """Verify session secret generation produces 32-byte (64 hex char) random strings."""
    secret1 = generate_session_secret()
    secret2 = generate_session_secret()

    assert len(secret1) == 64
    assert all(c in string.hexdigits for c in secret1)
    assert secret1 != secret2


def test_generate_api_key_format_and_pattern():
    """Verify API key conforms to dec_<32_random_alphanumeric_characters> contract."""
    key = generate_api_key()

    pattern = re.compile(r"^dec_[a-zA-Z0-9]{32}$")
    assert pattern.match(key) is not None
    assert len(key) == 36


def test_generate_api_key_uniqueness_batch():
    """Verify high entropy and uniqueness across 500 generated keys."""
    keys = {generate_api_key() for _ in range(500)}
    assert len(keys) == 500


def test_extract_key_prefix():
    """Verify key prefix extraction returns exactly first 10 characters."""
    key = "dec_1234567890abcdefghijklmnopqr"
    prefix = extract_key_prefix(key)

    assert len(prefix) == 10
    assert prefix == "dec_123456"

    # Exact 10 character boundary
    exact_10 = "dec_123456"
    assert extract_key_prefix(exact_10) == "dec_123456"

    with pytest.raises(ValueError):
        extract_key_prefix("dec_short")

    with pytest.raises(ValueError):
        extract_key_prefix("")

    with pytest.raises(ValueError):
        extract_key_prefix(1234567890)  # type: ignore


def test_hash_api_key_determinism_and_format():
    """Verify SHA-256 API key hashing produces 64-character deterministic lowercase hex digest."""
    key = "dec_testkey1234567890123456789012"
    hash1 = hash_api_key(key)
    hash2 = hash_api_key(key)

    assert len(hash1) == 64
    assert re.match(r"^[a-f0-9]{64}$", hash1) is not None
    assert hash1 == hash2

    # Distinct keys produce distinct hashes
    other_hash = hash_api_key("dec_anotherkey12345678901234567890")
    assert hash1 != other_hash


def test_hash_api_key_invalid_inputs():
    """Verify invalid inputs to hash_api_key raise ValueError."""
    with pytest.raises(ValueError):
        hash_api_key("")

    with pytest.raises(ValueError):
        hash_api_key(None)  # type: ignore

    with pytest.raises(ValueError):
        hash_api_key(12345)  # type: ignore


def test_constant_time_compare_comprehensive():
    """Verify constant-time equality comparisons across edge cases."""
    base = "dec_hash_digest_1234567890abcdef"

    # Exact match
    assert constant_time_compare(base, str(base)) is True

    # Empty strings
    assert constant_time_compare("", "") is True

    # Length mismatch
    assert constant_time_compare(base, base[:-1]) is False
    assert constant_time_compare(base, base + "x") is False

    # Single character difference at start, middle, end
    assert constant_time_compare("x" + base[1:], base) is False
    mid = len(base) // 2
    assert constant_time_compare(base[:mid] + "x" + base[mid + 1:], base) is False
    assert constant_time_compare(base[:-1] + "x", base) is False

    # Non-string types
    assert constant_time_compare(base, None) is False  # type: ignore
    assert constant_time_compare(None, base) is False  # type: ignore
    assert constant_time_compare(12345, 12345) is False  # type: ignore
